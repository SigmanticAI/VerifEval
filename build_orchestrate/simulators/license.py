"""
License Management for Commercial Simulators
============================================

Handles license detection, validation, and configuration for:
- FlexLM-based licenses (Questa, VCS, etc.)
- Node-locked licenses
- License files
- License servers

Author: TB Eval Team
Version: 0.1.0
"""

import os
import re
import socket
import subprocess
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Optional, List, Dict, Any, Tuple
from datetime import datetime, date


class LicenseType(Enum):
    """Types of licenses"""
    FLEXLM_SERVER = "flexlm_server"      # FlexLM floating license
    NODE_LOCKED = "node_locked"           # Node-locked to machine
    LICENSE_FILE = "license_file"         # License file
    EVALUATION = "evaluation"             # Evaluation/trial license
    UNKNOWN = "unknown"


class LicenseStatus(Enum):
    """License validation status"""
    VALID = "valid"
    EXPIRED = "expired"
    NOT_FOUND = "not_found"
    SERVER_UNREACHABLE = "server_unreachable"
    INSUFFICIENT_LICENSES = "insufficient_licenses"
    INVALID_HOST = "invalid_host"
    CHECKOUT_FAILED = "checkout_failed"
    UNKNOWN = "unknown"
    NOT_REQUIRED = "not_required"  # For open-source tools


@dataclass
class LicenseFeature:
    """
    A single licensed feature
    
    Attributes:
        name: Feature name (e.g., "msimhdlsim", "questa_sv")
        version: Feature version
        available: Number of licenses available
        used: Number of licenses in use
        expiration: Expiration date
    """
    name: str
    version: str = ""
    available: int = 0
    used: int = 0
    expiration: Optional[date] = None
    
    def is_available(self) -> bool:
        """Check if feature has available licenses"""
        return self.available > self.used
    
    def is_expired(self) -> bool:
        """Check if feature is expired"""
        if self.expiration is None:
            return False
        return date.today() > self.expiration


@dataclass
class LicenseCheckResult:
    """
    Result of license validation
    
    Attributes:
        status: Overall license status
        license_type: Type of license detected
        message: Human-readable status message
        server: License server (if applicable)
        file_path: License file path (if applicable)
        features: Available license features
        expiration: Earliest expiration date
        host_id: Host ID for node-locked licenses
        errors: List of errors encountered
        warnings: List of warnings
    """
    status: LicenseStatus = LicenseStatus.UNKNOWN
    license_type: LicenseType = LicenseType.UNKNOWN
    message: str = ""
    server: Optional[str] = None
    file_path: Optional[str] = None
    features: List[LicenseFeature] = field(default_factory=list)
    expiration: Optional[date] = None
    host_id: Optional[str] = None
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    
    def is_valid(self) -> bool:
        """Check if license is valid for use"""
        return self.status in [LicenseStatus.VALID, LicenseStatus.NOT_REQUIRED]
    
    def has_feature(self, feature_name: str) -> bool:
        """Check if a specific feature is licensed"""
        return any(f.name == feature_name and f.is_available() for f in self.features)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "status": self.status.value,
            "license_type": self.license_type.value,
            "message": self.message,
            "server": self.server,
            "file_path": self.file_path,
            "features": [
                {
                    "name": f.name,
                    "version": f.version,
                    "available": f.available,
                    "used": f.used,
                    "expiration": str(f.expiration) if f.expiration else None,
                }
                for f in self.features
            ],
            "expiration": str(self.expiration) if self.expiration else None,
            "host_id": self.host_id,
            "errors": self.errors,
            "warnings": self.warnings,
        }


