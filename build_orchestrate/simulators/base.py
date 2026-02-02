"""
Base Simulator Interface
========================

Abstract base class that all simulator implementations must follow.
Provides common interface for:
- Availability checking
- Version detection
- VUnit configuration
- Coverage options
- Compilation/simulation flags

Author: TB Eval Team
Version: 0.1.0
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum, auto
from pathlib import Path
from typing import Optional, Dict, Any, List, Tuple
import subprocess
import os


class SimulatorFeature(Enum):
    """Features that simulators may support"""
    SYSTEMVERILOG = auto()
    VHDL = auto()
    VERILOG = auto()
    UVM = auto()
    COVERAGE_LINE = auto()
    COVERAGE_BRANCH = auto()
    COVERAGE_TOGGLE = auto()
    COVERAGE_FSM = auto()
    COVERAGE_ASSERTION = auto()
    WAVEFORM_VCD = auto()
    WAVEFORM_FST = auto()
    WAVEFORM_WLF = auto()
    GUI_MODE = auto()
    PARALLEL_EXECUTION = auto()
    COCOTB_INTEGRATION = auto()


@dataclass
class SimulatorCapabilities:
    """
    Describes what a simulator can do
    
    Attributes:
        supported_features: Set of supported features
        max_parallel_jobs: Maximum parallel compilation jobs
        vunit_simulator_name: Name as recognized by VUnit
        supported_languages: List of supported HDL languages
    """
    supported_features: set = field(default_factory=set)
    max_parallel_jobs: int = 4
    vunit_simulator_name: str = "modelsim"
    supported_languages: List[str] = field(default_factory=lambda: ["verilog"])
    
    def supports(self, feature: SimulatorFeature) -> bool:
        """Check if feature is supported"""
        return feature in self.supported_features
    
    def supports_uvm(self) -> bool:
        """Check if UVM is supported"""
        return self.supports(SimulatorFeature.UVM)
    
    def supports_coverage(self) -> bool:
        """Check if any coverage is supported"""
        coverage_features = [
            SimulatorFeature.COVERAGE_LINE,
            SimulatorFeature.COVERAGE_BRANCH,
            SimulatorFeature.COVERAGE_TOGGLE,
        ]
        return any(self.supports(f) for f in coverage_features)


@dataclass
class SimulatorVersion:
    """
    Simulator version information
    
    Attributes:
        major: Major version number
        minor: Minor version number
        patch: Patch version number
        full_string: Full version string as reported
        product_name: Product name (e.g., "Questa", "ModelSim")
        edition: Edition (e.g., "Intel FPGA Starter", "Advanced")
    """
    major: int = 0
    minor: int = 0
    patch: int = 0
    full_string: str = ""
    product_name: str = ""
    edition: str = ""
    
    def __str__(self) -> str:
        return self.full_string or f"{self.major}.{self.minor}.{self.patch}"
    
    def __ge__(self, other: "SimulatorVersion") -> bool:
        """Compare versions"""
        return (self.major, self.minor, self.patch) >= (other.major, other.minor, other.patch)
    
    def to_tuple(self) -> Tuple[int, int, int]:
        return (self.major, self.minor, self.patch)


@dataclass
class SimulatorEnvironment:
    """
    Environment configuration for simulator
    
    Attributes:
        path: Installation path
        bin_dir: Binary directory
        lib_dir: Library directory
        env_vars: Environment variables to set
        path_additions: Directories to add to PATH
    """
    path: Optional[Path] = None
    bin_dir: Optional[Path] = None
    lib_dir: Optional[Path] = None
    env_vars: Dict[str, str] = field(default_factory=dict)
    path_additions: List[Path] = field(default_factory=list)
    
    def get_env(self) -> Dict[str, str]:
        """Get complete environment with modifications"""
        env = os.environ.copy()
        
        # Add environment variables
        env.update(self.env_vars)
        
        # Modify PATH
        if self.path_additions:
            path_str = os.pathsep.join(str(p) for p in self.path_additions)
            existing_path = env.get("PATH", "")
            env["PATH"] = f"{path_str}{os.pathsep}{existing_path}"
        
        return env


class BaseSimulator(ABC):
    """
    Abstract base class for simulator implementations
    
    All simulator implementations must inherit from this class and
    implement the abstract methods.
    """
    
    def __init__(self):
        self._version: Optional[SimulatorVersion] = None
        self._capabilities: Optional[SimulatorCapabilities] = None
        self._environment: Optional[SimulatorEnvironment] = None
        self._available: Optional[bool] = None
    
    # =========================================================================
    # ABSTRACT METHODS - Must be implemented by subclasses
    # =========================================================================
    
    @abstractmethod
    def get_name(self) -> str:
        """Get simulator name"""
        pass
    
    @abstractmethod
    def detect_installation(self) -> bool:
        """
        Detect if simulator is installed and available
        
        Returns:
            True if simulator is found and usable
        """
        pass
    
    @abstractmethod
    def get_version(self) -> Optional[SimulatorVersion]:
        """
        Get simulator version
        
        Returns:
            SimulatorVersion object or None if not detected
        """
        pass
    
    @abstractmethod
    def get_capabilities(self) -> SimulatorCapabilities:
        """
        Get simulator capabilities
        
        Returns:
            SimulatorCapabilities describing what this simulator supports
        """
        pass
    
    @abstractmethod
    def configure_vunit(self, vu: Any) -> None:
        """
        Configure VUnit instance for this simulator
        
        Args:
            vu: VUnit instance to configure
        """
        pass
    
    @abstractmethod
    def get_compile_options(self) -> Dict[str, List[str]]:
        """
        Get compilation options for VUnit
        
        Returns:
            Dictionary of compile options (e.g., {"modelsim.vlog_flags": [...]})
        """
        pass
    
    @abstractmethod
    def get_sim_options(self) -> Dict[str, List[str]]:
        """
        Get simulation options for VUnit
        
        Returns:
            Dictionary of simulation options
        """
        pass
    
    # =========================================================================
    # COMMON METHODS - Implemented in base class
    # =========================================================================
    
    def is_available(self) -> bool:
        """
        Check if simulator is available for use
        
        Returns:
            True if simulator can be used
        """
        if self._available is None:
            self._available = self.detect_installation()
        return self._available
    
    def get_environment(self) -> SimulatorEnvironment:
        """
        Get environment configuration
        
        Returns:
            SimulatorEnvironment with paths and env vars
        """
        if self._environment is None:
            self._environment = SimulatorEnvironment()
        return self._environment
    
    def run_command(
        self,
        cmd: List[str],
        timeout: int = 30,
        check: bool = False,
        capture_output: bool = True,
        env: Optional[Dict[str, str]] = None
    ) -> subprocess.CompletedProcess:
        """
        Run a command with simulator environment
        
        Args:
            cmd: Command and arguments
            timeout: Timeout in seconds
            check: Raise exception on non-zero return
            capture_output: Capture stdout/stderr
            env: Additional environment variables
        
        Returns:
            CompletedProcess result
        """
        # Merge environment
        run_env = self.get_environment().get_env()
        if env:
            run_env.update(env)
        
        return subprocess.run(
            cmd,
            timeout=timeout,
            check=check,
            capture_output=capture_output,
            env=run_env,
            text=True
        )
    
    def validate_for_project(self, project_config: Dict[str, Any]) -> List[str]:
        """
        Validate simulator configuration for a specific project
        
        Args:
            project_config: Project configuration dictionary
        
        Returns:
            List of warning/error messages (empty if valid)
        """
        issues = []
        
        if not self.is_available():
            issues.append(f"Simulator '{self.get_name()}' is not available")
        
        # Check language support
        language = project_config.get("language", "systemverilog")
        caps = self.get_capabilities()
        
        if language == "vhdl" and "vhdl" not in caps.supported_languages:
            issues.append(f"Simulator does not support VHDL")
        
        # Check UVM requirement
        if project_config.get("tb_type") == "uvm_sv":
            if not caps.supports_uvm():
                issues.append(f"Simulator does not support UVM")
        
        return issues
    
    def get_info(self) -> Dict[str, Any]:
        """
        Get simulator information as dictionary
        
        Returns:
            Dictionary with simulator details
        """
        version = self.get_version()
        caps = self.get_capabilities()
        
        return {
            "name": self.get_name(),
            "available": self.is_available(),
            "version": str(version) if version else None,
            "product": version.product_name if version else None,
            "edition": version.edition if version else None,
            "vunit_name": caps.vunit_simulator_name,
            "supports_uvm": caps.supports_uvm(),
            "supports_coverage": caps.supports_coverage(),
            "supported_languages": caps.supported_languages,
        }
