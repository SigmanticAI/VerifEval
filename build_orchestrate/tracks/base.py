"""
Base Track Interface
====================

Abstract base class defining the interface for all track handlers.

Author: TB Eval Team
Version: 0.1.0
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Optional, List, Dict, Any, Tuple
import time
import subprocess
import os

from ..models import (
    BuildStatus,
    CompilationResult,
    TestDiscoveryResult,
    CoverageConfig,
    SimulatorType,
)


class ExecutionMode(Enum):
    """How tests will be executed"""
    COCOTB_MAKE = "cocotb_make"      # Via Makefile (Track A)
    COCOTB_RUNNER = "cocotb_runner"  # Via cocotb-runner (Track A)
    VUNIT_RUN = "vunit_run"          # Via VUnit run.py (Track B)
    QUESTA_VSIM = "questa_vsim"      # Direct vsim for UVM (Track B)


@dataclass
class TrackCapabilities:
    """
    Describes what a track can do
    
    Attributes:
        supported_tb_types: TB types this track handles
        supported_simulators: Simulators this track can use
        supports_coverage: Whether coverage collection is supported
        supports_parallel: Whether parallel test execution is supported
        execution_mode: How tests are executed
    """
    supported_tb_types: List[str] = field(default_factory=list)
    supported_simulators: List[SimulatorType] = field(default_factory=list)
    supports_coverage: bool = True
    supports_parallel: bool = False
    execution_mode: ExecutionMode = ExecutionMode.VUNIT_RUN


@dataclass
class TrackBuildResult:
    """
    Result of track build operation
    
    Attributes:
        success: Whether build succeeded
        status: Build status enum
        compilation: Compilation result
        tests_discovered: Discovered tests
        coverage_config: Coverage configuration
        execution_command: Command to run tests (for Step 4)
        execution_env: Environment variables for execution
        output_files: Generated files (Makefile, run.py, etc.)
        duration_ms: Build duration
        errors: List of errors
        warnings: List of warnings
    """
    success: bool = False
    status: BuildStatus = BuildStatus.PENDING
    compilation: Optional[CompilationResult] = None
    tests_discovered: Optional[TestDiscoveryResult] = None
    coverage_config: Optional[CoverageConfig] = None
    execution_command: List[str] = field(default_factory=list)
    execution_env: Dict[str, str] = field(default_factory=dict)
    execution_cwd: Optional[str] = None
    output_files: Dict[str, str] = field(default_factory=dict)
    duration_ms: float = 0.0
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "success": self.success,
            "status": self.status.value,
            "compilation": self.compilation.to_dict() if self.compilation else None,
            "tests_discovered": self.tests_discovered.to_dict() if self.tests_discovered else None,
            "coverage_config": self.coverage_config.to_dict() if self.coverage_config else None,
            "execution_command": self.execution_command,
            "execution_env": self.execution_env,
            "execution_cwd": self.execution_cwd,
            "output_files": self.output_files,
            "duration_ms": self.duration_ms,
            "errors": self.errors,
            "warnings": self.warnings,
        }


class BaseTrack(ABC):
    """
    Abstract base class for track handlers
    
    All track implementations must inherit from this class and
    implement the abstract methods.
    
    Lifecycle:
        1. __init__() - Initialize with route info and config
        2. validate_prerequisites() - Check required tools
        3. build() - Run full build pipeline
           - configure_simulator()
           - compile_sources()
           - discover_tests()
           - setup_coverage()
        4. get_execution_command() - Get command for Step 4
    """
    
    def __init__(
        self,
        submission_dir: Path,
        route_info,  # RouteInfo or dict
        build_config,  # BuildConfig
    ):
        """
        Initialize track handler
        
        Args:
            submission_dir: Path to submission directory
            route_info: Routing information from Step 2
            build_config: Build configuration from Step 3
        """
        self.submission_dir = Path(submission_dir)
        self.route_info = route_info
        self.build_config = build_config
        
        # Output directory
        self.output_dir = self.submission_dir / build_config.output_dir
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Extract commonly used values from route_info
        if hasattr(route_info, 'tb_type'):
            self.tb_type = route_info.tb_type
            self.track = route_info.track
            self.chosen_simulator = route_info.chosen_simulator
            self.dut_files = route_info.dut_files
            self.tb_files = route_info.tb_files
            self.top_module = route_info.top_module
            self.language = route_info.language
        else:
            # Dict access (from JSON)
            self.tb_type = route_info.get('tb_type', 'unknown')
            self.track = route_info.get('track', 'B')
            self.chosen_simulator = route_info.get('chosen_simulator', 'verilator')
            self.dut_files = route_info.get('dut_files', [])
            self.tb_files = route_info.get('tb_files', [])
            self.top_module = route_info.get('top_module')
            self.language = route_info.get('language', 'systemverilog')
        
        # Build result (populated during build)
        self._build_result: Optional[TrackBuildResult] = None
    
    # =========================================================================
    # ABSTRACT METHODS - Must be implemented by subclasses
    # =========================================================================
    
    @abstractmethod
    def get_track_name(self) -> str:
        """Get human-readable track name"""
        pass
    
    @abstractmethod
    def get_capabilities(self) -> TrackCapabilities:
        """Get track capabilities"""
        pass
    
    @abstractmethod
    def validate_prerequisites(self) -> List[str]:
        """
        Validate that all prerequisites are met
        
        Returns:
            List of error messages (empty if all prerequisites met)
        """
        pass
    
    @abstractmethod
    def configure_simulator(self) -> Tuple[bool, List[str]]:
        """
        Configure simulator for this track
        
        Returns:
            Tuple of (success, list of warnings/errors)
        """
        pass
    
    @abstractmethod
    def compile_sources(self) -> CompilationResult:
        """
        Compile all source files
        
        Returns:
            CompilationResult with compilation status
        """
        pass
    
    @abstractmethod
    def discover_tests(self) -> TestDiscoveryResult:
        """
        Discover tests in the project
        
        Returns:
            TestDiscoveryResult with discovered tests
        """
        pass
    
    @abstractmethod
    def get_execution_command(self) -> List[str]:
        """
        Get command to execute tests (for Step 4)
        
        Returns:
            Command as list of strings
        """
        pass
    
    @abstractmethod
    def get_execution_environment(self) -> Dict[str, str]:
        """
        Get environment variables for test execution
        
        Returns:
            Dictionary of environment variables
        """
        pass
    
    # =========================================================================
    # COMMON METHODS - Implemented in base class
    # =========================================================================
    
    def build(self) -> TrackBuildResult:
        """
        Run full build pipeline
        
        Steps:
        1. Validate prerequisites
        2. Configure simulator
        3. Compile sources
        4. Discover tests
        5. Setup coverage
        
        Returns:
            TrackBuildResult with all build information
        """
        start_time = time.time()
        
        result = TrackBuildResult()
        
        try:
            # Step 1: Validate prerequisites
            prereq_errors = self.validate_prerequisites()
            if prereq_errors:
                result.errors.extend(prereq_errors)
                result.status = BuildStatus.FAILURE
                result.duration_ms = (time.time() - start_time) * 1000
                return result
            
            # Step 2: Configure simulator
            sim_ok, sim_messages = self.configure_simulator()
            if not sim_ok:
                result.errors.extend(sim_messages)
                result.status = BuildStatus.FAILURE
                result.duration_ms = (time.time() - start_time) * 1000
                return result
            result.warnings.extend([m for m in sim_messages if m])
            
            # Step 3: Compile sources
            result.compilation = self.compile_sources()
            if not result.compilation.is_success():
                result.errors.append("Compilation failed")
                result.status = BuildStatus.FAILURE
                result.duration_ms = (time.time() - start_time) * 1000
                return result
            
            # Step 4: Discover tests
            result.tests_discovered = self.discover_tests()
            if result.tests_discovered.total_count == 0:
                result.warnings.append("No tests discovered")
            
            # Step 5: Setup coverage
            result.coverage_config = self.setup_coverage()
            
            # Step 6: Get execution command
            result.execution_command = self.get_execution_command()
            result.execution_env = self.get_execution_environment()
            result.execution_cwd = str(self.get_execution_cwd())
            
            # Success
            result.success = True
            result.status = BuildStatus.SUCCESS
            
        except Exception as e:
            result.errors.append(f"Build failed with exception: {str(e)}")
            result.status = BuildStatus.FAILURE
        
        result.duration_ms = (time.time() - start_time) * 1000
        self._build_result = result
        
        return result
    
    def setup_coverage(self) -> CoverageConfig:
        """
        Setup coverage configuration
        
        Default implementation returns config from build_config.
        Override in subclasses for track-specific coverage setup.
        """
        return self.build_config.coverage
    
    def get_execution_cwd(self) -> Path:
        """
        Get working directory for test execution
        
        Default: output directory
        """
        return self.output_dir
    
    def get_build_result(self) -> Optional[TrackBuildResult]:
        """Get the build result (after build() is called)"""
        return self._build_result
    
    # =========================================================================
    # UTILITY METHODS
    # =========================================================================
    
    def run_command(
        self,
        cmd: List[str],
        cwd: Optional[Path] = None,
        env: Optional[Dict[str, str]] = None,
        timeout: int = 300,
        capture_output: bool = True,
    ) -> subprocess.CompletedProcess:
        """
        Run a command with proper environment
        
        Args:
            cmd: Command and arguments
            cwd: Working directory
            env: Additional environment variables
            timeout: Timeout in seconds
            capture_output: Whether to capture stdout/stderr
        
        Returns:
            CompletedProcess result
        """
        # Build environment
        run_env = os.environ.copy()
        if env:
            run_env.update(env)
        
        return subprocess.run(
            cmd,
            cwd=cwd or self.submission_dir,
            env=run_env,
            timeout=timeout,
            capture_output=capture_output,
            text=True,
        )
    
    def check_tool_available(self, tool: str) -> bool:
        """Check if a tool is available in PATH"""
        import shutil
        return shutil.which(tool) is not None
    
    def get_dut_file_paths(self) -> List[Path]:
        """Get absolute paths to DUT files"""
        return [self.submission_dir / f for f in self.dut_files]
    
    def get_tb_file_paths(self) -> List[Path]:
        """Get absolute paths to TB files"""
        return [self.submission_dir / f for f in self.tb_files]
    
    def get_all_hdl_files(self) -> List[Path]:
        """Get all HDL files (DUT + TB)"""
        hdl_extensions = {'.sv', '.v', '.svh', '.vh', '.vhd', '.vhdl'}
        all_files = self.get_dut_file_paths() + self.get_tb_file_paths()
        return [f for f in all_files if f.suffix.lower() in hdl_extensions]
    
    def get_python_test_files(self) -> List[Path]:
        """Get Python test files"""
        return [
            self.submission_dir / f 
            for f in self.tb_files 
            if f.endswith('.py')
        ]
    
    def write_file(self, path: Path, content: str) -> None:
        """Write content to file, creating directories as needed"""
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content)
    
    def log_info(self, message: str) -> None:
        """Log info message (can be overridden for custom logging)"""
        print(f"[{self.get_track_name()}] {message}")
