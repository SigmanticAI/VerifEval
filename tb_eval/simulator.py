"""
Simulation runner using Verilator + cocotb.

Handles compilation, simulation, and coverage collection.
"""

import os
import subprocess
import shutil
from pathlib import Path
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple
import json
import re

from .config import DesignConfig, BenchmarkConfig, DUTS_DIR, GENERATED_DIR, RESULTS_DIR


@dataclass
class SimulationResult:
    """Result of a simulation run."""
    success: bool
    build_success: bool
    sim_success: bool
    build_errors: List[str] = field(default_factory=list)
    sim_errors: List[str] = field(default_factory=list)
    sim_output: str = ""
    test_results: Dict[str, bool] = field(default_factory=dict)
    coverage_data: Optional[Dict] = None
    lint_errors: int = 0
    lint_warnings: int = 0


class VerilatorSimulator:
    """Verilator + cocotb simulator."""
    
    def __init__(self, config: BenchmarkConfig = None):
        self.config = config or BenchmarkConfig()
        self._check_dependencies()
    
    def _check_dependencies(self):
        """Check that required tools are available."""
        # Check Verilator
        result = subprocess.run(['which', 'verilator'], capture_output=True, text=True)
        if result.returncode != 0:
            raise RuntimeError("Verilator not found. Please install Verilator.")
        
        # Check cocotb is importable
        try:
            import cocotb
        except ImportError:
            raise RuntimeError("cocotb not found. Please install: pip install cocotb")
    
    def _create_makefile(self, design: DesignConfig, work_dir: Path, 
                         tb_file: Path) -> Path:
        """Create a Makefile for cocotb + Verilator simulation."""
        
        dut_path = (DUTS_DIR / design.name / design.dut_file).resolve()
        
        # Determine top-level signals for cocotb
        toplevel = design.module_name
        tb_module = tb_file.stem  # Get module name from file (without .py)
        
        makefile_content = f"""# Cocotb Makefile for {design.name}

# Simulator
SIM ?= verilator
TOPLEVEL_LANG ?= verilog

# DUT (absolute path)
VERILOG_SOURCES = {dut_path}
TOPLEVEL = {toplevel}
MODULE = {tb_module}

# Verilator extra args for coverage
EXTRA_ARGS += --coverage --coverage-line --coverage-toggle
EXTRA_ARGS += -Wno-fatal
EXTRA_ARGS += --trace

# Include cocotb makefiles
include $(shell cocotb-config --makefiles)/Makefile.sim
"""
        
        makefile_path = work_dir / "Makefile"
        makefile_path.write_text(makefile_content)
        
        return makefile_path
    
    def _run_lint(self, design: DesignConfig, tb_file: Path) -> Tuple[int, int]:
        """
        Run linting on the testbench.
        
        Uses Python's built-in ast and pylint if available.
        Returns (errors, warnings).
        """
        errors = 0
        warnings = 0
        
        # Basic Python syntax check
        code = tb_file.read_text()
        try:
            compile(code, str(tb_file), 'exec')
        except SyntaxError as e:
            errors += 1
        
        # Check for common issues
        lines = code.split('\n')
        for i, line in enumerate(lines, 1):
            # Check for bare except
            if re.search(r'\bexcept\s*:', line):
                warnings += 1
            # Check for print statements without logging
            if re.search(r'\bprint\s*\(', line) and 'cocotb' not in line.lower():
                warnings += 1
            # Check for hardcoded delays without comments
            if re.search(r'Timer\s*\(\s*\d+', line) and '#' not in line:
                warnings += 1
        
        # Try pylint if available
        try:
            result = subprocess.run(
                ['python', '-m', 'pylint', '--errors-only', str(tb_file)],
                capture_output=True,
                text=True,
                timeout=30
            )
            # Count pylint errors
            for line in result.stdout.split('\n'):
                if ': E' in line:
                    errors += 1
                elif ': W' in line:
                    warnings += 1
        except (subprocess.TimeoutExpired, FileNotFoundError):
            pass  # pylint not available or timed out
        
        return errors, warnings
    
    def _parse_coverage(self, work_dir: Path) -> Optional[Dict[str, float]]:
        """Parse Verilator coverage data."""
        
        coverage = {
            "line": 0.0,
            "toggle": 0.0,
            "branch": 0.0,
            "fsm": 0.0,
            "group": 0.0,
        }
        
        # Look for coverage.dat file - Verilator puts it in parent of sim_build
        cov_file = work_dir / "coverage.dat"
        if not cov_file.exists():
            cov_file = work_dir.parent / "coverage.dat"
        if not cov_file.exists():
            # Try finding any coverage.dat file
            dat_files = list(work_dir.glob("**/coverage.dat"))
            if dat_files:
                cov_file = dat_files[0]
            else:
                return None
        
        # Parse Verilator coverage format
        # Format: C 'attributes' count
        try:
            content = cov_file.read_text()
            
            total_toggles = 0
            covered_toggles = 0
            total_lines = 0
            covered_lines = 0
            total_branches = 0
            covered_branches = 0
            
            for line in content.split('\n'):
                if not line.startswith('C '):
                    continue
                
                # Parse the coverage line
                # Format: C 'metadata' count
                try:
                    # Extract the count (last part after the quote)
                    parts = line.rsplit("'", 1)
                    if len(parts) < 2:
                        continue
                    
                    count_str = parts[1].strip()
                    count = int(count_str) if count_str.isdigit() else 0
                    
                    metadata = parts[0]
                    
                    # Determine coverage type from metadata
                    if 'ttoggle' in metadata or 'v_toggle' in metadata:
                        # Toggle coverage
                        total_toggles += 1
                        if count > 0:
                            covered_toggles += 1
                    elif 'tline' in metadata or 'v_line' in metadata:
                        # Line coverage
                        total_lines += 1
                        if count > 0:
                            covered_lines += 1
                    elif 'tbranch' in metadata or 'v_branch' in metadata:
                        # Branch coverage
                        total_branches += 1
                        if count > 0:
                            covered_branches += 1
                    else:
                        # Default to toggle for this format
                        if ':0->1' in metadata or ':1->0' in metadata:
                            total_toggles += 1
                            if count > 0:
                                covered_toggles += 1
                        
                except (ValueError, IndexError):
                    continue
            
            # Calculate percentages
            if total_toggles > 0:
                coverage["toggle"] = (covered_toggles / total_toggles) * 100
            if total_lines > 0:
                coverage["line"] = (covered_lines / total_lines) * 100
            if total_branches > 0:
                coverage["branch"] = (covered_branches / total_branches) * 100
            
            # For line coverage, if we don't have specific line data,
            # use toggle as an approximation (all signals exercised = good coverage)
            if coverage["line"] == 0.0 and coverage["toggle"] > 0:
                coverage["line"] = coverage["toggle"]
                
        except Exception as e:
            print(f"Warning: Could not parse coverage data: {e}")
            return None
        
        return coverage
    
    def _parse_test_results(self, output: str) -> Dict[str, bool]:
        """Parse test results from cocotb output."""
        results = {}
        
        # Look for test pass/fail lines
        for line in output.split('\n'):
            # cocotb format: "test_name passed" or "test_name failed"
            if 'passed' in line.lower():
                match = re.search(r'(\w+)\s+passed', line, re.IGNORECASE)
                if match:
                    results[match.group(1)] = True
            elif 'failed' in line.lower():
                match = re.search(r'(\w+)\s+failed', line, re.IGNORECASE)
                if match:
                    results[match.group(1)] = False
        
        return results
    
    def run_simulation(self, design: DesignConfig, 
                       tb_file: Path,
                       run_id: int = 1) -> SimulationResult:
        """
        Run simulation for a design with given testbench.
        
        Steps:
        1. Create work directory
        2. Generate Makefile
        3. Run cocotb simulation
        4. Collect coverage data
        5. Run linting
        """
        
        result = SimulationResult(
            success=False,
            build_success=False,
            sim_success=False
        )
        
        # Create work directory
        work_dir = GENERATED_DIR / design.name / f"run_{run_id}" / "sim"
        work_dir.mkdir(parents=True, exist_ok=True)
        
        # Copy testbench to work directory
        dest_tb = work_dir / f"test_{design.name}.py"
        shutil.copy(tb_file, dest_tb)
        
        # Create Makefile
        self._create_makefile(design, work_dir, dest_tb)
        
        # Set up environment
        env = os.environ.copy()
        env['COCOTB_RESOLVE_X'] = 'ZEROS'  # Handle X values
        
        # Run simulation
        print(f"    Running simulation for {design.name} (run {run_id})...")
        
        try:
            proc = subprocess.run(
                ['make', '-C', str(work_dir)],
                capture_output=True,
                text=True,
                timeout=self.config.simulation_timeout_ms / 1000,
                env=env
            )
            
            result.sim_output = proc.stdout + proc.stderr
            
            # Check for compilation/build errors (Verilator errors)
            if '%Error' in proc.stderr or 'verilator' in proc.stderr.lower() and 'error' in proc.stderr.lower():
                result.build_success = False
                result.build_errors = [l for l in proc.stderr.split('\n') if 'error' in l.lower()]
            else:
                # Build was successful
                result.build_success = True
                
                # Check if simulation actually ran (look for cocotb output)
                if 'cocotb' in result.sim_output.lower() or 'TESTS=' in result.sim_output:
                    result.sim_success = True
                    
                    # Parse test results from output
                    result.test_results = self._parse_test_results(result.sim_output)
                    
                    # Note: Test failures don't mean simulation failed
                    # Simulation success means it ran, test results are separate
                else:
                    result.sim_success = False
                    result.sim_errors = ["Simulation did not produce expected output"]
            
            # Parse coverage if simulation succeeded
            if result.sim_success:
                result.coverage_data = self._parse_coverage(work_dir)
            
        except subprocess.TimeoutExpired:
            result.sim_errors = ["Simulation timed out"]
        except Exception as e:
            result.sim_errors = [str(e)]
        
        # Run linting regardless of simulation success
        result.lint_errors, result.lint_warnings = self._run_lint(design, tb_file)
        
        # Overall success
        result.success = result.build_success and result.sim_success
        
        return result


def run_verilator_lint_only(design: DesignConfig) -> Tuple[int, int]:
    """Run Verilator lint only on DUT."""
    
    dut_path = DUTS_DIR / design.name / design.dut_file
    
    errors = 0
    warnings = 0
    
    try:
        result = subprocess.run(
            ['verilator', '--lint-only', '-Wall', str(dut_path)],
            capture_output=True,
            text=True,
            timeout=30
        )
        
        for line in result.stderr.split('\n'):
            if '%Error' in line:
                errors += 1
            elif '%Warning' in line:
                warnings += 1
                
    except Exception as e:
        print(f"Warning: Verilator lint failed: {e}")
    
    return errors, warnings

