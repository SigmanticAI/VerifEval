"""
Coverage metrics calculator

Calculates aggregated coverage metrics from parsed coverage data.

This module takes raw coverage data (ModuleCoverage objects) and calculates:
- Line coverage percentages
- Branch coverage percentages  
- Toggle coverage percentages
- FSM coverage percentages
- Weighted overall scores
- Uncovered hotspots

Author: TB Eval Team
Version: 0.1.0
"""

from typing import List, Dict, Optional, Tuple, Set
from dataclasses import dataclass, field
from pathlib import Path
import logging

from ..models import (
    ModuleCoverage,
    FileCoverage,
    LineCoverageData,
    BranchData,
    ToggleData,
    StructuralCoverageMetrics,
    LineCoverageMetrics,
    BranchCoverageMetrics,
    ToggleCoverageMetrics,
    FSMCoverageMetrics,
)
from ..config import CoverageWeights, CoverageThresholds


# =============================================================================
# HOTSPOT IDENTIFICATION
# =============================================================================

@dataclass
class UncoveredRegion:
    """
    Represents a region of uncovered code
    
    Attributes:
        file_path: Source file path
        start_line: First uncovered line
        end_line: Last uncovered line
        line_count: Number of uncovered lines
        priority: Priority level (high/medium/low)
        context: Surrounding code context
    """
    file_path: str
    start_line: int
    end_line: int
    line_count: int
    priority: str = "medium"
    context: Optional[str] = None
    
    @property
    def is_critical(self) -> bool:
        """Check if this is a critical hotspot"""
        return self.priority == "high" or self.line_count > 10
    
    def to_dict(self) -> Dict[str, any]:
        """Convert to dictionary"""
        return {
            "file": self.file_path,
            "start_line": self.start_line,
            "end_line": self.end_line,
            "line_count": self.line_count,
            "priority": self.priority,
            "is_critical": self.is_critical,
        }


# =============================================================================
# METRICS CALCULATOR
# =============================================================================

