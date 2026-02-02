"""
Questa/ModelSim Simulator Integration
=====================================

Full integration for Mentor/Siemens Questa and ModelSim simulators.

Features:
- Auto-detection of installation
- License management
- VUnit configuration
- UVM support
- Coverage configuration
- Compilation/simulation options

Supported Products:
- Questa Advanced Simulator
- Questa Prime
- ModelSim PE/SE/DE
- ModelSim Intel FPGA Edition
- Questa Intel FPGA Edition

Author: TB Eval Team
Version: 0.1.0
"""

import os
import re
import shutil
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional, Dict, Any, List, Tuple

from .base import (
    BaseSimulator,
    SimulatorCapabilities,
    SimulatorVersion,
    SimulatorEnvironment,
    SimulatorFeature,
)
from .license import (
    LicenseManager,
    LicenseCheckResult,
    LicenseStatus,
)
from ..models import QuestaConfig


@dataclass
class QuestaInstallation:
    """
    Detected Questa/ModelSim installation
    
    Attributes:
        path: Installation root path
        bin_dir: Binary directory (with vsim, vlog, etc.)
        version: Detected version
        product: Product name (Questa, ModelSim)
        edition: Edition (Advanced, PE, Intel FPGA, etc.)
        is_questa: True if Questa (vs ModelSim)
        uvm_home: Path to UVM library (if found)
        has_uvm: True if UVM is available
    """
    path: Path
    bin_dir: Path
    version: SimulatorVersion
    product: str = "ModelSim"
    edition: str = ""
    is_questa: bool = False
    uvm_home: Optional[Path] = None
    has_uvm: bool = False
    
    def get_vsim(self) -> Path:
        """Get path to vsim executable"""
        return self.bin_dir / ("vsim.exe" if os.name == "nt" else "vsim")
    
    def get_vlog(self) -> Path:
        """Get path to vlog executable"""
        return self.bin_dir / ("vlog.exe" if os.name == "nt" else "vlog")
    
    def get_vcom(self) -> Path:
        """Get path to vcom executable"""
        return self.bin_dir / ("vcom.exe" if os.name == "nt" else "vcom")
    
    def get_vlib(self) -> Path:
        """Get path to vlib executable"""
        return self.bin_dir / ("vlib.exe" if os.name == "nt" else "vlib")


