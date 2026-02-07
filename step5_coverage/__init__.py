"""
Step 5: Coverage Analysis Package

This package provides coverage analysis functionality for the TB Eval framework.
It processes coverage data from test execution (Step 4) and generates detailed
coverage reports consumed by Step 7 for scoring.

Main Components:
- Models: Data structures for coverage representation
- Parsers: Coverage file format parsers (Verilator, LCOV, Covered)
- Analyzers: Coverage analysis and calculation
- Reporters: Report generation
- Tools: External tool integration

Typical Usage:
    >>> from step5_coverage import CoverageAnalyzer, CoverageAnalysisConfig
    >>> 
    >>> # Configure analysis
    >>> config = CoverageAnalysisConfig.from_yaml(".tbeval.yaml")
    >>> 
    >>> # Run analysis
    >>> analyzer = CoverageAnalyzer(config)
    >>> report = analyzer.analyze()
    >>> 
    >>> # Save report
    >>> report.save("coverage_report.json")

Author: TB Eval Team
Version: 0.1.0
"""

# =============================================================================
# VERSION INFORMATION
# =============================================================================

__version__ = "0.1.0"
__author__ = "TB Eval Team"
__license__ = "MIT"


# =============================================================================
# IMPORTS - Models
# =============================================================================

from .models import (
    # Enums
    CoverageFormat,
    CoverageGranularity,
    CoverageType,
    
    # Low-level coverage data
    LineCoverageData,
    BranchData,
    ToggleData,
    
    # File/Module aggregation
    FileCoverage,
    ModuleCoverage,
    
    # High-level metrics
    LineCoverageMetrics,
    BranchCoverageMetrics,
    ToggleCoverageMetrics,
    FSMCoverageMetrics,
    StructuralCoverageMetrics,
    
    # Analysis structures
    PerTestCoverage,
    HierarchicalCoverage,
    
    # Mutation testing integration
    MutationTarget,
    MutationTestingData,
    
    # Main output
    CoverageReport,
    
    # Helper functions
    merge_module_coverage,
    calculate_differential_coverage,
)


# =============================================================================
# IMPORTS - Configuration (will be implemented next)
# =============================================================================

from .config import (
    CoverageThresholds,
    CoverageWeights,
    ParserConfig,
    MergingConfig,
    ReportingConfig,
    CoverageAnalysisConfig,
    load_config_from_yaml,
    create_default_config_file,
    load_config_from_env,
)

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

# =============================================================================
# IMPORTS - Parsers (to be implemented)
# =============================================================================

# Placeholder imports - will be uncommented once parsers are implemented
# from .parsers import (
#     BaseParser,
#     VerilatorParser,
#     LCOVParser,
#     CoveredParser,
#     FormatDetector,
# )


# =============================================================================
# IMPORTS - Analyzers (to be implemented)
# =============================================================================

# Placeholder imports - will be uncommented once analyzers are implemented
# from .analyzer import CoverageAnalyzer
from .analyzer import (
    CoverageAnalyzer,
    AnalysisResult,
    analyze_coverage,
    quick_analyze,
)


# =============================================================================
# IMPORTS - Reporters (to be implemented)
# =============================================================================

# Placeholder imports - will be uncommented once reporters are implemented
# from .reporters import (
#     JSONReporter,
#     SummaryReporter,
#     TestEnricher,
# )


# =============================================================================
# PUBLIC API DEFINITION
# =============================================================================

__all__ = [
    # Version
    "__version__",
    "__author__",
    "__license__",
    
    # Enums
    "CoverageFormat",
    "CoverageGranularity",
    "CoverageType",
    
    # Low-level data structures
    "LineCoverageData",
    "BranchData",
    "ToggleData",
    
    # Mid-level aggregation
    "FileCoverage",
    "ModuleCoverage",
    
    # High-level metrics
    "LineCoverageMetrics",
    "BranchCoverageMetrics",
    "ToggleCoverageMetrics",
    "FSMCoverageMetrics",
    "StructuralCoverageMetrics",
    
    # Analysis structures
    "PerTestCoverage",
    "HierarchicalCoverage",
    
    # Mutation testing
    "MutationTarget",
    "MutationTestingData",
    
    # Main output
    "CoverageReport",
    
    # Helper functions
    "merge_module_coverage",
    "calculate_differential_coverage",
    "CoverageThresholds",
    "CoverageWeights",
    "ParserConfig",
    "MergingConfig",
    "ReportingConfig",
    "CoverageAnalysisConfig",
    "load_config_from_yaml",
    "create_default_config_file",
    "load_config_from_env",
    "BaseParser",
    "ParseResult",
    "MergeResult",
    
    # Verilator parser
    "VerilatorParser",
    "create_verilator_parser",
    "is_verilator_coverage_available",
    "get_verilator_coverage_version",
    "CoverageAnalyzer",
    "AnalysisResult",
    "analyze_coverage",
    "quick_analyze",
    
    # Configuration (to be uncommented)
    # "CoverageThresholds",
    # "CoverageWeights",
    # "ParserConfig",
    # "MergingConfig",
    # "ReportingConfig",
    # "CoverageAnalysisConfig",
    
    # Parsers (to be uncommented)
    # "BaseParser",
    # "VerilatorParser",
    # "LCOVParser",
    # "CoveredParser",
    # "FormatDetector",
    
    # Main analyzer (to be uncommented)
    # "CoverageAnalyzer",
    
    # Reporters (to be uncommented)
    # "JSONReporter",
    # "SummaryReporter",
    # "TestEnricher",
]


