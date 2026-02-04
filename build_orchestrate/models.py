"""
Data models for Step 3: Build & Orchestrate

This module contains all data structures used throughout the build
and orchestration phase, including:
- Build configuration options
- Simulator-specific configurations
- Compilation results
- Test case definitions
- Build manifest output

Author: TB Eval Team
Version: 0.1.0
"""

from dataclasses import dataclass, field, asdict
from enum import Enum
from typing import List, Optional, Dict, Any, Union
from datetime import datetime
from pathlib import Path


# =============================================================================
# ENUMS
# =============================================================================

class BuildStatus(Enum):
    """Build process status"""
    PENDING = "pending"
    COMPILING = "compiling"
    SUCCESS = "success"
    WARNING = "warning"
    FAILURE = "failure"
    SKIPPED = "skipped"


class FailureMode(Enum):
    """How to handle failures during build"""
    BLOCKING = "blocking"    # Stop immediately on failure
    ADVISORY = "advisory"    # Log and continue


class CoverageType(Enum):
    """Types of coverage to collect"""
    LINE = "line"
    BRANCH = "branch"
    TOGGLE = "toggle"
    FSM = "fsm"
    CONDITION = "condition"
    STATEMENT = "statement"
    ALL = "all"
    NONE = "none"


class SimulatorType(Enum):
    """Supported simulators"""
    QUESTA = "questa"
    MODELSIM = "modelsim"
    VERILATOR = "verilator"
    GHDL = "ghdl"
    ICARUS = "icarus"


class LicenseType(Enum):
    """License types for commercial simulators"""
    NODE_LOCKED = "node_locked"
    FLOATING = "floating"
    LICENSE_FILE = "license_file"
    UNKNOWN = "unknown"


class LicenseStatus(Enum):
    """License check status"""
    VALID = "valid"
    EXPIRED = "expired"
    NOT_FOUND = "not_found"
    SERVER_UNREACHABLE = "server_unreachable"
    UNKNOWN = "unknown"
    NOT_REQUIRED = "not_required"  # For open-source simulators


class TestStatus(Enum):
    """Status of a discovered test"""
    DISCOVERED = "discovered"
    READY = "ready"
    SKIPPED = "skipped"
    FILTERED = "filtered"


# =============================================================================
# LICENSE MODELS
# =============================================================================

@dataclass
class LicenseInfo:
    """
    Information about simulator license
    
    Attributes:
        license_type: Type of license (node_locked, floating, etc.)
        status: Current license status
        server: License server address (for floating licenses)
        file_path: Path to license file (if applicable)
        expiration: License expiration date (if known)
        features: Licensed features list
        message: Additional information or error message
    """
    license_type: LicenseType = LicenseType.UNKNOWN
    status: LicenseStatus = LicenseStatus.UNKNOWN
    server: Optional[str] = None
    file_path: Optional[str] = None
    expiration: Optional[str] = None
    features: List[str] = field(default_factory=list)
    message: str = ""
    
    def is_valid(self) -> bool:
        """Check if license is valid for use"""
        return self.status in [LicenseStatus.VALID, LicenseStatus.NOT_REQUIRED]
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "license_type": self.license_type.value,
            "status": self.status.value,
            "server": self.server,
            "file_path": self.file_path,
            "expiration": self.expiration,
            "features": self.features,
            "message": self.message,
        }


# =============================================================================
# SIMULATOR CONFIGURATION MODELS
# =============================================================================

@dataclass
class BaseSimulatorConfig:
    """
    Base configuration for all simulators
    
    Attributes:
        simulator_type: Type of simulator
        path: Path to simulator installation
        version: Simulator version (detected or specified)
        available: Whether simulator is available
        license_info: License information (for commercial simulators)
        compile_options: Additional compilation options
        sim_options: Additional simulation options
        env_vars: Environment variables to set
    """
    simulator_type: SimulatorType
    path: Optional[str] = None
    version: Optional[str] = None
    available: bool = False
    license_info: Optional[LicenseInfo] = None
    compile_options: List[str] = field(default_factory=list)
    sim_options: List[str] = field(default_factory=list)
    env_vars: Dict[str, str] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "simulator_type": self.simulator_type.value,
            "path": self.path,
            "version": self.version,
            "available": self.available,
            "license_info": self.license_info.to_dict() if self.license_info else None,
            "compile_options": self.compile_options,
            "sim_options": self.sim_options,
            "env_vars": self.env_vars,
        }


