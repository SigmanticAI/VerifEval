"""
Data models for classification and routing
"""
from dataclasses import dataclass, field, asdict
from enum import Enum
from typing import List, Optional, Dict, Any
from datetime import datetime


class TBType(Enum):
    """Supported testbench types"""
    COCOTB = "cocotb"
    PYUVM = "pyuvm"
    UVM_SV = "uvm_sv"
    VUNIT = "vunit"
    SYSTEMVERILOG = "systemverilog"
    VHDL = "vhdl"
    UNKNOWN = "unknown"


class Track(Enum):
    """Execution tracks"""
    A = "A"  # CocoTB/PyUVM (Python)
    B = "B"  # VUnit/SV/VHDL (HDL with orchestration)
    C = "C"  # Commercial simulator required


class Simulator(Enum):
    """Supported simulators"""
    VERILATOR = "verilator"
    ICARUS = "icarus"
    GHDL = "ghdl"
    QUESTA = "questa"
    COMMERCIAL_REQUIRED = "commercial_required"
    AUTO = "auto"


class Language(Enum):
    """HDL Languages"""
    SYSTEMVERILOG = "systemverilog"
    VERILOG = "verilog"
    VHDL = "vhdl"
    PYTHON = "python"
    MIXED = "mixed"


class QualityStatus(Enum):
    """Quality gate status"""
    PASS = "pass"
    WARNING = "warning"
    FAIL = "fail"
    SKIPPED = "skipped"


@dataclass
class Violation:
    """Single linting/quality violation"""
    file: str
    line: int
    column: int
    severity: str  # error, warning, info
    rule: str
    message: str
    suggestion: Optional[str] = None


@dataclass
class FileQualityReport:
    """Quality report for a single file"""
    path: str
    status: str
    violations: List[Violation] = field(default_factory=list)
    
    @property
    def error_count(self) -> int:
        return sum(1 for v in self.violations if v.severity == "error")
    
    @property
    def warning_count(self) -> int:
        return sum(1 for v in self.violations if v.severity == "warning")


@dataclass
class QualityReport:
    """Complete quality gate report"""
    status: str
    linter: str
    timestamp: str
    total_files: int
    files_checked: int
    total_violations: int
    critical_errors: int
    warnings: int
    style_issues: int
    files: List[FileQualityReport] = field(default_factory=list)
    violations_by_category: Dict[str, int] = field(default_factory=dict)
    execution_time_ms: float = 0.0
    
    def has_critical_errors(self) -> bool:
        return self.critical_errors > 0
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class DetectionResult:
    """Result from a testbench detector"""
    tb_type: TBType
    confidence: float
    files_detected: List[str]
    detection_method: str
    language: Language
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class RoutingDecision:
    """Final routing decision output"""
    # Core routing info
    tb_type: str
    track: str
    entrypoint: str
    chosen_simulator: str
    language: str
    confidence: float
    detection_method: str
    
    # File lists
    dut_files: List[str] = field(default_factory=list)
    tb_files: List[str] = field(default_factory=list)
    top_module: Optional[str] = None
    
    # Quality gate results
    quality_gate_passed: bool = True
    quality_metrics: Optional[Dict[str, Any]] = None
    
    # Recommendations and warnings
    recommendations: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    
    # Metadata
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    framework_version: str = "1.0.0"
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
    
    def is_valid(self) -> bool:
        """Check if routing decision is valid for execution"""
        return (
            self.tb_type != TBType.UNKNOWN.value
            and len(self.dut_files) > 0
            and len(self.tb_files) > 0
            and self.quality_gate_passed
            and len(self.errors) == 0
        )


@dataclass  
class ProjectConfig:
    """Project-level configuration"""
    project_name: str = "unnamed_project"
    
    # Quality gate config
    quality_gate_mode: str = "advisory"  # blocking, advisory, disabled
    fail_on_critical_errors: bool = True
    fail_on_syntax_errors: bool = True
    fail_on_lint_warnings: bool = False
    fail_on_style_issues: bool = False
    
    # Linter config
    verible_rules_file: Optional[str] = None
    verible_waiver_file: Optional[str] = None
    
    # Detection preferences
    preferred_simulator: Optional[str] = None
    enable_uvm_detection: bool = True

    #Questa-specific settings 
    questa_path: Optional[str] = None           # ← NEW: Path to Questa installation
    questa_license_server: Optional[str] = None # ← NEW: License server (if needed)
    questa_args: List[str] = field(default_factory=list) # ← NEW: Extra vsim args
    # File patterns
    dut_directories: List[str] = field(default_factory=lambda: ["rtl", "src", "design", "hdl"])
    tb_directories: List[str] = field(default_factory=lambda: ["tb", "testbench", "test", "tests", "sim"])
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ProjectConfig":
        """Create config from dictionary"""
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})
