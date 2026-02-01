"""
Configuration management for Step 3: Build & Orchestrate

This module handles:
- Loading configuration from .tbeval.yaml
- Merging configuration with route.json from Step 2
- Environment variable handling for simulators/licenses
- Configuration validation

Author: TB Eval Team
Version: 0.1.0
"""

import os
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional, Dict, Any, List, Tuple
import yaml

from .models import (
    BuildConfig,
    SimulatorType,
    FailureMode,
    CoverageType,
    CoverageConfig,
    QuestaConfig,
    VerilatorConfig,
    GHDLConfig,
    LicenseInfo,
    LicenseType,
    LicenseStatus,
)


# =============================================================================
# CONFIGURATION ERRORS
# =============================================================================

@dataclass
class ConfigError:
    """Configuration error or warning"""
    field: str
    message: str
    severity: str = "error"  # error, warning, info
    
    def __str__(self) -> str:
        return f"[{self.severity.upper()}] {self.field}: {self.message}"


@dataclass  
class ConfigValidationResult:
    """Result of configuration validation"""
    valid: bool
    errors: List[ConfigError] = field(default_factory=list)
    warnings: List[ConfigError] = field(default_factory=list)
    
    def add_error(self, field: str, message: str) -> None:
        self.errors.append(ConfigError(field, message, "error"))
        self.valid = False
    
    def add_warning(self, field: str, message: str) -> None:
        self.warnings.append(ConfigError(field, message, "warning"))


# =============================================================================
# ENVIRONMENT VARIABLE MAPPINGS
# =============================================================================

class EnvironmentVariables:
    """Known environment variables for simulator configuration"""
    
    # Questa/ModelSim license
    QUESTA_LICENSE_VARS = [
        "LM_LICENSE_FILE",
        "MGLS_LICENSE_FILE", 
        "MLM_LICENSE_FILE",
    ]
    
    # Questa paths
    QUESTA_PATH_VARS = [
        "QUESTA_HOME",
        "QUESTASIM_HOME",
        "MODEL_TECH",
        "MTI_HOME",
    ]
    
    # Verilator
    VERILATOR_PATH_VARS = [
        "VERILATOR_ROOT",
    ]
    
    # GHDL
    GHDL_PATH_VARS = [
        "GHDL_PREFIX",
    ]
    
    # UVM
    UVM_VARS = [
        "UVM_HOME",
    ]
    
    @classmethod
    def get_questa_license(cls) -> Optional[str]:
        """Get Questa license from environment"""
        for var in cls.QUESTA_LICENSE_VARS:
            value = os.environ.get(var)
            if value:
                return value
        return None
    
    @classmethod
    def get_questa_path(cls) -> Optional[str]:
        """Get Questa installation path from environment"""
        for var in cls.QUESTA_PATH_VARS:
            value = os.environ.get(var)
            if value and Path(value).exists():
                return value
        return None
    
    @classmethod
    def get_verilator_path(cls) -> Optional[str]:
        """Get Verilator path from environment"""
        for var in cls.VERILATOR_PATH_VARS:
            value = os.environ.get(var)
            if value and Path(value).exists():
                return value
        return None
    
    @classmethod
    def get_uvm_home(cls) -> Optional[str]:
        """Get UVM_HOME from environment"""
        return os.environ.get("UVM_HOME")


# =============================================================================
# ROUTE JSON LOADER
# =============================================================================

@dataclass
class RouteInfo:
    """
    Parsed information from Step 2 route.json
    
    Attributes:
        tb_type: Testbench type (cocotb, uvm_sv, vunit, etc.)
        track: Execution track (A or B)
        chosen_simulator: Simulator chosen by Step 2
        dut_files: List of DUT files
        tb_files: List of testbench files
        top_module: Top module name
        language: HDL language
        quality_gate_passed: Whether quality gate passed
    """
    tb_type: str
    track: str
    chosen_simulator: str
    dut_files: List[str]
    tb_files: List[str]
    top_module: Optional[str] = None
    language: str = "systemverilog"
    quality_gate_passed: bool = True
    confidence: float = 1.0
    
    @classmethod
    def from_file(cls, path: Path) -> "RouteInfo":
        """Load from route.json file"""
        with open(path, 'r') as f:
            data = json.load(f)
        
        return cls(
            tb_type=data.get("tb_type", "unknown"),
            track=data.get("track", "B"),
            chosen_simulator=data.get("chosen_simulator", "verilator"),
            dut_files=data.get("dut_files", []),
            tb_files=data.get("tb_files", []),
            top_module=data.get("top_module"),
            language=data.get("language", "systemverilog"),
            quality_gate_passed=data.get("quality_gate_passed", True),
            confidence=data.get("confidence", 1.0),
        )
    
    def get_simulator_type(self) -> SimulatorType:
        """Convert string simulator to enum"""
        mapping = {
            "questa": SimulatorType.QUESTA,
            "modelsim": SimulatorType.MODELSIM,
            "verilator": SimulatorType.VERILATOR,
            "ghdl": SimulatorType.GHDL,
            "icarus": SimulatorType.ICARUS,
        }
        return mapping.get(self.chosen_simulator.lower(), SimulatorType.VERILATOR)


