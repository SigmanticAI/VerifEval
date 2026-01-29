"""
Questa Simulator Module.

Provides UVM/SystemVerilog simulation capabilities using Questa.

Workflow:
    1. vlib - Create work library
    2. vlog - Compile SystemVerilog/Verilog sources with UVM
    3. vopt - Optimize design (optional, improves performance)
    4. vsim - Run simulation with specified UVM test
    5. vcover - Extract coverage data

Example Usage:
    from questa.simulator import QuestaSimulator
    from questa.config import set_license
    
    # Configure license
    set_license("1717@license.company.com")
    
    # Create simulator
    sim = QuestaSimulator()
    
    # Run simulation
    result = sim.run_uvm_test(
        source_files=["rtl/dut.sv", "tb/tb_top.sv"],
        top_module="tb_top",
        uvm_test="base_test"
    )
    
    print(f"Pass: {result.passed}")
    print(f"Coverage: {result.coverage_percent}%")
"""

import os
import re
import shutil
import subprocess
import tempfile
from pathlib import Path
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any, Tuple

from .config import QuestaConfig, get_config


@dataclass
class SimulationResult:
    """Result of a Questa simulation run."""
    
    # Status
    compile_success: bool = False
    simulation_success: bool = False
    passed: bool = False
    
    # Compilation info
    compile_errors: List[str] = field(default_factory=list)
    compile_warnings: List[str] = field(default_factory=list)
    
    # Simulation info
    simulation_errors: List[str] = field(default_factory=list)
    simulation_warnings: List[str] = field(default_factory=list)
    simulation_log: str = ""
    
    # Test results
    uvm_test_name: str = ""
    test_passed: bool = False
    test_errors: int = 0
    test_warnings: int = 0
    test_fatals: int = 0
    
    # Coverage data (percentages)
    line_coverage: float = 0.0
    branch_coverage: float = 0.0
    toggle_coverage: float = 0.0
    fsm_coverage: float = 0.0
    assertion_coverage: float = 0.0
    functional_coverage: float = 0.0
    
    # Timing
    compile_time_sec: float = 0.0
    simulation_time_sec: float = 0.0
    
    # Output files
    coverage_db: Optional[Path] = None
    waveform_file: Optional[Path] = None
    log_file: Optional[Path] = None
    
    @property
    def coverage_percent(self) -> float:
        """Average coverage across all metrics."""
        metrics = [
            self.line_coverage,
            self.branch_coverage,
            self.toggle_coverage,
            self.functional_coverage,
        ]
        non_zero = [m for m in metrics if m > 0]
        return sum(non_zero) / len(non_zero) if non_zero else 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            'compile_success': self.compile_success,
            'simulation_success': self.simulation_success,
            'passed': self.passed,
            'uvm_test_name': self.uvm_test_name,
            'test_passed': self.test_passed,
            'test_errors': self.test_errors,
            'test_warnings': self.test_warnings,
            'test_fatals': self.test_fatals,
            'coverage': {
                'line': round(self.line_coverage, 2),
                'branch': round(self.branch_coverage, 2),
                'toggle': round(self.toggle_coverage, 2),
                'fsm': round(self.fsm_coverage, 2),
                'assertion': round(self.assertion_coverage, 2),
                'functional': round(self.functional_coverage, 2),
                'average': round(self.coverage_percent, 2),
            },
            'timing': {
                'compile_sec': round(self.compile_time_sec, 2),
                'simulation_sec': round(self.simulation_time_sec, 2),
            },
            'errors': self.compile_errors + self.simulation_errors,
            'warnings': self.compile_warnings + self.simulation_warnings,
        }


