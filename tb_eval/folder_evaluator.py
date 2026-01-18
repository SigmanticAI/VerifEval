"""
Folder-based verification evaluator.

Takes a folder containing verification files (testbenches, interfaces, etc.)
and evaluates them against a DUT.
"""

import os
import shutil
import subprocess
from pathlib import Path
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple
import json
import re

from .config import BenchmarkConfig, GENERATED_DIR, RESULTS_DIR


@dataclass
class VerificationFolder:
    """Represents a verification folder structure."""
    path: Path
    dut_files: List[Path] = field(default_factory=list)
    tb_files: List[Path] = field(default_factory=list)
    support_files: List[Path] = field(default_factory=list)  # interfaces, drivers, etc.
    makefile: Optional[Path] = None
    top_module: Optional[str] = None
    test_module: Optional[str] = None


@dataclass
class FolderEvalResult:
    """Result of folder evaluation."""
    success: bool
    build_success: bool
    sim_success: bool
    tests_passed: int = 0
    tests_failed: int = 0
    tests_total: int = 0
    coverage: Dict[str, float] = field(default_factory=dict)
    errors: List[str] = field(default_factory=list)
    output: str = ""


def parse_verification_folder(folder_path: Path) -> VerificationFolder:
    """
    Parse a verification folder to identify its structure.
    
    Looks for:
    - .v/.sv files -> DUT or support
    - .py files -> testbenches or support
    - Makefile -> build configuration
    """
    folder = VerificationFolder(path=folder_path)
    
    if not folder_path.exists():
        raise ValueError(f"Folder does not exist: {folder_path}")
    
    for file in folder_path.iterdir():
        if file.is_file():
            suffix = file.suffix.lower()
            name = file.stem.lower()
            
            if suffix in ['.v', '.sv']:
                # Verilog/SystemVerilog files
                if 'tb' in name or 'test' in name:
                    folder.tb_files.append(file)
                else:
                    folder.dut_files.append(file)
                    
            elif suffix == '.py':
                # Python files
                if name.startswith('test_') or name.endswith('_test'):
                    folder.tb_files.append(file)
                else:
                    folder.support_files.append(file)
                    
            elif file.name.lower() == 'makefile':
                folder.makefile = file
    
    # Try to determine top module and test module
    if folder.makefile:
        makefile_content = folder.makefile.read_text()
        
        # Parse TOPLEVEL
        match = re.search(r'TOPLEVEL\s*[?:]?=\s*(\w+)', makefile_content)
        if match:
            folder.top_module = match.group(1)
        
        # Parse MODULE
        match = re.search(r'MODULE\s*[?:]?=\s*(\w+)', makefile_content)
        if match:
            folder.test_module = match.group(1)
    
    return folder


def create_work_directory(folder: VerificationFolder, 
                          work_dir: Path) -> Path:
    """
    Create a work directory with all necessary files.
    Copies files and generates Makefile if needed.
    """
    work_dir.mkdir(parents=True, exist_ok=True)
    
    # Copy all files
    for file in folder.dut_files + folder.tb_files + folder.support_files:
        shutil.copy(file, work_dir / file.name)
    
    # Copy or generate Makefile
    if folder.makefile:
        shutil.copy(folder.makefile, work_dir / "Makefile")
    else:
        # Generate Makefile
        generate_makefile(folder, work_dir)
    
    return work_dir


def generate_makefile(folder: VerificationFolder, work_dir: Path) -> Path:
    """Generate a Makefile for the verification folder."""
    
    # Determine DUT files
    verilog_sources = " ".join([f"$(PWD)/{f.name}" for f in folder.dut_files])
    
    # Determine top module (guess from first DUT file if not set)
    top_module = folder.top_module
    if not top_module and folder.dut_files:
        # Try to extract module name from first file
        content = folder.dut_files[0].read_text()
        match = re.search(r'module\s+(\w+)', content)
        if match:
            top_module = match.group(1)
    top_module = top_module or "top"
    
    # Determine test module
    test_module = folder.test_module
    if not test_module and folder.tb_files:
        # Use first Python test file
        for f in folder.tb_files:
            if f.suffix == '.py':
                test_module = f.stem
                break
    test_module = test_module or "test"
    
    makefile_content = f"""# Auto-generated Makefile for verification

SIM ?= verilator
TOPLEVEL_LANG ?= verilog

# DUT files
VERILOG_SOURCES = {verilog_sources}
TOPLEVEL = {top_module}
MODULE = {test_module}

# Verilator args
EXTRA_ARGS += --coverage --coverage-line --coverage-toggle
EXTRA_ARGS += -Wno-fatal
EXTRA_ARGS += --trace

# Include cocotb makefiles
include $(shell cocotb-config --makefiles)/Makefile.sim
"""
    
    makefile_path = work_dir / "Makefile"
    makefile_path.write_text(makefile_content)
    
    return makefile_path


def parse_test_results(output: str) -> Tuple[int, int, int]:
    """Parse test results from cocotb output."""
    # Look for summary line: TESTS=N PASS=N FAIL=N
    match = re.search(r'TESTS=(\d+)\s+PASS=(\d+)\s+FAIL=(\d+)', output)
    if match:
        total = int(match.group(1))
        passed = int(match.group(2))
        failed = int(match.group(3))
        return passed, failed, total
    return 0, 0, 0


