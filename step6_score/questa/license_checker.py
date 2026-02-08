"""
Questa license and tool availability checker

This module detects:
- Questa tool availability (vcover, qverify, vsim)
- License validity
- Tool versions
- Available features (functional coverage, assertions, UVM)

Used to automatically determine scoring tier:
- Tier 1 (open-source): No Questa
- Tier 2 (professional): Questa available

Author: TB Eval Team
Version: 0.1.0
"""

import os
import subprocess
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Dict, List, Tuple
import logging
import re

logger = logging.getLogger(__name__)


# =============================================================================
# DATA MODELS
# =============================================================================

@dataclass
class QuestaToolInfo:
    """
    Information about a Questa tool
    
    Attributes:
        name: Tool name (vcover, qverify, vsim)
        available: Whether tool is available
        path: Full path to tool executable
        version: Tool version string
        license_valid: Whether license is valid for this tool
    """
    name: str
    available: bool
    path: Optional[str] = None
    version: Optional[str] = None
    license_valid: bool = False
    
    def to_dict(self) -> Dict:
        """Serialize to dictionary"""
        return {
            "name": self.name,
            "available": self.available,
            "path": self.path,
            "version": self.version,
            "license_valid": self.license_valid,
        }


@dataclass
class QuestaCapabilities:
    """
    Complete Questa capabilities report
    
    Attributes:
        questa_available: Whether any Questa tools are available
        license_valid: Whether license is valid
        vcover: vcover tool info
        qverify: qverify tool info
        vsim: vsim tool info
        functional_coverage: Functional coverage available
        assertion_coverage: Assertion coverage available
        uvm_support: UVM support available
        questa_version: Overall Questa version
        license_type: License type (node-locked, floating, etc.)
    """
    questa_available: bool
    license_valid: bool
    
    # Tool availability
    vcover: QuestaToolInfo
    qverify: QuestaToolInfo
    vsim: QuestaToolInfo
    
    # Feature availability
    functional_coverage: bool
    assertion_coverage: bool
    uvm_support: bool
    
    # Version info
    questa_version: Optional[str] = None
    license_type: Optional[str] = None
    
    @property
    def tier2_available(self) -> bool:
        """Check if Tier 2 (professional) scoring is available"""
        return (
            self.questa_available and
            self.license_valid and
            self.vcover.available
        )
    
    def to_dict(self) -> Dict:
        """Serialize to dictionary"""
        return {
            "questa_available": self.questa_available,
            "license_valid": self.license_valid,
            "tier2_available": self.tier2_available,
            
            "tools": {
                "vcover": self.vcover.to_dict(),
                "qverify": self.qverify.to_dict(),
                "vsim": self.vsim.to_dict(),
            },
            
            "features": {
                "functional_coverage": self.functional_coverage,
                "assertion_coverage": self.assertion_coverage,
                "uvm_support": self.uvm_support,
            },
            
            "version": self.questa_version,
            "license_type": self.license_type,
        }


# =============================================================================
# LICENSE CHECKER
# =============================================================================

