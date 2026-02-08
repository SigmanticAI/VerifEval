"""
TB Eval - Step 7: Scoring & Export

A comprehensive scoring system for hardware verification testbenches.

Supports two scoring tiers:
- Tier 1 (Open Source): Verilator-based structural coverage
- Tier 2 (Professional): Questa-based functional coverage, assertions, UVM

Quick Start:
    >>> from step7_score import TestbenchAnalyzer, ScoreCalculationConfig
    >>> from pathlib import Path
    >>> 
    >>> config = ScoreCalculationConfig.from_yaml(Path(".tbeval.yaml"))
    >>> analyzer = TestbenchAnalyzer(config)
    >>> result = analyzer.run(submission_id="student_42_alu")
    >>> print(f"Score: {result.report.score.percentage:.2f}%")

One-liner API:
    >>> from step7_score import analyze
    >>> report = analyze(Path("./submission"))

Author: TB Eval Team
Version: 0.1.0
License: MIT
"""

__version__ = "0.1.0"
__author__ = "TB Eval Team"
__license__ = "MIT"

# =============================================================================
# CORE IMPORTS
# =============================================================================

# Main orchestrator
from .analyzer import (
    TestbenchAnalyzer,
    AnalysisResult,
    analyze,
    analyze_from_config,
)

# Models - Data structures
from .models import (
    # Core data types
    ComponentScore,
    ComponentType,
    TierScore,
    ScoringTier,
    Grade,
    FinalReport,
    Improvement,
    Recommendation,
    
    # Metrics
    CoverageMetrics,
    QualityMetrics,
    TestExecutionMetrics,
    EfficiencyMetrics,
    StabilityMetrics,
    
    # Questa-specific metrics
    FunctionalCoverageMetrics,
    AssertionCoverageMetrics,
    UVMConformanceMetrics,
)

# Configuration
from .config import (
    ScoreCalculationConfig,
    Tier1Weights,
    Tier2Weights,
    GradeThresholds,
    ExportConfig,
    QuestaConfig,
    create_default_config_file,
)

# =============================================================================
# SCORERS
# =============================================================================

# Tier 1 scorers
from .scorers.coverage_scorer import (
    CoverageScorer,
    CoverageScoringConfig,
    score_coverage,
)

from .scorers.quality_scorer import (
    QualityScorer,
    QualityScoringConfig,
    score_quality,
)

from .scorers.efficiency_scorer import (
    EfficiencyScorer,
    EfficiencyScoringConfig,
    score_efficiency,
)

from .scorers.test_pass_rate_scorer import (
    TestPassRateScorer,
    PassRateScoringConfig,
    score_test_pass_rate,
)

from .scorers.behavioral_scorer import (
    BehavioralScorer,
    BehavioralScoringConfig,
    score_behavioral_accuracy,
)

# Tier aggregators
from .scorers.tier1_scorer import (
    Tier1Scorer,
    calculate_tier1_score,
    generate_tier1_report,
)

from .scorers.tier2_scorer import (
    Tier2Scorer,
    calculate_tier2_score,
    generate_tier2_report,
)

# Tier 2 specific scorers
from .scorers.stability_scorer import (
    StabilityScorer,
    StabilityScoringConfig,
    score_stability,
)

# =============================================================================
# QUESTA INTEGRATION
# =============================================================================

from .questa.license_checker import (
    check_questa_availability,
    is_questa_available,
    is_tier2_available,
    print_questa_status,
)

from .questa.functional_cov import (
    FunctionalCoverageParser,
    FunctionalCoverageScorer,
    score_functional_coverage,
)

from .questa.assertion_cov import (
    AssertionCoverageParser,
    AssertionCoverageScorer,
    score_assertion_coverage,
)

from .questa.uvm_analyzer import (
    UVMAnalyzer,
    UVMConformanceScorer,
    score_uvm_conformance,
)

# =============================================================================
# EXPORTERS
# =============================================================================

from .exporters import (
    export_html,
    export_junit,
    export_csv,
    export_pdf,
    export_all,
    is_pdf_export_available,
    get_available_formats,
    BatchExporter,
)

# =============================================================================
# PUBLIC API
# =============================================================================

