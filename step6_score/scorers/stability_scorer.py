"""
Multi-seed stability scorer for Step 7: Scoring

Analyzes test behavior across multiple random seeds to evaluate:
- Pass rate consistency
- Coverage variance
- Flaky test detection
- Coverage convergence
- Result reproducibility

Used by Tier 2 scoring system.

Author: TB Eval Team
Version: 0.1.0
"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional, Dict, List, Set, Tuple, Any
import json
import math
import statistics
import logging

from ..models import (
    ComponentScore,
    ComponentType,
    StabilityMetrics,
    Improvement,
)

logger = logging.getLogger(__name__)


# =============================================================================
# DATA MODELS
# =============================================================================

@dataclass
class TestRunData:
    """
    Single test run data
    
    Attributes:
        seed: Random seed used
        test_name: Test name
        passed: Whether test passed
        coverage: Coverage percentage (0-100)
        duration_ms: Test duration in milliseconds
        assertions: Number of assertions checked
    """
    seed: int
    test_name: str
    passed: bool
    coverage: float = 0.0
    duration_ms: float = 0.0
    assertions: int = 0


@dataclass
class TestStabilityData:
    """
    Stability data for a single test across multiple seeds
    
    Attributes:
        test_name: Test name
        runs: List of test runs
        pass_rate: Pass rate (0.0-1.0)
        pass_rate_variance: Variance in pass rate
        coverage_mean: Mean coverage
        coverage_variance: Variance in coverage
        is_flaky: Whether test is flaky
        flakiness_score: Flakiness score (0.0-1.0)
    """
    test_name: str
    runs: List[TestRunData] = field(default_factory=list)
    pass_rate: float = 0.0
    pass_rate_variance: float = 0.0
    coverage_mean: float = 0.0
    coverage_variance: float = 0.0
    is_flaky: bool = False
    flakiness_score: float = 0.0
    
    def calculate_statistics(self) -> None:
        """Calculate stability statistics"""
        if not self.runs:
            return
        
        # Pass rate
        passes = sum(1 for r in self.runs if r.passed)
        self.pass_rate = passes / len(self.runs)
        
        # Pass rate variance (0 if all pass or all fail)
        if 0 < passes < len(self.runs):
            # Binary variance: p * (1-p)
            self.pass_rate_variance = self.pass_rate * (1 - self.pass_rate)
        else:
            self.pass_rate_variance = 0.0
        
        # Coverage statistics
        coverages = [r.coverage for r in self.runs]
        if coverages:
            self.coverage_mean = statistics.mean(coverages)
            if len(coverages) > 1:
                self.coverage_variance = statistics.variance(coverages)
            else:
                self.coverage_variance = 0.0
        
        # Flakiness detection
        # Flaky if: pass rate is between 0.1 and 0.9 (not consistently passing/failing)
        self.is_flaky = 0.1 < self.pass_rate < 0.9
        
        # Flakiness score (higher = more flaky)
        # Maximum flakiness at 50% pass rate
        self.flakiness_score = 4 * self.pass_rate * (1 - self.pass_rate)


# =============================================================================
# MULTI-SEED ANALYZER
# =============================================================================

class MultiSeedAnalyzer:
    """
    Analyze test stability across multiple random seeds
    
    Processes multiple test runs to detect:
    - Flaky tests
    - Coverage variance
    - Pass rate stability
    - Convergence behavior
    """
    
    def __init__(self):
        """Initialize multi-seed analyzer"""
        self.test_stability: Dict[str, TestStabilityData] = {}
        self.all_runs: List[TestRunData] = []
    
    def add_test_run(
        self,
        seed: int,
        test_name: str,
        passed: bool,
        coverage: float = 0.0,
        duration_ms: float = 0.0,
        assertions: int = 0
    ) -> None:
        """
        Add a test run result
        
        Args:
            seed: Random seed
            test_name: Test name
            passed: Whether test passed
            coverage: Coverage percentage
            duration_ms: Duration in milliseconds
            assertions: Number of assertions
        """
        run = TestRunData(
            seed=seed,
            test_name=test_name,
            passed=passed,
            coverage=coverage,
            duration_ms=duration_ms,
            assertions=assertions
        )
        
        self.all_runs.append(run)
        
        # Add to test-specific data
        if test_name not in self.test_stability:
            self.test_stability[test_name] = TestStabilityData(test_name=test_name)
        
        self.test_stability[test_name].runs.append(run)
    
    def load_from_reports(self, report_paths: List[Path]) -> None:
        """
        Load test runs from multiple test reports
        
        Args:
            report_paths: List of paths to test_report.json files
        """
        logger.info(f"Loading {len(report_paths)} test reports")
        
        for report_path in report_paths:
            self._load_report(report_path)
        
        logger.info(f"Loaded {len(self.all_runs)} test runs for {len(self.test_stability)} tests")
    
    def _load_report(self, report_path: Path) -> None:
        """Load a single test report"""
        try:
            with open(report_path) as f:
                data = json.load(f)
            
            # Extract seed (from filename or metadata)
            seed = self._extract_seed(report_path, data)
            
            # Extract test results
            tests = data.get("tests", []) or data.get("test_cases", [])
            
            for test in tests:
                test_name = test.get("name") or test.get("test_name")
                passed = test.get("status") == "passed" or test.get("passed", False)
                coverage = test.get("coverage", 0.0)
                duration = test.get("duration_ms", 0.0)
                assertions = test.get("assertions", 0)
                
                if test_name:
                    self.add_test_run(
                        seed=seed,
                        test_name=test_name,
                        passed=passed,
                        coverage=coverage,
                        duration_ms=duration,
                        assertions=assertions
                    )
        
        except Exception as e:
            logger.warning(f"Failed to load report {report_path}: {e}")
    
    def _extract_seed(self, report_path: Path, data: Dict) -> int:
        """Extract seed from report filename or metadata"""
        # Try to extract from filename
        # Example: test_report_seed_12345.json
        import re
        match = re.search(r'seed[_-]?(\d+)', report_path.name)
        if match:
            return int(match.group(1))
        
        # Try metadata
        seed = data.get("metadata", {}).get("seed")
        if seed is not None:
            return int(seed)
        
        # Try config
        seed = data.get("config", {}).get("seed")
        if seed is not None:
            return int(seed)
        
        # Default to hash of filename
        return hash(report_path.name) % 10000
    
    def analyze(self) -> None:
        """Analyze stability across all test runs"""
        logger.info("Analyzing test stability")
        
        for test_data in self.test_stability.values():
            test_data.calculate_statistics()
        
        logger.info(
            f"Analysis complete: {len(self.test_stability)} tests, "
            f"{self.get_flaky_test_count()} flaky tests"
        )
    
    def get_overall_stability(self) -> float:
        """
        Calculate overall stability score
        
        Returns:
            Stability score (0.0-1.0, higher is better)
        """
        if not self.test_stability:
            return 0.0
        
        # Average stability across all tests
        stability_scores = []
        
        for test_data in self.test_stability.values():
            # Stability = 1 - flakiness_score
            test_stability = 1.0 - test_data.flakiness_score
            
            # Penalize for coverage variance
            if test_data.coverage_variance > 0:
                # Normalize variance (assume max variance of 100)
                variance_penalty = min(test_data.coverage_variance / 100.0, 0.5)
                test_stability -= variance_penalty
            
            stability_scores.append(max(0.0, test_stability))
        
        return statistics.mean(stability_scores)
    
    def get_pass_rate_variance(self) -> float:
        """Get average pass rate variance across all tests"""
        if not self.test_stability:
            return 0.0
        
        variances = [t.pass_rate_variance for t in self.test_stability.values()]
        return statistics.mean(variances)
    
    def get_coverage_variance(self) -> float:
        """Get average coverage variance across all tests"""
        if not self.test_stability:
            return 0.0
        
        variances = [t.coverage_variance for t in self.test_stability.values()]
        return statistics.mean(variances)
    
    def get_flaky_tests(self) -> List[TestStabilityData]:
        """Get list of flaky tests"""
        return [t for t in self.test_stability.values() if t.is_flaky]
    
    def get_flaky_test_count(self) -> int:
        """Get number of flaky tests"""
        return len(self.get_flaky_tests())
    
    def calculate_convergence(self) -> float:
        """
        Calculate coverage convergence score
        
        Returns:
            Convergence score (0.0-1.0, higher = faster convergence)
        """
        if not self.test_stability:
            return 0.0
        
        # For each test, check if coverage stabilizes
        convergence_scores = []
        
        for test_data in self.test_stability.values():
            if len(test_data.runs) < 3:
                continue
            
            # Check if variance decreases over time
            coverages = [r.coverage for r in sorted(test_data.runs, key=lambda x: x.seed)]
            
            # Calculate moving variance
            window_size = min(5, len(coverages) // 2)
            if window_size < 2:
                continue
            
            early_variance = statistics.variance(coverages[:window_size])
            late_variance = statistics.variance(coverages[-window_size:])
            
            # Convergence if variance decreases
            if early_variance > 0:
                convergence = 1.0 - (late_variance / early_variance)
                convergence_scores.append(max(0.0, min(1.0, convergence)))
        
        if convergence_scores:
            return statistics.mean(convergence_scores)
        
        return 0.5  # Neutral if can't calculate


# =============================================================================
# STABILITY SCORER
# =============================================================================

@dataclass
class StabilityScoringConfig:
    """Configuration for stability scoring"""
    weight: float = 0.10  # Default Tier 2 weight
    min_runs_per_test: int = 3  # Minimum runs needed for analysis
    max_flaky_tests: int = 0  # Maximum allowed flaky tests
    max_pass_rate_variance: float = 0.1  # Maximum allowed variance
    max_coverage_variance: float = 10.0  # Maximum allowed variance


class StabilityScorer:
    """
    Score multi-seed stability
    
    Evaluates test suite stability across multiple random seeds.
    """
    
    def __init__(self, config: Optional[StabilityScoringConfig] = None):
        """
        Initialize stability scorer
        
        Args:
            config: Scoring configuration
        """
        self.config = config or StabilityScoringConfig()
        self.analyzer = MultiSeedAnalyzer()
        self.metrics: Optional[StabilityMetrics] = None
    
    def score(
        self,
        report_paths: Optional[List[Path]] = None,
        test_runs: Optional[List[TestRunData]] = None
    ) -> ComponentScore:
        """
        Calculate stability component score
        
        Args:
            report_paths: List of paths to test reports
            test_runs: Pre-parsed test run data (alternative)
        
        Returns:
            ComponentScore for stability
        
        Raises:
            ValueError: If insufficient data provided
        """
        logger.info("Scoring multi-seed stability")
        
        # Load data
        if report_paths:
            self.analyzer.load_from_reports(report_paths)
        elif test_runs:
            for run in test_runs:
                self.analyzer.add_test_run(
                    seed=run.seed,
                    test_name=run.test_name,
                    passed=run.passed,
                    coverage=run.coverage,
                    duration_ms=run.duration_ms,
                    assertions=run.assertions
                )
        else:
            raise ValueError("Either report_paths or test_runs required")
        
        # Analyze
        self.analyzer.analyze()
        
        # Check minimum runs
        if len(self.analyzer.all_runs) < self.config.min_runs_per_test:
            logger.warning(
                f"Insufficient runs for stability analysis "
                f"(have {len(self.analyzer.all_runs)}, need {self.config.min_runs_per_test})"
            )
        
        # Calculate metrics
        self.metrics = StabilityMetrics(
            overall_stability=self.analyzer.get_overall_stability(),
            pass_rate_variance=self.analyzer.get_pass_rate_variance(),
            coverage_variance=self.analyzer.get_coverage_variance(),
            flaky_test_count=self.analyzer.get_flaky_test_count(),
            convergence_score=self.analyzer.calculate_convergence()
        )
        
        # Calculate score
        score_value = self._calculate_score()
        
        # Validate thresholds
        threshold_met = self._check_thresholds()
        
        # Generate raw metrics
        raw_metrics = self._get_raw_metrics()
        
        # Generate recommendations
        recommendations = self._generate_recommendations()
        
        # Generate details
        details = self._generate_details()
        
        # Create component score
        component_score = ComponentScore(
            component_type=ComponentType.MULTISEED_STABILITY,
            value=score_value,
            weight=self.config.weight,
            raw_metrics=raw_metrics,
            threshold_met=threshold_met,
            threshold_value=0.70,
            details=details,
            recommendations=recommendations,
        )
        
        logger.info(
            f"Stability score: {score_value:.4f} "
            f"({component_score.percentage:.2f}%) - "
            f"{'PASS' if threshold_met else 'FAIL'}"
        )
        
        return component_score
    
    def _calculate_score(self) -> float:
        """Calculate overall stability score"""
        if not self.metrics:
            return 0.0
        
        # Weighted combination
        score = (
            self.metrics.overall_stability * 0.40 +
            (1.0 - min(self.metrics.pass_rate_variance / 0.25, 1.0)) * 0.30 +
            (1.0 - min(self.metrics.coverage_variance / 50.0, 1.0)) * 0.20 +
            self.metrics.convergence_score * 0.10
        )
        
        return max(0.0, min(1.0, score))
    
    def _check_thresholds(self) -> bool:
        """Check if stability meets thresholds"""
        if not self.metrics:
            return False
        
        # Check flaky tests
        if self.metrics.flaky_test_count > self.config.max_flaky_tests:
            return False
        
        # Check pass rate variance
        if self.metrics.pass_rate_variance > self.config.max_pass_rate_variance:
            return False
        
        # Check coverage variance
        if self.metrics.coverage_variance > self.config.max_coverage_variance:
            return False
        
        return True
    
    def _get_raw_metrics(self) -> Dict[str, Any]:
        """Get raw stability metrics"""
        if not self.metrics:
            return {}
        
        return {
            "overall_stability": self.metrics.overall_stability,
            "pass_rate_variance": self.metrics.pass_rate_variance,
            "coverage_variance": self.metrics.coverage_variance,
            "flaky_test_count": self.metrics.flaky_test_count,
            "convergence_score": self.metrics.convergence_score,
            "total_runs": len(self.analyzer.all_runs),
            "total_tests": len(self.analyzer.test_stability),
        }
    
    def _generate_details(self) -> str:
        """Generate human-readable details"""
        if not self.metrics:
            return "Stability metrics not available"
        
        m = self.metrics
        
        details = (
            f"Multi-Seed Stability: {m.overall_stability * 100:.2f}%\n"
            f"  Pass Rate Variance:  {m.pass_rate_variance:.4f}\n"
            f"  Coverage Variance:   {m.coverage_variance:.2f}\n"
            f"  Flaky Tests:         {m.flaky_test_count}\n"
            f"  Convergence Score:   {m.convergence_score * 100:.2f}%\n"
            f"\n"
            f"  Total Runs:  {len(self.analyzer.all_runs)}\n"
            f"  Total Tests: {len(self.analyzer.test_stability)}"
        )
        
        return details
    
    def _generate_recommendations(self) -> List[str]:
        """Generate recommendations for improving stability"""
        if not self.metrics:
            return []
        
        recommendations = []
        m = self.metrics
        
        # Flaky tests
        if m.flaky_test_count > 0:
            flaky_tests = self.analyzer.get_flaky_tests()
            test_names = [t.test_name for t in flaky_tests[:3]]
            recommendations.append(
                f"Fix {m.flaky_test_count} flaky test(s): {', '.join(test_names)}. "
                f"Investigate non-deterministic behavior and add proper synchronization."
            )
        
        # Pass rate variance
        if m.pass_rate_variance > self.config.max_pass_rate_variance:
            recommendations.append(
                f"Pass rate variance ({m.pass_rate_variance:.4f}) exceeds threshold "
                f"({self.config.max_pass_rate_variance:.4f}). "
                f"Tests should pass consistently across different seeds."
            )
        
        # Coverage variance
        if m.coverage_variance > self.config.max_coverage_variance:
            recommendations.append(
                f"Coverage variance ({m.coverage_variance:.2f}) exceeds threshold "
                f"({self.config.max_coverage_variance:.2f}). "
                f"Improve test determinism and coverage stability."
            )
        
        # Convergence
        if m.convergence_score < 0.70:
            recommendations.append(
                f"Coverage convergence is low ({m.convergence_score * 100:.1f}%). "
                f"Increase number of test iterations or improve test quality."
            )
        
        # General stability
        if m.overall_stability < 0.70:
            recommendations.append(
                "Overall stability is below threshold. Run more regression seeds "
                "and fix non-deterministic tests."
            )
        
        return recommendations
    
    def generate_improvements(self) -> List[Improvement]:
        """Generate actionable improvements for stability"""
        if not self.metrics:
            return []
        
        improvements = []
        m = self.metrics
        
        # Flakiness improvement
        if m.flaky_test_count > 0:
            impact = (m.flaky_test_count / len(self.analyzer.test_stability)) * self.config.weight
            improvements.append(Improvement(
                component=ComponentType.MULTISEED_STABILITY,
                priority="high",
                current_value=100.0 - (m.flaky_test_count / len(self.analyzer.test_stability) * 100),
                target_value=100.0,
                impact=impact,
                actions=[
                    "Identify root cause of flaky tests (timing, race conditions)",
                    "Add proper clock synchronization in testbench",
                    "Fix non-deterministic random constraints",
                    "Use fixed delays instead of #0 timing",
                    "Review test teardown and cleanup procedures",
                ]
            ))
        
        # Variance improvement
        if m.coverage_variance > self.config.max_coverage_variance:
            impact = (m.coverage_variance / 50.0) * 0.20 * self.config.weight
            improvements.append(Improvement(
                component=ComponentType.MULTISEED_STABILITY,
                priority="medium",
                current_value=100.0 - m.coverage_variance,
                target_value=100.0 - self.config.max_coverage_variance,
                impact=min(impact, 0.05),
                actions=[
                    "Increase test iterations for more consistent coverage",
                    "Use constrained random instead of pure random",
                    "Add coverage-driven test generation",
                    "Improve test scenario diversity",
                ]
            ))
        
        improvements.sort(key=lambda x: x.impact, reverse=True)
        return improvements


# =============================================================================
# CONVENIENCE FUNCTIONS
# =============================================================================

def score_stability(
    report_paths: List[Path],
    weight: float = 0.10
) -> ComponentScore:
    """
    Convenience function to score stability
    
    Args:
        report_paths: List of paths to test reports
        weight: Weight for this component
    
    Returns:
        ComponentScore for stability
    """
    config = StabilityScoringConfig(weight=weight)
    scorer = StabilityScorer(config=config)
    return scorer.score(report_paths=report_paths)