class QuestaSimulator(BaseSimulator):
    """
    Questa/ModelSim simulator integration
    
    Usage:
        config = QuestaConfig(license_server="1234@server.com")
        questa = QuestaSimulator(config)
        
        if questa.is_available():
            questa.configure_vunit(vu)
    """
    
    # Common installation paths to search
    INSTALL_PATHS = [
        # Questa
        Path("/opt/mentor/questasim"),
        Path("/opt/questa"),
        Path("/opt/mentor/questa"),
        Path("/tools/mentor/questasim"),
        # ModelSim
        Path("/opt/mentor/modelsim"),
        Path("/opt/modelsim"),
        Path("/opt/intelFPGA/modelsim"),
        Path("/opt/intelFPGA_lite/modelsim"),
        # Windows paths
        Path("C:/mentor/questasim"),
        Path("C:/modeltech64"),
        Path("C:/intelFPGA/modelsim"),
    ]
    
    # Environment variables for installation path
    PATH_ENV_VARS = [
        "QUESTA_HOME",
        "QUESTASIM_HOME",
        "MTI_HOME",
        "MODEL_TECH",
        "MODELSIM_HOME",
    ]
    
    def __init__(self, config: Optional[QuestaConfig] = None):
        """
        Initialize Questa simulator
        
        Args:
            config: Questa configuration (optional)
        """
        super().__init__()
        self.config = config or QuestaConfig()
        self._installation: Optional[QuestaInstallation] = None
        self._license_result: Optional[LicenseCheckResult] = None
        self._license_manager = LicenseManager()
    
    # =========================================================================
    # BASE CLASS IMPLEMENTATION
    # =========================================================================
    
    def get_name(self) -> str:
        """Get simulator name"""
        if self._installation:
            return f"{self._installation.product} {self._installation.edition}".strip()
        return "Questa/ModelSim"
    
    def detect_installation(self) -> bool:
        """Detect if Questa/ModelSim is installed"""
        # Try explicit path first
        if self.config.path:
            installation = self._check_path(Path(self.config.path))
            if installation:
                self._installation = installation
                return True
        
        # Try environment variables
        for env_var in self.PATH_ENV_VARS:
            env_path = os.environ.get(env_var)
            if env_path:
                installation = self._check_path(Path(env_path))
                if installation:
                    self._installation = installation
                    return True
        
        # Try to find vsim in PATH
        vsim_path = shutil.which("vsim")
        if vsim_path:
            # Get installation directory from vsim location
            bin_dir = Path(vsim_path).parent
            install_dir = bin_dir.parent
            installation = self._check_path(install_dir)
            if installation:
                self._installation = installation
                return True
        
        # Search common installation paths
        for install_path in self.INSTALL_PATHS:
            if install_path.exists():
                installation = self._check_path(install_path)
                if installation:
                    self._installation = installation
                    return True
        
        return False
    
    def get_version(self) -> Optional[SimulatorVersion]:
        """Get simulator version"""
        if self._installation:
            return self._installation.version
        
        # Try to detect
        if self.detect_installation():
            return self._installation.version
        
        return None
    
    def get_capabilities(self) -> SimulatorCapabilities:
        """Get simulator capabilities"""
        features = {
            SimulatorFeature.SYSTEMVERILOG,
            SimulatorFeature.VERILOG,
            SimulatorFeature.VHDL,
            SimulatorFeature.COVERAGE_LINE,
            SimulatorFeature.COVERAGE_BRANCH,
            SimulatorFeature.COVERAGE_TOGGLE,
            SimulatorFeature.COVERAGE_FSM,
            SimulatorFeature.COVERAGE_ASSERTION,
            SimulatorFeature.WAVEFORM_VCD,
            SimulatorFeature.WAVEFORM_WLF,
            SimulatorFeature.GUI_MODE,
            SimulatorFeature.PARALLEL_EXECUTION,
        }
        
        # Check UVM support
        if self._installation and self._installation.has_uvm:
            features.add(SimulatorFeature.UVM)
        elif self._installation and self._installation.is_questa:
            # Questa typically includes UVM
            features.add(SimulatorFeature.UVM)
        
        return SimulatorCapabilities(
            supported_features=features,
            max_parallel_jobs=8,
            vunit_simulator_name="modelsim",
            supported_languages=["systemverilog", "verilog", "vhdl"],
        )
    
    def configure_vunit(self, vu: Any) -> None:
        """
        Configure VUnit instance for Questa/ModelSim
        
        Args:
            vu: VUnit instance to configure
        """
        # Set simulator-specific options
        compile_options = self.get_compile_options()
        sim_options = self.get_sim_options()
        
        # Apply compile options
        for opt_name, opt_values in compile_options.items():
            vu.set_compile_option(opt_name, opt_values)
        
        # Apply simulation options
        for opt_name, opt_values in sim_options.items():
            vu.set_sim_option(opt_name, opt_values)
    
    def get_compile_options(self) -> Dict[str, List[str]]:
        """Get VUnit compile options for Questa"""
        options = {}
        
        # Verilog/SystemVerilog compilation flags
        vlog_flags = list(self.config.vlog_flags)
        
        # Add standard flags if not present
        if "-sv" not in vlog_flags:
            vlog_flags.append("-sv")
        
        # Add access flags for debugging/coverage
        if "+acc=r" not in vlog_flags and "+acc" not in " ".join(vlog_flags):
            vlog_flags.append("+acc=r")
        
        # Add timescale if not present
        if not any("-timescale" in f for f in vlog_flags):
            vlog_flags.extend(["-timescale", "1ns/1ps"])
        
        options["modelsim.vlog_flags"] = vlog_flags
        
        # VHDL compilation flags
        vcom_flags = list(self.config.vcom_flags)
        if "-2008" not in vcom_flags and "-93" not in vcom_flags:
            vcom_flags.append("-2008")
        
        options["modelsim.vcom_flags"] = vcom_flags
        
        return options
    
    def get_sim_options(self) -> Dict[str, List[str]]:
        """Get VUnit simulation options for Questa"""
        options = {}
        
        vsim_flags = list(self.config.vsim_flags)
        
        # Add optimization flags
        if "-voptargs=+acc" not in vsim_flags:
            vsim_flags.append("-voptargs=+acc")
        
        # Add coverage flags if enabled
        if self.config.coverage_enabled:
            for cov_opt in self.config.coverage_options:
                if cov_opt not in vsim_flags:
                    vsim_flags.append(cov_opt)
        
        # Suppress warnings if configured
        for warning in self.config.suppress_warnings:
            vsim_flags.append(f"-suppress {warning}")
        
        options["modelsim.vsim_flags"] = vsim_flags
        
        # GUI mode
        if self.config.gui_mode:
            options["modelsim.gui"] = True
        
        return options
    
    # =========================================================================
    # QUESTA-SPECIFIC METHODS
    # =========================================================================
    
    def get_installation(self) -> Optional[QuestaInstallation]:
        """Get detected installation information"""
        if self._installation is None:
            self.detect_installation()
        return self._installation
    
    def check_license(self) -> LicenseCheckResult:
        """
        Check Questa license status
        
        Returns:
            LicenseCheckResult with license validation details
        """
        if self._license_result is not None:
            return self._license_result
        
        # Determine license source
        license_source = None
        
        if self.config.license_server:
            license_source = self.config.license_server
        elif self.config.license_file:
            license_source = self.config.license_file
        
        # Use license manager to detect/validate
        self._license_result = self._license_manager.detect_license(license_source)
        
        return self._license_result
    
    def get_environment(self) -> SimulatorEnvironment:
        """Get environment configuration for Questa"""
        if self._environment:
            return self._environment
        
        env = SimulatorEnvironment()
        
        if self._installation:
            env.path = self._installation.path
            env.bin_dir = self._installation.bin_dir
            env.path_additions = [self._installation.bin_dir]
            
            # Set MTI_HOME
            env.env_vars["MTI_HOME"] = str(self._installation.path)
            
            # Set MODEL_TECH
            env.env_vars["MODEL_TECH"] = str(self._installation.bin_dir)
        
        # Add license environment
        license_result = self.check_license()
        license_env = self._license_manager.configure_environment(license_result)
        env.env_vars.update(license_env)
        
        # Add UVM environment if available
        if self._installation and self._installation.uvm_home:
            env.env_vars["UVM_HOME"] = str(self._installation.uvm_home)
        
        self._environment = env
        return env
    
    def get_uvm_compile_flags(self) -> List[str]:
        """Get UVM-specific compilation flags"""
        flags = []
        
        # UVM include path
        if self._installation and self._installation.uvm_home:
            flags.append(f"+incdir+{self._installation.uvm_home}/src")
            flags.append(f"{self._installation.uvm_home}/src/uvm_pkg.sv")
        else:
            # Use built-in UVM (Questa typically has it)
            flags.append("-L uvm")
        
        return flags
    
    def get_uvm_sim_flags(
        self,
        test_name: Optional[str] = None,
        verbosity: Optional[str] = None,
        timeout: Optional[int] = None
    ) -> List[str]:
        """
        Get UVM-specific simulation flags
        
        Args:
            test_name: UVM test name to run
            verbosity: UVM verbosity level
            timeout: Simulation timeout in nanoseconds
        
        Returns:
            List of UVM plusargs
        """
        flags = []
        
        # Test name
        if test_name:
            flags.append(f"+UVM_TESTNAME={test_name}")
        
        # Verbosity
        verb = verbosity or self.config.uvm_verbosity
        flags.append(f"+UVM_VERBOSITY={verb}")
        
        # Timeout
        if timeout or self.config.uvm_timeout:
            to = timeout or self.config.uvm_timeout
            flags.append(f"+UVM_TIMEOUT={to}")
        
        # Common UVM flags
        flags.extend([
            "+UVM_NO_RELNOTES",  # Suppress release notes
        ])
        
        return flags
    
    def get_coverage_merge_command(
        self,
        output_file: str,
        input_files: List[str]
    ) -> List[str]:
        """
        Get command to merge coverage databases
        
        Args:
            output_file: Output merged database path
            input_files: List of input database paths
        
        Returns:
            Command as list of strings
        """
        if not self._installation:
            raise RuntimeError("Questa installation not detected")
        
        vcover = self._installation.bin_dir / "vcover"
        
        cmd = [
            str(vcover),
            "merge",
            "-out", output_file,
        ]
        cmd.extend(input_files)
        
        return cmd
    
    def get_coverage_report_command(
        self,
        database: str,
        output_dir: str,
        format: str = "html"
    ) -> List[str]:
        """
        Get command to generate coverage report
        
        Args:
            database: Coverage database path
            output_dir: Output directory for report
            format: Report format (html, text, xml)
        
        Returns:
            Command as list of strings
        """
        if not self._installation:
            raise RuntimeError("Questa installation not detected")
        
        vcover = self._installation.bin_dir / "vcover"
        
        cmd = [str(vcover), "report"]
        
        if format == "html":
            cmd.extend(["-html", "-htmldir", output_dir])
        elif format == "text":
            cmd.extend(["-file", f"{output_dir}/coverage.txt"])
        elif format == "xml":
            cmd.extend(["-xml", "-xmldir", output_dir])
        
        cmd.append(database)
        
        return cmd
    
    def compile_file(
        self,
        file_path: Path,
        library: str = "work",
        options: Optional[List[str]] = None
    ) -> Tuple[bool, str]:
        """
        Compile a single file
        
        Args:
            file_path: Path to source file
            library: Target library
            options: Additional compile options
        
        Returns:
            Tuple of (success, output)
        """
        if not self._installation:
            return False, "Questa installation not detected"
        
        # Determine compiler based on file type
        suffix = file_path.suffix.lower()
        
        if suffix in [".sv", ".v", ".svh", ".vh"]:
            compiler = self._installation.get_vlog()
            default_options = self.get_compile_options().get("modelsim.vlog_flags", [])
        elif suffix in [".vhd", ".vhdl"]:
            compiler = self._installation.get_vcom()
            default_options = self.get_compile_options().get("modelsim.vcom_flags", [])
        else:
            return False, f"Unknown file type: {suffix}"
        
        # Build command
        cmd = [
            str(compiler),
            "-work", library,
        ]
        cmd.extend(default_options)
        if options:
            cmd.extend(options)
        cmd.append(str(file_path))
        
        # Run compilation
        try:
            result = self.run_command(cmd, timeout=60)
            success = result.returncode == 0
            output = result.stdout + result.stderr
            return success, output
        except subprocess.TimeoutExpired:
            return False, "Compilation timed out"
        except Exception as e:
            return False, str(e)
    
    # =========================================================================
    # PRIVATE METHODS
    # =========================================================================
    
    def _check_path(self, install_path: Path) -> Optional[QuestaInstallation]:
        """
        Check if path contains valid Questa/ModelSim installation
        
        Args:
            install_path: Path to check
        
        Returns:
            QuestaInstallation if valid, None otherwise
        """
        # Check for bin directory
        bin_candidates = [
            install_path / "bin",
            install_path / "win64",
            install_path / "linux_x86_64",
            install_path / "linuxpe",
            install_path,
        ]
        
        bin_dir = None
        for candidate in bin_candidates:
            vsim = candidate / ("vsim.exe" if os.name == "nt" else "vsim")
            if vsim.exists():
                bin_dir = candidate
                break
        
        if not bin_dir:
            return None
        
        # Get version
        version = self._detect_version(bin_dir)
        if not version:
            return None
        
        # Check for UVM
        uvm_home, has_uvm = self._detect_uvm(install_path)
        
        return QuestaInstallation(
            path=install_path,
            bin_dir=bin_dir,
            version=version,
            product=version.product_name,
            edition=version.edition,
            is_questa="questa" in version.product_name.lower(),
            uvm_home=uvm_home,
            has_uvm=has_uvm,
        )
    
    def _detect_version(self, bin_dir: Path) -> Optional[SimulatorVersion]:
        """Detect simulator version from vsim -version output"""
        vsim = bin_dir / ("vsim.exe" if os.name == "nt" else "vsim")
        
        try:
            result = subprocess.run(
                [str(vsim), "-version"],
                capture_output=True,
                text=True,
                timeout=10,
            )
            
            if result.returncode != 0:
                return None
            
            output = result.stdout + result.stderr
            return self._parse_version_string(output)
            
        except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
            return None
    
    def _parse_version_string(self, output: str) -> Optional[SimulatorVersion]:
        """
        Parse version from vsim -version output
        
        Example outputs:
        - "Questa Intel Starter FPGA Edition-64 vsim 2021.2 Simulator 2021.04 Apr  9 2021"
        - "Model Technology ModelSim - INTEL FPGA STARTER EDITION vsim 2020.1 Simulator 2020.02 Feb 28 2020"
        - "Questa Sim-64 vsim 2023.1 Simulator 2023.01 Jan 23 2023"
        """
        version = SimulatorVersion(full_string=output.strip())
        
        # Determine product
        output_lower = output.lower()
        if "questa" in output_lower:
            version.product_name = "Questa"
            version.is_questa = True
        elif "modelsim" in output_lower or "model technology" in output_lower:
            version.product_name = "ModelSim"
        else:
            version.product_name = "Unknown"
        
        # Extract edition
        edition_patterns = [
            r"Intel.*?FPGA.*?(?:STARTER|PRO|EDITION)",
            r"(?:Starter|Advanced|Prime|SE|PE|DE)",
        ]
        for pattern in edition_patterns:
            match = re.search(pattern, output, re.IGNORECASE)
            if match:
                version.edition = match.group(0)
                break
        
        # Extract version numbers
        version_patterns = [
            r"vsim\s+(\d+)\.(\d+)",
            r"Simulator\s+(\d+)\.(\d+)",
            r"(\d{4})\.(\d+)",
        ]
        
        for pattern in version_patterns:
            match = re.search(pattern, output)
            if match:
                version.major = int(match.group(1))
                version.minor = int(match.group(2))
                break
        
        return version
    
    def _detect_uvm(self, install_path: Path) -> Tuple[Optional[Path], bool]:
        """
        Detect UVM installation
        
        Returns:
            Tuple of (uvm_home path, has_uvm boolean)
        """
        # Check common UVM locations
        uvm_candidates = [
            install_path / "verilog_src" / "uvm-1.2",
            install_path / "verilog_src" / "uvm-1.1d",
            install_path / "uvm-1.2",
            install_path / "uvm",
            install_path / "share" / "uvm",
        ]
        
        for candidate in uvm_candidates:
            if candidate.exists() and (candidate / "src" / "uvm_pkg.sv").exists():
                return candidate, True
        
        # Check environment
        uvm_home_env = os.environ.get("UVM_HOME")
        if uvm_home_env:
            uvm_path = Path(uvm_home_env)
            if uvm_path.exists():
                return uvm_path, True
        
        # Questa typically has built-in UVM
        # We'll assume it's available for Questa products
        return None, "questa" in str(install_path).lower()
    
    def validate_configuration(self) -> List[str]:
        """
        Validate full configuration
        
        Returns:
            List of error/warning messages (empty if valid)
        """
        issues = []
        
        # Check installation
        if not self.is_available():
            issues.append("Questa/ModelSim installation not found")
            return issues
        
        # Check license
        license_result = self.check_license()
        if not license_result.is_valid():
            issues.append(f"License issue: {license_result.message}")
        
        # Check version compatibility
        version = self.get_version()
        if version:
            # Warn about old versions
            if version.major < 2019:
                issues.append(
                    f"Warning: Version {version} is old. "
                    "Consider upgrading for better SystemVerilog support."
                )
        
        return issues
    
    def get_info(self) -> Dict[str, Any]:
        """Get comprehensive simulator information"""
        info = super().get_info()
        
        # Add Questa-specific info
        if self._installation:
            info.update({
                "installation_path": str(self._installation.path),
                "bin_dir": str(self._installation.bin_dir),
                "is_questa": self._installation.is_questa,
                "has_uvm": self._installation.has_uvm,
                "uvm_home": str(self._installation.uvm_home) if self._installation.uvm_home else None,
            })
        
        # Add license info
        license_result = self.check_license()
        info["license"] = license_result.to_dict()
        
        return info


# =============================================================================
# FACTORY FUNCTION
# =============================================================================

def create_questa_simulator(
    config: Optional[QuestaConfig] = None,
    auto_detect: bool = True
) -> QuestaSimulator:
    """
    Factory function to create configured Questa simulator
    
    Args:
        config: Questa configuration
        auto_detect: Whether to auto-detect installation
    
    Returns:
        Configured QuestaSimulator instance
    """
    simulator = QuestaSimulator(config)
    
    if auto_detect:
        simulator.detect_installation()
    
    return simulator
