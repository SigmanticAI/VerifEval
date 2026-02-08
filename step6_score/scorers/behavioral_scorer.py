"""
Behavioral accuracy scorer for Step 7: Scoring

Scores behavioral accuracy component based on heuristic analysis:
- Assertion count (more assertions = better verification)
- Test scenario diversity (different test types)
- Test naming quality (descriptive names)
- Stimulus variety (range of inputs tested)

Used by Tier 1 scoring system (heuristic approximation).
For Tier 2, this is replaced by actual functional coverage and assertion
coverage from Questa.

The behavioral score estimates how well tests verify design behavior
beyond just structural coverage.

Author: TB Eval Team
Version: 0.1.0
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Dict, List, Any, Set
import logging
import re
import json

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
class BehavioralScoringConfig:
    """
    Configuration for behavioral accuracy scoring
    
    Attributes:
        weight: Weight for this component in overall score
        min_assertions_per_test: Minimum expected assertions per test
        scenario_diversity_weight: Weight for test scenario diversity
        assertion_weight: Weight for assertion count
        naming_weight: Weight for test naming quality
    """
    weight: float = 0.05  # Default Tier 1 weight (small - it's heuristic)
    min_assertions_per_test: float = 3.0  # Minimum expected
    scenario_diversity_weight: float = 0.40
    assertion_weight: float = 0.40
    naming_weight: float = 0.20


# =============================================================================
# BEHAVIORAL SCORER
# =============================================================================

class BehavioralScorer:
    """
    Score behavioral accuracy component (heuristic-based)
    
    This scorer provides a heuristic estimate of behavioral verification
    quality when Questa functional coverage is not available.
    
    Heuristics used:
    1. Assertion count: More assertions = better verification
    2. Test scenario diversity: Different test types (reset, overflow, etc.)
    3. Test naming: Descriptive names indicate behavioral intent
    4. Test complexity: Longer tests may verify more behavior
    
    Note: This is an approximation. For precise behavioral coverage,
    use Tier 2 with Questa functional coverage.
    
    Scoring algorithm:
    1. Load test execution metrics from Step 4
    2. Analyze test structure (names, assertions, patterns)
    3. Calculate heuristic scores
    4. Combine into overall behavioral score
    """
    
    # Behavioral test patterns (common test naming conventions)
    SCENARIO_PATTERNS = {
        'reset': r'reset|rst|init',
        'basic': r'basic|simple|sanity',
        'corner': r'corner|edge|boundary|limit',
        'error': r'error|fail|invalid|illegal',
        'overflow': r'overflow|underflow|wrap',
        'stress': r'stress|random|exhaustive',
        'timing': r'timing|delay|sync|async',
        'protocol': r'protocol|handshake|sequence',
    }
    
    def __init__(
        self,
        config: Optional[BehavioralScoringConfig] = None,
        test_report_path: Optional[Path] = None
    ):
        """
        Initialize behavioral scorer
        
        Args:
            config: Scoring configuration
            test_report_path: Path to test_report.json (optional)
        """
        self.config = config or BehavioralScoringConfig()
        self.test_report_path = test_report_path
        self.test_metrics: Optional[TestExecutionMetrics] = None
        self.test_report_data: Optional[Dict] = None
    
    def score(
        self,
        test_report_path: Optional[Path] = None
    ) -> ComponentScore:
        """
        Calculate behavioral accuracy component score
        
        Args:
            test_report_path: Path to test_report.json from Step 4
        
        Returns:
            ComponentScore for behavioral accuracy
        
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
        
        logger.info(f"Scoring behavioral accuracy from: {report_path}")
        
        # Load test execution metrics
        self.test_metrics = TestExecutionMetrics.from_test_report(report_path)
        
        # Load full test report for detailed analysis
        with open(report_path) as f:
            self.test_report_data = json.load(f)
        
        # Calculate behavioral score (heuristic)
        score_value = self._calculate_behavioral_score()
        
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
            component_type=ComponentType.BEHAVIORAL_ACCURACY,
            value=score_value,
            weight=self.config.weight,
            raw_metrics=raw_metrics,
            threshold_met=threshold_met,
            threshold_value=0.60,  # 60% minimum (it's heuristic)
            details=details,
            recommendations=recommendations,
        )
        
        logger.info(
            f"Behavioral score: {score_value:.4f} "
            f"({component_score.percentage:.2f}%) - "
            f"{'PASS' if threshold_met else 'FAIL'}"
        )
        
        return component_score
    
    def _calculate_behavioral_score(self) -> float:
        """
        Calculate heuristic behavioral accuracy score
        
        Returns:
            Score value (0.0-1.0)
        """
        # Calculate sub-scores
        assertion_score = self._calculate_assertion_score()
        diversity_score = self._calculate_diversity_score()
        naming_score = self._calculate_naming_score()
        
        # Weighted combination
        overall_score = (
            assertion_score * self.config.assertion_weight +
            diversity_score * self.config.scenario_diversity_weight +
            naming_score * self.config.naming_weight
        )
        
        return min(1.0, max(0.0, overall_score))
    
    def _calculate_assertion_score(self) -> float:
        """
        Calculate score based on assertion count
        
        Returns:
            Assertion score (0.0-1.0)
        """
        # Try to extract assertion count from test report
        assertion_count = self._extract_assertion_count()
        
        if assertion_count == 0:
            logger.warning("No assertions found - using default low score")
            return 0.5  # Neutral-low
        
        # Calculate assertions per test
        total_tests = self.test_metrics.total_tests
        assertions_per_test = assertion_count / max(total_tests, 1)
        
        # Score: 1.0 if >= min_assertions_per_test, scales below
        target = self.config.min_assertions_per_test
        if assertions_per_test >= target:
            score = 1.0
        else:
            score = assertions_per_test / target
        
        return min(1.0, score)
    
    def _calculate_diversity_score(self) -> float:
        """
        Calculate score based on test scenario diversity
        
        Returns:
            Diversity score (0.0-1.0)
        """
        # Extract test names
        test_names = self._extract_test_names()
        
        if not test_names:
            return 0.5  # Neutral
        
        # Count scenario types covered
        scenarios_found = set()
        for test_name in test_names:
            test_name_lower = test_name.lower()
            for scenario, pattern in self.SCENARIO_PATTERNS.items():
                if re.search(pattern, test_name_lower):
                    scenarios_found.add(scenario)
        
        # Score: percentage of scenario types covered
        # Full coverage = all 8 scenario types
        diversity_ratio = len(scenarios_found) / len(self.SCENARIO_PATTERNS)
        
        # Also reward having multiple tests per scenario
        if len(test_names) >= len(self.SCENARIO_PATTERNS) * 2:
            diversity_ratio = min(1.0, diversity_ratio * 1.2)
        
        return min(1.0, diversity_ratio)
    
    def _calculate_naming_score(self) -> float:
        """
        Calculate score based on test naming quality
        
        Returns:
            Naming score (0.0-1.0)
        """
        test_names = self._extract_test_names()
        
        if not test_names:
            return 0.5  # Neutral
        
        quality_count = 0
        
        for name in test_names:
            # Good naming indicators:
            # - Starts with "test_"
            # - Has descriptive words (not just "test_1")
            # - Uses underscores (snake_case)
            # - Reasonable length (10-50 chars)
            
            if name.startswith('test_'):
                quality_count += 1
            
            if len(name) >= 10 and len(name) <= 50:
                quality_count += 1
            
            if '_' in name[5:]:  # Has underscores beyond "test_"
                quality_count += 1
            
            # Not just numbered (test_1, test_2, etc.)
            if not re.match(r'test_\d+$', name):
                quality_count += 1
        
        # Score: average quality per test (max 4 points per test)
        max_points = len(test_names) * 4
        if max_points == 0:
            return 0.5
        
        score = quality_count / max_points
        return min(1.0, score)
    
    def _extract_assertion_count(self) -> int:
        """
        Extract total assertion count from test report
        
        Returns:
            Total number of assertions across all tests
        """
        if not self.test_report_data:
            return 0
        
        # Look for assertion count in test report
        # Common locations:
        # - test_report["metadata"]["assertions"]
        # - test_report["tests"][i]["assertions"]
        # - test_report["summary"]["total_assertions"]
        
        total = 0
        
        # Try metadata
        if "metadata" in self.test_report_data:
            total += self.test_report_data["metadata"].get("assertions", 0)
        
        # Try summary
        if "summary" in self.test_report_data:
            total += self.test_report_data["summary"].get("total_assertions", 0)
        
        # Try per-test
        if "tests" in self.test_report_data:
            for test in self.test_report_data["tests"]:
                total += test.get("assertions", 0)
                total += test.get("assertion_count", 0)
        
        # If still zero, estimate from test count (conservative)
        if total == 0 and self.test_metrics:
            # Assume at least 1 assertion per test (very conservative)
            total = self.test_metrics.total_tests
        
        return total
    
    def _extract_test_names(self) -> List[str]:
        """
        Extract test names from test report
        
        Returns:
            List of test names
        """
        if not self.test_report_data:
            return []
        
        test_names = []
        
        # Try tests array
        if "tests" in self.test_report_data:
            for test in self.test_report_data["tests"]:
                name = test.get("name") or test.get("test_name") or test.get("id")
                if name:
                    test_names.append(name)
        
        # Try test_cases
        if "test_cases" in self.test_report_data:
            for test in self.test_report_data["test_cases"]:
                name = test.get("name") or test.get("test_name")
                if name:
                    test_names.append(name)
        
        return test_names
    
    def _check_thresholds(self) -> bool:
        """
        Check if behavioral score meets threshold
        
        Returns:
            True if threshold is met
        """
        # Behavioral score is heuristic - use lower threshold
        return self._calculate_behavioral_score() >= 0.60
    
    def _get_raw_metrics(self) -> Dict[str, Any]:
        """
        Get raw behavioral metrics
        
        Returns:
            Dictionary of raw metrics
        """
        assertion_count = self._extract_assertion_count()
        test_names = self._extract_test_names()
        
        # Find scenarios covered
        scenarios_found = set()
        for test_name in test_names:
            test_name_lower = test_name.lower()
            for scenario, pattern in self.SCENARIO_PATTERNS.items():
                if re.search(pattern, test_name_lower):
                    scenarios_found.add(scenario)
        
        return {
            "assertion_count": assertion_count,
            "assertions_per_test": assertion_count / max(self.test_metrics.total_tests, 1),
            "test_count": len(test_names),
            "scenario_types_covered": len(scenarios_found),
            "scenarios": list(scenarios_found),
            "heuristic_based": True,
            "note": "This is a heuristic estimate. Use Tier 2 (Questa) for accurate behavioral coverage.",
        }
    
    def _generate_details(self) -> str:
        """
        Generate human-readable details
        
        Returns:
            Details string
        """
        assertion_count = self._extract_assertion_count()
        test_names = self._extract_test_names()
        
        scenarios_found = set()
        for test_name in test_names:
            test_name_lower = test_name.lower()
            for scenario, pattern in self.SCENARIO_PATTERNS.items():
                if re.search(pattern, test_name_lower):
                    scenarios_found.add(scenario)
        
        assertions_per_test = assertion_count / max(len(test_names), 1)
        
        details = (
            f"Behavioral Accuracy: {self._calculate_behavioral_score() * 100:.2f}% (heuristic)\n"
            f"  Assertions: {assertion_count} total ({assertions_per_test:.1f} per test)\n"
            f"  Scenarios:  {len(scenarios_found)}/{len(self.SCENARIO_PATTERNS)} types covered\n"
            f"  Test Names: {'Good' if self._calculate_naming_score() > 0.7 else 'Needs improvement'}\n"
            f"\n"
            f"Note: This is a heuristic estimate based on test structure.\n"
            f"      For accurate behavioral coverage, use Tier 2 with Questa."
        )
        
        return details
    
    def _generate_recommendations(self) -> List[str]:
        """
        Generate recommendations for improving behavioral accuracy
        
        Returns:
            List of recommendation strings
        """
        recommendations = []
        
        assertion_score = self._calculate_assertion_score()
        diversity_score = self._calculate_diversity_score()
        naming_score = self._calculate_naming_score()
        
        # Assertion recommendations
        if assertion_score < 0.70:
            assertion_count = self._extract_assertion_count()
            target_count = int(self.test_metrics.total_tests * self.config.min_assertions_per_test)
            gap = max(0, target_count - assertion_count)
            
            recommendations.append(
                f"Add more assertions to tests (current: {assertion_count}, target: ~{target_count}). "
                f"Assertions verify behavioral correctness beyond structural coverage."
            )
        
        # Diversity recommendations
        if diversity_score < 0.70:
            test_names = self._extract_test_names()
            scenarios_found = set()
            for test_name in test_names:
                test_name_lower = test_name.lower()
                for scenario, pattern in self.SCENARIO_PATTERNS.items():
                    if re.search(pattern, test_name_lower):
                        scenarios_found.add(scenario)
            
            missing_scenarios = set(self.SCENARIO_PATTERNS.keys()) - scenarios_found
            
            recommendations.append(
                f"Improve test scenario diversity. Missing scenarios: {', '.join(missing_scenarios)}. "
                f"Add tests for: reset conditions, corner cases, error handling, stress testing."
            )
        
        # Naming recommendations
        if naming_score < 0.70:
            recommendations.append(
                "Improve test naming. Use descriptive names that indicate behavior being tested. "
                "Example: 'test_fifo_overflow_wraps_correctly' instead of 'test_1'."
            )
        
        # General recommendation
        if not recommendations:
            recommendations.append(
                "Behavioral verification looks good (based on heuristics). "
                "Consider upgrading to Tier 2 with Questa for precise functional coverage analysis."
            )
        
        return recommendations
    
    def generate_improvements(self) -> List[Improvement]:
        """
        Generate actionable improvements for behavioral accuracy
        
        Returns:
            List of Improvement objects with specific actions
        """
        improvements = []
        
        assertion_score = self._calculate_assertion_score()
        diversity_score = self._calculate_diversity_score()
        
        # Assertion improvement
        if assertion_score < 0.80:
            impact = (0.80 - assertion_score) * self.config.assertion_weight * self.config.weight
            
            improvements.append(Improvement(
                component=ComponentType.BEHAVIORAL_ACCURACY,
                priority="medium",
                current_value=assertion_score * 100,
                target_value=80.0,
                impact=impact,
                actions=[
                    "Add assertions to verify output correctness",
                    "Check state machine transitions with assertions",
                    "Verify protocol compliance with assertions",
                    "Add temporal assertions (assert_eventually, etc.)",
                    "Document expected behavior in assertion messages",
                ]
            ))
        
        # Diversity improvement
        if diversity_score < 0.80:
            impact = (0.80 - diversity_score) * self.config.scenario_diversity_weight * self.config.weight
            
            improvements.append(Improvement(
                component=ComponentType.BEHAVIORAL_ACCURACY,
                priority="medium",
                current_value=diversity_score * 100,
                target_value=80.0,
                impact=impact,
                actions=[
                    "Add reset/initialization tests",
                    "Add boundary/corner case tests",
                    "Add error injection tests",
                    "Add stress/random tests",
                    "Add timing/synchronization tests",
                ]
            ))
        
        # Sort by impact
        improvements.sort(key=lambda x: x.impact, reverse=True)
        
        return improvements


