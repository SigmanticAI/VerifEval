"""
Test pass rate scorer for Step 7: Scoring

Scores test pass rate component based on:
- Test pass/fail ratio
- Error handling
- Test reliability
- Execution stability

Used by Tier 1 scoring system (higher weight when tests are primary metric).

A high pass rate indicates reliable, well-written tests that consistently
verify design correctness.

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
    TestExecutionMetrics,
    Improvement,
)

logger = logging.getLogger(__name__)


# =============================================================================
# CONFIGURATION
# =============================================================================

@dataclass
class PassRateScoringConfig:
    """
    Configuration for pass rate scoring
    
    Attributes:
        weight: Weight for this component in overall score
        min_pass_rate: Minimum acceptable pass rate (0.0-1.0)
        allow_errors: Whether errors are acceptable (vs. only fails)
        error_penalty: Penalty multiplier for errors vs. failures
    """
    weight: float = 0.20  # Default Tier 1 weight
    min_pass_rate: float = 0.90  # 90% minimum
    allow_errors: bool = False  # Errors are worse than failures
    error_penalty: float = 1.5  # Errors count 1.5x worse than failures


# =============================================================================
# PASS RATE SCORER
# =============================================================================

class TestPassRateScorer:
    """
    Score test pass rate component
    
    This scorer evaluates how many tests pass vs. fail/error.
    A high pass rate indicates:
    - Well-written tests
    - Correct implementation
    - Reliable testbench
    - Stable execution
    
    Scoring algorithm:
    1. Load test execution metrics from Step 4
    2. Calculate pass rate: passed / total
    3. Apply penalty for errors (worse than failures)
    4. Validate against threshold
    5. Generate recommendations for fixing failures
    """
    
    def __init__(
        self,
        config: Optional[PassRateScoringConfig] = None,
        test_report_path: Optional[Path] = None
    ):
        """
        Initialize pass rate scorer
        
        Args:
            config: Scoring configuration
            test_report_path: Path to test_report.json (optional)
        """
        self.config = config or PassRateScoringConfig()
        self.test_report_path = test_report_path
        self.test_metrics: Optional[TestExecutionMetrics] = None
    
    def score(
        self,
        test_report_path: Optional[Path] = None
    ) -> ComponentScore:
        """
        Calculate pass rate component score
        
        Args:
            test_report_path: Path to test_report.json from Step 4
        
        Returns:
            ComponentScore for test pass rate
        
        Raises:
            FileNotFoundError: If test report not found
            ValueError: If report format is invalid
        """
        # Use provided path or configured path
        report_path = test_report_path or self.test_report_path
        
        if not report_path:
            raise ValueError("Test report path not provided")
        
        if not Path(report_path).exists():
            raise FileNotFoundError(f"Test report not found: {report_path}")
        
        logger.info(f"Scoring test pass rate from: {report_path}")
        
        # Load test execution metrics
        self.test_metrics = TestExecutionMetrics.from_test_report(report_path)
        
        # Calculate pass rate score
        score_value = self._calculate_pass_rate_score()
        
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
            component_type=ComponentType.TEST_PASS_RATE,
            value=score_value,
            weight=self.config.weight,
            raw_metrics=raw_metrics,
            threshold_met=threshold_met,
            threshold_value=self.config.min_pass_rate,
            details=details,
            recommendations=recommendations,
        )
        
        logger.info(
            f"Pass rate score: {score_value:.4f} "
            f"({component_score.percentage:.2f}%) - "
            f"{'PASS' if threshold_met else 'FAIL'}"
        )
        
        return component_score
    
    def _calculate_pass_rate_score(self) -> float:
        """
        Calculate pass rate score with error penalty
        
        Returns:
            Score value (0.0-1.0)
        """
        if not self.test_metrics:
            return 0.0
        
        total = self.test_metrics.total_tests
        
        if total == 0:
            logger.warning("No tests found - returning 0.0 score")
            return 0.0
        
        passed = self.test_metrics.passed_tests
        failed = self.test_metrics.failed_tests
        errors = self.test_metrics.error_tests
        
        # Base pass rate
        base_pass_rate = passed / total
        
        # Apply error penalty if errors exist
        if errors > 0 and not self.config.allow_errors:
            # Errors are worse than failures - penalize more heavily
            error_impact = (errors * self.config.error_penalty) / total
            failed_impact = failed / total
            
            # Adjusted score accounts for error penalty
            score = max(0.0, base_pass_rate - error_impact - failed_impact + (failed / total))
        else:
            # Simple pass rate
            score = base_pass_rate
        
        return min(1.0, max(0.0, score))
    
    def _check_thresholds(self) -> bool:
        """
        Check if pass rate meets threshold
        
        Returns:
            True if threshold is met
        """
        if not self.test_metrics:
            return False
        
        # Check pass rate threshold
        pass_rate = self.test_metrics.pass_rate
        
        if pass_rate < self.config.min_pass_rate:
            return False
        
        # Check error requirement
        if not self.config.allow_errors and self.test_metrics.error_tests > 0:
            return False
        
        return True
    
    def _get_raw_metrics(self) -> Dict[str, Any]:
        """
        Get raw test metrics
        
        Returns:
            Dictionary of raw metrics
        """
        if not self.test_metrics:
            return {}
        
        return {
            "total_tests": self.test_metrics.total_tests,
            "passed_tests": self.test_metrics.passed_tests,
            "failed_tests": self.test_metrics.failed_tests,
            "error_tests": self.test_metrics.error_tests,
            "pass_rate": self.test_metrics.pass_rate,
            "source_report": self.test_metrics.source_report,
        }
    
    def _generate_details(self) -> str:
        """
        Generate human-readable details
        
        Returns:
            Details string
        """
        if not self.test_metrics:
            return "Test metrics not available"
        
        tm = self.test_metrics
        
        details = (
            f"Test Pass Rate: {tm.pass_rate * 100:.2f}%\n"
            f"  Total:  {tm.total_tests}\n"
            f"  Passed: {tm.passed_tests}\n"
            f"  Failed: {tm.failed_tests}\n"
            f"  Errors: {tm.error_tests}"
        )
        
        return details
    
    def _generate_recommendations(self) -> List[str]:
        """
        Generate recommendations for improving pass rate
        
        Returns:
            List of recommendation strings
        """
        if not self.test_metrics:
            return []
        
        recommendations = []
        tm = self.test_metrics
        
        # Failed tests recommendations
        if tm.failed_tests > 0:
            recommendations.append(
                f"Fix {tm.failed_tests} failing test(s). "
                f"Review test logs to identify root causes. "
                f"Common issues: incorrect expected values, timing issues, or design bugs."
            )
        
        # Error tests recommendations
        if tm.error_tests > 0:
            recommendations.append(
                f"Fix {tm.error_tests} test(s) with errors. "
                f"Errors indicate problems in test code itself (exceptions, syntax errors, etc.). "
                f"Review test implementation and fix Python/SystemVerilog errors."
            )
        
        # Pass rate threshold recommendation
        if tm.pass_rate < self.config.min_pass_rate:
            gap = (self.config.min_pass_rate - tm.pass_rate) * 100
            missing_passes = int(gap / 100.0 * tm.total_tests)
            recommendations.append(
                f"Increase pass rate by {gap:.1f}% to meet {self.config.min_pass_rate * 100:.0f}% threshold. "
                f"Need ~{missing_passes} more passing test(s)."
            )
        
        # If all tests pass, suggest additional tests
        if tm.pass_rate == 1.0:
            recommendations.append(
                "All tests passing! Consider adding more corner case tests to improve coverage."
            )
        
        return recommendations
    
    def generate_improvements(self) -> List[Improvement]:
        """
        Generate actionable improvements for pass rate
        
        Returns:
            List of Improvement objects with specific actions
        """
        if not self.test_metrics:
            return []
        
        improvements = []
        tm = self.test_metrics
        
        # Failed tests improvement
        if tm.failed_tests > 0:
            current_pct = tm.pass_rate * 100
            target_pct = min(100.0, self.config.min_pass_rate * 100)
            impact = (target_pct - current_pct) / 100.0 * self.config.weight
            
            improvements.append(Improvement(
                component=ComponentType.TEST_PASS_RATE,
                priority="high",
                current_value=current_pct,
                target_value=target_pct,
                impact=impact,
                actions=[
                    f"Debug and fix {tm.failed_tests} failing test(s)",
                    "Review test failure logs in test_report.json",
                    "Check for incorrect expected values",
                    "Verify timing and synchronization",
                    "Validate test assumptions against design spec",
                ]
            ))
        
        # Error tests improvement
        if tm.error_tests > 0:
            impact = tm.error_tests / tm.total_tests * self.config.weight * self.config.error_penalty
            
            improvements.append(Improvement(
                component=ComponentType.TEST_PASS_RATE,
                priority="high",
                current_value=0.0,  # Errors are failures
                target_value=100.0,  # Must fix
                impact=impact,
                actions=[
                    f"Fix {tm.error_tests} test(s) with runtime errors",
                    "Check for Python exceptions (NameError, TypeError, etc.)",
                    "Verify import statements and module paths",
                    "Fix syntax errors in test code",
                    "Add error handling (try/except) where appropriate",
                ]
            ))
        
        # Sort by impact (highest first)
        improvements.sort(key=lambda x: x.impact, reverse=True)
        
        return improvements
    
    def get_pass_rate_breakdown(self) -> Dict[str, Any]:
        """
        Get detailed pass rate breakdown for reporting
        
        Returns:
            Dictionary with pass rate breakdown
        """
        if not self.test_metrics:
            return {}
        
        tm = self.test_metrics
        
        return {
            "overall": {
                "pass_rate": tm.pass_rate,
                "percentage": tm.pass_rate * 100.0,
                "threshold": self.config.min_pass_rate,
                "meets_threshold": tm.pass_rate >= self.config.min_pass_rate,
            },
            "counts": {
                "total": tm.total_tests,
                "passed": tm.passed_tests,
                "failed": tm.failed_tests,
                "errors": tm.error_tests,
            },
            "status": {
                "all_pass": tm.failed_tests == 0 and tm.error_tests == 0,
                "has_failures": tm.failed_tests > 0,
                "has_errors": tm.error_tests > 0,
            },
        }


# =============================================================================
# CONVENIENCE FUNCTIONS
# =============================================================================

def score_test_pass_rate(
    test_report_path: Path,
    weight: float = 0.20,
    min_pass_rate: float = 0.90
) -> ComponentScore:
    """
    Convenience function to score test pass rate
    
    Args:
        test_report_path: Path to test_report.json
        weight: Weight for this component (default: 0.20 for Tier 1)
        min_pass_rate: Minimum acceptable pass rate (default: 0.90)
    
    Returns:
        ComponentScore for test pass rate
    
    Example:
        >>> score = score_test_pass_rate(
        ...     Path(".tbeval/test_runs/test_report.json"),
        ...     weight=0.20,
        ...     min_pass_rate=0.95
        ... )
        >>> print(f"Pass Rate: {score.percentage:.2f}%")
    """
    config = PassRateScoringConfig(
        weight=weight,
        min_pass_rate=min_pass_rate
    )
    
    scorer = TestPassRateScorer(config=config)
    return scorer.score(test_report_path)


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
    
    # Check if test report provided
    if len(sys.argv) < 2:
        print("Usage: python -m step7_score.scorers.test_pass_rate_scorer <test_report.json>")
        sys.exit(1)
    
    test_report = Path(sys.argv[1])
    
    if not test_report.exists():
        print(f"Error: Test report not found: {test_report}")
        sys.exit(1)
    
    print("=" * 60)
    print("TEST PASS RATE SCORING")
    print("=" * 60)
    
    # Create scorer
    config = PassRateScoringConfig(
        weight=0.20,
        min_pass_rate=0.90,
        allow_errors=False,
        error_penalty=1.5,
    )
    
    scorer = TestPassRateScorer(config=config)
    
    # Calculate score
    try:
        score = scorer.score(test_report)
        
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
        
        # Get pass rate breakdown
        breakdown = scorer.get_pass_rate_breakdown()
        print(f"\nPass Rate Breakdown:")
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
        
        output_path = Path("pass_rate_score.json")
        with open(output_path, 'w') as f:
            json.dump(output, f, indent=2)
        
        print(f"\n✓ Score exported to: {output_path}")
        
        sys.exit(0 if score.threshold_met else 1)
    
    except Exception as e:
        print(f"\n✗ Error scoring pass rate: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
