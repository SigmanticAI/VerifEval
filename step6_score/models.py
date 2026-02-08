"""
Data models for Step 7: Scoring & Export

This module contains all data structures for testbench evaluation scoring:
- Enums: ScoringTier, Grade, ComponentType
- Component scores: Individual scoring components
- Metrics: Coverage, Quality, Efficiency, Stability
- Questa metrics: Functional coverage, assertions, UVM
- Tier scores: Tier 1 (open-source) and Tier 2 (professional)
- Final report: Complete evaluation with recommendations

Design Philosophy:
- Immutable data classes with computed properties
- Clear serialization to JSON/dict
- Self-validating (raises on invalid data)
- Integration with Step 2, 4, 5 outputs

Author: TB Eval Team
Version: 0.1.0
"""

from dataclasses import dataclass, field, asdict
from enum import Enum
from typing import Dict, List, Set, Optional, Tuple, Any, Union
from pathlib import Path
from datetime import datetime
import json
import math


# =============================================================================
# ENUMS
# =============================================================================

class ScoringTier(Enum):
    """
    Scoring tier based on available tools
    
    OPEN_SOURCE: Verilator-based structural coverage only
    PROFESSIONAL: Full Questa-based analysis
    """
    OPEN_SOURCE = "open_source"
    PROFESSIONAL = "professional"
    
    def __str__(self) -> str:
        return self.value
    
    @property
    def display_name(self) -> str:
        """Human-readable tier name"""
        return {
            ScoringTier.OPEN_SOURCE: "Open Source (Verilator)",
            ScoringTier.PROFESSIONAL: "Professional (Questa)"
        }[self]


class Grade(Enum):
    """
    Letter grades with numeric thresholds
    
    A: 90-100%
    B: 80-89%
    C: 70-79%
    D: 60-69%
    F: 0-59%
    """
    A = "A"
    B = "B"
    C = "C"
    D = "D"
    F = "F"
    
    @classmethod
    def from_score(cls, score: float) -> 'Grade':
        """
        Convert numeric score (0.0-1.0) to letter grade
        
        Args:
            score: Normalized score (0.0 to 1.0)
        
        Returns:
            Grade enum
        
        Example:
            >>> Grade.from_score(0.92)
            Grade.A
        """
        percentage = score * 100.0
        
        if percentage >= 90.0:
            return cls.A
        elif percentage >= 80.0:
            return cls.B
        elif percentage >= 70.0:
            return cls.C
        elif percentage >= 60.0:
            return cls.D
        else:
            return cls.F
    
    @property
    def min_percentage(self) -> float:
        """Minimum percentage for this grade"""
        return {
            Grade.A: 90.0,
            Grade.B: 80.0,
            Grade.C: 70.0,
            Grade.D: 60.0,
            Grade.F: 0.0,
        }[self]
    
    @property
    def is_passing(self) -> bool:
        """Check if grade is passing (C or better)"""
        return self in [Grade.A, Grade.B, Grade.C]


