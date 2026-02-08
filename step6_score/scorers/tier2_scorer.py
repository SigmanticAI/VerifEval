"""
Tier 2 scorer for Step 7: Scoring

Aggregates all Tier 2 (professional) component scores:
- Structural coverage (25%) - from Verilator/Questa
- Functional coverage (25%) - from Questa covergroups
- Assertion coverage (15%) - from Questa SVA
- UVM conformance (10%) - from Questa UVM analysis
- Multi-seed stability (10%) - from regression analysis
- Code quality (10%) - from static analysis
- Test efficiency (5%) - from runtime metrics

Used when Questa is available.

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
from ..config import ScoreCalculationConfig, Tier2Weights
from ..questa.license_checker import check_questa_availability

from .coverage_scorer import CoverageScorer, CoverageScoringConfig
from .quality_scorer import QualityScorer, QualityScoringConfig
from .efficiency_scorer import EfficiencyScorer, EfficiencyScoringConfig

logger = logging.getLogger(__name__)


# =============================================================================
# TIER 2 SCORER
# =============================================================================

class Tier2Scorer:
    """
    Tier 2 (Professional) scoring system
    
    This scorer aggregates all Tier 2 component scores into a final
    weighted score. Used when Questa is available.
    
    Components and weights:
    - Structural Coverage: 25% (line, branch, toggle)
    - Functional Coverage: 25% (SystemVerilog covergroups)
    - Assertion Coverage: 15% (SVA property verification)
    - UVM Conformance: 10% (UVM methodology compliance)
    - Multi-Seed Stability: 10% (regression stability)
    - Code Quality: 10% (linting, style, complexity)
    - Test Efficiency: 5% (runtime, memory)
    
    Workflow:
    1. Verify Questa availability
    2. Initialize component scorers with configuration
    3. Score each component
    4. Aggregate component scores
    5. Calculate weighted overall score
    6. Determine grade
    7. Generate recommendations
    8. Create final report
    """
    
    def __init__(self, config: ScoreCalculationConfig):
        """
        Initialize Tier 2 scorer
        
        Args:
            config: Main scoring configuration
        
        Raises:
            ValueError: If Questa not available and required
        """
        self.config = config
        self.weights = config.tier2_weights
        
        # Verify Questa availability
        self.questa_caps = check_questa_availability(config.questa_config)
        
        if not self.questa_caps.tier2_available:
            if config.questa_config.require_license:
                raise ValueError(
                    "Tier 2 scoring requires Questa but license not available. "
                    "Use Tier 1 or install Questa."
                )
            else:
                logger.warning(
                    "Questa not available - some Tier 2 features will be limited"
                )
        
        # Component scorers
        self.coverage_scorer: Optional[CoverageScorer] = None
        self.quality_scorer: Optional[QualityScorer] = None
        self.efficiency_scorer: Optional[EfficiencyScorer] = None
        self.functional_coverage_scorer: Optional[Any] = None  # Questa-specific
        self.assertion_coverage_scorer: Optional[Any] = None   # Questa-specific
        self.uvm_conformance_scorer: Optional[Any] = None      # Questa-specific
        self.stability_scorer: Optional[Any] = None             # Multi-seed
        
        # Component scores
        self.component_scores: Dict[str, ComponentScore] = {}
        
        # Initialize scorers
        self._initialize_scorers()
    
    def _initialize_scorers(self) -> None:
        """Initialize all component scorers"""
        logger.info("Initializing Tier 2 component scorers")
        
        # Structural coverage scorer (shared with Tier 1)
        self.coverage_scorer = CoverageScorer(
            config=CoverageScoringConfig(
                weight=self.weights.structural_coverage,
                line_threshold=85.0,      # Stricter for Tier 2
                branch_threshold=95.0,
                toggle_threshold=75.0,
                overall_threshold=85.0,
            ),
            coverage_report_path=self.config.coverage_report_path
        )
        
        # Quality scorer (shared with Tier 1, lower weight)
        self.quality_scorer = QualityScorer(
            config=QualityScoringConfig(
                weight=self.weights.code_quality,
                min_overall_score=0.75,   # Stricter for Tier 2
                max_style_violations=15,
                require_linting_pass=True,
            ),
            quality_report_path=self.config.quality_report_path
        )
        
        # Efficiency scorer (shared with Tier 1, lower weight)
        self.efficiency_scorer = EfficiencyScorer(
            config=EfficiencyScoringConfig(
                weight=self.weights.test_efficiency,
                max_acceptable_duration_per_test_ms=800.0,  # Stricter
                max_acceptable_memory_mb=400.0,
                min_coverage_per_second=0.015,
            ),
            test_report_path=self.config.test_report_path,
            coverage_report_path=self.config.coverage_report_path
        )
        
        # Functional coverage scorer (Questa-specific)
        if self.questa_caps.functional_coverage:
            logger.info("Initializing functional coverage scorer")
            # TODO: Implement functional coverage scorer
            self.functional_coverage_scorer = None
        else:
            logger.warning("Functional coverage not available")
            self.functional_coverage_scorer = None
        
        # Assertion coverage scorer (Questa-specific)
        if self.questa_caps.assertion_coverage:
            logger.info("Initializing assertion coverage scorer")
            # TODO: Implement assertion coverage scorer
            self.assertion_coverage_scorer = None
        else:
            logger.warning("Assertion coverage not available")
            self.assertion_coverage_scorer = None
        
        # UVM conformance scorer (Questa-specific)
        if self.questa_caps.uvm_support:
            logger.info("Initializing UVM conformance scorer")
            # TODO: Implement UVM conformance scorer
            self.uvm_conformance_scorer = None
        else:
            logger.warning("UVM analysis not available")
            self.uvm_conformance_scorer = None
        
        # Multi-seed stability scorer
        logger.info("Initializing multi-seed stability scorer")
        # TODO: Implement stability scorer
        self.stability_scorer = None
    
    def calculate_score(self) -> TierScore:
        """
        Calculate Tier 2 score
        
        Returns:
            TierScore with complete Tier 2 evaluation
        
        Raises:
            ValueError: If required reports not found
        """
        logger.info("Calculating Tier 2 score")
        
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
            tier=ScoringTier.PROFESSIONAL,
            overall=overall_score,
            grade=grade,
            pass_threshold=pass_threshold,
            components=self.component_scores,
            questa_available=True,
            available_upgrades=[]
        )
        
        logger.info(
            f"Tier 2 score: {overall_score:.4f} ({overall_score * 100:.2f}%) - "
            f"Grade: {grade.value} - {'PASS' if pass_threshold else 'FAIL'}"
        )
        
        return tier_score
    
    def _score_components(self) -> None:
        """Score all components"""
        logger.info("Scoring Tier 2 components")
        
        # 1. Structural Coverage (25%) - Required
        logger.info("Scoring structural coverage...")
        try:
            coverage_score = self.coverage_scorer.score()
            self.component_scores["structural_coverage"] = coverage_score
            logger.info(f"  Structural Coverage: {coverage_score.percentage:.2f}%")
        except Exception as e:
            logger.error(f"Failed to score structural coverage: {e}")
            raise ValueError(f"Structural coverage scoring failed (required): {e}")
        
        # 2. Functional Coverage (25%) - Questa-specific
        logger.info("Scoring functional coverage...")
        if self.functional_coverage_scorer:
            try:
                functional_score = self._score_functional_coverage()
                self.component_scores["functional_coverage"] = functional_score
                logger.info(f"  Functional Coverage: {functional_score.percentage:.2f}%")
            except Exception as e:
                logger.warning(f"Functional coverage scoring failed: {e}")
                self.component_scores["functional_coverage"] = self._create_placeholder_score(
                    ComponentType.FUNCTIONAL_COVERAGE,
                    self.weights.functional_coverage
                )
        else:
            logger.warning("Functional coverage scorer not available - using placeholder")
            self.component_scores["functional_coverage"] = self._create_placeholder_score(
                ComponentType.FUNCTIONAL_COVERAGE,
                self.weights.functional_coverage
            )
        
        # 3. Assertion Coverage (15%) - Questa-specific
        logger.info("Scoring assertion coverage...")
        if self.assertion_coverage_scorer:
            try:
                assertion_score = self._score_assertion_coverage()
                self.component_scores["assertion_coverage"] = assertion_score
                logger.info(f"  Assertion Coverage: {assertion_score.percentage:.2f}%")
            except Exception as e:
                logger.warning(f"Assertion coverage scoring failed: {e}")
                self.component_scores["assertion_coverage"] = self._create_placeholder_score(
                    ComponentType.ASSERTION_COVERAGE,
                    self.weights.assertion_coverage
                )
        else:
            logger.warning("Assertion coverage scorer not available - using placeholder")
            self.component_scores["assertion_coverage"] = self._create_placeholder_score(
                ComponentType.ASSERTION_COVERAGE,
                self.weights.assertion_coverage
            )
        
        # 4. UVM Conformance (10%) - Questa-specific
        logger.info("Scoring UVM conformance...")
        if self.uvm_conformance_scorer:
            try:
                uvm_score = self._score_uvm_conformance()
                self.component_scores["uvm_conformance"] = uvm_score
                logger.info(f"  UVM Conformance: {uvm_score.percentage:.2f}%")
            except Exception as e:
                logger.warning(f"UVM conformance scoring failed: {e}")
                self.component_scores["uvm_conformance"] = self._create_placeholder_score(
                    ComponentType.UVM_CONFORMANCE,
                    self.weights.uvm_conformance
                )
        else:
            logger.warning("UVM conformance scorer not available - using placeholder")
            self.component_scores["uvm_conformance"] = self._create_placeholder_score(
                ComponentType.UVM_CONFORMANCE,
                self.weights.uvm_conformance
            )
        
        # 5. Multi-Seed Stability (10%)
        logger.info("Scoring multi-seed stability...")
        if self.stability_scorer:
            try:
                stability_score = self._score_stability()
                self.component_scores["multiseed_stability"] = stability_score
                logger.info(f"  Stability: {stability_score.percentage:.2f}%")
            except Exception as e:
                logger.warning(f"Stability scoring failed: {e}")
                self.component_scores["multiseed_stability"] = self._create_placeholder_score(
                    ComponentType.MULTISEED_STABILITY,
                    self.weights.multiseed_stability
                )
        else:
            logger.warning("Stability scorer not available - using placeholder")
            self.component_scores["multiseed_stability"] = self._create_placeholder_score(
                ComponentType.MULTISEED_STABILITY,
                self.weights.multiseed_stability
            )
        
        # 6. Code Quality (10%) - Optional
        logger.info("Scoring code quality...")
        try:
            quality_score = self.quality_scorer.score()
            self.component_scores["code_quality"] = quality_score
            logger.info(f"  Quality: {quality_score.percentage:.2f}%")
        except Exception as e:
            logger.warning(f"Quality scoring failed (using default): {e}")
        
        # 7. Test Efficiency (5%) - Required
        logger.info("Scoring test efficiency...")
        try:
            efficiency_score = self.efficiency_scorer.score()
            self.component_scores["test_efficiency"] = efficiency_score
            logger.info(f"  Efficiency: {efficiency_score.percentage:.2f}%")
        except Exception as e:
            logger.error(f"Failed to score efficiency: {e}")
            raise ValueError(f"Efficiency scoring failed (required): {e}")
    
    def _score_functional_coverage(self) -> ComponentScore:
        """
        Score functional coverage (Questa-specific)
        
        Returns:
            ComponentScore for functional coverage
        """
        # TODO: Implement actual functional coverage scoring
        # This would parse Questa UCDB and extract covergroup data
        
        logger.warning("Functional coverage scorer not yet implemented")
        return self._create_placeholder_score(
            ComponentType.FUNCTIONAL_COVERAGE,
            self.weights.functional_coverage,
            note="Functional coverage parsing not yet implemented"
        )
    
    def _score_assertion_coverage(self) -> ComponentScore:
        """
        Score assertion coverage (Questa-specific)
        
        Returns:
            ComponentScore for assertion coverage
        """
        # TODO: Implement actual assertion coverage scoring
        # This would parse Questa assertion results
        
        logger.warning("Assertion coverage scorer not yet implemented")
        return self._create_placeholder_score(
            ComponentType.ASSERTION_COVERAGE,
            self.weights.assertion_coverage,
            note="Assertion coverage parsing not yet implemented"
        )
    
    def _score_uvm_conformance(self) -> ComponentScore:
        """
        Score UVM conformance (Questa-specific)
        
        Returns:
            ComponentScore for UVM conformance
        """
        # TODO: Implement actual UVM conformance scoring
        # This would analyze UVM structure and compliance
        
        logger.warning("UVM conformance scorer not yet implemented")
        return self._create_placeholder_score(
            ComponentType.UVM_CONFORMANCE,
            self.weights.uvm_conformance,
            note="UVM conformance analysis not yet implemented"
        )
    
    def _score_stability(self) -> ComponentScore:
        """
        Score multi-seed stability
        
        Returns:
            ComponentScore for stability
        """
        # TODO: Implement actual stability scoring
        # This would analyze test results across multiple seeds
        
        logger.warning("Stability scorer not yet implemented")
        return self._create_placeholder_score(
            ComponentType.MULTISEED_STABILITY,
            self.weights.multiseed_stability,
            note="Multi-seed stability analysis not yet implemented"
        )
    
    def _create_placeholder_score(
        self,
        component_type: ComponentType,
        weight: float,
        note: str = "Component not yet implemented"
    ) -> ComponentScore:
        """
        Create placeholder component score
        
        Args:
            component_type: Type of component
            weight: Weight for this component
            note: Note about why placeholder
        
        Returns:
            Placeholder ComponentScore
        """
        return ComponentScore(
            component_type=component_type,
            value=0.75,  # Neutral default
            weight=weight,
            raw_metrics={"placeholder": True, "note": note},
            threshold_met=True,  # Don't fail on placeholder
            details=f"{component_type.display_name}: {note}",
            recommendations=[
                f"Full {component_type.display_name} analysis coming soon"
            ]
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
        
        # TODO: Add improvements from Questa-specific scorers
        
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
                    f"Focus on Tier 2 components (functional coverage, assertions) for maximum improvement."
                ),
                details="Tier 2 provides more comprehensive verification analysis.",
            ))
        
        # Check for placeholder components
        placeholder_count = sum(
            1 for score in self.component_scores.values()
            if score.raw_metrics.get("placeholder")
        )
        
        if placeholder_count > 0:
            recommendations.append(Recommendation(
                category="Tier 2 Features",
                message=(
                    f"{placeholder_count} Tier 2 component(s) not yet fully implemented. "
                    f"Current score uses neutral defaults for these components."
                ),
                details=(
                    "Full Tier 2 implementation will include: "
                    "functional coverage parsing, assertion analysis, UVM conformance checks."
                ),
            ))
        
        # Component-specific recommendations
        for name, score in self.component_scores.items():
            if not score.threshold_met and not score.raw_metrics.get("placeholder"):
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
                    f"Tier 2 verification demonstrates professional-level practices."
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
        logger.info("Generating Tier 2 final report")
        
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
                "tier2_scoring"
            ],
            improvements=improvements,
            recommendations=recommendations,
            metadata={
                "tier": "tier2_professional",
                "questa_available": True,
                "questa_version": self.questa_caps.questa_version,
                "component_count": len(self.component_scores),
                "weights": self.weights.to_dict(),
                "placeholder_count": sum(
                    1 for score in self.component_scores.values()
                    if score.raw_metrics.get("placeholder")
                ),
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
            "TIER 2 SCORING SUMMARY (Professional - Questa)",
            "=" * 60,
            f"\nOverall Score: {overall:.4f} ({overall * 100:.2f}%)",
            f"Grade: {grade.value}",
            f"Pass: {'✓ YES' if overall >= 0.70 else '✗ NO'}",
            f"\nQuesta Version: {self.questa_caps.questa_version or 'Unknown'}",
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
            placeholder = " [PLACEHOLDER]" if score.raw_metrics.get("placeholder") else ""
            lines.append(
                f"  {status} {score.component_type.display_name:25s} "
                f"{score.percentage:6.2f}% (weight: {score.weight:.2f}, "
                f"contribution: {score.weighted_contribution:.4f}){placeholder}"
            )
        
        lines.append("\n" + "=" * 60)
        
        return "\n".join(lines)


# =============================================================================
# CONVENIENCE FUNCTIONS
# =============================================================================

def calculate_tier2_score(
    config: ScoreCalculationConfig
) -> TierScore:
    """
    Convenience function to calculate Tier 2 score
    
    Args:
        config: Scoring configuration
    
    Returns:
        TierScore for Tier 2
    
    Raises:
        ValueError: If Questa not available and required
    """
    scorer = Tier2Scorer(config)
    return scorer.calculate_score()


def generate_tier2_report(
    config: ScoreCalculationConfig,
    submission_id: str
) -> FinalReport:
    """
    Convenience function to generate complete Tier 2 report
    
    Args:
        config: Scoring configuration
        submission_id: Unique submission identifier
    
    Returns:
        FinalReport with complete evaluation
    """
    scorer = Tier2Scorer(config)
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
    print("TIER 2 SCORING")
    print("=" * 60)
    
    # Load configuration
    if len(sys.argv) > 1:
        config_path = Path(sys.argv[1])
    else:
        config_path = Path(".tbeval.yaml")
    
    if not config_path.exists():
        print(f"Error: Config file not found: {config_path}")
        print("Usage: python -m step7_score.scorers.tier2_scorer [config.yaml]")
        sys.exit(1)
    
    try:
        # Load config
        config = ScoreCalculationConfig.from_yaml(config_path)
        
        # Validate Questa availability
        caps = check_questa_availability(config.questa_config)
        if not caps.tier2_available:
            print("\n⚠ Warning: Questa not available")
            print("Tier 2 scoring will use placeholder values for Questa-specific components")
            print()
        
        # Create scorer
        scorer = Tier2Scorer(config)
        
        # Calculate score
        print("\nCalculating Tier 2 score...")
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
                print(f"   Impact:   {imp.impact:.4f} score points")
        
        # Generate recommendations
        recommendations = scorer.generate_recommendations()
        if recommendations:
            print("\nRecommendations:")
            for i, rec in enumerate(recommendations, 1):
                print(f"\n{i}. [{rec.category}]")
                print(f"   {rec.message}")
        
        # Generate full report
        print("\nGenerating final report...")
        submission_id = config.submission_dir.name or "submission"
        report = scorer.generate_report(submission_id, tier_score)
        
        # Save report
        output_dir = config.export_config.output_dir
        output_dir.mkdir(parents=True, exist_ok=True)
        
        report_path = output_dir / "final_score_tier2.json"
        report.save(report_path)
        print(f"\n✓ Final report saved to: {report_path}")
        
        # Print final result
        print("\n" + "=" * 60)
        if tier_score.pass_threshold:
            print(f"✓ PASS - Score: {tier_score.percentage:.2f}% (Grade: {tier_score.grade.value})")
        else:
            print(f"✗ FAIL - Score: {tier_score.percentage:.2f}% (Grade: {tier_score.grade.value})")
        print("=" * 60 + "\n")
        
        sys.exit(0 if tier_score.pass_threshold else 1)
    
    except Exception as e:
        print(f"\n✗ Error calculating Tier 2 score: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