@dataclass
class QuestaConfig(BaseSimulatorConfig):
    """
    Questa/ModelSim specific configuration
    
    Attributes:
        license_server: License server (e.g., "1234@server.com")
        license_file: Path to license file
        vlog_flags: Additional vlog (Verilog/SV compiler) flags
        vcom_flags: Additional vcom (VHDL compiler) flags
        vsim_flags: Additional vsim (simulator) flags
        uvm_home: Path to UVM installation (usually built-in)
        uvm_dpi: Path to UVM DPI library
        coverage_options: Coverage collection options
        gui_mode: Whether to run in GUI mode
        suppress_warnings: Warning codes to suppress
    """
    simulator_type: SimulatorType = SimulatorType.QUESTA
    license_server: Optional[str] = None
    license_file: Optional[str] = None
    
    # Compilation flags
    vlog_flags: List[str] = field(default_factory=lambda: [
        "-sv",              # SystemVerilog mode
        "+acc=r",           # Enable access for debugging
        "-timescale", "1ns/1ps",
    ])
    vcom_flags: List[str] = field(default_factory=lambda: [
        "-2008",            # VHDL 2008
    ])
    
    # Simulation flags
    vsim_flags: List[str] = field(default_factory=lambda: [
        "-voptargs=+acc",   # Enable full visibility
    ])
    
    # UVM configuration
    uvm_home: Optional[str] = None
    uvm_dpi: Optional[str] = None
    uvm_verbosity: str = "UVM_MEDIUM"
    uvm_timeout: Optional[int] = None  # Timeout in ns
    
    # Coverage options
    coverage_enabled: bool = True
    coverage_options: List[str] = field(default_factory=lambda: [
        "-coverstore", "coverage_db",
        "-coverage",
    ])
    
    # GUI options
    gui_mode: bool = False
    
    # Warning suppression
    suppress_warnings: List[str] = field(default_factory=list)
    
    def get_vunit_sim_options(self) -> Dict[str, Any]:
        """Get options formatted for VUnit's set_sim_option"""
        options = {}
        
        # Combine all vsim flags
        all_vsim_flags = self.vsim_flags.copy()
        
        if self.coverage_enabled:
            all_vsim_flags.extend(self.coverage_options)
        
        if self.suppress_warnings:
            for warning in self.suppress_warnings:
                all_vsim_flags.append(f"-suppress {warning}")
        
        options["modelsim.vsim_flags"] = all_vsim_flags
        options["modelsim.vlog_flags"] = self.vlog_flags
        options["modelsim.vcom_flags"] = self.vcom_flags
        
        return options
    
    def get_uvm_plusargs(self, test_name: Optional[str] = None) -> List[str]:
        """Get UVM-specific plusargs for simulation"""
        plusargs = [
            f"+UVM_VERBOSITY={self.uvm_verbosity}",
        ]
        
        if test_name:
            plusargs.append(f"+UVM_TESTNAME={test_name}")
        
        if self.uvm_timeout:
            plusargs.append(f"+UVM_TIMEOUT={self.uvm_timeout}")
        
        return plusargs
    
    def to_dict(self) -> Dict[str, Any]:
        base = super().to_dict()
        base.update({
            "license_server": self.license_server,
            "license_file": self.license_file,
            "vlog_flags": self.vlog_flags,
            "vcom_flags": self.vcom_flags,
            "vsim_flags": self.vsim_flags,
            "uvm_home": self.uvm_home,
            "uvm_verbosity": self.uvm_verbosity,
            "coverage_enabled": self.coverage_enabled,
            "coverage_options": self.coverage_options,
            "gui_mode": self.gui_mode,
        })
        return base