def parse_coverage_data(work_dir: Path) -> Dict[str, float]:
    """Parse coverage data from Verilator output."""
    coverage = {
        "line": 0.0,
        "toggle": 0.0,
        "branch": 0.0,
    }
    
    cov_file = work_dir / "coverage.dat"
    if not cov_file.exists():
        return coverage
    
    try:
        content = cov_file.read_text()
        
        total_toggles = 0
        covered_toggles = 0
        
        for line in content.split('\n'):
            if not line.startswith('C '):
                continue
            
            try:
                parts = line.rsplit("'", 1)
                if len(parts) < 2:
                    continue
                
                count_str = parts[1].strip()
                count = int(count_str) if count_str.isdigit() else 0
                
                if ':0->1' in line or ':1->0' in line:
                    total_toggles += 1
                    if count > 0:
                        covered_toggles += 1
                        
            except (ValueError, IndexError):
                continue
        
        if total_toggles > 0:
            coverage["toggle"] = (covered_toggles / total_toggles) * 100
            coverage["line"] = coverage["toggle"]  # Approximation
            
    except Exception as e:
        print(f"Warning: Could not parse coverage: {e}")
    
    return coverage


def run_folder_evaluation(folder_path: Path,
                          config: BenchmarkConfig = None,
                          run_id: int = 1) -> FolderEvalResult:
    """
    Run evaluation on a verification folder.
    
    Steps:
    1. Parse folder structure
    2. Create work directory
    3. Run simulation
    4. Collect results and coverage
    """
    config = config or BenchmarkConfig()
    result = FolderEvalResult(success=False, build_success=False, sim_success=False)
    
    try:
        # Parse folder
        folder = parse_verification_folder(folder_path)
        
        if not folder.dut_files:
            result.errors.append("No DUT files found in folder")
            return result
        
        if not folder.tb_files:
            result.errors.append("No testbench files found in folder")
            return result
        
        # Create work directory
        work_dir = GENERATED_DIR / folder_path.name / f"run_{run_id}"
        create_work_directory(folder, work_dir)
        
        # Set up environment
        env = os.environ.copy()
        env['COCOTB_RESOLVE_X'] = 'ZEROS'
        
        # Run simulation
        print(f"  Running evaluation for {folder_path.name}...")
        
        proc = subprocess.run(
            ['make', '-C', str(work_dir)],
            capture_output=True,
            text=True,
            timeout=config.simulation_timeout_ms / 1000,
            env=env
        )
        
        result.output = proc.stdout + proc.stderr
        
        # Check for build errors
        if '%Error' in proc.stderr:
            result.build_success = False
            result.errors.append("Build failed - Verilator errors")
        else:
            result.build_success = True
            
            # Check for simulation
            if 'cocotb' in result.output.lower() or 'TESTS=' in result.output:
                result.sim_success = True
                
                # Parse test results
                passed, failed, total = parse_test_results(result.output)
                result.tests_passed = passed
                result.tests_failed = failed
                result.tests_total = total
                
                # Parse coverage
                result.coverage = parse_coverage_data(work_dir)
            else:
                result.sim_success = False
                result.errors.append("Simulation did not produce expected output")
        
        result.success = result.build_success and result.sim_success
        
    except subprocess.TimeoutExpired:
        result.errors.append("Simulation timed out")
    except Exception as e:
        result.errors.append(str(e))
    
    return result


class FolderEvaluator:
    """
    Evaluator for verification folders.
    """
    
    def __init__(self, config: BenchmarkConfig = None):
        self.config = config or BenchmarkConfig()
    
    def evaluate(self, folder_path: Path, num_runs: int = 1) -> List[FolderEvalResult]:
        """Evaluate a verification folder with multiple runs."""
        results = []
        
        for run_id in range(1, num_runs + 1):
            result = run_folder_evaluation(folder_path, self.config, run_id)
            results.append(result)
            
            # Print summary
            status = "✓" if result.success else "✗"
            print(f"    {status} Run {run_id}: {result.tests_passed}/{result.tests_total} tests passed")
            
            if result.coverage:
                avg_cov = sum(v for v in result.coverage.values() if v > 0)
                num_metrics = sum(1 for v in result.coverage.values() if v > 0)
                if num_metrics > 0:
                    print(f"       Coverage: {avg_cov/num_metrics:.1f}%")
        
        return results
    
    def evaluate_multiple(self, folder_paths: List[Path]) -> Dict[str, List[FolderEvalResult]]:
        """Evaluate multiple verification folders."""
        all_results = {}
        
        for folder_path in folder_paths:
            print(f"\nEvaluating: {folder_path.name}")
            results = self.evaluate(folder_path)
            all_results[folder_path.name] = results
        
        return all_results
    
    def generate_report(self, results: Dict[str, List[FolderEvalResult]]) -> str:
        """Generate a summary report."""
        report = []
        report.append("=" * 60)
        report.append("FOLDER EVALUATION REPORT")
        report.append("=" * 60)
        
        total_passed = 0
        total_failed = 0
        
        for folder_name, folder_results in results.items():
            report.append(f"\n{folder_name}:")
            
            for i, result in enumerate(folder_results, 1):
                status = "PASS" if result.success else "FAIL"
                report.append(f"  Run {i}: {status}")
                report.append(f"    Tests: {result.tests_passed}/{result.tests_total}")
                
                if result.coverage:
                    for metric, value in result.coverage.items():
                        if value > 0:
                            report.append(f"    {metric}: {value:.1f}%")
                
                if result.errors:
                    report.append(f"    Errors: {result.errors[:3]}")
                
                total_passed += result.tests_passed
                total_failed += result.tests_failed
        
        report.append("\n" + "=" * 60)
        report.append(f"TOTAL: {total_passed} passed, {total_failed} failed")
        report.append("=" * 60)
        
        return "\n".join(report)

