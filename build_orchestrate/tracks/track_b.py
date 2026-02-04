"""
Track B: VUnit/HDL/UVM Handler
==============================

Handles HDL-based testbenches with VUnit orchestration:
- VUnit native testbenches
- SystemVerilog testbenches
- VHDL testbenches
- UVM-SV testbenches (with Questa)

Build Flow:
1. Detect/Generate VUnit run.py
2. Configure simulator (Verilator, GHDL, or Questa)
3. VUnit compilation
4. VUnit test discovery
5. Execution via VUnit

Author: TB Eval Team
Version: 0.1.0
"""

import os
import sys
import re
import subprocess
from pathlib import Path
from typing import Optional, List, Dict, Any, Tuple
from datetime import datetime

from .base import (
    BaseTrack,
    TrackCapabilities,
    TrackBuildResult,
    ExecutionMode,
)
from ..models import (
    BuildStatus,
    CompilationResult,
    CompilationError,
    LibraryCompilationResult,
    TestDiscoveryResult,
    TestCase,
    TestStatus,
    CoverageConfig,
    CoverageType,
    SimulatorType,
    QuestaConfig,
    VerilatorConfig,
    GHDLConfig,
)
from ..discovery.vunit_discovery import VUnitTestDiscovery
from ..discovery.uvm_discovery import UVMTestDiscovery
from ..project.detector import VUnitProjectDetector
from ..project.generator import VUnitProjectGenerator