class FlexLMLicenseChecker:
    """
    FlexLM license checker for Mentor/Siemens tools
    
    Handles:
    - License server connectivity
    - Feature availability
    - License expiration
    """
    
    # Common Questa/ModelSim FlexLM features
    QUESTA_FEATURES = [
        "msimhdlsim",           # ModelSim HDL simulator
        "msimhdlmix",           # ModelSim mixed language
        "qhsimvh",              # Questa VHDL
        "qhsimvlog",            # Questa Verilog
        "qhsimsv",              # Questa SystemVerilog
        "qhsim",                # Questa simulator
        "questa_sv",            # Questa SystemVerilog
        "questa_vlog",          # Questa Verilog
        "questa_vhdl",          # Questa VHDL
        "questa_core",          # Questa core
        "msimpe",               # ModelSim PE
        "qverify_uvm",          # UVM verification
    ]
    
    def __init__(self, license_source: str):
        """
        Initialize license checker
        
        Args:
            license_source: License server (port@host) or file path
        """
        self.license_source = license_source
        self.is_server = "@" in license_source
    
    def check_license(self) -> LicenseCheckResult:
        """
        Check license status
        
        Returns:
            LicenseCheckResult with validation details
        """
        if self.is_server:
            return self._check_server_license()
        else:
            return self._check_file_license()
    
    def _check_server_license(self) -> LicenseCheckResult:
        """Check license server connectivity and features"""
        result = LicenseCheckResult(
            license_type=LicenseType.FLEXLM_SERVER,
            server=self.license_source
        )
        
        # Parse server string (port@host or just host)
        try:
            if "@" in self.license_source:
                parts = self.license_source.split("@")
                port = int(parts[0]) if parts[0].isdigit() else 27000
                host = parts[1] if len(parts) > 1 else parts[0]
            else:
                host = self.license_source
                port = 27000
        except Exception as e:
            result.status = LicenseStatus.NOT_FOUND
            result.message = f"Invalid license server format: {self.license_source}"
            result.errors.append(str(e))
            return result
        
        # Check server connectivity
        if not self._check_server_reachable(host, port):
            result.status = LicenseStatus.SERVER_UNREACHABLE
            result.message = f"Cannot reach license server: {host}:{port}"
            result.errors.append("License server is not reachable")
            return result
        
        # Try to query features using lmstat (if available)
        features = self._query_features_lmstat()
        if features:
            result.features = features
            
            # Check if any required features are available
            available_features = [f for f in features if f.is_available()]
            if available_features:
                result.status = LicenseStatus.VALID
                result.message = f"License server OK - {len(available_features)} features available"
                
                # Find earliest expiration
                expirations = [f.expiration for f in features if f.expiration]
                if expirations:
                    result.expiration = min(expirations)
            else:
                result.status = LicenseStatus.INSUFFICIENT_LICENSES
                result.message = "No available license features"
        else:
            # Couldn't query features, but server is reachable
            result.status = LicenseStatus.VALID
            result.message = f"License server reachable: {host}:{port}"
            result.warnings.append("Could not query license features (lmstat not available)")
        
        return result
    
    def _check_file_license(self) -> LicenseCheckResult:
        """Check license file"""
        result = LicenseCheckResult(
            license_type=LicenseType.LICENSE_FILE,
            file_path=self.license_source
        )
        
        file_path = Path(self.license_source)
        
        if not file_path.exists():
            result.status = LicenseStatus.NOT_FOUND
            result.message = f"License file not found: {self.license_source}"
            result.errors.append("File does not exist")
            return result
        
        # Parse license file
        try:
            features, host_id, expiration = self._parse_license_file(file_path)
            result.features = features
            result.host_id = host_id
            result.expiration = expiration
            
            # Check expiration
            if expiration and date.today() > expiration:
                result.status = LicenseStatus.EXPIRED
                result.message = f"License expired on {expiration}"
            else:
                result.status = LicenseStatus.VALID
                result.message = f"License file valid - {len(features)} features"
                
        except Exception as e:
            result.status = LicenseStatus.UNKNOWN
            result.message = f"Error parsing license file: {str(e)}"
            result.errors.append(str(e))
        
        return result
    
    def _check_server_reachable(self, host: str, port: int, timeout: int = 5) -> bool:
        """Check if license server is reachable"""
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(timeout)
            result = sock.connect_ex((host, port))
            sock.close()
            return result == 0
        except Exception:
            return False
    
    def _query_features_lmstat(self) -> List[LicenseFeature]:
        """Query license features using lmstat"""
        features = []
        
        # Try to find lmstat
        lmstat_paths = [
            "lmstat",
            "/opt/mentor/licensing/lmstat",
            "/opt/flexlm/lmstat",
        ]
        
        lmstat_cmd = None
        for path in lmstat_paths:
            try:
                subprocess.run([path, "-v"], capture_output=True, timeout=5)
                lmstat_cmd = path
                break
            except (FileNotFoundError, subprocess.TimeoutExpired):
                continue
        
        if not lmstat_cmd:
            return features
        
        # Query all features
        try:
            result = subprocess.run(
                [lmstat_cmd, "-a", "-c", self.license_source],
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode == 0:
                features = self._parse_lmstat_output(result.stdout)
                
        except Exception:
            pass
        
        return features
    
    def _parse_lmstat_output(self, output: str) -> List[LicenseFeature]:
        """Parse lmstat -a output"""
        features = []
        
        # Pattern: Users of featurename:  (Total of X licenses issued;  Y currently in use)
        pattern = r'Users of (\w+):\s+\(Total of (\d+) licenses? issued;\s*(\d+) currently in use'
        
        for match in re.finditer(pattern, output):
            feature_name = match.group(1)
            total = int(match.group(2))
            used = int(match.group(3))
            
            features.append(LicenseFeature(
                name=feature_name,
                available=total,
                used=used,
            ))
        
        return features
    
    def _parse_license_file(
        self,
        file_path: Path
    ) -> Tuple[List[LicenseFeature], Optional[str], Optional[date]]:
        """Parse FlexLM license file"""
        features = []
        host_id = None
        earliest_expiration = None
        
        content = file_path.read_text(errors='ignore')
        
        # Find HOST line
        host_match = re.search(r'SERVER\s+\S+\s+(\w+)', content)
        if host_match:
            host_id = host_match.group(1)
        
        # Find FEATURE/INCREMENT lines
        feature_pattern = r'(?:FEATURE|INCREMENT)\s+(\w+)\s+\S+\s+(\S+)\s+(\d+)'
        
        for match in re.finditer(feature_pattern, content):
            feature_name = match.group(1)
            exp_str = match.group(2)
            count = int(match.group(3))
            
            # Parse expiration
            expiration = None
            if exp_str not in ["permanent", "0"]:
                try:
                    # Format: dd-mmm-yyyy or yyyy.mmdd
                    if "-" in exp_str:
                        expiration = datetime.strptime(exp_str, "%d-%b-%Y").date()
                    elif "." in exp_str:
                        expiration = datetime.strptime(exp_str, "%Y.%m%d").date()
                except ValueError:
                    pass
            
            features.append(LicenseFeature(
                name=feature_name,
                available=count,
                used=0,
                expiration=expiration,
            ))
            
            if expiration:
                if earliest_expiration is None or expiration < earliest_expiration:
                    earliest_expiration = expiration
        
        return features, host_id, earliest_expiration


class LicenseManager:
    """
    High-level license management
    
    Handles:
    - Auto-detection of license configuration
    - Multiple license source support
    - License validation and caching
    """
    
    # Environment variables to check for licenses
    LICENSE_ENV_VARS = [
        "LM_LICENSE_FILE",
        "MGLS_LICENSE_FILE",
        "MLM_LICENSE_FILE",
        "SNPSLMD_LICENSE_FILE",
        "MENTOR_LICENSE_FILE",
    ]
    
    # Common license file locations
    LICENSE_FILE_PATHS = [
        Path.home() / "license.dat",
        Path.home() / ".mentor" / "license.dat",
        Path("/opt/mentor/license.dat"),
        Path("/opt/licenses/mentor.dat"),
    ]
    
    def __init__(self):
        self._cached_result: Optional[LicenseCheckResult] = None
    
    def detect_license(
        self,
        explicit_source: Optional[str] = None
    ) -> LicenseCheckResult:
        """
        Detect and validate license
        
        Args:
            explicit_source: Explicit license source (overrides auto-detection)
        
        Returns:
            LicenseCheckResult with validation details
        
        Detection order:
        1. Explicit source parameter
        2. Environment variables
        3. Common file locations
        """
        # Try explicit source first
        if explicit_source:
            return self._check_source(explicit_source)
        
        # Try environment variables
        for env_var in self.LICENSE_ENV_VARS:
            value = os.environ.get(env_var)
            if value:
                result = self._check_source(value)
                if result.is_valid():
                    return result
        
        # Try common file locations
        for file_path in self.LICENSE_FILE_PATHS:
            if file_path.exists():
                result = self._check_source(str(file_path))
                if result.is_valid():
                    return result
        
        # No license found
        return LicenseCheckResult(
            status=LicenseStatus.NOT_FOUND,
            message="No license configuration found. "
                   "Set LM_LICENSE_FILE environment variable or provide license in .tbeval.yaml",
            errors=["License not found in environment or common locations"]
        )
    
    def _check_source(self, source: str) -> LicenseCheckResult:
        """Check a single license source"""
        # Handle multiple sources (colon-separated)
        sources = source.split(os.pathsep) if os.pathsep in source else [source]
        
        all_features = []
        best_result = None
        
        for src in sources:
            src = src.strip()
            if not src:
                continue
            
            checker = FlexLMLicenseChecker(src)
            result = checker.check_license()
            
            if result.is_valid():
                all_features.extend(result.features)
                if best_result is None:
                    best_result = result
        
        if best_result:
            # Merge features from all sources
            best_result.features = all_features
            return best_result
        
        # Return last result (which should have error info)
        return result if 'result' in dir() else LicenseCheckResult(
            status=LicenseStatus.NOT_FOUND,
            message=f"Could not validate license: {source}"
        )
    
    def configure_environment(
        self,
        license_result: LicenseCheckResult
    ) -> Dict[str, str]:
        """
        Get environment variables to configure for license
        
        Args:
            license_result: License check result
        
        Returns:
            Dictionary of environment variables to set
        """
        env_vars = {}
        
        if license_result.server:
            env_vars["LM_LICENSE_FILE"] = license_result.server
            env_vars["MGLS_LICENSE_FILE"] = license_result.server
        elif license_result.file_path:
            env_vars["LM_LICENSE_FILE"] = license_result.file_path
            env_vars["MGLS_LICENSE_FILE"] = license_result.file_path
        
        return env_vars
    
    def get_license_summary(self, result: LicenseCheckResult) -> str:
        """Get human-readable license summary"""
        lines = []
        
        lines.append(f"License Status: {result.status.value.upper()}")
        lines.append(f"Type: {result.license_type.value}")
        
        if result.server:
            lines.append(f"Server: {result.server}")
        if result.file_path:
            lines.append(f"File: {result.file_path}")
        
        if result.features:
            lines.append(f"\nAvailable Features ({len(result.features)}):")
            for feature in result.features[:10]:  # Show first 10
                avail = feature.available - feature.used
                lines.append(f"  - {feature.name}: {avail}/{feature.available}")
            if len(result.features) > 10:
                lines.append(f"  ... and {len(result.features) - 10} more")
        
        if result.expiration:
            lines.append(f"\nExpiration: {result.expiration}")
        
        if result.errors:
            lines.append(f"\nErrors:")
            for error in result.errors:
                lines.append(f"  - {error}")
        
        if result.warnings:
            lines.append(f"\nWarnings:")
            for warning in result.warnings:
                lines.append(f"  - {warning}")
        
        return "\n".join(lines)