@dataclass
class VerilatorConfig(BaseSimulatorConfig):
    """
    Verilator specific configuration
    
    Attributes:
        verilator_flags: Additional verilator compilation flags
        trace_enabled: Enable waveform tracing
        trace_format: Trace format (vcd, fst)
        coverage_enabled: Enable coverage
        coverage_types: Types of coverage to collect
        threads: Number of threads for simulation
        opt_level: Optimization level
    """
    simulator_type: SimulatorType = SimulatorType.VERILATOR
    
    # Compilation flags
    verilator_flags: List[str] = field(default_factory=lambda: [
        "--binary",
        "-Wall",
        "--trace",
    ])
    
    # Trace options
    trace_enabled: bool = True
    trace_format: str = "vcd"  # vcd or fst
    
    # Coverage options
    coverage_enabled: bool = True
    coverage_types: List[CoverageType] = field(default_factory=lambda: [
        CoverageType.LINE,
        CoverageType.TOGGLE,
    ])
    
    # Performance options
    threads: int = 1
    opt_level: str = "-O2"
    
    def get_coverage_flags(self) -> List[str]:
        """Get coverage-related flags"""
        if not self.coverage_enabled:
            return []
        
        flags = ["--coverage"]
        
        for cov_type in self.coverage_types:
            if cov_type == CoverageType.LINE:
                flags.append("--coverage-line")
            elif cov_type == CoverageType.TOGGLE:
                flags.append("--coverage-toggle")
        
        return flags
    
    def to_dict(self) -> Dict[str, Any]:
        base = super().to_dict()
        base.update({
            "verilator_flags": self.verilator_flags,
            "trace_enabled": self.trace_enabled,
            "trace_format": self.trace_format,
            "coverage_enabled": self.coverage_enabled,
            "coverage_types": [ct.value for ct in self.coverage_types],
            "threads": self.threads,
            "opt_level": self.opt_level,
        })
        return base


@dataclass
class GHDLConfig(BaseSimulatorConfig):
    """
    GHDL specific configuration
    
    Attributes:
        ghdl_flags: Additional GHDL flags
        std: VHDL standard (93, 08, etc.)
        workdir: Working directory for compiled files
    """
    simulator_type: SimulatorType = SimulatorType.GHDL
    
    # Compilation flags
    ghdl_flags: List[str] = field(default_factory=list)
    std: str = "08"  # VHDL 2008
    workdir: str = "work"
    
    def to_dict(self) -> Dict[str, Any]:
        base = super().to_dict()
        base.update({
            "ghdl_flags": self.ghdl_flags,
            "std": self.std,
            "workdir": self.workdir,
        })
        return base


# Type alias for any simulator config
SimulatorConfig = Union[QuestaConfig, VerilatorConfig, GHDLConfig, BaseSimulatorConfig]


# =============================================================================
# COMPILATION MODELS
# =============================================================================

@dataclass
class CompilationError:
    """
    A single compilation error or warning
    
    Attributes:
        file: Source file path
        line: Line number
        column: Column number
        severity: error, warning, info
        code: Error code (simulator-specific)
        message: Error message
        context: Surrounding code context
    """
    file: str
    line: int
    column: int = 0
    severity: str = "error"
    code: str = ""
    message: str = ""
    context: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
    
    def __str__(self) -> str:
        loc = f"{self.file}:{self.line}"
        if self.column:
            loc += f":{self.column}"
        return f"{loc}: {self.severity}: {self.message}"