class ComponentType(Enum):
    """
    Types of scoring components
    
    Tier 1 (Open Source) components:
    - STRUCTURAL_COVERAGE: Line/branch/toggle from Verilator
    - TEST_PASS_RATE: Pass/fail/error ratio
    - CODE_QUALITY: Linting and style
    - TEST_EFFICIENCY: Runtime and memory
    - BEHAVIORAL_ACCURACY: Heuristic estimation
    
    Tier 2 (Professional) additional components:
    - FUNCTIONAL_COVERAGE: SystemVerilog covergroups
    - ASSERTION_COVERAGE: SVA property verification
    - UVM_CONFORMANCE: UVM methodology compliance
    - MULTISEED_STABILITY: Regression stability
    """
    # Tier 1 components
    STRUCTURAL_COVERAGE = "structural_coverage"
    TEST_PASS_RATE = "test_pass_rate"
    CODE_QUALITY = "code_quality"
    TEST_EFFICIENCY = "test_efficiency"
    BEHAVIORAL_ACCURACY = "behavioral_accuracy"
    
    # Tier 2 additional components
    FUNCTIONAL_COVERAGE = "functional_coverage"
    ASSERTION_COVERAGE = "assertion_coverage"
    UVM_CONFORMANCE = "uvm_conformance"
    MULTISEED_STABILITY = "multiseed_stability"
    
    @property
    def display_name(self) -> str:
        """Human-readable component name"""
        return {
            ComponentType.STRUCTURAL_COVERAGE: "Structural Coverage",
            ComponentType.FUNCTIONAL_COVERAGE: "Functional Coverage",
            ComponentType.ASSERTION_COVERAGE: "Assertion Coverage",
            ComponentType.UVM_CONFORMANCE: "UVM Conformance",
            ComponentType.MULTISEED_STABILITY: "Multi-Seed Stability",
            ComponentType.CODE_QUALITY: "Code Quality",
            ComponentType.TEST_EFFICIENCY: "Test Efficiency",
            ComponentType.TEST_PASS_RATE: "Test Pass Rate",
            ComponentType.BEHAVIORAL_ACCURACY: "Behavioral Accuracy",
        }[self]
    
    @property
    def requires_questa(self) -> bool:
        """Check if component requires Questa"""
        return self in [
            ComponentType.FUNCTIONAL_COVERAGE,
            ComponentType.ASSERTION_COVERAGE,
            ComponentType.UVM_CONFORMANCE,
        ]


# =============================================================================
# COMPONENT SCORES
# =============================================================================

@dataclass
class ComponentScore:
    """
    Individual scoring component
    
    Represents one aspect of testbench quality (e.g., coverage, quality).
    Includes raw metrics, computed score, and threshold validation.
    
    Attributes:
        component_type: Type of component
        value: Normalized score (0.0 to 1.0)
        weight: Weight in overall score (0.0 to 1.0)
        raw_metrics: Raw measurement data
        threshold_met: Whether component meets quality threshold
        threshold_value: Minimum required value (optional)
        details: Human-readable details
        recommendations: Suggested improvements
    """
    component_type: ComponentType
    value: float
    weight: float
    raw_metrics: Dict[str, Any]
    threshold_met: bool
    threshold_value: Optional[float] = None
    details: Optional[str] = None
    recommendations: List[str] = field(default_factory=list)
    
    def __post_init__(self):
        """Validate component score"""
        if not 0.0 <= self.value <= 1.0:
            raise ValueError(f"Component value must be 0.0-1.0, got {self.value}")
        
        if not 0.0 <= self.weight <= 1.0:
            raise ValueError(f"Component weight must be 0.0-1.0, got {self.weight}")
    
    @property
    def weighted_contribution(self) -> float:
        """Calculate contribution to overall score"""
        return self.value * self.weight
    
    @property
    def percentage(self) -> float:
        """Convert value to percentage (0-100)"""
        return self.value * 100.0
    
    @property
    def grade(self) -> Grade:
        """Get letter grade for this component"""
        return Grade.from_score(self.value)
    
    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary"""
        return {
            "component": self.component_type.value,
            "display_name": self.component_type.display_name,
            "score": round(self.value, 4),
            "percentage": round(self.percentage, 2),
            "grade": self.grade.value,
            "weight": self.weight,
            "weighted_contribution": round(self.weighted_contribution, 4),
            "threshold_met": self.threshold_met,
            "threshold_value": self.threshold_value,
            "details": self.details,
            "recommendations": self.recommendations,
            "raw_metrics": self.raw_metrics
        }


# =============================================================================
# METRICS FROM PREVIOUS STEPS
# =============================================================================

@dataclass
class CoverageMetrics:
    """
    Coverage metrics from Step 5
    
    Loaded from coverage_report.json (step5_coverage output)
    
    Attributes:
        line_coverage: Line coverage percentage
        branch_coverage: Branch coverage percentage
        toggle_coverage: Toggle coverage percentage
        fsm_coverage: FSM coverage percentage
        weighted_score: Overall weighted coverage score (0.0-1.0)
        source_report: Path to coverage_report.json
    """
    line_coverage: float
    branch_coverage: float
    toggle_coverage: float
    fsm_coverage: float
    weighted_score: float
    source_report: str
    
    @classmethod
    def from_coverage_report(cls, report_path: Path) -> 'CoverageMetrics':
        """
        Load from coverage_report.json
        
        Args:
            report_path: Path to coverage_report.json from Step 5
        
        Returns:
            CoverageMetrics instance
        
        Raises:
            FileNotFoundError: If report doesn't exist
            ValueError: If report format is invalid
        """
        report_path = Path(report_path)
        
        if not report_path.exists():
            raise FileNotFoundError(f"Coverage report not found: {report_path}")
        
        with open(report_path) as f:
            data = json.load(f)
        
        structural = data["structural_coverage"]
        
        return cls(
            line_coverage=structural["line"]["percentage"],
            branch_coverage=structural["branch"]["percentage"],
            toggle_coverage=structural["toggle"]["percentage"],
            fsm_coverage=structural["fsm"]["percentage"],
            weighted_score=structural["weighted_score"],
            source_report=str(report_path)
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary"""
        return {
            "line": round(self.line_coverage, 2),
            "branch": round(self.branch_coverage, 2),
            "toggle": round(self.toggle_coverage, 2),
            "fsm": round(self.fsm_coverage, 2),
            "weighted": round(self.weighted_score, 4),
            "source": self.source_report
        }