# =============================================================================
# MAIN CONFIGURATION MANAGER
# =============================================================================

class BuildConfigManager:
    """
    Manages build configuration for Step 3
    
    Configuration Sources (in priority order):
    1. CLI arguments (highest priority)
    2. Environment variables
    3. .tbeval.yaml in submission directory
    4. route.json from Step 2
    5. Default values (lowest priority)
    """
    
    CONFIG_FILENAMES = [
        ".tbeval.yaml",
        ".tbeval.yml",
        "tbeval.yaml",
        "tbeval_config.yaml",
    ]
    
    def __init__(self, submission_dir: Path):
        self.submission_dir = Path(submission_dir)
        self.config_path: Optional[Path] = None
        self.raw_config: Dict[str, Any] = {}
        self.route_info: Optional[RouteInfo] = None
    
    def load(
        self,
        route_json_path: Optional[Path] = None,
        cli_overrides: Optional[Dict[str, Any]] = None
    ) -> BuildConfig:
        """
        Load and merge all configuration sources
        
        Args:
            route_json_path: Path to route.json (default: submission_dir/route.json)
            cli_overrides: Dictionary of CLI argument overrides
        
        Returns:
            Merged BuildConfig
        """
        # Load route.json from Step 2
        route_path = route_json_path or (self.submission_dir / "route.json")
        if route_path.exists():
            self.route_info = RouteInfo.from_file(route_path)
        
        # Load .tbeval.yaml
        self._load_config_file()
        
        # Build configuration with merging
        config = self._build_config(cli_overrides or {})
        
        return config
    
    def _load_config_file(self) -> None:
        """Find and load configuration file"""
        for filename in self.CONFIG_FILENAMES:
            config_path = self.submission_dir / filename
            if config_path.exists():
                self.config_path = config_path
                with open(config_path, 'r') as f:
                    self.raw_config = yaml.safe_load(f) or {}
                return
        
        # No config file found - use empty dict
        self.raw_config = {}
    
    def _build_config(self, cli_overrides: Dict[str, Any]) -> BuildConfig:
        """Build final configuration from all sources"""
        
        # Determine simulator
        simulator = self._determine_simulator(cli_overrides)
        
        # Build simulator-specific config
        simulator_config = self._build_simulator_config(simulator, cli_overrides)
        
        # Build coverage config
        coverage_config = self._build_coverage_config(cli_overrides)
        
        # Determine failure mode
        failure_mode = self._get_value(
            cli_overrides.get("failure_mode"),
            self.raw_config.get("failure_mode"),
            "advisory"
        )
        
        # Build final config
        config = BuildConfig(
            project_name=self._get_value(
                cli_overrides.get("project_name"),
                self.raw_config.get("project_name"),
                self.route_info.tb_type if self.route_info else "tb_project"
            ),
            simulator=simulator,
            simulator_config=simulator_config,
            coverage=coverage_config,
            failure_mode=FailureMode(failure_mode),
            parallel_jobs=int(self._get_value(
                cli_overrides.get("parallel"),
                self.raw_config.get("parallel_jobs"),
                4
            )),
            incremental=self._get_value(
                cli_overrides.get("incremental"),
                self.raw_config.get("incremental"),
                True
            ),
            clean_build=self._get_value(
                cli_overrides.get("clean"),
                self.raw_config.get("clean_build"),
                False
            ),
            output_dir=self._get_value(
                cli_overrides.get("output"),
                self.raw_config.get("output_dir"),
                ".tbeval"
            ),
            vunit_args=self.raw_config.get("vunit_args", []),
            env_vars=self.raw_config.get("env_vars", {}),
        )
        
        return config
    
    def _determine_simulator(self, cli_overrides: Dict[str, Any]) -> SimulatorType:
        """Determine which simulator to use"""
        # CLI override has highest priority
        if "simulator" in cli_overrides:
            return SimulatorType(cli_overrides["simulator"])
        
        # Then config file
        if "simulator" in self.raw_config:
            sim_str = self.raw_config["simulator"].lower()
            if sim_str in ["questa", "modelsim"]:
                return SimulatorType.QUESTA
            elif sim_str == "verilator":
                return SimulatorType.VERILATOR
            elif sim_str == "ghdl":
                return SimulatorType.GHDL
            elif sim_str == "icarus":
                return SimulatorType.ICARUS
        
        # Then route.json
        if self.route_info:
            return self.route_info.get_simulator_type()
        
        # Default
        return SimulatorType.VERILATOR
    
    def _build_simulator_config(
        self,
        simulator: SimulatorType,
        cli_overrides: Dict[str, Any]
    ):
        """Build simulator-specific configuration"""
        
        if simulator in [SimulatorType.QUESTA, SimulatorType.MODELSIM]:
            return self._build_questa_config(cli_overrides)
        elif simulator == SimulatorType.VERILATOR:
            return self._build_verilator_config(cli_overrides)
        elif simulator == SimulatorType.GHDL:
            return self._build_ghdl_config(cli_overrides)
        else:
            return None
    
    def _build_questa_config(self, cli_overrides: Dict[str, Any]) -> QuestaConfig:
        """Build Questa-specific configuration"""
        questa_section = self.raw_config.get("questa", {})
        
        # Determine license
        license_server = self._get_value(
            cli_overrides.get("license_server"),
            questa_section.get("license_server"),
            EnvironmentVariables.get_questa_license()
        )
        
        license_file = self._get_value(
            cli_overrides.get("license_file"),
            questa_section.get("license_file"),
            None
        )
        
        # Determine installation path
        questa_path = self._get_value(
            cli_overrides.get("questa_path"),
            questa_section.get("path"),
            self.raw_config.get("questa_path"),
            EnvironmentVariables.get_questa_path()
        )
        
        # Build license info
        license_info = self._detect_questa_license(license_server, license_file)
        
        # Get UVM home
        uvm_home = self._get_value(
            questa_section.get("uvm_home"),
            EnvironmentVariables.get_uvm_home()
        )
        
        # Build config
        config = QuestaConfig(
            path=questa_path,
            license_server=license_server,
            license_file=license_file,
            license_info=license_info,
            uvm_home=uvm_home,
            uvm_verbosity=questa_section.get("uvm_verbosity", "UVM_MEDIUM"),
            coverage_enabled=self._get_value(
                cli_overrides.get("coverage"),
                questa_section.get("coverage_enabled"),
                True
            ),
            gui_mode=self._get_value(
                cli_overrides.get("gui"),
                questa_section.get("gui"),
                False
            ),
        )
        
        # Add custom flags from config
        if "vlog_flags" in questa_section:
            config.vlog_flags.extend(questa_section["vlog_flags"])
        if "vsim_flags" in questa_section:
            config.vsim_flags.extend(questa_section["vsim_flags"])
        if "suppress_warnings" in questa_section:
            config.suppress_warnings.extend(questa_section["suppress_warnings"])
        
        # Check availability
        config.available = self._check_questa_available(config)
        
        return config
    
    def _build_verilator_config(self, cli_overrides: Dict[str, Any]) -> VerilatorConfig:
        """Build Verilator-specific configuration"""
        verilator_section = self.raw_config.get("verilator", {})
        
        config = VerilatorConfig(
            path=self._get_value(
                cli_overrides.get("verilator_path"),
                verilator_section.get("path"),
                EnvironmentVariables.get_verilator_path()
            ),
            coverage_enabled=self._get_value(
                cli_overrides.get("coverage"),
                verilator_section.get("coverage_enabled"),
                True
            ),
            trace_enabled=verilator_section.get("trace_enabled", True),
            trace_format=verilator_section.get("trace_format", "vcd"),
            threads=verilator_section.get("threads", 1),
        )
        
        # Add custom flags
        if "flags" in verilator_section:
            config.verilator_flags.extend(verilator_section["flags"])
        
        # Check availability
        config.available = self._check_verilator_available(config)
        
        # License not required for open source tool
        config.license_info = LicenseInfo(
            license_type=LicenseType.UNKNOWN,
            status=LicenseStatus.NOT_REQUIRED,
            message="Verilator is open source - no license required"
        )
        
        return config
    
    def _build_ghdl_config(self, cli_overrides: Dict[str, Any]) -> GHDLConfig:
        """Build GHDL-specific configuration"""
        ghdl_section = self.raw_config.get("ghdl", {})
        
        config = GHDLConfig(
            std=ghdl_section.get("std", "08"),
            workdir=ghdl_section.get("workdir", "work"),
        )
        
        # Check availability
        config.available = self._check_ghdl_available(config)
        
        # License not required
        config.license_info = LicenseInfo(
            license_type=LicenseType.UNKNOWN,
            status=LicenseStatus.NOT_REQUIRED,
            message="GHDL is open source - no license required"
        )
        
        return config
    
    def _build_coverage_config(self, cli_overrides: Dict[str, Any]) -> CoverageConfig:
        """Build coverage configuration"""
        coverage_section = self.raw_config.get("coverage", {})
        
        # Determine if coverage enabled
        enabled = self._get_value(
            cli_overrides.get("coverage"),
            coverage_section.get("enabled"),
            True
        )
        
        # Handle explicit disable
        if cli_overrides.get("no_coverage"):
            enabled = False
        
        # Parse coverage types
        types_str = coverage_section.get("types", ["all"])
        types = []
        for t in types_str:
            try:
                types.append(CoverageType(t.lower()))
            except ValueError:
                pass
        if not types:
            types = [CoverageType.ALL]
        
        return CoverageConfig(
            enabled=enabled,
            types=types,
            merge_databases=coverage_section.get("merge", True),
            output_format=coverage_section.get("format", "lcov"),
            output_dir=coverage_section.get("output_dir", "coverage"),
        )
    
    def _detect_questa_license(
        self,
        license_server: Optional[str],
        license_file: Optional[str]
    ) -> LicenseInfo:
        """Detect and validate Questa license"""
        
        # Check license server
        if license_server:
            return LicenseInfo(
                license_type=LicenseType.FLOATING,
                status=LicenseStatus.UNKNOWN,  # Will verify at runtime
                server=license_server,
                message=f"License server configured: {license_server}"
            )
        
        # Check license file
        if license_file and Path(license_file).exists():
            return LicenseInfo(
                license_type=LicenseType.LICENSE_FILE,
                status=LicenseStatus.UNKNOWN,
                file_path=license_file,
                message=f"License file: {license_file}"
            )
        
        # Check environment
        env_license = EnvironmentVariables.get_questa_license()
        if env_license:
            if "@" in env_license:
                # Server format: port@host
                return LicenseInfo(
                    license_type=LicenseType.FLOATING,
                    status=LicenseStatus.UNKNOWN,
                    server=env_license,
                    message=f"License from environment: {env_license}"
                )
            elif Path(env_license).exists():
                return LicenseInfo(
                    license_type=LicenseType.LICENSE_FILE,
                    status=LicenseStatus.UNKNOWN,
                    file_path=env_license,
                    message=f"License file from environment: {env_license}"
                )
        
        # No license found
        return LicenseInfo(
            license_type=LicenseType.UNKNOWN,
            status=LicenseStatus.NOT_FOUND,
            message="No Questa license configured. Set LM_LICENSE_FILE or configure in .tbeval.yaml"
        )
    
    def _check_questa_available(self, config: QuestaConfig) -> bool:
        """Check if Questa is available"""
        import subprocess
        
        # Determine vsim command
        if config.path:
            vsim = Path(config.path) / "bin" / "vsim"
        else:
            vsim = "vsim"
        
        try:
            result = subprocess.run(
                [str(vsim), "-version"],
                capture_output=True,
                timeout=10
            )
            if result.returncode == 0:
                # Parse version from output
                output = result.stdout.decode('utf-8', errors='ignore')
                config.version = self._parse_questa_version(output)
                return True
        except (FileNotFoundError, subprocess.TimeoutExpired):
            pass
        
        return False
    
    def _check_verilator_available(self, config: VerilatorConfig) -> bool:
        """Check if Verilator is available"""
        import subprocess
        
        try:
            result = subprocess.run(
                ["verilator", "--version"],
                capture_output=True,
                timeout=5
            )
            if result.returncode == 0:
                output = result.stdout.decode('utf-8', errors='ignore')
                config.version = output.strip().split()[1] if output else None
                return True
        except (FileNotFoundError, subprocess.TimeoutExpired):
            pass
        
        return False
    
    def _check_ghdl_available(self, config: GHDLConfig) -> bool:
        """Check if GHDL is available"""
        import subprocess
        
        try:
            result = subprocess.run(
                ["ghdl", "--version"],
                capture_output=True,
                timeout=5
            )
            if result.returncode == 0:
                output = result.stdout.decode('utf-8', errors='ignore')
                config.version = output.split('\n')[0] if output else None
                return True
        except (FileNotFoundError, subprocess.TimeoutExpired):
            pass
        
        return False
    
    def _parse_questa_version(self, output: str) -> Optional[str]:
        """Parse Questa version from vsim -version output"""
        # Output looks like: "Questa Intel Starter FPGA Edition-64 vsim 2021.2 ..."
        # or "Model Technology ModelSim - INTEL FPGA STARTER EDITION vsim 2020.1 ..."
        import re
        
        patterns = [
            r'vsim\s+(\d+\.\d+)',
            r'Questa.*?(\d+\.\d+)',
            r'ModelSim.*?(\d+\.\d+)',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, output)
            if match:
                return match.group(1)
        
        return None
    
    def _get_value(self, *sources) -> Any:
        """Get first non-None value from sources"""
        for source in sources:
            if source is not None:
                return source
        return None
    
    def validate(self, config: BuildConfig) -> ConfigValidationResult:
        """Validate configuration"""
        result = ConfigValidationResult(valid=True)
        
        # Check simulator availability
        if config.simulator_config:
            if not config.simulator_config.available:
                result.add_error(
                    "simulator",
                    f"Simulator '{config.simulator.value}' is not available"
                )
        
        # Check license for commercial simulators
        if config.simulator in [SimulatorType.QUESTA, SimulatorType.MODELSIM]:
            if config.simulator_config:
                license_info = config.simulator_config.license_info
                if license_info and not license_info.is_valid():
                    if license_info.status == LicenseStatus.NOT_FOUND:
                        result.add_error("license", license_info.message)
                    else:
                        result.add_warning("license", license_info.message)
        
        # Check route.json was loaded
        if not self.route_info:
            result.add_warning(
                "route_json",
                "route.json not found - some configuration may be missing"
            )
        
        # Check for conflicting options
        if config.clean_build and config.incremental:
            result.add_warning(
                "build_options",
                "Both clean_build and incremental are set - clean_build takes precedence"
            )
        
        return result
    
    def get_route_info(self) -> Optional[RouteInfo]:
        """Get parsed route information"""
        return self.route_info
    
    def get_config_file_path(self) -> Optional[Path]:
        """Get path to loaded config file"""
        return self.config_path


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def load_build_config(
    submission_dir: Path,
    route_json_path: Optional[Path] = None,
    cli_overrides: Optional[Dict[str, Any]] = None
) -> Tuple[BuildConfig, ConfigValidationResult]:
    """
    Convenience function to load and validate build configuration
    
    Args:
        submission_dir: Path to submission directory
        route_json_path: Path to route.json (optional)
        cli_overrides: CLI argument overrides (optional)
    
    Returns:
        Tuple of (BuildConfig, ConfigValidationResult)
    """
    manager = BuildConfigManager(submission_dir)
    config = manager.load(route_json_path, cli_overrides)
    validation = manager.validate(config)
    
    return config, validation


