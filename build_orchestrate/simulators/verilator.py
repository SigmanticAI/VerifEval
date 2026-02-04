"""
Verilator Simulator Integration
===============================

Full integration for Verilator open-source simulator.

Features:
- Auto-detection of installation
- Coverage support (--coverage)
- Waveform tracing (VCD/FST)
- CocoTB integration
- Multi-threading support

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
from ..models import VerilatorConfig, CoverageType


@dataclass
class VerilatorInstallation:
    """
    Detected Verilator installation
    
    Attributes:
        path: Installation root path (VERILATOR_ROOT)
        bin_path: Path to verilator binary
        include_path: Path to include files
        version: Detected version
        has_systemc: Whether SystemC support is available
        has_threads: Whether threading support is available
    """
    path: Optional[Path]
    bin_path: Path
    include_path: Optional[Path] = None
    version: Optional[SimulatorVersion] = None
    has_systemc: bool = False
    has_threads: bool = True


class VerilatorSimulator(BaseSimulator):
    """
    Verilator simulator integration
    
    Usage:
        config = VerilatorConfig(coverage_enabled=True)
        verilator = VerilatorSimulator(config)
        
        if verilator.is_available():
            cmd = verilator.get_compile_command(sources, top_module)
    """
    
    # Minimum recommended version
    MIN_VERSION = (4, 106)
    
    # Environment variable for installation root
    ROOT_ENV_VAR = "VERILATOR_ROOT"
    
    def __init__(self, config: Optional[VerilatorConfig] = None):
        """
        Initialize Verilator simulator
        
        Args:
            config: Verilator configuration (optional)
        """
        super().__init__()
        self.config = config or VerilatorConfig()
        self._installation: Optional[VerilatorInstallation] = None
    
    # =========================================================================
    # BASE CLASS IMPLEMENTATION
    # =========================================================================
    
    def get_name(self) -> str:
        """Get simulator name"""
        if self._installation and self._installation.version:
            return f"Verilator {self._installation.version}"
        return "Verilator"
    
    def detect_installation(self) -> bool:
        """Detect if Verilator is installed"""
        # Try explicit path first
        if self.config.path:
            installation = self._check_path(Path(self.config.path))
            if installation:
                self._installation = installation
                return True
        
        # Try VERILATOR_ROOT environment variable
        verilator_root = os.environ.get(self.ROOT_ENV_VAR)
        if verilator_root:
            installation = self._check_path(Path(verilator_root))
            if installation:
                self._installation = installation
                return True
        
        # Try to find verilator in PATH
        verilator_path = shutil.which("verilator")
        if verilator_path:
            # Get version and create installation info
            version = self._detect_version_from_binary(Path(verilator_path))
            
            # Try to find include path
            include_path = self._find_include_path(Path(verilator_path))
            
            self._installation = VerilatorInstallation(
                path=None,  # Not from VERILATOR_ROOT
                bin_path=Path(verilator_path),
                include_path=include_path,
                version=version,
                has_threads=self._check_thread_support(),
            )
            return True
        
        return False
    
    def get_version(self) -> Optional[SimulatorVersion]:
        """Get Verilator version"""
        if self._installation:
            return self._installation.version
        
        if self.detect_installation():
            return self._installation.version
        
        return None
    
    def get_capabilities(self) -> SimulatorCapabilities:
        """Get Verilator capabilities"""
        features = {
            SimulatorFeature.SYSTEMVERILOG,
            SimulatorFeature.VERILOG,
            SimulatorFeature.COVERAGE_LINE,
            SimulatorFeature.COVERAGE_TOGGLE,
            SimulatorFeature.WAVEFORM_VCD,
            SimulatorFeature.WAVEFORM_FST,
            SimulatorFeature.COCOTB_INTEGRATION,
            SimulatorFeature.PARALLEL_EXECUTION,
        }
        
        # Check version for additional features
        version = self.get_version()
        if version and version >= SimulatorVersion(major=5, minor=0):
            features.add(SimulatorFeature.COVERAGE_BRANCH)
        
        return SimulatorCapabilities(
            supported_features=features,
            max_parallel_jobs=os.cpu_count() or 4,
            vunit_simulator_name="",  # VUnit doesn't directly support Verilator
            supported_languages=["systemverilog", "verilog"],
        )
    
    def configure_vunit(self, vu: Any) -> None:
        """
        Configure VUnit for Verilator
        
        Note: VUnit doesn't natively support Verilator.
        This is a placeholder for potential future integration.
        """
        # VUnit doesn't support Verilator directly
        # For VUnit projects, we'd need a wrapper or use ModelSim mode
        pass
    
    def get_compile_options(self) -> Dict[str, List[str]]:
        """Get compilation options"""
        options = {}
        
        # Basic Verilator flags
        flags = list(self.config.verilator_flags)
        
        # Add coverage flags if enabled
        if self.config.coverage_enabled:
            flags.extend(self.get_coverage_flags())
        
        # Add trace flags if enabled
        if self.config.trace_enabled:
            flags.append("--trace")
            if self.config.trace_format == "fst":
                flags.append("--trace-fst")
        
        # Add threading
        if self.config.threads > 1:
            flags.append(f"--threads {self.config.threads}")
        
        # Optimization
        if self.config.opt_level:
            flags.append(self.config.opt_level)
        
        options["verilator_flags"] = flags
        
        return options
    
    def get_sim_options(self) -> Dict[str, List[str]]:
        """Get simulation options (runtime flags)"""
        options = {}
        
        runtime_flags = []
        
        # Coverage runtime
        if self.config.coverage_enabled:
            runtime_flags.append("+verilator+coverage")
        
        # Trace runtime
        if self.config.trace_enabled:
            runtime_flags.append("+trace")
        
        options["runtime_flags"] = runtime_flags
        
        return options
    
    # =========================================================================
    # VERILATOR-SPECIFIC METHODS
    # =========================================================================
    
    def get_installation(self) -> Optional[VerilatorInstallation]:
        """Get detected installation information"""
        if self._installation is None:
            self.detect_installation()
        return self._installation
    
    def check_license(self) -> LicenseCheckResult:
        """
        Check license - Verilator is open source
        
        Returns:
            LicenseCheckResult indicating no license required
        """
        return LicenseCheckResult(
            status=LicenseStatus.NOT_REQUIRED,
            license_type=LicenseType.UNKNOWN,
            message="Verilator is open source (LGPL) - no license required",
        )
    
    def get_environment(self) -> SimulatorEnvironment:
        """Get environment configuration for Verilator"""
        if self._environment:
            return self._environment
        
        env = SimulatorEnvironment()
        
        if self._installation:
            if self._installation.path:
                env.path = self._installation.path
                env.env_vars["VERILATOR_ROOT"] = str(self._installation.path)
            
            if self._installation.bin_path:
                env.bin_dir = self._installation.bin_path.parent
                env.path_additions = [self._installation.bin_path.parent]
            
            if self._installation.include_path:
                env.env_vars["VERILATOR_INCLUDE"] = str(self._installation.include_path)
        
        self._environment = env
        return env
    
    def get_coverage_flags(self) -> List[str]:
        """Get coverage-related compilation flags"""
        if not self.config.coverage_enabled:
            return []
        
        flags = ["--coverage"]
        
        for cov_type in self.config.coverage_types:
            if cov_type == CoverageType.LINE:
                flags.append("--coverage-line")
            elif cov_type == CoverageType.TOGGLE:
                flags.append("--coverage-toggle")
            elif cov_type == CoverageType.ALL:
                flags.extend(["--coverage-line", "--coverage-toggle"])
        
        return flags
    
    def get_compile_command(
        self,
        sources: List[Path],
        top_module: str,
        output_dir: Optional[Path] = None,
        extra_args: Optional[List[str]] = None,
    ) -> List[str]:
        """
        Build Verilator compilation command
        
        Args:
            sources: List of source files
            top_module: Top module name
            output_dir: Output directory for generated files
            extra_args: Additional arguments
        
        Returns:
            Command as list of strings
        """
        cmd = ["verilator"]
        
        # Output mode
        cmd.append("--cc")  # Generate C++
        cmd.append("--exe")  # Generate executable
        cmd.append("--build")  # Build immediately
        
        # Top module
        cmd.extend(["--top-module", top_module])
        
        # Output directory
        if output_dir:
            cmd.extend(["-Mdir", str(output_dir)])
        
        # Parallel build
        cmd.extend(["-j", str(os.cpu_count() or 4)])
        
        # Warnings
        cmd.append("-Wall")
        cmd.append("-Wno-fatal")
        
        # Coverage
        if self.config.coverage_enabled:
            cmd.extend(self.get_coverage_flags())
        
        # Trace
        if self.config.trace_enabled:
            cmd.append("--trace")
            if self.config.trace_format == "fst":
                cmd.append("--trace-fst")
            cmd.append("--trace-structs")
        
        # Timing (for Verilator 5+)
        version = self.get_version()
        if version and version.major >= 5:
            cmd.append("--timing")
        
        # Threading
        if self.config.threads > 1:
            cmd.append(f"--threads")
            cmd.append(str(self.config.threads))
        
        # Optimization
        if self.config.opt_level:
            cmd.append(self.config.opt_level)
        
        # Extra args from config
        cmd.extend(self.config.verilator_flags)
        
        # Extra args from parameter
        if extra_args:
            cmd.extend(extra_args)
        
        # Add source files
        for source in sources:
            cmd.append(str(source))
        
        return cmd
    
    def get_cocotb_compile_command(
        self,
        sources: List[Path],
        top_module: str,
        output_dir: Path,
    ) -> List[str]:
        """
        Build Verilator command for CocoTB integration
        
        Args:
            sources: List of source files
            top_module: Top module name
            output_dir: Output directory
        
        Returns:
            Command as list of strings
        """
        cmd = self.get_compile_command(
            sources=sources,
            top_module=top_module,
            output_dir=output_dir,
        )
        
        # Add CocoTB-specific flags
        cmd.append("--vpi")  # Enable VPI for CocoTB
        
        return cmd
    
    def merge_coverage(
        self,
        output_file: Path,
        input_files: List[Path],
    ) -> Tuple[bool, str]:
        """
        Merge coverage data files
        
        Args:
            output_file: Output merged file
            input_files: Input coverage files
        
        Returns:
            Tuple of (success, message)
        """
        cmd = [
            "verilator_coverage",
            "--write", str(output_file),
        ]
        
        for input_file in input_files:
            cmd.append(str(input_file))
        
        try:
            result = self.run_command(cmd, timeout=60)
            if result.returncode == 0:
                return True, f"Coverage merged to {output_file}"
            else:
                return False, result.stderr
        except Exception as e:
            return False, str(e)
    
    def generate_coverage_report(
        self,
        coverage_data: Path,
        output_dir: Path,
        format: str = "html",
    ) -> Tuple[bool, str]:
        """
        Generate coverage report
        
        Args:
            coverage_data: Coverage data file (.dat)
            output_dir: Output directory for report
            format: Report format (html, annotate, info)
        
        Returns:
            Tuple of (success, message)
        """
        output_dir.mkdir(parents=True, exist_ok=True)
        
        if format == "annotate":
            cmd = [
                "verilator_coverage",
                "--annotate", str(output_dir),
                str(coverage_data),
            ]
        elif format == "info":
            # Generate LCOV info file
            info_file = output_dir / "coverage.info"
            cmd = [
                "verilator_coverage",
                "--write-info", str(info_file),
                str(coverage_data),
            ]
        else:
            # Default: annotated source + we'll use genhtml
            annotate_dir = output_dir / "annotate"
            cmd = [
                "verilator_coverage",
                "--annotate", str(annotate_dir),
                str(coverage_data),
            ]
        
        try:
            result = self.run_command(cmd, timeout=120)
            
            if result.returncode != 0:
                return False, result.stderr
            
            # For HTML, run genhtml on the info file
            if format == "html":
                info_file = output_dir / "coverage.info"
                if info_file.exists():
                    html_cmd = [
                        "genhtml",
                        str(info_file),
                        "-o", str(output_dir / "html"),
                    ]
                    html_result = self.run_command(html_cmd, timeout=120)
                    if html_result.returncode != 0:
                        return True, f"Coverage data generated, but HTML generation failed: {html_result.stderr}"
            
            return True, f"Coverage report generated in {output_dir}"
            
        except Exception as e:
            return False, str(e)
    
    def get_info(self) -> Dict[str, Any]:
        """Get comprehensive simulator information"""
        info = super().get_info()
        
        # Add Verilator-specific info
        if self._installation:
            info.update({
                "installation_path": str(self._installation.path) if self._installation.path else None,
                "binary_path": str(self._installation.bin_path),
                "include_path": str(self._installation.include_path) if self._installation.include_path else None,
                "has_threads": self._installation.has_threads,
                "has_systemc": self._installation.has_systemc,
            })
        
        # Add config info
        info.update({
            "coverage_enabled": self.config.coverage_enabled,
            "trace_enabled": self.config.trace_enabled,
            "trace_format": self.config.trace_format,
            "threads": self.config.threads,
        })
        
        return info
    
    # =========================================================================
    # PRIVATE METHODS
    # =========================================================================
    
    def _check_path(self, install_path: Path) -> Optional[VerilatorInstallation]:
        """Check if path contains valid Verilator installation"""
        # Look for verilator binary
        bin_candidates = [
            install_path / "bin" / "verilator",
            install_path / "verilator",
        ]
        
        bin_path = None
        for candidate in bin_candidates:
            if candidate.exists() and candidate.is_file():
                bin_path = candidate
                break
        
        if not bin_path:
            return None
        
        # Get version
        version = self._detect_version_from_binary(bin_path)
        if not version:
            return None
        
        # Find include path
        include_path = self._find_include_path(bin_path)
        
        return VerilatorInstallation(
            path=install_path,
            bin_path=bin_path,
            include_path=include_path,
            version=version,
            has_threads=self._check_thread_support(),
        )
    
    def _detect_version_from_binary(self, binary: Path) -> Optional[SimulatorVersion]:
        """Detect version from verilator --version"""
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
        Parse version from verilator --version output
        
        Example outputs:
        - "Verilator 5.006 2023-01-22 rev v5.006"
        - "Verilator 4.228 2022-01-17 rev v4.228"
        """
        version = SimulatorVersion(full_string=output.strip())
        version.product_name = "Verilator"
        
        # Extract version numbers
        match = re.search(r'Verilator\s+(\d+)\.(\d+)', output)
        if match:
            version.major = int(match.group(1))
            version.minor = int(match.group(2))
        
        return version
    
    def _find_include_path(self, binary: Path) -> Optional[Path]:
        """Find Verilator include directory"""
        # Common locations relative to binary
        candidates = [
            binary.parent.parent / "include",
            binary.parent.parent / "share" / "verilator" / "include",
            Path("/usr/share/verilator/include"),
            Path("/usr/local/share/verilator/include"),
        ]
        
        # Also try VERILATOR_ROOT
        verilator_root = os.environ.get("VERILATOR_ROOT")
        if verilator_root:
            candidates.insert(0, Path(verilator_root) / "include")
        
        for candidate in candidates:
            if candidate.exists() and (candidate / "verilated.h").exists():
                return candidate
        
        return None
    
    def _check_thread_support(self) -> bool:
        """Check if Verilator was built with thread support"""
        # Try compiling with --threads to see if it's supported
        # For now, assume modern Verilator has thread support
        version = self.get_version()
        if version and version.major >= 4:
            return True
        return False
    
    def validate_for_project(self, project_config: Dict[str, Any]) -> List[str]:
        """Validate Verilator configuration for a project"""
        issues = []
        
        if not self.is_available():
            issues.append("Verilator is not available")
            return issues
        
        # Check version
        version = self.get_version()
        if version and (version.major, version.minor) < self.MIN_VERSION:
            issues.append(
                f"Verilator version {version} is old. "
                f"Version {'.'.join(map(str, self.MIN_VERSION))}+ recommended."
            )
        
        # Check language support
        language = project_config.get("language", "systemverilog")
        if language == "vhdl":
            issues.append("Verilator does not support VHDL. Use GHDL instead.")
        
        # Check UVM support
        if project_config.get("tb_type") == "uvm_sv":
            issues.append(
                "Verilator has limited UVM support. "
                "Full UVM requires commercial simulator (Questa, VCS, Xcelium)."
            )
        
        return issues


# =============================================================================
# FACTORY FUNCTION
# =============================================================================

def create_verilator_simulator(
    config: Optional[VerilatorConfig] = None,
    auto_detect: bool = True,
) -> VerilatorSimulator:
    """
    Factory function to create configured Verilator simulator
    
    Args:
        config: Verilator configuration
        auto_detect: Whether to auto-detect installation
    
    Returns:
        Configured VerilatorSimulator instance
    """
    simulator = VerilatorSimulator(config)
    
    if auto_detect:
        simulator.detect_installation()
    
    return simulator
