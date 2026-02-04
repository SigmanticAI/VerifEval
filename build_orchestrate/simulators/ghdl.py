"""
GHDL Simulator Integration
==========================

Full integration for GHDL open-source VHDL simulator.

Features:
- Auto-detection of installation
- Coverage support (--coverage)
- Waveform tracing (VCD/GHW)
- VUnit integration
- Multiple VHDL standards (93, 08)

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
from .license import LicenseCheckResult, LicenseStatus, LicenseType
from ..models import GHDLConfig


@dataclass
class GHDLInstallation:
    """
    Detected GHDL installation
    
    Attributes:
        bin_path: Path to ghdl binary
        prefix: GHDL_PREFIX path (install location)
        version: Detected version
        backend: GHDL backend (mcode, llvm, gcc)
        supports_coverage: Whether --coverage is supported
        supports_psl: Whether PSL assertions are supported
    """
    bin_path: Path
    prefix: Optional[Path] = None
    version: Optional[SimulatorVersion] = None
    backend: str = "mcode"
    supports_coverage: bool = False
    supports_psl: bool = False
    
    def get_lib_path(self) -> Optional[Path]:
        """Get path to GHDL libraries"""
        if self.prefix:
            return self.prefix / "lib" / "ghdl"
        return None


class GHDLSimulator(BaseSimulator):
    """
    GHDL simulator integration
    
    GHDL is an open-source VHDL simulator with three backends:
    - mcode: Portable, fast compilation
    - llvm: Uses LLVM, better performance
    - gcc: Uses GCC, best performance
    
    Usage:
        config = GHDLConfig(std="08", coverage_enabled=True)
        ghdl = GHDLSimulator(config)
        
        if ghdl.is_available():
            ghdl.configure_vunit(vu)
    """
    
    # Minimum recommended version
    MIN_VERSION = (2, 0)
    
    # Environment variable for installation prefix
    PREFIX_ENV_VAR = "GHDL_PREFIX"
    
    # Supported VHDL standards
    SUPPORTED_STANDARDS = ["87", "93", "02", "08", "19"]
    
    def __init__(self, config: Optional[GHDLConfig] = None):
        """
        Initialize GHDL simulator
        
        Args:
            config: GHDL configuration (optional)
        """
        super().__init__()
        self.config = config or GHDLConfig()
        self._installation: Optional[GHDLInstallation] = None
    
    # =========================================================================
    # BASE CLASS IMPLEMENTATION
    # =========================================================================
    
    def get_name(self) -> str:
        """Get simulator name"""
        if self._installation and self._installation.version:
            backend = f" ({self._installation.backend})" if self._installation.backend else ""
            return f"GHDL {self._installation.version}{backend}"
        return "GHDL"
    
    def detect_installation(self) -> bool:
        """Detect if GHDL is installed"""
        # Try to find ghdl in PATH
        ghdl_path = shutil.which("ghdl")
        if not ghdl_path:
            return False
        
        # Get installation details
        installation = self._analyze_installation(Path(ghdl_path))
        if installation:
            self._installation = installation
            return True
        
        return False
    
    def get_version(self) -> Optional[SimulatorVersion]:
        """Get GHDL version"""
        if self._installation:
            return self._installation.version
        
        if self.detect_installation():
            return self._installation.version
        
        return None
    
    def get_capabilities(self) -> SimulatorCapabilities:
        """Get GHDL capabilities"""
        features = {
            SimulatorFeature.VHDL,
            SimulatorFeature.WAVEFORM_VCD,
            SimulatorFeature.PARALLEL_EXECUTION,
        }
        
        # Check version-specific features
        if self._installation:
            if self._installation.supports_coverage:
                features.add(SimulatorFeature.COVERAGE_LINE)
                features.add(SimulatorFeature.COVERAGE_BRANCH)
            
            if self._installation.backend in ["llvm", "gcc"]:
                # Better performance backends
                features.add(SimulatorFeature.WAVEFORM_FST)
        
        return SimulatorCapabilities(
            supported_features=features,
            max_parallel_jobs=os.cpu_count() or 4,
            vunit_simulator_name="ghdl",
            supported_languages=["vhdl"],
        )
    
    def configure_vunit(self, vu: Any) -> None:
        """
        Configure VUnit for GHDL
        
        Args:
            vu: VUnit instance to configure
        """
        # GHDL is natively supported by VUnit
        # Set VHDL standard
        if self.config.std:
            vu.set_compile_option("ghdl.a_flags", [f"--std={self.config.std}"])
        
        # Enable coverage if requested
        if self._installation and self._installation.supports_coverage:
            vu.set_sim_option("ghdl.elab_flags", ["--coverage"])
            vu.set_sim_option("ghdl.sim_flags", ["--coverage"])
    
    def get_compile_options(self) -> Dict[str, List[str]]:
        """Get compilation options for VUnit"""
        options = {}
        
        # Analysis (compilation) flags
        a_flags = [f"--std={self.config.std}"]
        
        # Add work directory
        if self.config.workdir:
            a_flags.append(f"--workdir={self.config.workdir}")
        
        # Add any custom flags
        a_flags.extend(self.config.ghdl_flags)
        
        options["ghdl.a_flags"] = a_flags
        
        return options
    
    def get_sim_options(self) -> Dict[str, List[str]]:
        """Get simulation options for VUnit"""
        options = {}
        
        # Elaboration flags
        elab_flags = []
        
        # Simulation flags
        sim_flags = []
        
        # Coverage
        if self._installation and self._installation.supports_coverage:
            elab_flags.append("--coverage")
            sim_flags.append("--coverage")
        
        # Waveform generation
        sim_flags.append("--vcd=wave.vcd")
        
        options["ghdl.elab_flags"] = elab_flags
        options["ghdl.sim_flags"] = sim_flags
        
        return options
    
    # =========================================================================
    # GHDL-SPECIFIC METHODS
    # =========================================================================
    
    def get_installation(self) -> Optional[GHDLInstallation]:
        """Get detected installation information"""
        if self._installation is None:
            self.detect_installation()
        return self._installation
    
    def check_license(self) -> LicenseCheckResult:
        """
        Check license - GHDL is open source
        
        Returns:
            LicenseCheckResult indicating no license required
        """
        return LicenseCheckResult(
            status=LicenseStatus.NOT_REQUIRED,
            license_type=LicenseType.UNKNOWN,
            message="GHDL is open source (GPL) - no license required",
        )
    
    def get_environment(self) -> SimulatorEnvironment:
        """Get environment configuration for GHDL"""
        if self._environment:
            return self._environment
        
        env = SimulatorEnvironment()
        
        if self._installation:
            env.bin_dir = self._installation.bin_path.parent
            env.path_additions = [self._installation.bin_path.parent]
            
            # Set GHDL_PREFIX if we found it
            if self._installation.prefix:
                env.path = self._installation.prefix
                env.env_vars["GHDL_PREFIX"] = str(self._installation.prefix)
        
        self._environment = env
        return env
    
    def analyze_file(
        self,
        file_path: Path,
        library: str = "work",
        workdir: Optional[Path] = None,
    ) -> Tuple[bool, str]:
        """
        Analyze (compile) a VHDL file
        
        Args:
            file_path: Path to VHDL file
            library: Target library name
            workdir: Working directory for compiled files
        
        Returns:
            Tuple of (success, output)
        """
        cmd = [
            "ghdl",
            "-a",  # analyze
            f"--std={self.config.std}",
            f"--work={library}",
        ]
        
        if workdir:
            cmd.append(f"--workdir={workdir}")
        
        cmd.extend(self.config.ghdl_flags)
        cmd.append(str(file_path))
        
        try:
            result = self.run_command(cmd, timeout=60)
            success = result.returncode == 0
            output = result.stdout + result.stderr
            return success, output
        except subprocess.TimeoutExpired:
            return False, "Analysis timed out"
        except Exception as e:
            return False, str(e)
    
    def elaborate(
        self,
        top_entity: str,
        library: str = "work",
        workdir: Optional[Path] = None,
        output_file: Optional[Path] = None,
    ) -> Tuple[bool, str]:
        """
        Elaborate (link) a design
        
        Args:
            top_entity: Top-level entity name
            library: Library containing top entity
            workdir: Working directory
            output_file: Output executable path
        
        Returns:
            Tuple of (success, output)
        """
        cmd = [
            "ghdl",
            "-e",  # elaborate
            f"--std={self.config.std}",
            f"--work={library}",
        ]
        
        if workdir:
            cmd.append(f"--workdir={workdir}")
        
        if output_file:
            cmd.extend(["-o", str(output_file)])
        
        cmd.extend(self.config.ghdl_flags)
        cmd.append(top_entity)
        
        try:
            result = self.run_command(cmd, timeout=120)
            success = result.returncode == 0
            output = result.stdout + result.stderr
            return success, output
        except subprocess.TimeoutExpired:
            return False, "Elaboration timed out"
        except Exception as e:
            return False, str(e)
    
    def run_simulation(
        self,
        top_entity: str,
        library: str = "work",
        workdir: Optional[Path] = None,
        stop_time: Optional[str] = None,
        waveform: Optional[Path] = None,
        generics: Optional[Dict[str, Any]] = None,
    ) -> Tuple[bool, str]:
        """
        Run simulation
        
        Args:
            top_entity: Top-level entity name
            library: Library containing top entity
            workdir: Working directory
            stop_time: Simulation stop time (e.g., "1ms")
            waveform: Output waveform file path
            generics: Generic parameter values
        
        Returns:
            Tuple of (success, output)
        """
        cmd = [
            "ghdl",
            "-r",  # run
            f"--std={self.config.std}",
            f"--work={library}",
        ]
        
        if workdir:
            cmd.append(f"--workdir={workdir}")
        
        cmd.append(top_entity)
        
        # Simulation options
        if stop_time:
            cmd.append(f"--stop-time={stop_time}")
        
        if waveform:
            if waveform.suffix == ".vcd":
                cmd.append(f"--vcd={waveform}")
            elif waveform.suffix == ".ghw":
                cmd.append(f"--wave={waveform}")
        
        # Generics
        if generics:
            for name, value in generics.items():
                cmd.append(f"-g{name}={value}")
        
        try:
            result = self.run_command(cmd, timeout=300)
            success = result.returncode == 0
            output = result.stdout + result.stderr
            return success, output
        except subprocess.TimeoutExpired:
            return False, "Simulation timed out"
        except Exception as e:
            return False, str(e)
    
    def generate_coverage_report(
        self,
        workdir: Path,
        output_file: Path,
    ) -> Tuple[bool, str]:
        """
        Generate coverage report
        
        Args:
            workdir: Working directory with coverage data
            output_file: Output report file
        
        Returns:
            Tuple of (success, message)
        """
        # GHDL generates coverage data during simulation
        # We need to process it
        
        cmd = [
            "ghdl",
            "--coverage",
            f"--workdir={workdir}",
        ]
        
        try:
            result = self.run_command(cmd, timeout=60)
            
            if result.returncode == 0:
                # Save coverage output
                output_file.parent.mkdir(parents=True, exist_ok=True)
                output_file.write_text(result.stdout)
                return True, f"Coverage report generated: {output_file}"
            else:
                return False, result.stderr
        except Exception as e:
            return False, str(e)
    
    def check_syntax(
        self,
        file_path: Path,
    ) -> Tuple[bool, List[str]]:
        """
        Check syntax of a VHDL file without full analysis
        
        Args:
            file_path: Path to VHDL file
        
        Returns:
            Tuple of (valid, list of error messages)
        """
        cmd = [
            "ghdl",
            "-s",  # syntax check
            f"--std={self.config.std}",
            str(file_path),
        ]
        
        try:
            result = self.run_command(cmd, timeout=30)
            
            if result.returncode == 0:
                return True, []
            else:
                errors = self._parse_error_messages(result.stderr)
                return False, errors
        except Exception as e:
            return False, [str(e)]
    
    def get_info(self) -> Dict[str, Any]:
        """Get comprehensive simulator information"""
        info = super().get_info()
        
        # Add GHDL-specific info
        if self._installation:
            info.update({
                "binary_path": str(self._installation.bin_path),
                "prefix": str(self._installation.prefix) if self._installation.prefix else None,
                "backend": self._installation.backend,
                "supports_coverage": self._installation.supports_coverage,
                "supports_psl": self._installation.supports_psl,
                "lib_path": str(self._installation.get_lib_path()) if self._installation.get_lib_path() else None,
            })
        
        # Add config info
        info.update({
            "vhdl_standard": self.config.std,
            "workdir": self.config.workdir,
        })
        
        return info
    
    # =========================================================================
    # PRIVATE METHODS
    # =========================================================================
    
    def _analyze_installation(self, binary: Path) -> Optional[GHDLInstallation]:
        """Analyze GHDL installation from binary path"""
        # Get version
        version = self._detect_version(binary)
        if not version:
            return None
        
        # Detect backend
        backend = self._detect_backend(binary)
        
        # Find prefix
        prefix = self._find_prefix(binary)
        
        # Check capabilities
        supports_coverage = self._check_coverage_support(binary)
        supports_psl = self._check_psl_support(binary)
        
        return GHDLInstallation(
            bin_path=binary,
            prefix=prefix,
            version=version,
            backend=backend,
            supports_coverage=supports_coverage,
            supports_psl=supports_psl,
        )
    
    def _detect_version(self, binary: Path) -> Optional[SimulatorVersion]:
        """Detect GHDL version"""
        try:
            result = subprocess.run(
                [str(binary), "--version"],
                capture_output=True,
                text=True,
                timeout=10,
            )
            
            if result.returncode != 0:
                return None
            
            return self._parse_version_string(result.stdout)
            
        except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
            return None
    
    def _parse_version_string(self, output: str) -> Optional[SimulatorVersion]:
        """
        Parse version from ghdl --version output
        
        Example outputs:
        - "GHDL 2.0.0 (mcode)"
        - "GHDL 3.0.0-dev (1.0.0.r854.g21f35626) [llvm]"
        """
        version = SimulatorVersion(full_string=output.strip())
        version.product_name = "GHDL"
        
        # Extract version numbers
        match = re.search(r'GHDL\s+(\d+)\.(\d+)(?:\.(\d+))?', output)
        if match:
            version.major = int(match.group(1))
            version.minor = int(match.group(2))
            version.patch = int(match.group(3)) if match.group(3) else 0
        
        # Extract backend
        if "mcode" in output.lower():
            version.edition = "mcode"
        elif "llvm" in output.lower():
            version.edition = "llvm"
        elif "gcc" in output.lower():
            version.edition = "gcc"
        
        return version
    
    def _detect_backend(self, binary: Path) -> str:
        """Detect GHDL backend from version output"""
        try:
            result = subprocess.run(
                [str(binary), "--version"],
                capture_output=True,
                text=True,
                timeout=10,
            )
            
            output = result.stdout.lower()
            
            if "llvm" in output:
                return "llvm"
            elif "gcc" in output:
                return "gcc"
            else:
                return "mcode"  # default
                
        except Exception:
            return "mcode"
    
    def _find_prefix(self, binary: Path) -> Optional[Path]:
        """Find GHDL_PREFIX (installation prefix)"""
        # Check environment variable first
        prefix_env = os.environ.get(self.PREFIX_ENV_VAR)
        if prefix_env:
            prefix_path = Path(prefix_env)
            if prefix_path.exists():
                return prefix_path
        
        # Try to infer from binary location
        # Binary is typically in <prefix>/bin/ghdl
        bin_dir = binary.parent
        if bin_dir.name == "bin":
            potential_prefix = bin_dir.parent
            lib_path = potential_prefix / "lib" / "ghdl"
            if lib_path.exists():
                return potential_prefix
        
        return None
    
    def _check_coverage_support(self, binary: Path) -> bool:
        """Check if GHDL supports coverage"""
        try:
            result = subprocess.run(
                [str(binary), "--help"],
                capture_output=True,
                text=True,
                timeout=10,
            )
            
            # Check if --coverage is mentioned
            return "--coverage" in result.stdout
            
        except Exception:
            return False
    
    def _check_psl_support(self, binary: Path) -> bool:
        """Check if GHDL supports PSL (Property Specification Language)"""
        try:
            result = subprocess.run(
                [str(binary), "--help"],
                capture_output=True,
                text=True,
                timeout=10,
            )
            
            # Check if PSL is mentioned
            return "psl" in result.stdout.lower()
            
        except Exception:
            return False
    
    def _parse_error_messages(self, stderr: str) -> List[str]:
        """Parse GHDL error messages from stderr"""
        errors = []
        
        for line in stderr.split('\n'):
            line = line.strip()
            if not line:
                continue
            
            # GHDL error format: file:line:col:error: message
            if ':error:' in line.lower() or ':warning:' in line.lower():
                errors.append(line)
        
        return errors
    
    def validate_for_project(self, project_config: Dict[str, Any]) -> List[str]:
        """Validate GHDL configuration for a project"""
        issues = []
        
        if not self.is_available():
            issues.append("GHDL is not available")
            return issues
        
        # Check version
        version = self.get_version()
        if version and (version.major, version.minor) < self.MIN_VERSION:
            issues.append(
                f"GHDL version {version} is old. "
                f"Version {'.'.join(map(str, self.MIN_VERSION))}+ recommended."
            )
        
        # Check language support
        language = project_config.get("language", "vhdl")
        if language != "vhdl":
            issues.append(f"GHDL only supports VHDL, not {language}")
        
        # Check VHDL standard
        if self.config.std not in self.SUPPORTED_STANDARDS:
            issues.append(
                f"VHDL standard '{self.config.std}' not in supported standards: "
                f"{', '.join(self.SUPPORTED_STANDARDS)}"
            )
        
        # Check coverage support if requested
        if project_config.get("coverage_enabled"):
            if self._installation and not self._installation.supports_coverage:
                issues.append(
                    "Coverage requested but GHDL installation doesn't support --coverage. "
                    "Rebuild GHDL with coverage support or use a pre-built package."
                )
        
        return issues


# =============================================================================
# FACTORY FUNCTION
# =============================================================================

def create_ghdl_simulator(
    config: Optional[GHDLConfig] = None,
    auto_detect: bool = True,
) -> GHDLSimulator:
    """
    Factory function to create configured GHDL simulator
    
    Args:
        config: GHDL configuration
        auto_detect: Whether to auto-detect installation
    
    Returns:
        Configured GHDLSimulator instance
    """
    simulator = GHDLSimulator(config)
    
    if auto_detect:
        simulator.detect_installation()
    
    return simulator
