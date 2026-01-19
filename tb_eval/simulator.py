"""
Simulator for TB-Eval.

Handles compilation, simulation, and coverage collection using Verilator + cocotb.
Supports both single-file and multi-file verification projects.
"""

import os
import re
import shutil
import subprocess
from pathlib import Path
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

from .config import EvalConfig, VerificationProject, WORK_DIR


@dataclass
class SimulationResult:
    """Result of a simulation run."""
    
    # Build status
    build_success: bool = False
    build_errors: List[str] = field(default_factory=list)
    
    # Simulation status
    sim_success: bool = False
    sim_errors: List[str] = field(default_factory=list)
    sim_output: str = ""
    
    # Test results
    tests_passed: int = 0
    tests_failed: int = 0
    tests_total: int = 0
    test_details: Dict[str, bool] = field(default_factory=dict)
    
    # Coverage data
    line_coverage: float = 0.0
    toggle_coverage: float = 0.0
    branch_coverage: float = 0.0
    
    # Lint results
    lint_errors: int = 0
    lint_warnings: int = 0
    
    @property
    def success(self) -> bool:
        return self.build_success and self.sim_success
    
    @property
    def average_coverage(self) -> float:
        """Average of non-zero coverage metrics."""
        values = [v for v in [self.line_coverage, self.toggle_coverage, 
                              self.branch_coverage] if v > 0]
        return sum(values) / len(values) if values else 0.0


class Simulator:
    """Verilator + cocotb simulator."""
    
    def __init__(self, config: EvalConfig = None):
        self.config = config or EvalConfig()
        self._verify_dependencies()
    
    def _verify_dependencies(self):
        """Verify required tools are available."""
        # Check Verilator
        result = subprocess.run(['which', 'verilator'], capture_output=True, text=True)
        if result.returncode != 0:
            raise RuntimeError("Verilator not found. Install with: brew install verilator")
        
        # Check cocotb
        try:
            import cocotb
        except ImportError:
            raise RuntimeError("cocotb not found. Install with: pip install cocotb")
    
    def run(self, project: VerificationProject, run_id: int = 1) -> SimulationResult:
        """
        Run simulation for a verification project.
        
        Steps:
        1. Create work directory
        2. Copy/generate files
        3. Run simulation
        4. Collect coverage
        5. Run lint
        """
        result = SimulationResult()
        
        # Create work directory
        work_dir = WORK_DIR / project.name / f"run_{run_id}"
        work_dir.mkdir(parents=True, exist_ok=True)
        
        try:
            # Set up work directory
            self._setup_work_dir(project, work_dir)
            
            # Run simulation
            self._run_simulation(work_dir, result)
            
            # Parse coverage if simulation succeeded
            if result.sim_success:
                self._parse_coverage(work_dir, result)
            
            # Run lint
            if self.config.enable_lint:
                self._run_lint(project, result)
                
        except Exception as e:
            result.build_errors.append(str(e))
        
        finally:
            # Clean up if requested
            if not self.config.keep_work_dir and work_dir.exists():
                shutil.rmtree(work_dir, ignore_errors=True)
        
        return result
    
    def _setup_work_dir(self, project: VerificationProject, work_dir: Path):
        """Set up the work directory with all necessary files."""
        
        # Copy all project files
        for f in project.dut_files + project.tb_files + project.support_files:
            shutil.copy(f, work_dir / f.name)
        
        # Copy or generate Makefile
        if project.makefile and project.makefile.exists():
            shutil.copy(project.makefile, work_dir / "Makefile")
        else:
            self._generate_makefile(project, work_dir)
    
    def _generate_makefile(self, project: VerificationProject, work_dir: Path):
        """Generate a Makefile for the project."""
        
        # DUT sources
        verilog_sources = " ".join([f"$(PWD)/{f.name}" for f in project.dut_files])
        
        # Determine top module
        top_module = project.top_module
        if not top_module and project.dut_files:
            # Extract from first DUT file
            content = project.dut_files[0].read_text()
            match = re.search(r'module\s+(\w+)', content)
            if match:
                top_module = match.group(1)
        top_module = top_module or "top"
        
        # Determine test module
        test_module = project.test_module
        if not test_module and project.tb_files:
            for f in project.tb_files:
                if f.suffix == '.py' and f.stem.startswith('test_'):
                    test_module = f.stem
                    break
        test_module = test_module or "test"
        
        makefile = f"""# Auto-generated Makefile for {project.name}

SIM ?= verilator
TOPLEVEL_LANG ?= verilog

VERILOG_SOURCES = {verilog_sources}
TOPLEVEL = {top_module}
MODULE = {test_module}

# Coverage flags
EXTRA_ARGS += --coverage --coverage-line --coverage-toggle
EXTRA_ARGS += -Wno-fatal
EXTRA_ARGS += --trace

include $(shell cocotb-config --makefiles)/Makefile.sim
"""
        
        (work_dir / "Makefile").write_text(makefile)
    
    def _run_simulation(self, work_dir: Path, result: SimulationResult):
        """Run the cocotb simulation."""
        
        env = os.environ.copy()
        env['COCOTB_RESOLVE_X'] = 'ZEROS'
        
        if self.config.verbose:
            print(f"  Running simulation in {work_dir}...")
        
        try:
            proc = subprocess.run(
                ['make', '-C', str(work_dir)],
                capture_output=True,
                text=True,
                timeout=self.config.simulation_timeout_sec,
                env=env
            )
            
            result.sim_output = proc.stdout + proc.stderr
            
            # Check for Verilator errors (build failure)
            if '%Error' in proc.stderr:
                result.build_success = False
                result.build_errors = [l for l in proc.stderr.split('\n') 
                                       if '%Error' in l or 'error' in l.lower()]
            else:
                result.build_success = True
                
                # Check for cocotb output (simulation ran)
                if 'cocotb' in result.sim_output.lower() or 'TESTS=' in result.sim_output:
                    result.sim_success = True
                    self._parse_test_results(result)
                else:
                    result.sim_success = False
                    result.sim_errors.append("Simulation did not produce expected output")
                    
        except subprocess.TimeoutExpired:
            result.sim_errors.append(f"Simulation timed out after {self.config.simulation_timeout_sec}s")
        except Exception as e:
            result.sim_errors.append(str(e))
    
    def _parse_test_results(self, result: SimulationResult):
        """Parse test results from cocotb output."""
        
        # Look for summary: TESTS=N PASS=N FAIL=N
        match = re.search(r'TESTS=(\d+)\s+PASS=(\d+)\s+FAIL=(\d+)', result.sim_output)
        if match:
            result.tests_total = int(match.group(1))
            result.tests_passed = int(match.group(2))
            result.tests_failed = int(match.group(3))
        
        # Parse individual test results
        for line in result.sim_output.split('\n'):
            if 'passed' in line.lower():
                match = re.search(r'(\w+)\s+passed', line, re.IGNORECASE)
                if match:
                    result.test_details[match.group(1)] = True
            elif 'failed' in line.lower():
                match = re.search(r'(\w+)\s+failed', line, re.IGNORECASE)
                if match:
                    result.test_details[match.group(1)] = False
    
    def _parse_coverage(self, work_dir: Path, result: SimulationResult):
        """Parse Verilator coverage data."""
        
        # Find coverage.dat file
        cov_file = work_dir / "coverage.dat"
        if not cov_file.exists():
            for f in work_dir.glob("**/coverage.dat"):
                cov_file = f
                break
        
        if not cov_file.exists():
            return
        
        try:
            content = cov_file.read_text()
            
            # Count coverage points
            line_total, line_covered = 0, 0
            toggle_total, toggle_covered = 0, 0
            branch_total, branch_covered = 0, 0
            
            for line in content.split('\n'):
                if not line.startswith('C '):
                    continue
                
                try:
                    # Format: C 'metadata' count
                    parts = line.rsplit("'", 1)
                    if len(parts) < 2:
                        continue
                    
                    count = int(parts[1].strip()) if parts[1].strip().isdigit() else 0
                    metadata = parts[0]
                    
                    # Classify coverage type
                    if ':0->1' in metadata or ':1->0' in metadata:
                        toggle_total += 1
                        if count > 0:
                            toggle_covered += 1
                    elif 'v_line' in metadata or 'tline' in metadata:
                        line_total += 1
                        if count > 0:
                            line_covered += 1
                    elif 'v_branch' in metadata or 'tbranch' in metadata:
                        branch_total += 1
                        if count > 0:
                            branch_covered += 1
                            
                except (ValueError, IndexError):
                    continue
            
            # Calculate percentages
            if toggle_total > 0:
                result.toggle_coverage = (toggle_covered / toggle_total) * 100
            if line_total > 0:
                result.line_coverage = (line_covered / line_total) * 100
            if branch_total > 0:
                result.branch_coverage = (branch_covered / branch_total) * 100
            
            # Use toggle as approximation for line if line not available
            if result.line_coverage == 0 and result.toggle_coverage > 0:
                result.line_coverage = result.toggle_coverage
                
        except Exception as e:
            if self.config.verbose:
                print(f"  Warning: Could not parse coverage: {e}")
    
    def _run_lint(self, project: VerificationProject, result: SimulationResult):
        """Run linting on testbench files."""
        
        for tb_file in project.tb_files:
            if tb_file.suffix != '.py':
                continue
            
            try:
                code = tb_file.read_text()
                
                # Basic Python syntax check
                try:
                    compile(code, str(tb_file), 'exec')
                except SyntaxError:
                    result.lint_errors += 1
                
                # Check for common issues
                for line in code.split('\n'):
                    if re.search(r'\bexcept\s*:', line):
                        result.lint_warnings += 1
                    if re.search(r'\bprint\s*\(', line) and 'cocotb' not in line.lower():
                        result.lint_warnings += 1
                        
            except Exception:
                pass