@dataclass
class LibraryCompilationResult:
    """
    Compilation result for a single library
    
    Attributes:
        library_name: Name of the library
        files_compiled: List of compiled files
        success: Whether compilation succeeded
        errors: List of compilation errors
        warnings: List of compilation warnings
        duration_ms: Compilation duration in milliseconds
    """
    library_name: str
    files_compiled: List[str] = field(default_factory=list)
    success: bool = True
    errors: List[CompilationError] = field(default_factory=list)
    warnings: List[CompilationError] = field(default_factory=list)
    duration_ms: float = 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "library_name": self.library_name,
            "files_compiled": self.files_compiled,
            "success": self.success,
            "errors": [e.to_dict() for e in self.errors],
            "warnings": [w.to_dict() for w in self.warnings],
            "duration_ms": self.duration_ms,
        }


@dataclass
class CompilationResult:
    """
    Overall compilation result
    
    Attributes:
        status: Overall build status
        libraries: Results per library
        total_files: Total files compiled
        total_errors: Total error count
        total_warnings: Total warning count
        duration_ms: Total compilation duration
        output_log: Path to compilation log file
    """
    status: BuildStatus = BuildStatus.PENDING
    libraries: List[LibraryCompilationResult] = field(default_factory=list)
    total_files: int = 0
    total_errors: int = 0
    total_warnings: int = 0
    duration_ms: float = 0.0
    output_log: Optional[str] = None
    
    def is_success(self) -> bool:
        """Check if compilation was successful"""
        return self.status == BuildStatus.SUCCESS
    
    def has_errors(self) -> bool:
        """Check if there are any errors"""
        return self.total_errors > 0
    
    def get_all_errors(self) -> List[CompilationError]:
        """Get all errors from all libraries"""
        errors = []
        for lib in self.libraries:
            errors.extend(lib.errors)
        return errors
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "status": self.status.value,
            "libraries": [lib.to_dict() for lib in self.libraries],
            "total_files": self.total_files,
            "total_errors": self.total_errors,
            "total_warnings": self.total_warnings,
            "duration_ms": self.duration_ms,
            "output_log": self.output_log,
        }


# =============================================================================
# TEST CASE MODELS
# =============================================================================

@dataclass
class TestCase:
    """
    A discovered test case
    
    Attributes:
        name: Test name
        full_name: Fully qualified test name (library.testbench.test)
        testbench: Test bench name
        library: Library name
        test_type: Type of test (vunit, uvm, cocotb)
        status: Discovery status
        attributes: Test attributes/tags
        plusargs: Simulator plusargs for this test
        timeout_ms: Test timeout in milliseconds
        skip_reason: Reason if test is skipped
    """
    name: str
    full_name: str = ""
    testbench: str = ""
    library: str = "work"
    test_type: str = "vunit"  # vunit, uvm, cocotb
    status: TestStatus = TestStatus.DISCOVERED
    attributes: Dict[str, Any] = field(default_factory=dict)
    plusargs: List[str] = field(default_factory=list)
    timeout_ms: Optional[int] = None
    skip_reason: Optional[str] = None
    
    def __post_init__(self):
        if not self.full_name:
            self.full_name = f"{self.library}.{self.testbench}.{self.name}"
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "full_name": self.full_name,
            "testbench": self.testbench,
            "library": self.library,
            "test_type": self.test_type,
            "status": self.status.value,
            "attributes": self.attributes,
            "plusargs": self.plusargs,
            "timeout_ms": self.timeout_ms,
            "skip_reason": self.skip_reason,
        }


@dataclass
class TestDiscoveryResult:
    """
    Result of test discovery phase
    
    Attributes:
        tests: List of discovered tests
        total_count: Total number of tests
        ready_count: Tests ready to run
        skipped_count: Tests that will be skipped
        discovery_method: How tests were discovered
        duration_ms: Discovery duration
    """
    tests: List[TestCase] = field(default_factory=list)
    total_count: int = 0
    ready_count: int = 0
    skipped_count: int = 0
    discovery_method: str = "vunit"
    duration_ms: float = 0.0
    
    def __post_init__(self):
        self.total_count = len(self.tests)
        self.ready_count = sum(1 for t in self.tests if t.status == TestStatus.READY)
        self.skipped_count = sum(1 for t in self.tests if t.status == TestStatus.SKIPPED)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "tests": [t.to_dict() for t in self.tests],
            "total_count": self.total_count,
            "ready_count": self.ready_count,
            "skipped_count": self.skipped_count,
            "discovery_method": self.discovery_method,
            "duration_ms": self.duration_ms,
        }


