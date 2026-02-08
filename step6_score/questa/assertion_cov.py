"""
Assertion coverage parser for Questa

Parses SystemVerilog Assertion (SVA) coverage data from Questa:
- Assertion definitions
- Assertion hits (pass/fail counts)
- Assertion vacuity
- Assertion coverage percentage
- Property verification results

Supports:
- UCDB (Unified Coverage Database) via vcover
- Text report parsing (fallback)

Author: TB Eval Team
Version: 0.1.0
"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional, Dict, List, Set, Tuple, Any
from enum import Enum
import subprocess
import re
import logging

from ..models import (
    ComponentScore,
    ComponentType,
    AssertionCoverageMetrics,
    Improvement,
)

logger = logging.getLogger(__name__)


# =============================================================================
# ENUMS
# =============================================================================

class AssertionStatus(Enum):
    """Assertion status"""
    NEVER_FIRED = "never_fired"
    PASSED = "passed"
    FAILED = "failed"
    VACUOUS = "vacuous"
    DISABLED = "disabled"


class AssertionSeverity(Enum):
    """Assertion severity level"""
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"
    FATAL = "fatal"


# =============================================================================
# DATA MODELS
# =============================================================================

@dataclass
class AssertionData:
    """
    Single assertion data
    
    Attributes:
        name: Assertion name
        type: Assertion type (assert, assume, cover)
        file: Source file
        line: Line number
        pass_count: Number of times assertion passed
        fail_count: Number of times assertion failed
        vacuous_count: Number of vacuous evaluations
        status: Current status
        severity: Severity level
        message: Assertion message/description
    """
    name: str
    type: str
    file: str
    line: int
    pass_count: int = 0
    fail_count: int = 0
    vacuous_count: int = 0
    status: AssertionStatus = AssertionStatus.NEVER_FIRED
    severity: AssertionSeverity = AssertionSeverity.ERROR
    message: Optional[str] = None
    
    @property
    def total_checks(self) -> int:
        """Total number of checks"""
        return self.pass_count + self.fail_count + self.vacuous_count
    
    @property
    def covered(self) -> bool:
        """Check if assertion is covered (fired at least once)"""
        return self.pass_count > 0 or self.fail_count > 0
    
    @property
    def passing(self) -> bool:
        """Check if assertion has no failures"""
        return self.fail_count == 0
    
    @property
    def has_failures(self) -> bool:
        """Check if assertion has failures"""
        return self.fail_count > 0


@dataclass
class AssertionGroupData:
    """
    Group of assertions (module/scope)
    
    Attributes:
        name: Group name (module/scope)
        assertions: Dictionary of assertions (name -> AssertionData)
        coverage: Group coverage percentage
    """
    name: str
    assertions: Dict[str, AssertionData] = field(default_factory=dict)
    coverage: float = 0.0
    
    def calculate_coverage(self) -> float:
        """Calculate group coverage"""
        if not self.assertions:
            return 0.0
        
        covered = sum(1 for a in self.assertions.values() if a.covered)
        self.coverage = (covered / len(self.assertions)) * 100.0
        return self.coverage
    
    @property
    def total_assertions(self) -> int:
        """Total number of assertions"""
        return len(self.assertions)
    
    @property
    def covered_assertions(self) -> int:
        """Number of covered assertions"""
        return sum(1 for a in self.assertions.values() if a.covered)
    
    @property
    def failed_assertions(self) -> int:
        """Number of assertions with failures"""
        return sum(1 for a in self.assertions.values() if a.has_failures)


# =============================================================================
# ASSERTION COVERAGE PARSER
# =============================================================================

class AssertionCoverageParser:
    """
    Parse Questa assertion coverage data
    
    Supports two modes:
    1. UCDB parsing via vcover tool (preferred)
    2. Text report parsing (fallback)
    """
    
    def __init__(self, vcover_path: Optional[str] = None):
        """
        Initialize assertion coverage parser
        
        Args:
            vcover_path: Path to vcover tool (auto-detect if None)
        """
        self.vcover_path = vcover_path or self._find_vcover()
        self.groups: Dict[str, AssertionGroupData] = {}
        self.all_assertions: Dict[str, AssertionData] = {}
    
    def _find_vcover(self) -> Optional[str]:
        """Find vcover tool in PATH"""
        import shutil
        return shutil.which("vcover")
    
    def parse_ucdb(self, ucdb_path: Path) -> Dict[str, AssertionGroupData]:
        """
        Parse UCDB file using vcover
        
        Args:
            ucdb_path: Path to .ucdb file
        
        Returns:
            Dictionary of assertion groups
        
        Raises:
            FileNotFoundError: If UCDB file not found
            ValueError: If vcover not available
        """
        ucdb_path = Path(ucdb_path)
        
        if not ucdb_path.exists():
            raise FileNotFoundError(f"UCDB file not found: {ucdb_path}")
        
        if not self.vcover_path:
            raise ValueError("vcover tool not available - cannot parse UCDB")
        
        logger.info(f"Parsing assertion coverage from UCDB: {ucdb_path}")
        
        # Generate assertion report from UCDB
        try:
            result = subprocess.run(
                [self.vcover_path, "report", "-details", "-assert", str(ucdb_path)],
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode != 0:
                raise ValueError(f"vcover failed: {result.stderr}")
            
            # Parse the text report
            self.groups = self._parse_text_report(result.stdout)
            
            logger.info(f"Parsed {len(self.all_assertions)} assertions from UCDB")
            return self.groups
        
        except subprocess.TimeoutExpired:
            raise ValueError("vcover timed out")
        except Exception as e:
            raise ValueError(f"Failed to parse UCDB: {e}")
    
    def parse_text_report(self, report_path: Path) -> Dict[str, AssertionGroupData]:
        """
        Parse text assertion report
        
        Args:
            report_path: Path to text report file
        
        Returns:
            Dictionary of assertion groups
        """
        report_path = Path(report_path)
        
        if not report_path.exists():
            raise FileNotFoundError(f"Report file not found: {report_path}")
        
        logger.info(f"Parsing assertion report: {report_path}")
        
        report_text = report_path.read_text()
        self.groups = self._parse_text_report(report_text)
        
        logger.info(f"Parsed {len(self.all_assertions)} assertions from text report")
        return self.groups
    
    def _parse_text_report(self, report_text: str) -> Dict[str, AssertionGroupData]:
        """
        Parse text assertion report content
        
        Args:
            report_text: Report text content
        
        Returns:
            Dictionary of assertion groups
        """
        groups = {}
        lines = report_text.split('\n')
        
        current_group = None
        
        for i, line in enumerate(lines):
            # Match assertion group/module header
            # Example: "Module: top.dut  Assertions: 15"
            group_match = re.match(r'\s*(?:Module|Scope):\s+(\S+)', line)
            if group_match:
                group_name = group_match.group(1)
                current_group = AssertionGroupData(name=group_name)
                groups[group_name] = current_group
                logger.debug(f"Found assertion group: {group_name}")
                continue
            
            # Match assertion entry
            # Example: "  assert_valid: file.sv:45  Passed: 100  Failed: 0  Status: PASS"
            assert_match = re.match(
                r'\s+(\w+):\s+(\S+):(\d+)\s+(?:Passed|Pass):\s*(\d+)\s+(?:Failed|Fail):\s*(\d+)',
                line
            )
            if assert_match and current_group:
                name = assert_match.group(1)
                file = assert_match.group(2)
                line_num = int(assert_match.group(3))
                pass_count = int(assert_match.group(4))
                fail_count = int(assert_match.group(5))
                
                # Determine status
                if fail_count > 0:
                    status = AssertionStatus.FAILED
                elif pass_count > 0:
                    status = AssertionStatus.PASSED
                else:
                    status = AssertionStatus.NEVER_FIRED
                
                assertion = AssertionData(
                    name=name,
                    type="assert",
                    file=file,
                    line=line_num,
                    pass_count=pass_count,
                    fail_count=fail_count,
                    status=status
                )
                
                current_group.assertions[name] = assertion
                self.all_assertions[f"{current_group.name}.{name}"] = assertion
                
                logger.debug(
                    f"  Found assertion: {name} "
                    f"(pass: {pass_count}, fail: {fail_count})"
                )
                continue
            
            # Match vacuous count
            # Example: "  Vacuous: 5"
            vacuous_match = re.match(r'\s+Vacuous:\s*(\d+)', line)
            if vacuous_match and current_group and current_group.assertions:
                vacuous_count = int(vacuous_match.group(1))
                # Apply to last assertion
                last_assertion = list(current_group.assertions.values())[-1]
                last_assertion.vacuous_count = vacuous_count
        
        # Calculate coverage for each group
        for group in groups.values():
            group.calculate_coverage()
        
        return groups
    
    def get_overall_coverage(self) -> float:
        """
        Calculate overall assertion coverage
        
        Returns:
            Overall coverage percentage (0-100)
        """
        if not self.all_assertions:
            return 0.0
        
        covered = sum(1 for a in self.all_assertions.values() if a.covered)
        return (covered / len(self.all_assertions)) * 100.0
    
    def get_pass_count(self) -> int:
        """Get total number of passing assertions"""
        return sum(1 for a in self.all_assertions.values() if a.passing and a.covered)
    
    def get_fail_count(self) -> int:
        """Get total number of failing assertions"""
        return sum(1 for a in self.all_assertions.values() if a.has_failures)
    
    def get_never_fired_count(self) -> int:
        """Get number of assertions that never fired"""
        return sum(1 for a in self.all_assertions.values() if not a.covered)
    
    def get_failed_assertions(self) -> List[AssertionData]:
        """
        Get list of failed assertions
        
        Returns:
            List of assertions with failures
        """
        return [a for a in self.all_assertions.values() if a.has_failures]
    
    def get_uncovered_assertions(self) -> List[AssertionData]:
        """
        Get list of uncovered assertions
        
        Returns:
            List of assertions that never fired
        """
        return [a for a in self.all_assertions.values() if not a.covered]


# =============================================================================
# ASSERTION COVERAGE SCORER
# =============================================================================

@dataclass
class AssertionCoverageScoringConfig:
    """Configuration for assertion coverage scoring"""
    weight: float = 0.15  # Default Tier 2 weight
    min_coverage: float = 85.0
    allow_failures: bool = False
    max_failures: int = 0


class AssertionCoverageScorer:
    """
    Score assertion coverage component
    
    Scores based on:
    - Assertion coverage (% of assertions that fired)
    - Pass/fail ratio
    - Number of uncovered assertions
    """
    
    def __init__(
        self,
        config: Optional[AssertionCoverageScoringConfig] = None,
        vcover_path: Optional[str] = None
    ):
        """
        Initialize assertion coverage scorer
        
        Args:
            config: Scoring configuration
            vcover_path: Path to vcover tool
        """
        self.config = config or AssertionCoverageScoringConfig()
        self.parser = AssertionCoverageParser(vcover_path)
        self.metrics: Optional[AssertionCoverageMetrics] = None
    
    def score(
        self,
        ucdb_path: Optional[Path] = None,
        report_path: Optional[Path] = None
    ) -> ComponentScore:
        """
        Calculate assertion coverage component score
        
        Args:
            ucdb_path: Path to .ucdb file
            report_path: Path to text report (fallback)
        
        Returns:
            ComponentScore for assertion coverage
        
        Raises:
            ValueError: If neither UCDB nor report provided
        """
        logger.info("Scoring assertion coverage")
        
        # Parse assertion data
        if ucdb_path:
            self.parser.parse_ucdb(ucdb_path)
        elif report_path:
            self.parser.parse_text_report(report_path)
        else:
            raise ValueError("Either ucdb_path or report_path required")
        
        # Calculate metrics
        total = len(self.parser.all_assertions)
        covered = total - self.parser.get_never_fired_count()
        passed = self.parser.get_pass_count()
        failed = self.parser.get_fail_count()
        
        coverage_pct = (covered / total * 100.0) if total > 0 else 0.0
        
        self.metrics = AssertionCoverageMetrics(
            total_assertions=total,
            covered_assertions=covered,
            pass_count=passed,
            fail_count=failed,
            coverage_percentage=coverage_pct
        )
        
        # Calculate score
        # Base score on coverage percentage
        score_value = coverage_pct / 100.0
        
        # Penalize failures if not allowed
        if not self.config.allow_failures and failed > 0:
            failure_penalty = min(0.5, failed * 0.1)
            score_value = max(0.0, score_value - failure_penalty)
        
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
            component_type=ComponentType.ASSERTION_COVERAGE,
            value=score_value,
            weight=self.config.weight,
            raw_metrics=raw_metrics,
            threshold_met=threshold_met,
            threshold_value=self.config.min_coverage / 100.0,
            details=details,
            recommendations=recommendations,
        )
        
        logger.info(
            f"Assertion coverage score: {score_value:.4f} "
            f"({component_score.percentage:.2f}%) - "
            f"{'PASS' if threshold_met else 'FAIL'}"
        )
        
        return component_score
    
    def _check_thresholds(self) -> bool:
        """Check if assertion coverage meets thresholds"""
        if not self.metrics:
            return False
        
        # Coverage threshold
        if self.metrics.coverage_percentage < self.config.min_coverage:
            return False
        
        # Failure threshold
        if not self.config.allow_failures and self.metrics.fail_count > self.config.max_failures:
            return False
        
        return True
    
    def _get_raw_metrics(self) -> Dict[str, Any]:
        """Get raw assertion coverage metrics"""
        if not self.metrics:
            return {}
        
        return {
            "total_assertions": self.metrics.total_assertions,
            "covered_assertions": self.metrics.covered_assertions,
            "pass_count": self.metrics.pass_count,
            "fail_count": self.metrics.fail_count,
            "coverage_percentage": self.metrics.coverage_percentage,
            "uncovered_count": self.parser.get_never_fired_count(),
        }
    
    def _generate_details(self) -> str:
        """Generate human-readable details"""
        if not self.metrics:
            return "Assertion coverage metrics not available"
        
        m = self.metrics
        
        details = (
            f"Assertion Coverage: {m.coverage_percentage:.2f}%\n"
            f"  Total:     {m.total_assertions}\n"
            f"  Covered:   {m.covered_assertions}\n"
            f"  Passed:    {m.pass_count}\n"
            f"  Failed:    {m.fail_count}\n"
            f"  Uncovered: {m.total_assertions - m.covered_assertions}"
        )
        
        return details
    
    def _generate_recommendations(self) -> List[str]:
        """Generate recommendations for improving assertion coverage"""
        if not self.metrics:
            return []
        
        recommendations = []
        m = self.metrics
        
        # Coverage recommendations
        if m.coverage_percentage < self.config.min_coverage:
            gap = self.config.min_coverage - m.coverage_percentage
            uncovered = m.total_assertions - m.covered_assertions
            recommendations.append(
                f"Increase assertion coverage by {gap:.1f}% to meet {self.config.min_coverage}% threshold. "
                f"{uncovered} assertion(s) never fired - add tests to trigger these assertions."
            )
        
        # Failure recommendations
        if m.fail_count > 0:
            recommendations.append(
                f"Fix {m.fail_count} failing assertion(s). "
                f"Review assertion failures in simulation logs and correct design or testbench issues."
            )
        
        # Uncovered assertions
        uncovered_list = self.parser.get_uncovered_assertions()
        if uncovered_list:
            recommendations.append(
                f"{len(uncovered_list)} assertion(s) never triggered. "
                f"Add directed tests to exercise assertion conditions."
            )
        
        return recommendations
    
    def generate_improvements(self) -> List[Improvement]:
        """Generate actionable improvements for assertion coverage"""
        if not self.metrics:
            return []
        
        improvements = []
        m = self.metrics
        
        # Coverage improvement
        if m.coverage_percentage < self.config.min_coverage:
            impact = (self.config.min_coverage - m.coverage_percentage) / 100.0 * self.config.weight
            improvements.append(Improvement(
                component=ComponentType.ASSERTION_COVERAGE,
                priority="high" if m.fail_count > 0 else "medium",
                current_value=m.coverage_percentage,
                target_value=self.config.min_coverage,
                impact=impact,
                actions=[
                    "Review uncovered assertions and add targeted tests",
                    "Increase test scenario diversity to trigger more assertions",
                    "Check if assertions are properly enabled in simulation",
                    "Verify assertion conditions are reachable",
                ]
            ))
        
        # Failure improvement
        if m.fail_count > 0:
            impact = 0.10 * self.config.weight  # Significant impact
            improvements.append(Improvement(
                component=ComponentType.ASSERTION_COVERAGE,
                priority="high",
                current_value=0.0,
                target_value=100.0,
                impact=impact,
                actions=[
                    f"Fix {m.fail_count} failing assertion(s)",
                    "Review assertion failure logs and waveforms",
                    "Determine if failures are design bugs or incorrect assertions",
                    "Update assertions or fix design to resolve failures",
                ]
            ))
        
        improvements.sort(key=lambda x: x.impact, reverse=True)
        return improvements


# =============================================================================
# CONVENIENCE FUNCTIONS
# =============================================================================

def score_assertion_coverage(
    ucdb_path: Optional[Path] = None,
    report_path: Optional[Path] = None,
    weight: float = 0.15
) -> ComponentScore:
    """
    Convenience function to score assertion coverage
    
    Args:
        ucdb_path: Path to .ucdb file
        report_path: Path to text report
        weight: Weight for this component
    
    Returns:
        ComponentScore for assertion coverage
    """
    config = AssertionCoverageScoringConfig(weight=weight)
    scorer = AssertionCoverageScorer(config=config)
    return scorer.score(ucdb_path, report_path)