# =============================================================================
# CONVENIENCE FUNCTIONS
# =============================================================================

def score_behavioral_accuracy(
    test_report_path: Path,
    weight: float = 0.05
) -> ComponentScore:
    """
    Convenience function to score behavioral accuracy
    
    Args:
        test_report_path: Path to test_report.json
        weight: Weight for this component (default: 0.05 for Tier 1)
    
    Returns:
        ComponentScore for behavioral accuracy
    
    Example:
        >>> score = score_behavioral_accuracy(
        ...     Path(".tbeval/test_runs/test_report.json"),
        ...     weight=0.05
        ... )
        >>> print(f"Behavioral: {score.percentage:.2f}%")
    """
    config = BehavioralScoringConfig(weight=weight)
    scorer = BehavioralScorer(config=config)
    return scorer.score(test_report_path)


# =============================================================================
# EXAMPLE USAGE
# =============================================================================

if __name__ == "__main__":
    import sys
    
    # Setup logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(levelname)s - %(message)s'
    )
    
    # Check if test report provided
    if len(sys.argv) < 2:
        print("Usage: python -m step7_score.scorers.behavioral_scorer <test_report.json>")
        sys.exit(1)
    
    test_report = Path(sys.argv[1])
    
    if not test_report.exists():
        print(f"Error: Test report not found: {test_report}")
        sys.exit(1)
    
    print("=" * 60)
    print("BEHAVIORAL ACCURACY SCORING (HEURISTIC)")
    print("=" * 60)
    
    # Create scorer
    config = BehavioralScoringConfig(
        weight=0.05,
        min_assertions_per_test=3.0,
    )
    
    scorer = BehavioralScorer(config=config)
    
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
        
        # Raw metrics
        print(f"\nRaw Metrics:")
        print(json.dumps(score.raw_metrics, indent=2))
        
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
            "improvements": [imp.to_dict() for imp in improvements],
        }
        
        output_path = Path("behavioral_score.json")
        with open(output_path, 'w') as f:
            json.dump(output, f, indent=2)
        
        print(f"\n✓ Score exported to: {output_path}")
        
        sys.exit(0 if score.threshold_met else 1)
    
    except Exception as e:
        print(f"\n✗ Error scoring behavioral accuracy: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
