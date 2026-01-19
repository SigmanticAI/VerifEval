"""
TB-Eval Configuration.

Configuration for testbench evaluation based on VerifLLMBench methodology.
Supports both single-file and multi-file verification projects.
"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional


# Base directories
TB_EVAL_DIR = Path(__file__).parent
EXAMPLES_DIR = TB_EVAL_DIR / "examples"
WORK_DIR = TB_EVAL_DIR / "work"


@dataclass
class EvalConfig:
    """Configuration for evaluation runs."""
    
    # Simulation settings
    simulation_timeout_sec: int = 120
    
    # Coverage options
    enable_line_coverage: bool = True
    enable_toggle_coverage: bool = True
    enable_branch_coverage: bool = True
    
    # Lint options
    enable_lint: bool = True
    
    # Output settings
    verbose: bool = False
    keep_work_dir: bool = False


@dataclass
class VerificationProject:
    """
    Represents a verification project (single or multi-file).
    
    A verification project contains:
    - DUT files (Verilog/SystemVerilog)
    - Testbench files (cocotb Python)
    - Optional support files (interfaces, drivers, monitors, etc.)
    - Optional Makefile
    """
    
    path: Path
    name: str = ""
    
    # Files discovered
    dut_files: List[Path] = field(default_factory=list)
    tb_files: List[Path] = field(default_factory=list)
    support_files: List[Path] = field(default_factory=list)
    makefile: Optional[Path] = None
    
    # Parsed from Makefile or inferred
    top_module: Optional[str] = None
    test_module: Optional[str] = None
    
    def __post_init__(self):
        if not self.name:
            self.name = self.path.name
    
    @property
    def is_single_file(self) -> bool:
        """Check if this is a single-file testbench."""
        return len(self.tb_files) == 1 and len(self.support_files) == 0
    
    @property
    def is_multi_file(self) -> bool:
        """Check if this is a multi-file verification project."""
        return len(self.tb_files) > 1 or len(self.support_files) > 0


def get_default_config() -> EvalConfig:
    """Get default evaluation configuration."""
    return EvalConfig()
