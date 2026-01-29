"""
Questa Configuration Module.

Handles Questa license server configuration and tool settings.

License Configuration:
    The license can be configured in three ways (in order of priority):
    1. Set via set_license() function at runtime
    2. QUESTA_LICENSE environment variable
    3. LM_LICENSE_FILE / MGLS_LICENSE_FILE environment variables (FlexLM)
    
    License format: port@server (e.g., "1717@license.company.com")
    
    Example:
        # Option 1: Runtime configuration
        from questa.config import set_license
        set_license("1717@license.company.com")
        
        # Option 2: Environment variable
        export QUESTA_LICENSE="1717@license.company.com"
        
        # Option 3: Standard FlexLM
        export LM_LICENSE_FILE="1717@license.company.com"
"""

import os
import shutil
import subprocess
from pathlib import Path
from dataclasses import dataclass, field
from typing import Optional, Dict, List, Any
from enum import Enum


class QuestaEdition(Enum):
    """Questa product editions."""
    QUESTA_CORE = "questa_core"           # Basic simulation
    QUESTA_PRIME = "questa_prime"         # Full features
    QUESTA_FORMAL = "questa_formal"       # Formal verification


@dataclass
class QuestaConfig:
    """
    Configuration for Questa simulator.
    
    Attributes:
        license_file: License server specification (port@server)
        install_path: Path to Questa installation (auto-detected if not set)
        edition: Questa edition to use
        uvm_home: Path to UVM library (uses built-in if not set)
        uvm_version: UVM version (default: 1.2)
        work_dir: Working directory for compilation artifacts
        coverage_db: Path to coverage database file
        verbose: Enable verbose output
        timeout_sec: Simulation timeout in seconds
        extra_vlog_args: Additional vlog (compiler) arguments
        extra_vsim_args: Additional vsim (simulator) arguments
        wave_format: Waveform format (wlf, vcd, fsdb)
    """
    
    # License configuration
    license_file: Optional[str] = None
    
    # Installation
    install_path: Optional[Path] = None
    edition: QuestaEdition = QuestaEdition.QUESTA_PRIME
    
    # UVM configuration
    uvm_home: Optional[Path] = None
    uvm_version: str = "1.2"
    
    # Runtime settings
    work_dir: Path = field(default_factory=lambda: Path("work"))
    coverage_db: Path = field(default_factory=lambda: Path("coverage.ucdb"))
    verbose: bool = False
    timeout_sec: int = 300
    
    # Tool arguments
    extra_vlog_args: List[str] = field(default_factory=list)
    extra_vsim_args: List[str] = field(default_factory=list)
    
    # Output settings
    wave_format: str = "wlf"
    generate_waves: bool = True
    
    def __post_init__(self):
        """Validate and resolve configuration after initialization."""
        self._resolve_license()
        self._resolve_install_path()
    
    def _resolve_license(self):
        """Resolve license file from environment if not set."""
        if self.license_file:
            return
        
        # Check environment variables in priority order
        env_vars = [
            'QUESTA_LICENSE',
            'MGLS_LICENSE_FILE',
            'LM_LICENSE_FILE',
        ]
        
        for var in env_vars:
            value = os.environ.get(var)
            if value:
                self.license_file = value
                return
    
    def _resolve_install_path(self):
        """Auto-detect Questa installation path."""
        if self.install_path:
            return
        
        # Try to find vsim in PATH
        vsim_path = shutil.which('vsim')
        if vsim_path:
            # Questa binaries are typically in <install>/bin
            self.install_path = Path(vsim_path).parent.parent
            return
        
        # Check common installation paths
        common_paths = [
            Path('/opt/mentor/questa'),
            Path('/opt/questasim'),
            Path('/eda/mentor/questa'),
            Path('/tools/questa'),
            Path(os.path.expanduser('~/questasim')),
        ]
        
        for path in common_paths:
            if path.exists() and (path / 'bin' / 'vsim').exists():
                self.install_path = path
                return
    
    @property
    def vlib_path(self) -> str:
        """Get path to vlib command."""
        if self.install_path:
            return str(self.install_path / 'bin' / 'vlib')
        return 'vlib'
    
    @property
    def vlog_path(self) -> str:
        """Get path to vlog command."""
        if self.install_path:
            return str(self.install_path / 'bin' / 'vlog')
        return 'vlog'
    
    @property
    def vopt_path(self) -> str:
        """Get path to vopt command."""
        if self.install_path:
            return str(self.install_path / 'bin' / 'vopt')
        return 'vopt'
    
    @property
    def vsim_path(self) -> str:
        """Get path to vsim command."""
        if self.install_path:
            return str(self.install_path / 'bin' / 'vsim')
        return 'vsim'
    
    @property
    def vcover_path(self) -> str:
        """Get path to vcover command."""
        if self.install_path:
            return str(self.install_path / 'bin' / 'vcover')
        return 'vcover'
    
    @property
    def qformal_path(self) -> str:
        """Get path to qformal command (formal verification)."""
        if self.install_path:
            return str(self.install_path / 'bin' / 'qformal')
        return 'qformal'
    
    def get_env(self) -> Dict[str, str]:
        """Get environment variables for Questa execution."""
        env = os.environ.copy()
        
        # Set license
        if self.license_file:
            env['LM_LICENSE_FILE'] = self.license_file
            env['MGLS_LICENSE_FILE'] = self.license_file
            env['QUESTA_LICENSE'] = self.license_file
        
        # Set UVM home if specified
        if self.uvm_home:
            env['UVM_HOME'] = str(self.uvm_home)
        
        # Add Questa to PATH if install path is known
        if self.install_path:
            bin_path = str(self.install_path / 'bin')
            env['PATH'] = f"{bin_path}:{env.get('PATH', '')}"
        
        return env
    
    def validate(self) -> List[str]:
        """
        Validate the configuration.
        
        Returns:
            List of error messages (empty if valid)
        """
        errors = []
        
        # Check license
        if not self.license_file:
            errors.append(
                "No license configured. Set QUESTA_LICENSE environment variable "
                "or use set_license() function. Format: port@server"
            )
        
        # Check tool availability
        tools = ['vlib', 'vlog', 'vsim', 'vcover']
        for tool in tools:
            tool_path = getattr(self, f'{tool}_path')
            if not shutil.which(tool_path):
                errors.append(f"Questa tool not found: {tool_path}")
        
        return errors
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert configuration to dictionary."""
        return {
            'license_file': self.license_file,
            'install_path': str(self.install_path) if self.install_path else None,
            'edition': self.edition.value,
            'uvm_version': self.uvm_version,
            'work_dir': str(self.work_dir),
            'coverage_db': str(self.coverage_db),
            'verbose': self.verbose,
            'timeout_sec': self.timeout_sec,
        }


# Global configuration instance
_config: Optional[QuestaConfig] = None


def get_config() -> QuestaConfig:
    """
    Get the global Questa configuration.
    
    Creates a default configuration if none exists.
    
    Returns:
        QuestaConfig instance
    """
    global _config
    if _config is None:
        _config = QuestaConfig()
    return _config


def set_license(license_file: str) -> None:
    """
    Set the Questa license server.
    
    Args:
        license_file: License specification in format port@server
                     Example: "1717@license.company.com"
    
    Example:
        from questa.config import set_license
        set_license("1717@license.company.com")
    """
    global _config
    if _config is None:
        _config = QuestaConfig(license_file=license_file)
    else:
        _config.license_file = license_file
    
    # Also set environment variables for consistency
    os.environ['QUESTA_LICENSE'] = license_file
    os.environ['LM_LICENSE_FILE'] = license_file


def configure(**kwargs) -> QuestaConfig:
    """
    Configure Questa with custom settings.
    
    Args:
        **kwargs: Configuration options (see QuestaConfig)
        
    Returns:
        Updated QuestaConfig instance
    
    Example:
        from questa.config import configure
        configure(
            license_file="1717@license.company.com",
            timeout_sec=600,
            verbose=True
        )
    """
    global _config
    _config = QuestaConfig(**kwargs)
    return _config


def check_license() -> bool:
    """
    Check if Questa license is available and valid.
    
    Returns:
        True if license is configured and Questa can be invoked
    """
    config = get_config()
    
    if not config.license_file:
        return False
    
    try:
        # Try running vsim -version to check license
        result = subprocess.run(
            [config.vsim_path, '-version'],
            capture_output=True,
            text=True,
            timeout=10,
            env=config.get_env()
        )
        return result.returncode == 0
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return False


def print_config() -> None:
    """Print current Questa configuration for debugging."""
    config = get_config()
    
    print("\n" + "=" * 60)
    print("QUESTA CONFIGURATION")
    print("=" * 60)
    
    print(f"\nLicense: {config.license_file or 'NOT CONFIGURED'}")
    print(f"Install Path: {config.install_path or 'Auto-detect'}")
    print(f"Edition: {config.edition.value}")
    print(f"UVM Version: {config.uvm_version}")
    
    print(f"\nTool Paths:")
    print(f"  vlib:   {config.vlib_path}")
    print(f"  vlog:   {config.vlog_path}")
    print(f"  vsim:   {config.vsim_path}")
    print(f"  vcover: {config.vcover_path}")
    
    print(f"\nRuntime:")
    print(f"  Work Dir: {config.work_dir}")
    print(f"  Timeout: {config.timeout_sec}s")
    print(f"  Verbose: {config.verbose}")
    
    # Validation
    errors = config.validate()
    if errors:
        print(f"\n⚠️  Configuration Issues:")
        for err in errors:
            print(f"  - {err}")
    else:
        print(f"\n✓ Configuration valid")
    
    print("=" * 60 + "\n")