class CoverageCalculator:
    """
    Calculate coverage metrics from parsed coverage data
    
    Takes ModuleCoverage objects from parsers and calculates aggregated
    StructuralCoverageMetrics suitable for Step 7 scoring.
    
    Usage:
        >>> calculator = CoverageCalculator()
        >>> module_coverage = parser.parse_file(coverage_file).coverage
        >>> metrics = calculator.calculate_metrics(module_coverage)
        >>> print(f"Line coverage: {metrics.line.percentage:.1f}%")
    """
    
    def __init__(
        self,
        weights: Optional[CoverageWeights] = None,
        thresholds: Optional[CoverageThresholds] = None
    ):
        """
        Initialize calculator
        
        Args:
            weights: Coverage weights for scoring (optional)
            thresholds: Coverage thresholds for validation (optional)
        """
        self.weights = weights or CoverageWeights()
        self.thresholds = thresholds or CoverageThresholds()
        self.logger = logging.getLogger(__name__)
    
    # =========================================================================
    # MAIN CALCULATION METHODS
    # =========================================================================
    
    def calculate_metrics(
        self,
        module_coverage: ModuleCoverage,
        identify_hotspots: bool = True,
        max_hotspots: int = 20
    ) -> StructuralCoverageMetrics:
        """
        Calculate complete structural coverage metrics
        
        Args:
            module_coverage: Parsed coverage data
            identify_hotspots: Whether to identify uncovered hotspots
            max_hotspots: Maximum hotspots to identify
        
        Returns:
            StructuralCoverageMetrics with all calculated metrics
        """
        metrics = StructuralCoverageMetrics()
        
        # Calculate line coverage
        metrics.line = self.calculate_line_coverage(module_coverage)
        
        # Calculate branch coverage
        metrics.branch = self.calculate_branch_coverage(module_coverage)
        
        # Calculate toggle coverage
        metrics.toggle = self.calculate_toggle_coverage(module_coverage)
        
        # Calculate FSM coverage (placeholder for Phase 2)
        metrics.fsm = self.calculate_fsm_coverage(module_coverage)
        
        # Calculate weighted overall score
        metrics.calculate_weighted_score(self.weights.to_dict())
        
        # Identify uncovered hotspots
        if identify_hotspots:
            hotspots = self.identify_hotspots(
                module_coverage,
                max_hotspots=max_hotspots
            )
            metrics.uncovered_hotspots = [h.to_dict() for h in hotspots]
        
        return metrics
    
    def calculate_line_coverage(
        self,
        module_coverage: ModuleCoverage
    ) -> LineCoverageMetrics:
        """
        Calculate line coverage metrics
        
        Args:
            module_coverage: Parsed coverage data
        
        Returns:
            LineCoverageMetrics with calculated values
        """
        metrics = LineCoverageMetrics()
        
        uncovered_lines = []
        
        for file_path, file_cov in module_coverage.files.items():
            # Count lines
            metrics.total_lines += len(file_cov.lines)
            
            for line_num, line_data in file_cov.lines.items():
                if line_data.is_covered:
                    metrics.covered_lines += 1
                else:
                    # Record uncovered line
                    uncovered_lines.append({
                        "file": file_path,
                        "line": line_num,
                        "code": line_data.source_line,
                    })
        
        # Calculate percentage
        metrics.calculate()
        
        # Store uncovered lines (limited)
        metrics.uncovered_lines = uncovered_lines[:100]  # Limit output size
        
        return metrics
    
    def calculate_branch_coverage(
        self,
        module_coverage: ModuleCoverage
    ) -> BranchCoverageMetrics:
        """
        Calculate branch coverage metrics
        
        Args:
            module_coverage: Parsed coverage data
        
        Returns:
            BranchCoverageMetrics with calculated values
        """
        metrics = BranchCoverageMetrics()
        
        uncovered_branches = []
        
        for file_path, file_cov in module_coverage.files.items():
            for branch in file_cov.branches:
                metrics.total_branches += 1
                
                if branch.is_fully_covered:
                    metrics.covered_branches += 1
                elif branch.is_partially_covered:
                    metrics.partially_covered += 1
                else:
                    # Uncovered branch
                    uncovered_branches.append({
                        "file": file_path,
                        "line": branch.line_number,
                        "block": branch.block_number,
                        "branch": branch.branch_number,
                    })
        
        # Calculate percentage
        metrics.calculate()
        
        # Store uncovered branches (limited)
        metrics.uncovered_branches = uncovered_branches[:100]
        
        return metrics
    
    def calculate_toggle_coverage(
        self,
        module_coverage: ModuleCoverage
    ) -> ToggleCoverageMetrics:
        """
        Calculate toggle coverage metrics
        
        Args:
            module_coverage: Parsed coverage data
        
        Returns:
            ToggleCoverageMetrics with calculated values
        """
        metrics = ToggleCoverageMetrics()
        
        untoggled_signals = []
        
        for signal_name, toggle_data in module_coverage.toggles.items():
            metrics.total_signals += 1
            
            fully_toggled = toggle_data.fully_toggled_bits
            bit_width = toggle_data.bit_width
            
            if fully_toggled == bit_width:
                # All bits fully toggled
                metrics.fully_toggled_signals += 1
            elif fully_toggled > 0:
                # Some bits toggled
                metrics.partially_toggled += 1
            else:
                # No bits toggled
                untoggled_signals.append(signal_name)
        
        # Calculate percentage
        metrics.calculate()
        
        # Store untoggled signals (limited)
        metrics.untoggled_signals = untoggled_signals[:50]
        
        return metrics
    
    def calculate_fsm_coverage(
        self,
        module_coverage: ModuleCoverage
    ) -> FSMCoverageMetrics:
        """
        Calculate FSM coverage metrics (Phase 2 - placeholder)
        
        Args:
            module_coverage: Parsed coverage data
        
        Returns:
            FSMCoverageMetrics (defaults to 100% if no FSMs)
        """
        metrics = FSMCoverageMetrics()
        
        # Phase 2: Parse FSM coverage data
        # For now, default to 100% (no FSMs detected)
        
        metrics.calculate()
        
        return metrics
    
    # =========================================================================
    # AGGREGATION METHODS
    # =========================================================================
    
    def calculate_metrics_for_multiple_modules(
        self,
        modules: List[ModuleCoverage]
    ) -> StructuralCoverageMetrics:
        """
        Calculate aggregated metrics across multiple modules
        
        Args:
            modules: List of ModuleCoverage objects
        
        Returns:
            Aggregated StructuralCoverageMetrics
        """
        if not modules:
            return StructuralCoverageMetrics()
        
        # Merge all modules into one
        merged = modules[0]
        for module in modules[1:]:
            merged.merge(module)
        
        # Calculate metrics on merged module
        return self.calculate_metrics(merged)
    
    def calculate_per_file_metrics(
        self,
        module_coverage: ModuleCoverage
    ) -> Dict[str, Dict[str, float]]:
        """
        Calculate metrics for each file individually
        
        Args:
            module_coverage: Parsed coverage data
        
        Returns:
            Dictionary mapping file path to metrics dict
        """
        per_file = {}
        
        for file_path, file_cov in module_coverage.files.items():
            per_file[file_path] = {
                "line_coverage": file_cov.line_coverage_percent,
                "branch_coverage": file_cov.branch_coverage_percent,
                "lines_total": file_cov.total_lines,
                "lines_covered": file_cov.covered_lines,
                "branches_total": file_cov.total_branches,
                "branches_covered": file_cov.covered_branches,
            }
        
        return per_file
    
    # =========================================================================
    # HOTSPOT IDENTIFICATION
    # =========================================================================
    
    def identify_hotspots(
        self,
        module_coverage: ModuleCoverage,
        max_hotspots: int = 20,
        min_region_size: int = 3
    ) -> List[UncoveredRegion]:
        """
        Identify uncovered code hotspots (regions of consecutive uncovered lines)
        
        Args:
            module_coverage: Parsed coverage data
            max_hotspots: Maximum hotspots to return
            min_region_size: Minimum consecutive lines to consider a hotspot
        
        Returns:
            List of UncoveredRegion objects, sorted by priority
        """
        hotspots = []
        
        for file_path, file_cov in module_coverage.files.items():
            # Get sorted line numbers
            line_numbers = sorted(file_cov.lines.keys())
            
            # Find consecutive uncovered regions
            current_region_start = None
            current_region_lines = []
            
            for line_num in line_numbers:
                line_data = file_cov.lines[line_num]
                
                if not line_data.is_covered:
                    # Uncovered line
                    if current_region_start is None:
                        # Start new region
                        current_region_start = line_num
                        current_region_lines = [line_num]
                    else:
                        # Check if consecutive
                        if line_num == current_region_lines[-1] + 1:
                            # Continue region
                            current_region_lines.append(line_num)
                        else:
                            # Gap - finalize previous region
                            if len(current_region_lines) >= min_region_size:
                                hotspot = self._create_hotspot(
                                    file_path,
                                    current_region_start,
                                    current_region_lines[-1],
                                    len(current_region_lines)
                                )
                                hotspots.append(hotspot)
                            
                            # Start new region
                            current_region_start = line_num
                            current_region_lines = [line_num]
                else:
                    # Covered line - finalize region if exists
                    if current_region_start is not None:
                        if len(current_region_lines) >= min_region_size:
                            hotspot = self._create_hotspot(
                                file_path,
                                current_region_start,
                                current_region_lines[-1],
                                len(current_region_lines)
                            )
                            hotspots.append(hotspot)
                        
                        current_region_start = None
                        current_region_lines = []
            
            # Finalize last region if exists
            if current_region_start is not None and len(current_region_lines) >= min_region_size:
                hotspot = self._create_hotspot(
                    file_path,
                    current_region_start,
                    current_region_lines[-1],
                    len(current_region_lines)
                )
                hotspots.append(hotspot)
        
        # Sort by priority and size
        hotspots.sort(key=lambda h: (
            0 if h.priority == "high" else (1 if h.priority == "medium" else 2),
            -h.line_count  # Larger regions first
        ))
        
        return hotspots[:max_hotspots]
    
    def _create_hotspot(
        self,
        file_path: str,
        start_line: int,
        end_line: int,
        line_count: int
    ) -> UncoveredRegion:
        """Create an UncoveredRegion with priority assessment"""
        
        # Assess priority based on size
        if line_count >= 10:
            priority = "high"
        elif line_count >= 5:
            priority = "medium"
        else:
            priority = "low"
        
        # Additional heuristics (can be enhanced)
        # - Check file path for critical modules
        # - Check function names
        # - Check complexity metrics
        
        return UncoveredRegion(
            file_path=file_path,
            start_line=start_line,
            end_line=end_line,
            line_count=line_count,
            priority=priority
        )
    
    # =========================================================================
    # VALIDATION METHODS
    # =========================================================================
    
    def validate_metrics(
        self,
        metrics: StructuralCoverageMetrics
    ) -> Tuple[bool, List[str]]:
        """
        Validate metrics against thresholds
        
        Args:
            metrics: Calculated metrics
        
        Returns:
            Tuple of (all_passed, violations)
        """
        violations = []
        
        # Check line coverage
        if metrics.line.percentage < self.thresholds.line:
            violations.append(
                f"Line coverage {metrics.line.percentage:.1f}% "
                f"below threshold {self.thresholds.line}%"
            )
        
        # Check branch coverage
        if metrics.branch.percentage < self.thresholds.branch:
            violations.append(
                f"Branch coverage {metrics.branch.percentage:.1f}% "
                f"below threshold {self.thresholds.branch}%"
            )
        
        # Check toggle coverage
        if metrics.toggle.percentage < self.thresholds.toggle:
            violations.append(
                f"Toggle coverage {metrics.toggle.percentage:.1f}% "
                f"below threshold {self.thresholds.toggle}%"
            )
        
        # Check FSM coverage
        if metrics.fsm.percentage < self.thresholds.fsm:
            violations.append(
                f"FSM coverage {metrics.fsm.percentage:.1f}% "
                f"below threshold {self.thresholds.fsm}%"
            )
        
        # Check overall coverage
        overall_pct = metrics.weighted_score * 100.0
        if overall_pct < self.thresholds.overall:
            violations.append(
                f"Overall coverage {overall_pct:.1f}% "
                f"below threshold {self.thresholds.overall}%"
            )
        
        return len(violations) == 0, violations
    
    # =========================================================================
    # COMPARISON METHODS
    # =========================================================================
    
    def compare_metrics(
        self,
        before: StructuralCoverageMetrics,
        after: StructuralCoverageMetrics
    ) -> Dict[str, float]:
        """
        Compare two sets of metrics (e.g., before/after changes)
        
        Args:
            before: Baseline metrics
            after: Updated metrics
        
        Returns:
            Dictionary with deltas for each metric
        """
        return {
            "line_delta": after.line.percentage - before.line.percentage,
            "branch_delta": after.branch.percentage - before.branch.percentage,
            "toggle_delta": after.toggle.percentage - before.toggle.percentage,
            "fsm_delta": after.fsm.percentage - before.fsm.percentage,
            "overall_delta": (after.weighted_score - before.weighted_score) * 100.0,
        }
    
    def calculate_improvement(
        self,
        before: StructuralCoverageMetrics,
        after: StructuralCoverageMetrics
    ) -> Dict[str, any]:
        """
        Calculate improvement metrics
        
        Args:
            before: Baseline metrics
            after: Updated metrics
        
        Returns:
            Dictionary with improvement analysis
        """
        deltas = self.compare_metrics(before, after)
        
        return {
            "deltas": deltas,
            "improved": any(d > 0 for d in deltas.values()),
            "regressed": any(d < 0 for d in deltas.values()),
            "total_improvement": sum(deltas.values()),
            "details": {
                "line_improved": deltas["line_delta"] > 0,
                "branch_improved": deltas["branch_delta"] > 0,
                "toggle_improved": deltas["toggle_delta"] > 0,
                "overall_improved": deltas["overall_delta"] > 0,
            }
        }
    
    # =========================================================================
    # UTILITY METHODS
    # =========================================================================
    
    def calculate_coverage_gaps(
        self,
        module_coverage: ModuleCoverage
    ) -> Dict[str, List[str]]:
        """
        Identify coverage gaps by category
        
        Args:
            module_coverage: Parsed coverage data
        
        Returns:
            Dictionary categorizing coverage gaps
        """
        gaps = {
            "uncovered_files": [],
            "partially_covered_files": [],
            "files_without_branches": [],
            "files_without_toggles": [],
        }
        
        for file_path, file_cov in module_coverage.files.items():
            coverage_pct = file_cov.line_coverage_percent
            
            if coverage_pct == 0:
                gaps["uncovered_files"].append(file_path)
            elif coverage_pct < 50:
                gaps["partially_covered_files"].append(file_path)
            
            if not file_cov.branches:
                gaps["files_without_branches"].append(file_path)
        
        # Check for files without toggle coverage
        files_with_toggles = set(module_coverage.source_files)
        files_with_data = set(module_coverage.files.keys())
        
        # This is a simplified check - real implementation would be more sophisticated
        
        return gaps
    
    def get_coverage_summary(
        self,
        metrics: StructuralCoverageMetrics
    ) -> str:
        """
        Generate human-readable coverage summary
        
        Args:
            metrics: Calculated metrics
        
        Returns:
            Formatted summary string
        """
        lines = [
            "Coverage Summary:",
            f"  Line:    {metrics.line.percentage:6.2f}% ({metrics.line.covered_lines}/{metrics.line.total_lines})",
            f"  Branch:  {metrics.branch.percentage:6.2f}% ({metrics.branch.covered_branches}/{metrics.branch.total_branches})",
            f"  Toggle:  {metrics.toggle.percentage:6.2f}% ({metrics.toggle.fully_toggled_signals}/{metrics.toggle.total_signals})",
            f"  FSM:     {metrics.fsm.percentage:6.2f}%",
            f"  Overall: {metrics.weighted_score * 100.0:6.2f}% (weighted)",
        ]
        
        return "\n".join(lines)


# =============================================================================
# CONVENIENCE FUNCTIONS
# =============================================================================

def calculate_coverage(
    module_coverage: ModuleCoverage,
    weights: Optional[CoverageWeights] = None,
    thresholds: Optional[CoverageThresholds] = None
) -> StructuralCoverageMetrics:
    """
    Convenience function to calculate coverage metrics
    
    Args:
        module_coverage: Parsed coverage data
        weights: Coverage weights (optional)
        thresholds: Coverage thresholds (optional)
    
    Returns:
        StructuralCoverageMetrics
    """
    calculator = CoverageCalculator(weights, thresholds)
    return calculator.calculate_metrics(module_coverage)


def quick_summary(module_coverage: ModuleCoverage) -> str:
    """
    Quick coverage summary string
    
    Args:
        module_coverage: Parsed coverage data
    
    Returns:
        Summary string
    """
    calculator = CoverageCalculator()
    metrics = calculator.calculate_metrics(module_coverage)
    return calculator.get_coverage_summary(metrics)
