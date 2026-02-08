"""
Tier 1 scorer for Step 7: Scoring

Aggregates all Tier 1 (open-source) component scores:
- Structural coverage (50%) - from Verilator
- Test pass rate (20%) - from test execution
- Code quality (15%) - from static analysis
- Test efficiency (10%) - from runtime metrics
- Behavioral accuracy (5%) - heuristic estimate

Used when Questa is not available.

Author: TB Eval Team
Version: 0.1.0
"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional, Dict, List, Any
from datetime import datetime
import logging

from ..models import (
    ComponentScore,
    ComponentType,
    TierScore,
    ScoringTier,
    Grade,
    FinalReport,
    Improvement,
    Recommendation,
)
from ..config import ScoreCalculationConfig, Tier1Weights

from .coverage_scorer import CoverageScorer, CoverageScoringConfig
from .quality_scorer import QualityScorer, QualityScoringConfig
from .efficiency_scorer import EfficiencyScorer, EfficiencyScoringConfig
from .test_pass_rate_scorer import TestPassRateScorer, PassRateScoringConfig
from .behavioral_scorer import BehavioralScorer, BehavioralScoringConfig

logger = logging.getLogger(__name__)


# =============================================================================
# TIER 1 SCORER
# =============================================================================

class Tier1Scorer:
    """
    Tier 1 (Open Source) scoring system
    
    This scorer aggregates all Tier 1 component scores into a final
    weighted score. Used when Questa is not available.
    
    Components and weights:
    - Structural Coverage: 50% (line, branch, toggle from Verilator)
    - Test Pass Rate: 20% (pass/fail ratio)
    - Code Quality: 15% (linting, style, complexity)
    - Test Efficiency: 10% (runtime, memory)
    - Behavioral Accuracy: 5% (heuristic based on assertions)
    
    Workflow:
    1. Initialize component scorers with configuration
    2. Score each component
    3. Aggregate component scores
    4. Calculate weighted overall score
    5. Determine grade
    6. Generate recommendations
    7. Create final report
    """
    
    def __init__(self, config: ScoreCalculationConfig):
        """
        Initialize Tier 1 scorer
        
        Args:
            config: Main scoring configuration
        """
        self.config = config
        self.weights = config.tier1_weights
        
        # Component scorers
        self.coverage_scorer: Optional[CoverageScorer] = None
        self.quality_scorer: Optional[QualityScorer] = None
        self.efficiency_scorer: Optional[EfficiencyScorer] = None
        self.pass_rate_scorer: Optional[TestPassRateScorer] = None
        self.behavioral_scorer: Optional[BehavioralScorer] = None
        
        # Component scores
        self.component_scores: Dict[str, ComponentScore] = {}
        
        # Initialize scorers
        self._initialize_scorers()
    
    def _initialize_scorers(self) -> None:
        """Initialize all component scorers"""
        logger.info("Initializing Tier 1 component scorers")
        
        # Coverage scorer
        self.coverage_scorer = CoverageScorer(
            config=CoverageScoringConfig(
                weight=self.weights.structural_coverage,
                line_threshold=80.0,
                branch_threshold=90.0,
                toggle_threshold=70.0,
                overall_threshold=80.0,
            ),
            coverage_report_path=self.config.coverage_report_path
        )
        
        # Quality scorer
        self.quality_scorer = QualityScorer(
            config=QualityScoringConfig(
                weight=self.weights.code_quality,
                min_overall_score=0.70,
                max_style_violations=20,
                require_linting_pass=True,
            ),
            quality_report_path=self.config.quality_report_path
        )
        
        # Efficiency scorer
        self.efficiency_scorer = EfficiencyScorer(
            config=EfficiencyScoringConfig(
                weight=self.weights.test_efficiency,
                max_acceptable_duration_per_test_ms=1000.0,
                max_acceptable_memory_mb=500.0,
                min_coverage_per_second=0.01,
            ),
            test_report_path=self.config.test_report_path,
            coverage_report_path=self.config.coverage_report_path
        )
        
        # Pass rate scorer
        self.pass_rate_scorer = TestPassRateScorer(
            config=PassRateScoringConfig(
                weight=self.weights.test_pass_rate,
                min_pass_rate=0.90,
                allow_errors=False,
            ),
            test_report_path=self.config.test_report_path
        )
        
        # Behavioral scorer
        self.behavioral_scorer = BehavioralScorer(
            config=BehavioralScoringConfig(
                weight=self.weights.behavioral_accuracy,
                min_assertions_per_test=3.0,
            ),
            test_report_path=self.config.test_report_path
        )
    
    def calculate_score(self) -> TierScore:
        """
        Calculate Tier 1 score
        
        Returns:
            TierScore with complete Tier 1 evaluation
        
        Raises:
            ValueError: If required reports not found
        """
        logger.info("Calculating Tier 1 score")
        
        # Score each component
        self._score_components()
        
        # Calculate overall score
        overall_score = self._calculate_overall_score()
        
        # Determine grade
        grade = Grade.from_score(overall_score)
        
        # Check if passing threshold met (C = 70%)
        pass_threshold = overall_score >= self.config.grade_thresholds.passing_percentage / 100.0
        
        # Create tier score
        tier_score = TierScore(
            tier=ScoringTier.OPEN_SOURCE,
            overall=overall_score,
            grade=grade,
            pass_threshold=pass_threshold,
            components=self.component_scores,
            questa_available=False,
            available_upgrades=["professional"] if not pass_threshold else []
        )
        
        logger.info(
            f"Tier 1 score: {overall_score:.4f} ({overall_score * 100:.2f}%) - "
            f"Grade: {grade.value} - {'PASS' if pass_threshold else 'FAIL'}"
        )
        
        return tier_score
    
    def _score_components(self) -> None:
        """Score all components"""
        logger.info("Scoring Tier 1 components")
        
        # 1. Coverage (50%) - Required
        logger.info("Scoring coverage...")
        try:
            coverage_score = self.coverage_scorer.score()
            self.component_scores["structural_coverage"] = coverage_score
            logger.info(f"  Coverage: {coverage_score.percentage:.2f}%")
        except Exception as e:
            logger.error(f"Failed to score coverage: {e}")
            raise ValueError(f"Coverage scoring failed (required): {e}")
        
        # 2. Pass Rate (20%) - Required
        logger.info("Scoring test pass rate...")
        try:
            pass_rate_score = self.pass_rate_scorer.score()
            self.component_scores["test_pass_rate"] = pass_rate_score
            logger.info(f"  Pass Rate: {pass_rate_score.percentage:.2f}%")
        except Exception as e:
            logger.error(f"Failed to score pass rate: {e}")
            raise ValueError(f"Pass rate scoring failed (required): {e}")
        
        # 3. Quality (15%) - Optional (uses default if missing)
        logger.info("Scoring code quality...")
        try:
            quality_score = self.quality_scorer.score()
            self.component_scores["code_quality"] = quality_score
            logger.info(f"  Quality: {quality_score.percentage:.2f}%")
        except Exception as e:
            logger.warning(f"Quality scoring failed (using default): {e}")
            # Quality scorer handles missing report with default score
        
        # 4. Efficiency (10%) - Required
        logger.info("Scoring test efficiency...")
        try:
            efficiency_score = self.efficiency_scorer.score()
            self.component_scores["test_efficiency"] = efficiency_score
            logger.info(f"  Efficiency: {efficiency_score.percentage:.2f}%")
        except Exception as e:
            logger.error(f"Failed to score efficiency: {e}")
            raise ValueError(f"Efficiency scoring failed (required): {e}")
        
        # 5. Behavioral (5%) - Heuristic
        logger.info("Scoring behavioral accuracy...")
        try:
            behavioral_score = self.behavioral_scorer.score()
            self.component_scores["behavioral_accuracy"] = behavioral_score
            logger.info(f"  Behavioral: {behavioral_score.percentage:.2f}%")
        except Exception as e:
            logger.warning(f"Behavioral scoring failed: {e}")
            # Create minimal behavioral score
            self.component_scores["behavioral_accuracy"] = ComponentScore(
                component_type=ComponentType.BEHAVIORAL_ACCURACY,
                value=0.65,  # Neutral default
                weight=self.weights.behavioral_accuracy,
                raw_metrics={"default": True},
                threshold_met=True,
                details="Behavioral scoring unavailable - using default"
            )
    
    def _calculate_overall_score(self) -> float:
        """
        Calculate weighted overall score
        
        Returns:
            Overall score (0.0-1.0)
        """
        if not self.component_scores:
            return 0.0
        
        # Weighted sum
        total_score = sum(
            score.weighted_contribution
            for score in self.component_scores.values()
        )
        
        return min(1.0, max(0.0, total_score))
    
    def generate_improvements(self) -> List[Improvement]:
        """
        Generate improvements across all components
        
        Returns:
            List of Improvement objects sorted by impact
        """
        all_improvements = []
        
        # Gather improvements from each component scorer
        if self.coverage_scorer and self.coverage_scorer.coverage_metrics:
            all_improvements.extend(self.coverage_scorer.generate_improvements())
        
        if self.quality_scorer and self.quality_scorer.quality_metrics:
            all_improvements.extend(self.quality_scorer.generate_improvements())
        
        if self.efficiency_scorer and self.efficiency_scorer.efficiency_metrics:
            all_improvements.extend(self.efficiency_scorer.generate_improvements())
        
        if self.pass_rate_scorer and self.pass_rate_scorer.test_metrics:
            all_improvements.extend(self.pass_rate_scorer.generate_improvements())
        
        if self.behavioral_scorer and self.behavioral_scorer.test_metrics:
            all_improvements.extend(self.behavioral_scorer.generate_improvements())
        
        # Sort by impact (highest first)
        all_improvements.sort(key=lambda x: x.impact, reverse=True)
        
        # Limit to top N
        max_improvements = self.config.recommendation_config.max_improvements
        return all_improvements[:max_improvements]
    
    def generate_recommendations(self) -> List[Recommendation]:
        """
        Generate general recommendations
        
        Returns:
            List of Recommendation objects
        """
        recommendations = []
        
        # Analyze overall performance
        overall_score = self._calculate_overall_score()
        
        # Low overall score
        if overall_score < 0.70:
            recommendations.append(Recommendation(
                category="Overall Quality",
                message=(
                    f"Overall score is {overall_score * 100:.1f}% (below 70% passing threshold). "
                    f"Focus on the lowest-scoring components for maximum improvement."
                ),
                details="Prioritize components with high weight and low scores.",
            ))
        
        # Check if Questa would help
        if overall_score < 0.85:
            recommendations.append(Recommendation(
                category="Upgrade to Tier 2",
                message=(
                    "Consider upgrading to Tier 2 (Questa) for more accurate behavioral coverage "
                    "and functional verification. Current Tier 1 score may undervalue your testbench."
                ),
                details=(
                    "Tier 2 provides: functional coverage, assertion coverage, UVM analysis, "
                    "and multi-seed stability analysis."
                ),
                references=["https://www.intel.com/questa"],
            ))
        
        # Component-specific recommendations
        for name, score in self.component_scores.items():
            if not score.threshold_met:
                recommendations.append(Recommendation(
                    category=score.component_type.display_name,
                    message=f"{score.component_type.display_name} below threshold ({score.percentage:.1f}%)",
                    details="; ".join(score.recommendations[:2]) if score.recommendations else None,
                ))
        
        # Excellent performance
        if overall_score >= 0.90:
            recommendations.append(Recommendation(
                category="Excellent Work",
                message=(
                    f"Outstanding testbench quality ({overall_score * 100:.1f}%)! "
                    f"Consider sharing best practices with the team."
                ),
                details="Continue maintaining high standards in verification.",
            ))
        
        return recommendations
    
    def generate_report(
        self,
        submission_id: str,
        tier_score: TierScore,
        total_duration_ms: float = 0.0
    ) -> FinalReport:
        """
        Generate final report
        
        Args:
            submission_id: Unique submission identifier
            tier_score: Calculated tier score
            total_duration_ms: Total evaluation duration
        
        Returns:
            FinalReport with complete evaluation
        """
        logger.info("Generating Tier 1 final report")
        
        # Generate improvements and recommendations
        improvements = self.generate_improvements()
        recommendations = self.generate_recommendations()
        
        # Create report
        report = FinalReport(
            submission_id=submission_id,
            generated_at=datetime.now(),
            framework_version="0.1.0",
            score=tier_score,
            quality_report_path=self.config.quality_report_path,
            test_report_path=self.config.test_report_path,
            coverage_report_path=self.config.coverage_report_path,
            total_duration_ms=total_duration_ms,
            steps_completed=[
                "intake",
                "quality_gate",
                "classification",
                "test_execution",
                "coverage_analysis",
                "tier1_scoring"
            ],
            improvements=improvements,
            recommendations=recommendations,
            metadata={
                "tier": "tier1_open_source",
                "questa_available": False,
                "component_count": len(self.component_scores),
                "weights": self.weights.to_dict(),
            }
        )
        
        return report
    
    def get_summary(self) -> str:
        """
        Get human-readable summary
        
        Returns:
            Summary string
        """
        if not self.component_scores:
            return "No scores calculated"
        
        overall = self._calculate_overall_score()
        grade = Grade.from_score(overall)
        
        lines = [
            "=" * 60,
            "TIER 1 SCORING SUMMARY (Open Source)",
            "=" * 60,
            f"\nOverall Score: {overall:.4f} ({overall * 100:.2f}%)",
            f"Grade: {grade.value}",
            f"Pass: {'✓ YES' if overall >= 0.70 else '✗ NO'}",
            "\nComponent Scores:",
        ]
        
        # Sort components by weight (highest first)
        sorted_components = sorted(
            self.component_scores.items(),
            key=lambda x: x[1].weight,
            reverse=True
        )
        
        for name, score in sorted_components:
            status = "✓" if score.threshold_met else "✗"
            lines.append(
                f"  {status} {score.component_type.display_name:25s} "
                f"{score.percentage:6.2f}% (weight: {score.weight:.2f}, "
                f"contribution: {score.weighted_contribution:.4f})"
            )
        
        lines.append("\n" + "=" * 60)
        
        return "\n".join(lines)


# =============================================================================
# CONVENIENCE FUNCTIONS
# =============================================================================

def calculate_tier1_score(
    config: ScoreCalculationConfig
) -> TierScore:
    """
    Convenience function to calculate Tier 1 score
    
    Args:
        config: Scoring configuration
    
    Returns:
        TierScore for Tier 1
    
    Example:
        >>> from step7_score.config import ScoreCalculationConfig
        >>> config = ScoreCalculationConfig.from_yaml(Path(".tbeval.yaml"))
        >>> score = calculate_tier1_score(config)
        >>> print(f"Score: {score.percentage:.2f}%")
    """
    scorer = Tier1Scorer(config)
    return scorer.calculate_score()


def generate_tier1_report(
    config: ScoreCalculationConfig,
    submission_id: str
) -> FinalReport:
    """
    Convenience function to generate complete Tier 1 report
    
    Args:
        config: Scoring configuration
        submission_id: Unique submission identifier
    
    Returns:
        FinalReport with complete evaluation
    
    Example:
        >>> report = generate_tier1_report(config, "student_123_fifo")
        >>> report.save(Path(".tbeval/score/final_score.json"))
    """
    scorer = Tier1Scorer(config)
    tier_score = scorer.calculate_score()
    return scorer.generate_report(submission_id, tier_score)


# =============================================================================
# EXAMPLE USAGE
# =============================================================================

if __name__ == "__main__":
    import sys
    from ..config import ScoreCalculationConfig
    
    # Setup logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(levelname)s - %(message)s'
    )
    
    print("=" * 60)
    print("TIER 1 SCORING")
    print("=" * 60)
    
    # Load configuration
    if len(sys.argv) > 1:
        config_path = Path(sys.argv[1])
    else:
        config_path = Path(".tbeval.yaml")
    
    if not config_path.exists():
        print(f"Error: Config file not found: {config_path}")
        print("Usage: python -m step7_score.scorers.tier1_scorer [config.yaml]")
        sys.exit(1)
    
    try:
        # Load config
        config = ScoreCalculationConfig.from_yaml(config_path)
        
        # Validate config
        issues = config.validate()
        if issues:
            print("\nConfiguration issues:")
            for issue in issues:
                print(f"  ⚠ {issue}")
            print()
        
        # Create scorer
        scorer = Tier1Scorer(config)
        
        # Calculate score
        print("\nCalculating Tier 1 score...")
        tier_score = scorer.calculate_score()
        
        # Print summary
        print("\n" + scorer.get_summary())
        
        # Generate improvements
        improvements = scorer.generate_improvements()
        if improvements:
            print("\nTop Improvements (by impact):")
            for i, imp in enumerate(improvements[:5], 1):
                print(f"\n{i}. {imp.component.display_name}")
                print(f"   Priority: {imp.priority.upper()}")
                print(f"   Current:  {imp.current_value:.2f}%")
                print(f"   Target:   {imp.target_value:.2f}%")
                print(f"   Impact:   {imp.impact:.4f} score points")
                print(f"   Top Action: {imp.actions[0] if imp.actions else 'N/A'}")
        
        # Generate recommendations
        recommendations = scorer.generate_recommendations()
        if recommendations:
            print("\nRecommendations:")
            for i, rec in enumerate(recommendations, 1):
                print(f"\n{i}. [{rec.category}]")
                print(f"   {rec.message}")
                if rec.details:
                    print(f"   → {rec.details}")
        
        # Generate full report
        print("\nGenerating final report...")
        submission_id = config.submission_dir.name or "submission"
        report = scorer.generate_report(submission_id, tier_score)
        
        # Save report
        output_dir = config.export_config.output_dir
        output_dir.mkdir(parents=True, exist_ok=True)
        
        report_path = output_dir / "final_score.json"
        report.save(report_path)
        print(f"\n✓ Final report saved to: {report_path}")
        
        # Save summary
        summary_path = output_dir / "score_summary.txt"
        summary_path.write_text(scorer.get_summary())
        print(f"✓ Summary saved to: {summary_path}")
        
        # Print final result
        print("\n" + "=" * 60)
        if tier_score.pass_threshold:
            print(f"✓ PASS - Score: {tier_score.percentage:.2f}% (Grade: {tier_score.grade.value})")
        else:
            print(f"✗ FAIL - Score: {tier_score.percentage:.2f}% (Grade: {tier_score.grade.value})")
        print("=" * 60 + "\n")
        
        sys.exit(0 if tier_score.pass_threshold else 1)
    
    except Exception as e:
        print(f"\n✗ Error calculating Tier 1 score: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