@dataclass
class QualityMetrics:
    """
    Code quality metrics from Step 2
    
    Loaded from quality_report.json (step2_quality_gate output)
    
    Attributes:
        overall_score: Overall quality score (0.0-1.0)
        linting_passed: Whether linting passed
        style_violations: Number of style violations
        complexity_score: Code complexity score
        documentation_score: Documentation completeness
        source_report: Path to quality_report.json
    """
    overall_score: float
    linting_passed: bool
    style_violations: int
    complexity_score: float
    documentation_score: float
    source_report: Optional[str] = None
    
    @classmethod
    def from_quality_report(cls, report_path: Path) -> 'QualityMetrics':
        """Load from quality_report.json"""
        report_path = Path(report_path)
        
        if not report_path.exists():
            # Use defaults if quality report not available
            return cls(
                overall_score=0.75,  # Neutral default
                linting_passed=True,
                style_violations=0,
                complexity_score=0.75,
                documentation_score=0.75,
                source_report=None
            )
        
        with open(report_path) as f:
            data = json.load(f)
        
        return cls(
            overall_score=data.get("overall_score", 0.75),
            linting_passed=data.get("linting_passed", True),
            style_violations=data.get("style_violations", 0),
            complexity_score=data.get("complexity_score", 0.75),
            documentation_score=data.get("documentation_score", 0.75),
            source_report=str(report_path)
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary"""
        return {
            "overall": round(self.overall_score, 4),
            "linting_passed": self.linting_passed,
            "style_violations": self.style_violations,
            "complexity": round(self.complexity_score, 4),
            "documentation": round(self.documentation_score, 4),
            "source": self.source_report
        }


@dataclass
class TestExecutionMetrics:
    """
    Test execution metrics from Step 4
    
    Loaded from test_report.json (step4_execution output)
    
    Attributes:
        total_tests: Total number of tests
        passed_tests: Number of passed tests
        failed_tests: Number of failed tests
        error_tests: Number of tests with errors
        pass_rate: Pass rate (0.0-1.0)
        total_duration_ms: Total execution time
        average_duration_ms: Average test duration
        peak_memory_mb: Peak memory usage
        source_report: Path to test_report.json
    """
    total_tests: int
    passed_tests: int
    failed_tests: int
    error_tests: int
    pass_rate: float
    total_duration_ms: float
    average_duration_ms: float
    peak_memory_mb: float
    source_report: str
    
    @classmethod
    def from_test_report(cls, report_path: Path) -> 'TestExecutionMetrics':
        """Load from test_report.json"""
        report_path = Path(report_path)
        
        if not report_path.exists():
            raise FileNotFoundError(f"Test report not found: {report_path}")
        
        with open(report_path) as f:
            data = json.load(f)
        
        results = data.get("results", {})
        total = results.get("total_tests", 0)
        passed = results.get("passed", 0)
        failed = results.get("failed", 0)
        errors = results.get("errors", 0)
        
        pass_rate = passed / total if total > 0 else 0.0
        
        timing = data.get("timing", {})
        total_duration = timing.get("total_duration_ms", 0.0)
        avg_duration = total_duration / total if total > 0 else 0.0
        
        return cls(
            total_tests=total,
            passed_tests=passed,
            failed_tests=failed,
            error_tests=errors,
            pass_rate=pass_rate,
            total_duration_ms=total_duration,
            average_duration_ms=avg_duration,
            peak_memory_mb=data.get("resources", {}).get("peak_memory_mb", 0.0),
            source_report=str(report_path)
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary"""
        return {
            "total": self.total_tests,
            "passed": self.passed_tests,
            "failed": self.failed_tests,
            "errors": self.error_tests,
            "pass_rate": round(self.pass_rate, 4),
            "duration_ms": round(self.total_duration_ms, 2),
            "avg_duration_ms": round(self.average_duration_ms, 2),
            "peak_memory_mb": round(self.peak_memory_mb, 2),
            "source": self.source_report
        }


@dataclass
class EfficiencyMetrics:
    """
    Test efficiency metrics
    
    Calculated from test execution data and coverage data.
    
    Attributes:
        runtime_score: Runtime efficiency (0.0-1.0, lower is better)
        memory_score: Memory efficiency (0.0-1.0, lower is better)
        coverage_per_second: Coverage gained per second
        test_redundancy: Percentage of redundant tests
        overall_efficiency: Combined efficiency score
    """
    runtime_score: float
    memory_score: float
    coverage_per_second: float
    test_redundancy: float
    overall_efficiency: float
    
    @classmethod
    def calculate(
        cls,
        test_metrics: TestExecutionMetrics,
        coverage_metrics: CoverageMetrics
    ) -> 'EfficiencyMetrics':
        """
        Calculate efficiency metrics
        
        Args:
            test_metrics: Test execution metrics
            coverage_metrics: Coverage metrics
        
        Returns:
            EfficiencyMetrics instance
        """
        # Runtime score (normalize to reasonable range)
        # Assume reasonable test time: 100ms per test
        expected_duration = test_metrics.total_tests * 100.0
        actual_duration = test_metrics.total_duration_ms
        runtime_ratio = expected_duration / max(actual_duration, 1.0)
        runtime_score = min(runtime_ratio, 1.0)
        
        # Memory score (normalize to reasonable range)
        # Assume reasonable memory: 100MB
        expected_memory = 100.0
        actual_memory = test_metrics.peak_memory_mb
        memory_ratio = expected_memory / max(actual_memory, 1.0)
        memory_score = min(memory_ratio, 1.0)
        
        # Coverage per second
        total_seconds = test_metrics.total_duration_ms / 1000.0
        coverage_per_second = coverage_metrics.weighted_score / max(total_seconds, 0.001)
        
        # Test redundancy (placeholder - would come from hierarchical coverage)
        test_redundancy = 0.0
        
        # Overall efficiency
        overall = (runtime_score * 0.4 + memory_score * 0.3 + 
                  min(coverage_per_second * 10, 1.0) * 0.3)
        
        return cls(
            runtime_score=runtime_score,
            memory_score=memory_score,
            coverage_per_second=coverage_per_second,
            test_redundancy=test_redundancy,
            overall_efficiency=overall
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary"""
        return {
            "runtime": round(self.runtime_score, 4),
            "memory": round(self.memory_score, 4),
            "coverage_per_second": round(self.coverage_per_second, 6),
            "test_redundancy": round(self.test_redundancy, 4),
            "overall": round(self.overall_efficiency, 4)
        }


@dataclass
class StabilityMetrics:
    """
    Multi-seed stability metrics
    
    Analyzes test behavior across multiple random seeds.
    Can be calculated with or without Questa.
    
    Attributes:
        overall_stability: Overall stability score (0.0-1.0)
        pass_rate_variance: Variance in pass rates across seeds
        coverage_variance: Variance in coverage across seeds
        flaky_test_count: Number of flaky tests
        convergence_score: Coverage convergence score
    """
    overall_stability: float
    pass_rate_variance: float
    coverage_variance: float
    flaky_test_count: int
    convergence_score: float
    
    @classmethod
    def calculate(cls, test_runs: List[Dict[str, Any]]) -> 'StabilityMetrics':
        """
        Calculate stability metrics from multiple test runs
        
        Args:
            test_runs: List of test run results with different seeds
        
        Returns:
            StabilityMetrics instance
        """
        if len(test_runs) < 2:
            # Not enough data for stability analysis
            return cls(
                overall_stability=1.0,
                pass_rate_variance=0.0,
                coverage_variance=0.0,
                flaky_test_count=0,
                convergence_score=1.0
            )
        
        # Calculate pass rate variance
        pass_rates = [run.get("pass_rate", 0.0) for run in test_runs]
        pass_rate_variance = _calculate_variance(pass_rates)
        
        # Calculate coverage variance
        coverages = [run.get("coverage", 0.0) for run in test_runs]
        coverage_variance = _calculate_variance(coverages)
        
        # Identify flaky tests (placeholder)
        flaky_test_count = 0
        
        # Convergence score (how quickly coverage stabilizes)
        convergence_score = 1.0 - coverage_variance
        
        # Overall stability
        overall = (1.0 - pass_rate_variance) * 0.5 + (1.0 - coverage_variance) * 0.5
        
        return cls(
            overall_stability=max(0.0, min(1.0, overall)),
            pass_rate_variance=pass_rate_variance,
            coverage_variance=coverage_variance,
            flaky_test_count=flaky_test_count,
            convergence_score=max(0.0, min(1.0, convergence_score))
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary"""
        return {
            "overall": round(self.overall_stability, 4),
            "pass_rate_variance": round(self.pass_rate_variance, 4),
            "coverage_variance": round(self.coverage_variance, 4),
            "flaky_tests": self.flaky_test_count,
            "convergence": round(self.convergence_score, 4)
        }


# =============================================================================
# QUESTA-SPECIFIC METRICS (Tier 2 only)
# =============================================================================

@dataclass
class FunctionalCoverageMetrics:
    """
    Functional coverage metrics from Questa
    
    Parsed from SystemVerilog covergroups via vcover.
    Only available with Questa license.
    
    Attributes:
        covergroup_coverage: Overall covergroup percentage
        coverpoint_coverage: Individual coverpoint percentage
        cross_coverage: Cross coverage percentage
        bin_coverage: Bin hit percentage
        goal_met: Whether coverage goals were met
    """
    covergroup_coverage: float
    coverpoint_coverage: float
    cross_coverage: float
    bin_coverage: float
    goal_met: bool
    
    @classmethod
    def from_questa_db(cls, ucdb_path: Path) -> 'FunctionalCoverageMetrics':
        """
        Load from Questa UCDB
        
        Args:
            ucdb_path: Path to Questa .ucdb file
        
        Returns:
            FunctionalCoverageMetrics instance
        """
        # Placeholder - actual implementation would use vcover
        return cls(
            covergroup_coverage=0.0,
            coverpoint_coverage=0.0,
            cross_coverage=0.0,
            bin_coverage=0.0,
            goal_met=False
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary"""
        return {
            "covergroup": round(self.covergroup_coverage, 2),
            "coverpoint": round(self.coverpoint_coverage, 2),
            "cross": round(self.cross_coverage, 2),
            "bin": round(self.bin_coverage, 2),
            "goal_met": self.goal_met
        }


@dataclass
class AssertionCoverageMetrics:
    """
    Assertion coverage metrics from Questa
    
    Tracks SVA assertion firings and coverage.
    Only available with Questa license.
    
    Attributes:
        total_assertions: Total number of assertions
        covered_assertions: Number of assertions that fired
        pass_count: Number of passing assertions
        fail_count: Number of failing assertions
        coverage_percentage: Assertion coverage percentage
    """
    total_assertions: int
    covered_assertions: int
    pass_count: int
    fail_count: int
    coverage_percentage: float
    
    @classmethod
    def from_questa_db(cls, ucdb_path: Path) -> 'AssertionCoverageMetrics':
        """Load from Questa UCDB"""
        # Placeholder
        return cls(
            total_assertions=0,
            covered_assertions=0,
            pass_count=0,
            fail_count=0,
            coverage_percentage=0.0
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary"""
        return {
            "total": self.total_assertions,
            "covered": self.covered_assertions,
            "passed": self.pass_count,
            "failed": self.fail_count,
            "percentage": round(self.coverage_percentage, 2)
        }


@dataclass
class UVMConformanceMetrics:
    """
    UVM methodology conformance metrics
    
    Analyzes adherence to UVM best practices.
    Only available with Questa license.
    
    Attributes:
        uvm_version: Detected UVM version
        component_hierarchy: UVM component hierarchy score
        sequence_usage: Sequence library usage score
        configuration_usage: Configuration object usage
        phase_usage: UVM phase usage correctness
        overall_conformance: Overall UVM conformance score
    """
    uvm_version: str
    component_hierarchy: float
    sequence_usage: float
    configuration_usage: float
    phase_usage: float
    overall_conformance: float
    
    @classmethod
    def analyze(cls, test_report: Path) -> 'UVMConformanceMetrics':
        """Analyze UVM conformance from test report"""
        # Placeholder
        return cls(
            uvm_version="unknown",
            component_hierarchy=0.0,
            sequence_usage=0.0,
            configuration_usage=0.0,
            phase_usage=0.0,
            overall_conformance=0.0
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary"""
        return {
            "uvm_version": self.uvm_version,
            "component_hierarchy": round(self.component_hierarchy, 4),
            "sequence_usage": round(self.sequence_usage, 4),
            "configuration": round(self.configuration_usage, 4),
            "phase_usage": round(self.phase_usage, 4),
            "overall": round(self.overall_conformance, 4)
        }


# =============================================================================
# TIER SCORES
# =============================================================================

@dataclass
class TierScore:
    """
    Complete score for a tier (Tier 1 or Tier 2)
    
    Aggregates all component scores into final score and grade.
    
    Attributes:
        tier: Scoring tier (open_source or professional)
        overall: Weighted overall score (0.0-1.0)
        grade: Letter grade (A-F)
        pass_threshold: Whether passing threshold met (70%)
        components: Individual component scores
        questa_available: Whether Questa was available
        available_upgrades: List of available tier upgrades
    """
    tier: ScoringTier
    overall: float
    grade: Grade
    pass_threshold: bool
    components: Dict[str, ComponentScore]
    questa_available: bool
    available_upgrades: List[str] = field(default_factory=list)
    
    def __post_init__(self):
        """Validate tier score"""
        if not 0.0 <= self.overall <= 1.0:
            raise ValueError(f"Overall score must be 0.0-1.0, got {self.overall}")
        
        # Validate components sum to ~1.0
        total_weight = sum(c.weight for c in self.components.values())
        if not (0.99 <= total_weight <= 1.01):
            raise ValueError(f"Component weights must sum to 1.0, got {total_weight:.4f}")
    
    def to_percentage(self) -> float:
        """Convert to percentage (0-100)"""
        return self.overall * 100.0
    
    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary"""
        return {
            "tier": self.tier.value,
            "tier_display": self.tier.display_name,
            "overall_score": round(self.overall, 4),
            "percentage": round(self.to_percentage(), 2),
            "grade": self.grade.value,
            "pass": self.pass_threshold,
            "components": {
                name: comp.to_dict()
                for name, comp in self.components.items()
            },
            "questa_available": self.questa_available,
            "available_upgrades": self.available_upgrades
        }


# =============================================================================
# RECOMMENDATIONS
# =============================================================================

@dataclass
class Improvement:
    """
    Actionable improvement recommendation
    
    Attributes:
        component: Affected component
        priority: Priority (high, medium, low)
        current_value: Current metric value
        target_value: Target metric value
        impact: Expected score impact
        actions: Suggested actions
    """
    component: ComponentType
    priority: str
    current_value: float
    target_value: float
    impact: float
    actions: List[str]
    
    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary"""
        return {
            "component": self.component.display_name,
            "priority": self.priority,
            "current": round(self.current_value, 2),
            "target": round(self.target_value, 2),
            "impact": round(self.impact, 2),
            "actions": self.actions
        }


@dataclass
class Recommendation:
    """
    General recommendation for testbench improvement
    
    Attributes:
        category: Recommendation category
        message: Human-readable message
        details: Additional details
        references: External references (URLs, docs)
    """
    category: str
    message: str
    details: Optional[str] = None
    references: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary"""
        return {
            "category": self.category,
            "message": self.message,
            "details": self.details,
            "references": self.references
        }


# =============================================================================
# FINAL REPORT
# =============================================================================

@dataclass
class FinalReport:
    """
    Complete evaluation report
    
    This is the main output of Step 7, consumed by exporters.
    
    Attributes:
        submission_id: Unique submission identifier
        generated_at: Report generation timestamp
        framework_version: TB Eval framework version
        score: Tier score (Tier 1 or Tier 2)
        quality_report_path: Path to quality report (Step 2)
        test_report_path: Path to test report (Step 4)
        coverage_report_path: Path to coverage report (Step 5)
        total_duration_ms: Total evaluation duration
        steps_completed: List of completed pipeline steps
        improvements: Actionable improvement recommendations
        recommendations: General recommendations
        metadata: Additional metadata
    """
    submission_id: str
    generated_at: datetime
    framework_version: str
    
    # Main scoring
    score: TierScore
    
    # Source reports
    quality_report_path: Optional[Path] = None
    test_report_path: Optional[Path] = None
    coverage_report_path: Optional[Path] = None
    
    # Execution metadata
    total_duration_ms: float = 0.0
    steps_completed: List[str] = field(default_factory=list)
    
    # Recommendations
    improvements: List[Improvement] = field(default_factory=list)
    recommendations: List[Recommendation] = field(default_factory=list)
    
    # Additional metadata
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Serialize to dictionary (for JSON export)
        
        Returns:
            Complete dictionary representation
        """
        return {
            "submission_id": self.submission_id,
            "generated_at": self.generated_at.isoformat(),
            "framework_version": self.framework_version,
            
            "score": self.score.to_dict(),
            
            "sources": {
                "quality_report": str(self.quality_report_path) if self.quality_report_path else None,
                "test_report": str(self.test_report_path) if self.test_report_path else None,
                "coverage_report": str(self.coverage_report_path) if self.coverage_report_path else None,
            },
            
            "execution": {
                "total_duration_ms": round(self.total_duration_ms, 2),
                "steps_completed": self.steps_completed,
            },
            
            "improvements": [imp.to_dict() for imp in self.improvements],
            "recommendations": [rec.to_dict() for rec in self.recommendations],
            
            "metadata": self.metadata,
        }
    
    def to_json(self, indent: int = 2) -> str:
        """Serialize to JSON string"""
        return json.dumps(self.to_dict(), indent=indent)
    
    def save(self, path: Path) -> None:
        """
        Save report to file
        
        Args:
            path: Output file path (final_score.json)
        """
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(self.to_json())
    
    @classmethod
    def load(cls, path: Path) -> 'FinalReport':
        """
        Load report from file
        
        Args:
            path: Path to final_score.json
        
        Returns:
            FinalReport instance
        """
        with open(path) as f:
            data = json.load(f)
        
        # Reconstruct report (simplified - full implementation would rebuild all objects)
        score_data = data["score"]
        tier = ScoringTier(score_data["tier"])
        grade = Grade(score_data["grade"])
        
        # Reconstruct components
        components = {}
        for name, comp_data in score_data["components"].items():
            comp_type = ComponentType(comp_data["component"])
            components[name] = ComponentScore(
                component_type=comp_type,
                value=comp_data["score"],
                weight=comp_data["weight"],
                raw_metrics=comp_data.get("raw_metrics", {}),
                threshold_met=comp_data["threshold_met"],
                threshold_value=comp_data.get("threshold_value"),
                details=comp_data.get("details")
            )
        
        tier_score = TierScore(
            tier=tier,
            overall=score_data["overall_score"],
            grade=grade,
            pass_threshold=score_data["pass"],
            components=components,
            questa_available=score_data["questa_available"]
        )
        
        return cls(
            submission_id=data["submission_id"],
            generated_at=datetime.fromisoformat(data["generated_at"]),
            framework_version=data["framework_version"],
            score=tier_score,
            total_duration_ms=data["execution"]["total_duration_ms"],
            steps_completed=data["execution"]["steps_completed"],
        )


# =============================================================================
# UTILITY FUNCTIONS
# =============================================================================

def _calculate_variance(values: List[float]) -> float:
    """Calculate variance of a list of values"""
    if len(values) < 2:
        return 0.0
    
    mean = sum(values) / len(values)
    variance = sum((x - mean) ** 2 for x in values) / len(values)
    return variance


def _calculate_std_dev(values: List[float]) -> float:
    """Calculate standard deviation"""
    return math.sqrt(_calculate_variance(values))


# =============================================================================
# EXAMPLE USAGE
# =============================================================================

if __name__ == "__main__":
    # Example: Create a Tier 1 score
    
    # Component scores
    structural_cov = ComponentScore(
        component_type=ComponentType.STRUCTURAL_COVERAGE,
        value=0.87,
        weight=0.50,
        raw_metrics={"line": 86.7, "branch": 95.0},
        threshold_met=True,
        threshold_value=0.80
    )
    
    test_pass_rate = ComponentScore(
        component_type=ComponentType.TEST_PASS_RATE,
        value=0.95,
        weight=0.20,
        raw_metrics={"passed": 19, "total": 20},
        threshold_met=True
    )
    
    code_quality = ComponentScore(
        component_type=ComponentType.CODE_QUALITY,
        value=0.73,
        weight=0.15,
        raw_metrics={"violations": 12},
        threshold_met=True
    )
    
    efficiency = ComponentScore(
        component_type=ComponentType.TEST_EFFICIENCY,
        value=0.82,
        weight=0.10,
        raw_metrics={"runtime_ms": 1500},
        threshold_met=True
    )
    
    behavioral = ComponentScore(
        component_type=ComponentType.BEHAVIORAL_ACCURACY,
        value=0.65,
        weight=0.05,
        raw_metrics={"assertions": 15},
        threshold_met=True
    )
    
    # Tier score
    tier_score = TierScore(
        tier=ScoringTier.OPEN_SOURCE,
        overall=0.85,
        grade=Grade.B,
        pass_threshold=True,
        components={
            "structural_coverage": structural_cov,
            "test_pass_rate": test_pass_rate,
            "code_quality": code_quality,
            "test_efficiency": efficiency,
            "behavioral_accuracy": behavioral,
        },
        questa_available=False,
        available_upgrades=["professional"]
    )
    
    # Final report
    report = FinalReport(
        submission_id="student_123_fifo",
        generated_at=datetime.now(),
        framework_version="0.1.0",
        score=tier_score,
        total_duration_ms=2500.0,
        steps_completed=["intake", "quality", "classify", "test", "coverage", "score"]
    )
    
    # Print summary
    print(report.to_json())
