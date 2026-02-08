"""
Functional coverage parser for Questa

Parses SystemVerilog functional coverage data from Questa:
- Covergroups
- Coverpoints
- Cross coverage
- Bins and bin hits
- Coverage goals

Supports:
- UCDB (Unified Coverage Database) via vcover
- Text report parsing (fallback)

Author: TB Eval Team
Version: 0.1.0
"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional, Dict, List, Set, Tuple, Any
import subprocess
import re
import logging

from ..models import (
    ComponentScore,
    ComponentType,
    FunctionalCoverageMetrics,
    Improvement,
)

logger = logging.getLogger(__name__)


# =============================================================================
# DATA MODELS
# =============================================================================

@dataclass
class BinData:
    """
    Functional coverage bin data
    
    Attributes:
        name: Bin name
        hits: Number of hits
        goal: Target number of hits (0 = any hit counts)
        covered: Whether bin goal is met
    """
    name: str
    hits: int
    goal: int = 0
    
    @property
    def covered(self) -> bool:
        """Check if bin is covered"""
        if self.goal == 0:
            return self.hits > 0
        return self.hits >= self.goal


@dataclass
class CoverpointData:
    """
    Coverpoint data
    
    Attributes:
        name: Coverpoint name
        bins: Dictionary of bins (name -> BinData)
        coverage: Coverage percentage (0-100)
        type_option: Coverpoint type (e.g., 'option.weight')
    """
    name: str
    bins: Dict[str, BinData] = field(default_factory=dict)
    coverage: float = 0.0
    type_option: Optional[str] = None
    
    def calculate_coverage(self) -> float:
        """Calculate coverpoint coverage based on bins"""
        if not self.bins:
            return 0.0
        
        covered_bins = sum(1 for bin in self.bins.values() if bin.covered)
        self.coverage = (covered_bins / len(self.bins)) * 100.0
        return self.coverage


@dataclass
class CrossCoverageData:
    """
    Cross coverage data
    
    Attributes:
        name: Cross coverage name
        dimensions: List of coverpoint names being crossed
        bins: Dictionary of cross bins (name -> BinData)
        coverage: Coverage percentage (0-100)
    """
    name: str
    dimensions: List[str] = field(default_factory=list)
    bins: Dict[str, BinData] = field(default_factory=dict)
    coverage: float = 0.0
    
    def calculate_coverage(self) -> float:
        """Calculate cross coverage based on bins"""
        if not self.bins:
            return 0.0
        
        covered_bins = sum(1 for bin in self.bins.values() if bin.covered)
        self.coverage = (covered_bins / len(self.bins)) * 100.0
        return self.coverage


@dataclass
class CovergroupData:
    """
    Covergroup data
    
    Attributes:
        name: Covergroup name
        instance: Instance name
        coverpoints: Dictionary of coverpoints (name -> CoverpointData)
        crosses: Dictionary of cross coverage (name -> CrossCoverageData)
        coverage: Overall covergroup coverage (0-100)
        goal: Coverage goal percentage
    """
    name: str
    instance: str
    coverpoints: Dict[str, CoverpointData] = field(default_factory=dict)
    crosses: Dict[str, CrossCoverageData] = field(default_factory=dict)
    coverage: float = 0.0
    goal: float = 100.0
    
    def calculate_coverage(self) -> float:
        """Calculate overall covergroup coverage"""
        if not self.coverpoints and not self.crosses:
            return 0.0
        
        # Weight coverpoints and crosses equally
        coverpoint_coverage = 0.0
        if self.coverpoints:
            coverpoint_coverage = sum(cp.coverage for cp in self.coverpoints.values()) / len(self.coverpoints)
        
        cross_coverage = 0.0
        if self.crosses:
            cross_coverage = sum(cross.coverage for cross in self.crosses.values()) / len(self.crosses)
        
        if self.coverpoints and self.crosses:
            self.coverage = (coverpoint_coverage + cross_coverage) / 2.0
        elif self.coverpoints:
            self.coverage = coverpoint_coverage
        else:
            self.coverage = cross_coverage
        
        return self.coverage
    
    @property
    def goal_met(self) -> bool:
        """Check if coverage goal is met"""
        return self.coverage >= self.goal


# =============================================================================
# FUNCTIONAL COVERAGE PARSER
# =============================================================================

class FunctionalCoverageParser:
    """
    Parse Questa functional coverage data
    
    Supports two modes:
    1. UCDB parsing via vcover tool (preferred)
    2. Text report parsing (fallback)
    """
    
    def __init__(self, vcover_path: Optional[str] = None):
        """
        Initialize functional coverage parser
        
        Args:
            vcover_path: Path to vcover tool (auto-detect if None)
        """
        self.vcover_path = vcover_path or self._find_vcover()
        self.covergroups: Dict[str, CovergroupData] = {}
    
    def _find_vcover(self) -> Optional[str]:
        """Find vcover tool in PATH"""
        import shutil
        return shutil.which("vcover")
    
    def parse_ucdb(self, ucdb_path: Path) -> Dict[str, CovergroupData]:
        """
        Parse UCDB file using vcover
        
        Args:
            ucdb_path: Path to .ucdb file
        
        Returns:
            Dictionary of covergroups (name -> CovergroupData)
        
        Raises:
            FileNotFoundError: If UCDB file not found
            ValueError: If vcover not available
        """
        ucdb_path = Path(ucdb_path)
        
        if not ucdb_path.exists():
            raise FileNotFoundError(f"UCDB file not found: {ucdb_path}")
        
        if not self.vcover_path:
            raise ValueError("vcover tool not available - cannot parse UCDB")
        
        logger.info(f"Parsing UCDB: {ucdb_path}")
        
        # Generate text report from UCDB
        try:
            result = subprocess.run(
                [self.vcover_path, "report", "-details", str(ucdb_path)],
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode != 0:
                raise ValueError(f"vcover failed: {result.stderr}")
            
            # Parse the text report
            self.covergroups = self._parse_text_report(result.stdout)
            
            logger.info(f"Parsed {len(self.covergroups)} covergroups from UCDB")
            return self.covergroups
        
        except subprocess.TimeoutExpired:
            raise ValueError("vcover timed out")
        except Exception as e:
            raise ValueError(f"Failed to parse UCDB: {e}")
    
    def parse_text_report(self, report_path: Path) -> Dict[str, CovergroupData]:
        """
        Parse text coverage report
        
        Args:
            report_path: Path to text report file
        
        Returns:
            Dictionary of covergroups
        """
        report_path = Path(report_path)
        
        if not report_path.exists():
            raise FileNotFoundError(f"Report file not found: {report_path}")
        
        logger.info(f"Parsing text report: {report_path}")
        
        report_text = report_path.read_text()
        self.covergroups = self._parse_text_report(report_text)
        
        logger.info(f"Parsed {len(self.covergroups)} covergroups from text report")
        return self.covergroups
    
    def _parse_text_report(self, report_text: str) -> Dict[str, CovergroupData]:
        """
        Parse text coverage report content
        
        Args:
            report_text: Report text content
        
        Returns:
            Dictionary of covergroups
        """
        covergroups = {}
        
        # Split into lines
        lines = report_text.split('\n')
        
        current_covergroup = None
        current_coverpoint = None
        current_cross = None
        
        for i, line in enumerate(lines):
            # Match covergroup header
            # Example: "Covergroup: my_cg  Coverage: 85.5%"
            cg_match = re.match(r'\s*Covergroup:\s+(\S+)\s+.*Coverage:\s+([\d.]+)%', line)
            if cg_match:
                cg_name = cg_match.group(1)
                cg_coverage = float(cg_match.group(2))
                
                current_covergroup = CovergroupData(
                    name=cg_name,
                    instance=cg_name,
                    coverage=cg_coverage
                )
                covergroups[cg_name] = current_covergroup
                logger.debug(f"Found covergroup: {cg_name} ({cg_coverage:.2f}%)")
                continue
            
            # Match coverpoint header
            # Example: "  Coverpoint: addr_cp  Coverage: 90.0%"
            cp_match = re.match(r'\s+Coverpoint:\s+(\S+)\s+.*Coverage:\s+([\d.]+)%', line)
            if cp_match and current_covergroup:
                cp_name = cp_match.group(1)
                cp_coverage = float(cp_match.group(2))
                
                current_coverpoint = CoverpointData(
                    name=cp_name,
                    coverage=cp_coverage
                )
                current_covergroup.coverpoints[cp_name] = current_coverpoint
                current_cross = None
                logger.debug(f"  Found coverpoint: {cp_name} ({cp_coverage:.2f}%)")
                continue
            
            # Match cross coverage header
            # Example: "  Cross: addr_x_data  Coverage: 75.0%"
            cross_match = re.match(r'\s+Cross:\s+(\S+)\s+.*Coverage:\s+([\d.]+)%', line)
            if cross_match and current_covergroup:
                cross_name = cross_match.group(1)
                cross_coverage = float(cross_match.group(2))
                
                current_cross = CrossCoverageData(
                    name=cross_name,
                    coverage=cross_coverage
                )
                current_covergroup.crosses[cross_name] = current_cross
                current_coverpoint = None
                logger.debug(f"  Found cross: {cross_name} ({cross_coverage:.2f}%)")
                continue
            
            # Match bin data
            # Example: "    Bin: low (0-9)  Hits: 15  Goal: 10"
            bin_match = re.match(r'\s+Bin:\s+(\S+).*Hits:\s+(\d+)(?:.*Goal:\s+(\d+))?', line)
            if bin_match:
                bin_name = bin_match.group(1)
                hits = int(bin_match.group(2))
                goal = int(bin_match.group(3)) if bin_match.group(3) else 0
                
                bin_data = BinData(name=bin_name, hits=hits, goal=goal)
                
                if current_coverpoint:
                    current_coverpoint.bins[bin_name] = bin_data
                elif current_cross:
                    current_cross.bins[bin_name] = bin_data
                
                logger.debug(f"    Found bin: {bin_name} (hits: {hits}, goal: {goal})")
        
        return covergroups
    
    def get_overall_coverage(self) -> float:
        """
        Calculate overall functional coverage
        
        Returns:
            Overall coverage percentage (0-100)
        """
        if not self.covergroups:
            return 0.0
        
        return sum(cg.coverage for cg in self.covergroups.values()) / len(self.covergroups)
    
    def get_coverpoint_coverage(self) -> float:
        """
        Calculate average coverpoint coverage
        
        Returns:
            Average coverpoint coverage percentage (0-100)
        """
        total_coverpoints = 0
        total_coverage = 0.0
        
        for cg in self.covergroups.values():
            for cp in cg.coverpoints.values():
                total_coverpoints += 1
                total_coverage += cp.coverage
        
        if total_coverpoints == 0:
            return 0.0
        
        return total_coverage / total_coverpoints
    
    def get_cross_coverage(self) -> float:
        """
        Calculate average cross coverage
        
        Returns:
            Average cross coverage percentage (0-100)
        """
        total_crosses = 0
        total_coverage = 0.0
        
        for cg in self.covergroups.values():
            for cross in cg.crosses.values():
                total_crosses += 1
                total_coverage += cross.coverage
        
        if total_crosses == 0:
            return 0.0
        
        return total_coverage / total_crosses
    
    def get_bin_coverage(self) -> float:
        """
        Calculate bin hit coverage
        
        Returns:
            Bin coverage percentage (0-100)
        """
        total_bins = 0
        covered_bins = 0
        
        for cg in self.covergroups.values():
            for cp in cg.coverpoints.values():
                for bin in cp.bins.values():
                    total_bins += 1
                    if bin.covered:
                        covered_bins += 1
            
            for cross in cg.crosses.values():
                for bin in cross.bins.values():
                    total_bins += 1
                    if bin.covered:
                        covered_bins += 1
        
        if total_bins == 0:
            return 0.0
        
        return (covered_bins / total_bins) * 100.0
    
    def check_goals(self) -> Tuple[int, int]:
        """
        Check coverage goals
        
        Returns:
            Tuple of (covergroups_meeting_goal, total_covergroups)
        """
        total = len(self.covergroups)
        meeting_goal = sum(1 for cg in self.covergroups.values() if cg.goal_met)
        
        return meeting_goal, total


# =============================================================================
# FUNCTIONAL COVERAGE SCORER
# =============================================================================

@dataclass
class FunctionalCoverageScoringConfig:
    """Configuration for functional coverage scoring"""
    weight: float = 0.25  # Default Tier 2 weight
    min_covergroup_coverage: float = 80.0
    min_coverpoint_coverage: float = 85.0
    min_cross_coverage: float = 75.0
    min_bin_coverage: float = 80.0


class FunctionalCoverageScorer:
    """
    Score functional coverage component
    
    Scores based on:
    - Overall covergroup coverage
    - Coverpoint coverage
    - Cross coverage
    - Bin hit coverage
    - Coverage goal achievement
    """
    
    def __init__(
        self,
        config: Optional[FunctionalCoverageScoringConfig] = None,
        vcover_path: Optional[str] = None
    ):
        """
        Initialize functional coverage scorer
        
        Args:
            config: Scoring configuration
            vcover_path: Path to vcover tool
        """
        self.config = config or FunctionalCoverageScoringConfig()
        self.parser = FunctionalCoverageParser(vcover_path)
        self.metrics: Optional[FunctionalCoverageMetrics] = None
    
    def score(
        self,
        ucdb_path: Optional[Path] = None,
        report_path: Optional[Path] = None
    ) -> ComponentScore:
        """
        Calculate functional coverage component score
        
        Args:
            ucdb_path: Path to .ucdb file
            report_path: Path to text report (fallback)
        
        Returns:
            ComponentScore for functional coverage
        
        Raises:
            ValueError: If neither UCDB nor report provided
        """
        logger.info("Scoring functional coverage")
        
        # Parse coverage data
        if ucdb_path:
            self.parser.parse_ucdb(ucdb_path)
        elif report_path:
            self.parser.parse_text_report(report_path)
        else:
            raise ValueError("Either ucdb_path or report_path required")
        
        # Calculate metrics
        self.metrics = FunctionalCoverageMetrics(
            covergroup_coverage=self.parser.get_overall_coverage(),
            coverpoint_coverage=self.parser.get_coverpoint_coverage(),
            cross_coverage=self.parser.get_cross_coverage(),
            bin_coverage=self.parser.get_bin_coverage(),
            goal_met=False  # Will be set below
        )
        
        # Check goals
        meeting_goal, total = self.parser.check_goals()
        self.metrics.goal_met = meeting_goal == total and total > 0
        
        # Calculate overall score (weighted average)
        score_value = (
            self.metrics.covergroup_coverage * 0.40 +
            self.metrics.coverpoint_coverage * 0.30 +
            self.metrics.cross_coverage * 0.20 +
            self.metrics.bin_coverage * 0.10
        ) / 100.0
        
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
            component_type=ComponentType.FUNCTIONAL_COVERAGE,
            value=score_value,
            weight=self.config.weight,
            raw_metrics=raw_metrics,
            threshold_met=threshold_met,
            threshold_value=self.config.min_covergroup_coverage / 100.0,
            details=details,
            recommendations=recommendations,
        )
        
        logger.info(
            f"Functional coverage score: {score_value:.4f} "
            f"({component_score.percentage:.2f}%) - "
            f"{'PASS' if threshold_met else 'FAIL'}"
        )
        
        return component_score
    
    def _check_thresholds(self) -> bool:
        """Check if functional coverage meets thresholds"""
        if not self.metrics:
            return False
        
        checks = [
            self.metrics.covergroup_coverage >= self.config.min_covergroup_coverage,
            self.metrics.coverpoint_coverage >= self.config.min_coverpoint_coverage,
            self.metrics.cross_coverage >= self.config.min_cross_coverage,
            self.metrics.bin_coverage >= self.config.min_bin_coverage,
        ]
        
        return all(checks)
    
    def _get_raw_metrics(self) -> Dict[str, Any]:
        """Get raw functional coverage metrics"""
        if not self.metrics:
            return {}
        
        return {
            "covergroup_coverage": self.metrics.covergroup_coverage,
            "coverpoint_coverage": self.metrics.coverpoint_coverage,
            "cross_coverage": self.metrics.cross_coverage,
            "bin_coverage": self.metrics.bin_coverage,
            "goal_met": self.metrics.goal_met,
            "total_covergroups": len(self.parser.covergroups),
        }
    
    def _generate_details(self) -> str:
        """Generate human-readable details"""
        if not self.metrics:
            return "Functional coverage metrics not available"
        
        m = self.metrics
        
        details = (
            f"Functional Coverage: {(m.covergroup_coverage + m.coverpoint_coverage + m.cross_coverage) / 3:.2f}%\n"
            f"  Covergroup:  {m.covergroup_coverage:.2f}%\n"
            f"  Coverpoint:  {m.coverpoint_coverage:.2f}%\n"
            f"  Cross:       {m.cross_coverage:.2f}%\n"
            f"  Bin:         {m.bin_coverage:.2f}%\n"
            f"  Goals Met:   {'Yes' if m.goal_met else 'No'}"
        )
        
        return details
    
    def _generate_recommendations(self) -> List[str]:
        """Generate recommendations for improving functional coverage"""
        if not self.metrics:
            return []
        
        recommendations = []
        m = self.metrics
        
        if m.covergroup_coverage < self.config.min_covergroup_coverage:
            gap = self.config.min_covergroup_coverage - m.covergroup_coverage
            recommendations.append(
                f"Increase covergroup coverage by {gap:.1f}% to meet {self.config.min_covergroup_coverage}% threshold. "
                f"Add more test scenarios to hit uncovered bins."
            )
        
        if m.coverpoint_coverage < self.config.min_coverpoint_coverage:
            gap = self.config.min_coverpoint_coverage - m.coverpoint_coverage
            recommendations.append(
                f"Increase coverpoint coverage by {gap:.1f}% to meet {self.config.min_coverpoint_coverage}% threshold. "
                f"Ensure all coverpoint bins are hit with sufficient test cases."
            )
        
        if m.cross_coverage < self.config.min_cross_coverage:
            gap = self.config.min_cross_coverage - m.cross_coverage
            recommendations.append(
                f"Increase cross coverage by {gap:.1f}% to meet {self.config.min_cross_coverage}% threshold. "
                f"Add tests that exercise combinations of coverpoint values."
            )
        
        if m.bin_coverage < self.config.min_bin_coverage:
            gap = self.config.min_bin_coverage - m.bin_coverage
            recommendations.append(
                f"Increase bin coverage by {gap:.1f}% to meet {self.config.min_bin_coverage}% threshold. "
                f"Review uncovered bins and add directed tests."
            )
        
        if not m.goal_met:
            recommendations.append(
                "Some covergroups have not met their coverage goals. "
                "Review individual covergroup reports and add targeted tests."
            )
        
        return recommendations
    
    def generate_improvements(self) -> List[Improvement]:
        """Generate actionable improvements for functional coverage"""
        if not self.metrics:
            return []
        
        improvements = []
        m = self.metrics
        
        # Covergroup improvement
        if m.covergroup_coverage < self.config.min_covergroup_coverage:
            impact = (self.config.min_covergroup_coverage - m.covergroup_coverage) / 100.0 * 0.40 * self.config.weight
            improvements.append(Improvement(
                component=ComponentType.FUNCTIONAL_COVERAGE,
                priority="high" if impact > 0.05 else "medium",
                current_value=m.covergroup_coverage,
                target_value=self.config.min_covergroup_coverage,
                impact=impact,
                actions=[
                    "Review covergroup reports to identify uncovered bins",
                    "Add directed tests for uncovered scenarios",
                    "Use constrained random testing to hit corner cases",
                    "Increase test iterations to improve coverage",
                ]
            ))
        
        # Cross coverage improvement
        if m.cross_coverage < self.config.min_cross_coverage:
            impact = (self.config.min_cross_coverage - m.cross_coverage) / 100.0 * 0.20 * self.config.weight
            improvements.append(Improvement(
                component=ComponentType.FUNCTIONAL_COVERAGE,
                priority="medium",
                current_value=m.cross_coverage,
                target_value=self.config.min_cross_coverage,
                impact=impact,
                actions=[
                    "Analyze cross coverage bins to find uncovered combinations",
                    "Add tests that exercise multiple coverpoint dimensions",
                    "Use cross-product constraints in random testing",
                ]
            ))
        
        improvements.sort(key=lambda x: x.impact, reverse=True)
        return improvements


# =============================================================================
# CONVENIENCE FUNCTIONS
# =============================================================================

def score_functional_coverage(
    ucdb_path: Optional[Path] = None,
    report_path: Optional[Path] = None,
    weight: float = 0.25
) -> ComponentScore:
    """
    Convenience function to score functional coverage
    
    Args:
        ucdb_path: Path to .ucdb file
        report_path: Path to text report
        weight: Weight for this component
    
    Returns:
        ComponentScore for functional coverage
    """
    config = FunctionalCoverageScoringConfig(weight=weight)
    scorer = FunctionalCoverageScorer(config=config)
    return scorer.score(ucdb_path, report_path)
