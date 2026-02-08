"""
step7_score.scorers — Scoring components for TB Eval

This sub-package contains all individual scorers and the two tier
aggregators.

Tier 1 (Open Source) components:
    - CoverageScorer        (50% weight — structural coverage)
    - TestPassRateScorer     (20% weight — pass/fail ratio)
    - QualityScorer          (15% weight — code quality)
    - EfficiencyScorer       (10% weight — runtime/memory)
    - BehavioralScorer       ( 5% weight — heuristic accuracy)

Tier 2 (Professional) adds:
    - FunctionalCoverage     (25% weight — Questa covergroups)
    - AssertionCoverage      (15% weight — SVA assertions)
    - UVMConformance         (10% weight — UVM methodology)
    - StabilityScorer        (10% weight — multi-seed stability)

Aggregators:
    - Tier1Scorer — aggregates all Tier 1 components
    - Tier2Scorer — aggregates all Tier 2 components
"""

from .tier1_scorer import Tier1Scorer, calculate_tier1_score, generate_tier1_report
from .tier2_scorer import Tier2Scorer, calculate_tier2_score, generate_tier2_report
from .coverage_scorer import CoverageScorer
from .quality_scorer import QualityScorer
from .efficiency_scorer import EfficiencyScorer
from .test_pass_rate_scorer import TestPassRateScorer
from .behavioral_scorer import BehavioralScorer

__all__ = [
    # Tier aggregators
    "Tier1Scorer",
    "Tier2Scorer",
    # Tier 1 convenience
    "calculate_tier1_score",
    "generate_tier1_report",
    # Tier 2 convenience
    "calculate_tier2_score",
    "generate_tier2_report",
    # Individual scorers
    "CoverageScorer",
    "QualityScorer",
    "EfficiencyScorer",
    "TestPassRateScorer",
    "BehavioralScorer",
]