class QuestaLicenseChecker:
    """
    Check Questa license and tool availability
    
    This class handles:
    - Tool detection (vcover, qverify, vsim)
    - License validation
    - Version checking
    - Feature detection
    - Result caching
    """
    
    def __init__(self, config: Optional['QuestaConfig'] = None):
        """
        Initialize license checker
        
        Args:
            config: Questa configuration (optional)
        """
        self.config = config
        self._cached_result: Optional[QuestaCapabilities] = None
    
    def check_availability(self, force_check: bool = False) -> QuestaCapabilities:
        """
        Check Questa availability and capabilities
        
        Args:
            force_check: Force re-check (ignore cache)
        
        Returns:
            QuestaCapabilities with complete availability info
        """
        # Return cached result if available
        if self._cached_result and not force_check:
            logger.debug("Returning cached Questa availability result")
            return self._cached_result
        
        logger.info("Checking Questa availability...")
        
        # Check each tool
        vcover_info = self._check_tool("vcover")
        qverify_info = self._check_tool("qverify")
        vsim_info = self._check_tool("vsim")
        
        # Determine overall availability
        questa_available = any([
            vcover_info.available,
            qverify_info.available,
            vsim_info.available,
        ])
        
        # Check license
        license_valid = False
        license_type = None
        if questa_available:
            license_valid, license_type = self._check_license()
        
        # Detect Questa version
        questa_version = None
        if vsim_info.version:
            questa_version = self._parse_questa_version(vsim_info.version)
        
        # Feature detection
        functional_coverage = vcover_info.available and license_valid
        assertion_coverage = vsim_info.available and license_valid
        uvm_support = vsim_info.available and license_valid
        
        # Build capabilities report
        capabilities = QuestaCapabilities(
            questa_available=questa_available,
            license_valid=license_valid,
            vcover=vcover_info,
            qverify=qverify_info,
            vsim=vsim_info,
            functional_coverage=functional_coverage,
            assertion_coverage=assertion_coverage,
            uvm_support=uvm_support,
            questa_version=questa_version,
            license_type=license_type,
        )
        
        # Cache result
        self._cached_result = capabilities
        
        # Log summary
        if capabilities.tier2_available:
            logger.info("✓ Questa available - Tier 2 (professional) scoring enabled")
        else:
            logger.info("✗ Questa not available - Using Tier 1 (open-source) scoring")
        
        return capabilities
    
    def _check_tool(self, tool_name: str) -> QuestaToolInfo:
        """
        Check if a specific Questa tool is available
        
        Args:
            tool_name: Tool name (vcover, qverify, vsim)
        
        Returns:
            QuestaToolInfo with availability details
        """
        # Check if tool path is configured
        if self.config:
            if tool_name == "vcover" and self.config.vcover_path:
                tool_path = str(self.config.vcover_path)
            elif tool_name == "qverify" and self.config.qverify_path:
                tool_path = str(self.config.qverify_path)
            else:
                tool_path = None
        else:
            tool_path = None
        
        # Try to find tool in PATH if not configured
        if not tool_path:
            tool_path = shutil.which(tool_name)
        
        if not tool_path:
            logger.debug(f"{tool_name} not found in PATH")
            return QuestaToolInfo(
                name=tool_name,
                available=False,
            )
        
        # Try to get version
        version = self._get_tool_version(tool_name, tool_path)
        
        # Check if tool actually works (can run -version)
        available = version is not None
        
        # Check license for this tool
        license_valid = False
        if available:
            license_valid = self._check_tool_license(tool_name, tool_path)
        
        return QuestaToolInfo(
            name=tool_name,
            available=available,
            path=tool_path,
            version=version,
            license_valid=license_valid,
        )
    
    def _get_tool_version(self, tool_name: str, tool_path: str) -> Optional[str]:
        """
        Get tool version by running tool -version
        
        Args:
            tool_name: Tool name
            tool_path: Path to tool executable
        
        Returns:
            Version string or None if failed
        """
        try:
            result = subprocess.run(
                [tool_path, "-version"],
                capture_output=True,
                text=True,
                timeout=5,
                env=self._get_questa_env()
            )
            
            if result.returncode == 0:
                # Parse version from output
                # Example: "Model Technology ModelSim DE vsim 2020.1 Simulator 2020.02 Feb 28 2020"
                version_match = re.search(r'vsim\s+([\d.]+)', result.stdout)
                if version_match:
                    return version_match.group(1)
                
                # Fallback: return first line
                lines = result.stdout.strip().split('\n')
                if lines:
                    return lines[0]
            
            return None
        
        except (subprocess.TimeoutExpired, FileNotFoundError, OSError) as e:
            logger.debug(f"Failed to get {tool_name} version: {e}")
            return None
    
    def _check_tool_license(self, tool_name: str, tool_path: str) -> bool:
        """
        Check if tool has valid license
        
        Args:
            tool_name: Tool name
            tool_path: Path to tool
        
        Returns:
            True if license is valid
        """
        # For most Questa tools, if -version works, license is OK
        # More thorough check would involve running tool with actual operation
        
        if tool_name == "vcover":
            # Try to run vcover with minimal operation
            try:
                result = subprocess.run(
                    [tool_path, "-help"],
                    capture_output=True,
                    text=True,
                    timeout=5,
                    env=self._get_questa_env()
                )
                
                # Check for license errors in output
                if "license" in result.stderr.lower() and "error" in result.stderr.lower():
                    return False
                
                return result.returncode == 0
            
            except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
                return False
        
        # For other tools, assume license is OK if version check passed
        return True
    
    def _check_license(self) -> Tuple[bool, Optional[str]]:
        """
        Check overall Questa license validity
        
        Returns:
            Tuple of (license_valid, license_type)
        """
        # Check for license environment variables
        license_file = os.environ.get("LM_LICENSE_FILE")
        mgc_license = os.environ.get("MGLS_LICENSE_FILE")
        
        if license_file or mgc_license:
            logger.debug(f"License file configured: {license_file or mgc_license}")
            # Assume license is valid if env var is set
            # More thorough check would query license server
            return True, "floating"
        
        # Check for QUESTA_HOME
        questa_home = os.environ.get("QUESTA_HOME") or os.environ.get("MODEL_TECH")
        if questa_home:
            logger.debug(f"QUESTA_HOME: {questa_home}")
            # Check for license file in Questa installation
            license_path = Path(questa_home) / "license.dat"
            if license_path.exists():
                return True, "node-locked"
        
        # If tools are available but no license env vars, might be demo/free version
        logger.debug("No license configuration found, but tools may work")
        return True, "unknown"
    
    def _parse_questa_version(self, version_string: str) -> str:
        """
        Parse Questa version from version string
        
        Args:
            version_string: Version string from tool
        
        Returns:
            Cleaned version string
        """
        # Extract version number (e.g., "2020.1" from full string)
        match = re.search(r'([\d]+\.[\d]+)', version_string)
        if match:
            return match.group(1)
        return version_string
    
    def _get_questa_env(self) -> Dict[str, str]:
        """
        Get environment variables for Questa tools
        
        Returns:
            Dictionary of environment variables
        """
        env = os.environ.copy()
        
        # Add QUESTA_HOME to PATH if configured
        questa_home = os.environ.get("QUESTA_HOME")
        if questa_home:
            bin_path = Path(questa_home) / "bin"
            if bin_path.exists():
                env["PATH"] = f"{bin_path}:{env.get('PATH', '')}"
        
        return env


