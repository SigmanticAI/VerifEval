"""
Coverage scorer for Step 7: Scoring

Scores structural coverage component based on:
- Line coverage
- Branch coverage
- Toggle coverage
- FSM coverage (if available)

Used by both Tier 1 and Tier 2 scoring systems.

The coverage score is calculated as a weighted average of individual
coverage types, using weights from the coverage report itself.

Author: TB Eval Team
Version: 0.1.0
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Dict, List, Any
import logging

from ..models import (
    ComponentScore,
    ComponentType,
    CoverageMetrics,
    Improvement,
)

logger = logging.getLogger(__name__)


# =============================================================================
# CONFIGURATION
# =============================================================================

@dataclass
class CoverageScoringConfig:
    """
    Configuration for coverage scoring
    
    Attributes:
        weight: Weight for this component in overall score
        line_threshold: Minimum line coverage percentage
        branch_threshold: Minimum branch coverage percentage
        toggle_threshold: Minimum toggle coverage percentage
        fsm_threshold: Minimum FSM coverage percentage
        overall_threshold: Minimum overall coverage percentage
    """
    weight: float = 0.50  # Default Tier 1 weight
    line_threshold: float = 80.0
    branch_threshold: float = 90.0
    toggle_threshold: float = 70.0
    fsm_threshold: float = 75.0
    overall_threshold: float = 80.0


# =============================================================================
# COVERAGE SCORER
# =============================================================================

class CoverageScorer:
    """
    Score structural coverage component
    
    This scorer evaluates testbench quality based on structural coverage
    metrics from Step 5 (coverage_report.json).
    
    Scoring algorithm:
    1. Load coverage metrics from report
    2. Use existing weighted score from Step 5
    3. Validate against thresholds
    4. Generate recommendations for improvement
    5. Create ComponentScore
    """
    
    def __init__(
        self,
        config: Optional[CoverageScoringConfig] = None,
        coverage_report_path: Optional[Path] = None
    ):
        """
        Initialize coverage scorer
        
        Args:
            config: Scoring configuration
            coverage_report_path: Path to coverage_report.json (optional)
        """
        self.config = config or CoverageScoringConfig()
        self.coverage_report_path = coverage_report_path
        self.coverage_metrics: Optional[CoverageMetrics] = None
    
    def score(
        self,
        coverage_report_path: Optional[Path] = None
    ) -> ComponentScore:
        """
        Calculate coverage component score
        
        Args:
            coverage_report_path: Path to coverage_report.json from Step 5
        
        Returns:
            ComponentScore for structural coverage
        
        Raises:
            FileNotFoundError: If coverage report not found
            ValueError: If coverage report format is invalid
        """
        # Use provided path or configured path
        report_path = coverage_report_path or self.coverage_report_path
        
        if not report_path:
            raise ValueError("Coverage report path not provided")
        
        if not Path(report_path).exists():
            raise FileNotFoundError(f"Coverage report not found: {report_path}")
        
        logger.info(f"Scoring coverage from: {report_path}")
        
        # Load coverage metrics
        self.coverage_metrics = CoverageMetrics.from_coverage_report(report_path)
        
        # Calculate score (use weighted score from Step 5)
        score_value = self.coverage_metrics.weighted_score
        
        # Validate thresholds
        threshold_met = self._check_thresholds()
        
        # Generate raw metrics dictionary
        raw_metrics = self._get_raw_metrics()
        
        # Generate recommendations
        recommendations = self._generate_recommendations()
        
        # Generate details
        details = self._generate_details()
        
        # Create component score
        component_score = ComponentScore(
            component_type=ComponentType.STRUCTURAL_COVERAGE,
            value=score_value,
            weight=self.config.weight,
            raw_metrics=raw_metrics,
            threshold_met=threshold_met,
            threshold_value=self.config.overall_threshold / 100.0,
            details=details,
            recommendations=recommendations,
        )
        
        logger.info(
            f"Coverage score: {score_value:.4f} "
            f"({component_score.percentage:.2f}%) - "
            f"{'PASS' if threshold_met else 'FAIL'}"
        )
        
        return component_score
    
    def _check_thresholds(self) -> bool:
        """
        Check if coverage meets all thresholds
        
        Returns:
            True if all thresholds are met
        """
        if not self.coverage_metrics:
            return False
        
        # Check individual thresholds
        checks = [
            self.coverage_metrics.line_coverage >= self.config.line_threshold,
            self.coverage_metrics.branch_coverage >= self.config.branch_threshold,
            self.coverage_metrics.toggle_coverage >= self.config.toggle_threshold,
            self.coverage_metrics.fsm_coverage >= self.config.fsm_threshold,
        ]
        
        # Check overall threshold
        overall_pct = self.coverage_metrics.weighted_score * 100.0
        checks.append(overall_pct >= self.config.overall_threshold)
        
        return all(checks)
    
    def _get_raw_metrics(self) -> Dict[str, Any]:
        """
        Get raw coverage metrics
        
        Returns:
            Dictionary of raw metrics
        """
        if not self.coverage_metrics:
            return {}
        
        return {
            "line_coverage": self.coverage_metrics.line_coverage,
            "branch_coverage": self.coverage_metrics.branch_coverage,
            "toggle_coverage": self.coverage_metrics.toggle_coverage,
            "fsm_coverage": self.coverage_metrics.fsm_coverage,
            "weighted_score": self.coverage_metrics.weighted_score,
            "source_report": self.coverage_metrics.source_report,
        }
    
    def _generate_details(self) -> str:
        """
        Generate human-readable details
        
        Returns:
            Details string
        """
        if not self.coverage_metrics:
            return "Coverage metrics not available"
        
        m = self.coverage_metrics
        
        details = (
            f"Structural Coverage: {m.weighted_score * 100:.2f}%\n"
            f"  Line:   {m.line_coverage:.2f}%\n"
            f"  Branch: {m.branch_coverage:.2f}%\n"
            f"  Toggle: {m.toggle_coverage:.2f}%\n"
            f"  FSM:    {m.fsm_coverage:.2f}%"
        )
        
        return details
    
    def _generate_recommendations(self) -> List[str]:
        """
        Generate recommendations for improving coverage
        
        Returns:
            List of recommendation strings
        """
        if not self.coverage_metrics:
            return []
        
        recommendations = []
        m = self.coverage_metrics
        
        # Line coverage recommendations
        if m.line_coverage < self.config.line_threshold:
            gap = self.config.line_threshold - m.line_coverage
            recommendations.append(
                f"Increase line coverage by {gap:.1f}% to meet {self.config.line_threshold}% threshold. "
                f"Add tests to exercise uncovered code paths."
            )
        
        # Branch coverage recommendations
        if m.branch_coverage < self.config.branch_threshold:
            gap = self.config.branch_threshold - m.branch_coverage
            recommendations.append(
                f"Increase branch coverage by {gap:.1f}% to meet {self.config.branch_threshold}% threshold. "
                f"Add tests for both true and false conditions in if/case statements."
            )
        
        # Toggle coverage recommendations
        if m.toggle_coverage < self.config.toggle_threshold:
            gap = self.config.toggle_threshold - m.toggle_coverage
            recommendations.append(
                f"Increase toggle coverage by {gap:.1f}% to meet {self.config.toggle_threshold}% threshold. "
                f"Ensure signals transition between 0 and 1 in both directions."
            )
        
        # FSM coverage recommendations
        if m.fsm_coverage < self.config.fsm_threshold:
            gap = self.config.fsm_threshold - m.fsm_coverage
            recommendations.append(
                f"Increase FSM coverage by {gap:.1f}% to meet {self.config.fsm_threshold}% threshold. "
                f"Add tests to exercise all FSM states and transitions."
            )
        
        # Overall coverage recommendation
        overall_pct = m.weighted_score * 100.0
        if overall_pct < self.config.overall_threshold:
            gap = self.config.overall_threshold - overall_pct
            recommendations.append(
                f"Increase overall coverage by {gap:.1f}% to meet {self.config.overall_threshold}% threshold. "
                f"Focus on the coverage types with the largest gaps."
            )
        
        # If coverage is good, suggest stretch goals
        if not recommendations:
            if overall_pct < 95.0:
                recommendations.append(
                    "Coverage meets all thresholds. Consider aiming for 95%+ for excellent quality."
                )
        
        return recommendations
    
    def generate_improvements(self) -> List[Improvement]:
        """
        Generate actionable improvements for coverage
        
        Returns:
            List of Improvement objects with specific actions
        """
        if not self.coverage_metrics:
            return []
        
        improvements = []
        m = self.coverage_metrics
        
        # Line coverage improvement
        if m.line_coverage < self.config.line_threshold:
            impact = (self.config.line_threshold - m.line_coverage) / 100.0 * 0.35  # Line weight
            improvements.append(Improvement(
                component=ComponentType.STRUCTURAL_COVERAGE,
                priority="high" if impact > 0.10 else "medium",
                current_value=m.line_coverage,
                target_value=self.config.line_threshold,
                impact=impact,
                actions=[
                    "Review coverage report to identify uncovered lines",
                    "Add directed tests for uncovered code paths",
                    "Consider corner cases and error conditions",
                    "Use coverage-driven test generation",
                ]
            ))
        
        # Branch coverage improvement
        if m.branch_coverage < self.config.branch_threshold:
            impact = (self.config.branch_threshold - m.branch_coverage) / 100.0 * 0.35  # Branch weight
            improvements.append(Improvement(
                component=ComponentType.STRUCTURAL_COVERAGE,
                priority="high" if impact > 0.10 else "medium",
                current_value=m.branch_coverage,
                target_value=self.config.branch_threshold,
                impact=impact,
                actions=[
                    "Identify partially covered branches in report",
                    "Add tests for both true/false conditions",
                    "Test boundary conditions thoroughly",
                    "Verify all case statement branches",
                ]
            ))
        
        # Toggle coverage improvement
        if m.toggle_coverage < self.config.toggle_threshold:
            impact = (self.config.toggle_threshold - m.toggle_coverage) / 100.0 * 0.20  # Toggle weight
            improvements.append(Improvement(
                component=ComponentType.STRUCTURAL_COVERAGE,
                priority="medium" if impact > 0.05 else "low",
                current_value=m.toggle_coverage,
                target_value=self.config.toggle_threshold,
                impact=impact,
                actions=[
                    "Check for signals that never toggle",
                    "Add tests to exercise full signal range",
                    "Test reset and initialization paths",
                    "Verify bidirectional signal behavior",
                ]
            ))
        
        # FSM coverage improvement
        if m.fsm_coverage < self.config.fsm_threshold and m.fsm_coverage > 0:
            impact = (self.config.fsm_threshold - m.fsm_coverage) / 100.0 * 0.10  # FSM weight
            improvements.append(Improvement(
                component=ComponentType.STRUCTURAL_COVERAGE,
                priority="medium" if impact > 0.05 else "low",
                current_value=m.fsm_coverage,
                target_value=self.config.fsm_threshold,
                impact=impact,
                actions=[
                    "Identify uncovered FSM states",
                    "Add tests for edge case state transitions",
                    "Test error recovery states",
                    "Verify all state machine paths",
                ]
            ))
        
        # Sort by impact (highest first)
        improvements.sort(key=lambda x: x.impact, reverse=True)
        
        return improvements
    
    def get_coverage_breakdown(self) -> Dict[str, Any]:
        """
        Get detailed coverage breakdown for reporting
        
        Returns:
            Dictionary with coverage breakdown
        """
        if not self.coverage_metrics:
            return {}
        
        m = self.coverage_metrics
        
        return {
            "overall": {
                "score": m.weighted_score,
                "percentage": m.weighted_score * 100.0,
                "threshold": self.config.overall_threshold,
                "meets_threshold": m.weighted_score * 100.0 >= self.config.overall_threshold,
            },
            "line": {
                "percentage": m.line_coverage,
                "threshold": self.config.line_threshold,
                "meets_threshold": m.line_coverage >= self.config.line_threshold,
                "gap": max(0, self.config.line_threshold - m.line_coverage),
            },
            "branch": {
                "percentage": m.branch_coverage,
                "threshold": self.config.branch_threshold,
                "meets_threshold": m.branch_coverage >= self.config.branch_threshold,
                "gap": max(0, self.config.branch_threshold - m.branch_coverage),
            },
            "toggle": {
                "percentage": m.toggle_coverage,
                "threshold": self.config.toggle_threshold,
                "meets_threshold": m.toggle_coverage >= self.config.toggle_threshold,
                "gap": max(0, self.config.toggle_threshold - m.toggle_coverage),
            },
            "fsm": {
                "percentage": m.fsm_coverage,
                "threshold": self.config.fsm_threshold,
                "meets_threshold": m.fsm_coverage >= self.config.fsm_threshold,
                "gap": max(0, self.config.fsm_threshold - m.fsm_coverage),
            },
        }


# =============================================================================
# CONVENIENCE FUNCTIONS
# =============================================================================

def score_coverage(
    coverage_report_path: Path,
    weight: float = 0.50,
    thresholds: Optional[Dict[str, float]] = None
) -> ComponentScore:
    """
    Convenience function to score coverage
    
    Args:
        coverage_report_path: Path to coverage_report.json
        weight: Weight for this component (default: 0.50 for Tier 1)
        thresholds: Optional threshold overrides
    
    Returns:
        ComponentScore for structural coverage
    
    Example:
        >>> score = score_coverage(
        ...     Path(".tbeval/coverage/coverage_report.json"),
        ...     weight=0.25  # Tier 2 weight
        ... )
        >>> print(f"Coverage: {score.percentage:.2f}%")
    """
    # Create config with thresholds
    config = CoverageScoringConfig(weight=weight)
    
    if thresholds:
        config.line_threshold = thresholds.get("line", config.line_threshold)
        config.branch_threshold = thresholds.get("branch", config.branch_threshold)
        config.toggle_threshold = thresholds.get("toggle", config.toggle_threshold)
        config.fsm_threshold = thresholds.get("fsm", config.fsm_threshold)
        config.overall_threshold = thresholds.get("overall", config.overall_threshold)
    
    # Create scorer and calculate score
    scorer = CoverageScorer(config=config)
    return scorer.score(coverage_report_path)


def get_coverage_metrics(coverage_report_path: Path) -> CoverageMetrics:
    """
    Load coverage metrics from report
    
    Args:
        coverage_report_path: Path to coverage_report.json
    
    Returns:
        CoverageMetrics object
    
    Example:
        >>> metrics = get_coverage_metrics(Path("coverage_report.json"))
        >>> print(f"Line: {metrics.line_coverage:.2f}%")
    """
    return CoverageMetrics.from_coverage_report(coverage_report_path)


# =============================================================================
# EXAMPLE USAGE
# =============================================================================

if __name__ == "__main__":
    import sys
    import json
    
    # Setup logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(levelname)s - %(message)s'
    )
    
    # Check if coverage report provided
    if len(sys.argv) < 2:
        print("Usage: python -m step7_score.scorers.coverage_scorer <coverage_report.json>")
        sys.exit(1)
    
    coverage_report = Path(sys.argv[1])
    
    if not coverage_report.exists():
        print(f"Error: Coverage report not found: {coverage_report}")
        sys.exit(1)
    
    print("=" * 60)
    print("COVERAGE SCORING")
    print("=" * 60)
    
    # Create scorer
    config = CoverageScoringConfig(
        weight=0.50,
        line_threshold=80.0,
        branch_threshold=90.0,
        toggle_threshold=70.0,
        fsm_threshold=75.0,
        overall_threshold=80.0,
    )
    
    scorer = CoverageScorer(config=config)
    
    # Calculate score
    try:
        score = scorer.score(coverage_report)
        
        print(f"\nComponent Score:")
        print(f"  Value:       {score.value:.4f}")
        print(f"  Percentage:  {score.percentage:.2f}%")
        print(f"  Grade:       {score.grade.value}")
        print(f"  Weight:      {score.weight}")
        print(f"  Contribution: {score.weighted_contribution:.4f}")
        print(f"  Threshold Met: {'✓ YES' if score.threshold_met else '✗ NO'}")
        
        print(f"\nDetails:")
        print(score.details)
        
        if score.recommendations:
            print(f"\nRecommendations:")
            for i, rec in enumerate(score.recommendations, 1):
                print(f"  {i}. {rec}")
        
        # Get coverage breakdown
        breakdown = scorer.get_coverage_breakdown()
        print(f"\nCoverage Breakdown:")
        print(json.dumps(breakdown, indent=2))
        
        # Generate improvements
        improvements = scorer.generate_improvements()
        if improvements:
            print(f"\nActionable Improvements:")
            for i, imp in enumerate(improvements, 1):
                print(f"\n{i}. {imp.component.display_name}")
                print(f"   Priority: {imp.priority.upper()}")
                print(f"   Current:  {imp.current_value:.2f}%")
                print(f"   Target:   {imp.target_value:.2f}%")
                print(f"   Impact:   {imp.impact:.4f} score points")
                print(f"   Actions:")
                for action in imp.actions:
                    print(f"     • {action}")
        
        # Export to JSON
        output = {
            "component_score": score.to_dict(),
            "breakdown": breakdown,
            "improvements": [imp.to_dict() for imp in improvements],
        }
        
        output_path = Path("coverage_score.json")
        with open(output_path, 'w') as f:
            json.dump(output, f, indent=2)
        
        print(f"\n✓ Score exported to: {output_path}")
        
        sys.exit(0 if score.threshold_met else 1)
    
    except Exception as e:
        print(f"\n✗ Error scoring coverage: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