# =============================================================================
# CONVENIENCE FUNCTIONS
# =============================================================================

def get_version() -> str:
    """
    Get the package version string.
    
    Returns:
        Version string (e.g., "0.1.0")
    """
    return __version__


def create_empty_report() -> CoverageReport:
    """
    Create an empty coverage report with default values.
    
    Useful for testing or initializing reports.
    
    Returns:
        Empty CoverageReport instance
    """
    return CoverageReport()


def load_report(path: str) -> CoverageReport:
    """
    Load a coverage report from a JSON file.
    
    Args:
        path: Path to coverage_report.json
    
    Returns:
        CoverageReport instance
    
    Example:
        >>> report = load_report(".tbeval/coverage/coverage_report.json")
        >>> print(report.structural_coverage.weighted_score)
    """
    from pathlib import Path
    return CoverageReport.load(Path(path))


def save_report(report: CoverageReport, path: str) -> None:
    """
    Save a coverage report to a JSON file.
    
    Args:
        report: CoverageReport instance
        path: Destination path
    
    Example:
        >>> report = CoverageReport()
        >>> save_report(report, "coverage_report.json")
    """
    from pathlib import Path
    report.save(Path(path))


# =============================================================================
# PACKAGE METADATA
# =============================================================================

# Package description for help()
__doc__ = """
step5_coverage - Coverage Analysis for TB Eval Framework

This package processes coverage data from hardware verification tests and
generates detailed coverage reports.

Key Features:
- Parse Verilator, LCOV, and Covered coverage formats
- Calculate line, branch, toggle, and FSM coverage
- Per-test and hierarchical coverage analysis
- Generate mutation testing targets for Step 6
- Export structured data for Step 7 scoring

Quick Start:
    1. Import the analyzer:
       >>> from step5_coverage import CoverageAnalyzer, CoverageAnalysisConfig
    
    2. Configure analysis:
       >>> config = CoverageAnalysisConfig.from_yaml(".tbeval.yaml")
    
    3. Run analysis:
       >>> analyzer = CoverageAnalyzer(config)
       >>> report = analyzer.analyze()
    
    4. Access results:
       >>> print(f"Line coverage: {report.structural_coverage.line.percentage}%")
       >>> print(f"Overall score: {report.structural_coverage.weighted_score}")

For detailed documentation, see: https://github.com/tbeval/step5_coverage
"""


# =============================================================================
# PACKAGE INITIALIZATION
# =============================================================================

def _check_dependencies():
    """Check for optional dependencies and emit warnings if missing."""
    import warnings
    
    # Check for optional dependencies
    optional_deps = {
        "yaml": "PyYAML",
        "lxml": "lxml",
    }
    
    missing_deps = []
    for module, package in optional_deps.items():
        try:
            __import__(module)
        except ImportError:
            missing_deps.append(package)
    
    if missing_deps:
        warnings.warn(
            f"Optional dependencies not found: {', '.join(missing_deps)}. "
            f"Some features may not be available. "
            f"Install with: pip install {' '.join(missing_deps)}",
            ImportWarning
        )


# Check dependencies on import (optional, can be disabled)
# _check_dependencies()


# =============================================================================
# CLI ENTRY POINT HINT
# =============================================================================

def _cli_entry_point():
    """
    Entry point for CLI execution: python -m step5_coverage
    
    This is called when the package is run as a script.
    Delegates to __main__.py
    """
    from . import __main__
    __main__.main()


# Note: Actual CLI invocation happens in __main__.py
# This is just for documentation


# =============================================================================
# DEVELOPMENT HELPERS
# =============================================================================

def _get_debug_info() -> dict:
    """
    Get debug information about the package.
    
    Returns:
        Dictionary with package info, useful for troubleshooting
    """
    import sys
    from pathlib import Path
    
    return {
        "version": __version__,
        "location": Path(__file__).parent,
        "python_version": sys.version,
        "models_loaded": "models" in sys.modules.get(__name__, {}).__dict__,
    }


# For debugging: uncomment to print info on import
# if __debug__:
#     import pprint
#     pprint.pprint(_get_debug_info())