class QuestaSimulator:
    """
    Questa UVM/SystemVerilog Simulator.
    
    Provides methods to compile and simulate UVM testbenches using Questa.
    
    Attributes:
        config: Questa configuration instance
    """
    
    def __init__(self, config: QuestaConfig = None):
        """
        Initialize Questa simulator.
        
        Args:
            config: Optional configuration. Uses global config if not provided.
        """
        self.config = config or get_config()
    
    def validate_environment(self) -> Tuple[bool, List[str]]:
        """
        Validate that Questa environment is properly configured.
        
        Returns:
            Tuple of (is_valid, list_of_errors)
        """
        errors = self.config.validate()
        return len(errors) == 0, errors
    
    def create_library(self, work_dir: Path = None) -> bool:
        """
        Create Questa work library.
        
        Args:
            work_dir: Path to work directory
            
        Returns:
            True if successful
        """
        work_dir = work_dir or self.config.work_dir
        work_dir = Path(work_dir)
        
        # Remove existing library
        if work_dir.exists():
            shutil.rmtree(work_dir)
        
        try:
            result = subprocess.run(
                [self.config.vlib_path, str(work_dir)],
                capture_output=True,
                text=True,
                timeout=30,
                env=self.config.get_env()
            )
            return result.returncode == 0
        except (subprocess.TimeoutExpired, FileNotFoundError):
            return False
    
    def compile(self, 
                source_files: List[Path],
                work_dir: Path = None,
                include_dirs: List[Path] = None,
                defines: Dict[str, str] = None,
                enable_coverage: bool = True) -> Tuple[bool, List[str], List[str]]:
        """
        Compile SystemVerilog/Verilog sources with vlog.
        
        Args:
            source_files: List of source file paths
            work_dir: Work library directory
            include_dirs: Include directories for `include
            defines: Preprocessor defines
            enable_coverage: Enable coverage instrumentation
            
        Returns:
            Tuple of (success, errors, warnings)
        """
        work_dir = work_dir or self.config.work_dir
        include_dirs = include_dirs or []
        defines = defines or {}
        
        # Build vlog command
        cmd = [
            self.config.vlog_path,
            '-work', str(work_dir),
            '-sv',                      # SystemVerilog mode
            '+acc',                     # Full access for debugging
            '-timescale', '1ns/1ps',    # Default timescale
        ]
        
        # UVM support
        cmd.extend([
            '-L', 'mtiAvm',              # UVM library
            '-L', 'mtiOvm',              # OVM library (compatibility)
            '-L', 'mtiUvm',              # UVM library
            '-L', 'mtiUPF',              # Unified Power Format
            '+define+UVM_NO_DPI',        # Disable DPI if issues
        ])
        
        # Coverage options
        if enable_coverage:
            cmd.extend([
                '+cover=bcestf',         # Branch, condition, expression, statement, toggle, FSM
                '-coveropt', '3',        # Detailed coverage
            ])
        
        # Include directories
        for inc_dir in include_dirs:
            cmd.extend(['+incdir+' + str(inc_dir)])
        
        # Defines
        for name, value in defines.items():
            if value:
                cmd.append(f'+define+{name}={value}')
            else:
                cmd.append(f'+define+{name}')
        
        # Extra arguments from config
        cmd.extend(self.config.extra_vlog_args)
        
        # Source files
        cmd.extend([str(f) for f in source_files])
        
        # Run compilation
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=self.config.timeout_sec,
                env=self.config.get_env()
            )
            
            output = result.stdout + result.stderr
            
            # Parse errors and warnings
            errors = re.findall(r'\*\* Error[^*]+', output)
            warnings = re.findall(r'\*\* Warning[^*]+', output)
            
            success = result.returncode == 0 and not errors
            return success, errors, warnings
            
        except subprocess.TimeoutExpired:
            return False, ["Compilation timed out"], []
        except FileNotFoundError:
            return False, [f"vlog not found: {self.config.vlog_path}"], []
    
    def optimize(self,
                 top_module: str,
                 work_dir: Path = None,
                 opt_name: str = None) -> Tuple[bool, str]:
        """
        Optimize design with vopt (optional but improves simulation speed).
        
        Args:
            top_module: Top-level module name
            work_dir: Work library directory
            opt_name: Name for optimized design
            
        Returns:
            Tuple of (success, optimized_name)
        """
        work_dir = work_dir or self.config.work_dir
        opt_name = opt_name or f"{top_module}_opt"
        
        cmd = [
            self.config.vopt_path,
            '-work', str(work_dir),
            '+acc',                      # Full access
            '-o', opt_name,              # Output name
            top_module,                  # Input module
        ]
        
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=self.config.timeout_sec,
                env=self.config.get_env()
            )
            
            success = result.returncode == 0
            return success, opt_name if success else ""
            
        except (subprocess.TimeoutExpired, FileNotFoundError):
            return False, ""
    
    def simulate(self,
                 top_module: str,
                 work_dir: Path = None,
                 uvm_test: str = None,
                 seed: int = None,
                 run_time: str = None,
                 coverage_db: Path = None,
                 waveform_file: Path = None,
                 plusargs: Dict[str, str] = None,
                 log_file: Path = None) -> SimulationResult:
        """
        Run simulation with vsim.
        
        Args:
            top_module: Top-level module name
            work_dir: Work library directory
            uvm_test: UVM test name to run
            seed: Random seed for simulation
            run_time: Simulation run time (e.g., "1ms", "-all")
            coverage_db: Path to coverage database output
            waveform_file: Path to waveform file output
            plusargs: Additional plusargs for simulation
            log_file: Path to simulation log file
            
        Returns:
            SimulationResult with test outcome and coverage
        """
        result = SimulationResult()
        result.uvm_test_name = uvm_test or ""
        
        work_dir = work_dir or self.config.work_dir
        coverage_db = coverage_db or self.config.coverage_db
        plusargs = plusargs or {}
        
        # Build vsim command
        cmd = [
            self.config.vsim_path,
            '-work', str(work_dir),
            '-c',                        # Command-line mode (no GUI)
            '-onfinish', 'stop',         # Stop on finish
        ]
        
        # Coverage
        cmd.extend([
            '-coverage',                 # Enable coverage collection
            '-coverstore', str(coverage_db.parent if coverage_db else '.'),
        ])
        
        # Waveform
        if self.config.generate_waves and waveform_file:
            cmd.extend([
                '-wlf', str(waveform_file),
            ])
        
        # Log file
        if log_file:
            cmd.extend(['-l', str(log_file)])
            result.log_file = log_file
        
        # UVM test selection
        if uvm_test:
            plusargs['UVM_TESTNAME'] = uvm_test
        
        # UVM verbosity
        if 'UVM_VERBOSITY' not in plusargs:
            plusargs['UVM_VERBOSITY'] = 'UVM_MEDIUM'
        
        # Seed
        if seed is not None:
            cmd.extend(['-sv_seed', str(seed)])
        
        # Add plusargs
        for name, value in plusargs.items():
            if value:
                cmd.append(f'+{name}={value}')
            else:
                cmd.append(f'+{name}')
        
        # Extra arguments from config
        cmd.extend(self.config.extra_vsim_args)
        
        # Top module
        cmd.append(top_module)
        
        # Run command (run simulation then quit)
        run_time = run_time or "-all"
        do_cmds = f"coverage save -onexit {coverage_db}; run {run_time}; quit -f"
        cmd.extend(['-do', do_cmds])
        
        if self.config.verbose:
            print(f"Running: {' '.join(cmd)}")
        
        # Execute simulation
        import time
        start_time = time.time()
        
        try:
            proc = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=self.config.timeout_sec,
                env=self.config.get_env()
            )
            
            result.simulation_time_sec = time.time() - start_time
            result.simulation_log = proc.stdout + proc.stderr
            
            # Parse results
            self._parse_simulation_output(result)
            
            # Get coverage if available
            if coverage_db and Path(coverage_db).exists():
                result.coverage_db = coverage_db
                self._extract_coverage(coverage_db, result)
            
            result.simulation_success = proc.returncode == 0
            result.passed = result.simulation_success and result.test_passed
            
        except subprocess.TimeoutExpired:
            result.simulation_errors.append("Simulation timed out")
        except FileNotFoundError:
            result.simulation_errors.append(f"vsim not found: {self.config.vsim_path}")
        
        return result
    
    def _parse_simulation_output(self, result: SimulationResult):
        """Parse simulation output for UVM test results."""
        log = result.simulation_log
        
        # Parse UVM test result
        if "UVM_FATAL" in log:
            result.test_fatals = len(re.findall(r'UVM_FATAL', log))
            result.test_passed = False
        elif "TEST PASSED" in log.upper() or "UVM_INFO.*TEST PASSED" in log:
            result.test_passed = True
        elif "TEST FAILED" in log.upper():
            result.test_passed = False
        else:
            # Check for no fatal/error messages
            result.test_passed = result.test_fatals == 0 and "Error" not in log
        
        # Count UVM messages
        result.test_errors = len(re.findall(r'UVM_ERROR', log))
        result.test_warnings = len(re.findall(r'UVM_WARNING', log))
        
        # Parse errors and warnings from simulation
        result.simulation_errors = re.findall(r'\*\* Error[^*]*', log)
        result.simulation_warnings = re.findall(r'\*\* Warning[^*]*', log)
    
    def _extract_coverage(self, coverage_db: Path, result: SimulationResult):
        """Extract coverage percentages from UCDB using vcover."""
        try:
            # Run vcover report
            proc = subprocess.run(
                [
                    self.config.vcover_path,
                    'report', '-summary',
                    str(coverage_db)
                ],
                capture_output=True,
                text=True,
                timeout=60,
                env=self.config.get_env()
            )
            
            output = proc.stdout + proc.stderr
            
            # Parse coverage percentages
            # Line coverage
            match = re.search(r'Stmts\s+\d+\s+\d+\s+([\d.]+)%', output)
            if match:
                result.line_coverage = float(match.group(1))
            
            # Branch coverage
            match = re.search(r'Branches\s+\d+\s+\d+\s+([\d.]+)%', output)
            if match:
                result.branch_coverage = float(match.group(1))
            
            # Toggle coverage
            match = re.search(r'Toggles\s+\d+\s+\d+\s+([\d.]+)%', output)
            if match:
                result.toggle_coverage = float(match.group(1))
            
            # FSM coverage
            match = re.search(r'FSM States\s+\d+\s+\d+\s+([\d.]+)%', output)
            if match:
                result.fsm_coverage = float(match.group(1))
            
            # Assertion coverage
            match = re.search(r'Assertions\s+\d+\s+\d+\s+([\d.]+)%', output)
            if match:
                result.assertion_coverage = float(match.group(1))
            
            # Functional coverage (covergroups)
            match = re.search(r'Covergroups\s+[\d.]+%\s+\d+\s+\d+\s+\d+\s+([\d.]+)%', output)
            if match:
                result.functional_coverage = float(match.group(1))
            
        except (subprocess.TimeoutExpired, FileNotFoundError):
            pass
    
    def run_uvm_test(self,
                     source_files: List[Path],
                     top_module: str,
                     uvm_test: str,
                     work_dir: Path = None,
                     include_dirs: List[Path] = None,
                     defines: Dict[str, str] = None,
                     seed: int = None,
                     cleanup: bool = True) -> SimulationResult:
        """
        Complete flow: compile and run a UVM test.
        
        This is the main entry point for running UVM simulations.
        
        Args:
            source_files: List of source files (RTL + testbench)
            top_module: Top-level module name
            uvm_test: Name of UVM test to run
            work_dir: Working directory (auto-created if None)
            include_dirs: Include directories
            defines: Preprocessor defines
            seed: Random seed
            cleanup: Remove work directory after simulation
            
        Returns:
            SimulationResult with test outcome and coverage
        """
        import time
        
        # Setup work directory
        if work_dir is None:
            work_dir = Path(tempfile.mkdtemp(prefix="questa_"))
        else:
            work_dir = Path(work_dir)
            work_dir.mkdir(parents=True, exist_ok=True)
        
        result = SimulationResult()
        result.uvm_test_name = uvm_test
        
        try:
            # Step 1: Create library
            if not self.create_library(work_dir):
                result.compile_errors.append("Failed to create work library")
                return result
            
            # Step 2: Compile sources
            start_time = time.time()
            compile_success, errors, warnings = self.compile(
                source_files=source_files,
                work_dir=work_dir,
                include_dirs=include_dirs,
                defines=defines
            )
            result.compile_time_sec = time.time() - start_time
            result.compile_success = compile_success
            result.compile_errors = errors
            result.compile_warnings = warnings
            
            if not compile_success:
                return result
            
            # Step 3: Run simulation
            coverage_db = work_dir / "coverage.ucdb"
            waveform_file = work_dir / "waves.wlf" if self.config.generate_waves else None
            log_file = work_dir / "simulation.log"
            
            sim_result = self.simulate(
                top_module=top_module,
                work_dir=work_dir,
                uvm_test=uvm_test,
                seed=seed,
                coverage_db=coverage_db,
                waveform_file=waveform_file,
                log_file=log_file
            )
            
            # Copy simulation results
            result.simulation_success = sim_result.simulation_success
            result.passed = sim_result.passed
            result.test_passed = sim_result.test_passed
            result.test_errors = sim_result.test_errors
            result.test_warnings = sim_result.test_warnings
            result.test_fatals = sim_result.test_fatals
            result.simulation_errors = sim_result.simulation_errors
            result.simulation_warnings = sim_result.simulation_warnings
            result.simulation_log = sim_result.simulation_log
            result.simulation_time_sec = sim_result.simulation_time_sec
            
            # Coverage
            result.line_coverage = sim_result.line_coverage
            result.branch_coverage = sim_result.branch_coverage
            result.toggle_coverage = sim_result.toggle_coverage
            result.fsm_coverage = sim_result.fsm_coverage
            result.assertion_coverage = sim_result.assertion_coverage
            result.functional_coverage = sim_result.functional_coverage
            result.coverage_db = sim_result.coverage_db
            
            # Copy files if we want to keep them
            if not cleanup:
                result.waveform_file = waveform_file
                result.log_file = log_file
            
        finally:
            if cleanup and work_dir.exists():
                shutil.rmtree(work_dir, ignore_errors=True)
        
        return result
    
    def run_tests(self,
                  source_files: List[Path],
                  top_module: str,
                  uvm_tests: List[str],
                  **kwargs) -> List[SimulationResult]:
        """
        Run multiple UVM tests.
        
        Args:
            source_files: List of source files
            top_module: Top-level module name
            uvm_tests: List of UVM test names to run
            **kwargs: Additional arguments passed to run_uvm_test
            
        Returns:
            List of SimulationResult for each test
        """
        results = []
        
        # Compile once
        work_dir = Path(tempfile.mkdtemp(prefix="questa_"))
        
        try:
            if not self.create_library(work_dir):
                return results
            
            success, errors, warnings = self.compile(
                source_files=source_files,
                work_dir=work_dir,
                include_dirs=kwargs.get('include_dirs'),
                defines=kwargs.get('defines')
            )
            
            if not success:
                # Return failed result for each test
                for test in uvm_tests:
                    result = SimulationResult()
                    result.uvm_test_name = test
                    result.compile_errors = errors
                    results.append(result)
                return results
            
            # Run each test
            for test in uvm_tests:
                coverage_db = work_dir / f"coverage_{test}.ucdb"
                log_file = work_dir / f"{test}.log"
                
                result = self.simulate(
                    top_module=top_module,
                    work_dir=work_dir,
                    uvm_test=test,
                    coverage_db=coverage_db,
                    log_file=log_file,
                    seed=kwargs.get('seed')
                )
                result.compile_success = True
                results.append(result)
        
        finally:
            shutil.rmtree(work_dir, ignore_errors=True)
        
        return results