def parse_verification_project(folder_path: Path) -> VerificationProject:
    """
    Parse a folder to create a VerificationProject.
    
    Identifies:
    - .v/.sv files -> DUT files
    - test_*.py files -> Testbench files  
    - Other .py files -> Support files
    - Makefile -> Build configuration
    """
    
    if not folder_path.exists():
        raise ValueError(f"Folder does not exist: {folder_path}")
    
    project = VerificationProject(path=folder_path)
    
    for file in folder_path.iterdir():
        if not file.is_file():
            continue
        
        suffix = file.suffix.lower()
        name = file.stem.lower()
        
        if suffix in ['.v', '.sv']:
            # Verilog/SystemVerilog -> DUT (unless it's a testbench)
            if 'tb' in name or 'test' in name:
                continue  # Skip Verilog testbenches
            project.dut_files.append(file)
            
        elif suffix == '.py':
            # Python files
            if name.startswith('test_') or name.endswith('_test'):
                project.tb_files.append(file)
            elif name != '__pycache__':
                project.support_files.append(file)
                
        elif file.name.lower() == 'makefile':
            project.makefile = file
    
    # Parse Makefile for module info
    if project.makefile:
        content = project.makefile.read_text()
        
        match = re.search(r'TOPLEVEL\s*[?:]?=\s*(\w+)', content)
        if match:
            project.top_module = match.group(1)
        
        match = re.search(r'MODULE\s*[?:]?=\s*(\w+)', content)
        if match:
            project.test_module = match.group(1)
    
    return project
