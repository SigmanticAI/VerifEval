"""
Formal-Eval Configuration.

Configuration for formal verification evaluation.
Supports both single-file and multi-file SVA projects.
"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional


# Base directories
FORMAL_EVAL_DIR = Path(__file__).parent
EXAMPLES_DIR = FORMAL_EVAL_DIR / "examples"
WORK_DIR = FORMAL_EVAL_DIR / "work"


@dataclass
class FormalConfig:
    """Configuration for formal evaluation runs."""
    
    # Verification settings
    bounded_depth: int = 20  # Bounded model checking depth
    timeout_sec: int = 60    # Timeout per assertion
    
    # Tool settings
    use_yosys: bool = True
    use_z3: bool = True
    
    # Output settings
    verbose: bool = False
    keep_work_dir: bool = False
    generate_traces: bool = True  # Generate counterexample traces


@dataclass
class FormalProject:
    """
    Represents a formal verification project (single or multi-file).
    
    A formal verification project contains:
    - Design files (Verilog/SystemVerilog RTL)
    - Assertion files (SVA properties)
    - Optional constraint/assumption files
    """
    
    path: Path
    name: str = ""
    
    # Files discovered
    design_files: List[Path] = field(default_factory=list)      # DUT RTL
    assertion_files: List[Path] = field(default_factory=list)   # SVA assertions
    constraint_files: List[Path] = field(default_factory=list)  # Assumptions
    
    # Parsed assertions
    assertions: List[dict] = field(default_factory=list)
    assumptions: List[dict] = field(default_factory=list)
    cover_points: List[dict] = field(default_factory=list)
    
    def __post_init__(self):
        if not self.name:
            self.name = self.path.name
    
    @property
    def is_single_file(self) -> bool:
        """Check if this is a single-file project."""
        total_files = len(self.design_files) + len(self.assertion_files)
        return total_files <= 2
    
    @property
    def is_multi_file(self) -> bool:
        """Check if this is a multi-file project."""
        return not self.is_single_file
    
    @property
    def all_files(self) -> List[Path]:
        """Get all project files."""
        return self.design_files + self.assertion_files + self.constraint_files


def get_default_config() -> FormalConfig:
    """Get default formal evaluation configuration."""
    return FormalConfig()


