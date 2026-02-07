"""
Coverage file parsers

This package provides parsers for various coverage file formats:
- Verilator (.dat)
- LCOV (.info)
- Covered (.cdd, text reports)
- Questa/ModelSim (.ucdb) - Phase 2
- VCS (.vdb) - Phase 2

Each parser implements the BaseParser interface and follows Q12 Option C:
1. Try external tool (preferred)
2. Fall back to Python parsing

Author: TB Eval Team
Version: 0.1.0
"""

from .base import (
    BaseParser,
    ParseResult,
    MergeResult,
)

from .verilator_parser import (
    VerilatorParser,
    create_verilator_parser,
    is_verilator_coverage_available,
    get_verilator_coverage_version,
)
from .lcov_parser import (
    LCOVParser,
    create_lcov_parser,
    is_lcov_available,
    get_lcov_version,
)

# Parsers will be imported as they're implemented
# from .verilator_parser import VerilatorParser
# from .lcov_parser import LCOVParser
# from .covered_parser import CoveredParser
# from .format_detector import FormatDetector

__all__ = [
    # Base classes
    "BaseParser",
    "ParseResult",
    "MergeResult",
    "VerilatorParser",
    "create_verilator_parser",
    "is_verilator_coverage_available",
    "get_verilator_coverage_version",
    "LCOVParser",
    "create_lcov_parser",
    "is_lcov_available",
    "get_lcov_version",
    
    # Parsers (to be uncommented as implemented)
    # "VerilatorParser",
    # "LCOVParser",
    # "CoveredParser",
    # "FormatDetector",
]