class HDLTrack(BaseTrack):
    """
    Track B handler for HDL-based testbenches
    
    Uses VUnit for test orchestration with various simulators.
    
    Supported TB Types:
    - vunit (native VUnit)
    - systemverilog (plain SV)
    - vhdl (plain VHDL)
    - uvm_sv (UVM with Questa)
    
    Simulator Selection:
    - vunit, systemverilog → Verilator (default) or Questa
    - vhdl → GHDL (default) or Questa
    - uvm_sv → Questa (required)
    """
    
    SUPPORTED_TB_TYPES = ['vunit', 'systemverilog', 'vhdl', 'uvm_sv']
    
    def __init__(
        self,
        submission_dir: Path,
        route_info,
        build_config,
    ):
        super().__init__(submission_dir, route_info, build_config)
        
        # Track B specific directories
        self.vunit_dir = self.output_dir / "vunit_project"
        self.vunit_out = self.output_dir / "vunit_out"
        
        # VUnit project paths
        self.run_py_path: Optional[Path] = None
        self.run_py_generated = False
        
        # Simulator instance (initialized during configure)
        self._simulator = None
        
        # Determine if this is a UVM project
        self.is_uvm = self.tb_type == 'uvm_sv'
        self.requires_questa = self.is_uvm or self.chosen_simulator == 'questa'
    
    # =========================================================================
    # ABSTRACT METHOD IMPLEMENTATIONS
    # =========================================================================
    
    def get_track_name(self) -> str:
        if self.is_uvm:
            return "Track B (UVM/Questa)"
        return "Track B (VUnit/HDL)"
    
    def get_capabilities(self) -> TrackCapabilities:
        simulators = [SimulatorType.VERILATOR, SimulatorType.GHDL]
        if self.requires_questa:
            simulators = [SimulatorType.QUESTA]
        
        return TrackCapabilities(
            supported_tb_types=self.SUPPORTED_TB_TYPES,
            supported_simulators=simulators,
            supports_coverage=True,
            supports_parallel=True,
            execution_mode=ExecutionMode.VUNIT_RUN,
        )
    
    def validate_prerequisites(self) -> List[str]:
        """Validate Track B prerequisites"""
        errors = []
        
        # Check Python
        if sys.version_info < (3, 7):
            errors.append("Python 3.7+ required")
        
        # Check VUnit
        try:
            import vunit
            self.log_info(f"VUnit version: {vunit.__version__}")
        except ImportError:
            errors.append(
                "VUnit not found. Install with: pip install vunit_hdl"
            )
        
        # Check simulator based on requirements
        if self.requires_questa:
            # UVM requires Questa
            if not self._check_questa_available():
                errors.append(
                    "Questa/ModelSim required for UVM testbenches but not found. "
                    "Ensure vsim is in PATH and license is configured."
                )
        else:
            # Check appropriate open-source simulator
            if self.language == 'vhdl':
                if not self.check_tool_available("ghdl"):
                    errors.append(
                        "GHDL not found. Install with: apt-get install ghdl"
                    )
            else:
                if not self.check_tool_available("verilator"):
                    # Try fallback to icarus
                    if not self.check_tool_available("iverilog"):
                        errors.append(
                            "No Verilog simulator found. Install Verilator or Icarus:\n"
                            "  apt-get install verilator\n"
                            "  apt-get install iverilog"
                        )
        
        # Check files exist
        for dut_file in self.dut_files:
            path = self.submission_dir / dut_file
            if not path.exists():
                errors.append(f"DUT file not found: {dut_file}")
        
        for tb_file in self.tb_files:
            path = self.submission_dir / tb_file
            if not path.exists():
                errors.append(f"TB file not found: {tb_file}")
        
        # Check for HDL files
        hdl_files = [
            f for f in (self.dut_files + self.tb_files)
            if f.endswith(('.sv', '.v', '.vhd', '.vhdl'))
        ]
        if not hdl_files:
            errors.append("No HDL files found in DUT or TB file lists")
        
        return errors
    
    def configure_simulator(self) -> Tuple[bool, List[str]]:
        """Configure simulator for Track B"""
        messages = []
        
        # Create directories
        self.vunit_dir.mkdir(parents=True, exist_ok=True)
        self.vunit_out.mkdir(parents=True, exist_ok=True)
        
        # Detect or generate VUnit project
        detector = VUnitProjectDetector(self.submission_dir)
        existing = detector.detect()
        
        if existing and existing.usable:
            self.run_py_path = existing.run_script
            self.run_py_generated = False
            messages.append(f"Using existing VUnit project: {existing.run_script}")
        else:
            # Generate VUnit project
            generator = VUnitProjectGenerator(self.submission_dir)
            
            try:
                generated = generator.generate(
                    route=self._create_route_info_object(),
                    build_config=self.build_config,
                    output_dir=self.output_dir,
                )
                
                self.run_py_path = generated.run_script
                self.run_py_generated = True
                messages.append(f"Generated VUnit project: {generated.run_script}")
                
                if generated.warnings:
                    messages.extend(generated.warnings)
                    
            except Exception as e:
                return False, [f"Failed to generate VUnit project: {str(e)}"]
        
        # Configure simulator-specific settings
        if self.requires_questa:
            ok, sim_messages = self._configure_questa()
        elif self.language == 'vhdl':
            ok, sim_messages = self._configure_ghdl()
        else:
            ok, sim_messages = self._configure_verilator()
        
        messages.extend(sim_messages)
        
        return ok, messages
    
    def compile_sources(self) -> CompilationResult:
        """Compile sources using VUnit"""
        result = CompilationResult(status=BuildStatus.COMPILING)
        start_time = datetime.now()
        
        if not self.run_py_path or not self.run_py_path.exists():
            result.status = BuildStatus.FAILURE
            result.libraries = [LibraryCompilationResult(
                library_name="work",
                success=False,
                errors=[CompilationError(
                    file="run.py",
                    line=0,
                    severity="error",
                    message="VUnit run script not found"
                )]
            )]
            result.total_errors = 1
            return result
        
        # Run VUnit with --compile flag
        vunit_cmd = [
            sys.executable,
            str(self.run_py_path),
            "--compile",
            f"--output-path={self.vunit_out}",
        ]
        
        # Add parallel jobs
        if self.build_config.parallel_jobs > 1:
            vunit_cmd.append(f"-p={self.build_config.parallel_jobs}")
        
        # Add clean flag if requested
        if self.build_config.clean_build:
            vunit_cmd.append("--clean")
        
        self.log_info(f"Running: {' '.join(vunit_cmd)}")
        
        try:
            # Get environment with simulator configuration
            env = os.environ.copy()
            env.update(self.get_execution_environment())
            
            proc = self.run_command(
                vunit_cmd,
                cwd=self.run_py_path.parent,
                env=env,
                timeout=600,
            )
            
            # Parse output
            stdout = proc.stdout or ""
            stderr = proc.stderr or ""
            
            lib_result = LibraryCompilationResult(
                library_name="work",
                success=(proc.returncode == 0),
            )
            
            # Parse for errors/warnings
            errors, warnings = self._parse_vunit_output(stdout + stderr)
            lib_result.errors = errors
            lib_result.warnings = warnings
            
            result.libraries = [lib_result]
            result.total_errors = len(errors)
            result.total_warnings = len(warnings)
            result.total_files = len(self.dut_files) + len(self.tb_files)
            
            if proc.returncode == 0:
                result.status = BuildStatus.SUCCESS
            else:
                result.status = BuildStatus.FAILURE
            
        except subprocess.TimeoutExpired:
            result.status = BuildStatus.FAILURE
            result.libraries = [LibraryCompilationResult(
                library_name="work",
                success=False,
                errors=[CompilationError(
                    file="",
                    line=0,
                    severity="error",
                    message="VUnit compilation timed out"
                )]
            )]
            result.total_errors = 1
            
        except Exception as e:
            result.status = BuildStatus.FAILURE
            result.libraries = [LibraryCompilationResult(
                library_name="work",
                success=False,
                errors=[CompilationError(
                    file="",
                    line=0,
                    severity="error",
                    message=f"Compilation failed: {str(e)}"
                )]
            )]
            result.total_errors = 1
        
        result.duration_ms = (datetime.now() - start_time).total_seconds() * 1000
        
        return result
    
    def discover_tests(self) -> TestDiscoveryResult:
        """Discover tests using VUnit and UVM discovery"""
        # For UVM, use UVM discovery
        if self.is_uvm:
            return self._discover_uvm_tests()
        
        # For VUnit, use VUnit discovery
        return self._discover_vunit_tests()
    
    def get_execution_command(self) -> List[str]:
        """Get VUnit execution command"""
        cmd = [
            sys.executable,
            str(self.run_py_path),
            f"--output-path={self.vunit_out}",
        ]
        
        # Add parallel execution
        if self.build_config.parallel_jobs > 1:
            cmd.append(f"-p={self.build_config.parallel_jobs}")
        
        # For UVM, we might need special handling
        if self.is_uvm:
            cmd.append("--num-threads=1")  # UVM typically single-threaded
        
        return cmd
    
    def get_execution_environment(self) -> Dict[str, str]:
        """Get environment for VUnit execution"""
        env = {}
        
        # Set simulator for VUnit
        if self.requires_questa:
            env["VUNIT_SIMULATOR"] = "modelsim"
            
            # Questa-specific environment
            if hasattr(self.build_config, 'simulator_config'):
                sim_config = self.build_config.simulator_config
                if isinstance(sim_config, QuestaConfig):
                    if sim_config.license_server:
                        env["LM_LICENSE_FILE"] = sim_config.license_server
                    if sim_config.path:
                        env["MTI_HOME"] = sim_config.path
                        env["PATH"] = f"{sim_config.path}/bin:{os.environ.get('PATH', '')}"
        
        elif self.language == 'vhdl':
            env["VUNIT_SIMULATOR"] = "ghdl"
        else:
            # VUnit doesn't natively support Verilator, but we can try modelsim mode
            # or use a custom approach
            env["VUNIT_SIMULATOR"] = "modelsim"
        
        # Coverage environment
        if self.build_config.coverage.enabled:
            env["VUNIT_COVERAGE"] = "1"
        
        return env
    
    def get_execution_cwd(self) -> Path:
        """Get working directory for execution"""
        if self.run_py_path:
            return self.run_py_path.parent
        return self.vunit_dir
    
    # =========================================================================
    # TRACK B SPECIFIC METHODS
    # =========================================================================
    
    def setup_coverage(self) -> CoverageConfig:
        """Setup coverage for VUnit"""
        config = self.build_config.coverage
        
        if config.enabled:
            if self.requires_questa:
                # Questa comprehensive coverage
                config.types = [CoverageType.ALL]
            else:
                # Open-source simulator coverage
                config.types = [
                    CoverageType.LINE,
                    CoverageType.BRANCH,
                ]
            
            config.output_dir = str(self.output_dir / "coverage")
        
        return config
    
    def _configure_questa(self) -> Tuple[bool, List[str]]:
        """Configure Questa simulator"""
        messages = []
        
        # Check Questa availability
        try:
            result = self.run_command(
                ["vsim", "-version"],
                timeout=10,
            )
            if result.returncode != 0:
                return False, ["Questa vsim command failed"]
            
            self.log_info(f"Questa: {result.stdout.strip()}")
            messages.append(f"Questa configured: {result.stdout.strip()}")
            
        except subprocess.TimeoutExpired:
            return False, ["Questa vsim timed out"]
        except FileNotFoundError:
            return False, ["Questa vsim not found in PATH"]
        except Exception as e:
            return False, [f"Questa configuration failed: {str(e)}"]
        
        # Check license
        license_server = None
        if hasattr(self.build_config, 'simulator_config'):
            sim_config = self.build_config.simulator_config
            if isinstance(sim_config, QuestaConfig):
                license_server = sim_config.license_server
        
        if not license_server:
            license_server = os.environ.get('LM_LICENSE_FILE')
        
        if not license_server:
            messages.append(
                "⚠️  No Questa license configured. "
                "Set LM_LICENSE_FILE or configure in .tbeval.yaml"
            )
        
        return True, messages
    
    def _configure_ghdl(self) -> Tuple[bool, List[str]]:
        """Configure GHDL simulator"""
        messages = []
        
        try:
            result = self.run_command(
                ["ghdl", "--version"],
                timeout=10,
            )
            if result.returncode == 0:
                version = result.stdout.split('\n')[0]
                self.log_info(f"GHDL: {version}")
                messages.append(f"GHDL configured: {version}")
                return True, messages
            
        except (subprocess.TimeoutExpired, FileNotFoundError):
            pass
        
        return False, ["GHDL not available"]
    
    def _configure_verilator(self) -> Tuple[bool, List[str]]:
        """Configure Verilator (for non-VHDL Track B)"""
        messages = []
        
        # Note: VUnit doesn't directly support Verilator
        # We'll use it in a custom way or fall back to Icarus
        
        if self.check_tool_available("verilator"):
            try:
                result = self.run_command(
                    ["verilator", "--version"],
                    timeout=10,
                )
                if result.returncode == 0:
                    self.log_info(f"Verilator: {result.stdout.strip()}")
                    messages.append(
                        "Note: VUnit has limited Verilator support. "
                        "Using VUnit with ModelSim interface."
                    )
                    return True, messages
            except Exception:
                pass
        
        # Try Icarus as fallback
        if self.check_tool_available("iverilog"):
            messages.append("Using Icarus Verilog as fallback simulator")
            return True, messages
        
        return False, ["No suitable Verilog simulator found"]
    
    def _discover_vunit_tests(self) -> TestDiscoveryResult:
        """Discover tests using VUnit --list"""
        discovery = VUnitTestDiscovery(
            submission_dir=self.submission_dir,
            run_script=self.run_py_path,
            output_path=self.vunit_out,
        )
        
        result = discovery.timed_discover([])
        
        # If VUnit discovery failed, try manual discovery
        if result.test_count == 0 and not result.errors:
            result.warnings.append("VUnit --list returned no tests, trying manual discovery")
            
            # Try to find testbenches in HDL files
            manual_tests = self._manual_test_discovery()
            result.tests.extend(manual_tests)
        
        return result.to_test_discovery_result()
    
    def _discover_uvm_tests(self) -> TestDiscoveryResult:
        """Discover UVM tests from SystemVerilog files"""
        discovery = UVMTestDiscovery(
            submission_dir=self.submission_dir,
            default_verbosity="UVM_MEDIUM",
        )
        
        tb_paths = [self.submission_dir / f for f in self.tb_files]
        result = discovery.timed_discover(tb_paths)
        
        # Also try VUnit discovery (might have VUnit wrapper)
        vunit_result = self._discover_vunit_tests()
        
        # Merge results
        seen_tests = {t.name for t in result.tests}
        for test in vunit_result.tests:
            if test.name not in seen_tests:
                result.tests.append(test)
        
        return result.to_test_discovery_result()
    
    def _manual_test_discovery(self) -> List[TestCase]:
        """Manual test discovery from HDL files"""
        tests = []
        
        # Pattern for testbench modules
        tb_pattern = re.compile(
            r'^\s*module\s+(\w*(?:tb|test|testbench)\w*)',
            re.MULTILINE | re.IGNORECASE
        )
        
        for tb_file in self.tb_files:
            if tb_file.endswith(('.sv', '.v')):
                path = self.submission_dir / tb_file
                if path.exists():
                    try:
                        content = path.read_text()
                        for match in tb_pattern.finditer(content):
                            module_name = match.group(1)
                            tests.append(TestCase(
                                name=module_name,
                                full_name=f"work.{module_name}",
                                testbench=module_name,
                                library="work",
                                test_type="hdl",
                                status=TestStatus.READY,
                            ))
                    except Exception:
                        pass
        
        return tests
    
    def _parse_vunit_output(
        self,
        output: str
    ) -> Tuple[List[CompilationError], List[CompilationError]]:
        """Parse VUnit output for errors and warnings"""
        errors = []
        warnings = []
        
        # Common error patterns from various simulators
        error_patterns = [
            # ModelSim/Questa
            r'\*\*\s*Error:\s*([^:]+):(\d+):\s*(.+)',
            r'\*\*\s*Error:\s*(.+)',
            # GHDL
            r'([^:]+):(\d+):(\d+):\s*error:\s*(.+)',
            # Generic
            r'ERROR:\s*(.+)',
        ]
        
        warning_patterns = [
            r'\*\*\s*Warning:\s*([^:]+):(\d+):\s*(.+)',
            r'\*\*\s*Warning:\s*(.+)',
            r'([^:]+):(\d+):(\d+):\s*warning:\s*(.+)',
            r'WARNING:\s*(.+)',
        ]
        
        for line in output.split('\n'):
            line = line.strip()
            
            # Check errors
            for pattern in error_patterns:
                match = re.match(pattern, line)
                if match:
                    groups = match.groups()
                    if len(groups) >= 3:
                        errors.append(CompilationError(
                            file=groups[0],
                            line=int(groups[1]) if groups[1].isdigit() else 0,
                            severity="error",
                            message=groups[-1],
                        ))
                    else:
                        errors.append(CompilationError(
                            file="",
                            line=0,
                            severity="error",
                            message=groups[0],
                        ))
                    break
            
            # Check warnings
            for pattern in warning_patterns:
                match = re.match(pattern, line)
                if match:
                    groups = match.groups()
                    if len(groups) >= 3:
                        warnings.append(CompilationError(
                            file=groups[0],
                            line=int(groups[1]) if groups[1].isdigit() else 0,
                            severity="warning",
                            message=groups[-1],
                        ))
                    else:
                        warnings.append(CompilationError(
                            file="",
                            line=0,
                            severity="warning",
                            message=groups[0],
                        ))
                    break
        
        return errors, warnings
    
    def _check_questa_available(self) -> bool:
        """Check if Questa is available"""
        try:
            result = self.run_command(
                ["vsim", "-version"],
                timeout=10,
            )
            return result.returncode == 0
        except Exception:
            return False
    
    def _create_route_info_object(self):
        """Create a route_info-like object for the generator"""
        from ..config import RouteInfo
        
        return RouteInfo(
            tb_type=self.tb_type,
            track=self.track,
            chosen_simulator=self.chosen_simulator,
            dut_files=self.dut_files,
            tb_files=self.tb_files,
            top_module=self.top_module,
            language=self.language,
        )
    
    def get_uvm_plusargs(self, test_name: Optional[str] = None) -> List[str]:
        """Get UVM plusargs for simulation"""
        plusargs = [
            "+UVM_VERBOSITY=UVM_MEDIUM",
            "+UVM_NO_RELNOTES",
        ]
        
        if test_name:
            plusargs.append(f"+UVM_TESTNAME={test_name}")
        
        return plusargs
