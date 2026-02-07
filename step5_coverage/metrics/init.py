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

__all__ = [
    "CoverageCalculator",
    "UncoveredRegion",
    "calculate_coverage",
    "quick_summary",
]
