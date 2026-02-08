"""
Efficiency scorer for Step 7: Scoring

Scores test efficiency component based on:
- Runtime performance (execution speed)
- Memory usage (peak memory consumption)
- Coverage per time unit (efficiency of coverage gain)
- Test redundancy (overlapping coverage)

Used by both Tier 1 and Tier 2 scoring systems.

The efficiency score rewards fast, memory-efficient tests that
achieve high coverage with minimal redundancy.

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
    CoverageMetrics,
    EfficiencyMetrics,
    Improvement,
)

logger = logging.getLogger(__name__)


# =============================================================================
# CONFIGURATION
# =============================================================================

@dataclass
class EfficiencyScoringConfig:
    """
    Configuration for efficiency scoring
    
    Attributes:
        weight: Weight for this component in overall score
        max_acceptable_duration_per_test_ms: Max acceptable test duration (ms)
        max_acceptable_memory_mb: Max acceptable peak memory (MB)
        min_coverage_per_second: Min coverage gain per second
        runtime_weight: Weight for runtime in efficiency score
        memory_weight: Weight for memory in efficiency score
        coverage_speed_weight: Weight for coverage speed in efficiency score
    """
    weight: float = 0.10  # Default Tier 1 weight (0.05 for Tier 2)
    
    # Thresholds
    max_acceptable_duration_per_test_ms: float = 1000.0  # 1 second per test
    max_acceptable_memory_mb: float = 500.0  # 500 MB peak
    min_coverage_per_second: float = 0.01  # 1% coverage per second minimum
    
    # Sub-weights for efficiency calculation
    runtime_weight: float = 0.40
    memory_weight: float = 0.30
    coverage_speed_weight: float = 0.30


# =============================================================================
# EFFICIENCY SCORER
# =============================================================================

class EfficiencyScorer:
    """
    Score test efficiency component
    
    This scorer evaluates how efficiently the testbench achieves coverage.
    Good efficiency means fast tests, low memory usage, and high coverage
    gain per unit time.
    
    Scoring algorithm:
    1. Load test execution metrics from Step 4
    2. Load coverage metrics from Step 5
    3. Calculate efficiency metrics (runtime, memory, coverage speed)
    4. Compute weighted efficiency score
    5. Generate recommendations for optimization
    """
    
    def __init__(
        self,
        config: Optional[EfficiencyScoringConfig] = None,
        test_report_path: Optional[Path] = None,
        coverage_report_path: Optional[Path] = None
    ):
        """
        Initialize efficiency scorer
        
        Args:
            config: Scoring configuration
            test_report_path: Path to test_report.json (optional)
            coverage_report_path: Path to coverage_report.json (optional)
        """
        self.config = config or EfficiencyScoringConfig()
        self.test_report_path = test_report_path
        self.coverage_report_path = coverage_report_path
        self.test_metrics: Optional[TestExecutionMetrics] = None
        self.coverage_metrics: Optional[CoverageMetrics] = None
        self.efficiency_metrics: Optional[EfficiencyMetrics] = None
    
    def score(
        self,
        test_report_path: Optional[Path] = None,
        coverage_report_path: Optional[Path] = None
    ) -> ComponentScore:
        """
        Calculate efficiency component score
        
        Args:
            test_report_path: Path to test_report.json from Step 4
            coverage_report_path: Path to coverage_report.json from Step 5
        
        Returns:
            ComponentScore for test efficiency
        
        Raises:
            FileNotFoundError: If required reports not found
            ValueError: If report format is invalid
        """
        # Use provided paths or configured paths
        test_path = test_report_path or self.test_report_path
        coverage_path = coverage_report_path or self.coverage_report_path
        
        if not test_path:
            raise ValueError("Test report path not provided")
        
        if not Path(test_path).exists():
            raise FileNotFoundError(f"Test report not found: {test_path}")
        
        logger.info(f"Scoring efficiency from test report: {test_path}")
        
        # Load test execution metrics
        self.test_metrics = TestExecutionMetrics.from_test_report(test_path)
        
        # Load coverage metrics (optional, but improves score)
        if coverage_path and Path(coverage_path).exists():
            logger.info(f"Loading coverage metrics from: {coverage_path}")
            self.coverage_metrics = CoverageMetrics.from_coverage_report(coverage_path)
        else:
            logger.warning("Coverage report not available - efficiency score will be limited")
            self.coverage_metrics = None
        
        # Calculate efficiency metrics
        self.efficiency_metrics = self._calculate_efficiency()
        
        # Calculate score
        score_value = self.efficiency_metrics.overall_efficiency
        
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
            component_type=ComponentType.TEST_EFFICIENCY,
            value=score_value,
            weight=self.config.weight,
            raw_metrics=raw_metrics,
            threshold_met=threshold_met,
            threshold_value=0.70,  # 70% minimum efficiency
            details=details,
            recommendations=recommendations,
        )
        
        logger.info(
            f"Efficiency score: {score_value:.4f} "
            f"({component_score.percentage:.2f}%) - "
            f"{'PASS' if threshold_met else 'FAIL'}"
        )
        
        return component_score
    
    def _calculate_efficiency(self) -> EfficiencyMetrics:
        """
        Calculate efficiency metrics
        
        Returns:
            EfficiencyMetrics with runtime, memory, and coverage speed
        """
        if not self.test_metrics:
            raise ValueError("Test metrics not loaded")
        
        # Calculate runtime efficiency
        # Score: 1.0 if avg duration <= threshold, decreases linearly beyond
        avg_duration = self.test_metrics.average_duration_ms
        expected_duration = self.config.max_acceptable_duration_per_test_ms
        
        if avg_duration <= expected_duration:
            runtime_score = 1.0
        else:
            # Penalize linearly up to 5x threshold, then cap at 0.1
            ratio = avg_duration / expected_duration
            runtime_score = max(0.1, 1.0 / ratio)
        
        # Calculate memory efficiency
        # Score: 1.0 if peak <= threshold, decreases linearly beyond
        peak_memory = self.test_metrics.peak_memory_mb
        expected_memory = self.config.max_acceptable_memory_mb
        
        if peak_memory <= expected_memory:
            memory_score = 1.0
        else:
            # Penalize linearly up to 5x threshold, then cap at 0.1
            ratio = peak_memory / expected_memory
            memory_score = max(0.1, 1.0 / ratio)
        
        # Calculate coverage per second (if coverage available)
        if self.coverage_metrics:
            total_seconds = self.test_metrics.total_duration_ms / 1000.0
            coverage_per_second = self.coverage_metrics.weighted_score / max(total_seconds, 0.001)
            
            # Score: 1.0 if coverage/sec >= threshold, scales below
            expected_cov_per_sec = self.config.min_coverage_per_second
            if coverage_per_second >= expected_cov_per_sec:
                cov_speed_score = 1.0
            else:
                cov_speed_score = coverage_per_second / expected_cov_per_sec
        else:
            # No coverage data - use neutral score
            coverage_per_second = 0.0
            cov_speed_score = 0.75  # Neutral
        
        # Calculate test redundancy (placeholder - would need hierarchical coverage)
        test_redundancy = 0.0
        
        # Calculate overall efficiency (weighted average)
        overall_efficiency = (
            runtime_score * self.config.runtime_weight +
            memory_score * self.config.memory_weight +
            cov_speed_score * self.config.coverage_speed_weight
        )
        
        return EfficiencyMetrics(
            runtime_score=runtime_score,
            memory_score=memory_score,
            coverage_per_second=coverage_per_second,
            test_redundancy=test_redundancy,
            overall_efficiency=overall_efficiency
        )
    
    def _check_thresholds(self) -> bool:
        """
        Check if efficiency meets thresholds
        
        Returns:
            True if thresholds are met
        """
        if not self.efficiency_metrics:
            return False
        
        # Overall efficiency should be >= 70%
        return self.efficiency_metrics.overall_efficiency >= 0.70
    
    def _get_raw_metrics(self) -> Dict[str, Any]:
        """
        Get raw efficiency metrics
        
        Returns:
            Dictionary of raw metrics
        """
        if not self.test_metrics or not self.efficiency_metrics:
            return {}
        
        return {
            "total_tests": self.test_metrics.total_tests,
            "total_duration_ms": self.test_metrics.total_duration_ms,
            "average_duration_ms": self.test_metrics.average_duration_ms,
            "peak_memory_mb": self.test_metrics.peak_memory_mb,
            "runtime_score": self.efficiency_metrics.runtime_score,
            "memory_score": self.efficiency_metrics.memory_score,
            "coverage_per_second": self.efficiency_metrics.coverage_per_second,
            "overall_efficiency": self.efficiency_metrics.overall_efficiency,
        }
    
    def _generate_details(self) -> str:
        """
        Generate human-readable details
        
        Returns:
            Details string
        """
        if not self.test_metrics or not self.efficiency_metrics:
            return "Efficiency metrics not available"
        
        tm = self.test_metrics
        em = self.efficiency_metrics
        
        details_lines = [
            f"Test Efficiency: {em.overall_efficiency * 100:.2f}%",
            f"  Runtime Score:  {em.runtime_score * 100:.2f}%",
            f"    Avg Duration: {tm.average_duration_ms:.2f}ms/test",
            f"    Total Time:   {tm.total_duration_ms / 1000:.2f}s",
            f"  Memory Score:   {em.memory_score * 100:.2f}%",
            f"    Peak Memory:  {tm.peak_memory_mb:.2f}MB",
        ]
        
        if self.coverage_metrics:
            details_lines.append(
                f"  Coverage Speed: {em.coverage_per_second * 100:.2f}%/sec"
            )
        
        return "\n".join(details_lines)
    
    def _generate_recommendations(self) -> List[str]:
        """
        Generate recommendations for improving efficiency
        
        Returns:
            List of recommendation strings
        """
        if not self.test_metrics or not self.efficiency_metrics:
            return []
        
        recommendations = []
        tm = self.test_metrics
        em = self.efficiency_metrics
        
        # Runtime recommendations
        if em.runtime_score < 0.80:
            avg_ms = tm.average_duration_ms
            target_ms = self.config.max_acceptable_duration_per_test_ms
            
            if avg_ms > target_ms * 2:
                recommendations.append(
                    f"Test runtime is {avg_ms:.0f}ms/test (target: {target_ms:.0f}ms). "
                    f"Optimize test execution: reduce unnecessary waits, use faster clock speeds, "
                    f"parallelize independent tests."
                )
            else:
                recommendations.append(
                    f"Test runtime is {avg_ms:.0f}ms/test (target: {target_ms:.0f}ms). "
                    f"Consider optimizing test setup/teardown and reducing simulation time."
                )
        
        # Memory recommendations
        if em.memory_score < 0.80:
            peak_mb = tm.peak_memory_mb
            target_mb = self.config.max_acceptable_memory_mb
            
            if peak_mb > target_mb * 2:
                recommendations.append(
                    f"Peak memory usage is {peak_mb:.0f}MB (target: {target_mb:.0f}MB). "
                    f"Significant optimization needed: reduce waveform capture, limit transaction history, "
                    f"optimize data structures."
                )
            else:
                recommendations.append(
                    f"Peak memory usage is {peak_mb:.0f}MB (target: {target_mb:.0f}MB). "
                    f"Consider disabling full waveform dumps and reducing logging verbosity."
                )
        
        # Coverage speed recommendations
        if self.coverage_metrics and em.coverage_per_second < self.config.min_coverage_per_second:
            recommendations.append(
                f"Coverage gain rate is low ({em.coverage_per_second * 100:.2f}%/sec). "
                f"Tests may be too slow or redundant. Consider faster targeted tests for uncovered areas."
            )
        
        # Overall efficiency recommendation
        if em.overall_efficiency < 0.70:
            gap = (0.70 - em.overall_efficiency) * 100
            recommendations.append(
                f"Improve overall efficiency by {gap:.1f}% to meet 70% threshold. "
                f"Focus on optimizing runtime and memory usage."
            )
        
        # If efficiency is good, suggest stretch goals
        if not recommendations:
            if em.overall_efficiency < 0.90:
                recommendations.append(
                    "Efficiency meets threshold. Consider aiming for 90%+ for optimal performance."
                )
        
        return recommendations
    
    def generate_improvements(self) -> List[Improvement]:
        """
        Generate actionable improvements for efficiency
        
        Returns:
            List of Improvement objects with specific actions
        """
        if not self.test_metrics or not self.efficiency_metrics:
            return []
        
        improvements = []
        tm = self.test_metrics
        em = self.efficiency_metrics
        
        # Runtime improvement
        if em.runtime_score < 0.80:
            impact = (0.80 - em.runtime_score) * self.config.runtime_weight * self.config.weight
            current_pct = em.runtime_score * 100
            
            improvements.append(Improvement(
                component=ComponentType.TEST_EFFICIENCY,
                priority="high" if impact > 0.03 else "medium",
                current_value=current_pct,
                target_value=80.0,
                impact=impact,
                actions=[
                    f"Reduce average test duration from {tm.average_duration_ms:.0f}ms to <{self.config.max_acceptable_duration_per_test_ms:.0f}ms",
                    "Use faster simulation clock periods where possible",
                    "Minimize wait cycles in test sequences",
                    "Remove unnecessary delays and idle periods",
                    "Consider parallel test execution",
                ]
            ))
        
        # Memory improvement
        if em.memory_score < 0.80:
            impact = (0.80 - em.memory_score) * self.config.memory_weight * self.config.weight
            current_pct = em.memory_score * 100
            
            improvements.append(Improvement(
                component=ComponentType.TEST_EFFICIENCY,
                priority="medium" if impact > 0.02 else "low",
                current_value=current_pct,
                target_value=80.0,
                impact=impact,
                actions=[
                    f"Reduce peak memory from {tm.peak_memory_mb:.0f}MB to <{self.config.max_acceptable_memory_mb:.0f}MB",
                    "Disable full waveform capture (use selective dumping)",
                    "Reduce transaction logging verbosity",
                    "Clear history buffers periodically",
                    "Optimize data structures (use generators, not lists)",
                ]
            ))
        
        # Coverage speed improvement
        if self.coverage_metrics and em.coverage_per_second < self.config.min_coverage_per_second:
            # Estimate impact (this is indirect - better coverage speed helps overall)
            impact = 0.02  # Moderate impact
            current_pct = (em.coverage_per_second / self.config.min_coverage_per_second) * 100
            
            improvements.append(Improvement(
                component=ComponentType.TEST_EFFICIENCY,
                priority="low",
                current_value=current_pct,
                target_value=100.0,
                impact=impact,
                actions=[
                    "Add targeted directed tests for uncovered areas",
                    "Reduce redundant test cases",
                    "Use coverage-driven test generation",
                    "Prioritize high-impact test scenarios",
                ]
            ))
        
        # Sort by impact (highest first)
        improvements.sort(key=lambda x: x.impact, reverse=True)
        
        return improvements
    
    def get_efficiency_breakdown(self) -> Dict[str, Any]:
        """
        Get detailed efficiency breakdown for reporting
        
        Returns:
            Dictionary with efficiency breakdown
        """
        if not self.test_metrics or not self.efficiency_metrics:
            return {}
        
        tm = self.test_metrics
        em = self.efficiency_metrics
        
        return {
            "overall": {
                "score": em.overall_efficiency,
                "percentage": em.overall_efficiency * 100.0,
                "meets_threshold": em.overall_efficiency >= 0.70,
            },
            "runtime": {
                "score": em.runtime_score,
                "percentage": em.runtime_score * 100.0,
                "average_duration_ms": tm.average_duration_ms,
                "threshold_ms": self.config.max_acceptable_duration_per_test_ms,
                "within_threshold": tm.average_duration_ms <= self.config.max_acceptable_duration_per_test_ms,
            },
            "memory": {
                "score": em.memory_score,
                "percentage": em.memory_score * 100.0,
                "peak_memory_mb": tm.peak_memory_mb,
                "threshold_mb": self.config.max_acceptable_memory_mb,
                "within_threshold": tm.peak_memory_mb <= self.config.max_acceptable_memory_mb,
            },
            "coverage_speed": {
                "coverage_per_second": em.coverage_per_second,
                "percentage_per_second": em.coverage_per_second * 100.0,
                "threshold": self.config.min_coverage_per_second,
                "available": self.coverage_metrics is not None,
            },
        }


# =============================================================================
# CONVENIENCE FUNCTIONS
# =============================================================================

def score_efficiency(
    test_report_path: Path,
    coverage_report_path: Optional[Path] = None,
    weight: float = 0.10,
    thresholds: Optional[Dict[str, float]] = None
) -> ComponentScore:
    """
    Convenience function to score efficiency
    
    Args:
        test_report_path: Path to test_report.json
        coverage_report_path: Path to coverage_report.json (optional)
        weight: Weight for this component (default: 0.10 for Tier 1)
        thresholds: Optional threshold overrides
    
    Returns:
        ComponentScore for test efficiency
    
    Example:
        >>> score = score_efficiency(
        ...     Path(".tbeval/test_runs/test_report.json"),
        ...     Path(".tbeval/coverage/coverage_report.json"),
        ...     weight=0.05  # Tier 2 weight
        ... )
        >>> print(f"Efficiency: {score.percentage:.2f}%")
    """
    # Create config with thresholds
    config = EfficiencyScoringConfig(weight=weight)
    
    if thresholds:
        config.max_acceptable_duration_per_test_ms = thresholds.get(
            "max_duration_ms", config.max_acceptable_duration_per_test_ms
        )
        config.max_acceptable_memory_mb = thresholds.get(
            "max_memory_mb", config.max_acceptable_memory_mb
        )
        config.min_coverage_per_second = thresholds.get(
            "min_coverage_per_sec", config.min_coverage_per_second
        )
    
    # Create scorer and calculate score
    scorer = EfficiencyScorer(config=config)
    return scorer.score(test_report_path, coverage_report_path)


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
        print("Usage: python -m step7_score.scorers.efficiency_scorer <test_report.json> [coverage_report.json]")
        sys.exit(1)
    
    test_report = Path(sys.argv[1])
    coverage_report = Path(sys.argv[2]) if len(sys.argv) > 2 else None
    
    if not test_report.exists():
        print(f"Error: Test report not found: {test_report}")
        sys.exit(1)
    
    print("=" * 60)
    print("EFFICIENCY SCORING")
    print("=" * 60)
    
    # Create scorer
    config = EfficiencyScoringConfig(
        weight=0.10,
        max_acceptable_duration_per_test_ms=1000.0,
        max_acceptable_memory_mb=500.0,
        min_coverage_per_second=0.01,
    )
    
    scorer = EfficiencyScorer(config=config)
    
    # Calculate score
    try:
        score = scorer.score(test_report, coverage_report)
        
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
        
        # Get efficiency breakdown
        breakdown = scorer.get_efficiency_breakdown()
        print(f"\nEfficiency Breakdown:")
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
        
        output_path = Path("efficiency_score.json")
        with open(output_path, 'w') as f:
            json.dump(output, f, indent=2)
        
        print(f"\n✓ Score exported to: {output_path}")
        
        sys.exit(0 if score.threshold_met else 1)
    
    except Exception as e:
        print(f"\n✗ Error scoring efficiency: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