__all__ = [
    # Version
    "__version__",
    "__author__",
    "__license__",
    
    # Core orchestrator
    "TestbenchAnalyzer",
    "AnalysisResult",
    "analyze",
    "analyze_from_config",
    
    # Configuration
    "ScoreCalculationConfig",
    "Tier1Weights",
    "Tier2Weights",
    "GradeThresholds",
    "ExportConfig",
    "QuestaConfig",
    "create_default_config_file",
    
    # Models - Core
    "ComponentScore",
    "ComponentType",
    "TierScore",
    "ScoringTier",
    "Grade",
    "FinalReport",
    "Improvement",
    "Recommendation",
    
    # Models - Metrics
    "CoverageMetrics",
    "QualityMetrics",
    "TestExecutionMetrics",
    "EfficiencyMetrics",
    "StabilityMetrics",
    "FunctionalCoverageMetrics",
    "AssertionCoverageMetrics",
    "UVMConformanceMetrics",
    
    # Tier 1 Scorers
    "CoverageScorer",
    "CoverageScoringConfig",
    "QualityScorer",
    "QualityScoringConfig",
    "EfficiencyScorer",
    "EfficiencyScoringConfig",
    "TestPassRateScorer",
    "PassRateScoringConfig",
    "BehavioralScorer",
    "BehavioralScoringConfig",
    
    # Tier Aggregators
    "Tier1Scorer",
    "Tier2Scorer",
    "calculate_tier1_score",
    "generate_tier1_report",
    "calculate_tier2_score",
    "generate_tier2_report",
    
    # Tier 2 Scorers
    "StabilityScorer",
    "StabilityScoringConfig",
    "FunctionalCoverageParser",
    "FunctionalCoverageScorer",
    "AssertionCoverageParser",
    "AssertionCoverageScorer",
    "UVMAnalyzer",
    "UVMConformanceScorer",
    
    # Questa
    "check_questa_availability",
    "is_questa_available",
    "is_tier2_available",
    "print_questa_status",
    
    # Convenience scoring functions
    "score_coverage",
    "score_quality",
    "score_efficiency",
    "score_test_pass_rate",
    "score_behavioral_accuracy",
    "score_stability",
    "score_functional_coverage",
    "score_assertion_coverage",
    "score_uvm_conformance",
    
    # Exporters
    "export_html",
    "export_junit",
    "export_csv",
    "export_pdf",
    "export_all",
    "is_pdf_export_available",
    "get_available_formats",
    "BatchExporter",
]

# =============================================================================
# CONVENIENCE FUNCTIONS
# =============================================================================

def get_version() -> str:
    """
    Get package version
    
    Returns:
        Version string
    """
    return __version__


def check_dependencies() -> dict:
    """
    Check availability of optional dependencies
    
    Returns:
        Dictionary of dependency availability
    """
    return {
        "questa": is_questa_available(),
        "tier2": is_tier2_available(),
        "pdf_export": is_pdf_export_available(),
    }


def print_info() -> None:
    """Print package information"""
    print(f"TB Eval - Step 7: Scoring & Export v{__version__}")
    print(f"Author: {__author__}")
    print(f"License: {__license__}")
    print("\nAvailable components:")
    print("  ✓ Tier 1 (Open Source) scoring")
    print("  ✓ Tier 2 (Professional) scoring")
    
    deps = check_dependencies()
    if deps["questa"]:
        print("  ✓ Questa integration available")
    else:
        print("  ✗ Questa not available (Tier 1 only)")
    
    if deps["pdf_export"]:
        print("  ✓ PDF export available")
    else:
        print("  ✗ PDF export not available (install reportlab)")


# =============================================================================
# MODULE INITIALIZATION
# =============================================================================

import warnings
import importlib.util

# Check for optional dependencies
_MISSING_DEPS = []

if importlib.util.find_spec("reportlab") is None:
    _MISSING_DEPS.append("reportlab")

if _MISSING_DEPS:
    warnings.warn(
        f"Optional dependencies not available: {', '.join(_MISSING_DEPS)}. "
        f"Some features will be disabled. "
        f"Install with: pip install {' '.join(_MISSING_DEPS)}",
        ImportWarning,
        stacklevel=2,
    )