# =============================================================================
# BUILD CONFIGURATION
# =============================================================================

@dataclass
class CoverageConfig:
    """
    Coverage collection configuration
    
    Attributes:
        enabled: Whether coverage is enabled
        types: Types of coverage to collect
        merge_databases: Whether to merge coverage from multiple runs
        output_format: Output format (lcov, html, etc.)
        output_dir: Directory for coverage output
    """
    enabled: bool = True
    types: List[CoverageType] = field(default_factory=lambda: [CoverageType.ALL])
    merge_databases: bool = True
    output_format: str = "lcov"
    output_dir: str = "coverage"
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "enabled": self.enabled,
            "types": [t.value for t in self.types],
            "merge_databases": self.merge_databases,
            "output_format": self.output_format,
            "output_dir": self.output_dir,
        }


@dataclass
class BuildConfig:
    """
    Complete build configuration
    
    Attributes:
        project_name: Project name
        simulator: Simulator to use
        simulator_config: Simulator-specific configuration
        coverage: Coverage configuration
        failure_mode: How to handle failures
        parallel_jobs: Number of parallel compilation jobs
        incremental: Enable incremental compilation
        clean_build: Force clean build
        output_dir: Output directory for build artifacts
        vunit_args: Additional arguments to pass to VUnit
        env_vars: Additional environment variables
    """
    project_name: str = "tb_eval_project"
    simulator: SimulatorType = SimulatorType.QUESTA
    simulator_config: Optional[SimulatorConfig] = None
    coverage: CoverageConfig = field(default_factory=CoverageConfig)
    failure_mode: FailureMode = FailureMode.ADVISORY
    parallel_jobs: int = 4
    incremental: bool = True
    clean_build: bool = False
    output_dir: str = ".tbeval"
    vunit_args: List[str] = field(default_factory=list)
    env_vars: Dict[str, str] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "project_name": self.project_name,
            "simulator": self.simulator.value,
            "simulator_config": self.simulator_config.to_dict() if self.simulator_config else None,
            "coverage": self.coverage.to_dict(),
            "failure_mode": self.failure_mode.value,
            "parallel_jobs": self.parallel_jobs,
            "incremental": self.incremental,
            "clean_build": self.clean_build,
            "output_dir": self.output_dir,
            "vunit_args": self.vunit_args,
            "env_vars": self.env_vars,
        }


# =============================================================================
# VUNIT PROJECT MODEL
# =============================================================================

@dataclass
class VUnitProjectInfo:
    """
    Information about the VUnit project
    
    Attributes:
        run_py_path: Path to run.py
        generated: Whether run.py was generated (vs existing)
        libraries: Libraries configured
        output_path: VUnit output path
        simulator_name: Simulator name as recognized by VUnit
    """
    run_py_path: str
    generated: bool = True
    libraries: List[str] = field(default_factory=lambda: ["work"])
    output_path: str = "vunit_out"
    simulator_name: str = "modelsim"  # VUnit's name for Questa
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


# =============================================================================
# BUILD MANIFEST (Final Output)
# =============================================================================

