"""
TB Eval - Step 7: Scoring & Export

A comprehensive scoring system for hardware verification testbenches.

Supports two scoring tiers:
- Tier 1 (Open Source): Verilator-based structural coverage
- Tier 2 (Professional): Questa-based functional coverage, assertions, UVM

Quick Start:
    >>> from step7_score import ScoreAnalyzer
    >>> from step7_score.config import ScoreCalculationConfig
    >>> 
    >>> config = ScoreCalculationConfig.from_yaml(".tbeval.yaml")
    >>> analyzer = ScoreAnalyzer(config)
    >>> result = analyzer.analyze()
    >>> print(f"Score: {result.score.percentage:.2f}%")

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

# Main analyzer (will be implemented)
# from .analyzer import ScoreAnalyzer  # TODO: Implement

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
    is_pdf_export_available,
)

# =============================================================================
# PUBLIC API
# =============================================================================

__all__ = [
    # Version
    "__version__",
    "__author__",
    "__license__",
    
    # Core classes
    # "ScoreAnalyzer",  # TODO: Uncomment when implemented
    "ScoreCalculationConfig",
    
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
    
    # Configuration
    "Tier1Weights",
    "Tier2Weights",
    "GradeThresholds",
    "ExportConfig",
    "QuestaConfig",
    "create_default_config_file",
    
    # Tier 1 Scorers
    "CoverageScorer",
    "QualityScorer",
    "EfficiencyScorer",
    "TestPassRateScorer",
    "BehavioralScorer",
    
    # Tier Aggregators
    "Tier1Scorer",
    "Tier2Scorer",
    "calculate_tier1_score",
    "generate_tier1_report",
    "calculate_tier2_score",
    "generate_tier2_report",
    
    # Tier 2 Scorers
    "StabilityScorer",
    "FunctionalCoverageScorer",
    "AssertionCoverageScorer",
    "UVMConformanceScorer",
    
    # Questa
    "check_questa_availability",
    "is_questa_available",
    "is_tier2_available",
    
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
    "is_pdf_export_available",
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

# Suppress specific warnings
import warnings
warnings.filterwarnings('ignore', message='.*reportlab.*', category=UserWarning)

# Check for critical dependencies
import importlib.util

_MISSING_DEPS = []

# Check for reportlab (optional)
if importlib.util.find_spec("reportlab") is None:
    _MISSING_DEPS.append("reportlab")

# Warn about missing optional dependencies
if _MISSING_DEPS and not any('SPHINX' in k for k in globals()):
    warnings.warn(
        f"Optional dependencies not available: {', '.join(_MISSING_DEPS)}. "
        f"Some features will be disabled. "
        f"Install with: pip install {' '.join(_MISSING_DEPS)}",
        ImportWarning
    )