# =============================================================================
# CONVENIENCE FUNCTIONS
# =============================================================================

def check_questa_availability(config: Optional['QuestaConfig'] = None) -> QuestaCapabilities:
    """
    Convenience function to check Questa availability
    
    Args:
        config: Questa configuration (optional)
    
    Returns:
        QuestaCapabilities report
    
    Example:
        >>> capabilities = check_questa_availability()
        >>> if capabilities.tier2_available:
        ...     print("Using Tier 2 scoring")
    """
    checker = QuestaLicenseChecker(config)
    return checker.check_availability()


def is_questa_available(config: Optional['QuestaConfig'] = None) -> bool:
    """
    Quick check if Questa is available
    
    Args:
        config: Questa configuration (optional)
    
    Returns:
        True if Questa is available
    
    Example:
        >>> if is_questa_available():
        ...     # Use Tier 2 scoring
    """
    capabilities = check_questa_availability(config)
    return capabilities.questa_available


def is_tier2_available(config: Optional['QuestaConfig'] = None) -> bool:
    """
    Check if Tier 2 (professional) scoring is available
    
    Args:
        config: Questa configuration (optional)
    
    Returns:
        True if Tier 2 scoring can be used
    
    Example:
        >>> if is_tier2_available():
        ...     tier = ScoringTier.PROFESSIONAL
        ... else:
        ...     tier = ScoringTier.OPEN_SOURCE
    """
    capabilities = check_questa_availability(config)
    return capabilities.tier2_available


def get_questa_version(config: Optional['QuestaConfig'] = None) -> Optional[str]:
    """
    Get Questa version string
    
    Args:
        config: Questa configuration (optional)
    
    Returns:
        Version string or None if not available
    """
    capabilities = check_questa_availability(config)
    return capabilities.questa_version


def print_questa_status(config: Optional['QuestaConfig'] = None) -> None:
    """
    Print Questa availability status (for CLI --doctor command)
    
    Args:
        config: Questa configuration (optional)
    """
    capabilities = check_questa_availability(config)
    
    print("\n" + "=" * 60)
    print("QUESTA AVAILABILITY CHECK")
    print("=" * 60)
    
    print(f"\nOverall Status:")
    print(f"  Questa Available: {'✓ YES' if capabilities.questa_available else '✗ NO'}")
    print(f"  License Valid:    {'✓ YES' if capabilities.license_valid else '✗ NO'}")
    print(f"  Tier 2 Scoring:   {'✓ ENABLED' if capabilities.tier2_available else '✗ DISABLED'}")
    
    if capabilities.questa_version:
        print(f"  Questa Version:   {capabilities.questa_version}")
    
    if capabilities.license_type:
        print(f"  License Type:     {capabilities.license_type}")
    
    print(f"\nTools:")
    for tool_name in ["vcover", "qverify", "vsim"]:
        tool = getattr(capabilities, tool_name)
        status = "✓" if tool.available else "✗"
        print(f"  {status} {tool_name:10s}", end="")
        
        if tool.available:
            print(f"  {tool.path}")
            if tool.version:
                print(f"     Version: {tool.version}")
        else:
            print("  Not found")
    
    print(f"\nFeatures:")
    print(f"  {'✓' if capabilities.functional_coverage else '✗'} Functional Coverage")
    print(f"  {'✓' if capabilities.assertion_coverage else '✗'} Assertion Coverage")
    print(f"  {'✓' if capabilities.uvm_support else '✗'} UVM Support")
    
    print("\n" + "=" * 60)
    
    if not capabilities.tier2_available:
        print("\nℹ️  Tier 2 (professional) scoring requires:")
        print("   - Questa Sim/ModelSim installation")
        print("   - Valid license (LM_LICENSE_FILE or MGLS_LICENSE_FILE)")
        print("   - vcover tool available in PATH")
        print("\nℹ️  Falling back to Tier 1 (open-source) scoring with Verilator")
    
    print()


# =============================================================================
# EXAMPLE USAGE
# =============================================================================

if __name__ == "__main__":
    # Example: Check Questa availability
    import sys
    
    # Setup logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(levelname)s - %(message)s'
    )
    
    # Check availability
    print_questa_status()
    
    # Get capabilities
    caps = check_questa_availability()
    
    # Print JSON summary
    import json
    print("\nJSON Summary:")
    print(json.dumps(caps.to_dict(), indent=2))
    
    # Determine tier
    if caps.tier2_available:
        print("\n✓ Use Tier 2 (professional) scoring")
        sys.exit(0)
    else:
        print("\n✗ Use Tier 1 (open-source) scoring")
        sys.exit(1)
