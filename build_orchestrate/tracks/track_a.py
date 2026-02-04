"""
Track A: CocoTB/PyUVM Handler
=============================

Handles Python-based testbenches:
- CocoTB testbenches
- PyUVM testbenches

Build Flow:
1. Verilator compilation with --coverage
2. Generate Makefile for CocoTB
3. CocoTB test discovery
4. Execution via make or cocotb-runner

Author: TB Eval Team
Version: 0.1.0
"""

import os
import re
import shutil
import subprocess
from dataclasses import dataclass, field
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
)
from ..discovery.cocotb_discovery import CocoTBTestDiscovery


@dataclass
class VerilatorBuildConfig:
    """Configuration for Verilator build"""
    top_module: str
    verilog_sources: List[Path]
    include_dirs: List[Path] = field(default_factory=list)
    defines: Dict[str, str] = field(default_factory=dict)
    coverage: bool = True
    trace: bool = True
    trace_format: str = "vcd"  # vcd or fst
    threads: int = 1
    extra_args: List[str] = field(default_factory=list)
    output_dir: Path = None


class CocoTBTrack(BaseTrack):
    """
    Track A handler for CocoTB and PyUVM testbenches
    
    Uses Verilator for simulation with CocoTB Python interface.
    
    Supported TB Types:
    - cocotb
    - pyuvm
    
    Build Process:
    1. Compile DUT with Verilator (--coverage enabled)
    2. Generate Makefile for CocoTB
    3. Discover Python test functions (@cocotb.test)
    4. Prepare execution environment
    """
    
    SUPPORTED_TB_TYPES = ['cocotb', 'pyuvm']
    
    def __init__(
        self,
        submission_dir: Path,
        route_info,
        build_config,
    ):
        super().__init__(submission_dir, route_info, build_config)
        
        # Track A specific directories
        self.verilator_dir = self.output_dir / "verilator"
        self.cocotb_dir = self.output_dir / "cocotb"
        
        # Detect top module
        self._top_module = self.top_module or self._detect_top_module()
        
        # Test module (Python file without .py)
        self._test_module = self._detect_test_module()
    
    # =========================================================================
    # ABSTRACT METHOD IMPLEMENTATIONS
    # =========================================================================
    
    def get_track_name(self) -> str:
        return "Track A (CocoTB)"
    
    def get_capabilities(self) -> TrackCapabilities:
        return TrackCapabilities(
            supported_tb_types=self.SUPPORTED_TB_TYPES,
            supported_simulators=[SimulatorType.VERILATOR],
            supports_coverage=True,
            supports_parallel=False,  # CocoTB tests run sequentially
            execution_mode=ExecutionMode.COCOTB_MAKE,
        )
    
    def validate_prerequisites(self) -> List[str]:
        """Validate Track A prerequisites"""
        errors = []
        
        # Check Verilator
        if not self.check_tool_available("verilator"):
            errors.append(
                "Verilator not found. Install with: apt-get install verilator "
                "or build from source: https://verilator.org"
            )
        else:
            # Check Verilator version (need 4.106+ for better SV support)
            version = self._get_verilator_version()
            if version and version < (4, 106):
                errors.append(
                    f"Verilator version {'.'.join(map(str, version))} is old. "
                    "Version 4.106+ recommended for better SystemVerilog support."
                )
        
        # Check Python cocotb
        try:
            import cocotb
            cocotb_version = cocotb.__version__
            self.log_info(f"CocoTB version: {cocotb_version}")
        except ImportError:
            errors.append(
                "CocoTB not found. Install with: pip install cocotb"
            )
        
        # Check for PyUVM if that's the TB type
        if self.tb_type == 'pyuvm':
            try:
                import pyuvm
                self.log_info(f"PyUVM available")
            except ImportError:
                errors.append(
                    "PyUVM not found. Install with: pip install pyuvm"
                )
        
        # Check for make
        if not self.check_tool_available("make"):
            errors.append("GNU Make not found. Required for CocoTB execution.")
        
        # Check DUT files exist
        for dut_file in self.dut_files:
            path = self.submission_dir / dut_file
            if not path.exists():
                errors.append(f"DUT file not found: {dut_file}")
        
        # Check TB files exist
        python_tb_found = False
        for tb_file in self.tb_files:
            path = self.submission_dir / tb_file
            if not path.exists():
                errors.append(f"TB file not found: {tb_file}")
            if tb_file.endswith('.py'):
                python_tb_found = True
        
        if not python_tb_found:
            errors.append("No Python test file found in testbench files")
        
        return errors
    
    def configure_simulator(self) -> Tuple[bool, List[str]]:
        """Configure Verilator for CocoTB"""
        messages = []
        
        # Create output directories
        self.verilator_dir.mkdir(parents=True, exist_ok=True)
        self.cocotb_dir.mkdir(parents=True, exist_ok=True)
        
        # Verify Verilator can be called
        try:
            result = self.run_command(
                ["verilator", "--version"],
                timeout=10
            )
            if result.returncode != 0:
                return False, ["Failed to run verilator --version"]
            
            self.log_info(f"Verilator: {result.stdout.strip()}")
            
        except subprocess.TimeoutExpired:
            return False, ["Verilator command timed out"]
        except Exception as e:
            return False, [f"Verilator configuration failed: {str(e)}"]
        
        # Check for SystemVerilog support
        sv_files = [f for f in self.dut_files if f.endswith('.sv')]
        if sv_files:
            messages.append(
                "SystemVerilog files detected. Using Verilator's SV support."
            )
        
        return True, messages
    
    def compile_sources(self) -> CompilationResult:
        """Compile DUT with Verilator"""
        result = CompilationResult(status=BuildStatus.COMPILING)
        start_time = datetime.now()
        
        # Prepare Verilator command
        verilator_cmd = self._build_verilator_command()
        
        self.log_info(f"Running: {' '.join(verilator_cmd)}")
        
        try:
            proc = self.run_command(
                verilator_cmd,
                cwd=self.verilator_dir,
                timeout=600,  # 10 minute timeout
            )
            
            # Parse output
            stdout = proc.stdout or ""
            stderr = proc.stderr or ""
            
            # Collect errors and warnings
            lib_result = LibraryCompilationResult(
                library_name="work",
                success=(proc.returncode == 0),
            )
            
            # Parse Verilator output for errors/warnings
            errors, warnings = self._parse_verilator_output(stdout + stderr)
            lib_result.errors = errors
            lib_result.warnings = warnings
            
            result.libraries = [lib_result]
            result.total_errors = len(errors)
            result.total_warnings = len(warnings)
            result.total_files = len(self.dut_files)
            
            if proc.returncode == 0:
                result.status = BuildStatus.SUCCESS
                
                # Run make to build the verilated model
                make_success = self._build_verilated_model()
                if not make_success:
                    result.status = BuildStatus.FAILURE
                    lib_result.errors.append(CompilationError(
                        file="Makefile",
                        line=0,
                        severity="error",
                        message="Failed to build Verilated model"
                    ))
                    result.total_errors += 1
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
                    message="Verilator compilation timed out"
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
        """Discover CocoTB tests from Python files"""
        discovery = CocoTBTestDiscovery(
            submission_dir=self.submission_dir,
            module_name=self._test_module,
        )
        
        python_files = self.get_python_test_files()
        result = discovery.timed_discover(python_files)
        
        # Mark all discovered tests as ready
        for test in result.tests:
            test.status = TestStatus.READY
        
        return result.to_test_discovery_result()
    
    def get_execution_command(self) -> List[str]:
        """Get command to run CocoTB tests"""
        # Option 1: Using make (traditional)
        makefile_path = self.cocotb_dir / "Makefile"
        
        if makefile_path.exists():
            return ["make", "-C", str(self.cocotb_dir)]
        
        # Option 2: Using cocotb-runner (modern)
        return [
            "python", "-m", "cocotb.runner",
            "--toplevel", self._top_module,
            "--module", self._test_module,
        ]
    
    def get_execution_environment(self) -> Dict[str, str]:
        """Get environment for CocoTB execution"""
        env = {}
        
        # CocoTB environment variables
        env["SIM"] = "verilator"
        env["TOPLEVEL_LANG"] = "verilog"
        env["TOPLEVEL"] = self._top_module
        env["MODULE"] = self._test_module
        
        # Verilator object directory
        env["VERILATOR_OBJ_DIR"] = str(self.verilator_dir)
        
        # Coverage
        if self.build_config.coverage.enabled:
            env["COVERAGE"] = "1"
            env["COCOTB_COVERAGE"] = "1"
        
        # Waves
        if hasattr(self.build_config.simulator_config, 'trace_enabled'):
            if self.build_config.simulator_config.trace_enabled:
                env["WAVES"] = "1"
        
        return env
    
    def get_execution_cwd(self) -> Path:
        """Get working directory for execution"""
        return self.cocotb_dir
    
    # =========================================================================
    # TRACK A SPECIFIC METHODS
    # =========================================================================
    
    def setup_coverage(self) -> CoverageConfig:
        """Setup coverage for CocoTB with Verilator"""
        config = self.build_config.coverage
        
        if config.enabled:
            # Verilator coverage types
            config.types = [
                CoverageType.LINE,
                CoverageType.TOGGLE,
            ]
            config.output_dir = str(self.output_dir / "coverage")
            config.output_format = "lcov"
        
        return config
    
    def generate_makefile(self) -> Path:
        """Generate Makefile for CocoTB execution"""
        makefile_path = self.cocotb_dir / "Makefile"
        
        # Get relative path from cocotb_dir to submission_dir
        rel_path = os.path.relpath(self.submission_dir, self.cocotb_dir)
        verilator_rel = os.path.relpath(self.verilator_dir, self.cocotb_dir)
        
        # Build source file list
        verilog_sources = []
        for dut_file in self.dut_files:
            if dut_file.endswith(('.v', '.sv')):
                verilog_sources.append(f"{rel_path}/{dut_file}")
        
        # Get include directories
        include_dirs = self._get_include_dirs()
        include_flags = " ".join(f"-I{d}" for d in include_dirs)
        
        # Determine Python test file
        python_test = None
        for tb_file in self.tb_files:
            if tb_file.endswith('.py'):
                python_test = tb_file
                break
        
        test_module = Path(python_test).stem if python_test else "test"
        
        # Generate Makefile content
        makefile_content = f'''# Auto-generated CocoTB Makefile
# Generated by TB Eval Framework - Track A
# {datetime.now().isoformat()}

# Simulation Configuration
SIM ?= verilator
TOPLEVEL_LANG ?= verilog

# Source files
VERILOG_SOURCES = {" ".join(verilog_sources)}

# Include directories
COMPILE_ARGS += {include_flags}

# Top-level module (DUT)
TOPLEVEL = {self._top_module}

# Python test module (without .py)
MODULE = {test_module}

# Verilator-specific settings
EXTRA_ARGS += --trace
EXTRA_ARGS += --trace-structs
'''

        # Add coverage if enabled
        if self.build_config.coverage.enabled:
            makefile_content += '''
# Coverage settings
EXTRA_ARGS += --coverage
EXTRA_ARGS += --coverage-line
EXTRA_ARGS += --coverage-toggle
'''

        makefile_content += '''
# Performance settings
EXTRA_ARGS += -j 4
EXTRA_ARGS += --threads 1

# Include cocotb's make rules
include $(shell cocotb-config --makefiles)/Makefile.sim

# Custom targets
.PHONY: waves coverage clean-all

waves:
\t@echo "Opening waveform viewer..."
\tgtkwave dump.vcd &

coverage:
\t@echo "Generating coverage report..."
\tverilator_coverage --annotate coverage_annotate coverage.dat
\tgenhtml coverage_annotate/coverage.info -o coverage_html

clean-all: clean
\trm -rf __pycache__ results.xml *.vcd *.fst coverage* obj_dir
'''

        self.write_file(makefile_path, makefile_content)
        self.log_info(f"Generated Makefile: {makefile_path}")
        
        return makefile_path
    
    def _build_verilator_command(self) -> List[str]:
        """Build Verilator compilation command"""
        cmd = [
            "verilator",
            "--cc",
            "--exe",
            "--build",
            "-j", "4",
        ]
        
        # Top module
        cmd.extend(["--top-module", self._top_module])
        
        # Output directory
        cmd.extend(["-Mdir", str(self.verilator_dir)])
        
        # Coverage
        if self.build_config.coverage.enabled:
            cmd.append("--coverage")
            cmd.append("--coverage-line")
            cmd.append("--coverage-toggle")
        
        # Trace (waveforms)
        cmd.append("--trace")
        
        # Warnings
        cmd.append("-Wall")
        cmd.append("-Wno-fatal")  # Don't treat warnings as errors
        
        # Timing (for modern Verilator)
        cmd.append("--timing")
        
        # Include directories
        for inc_dir in self._get_include_dirs():
            cmd.extend(["-I", str(inc_dir)])
        
        # CocoTB VPI
        try:
            import cocotb
            cocotb_share = Path(cocotb.__file__).parent / "share"
            if cocotb_share.exists():
                vpi_file = cocotb_share / "lib" / "verilator" / "cocotb_vpi.cpp"
                if vpi_file.exists():
                    cmd.append(str(vpi_file))
        except ImportError:
            pass
        
        # Add source files (absolute paths)
        for dut_file in self.dut_files:
            if dut_file.endswith(('.v', '.sv')):
                cmd.append(str(self.submission_dir / dut_file))
        
        return cmd
    
    def _build_verilated_model(self) -> bool:
        """Build the Verilated model using make"""
        makefile = self.verilator_dir / f"V{self._top_module}.mk"
        
        if not makefile.exists():
            self.log_info("Verilator Makefile not found - skipping make step")
            return True  # Might be using --build flag
        
        try:
            result = self.run_command(
                ["make", "-j4", "-f", makefile.name],
                cwd=self.verilator_dir,
                timeout=300,
            )
            return result.returncode == 0
        except Exception:
            return False
    
    def _parse_verilator_output(
        self,
        output: str
    ) -> Tuple[List[CompilationError], List[CompilationError]]:
        """Parse Verilator output for errors and warnings"""
        errors = []
        warnings = []
        
        # Verilator error format: %Error: file:line:col: message
        # Verilator warning format: %Warning-TAG: file:line:col: message
        
        error_pattern = re.compile(
            r'%Error(?:-(\w+))?: ([^:]+):(\d+):(?:(\d+):)? (.+)'
        )
        warning_pattern = re.compile(
            r'%Warning-(\w+): ([^:]+):(\d+):(?:(\d+):)? (.+)'
        )
        
        for line in output.split('\n'):
            line = line.strip()
            
            # Check for errors
            match = error_pattern.match(line)
            if match:
                code = match.group(1) or ""
                file = match.group(2)
                line_num = int(match.group(3))
                col = int(match.group(4)) if match.group(4) else 0
                message = match.group(5)
                
                errors.append(CompilationError(
                    file=file,
                    line=line_num,
                    column=col,
                    severity="error",
                    code=code,
                    message=message,
                ))
                continue
            
            # Check for warnings
            match = warning_pattern.match(line)
            if match:
                code = match.group(1)
                file = match.group(2)
                line_num = int(match.group(3))
                col = int(match.group(4)) if match.group(4) else 0
                message = match.group(5)
                
                warnings.append(CompilationError(
                    file=file,
                    line=line_num,
                    column=col,
                    severity="warning",
                    code=code,
                    message=message,
                ))
        
        return errors, warnings
    
    def _detect_top_module(self) -> str:
        """Detect top module name from DUT files"""
        # Try to find module declaration in DUT files
        module_pattern = re.compile(r'^\s*module\s+(\w+)', re.MULTILINE)
        
        for dut_file in self.dut_files:
            if dut_file.endswith(('.v', '.sv')):
                try:
                    content = (self.submission_dir / dut_file).read_text()
                    matches = module_pattern.findall(content)
                    if matches:
                        # Return last module (often the top) or first
                        # Prefer module with 'top' in name
                        for module in matches:
                            if 'top' in module.lower():
                                return module
                        return matches[0]
                except Exception:
                    pass
        
        # Fallback: use first DUT filename stem
        if self.dut_files:
            return Path(self.dut_files[0]).stem
        
        return "top"
    
    def _detect_test_module(self) -> str:
        """Detect Python test module name"""
        for tb_file in self.tb_files:
            if tb_file.endswith('.py'):
                return Path(tb_file).stem
        return "test"
    
    def _get_include_dirs(self) -> List[Path]:
        """Get include directories from source files"""
        include_dirs = set()
        
        # Add directories containing DUT files
        for dut_file in self.dut_files:
            dir_path = (self.submission_dir / dut_file).parent
            include_dirs.add(dir_path)
        
        # Look for common include directories
        common_includes = ["include", "inc", "rtl", "src"]
        for inc_dir in common_includes:
            path = self.submission_dir / inc_dir
            if path.exists() and path.is_dir():
                include_dirs.add(path)
        
        return list(include_dirs)
    
    def _get_verilator_version(self) -> Optional[Tuple[int, ...]]:
        """Get Verilator version as tuple"""
        try:
            result = self.run_command(
                ["verilator", "--version"],
                timeout=5,
            )
            if result.returncode == 0:
                # Parse "Verilator 5.006 2023-01-22" format
                match = re.search(r'(\d+)\.(\d+)', result.stdout)
                if match:
                    return (int(match.group(1)), int(match.group(2)))
        except Exception:
            pass
        return None