def create_default_config_file(output_path: Path) -> None:
    """
    Create a default .tbeval.yaml configuration file
    
    Args:
        output_path: Path where to write the config file
    """
    default_config = {
        "project_name": "my_project",
        
        # Simulator selection
        "simulator": "questa",  # Options: questa, verilator, ghdl
        
        # Build options
        "parallel_jobs": 4,
        "incremental": True,
        "clean_build": False,
        "failure_mode": "advisory",  # Options: blocking, advisory
        
        # Output
        "output_dir": ".tbeval",
        
        # Coverage
        "coverage": {
            "enabled": True,
            "types": ["all"],
            "merge": True,
            "format": "lcov",
            "output_dir": "coverage",
        },
        
        # Questa-specific configuration
        "questa": {
            "path": None,  # Auto-detect or specify: "/opt/mentor/questasim"
            "license_server": None,  # e.g., "1234@license-server.com"
            "license_file": None,  # e.g., "/path/to/license.dat"
            "uvm_verbosity": "UVM_MEDIUM",
            "coverage_enabled": True,
            "gui": False,
            "vlog_flags": [],  # Additional vlog flags
            "vsim_flags": [],  # Additional vsim flags
            "suppress_warnings": [],  # Warning codes to suppress
        },
        
        # Verilator-specific configuration
        "verilator": {
            "path": None,  # Auto-detect or specify
            "coverage_enabled": True,
            "trace_enabled": True,
            "trace_format": "vcd",
            "threads": 1,
            "flags": [],  # Additional verilator flags
        },
        
        # GHDL-specific configuration
        "ghdl": {
            "std": "08",  # VHDL standard: 93, 02, 08
            "workdir": "work",
        },
        
        # Additional VUnit arguments
        "vunit_args": [],
        
        # Additional environment variables
        "env_vars": {},
    }
    
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_path, 'w') as f:
        yaml.dump(default_config, f, default_flow_style=False, sort_keys=False)
    
    print(f"Created default configuration: {output_path}")
