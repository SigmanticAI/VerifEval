"""
Coverage metrics calculation

This package provides coverage metric calculation and aggregation.

Author: TB Eval Team
Version: 0.1.0
"""

from .calculator import (
    CoverageCalculator,
    UncoveredRegion,
    calculate_coverage,
    quick_summary,
)
from .merger import (
    CoverageMerger,
    MergeStatistics,
    merge_coverage_simple,
    merge_coverage_with_tracking,
)

__all__ = [
    "CoverageCalculator",
    "UncoveredRegion",
    "calculate_coverage",
    "quick_summary",
    # Merger
    "CoverageMerger",
    "MergeStatistics",
    "merge_coverage_simple",
    "merge_coverage_with_tracking",
]