@dataclass
class BuildManifest:
    """
    Final output of Step 3 - Build Manifest
    
    This is the main output file that Step 4 (Execute) will consume.
    
    Attributes:
        build_status: Overall build status
        timestamp: When build completed
        duration_ms: Total build duration
        
        # Input references
        route_json_path: Path to input route.json
        submission_dir: Path to submission directory
        
        # Project information
        vunit_project: VUnit project information
        simulator_config: Simulator configuration used
        
        # Compilation results
        compilation: Compilation results
        
        # Test discovery
        tests_discovered: Discovered tests
        
        # Coverage configuration
        coverage_config: Coverage settings
        
        # Errors and warnings
        errors: List of blocking errors
        warnings: List of non-blocking warnings
        
        # Framework metadata
        framework_version: Version of tb-eval framework
    """
    build_status: BuildStatus = BuildStatus.PENDING
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    duration_ms: float = 0.0
    
    # Input references
    route_json_path: str = ""
    submission_dir: str = ""
    
    # Project information
    vunit_project: Optional[VUnitProjectInfo] = None
    simulator_config: Optional[SimulatorConfig] = None
    
    # Compilation results
    compilation: Optional[CompilationResult] = None

    #Execution info
    execution_command: List[str] = field(default_factory=list)
    execution_env: Dict[str, str] = field(default_factory=dict)
    execution_cwd: Optional[str] = None
    track_used: Optional[str] = None  # "A" or "B"
    
    # Test discovery
    tests_discovered: Optional[TestDiscoveryResult] = None
    
    # Coverage configuration
    coverage_config: Optional[CoverageConfig] = None
    
    # Errors and warnings
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    
    # Framework metadata
    framework_version: str = "0.1.0"
    
    def is_success(self) -> bool:
        """Check if build was successful"""
        return self.build_status == BuildStatus.SUCCESS
    
    def is_ready_for_execution(self) -> bool:
        """Check if ready for Step 4 execution"""
        return (
            self.is_success() and
            self.vunit_project is not None and
            self.tests_discovered is not None and
            self.tests_discovered.ready_count > 0
        )
    
    def get_test_count(self) -> int:
        """Get number of tests ready to run"""
        if self.tests_discovered:
            return self.tests_discovered.ready_count
        return 0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "build_status": self.build_status.value,
            "timestamp": self.timestamp,
            "duration_ms": self.duration_ms,
            "route_json_path": self.route_json_path,
            "submission_dir": self.submission_dir,
            "vunit_project": self.vunit_project.to_dict() if self.vunit_project else None,
            "simulator_config": self.simulator_config.to_dict() if self.simulator_config else None,
            "compilation": self.compilation.to_dict() if self.compilation else None,
            "tests_discovered": self.tests_discovered.to_dict() if self.tests_discovered else None,
            "coverage_config": self.coverage_config.to_dict() if self.coverage_config else None,
            "errors": self.errors,
            "warnings": self.warnings,
            "framework_version": self.framework_version,
        }
    
    def to_json(self, indent: int = 2) -> str:
        """Serialize to JSON string"""
        import json
        return json.dumps(self.to_dict(), indent=indent)
    
    def save(self, path: Path) -> None:
        """Save to file"""
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(self.to_json())
    
    @classmethod
    def load(cls, path: Path) -> "BuildManifest":
        """Load from file"""
        import json
        path = Path(path)
        data = json.loads(path.read_text())
        # Note: This is a simplified loader - full implementation would
        # reconstruct nested objects properly
        return cls(
            build_status=BuildStatus(data["build_status"]),
            timestamp=data["timestamp"],
            duration_ms=data["duration_ms"],
            route_json_path=data["route_json_path"],
            submission_dir=data["submission_dir"],
            errors=data.get("errors", []),
            warnings=data.get("warnings", []),
            framework_version=data.get("framework_version", "0.1.0"),
        )


# =============================================================================
# BUILD ERROR MODEL
# =============================================================================

@dataclass
class BuildError(Exception):
    """
    Exception raised during build process
    
    Attributes:
        message: Error message
        stage: Build stage where error occurred
        details: Additional error details
        recoverable: Whether error is recoverable
    """
    message: str
    stage: str = "unknown"
    details: Optional[Dict[str, Any]] = None
    recoverable: bool = False
    
    def __str__(self) -> str:
        return f"[{self.stage}] {self.message}"
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "message": self.message,
            "stage": self.stage,
            "details": self.details,
            "recoverable": self.recoverable,
        }
