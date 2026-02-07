"""
Coverage merger with advanced per-test tracking

Merges coverage from multiple test runs while tracking:
- Unique coverage contributions per test (Q13)
- Overlapping coverage between tests
- Test efficiency and redundancy
- Optimal test execution order
- Differential coverage progression

This enables hierarchical coverage analysis (Q4.1) with detailed
per-test breakdowns for test suite optimization.

Author: TB Eval Team
Version: 0.1.0
"""

from typing import List, Dict, Optional, Set, Tuple
from dataclasses import dataclass, field
from pathlib import Path
import logging

from ..models import (
    ModuleCoverage,
    FileCoverage,
    LineCoverageData,
    BranchData,
    StructuralCoverageMetrics,
    PerTestCoverage,
    HierarchicalCoverage,
)
from .calculator import CoverageCalculator


# =============================================================================
# MERGE TRACKING
# =============================================================================

@dataclass
class MergeStatistics:
    """
    Statistics about a merge operation
    
    Attributes:
        total_tests: Total number of tests merged
        total_lines: Total unique lines across all tests
        total_branches: Total unique branches
        merge_time_ms: Time taken to merge (milliseconds)
        overlap_percentage: Average overlap between tests
    """
    total_tests: int = 0
    total_lines: int = 0
    total_branches: int = 0
    merge_time_ms: float = 0.0
    overlap_percentage: float = 0.0
    
    def to_dict(self) -> Dict[str, any]:
        """Convert to dictionary"""
        return {
            "total_tests": self.total_tests,
            "total_lines": self.total_lines,
            "total_branches": self.total_branches,
            "merge_time_ms": self.merge_time_ms,
            "overlap_percentage": round(self.overlap_percentage, 2),
        }


# =============================================================================
# COVERAGE MERGER
# =============================================================================

class CoverageMerger:
    """
    Merge coverage from multiple test runs with advanced tracking
    
    This class implements Q13 advanced tracking by maintaining detailed
    information about each test's contribution to overall coverage.
    
    Features:
    - Unique coverage identification per test
    - Redundancy detection
    - Efficiency scoring
    - Optimal test ordering
    - Differential coverage tracking
    
    Usage:
        >>> merger = CoverageMerger()
        >>> hierarchical = merger.merge_with_tracking(test_coverages, test_durations)
        >>> print(f"Essential tests: {hierarchical.essential_tests}")
        >>> print(f"Redundant tests: {hierarchical.redundant_tests}")
    """
    
    def __init__(self, calculator: Optional[CoverageCalculator] = None):
        """
        Initialize merger
        
        Args:
            calculator: CoverageCalculator for metrics (optional)
        """
        self.calculator = calculator or CoverageCalculator()
        self.logger = logging.getLogger(__name__)
    
    # =========================================================================
    # SIMPLE MERGING (Q6.1, Q6.2)
    # =========================================================================
    
    def merge_simple(
        self,
        coverages: List[ModuleCoverage]
    ) -> ModuleCoverage:
        """
        Simple merge without per-test tracking
        
        Just sums hit counts across all tests.
        
        Args:
            coverages: List of ModuleCoverage objects to merge
        
        Returns:
            Merged ModuleCoverage
        """
        if not coverages:
            return ModuleCoverage(module_name="empty")
        
        # Start with first coverage
        merged = ModuleCoverage(
            module_name=coverages[0].module_name or "merged",
            source_files=coverages[0].source_files.copy()
        )
        
        # Copy first coverage's data
        for file_path, file_cov in coverages[0].files.items():
            merged.files[file_path] = FileCoverage(file_path=file_path)
            for line_num, line_data in file_cov.lines.items():
                merged.files[file_path].lines[line_num] = LineCoverageData(
                    line_number=line_num,
                    hit_count=line_data.hit_count
                )
            for branch in file_cov.branches:
                merged.files[file_path].branches.append(BranchData(
                    line_number=branch.line_number,
                    block_number=branch.block_number,
                    branch_number=branch.branch_number,
                    taken_count=branch.taken_count,
                    not_taken_count=branch.not_taken_count
                ))
        
        # Copy toggle data
        for signal_name, toggle_data in coverages[0].toggles.items():
            merged.toggles[signal_name] = toggle_data
        
        # Merge remaining coverages
        for coverage in coverages[1:]:
            merged.merge(coverage)
        
        return merged
    
    # =========================================================================
    # ADVANCED MERGING (Q13 - with tracking)
    # =========================================================================
    
    def merge_with_tracking(
        self,
        test_coverages: Dict[str, ModuleCoverage],
        test_durations: Optional[Dict[str, float]] = None,
        essential_threshold: float = 5.0,
        redundant_threshold: float = 1.0
    ) -> HierarchicalCoverage:
        """
        Merge coverage with full per-test tracking (Q13)
        
        Tracks:
        - Unique lines covered by each test
        - Overlapping coverage between tests
        - Test efficiency (unique coverage per second)
        - Redundancy scores
        
        Args:
            test_coverages: Dictionary mapping test name to ModuleCoverage
            test_durations: Dictionary mapping test name to duration in ms (optional)
            essential_threshold: Minimum % unique coverage for essential tests
            redundant_threshold: Maximum % unique coverage for redundant tests
        
        Returns:
            HierarchicalCoverage with detailed per-test breakdown
        """
        import time
        start_time = time.time()
        
        hierarchical = HierarchicalCoverage()
        
        if not test_coverages:
            return hierarchical
        
        # Initialize test durations if not provided
        if test_durations is None:
            test_durations = {name: 1000.0 for name in test_coverages.keys()}
        
        # Step 1: Merge all coverage to get baseline
        all_coverages = list(test_coverages.values())
        merged_module = self.merge_simple(all_coverages)
        
        # Calculate merged metrics
        hierarchical.merged = self.calculator.calculate_metrics(merged_module)
        
        # Step 2: Build line and branch tracking
        # Track which tests cover which lines/branches
        line_coverage_map = self._build_line_coverage_map(test_coverages)
        branch_coverage_map = self._build_branch_coverage_map(test_coverages)
        
        # Step 3: Calculate per-test metrics
        hierarchical.per_test = self._calculate_per_test_coverage(
            test_coverages,
            test_durations,
            line_coverage_map,
            branch_coverage_map
        )
        
        # Step 4: Calculate differential coverage
        hierarchical.differential = self._calculate_differential_coverage(
            hierarchical.per_test,
            line_coverage_map
        )
        
        # Step 5: Calculate optimal test order
        hierarchical.optimal_test_order = self._calculate_optimal_order(
            hierarchical.per_test,
            line_coverage_map
        )
        
        # Step 6: Identify test value
        hierarchical.identify_test_value(essential_threshold, redundant_threshold)
        
        self.logger.info(
            f"Merged {len(test_coverages)} tests in {(time.time() - start_time) * 1000:.1f}ms"
        )
        
        return hierarchical
    
    def _build_line_coverage_map(
        self,
        test_coverages: Dict[str, ModuleCoverage]
    ) -> Dict[Tuple[str, int], Set[str]]:
        """
        Build map of (file, line) -> set of tests that cover it
        
        Args:
            test_coverages: Dictionary of test coverages
        
        Returns:
            Dictionary mapping (file_path, line_number) to set of test names
        """
        coverage_map: Dict[Tuple[str, int], Set[str]] = {}
        
        for test_name, module_cov in test_coverages.items():
            for file_path, file_cov in module_cov.files.items():
                for line_num, line_data in file_cov.lines.items():
                    if line_data.is_covered:
                        key = (file_path, line_num)
                        if key not in coverage_map:
                            coverage_map[key] = set()
                        coverage_map[key].add(test_name)
        
        return coverage_map
    
    def _build_branch_coverage_map(
        self,
        test_coverages: Dict[str, ModuleCoverage]
    ) -> Dict[Tuple[str, int, int, int], Set[str]]:
        """
        Build map of (file, line, block, branch) -> set of tests that cover it
        
        Args:
            test_coverages: Dictionary of test coverages
        
        Returns:
            Dictionary mapping branch ID to set of test names
        """
        coverage_map: Dict[Tuple[str, int, int, int], Set[str]] = {}
        
        for test_name, module_cov in test_coverages.items():
            for file_path, file_cov in module_cov.files.items():
                for branch in file_cov.branches:
                    if branch.taken_count > 0:
                        key = (file_path, branch.line_number, 
                               branch.block_number, branch.branch_number)
                        if key not in coverage_map:
                            coverage_map[key] = set()
                        coverage_map[key].add(test_name)
        
        return coverage_map
    
    def _calculate_per_test_coverage(
        self,
        test_coverages: Dict[str, ModuleCoverage],
        test_durations: Dict[str, float],
        line_coverage_map: Dict[Tuple[str, int], Set[str]],
        branch_coverage_map: Dict[Tuple[str, int, int, int], Set[str]]
    ) -> List[PerTestCoverage]:
        """
        Calculate detailed per-test coverage with unique contributions
        
        Args:
            test_coverages: Dictionary of test coverages
            test_durations: Dictionary of test durations
            line_coverage_map: Map of lines to covering tests
            branch_coverage_map: Map of branches to covering tests
        
        Returns:
            List of PerTestCoverage objects
        """
        per_test_list = []
        
        # Get total unique lines for percentage calculation
        total_unique_lines = len(line_coverage_map)
        
        for test_name, module_cov in test_coverages.items():
            # Calculate standalone coverage for this test
            standalone_metrics = self.calculator.calculate_metrics(module_cov)
            
            # Identify unique vs overlapping lines
            unique_lines: Set[int] = set()
            overlapping_lines: Set[int] = set()
            
            for file_path, file_cov in module_cov.files.items():
                for line_num, line_data in file_cov.lines.items():
                    if line_data.is_covered:
                        key = (file_path, line_num)
                        covering_tests = line_coverage_map.get(key, set())
                        
                        if len(covering_tests) == 1:
                            # Only this test covers this line
                            unique_lines.add(line_num)
                        else:
                            # Other tests also cover this line
                            overlapping_lines.add(line_num)
            
            # Identify unique branches
            unique_branches: Set[Tuple[int, int, int]] = set()
            
            for file_path, file_cov in module_cov.files.items():
                for branch in file_cov.branches:
                    if branch.taken_count > 0:
                        key = (file_path, branch.line_number,
                               branch.block_number, branch.branch_number)
                        covering_tests = branch_coverage_map.get(key, set())
                        
                        if len(covering_tests) == 1:
                            unique_branches.add((branch.line_number,
                                               branch.block_number,
                                               branch.branch_number))
            
            # Create PerTestCoverage
            per_test = PerTestCoverage(
                test_name=test_name,
                test_full_name=f"test_{test_name}",
                test_duration_ms=test_durations.get(test_name, 0.0),
                coverage_standalone=standalone_metrics,
                unique_lines=unique_lines,
                unique_branches=unique_branches,
                overlapping_lines=overlapping_lines
            )
            
            # Calculate derived metrics
            per_test.calculate_metrics(total_unique_lines)
            
            per_test_list.append(per_test)
        
        return per_test_list
    
    def _calculate_differential_coverage(
        self,
        per_test_list: List[PerTestCoverage],
        line_coverage_map: Dict[Tuple[str, int], Set[str]]
    ) -> Dict[str, float]:
        """
        Calculate differential coverage (Q4.1)
        
        Shows cumulative coverage as tests are added in order.
        
        Args:
            per_test_list: List of per-test coverage
            line_coverage_map: Map of lines to covering tests
        
        Returns:
            Dictionary mapping test name to cumulative coverage percentage
        """
        differential = {}
        cumulative_lines: Set[Tuple[str, int]] = set()
        total_lines = len(line_coverage_map)
        
        for per_test in per_test_list:
            # Add this test's lines to cumulative set
            for line in per_test.unique_lines:
                # Find the file for this line (simplified - assumes single file)
                for key in line_coverage_map.keys():
                    if key[1] == line:
                        cumulative_lines.add(key)
                        break
            
            for line in per_test.overlapping_lines:
                # Find the file for this line
                for key in line_coverage_map.keys():
                    if key[1] == line:
                        cumulative_lines.add(key)
                        break
            
            # Calculate cumulative percentage
            cumulative_pct = (len(cumulative_lines) / total_lines * 100.0) if total_lines > 0 else 0.0
            differential[per_test.test_name] = cumulative_pct
        
        return differential
    
    def _calculate_optimal_order(
        self,
        per_test_list: List[PerTestCoverage],
        line_coverage_map: Dict[Tuple[str, int], Set[str]]
    ) -> List[str]:
        """
        Calculate optimal test execution order using greedy algorithm
        
        Greedy strategy: At each step, pick the test that adds the most
        new coverage to what's already covered.
        
        Args:
            per_test_list: List of per-test coverage
            line_coverage_map: Map of lines to covering tests
        
        Returns:
            List of test names in optimal order
        """
        # Build map of test to lines it covers
        test_to_lines: Dict[str, Set[Tuple[str, int]]] = {}
        
        for per_test in per_test_list:
            test_lines = set()
            
            # Add unique and overlapping lines
            for line in per_test.unique_lines:
                for key in line_coverage_map.keys():
                    if key[1] == line:
                        test_lines.add(key)
            
            for line in per_test.overlapping_lines:
                for key in line_coverage_map.keys():
                    if key[1] == line:
                        test_lines.add(key)
            
            test_to_lines[per_test.test_name] = test_lines
        
        # Greedy algorithm
        optimal_order = []
        covered_lines: Set[Tuple[str, int]] = set()
        remaining_tests = set(test_to_lines.keys())
        
        while remaining_tests:
            # Find test that adds most new coverage
            best_test = None
            best_new_coverage = 0
            
            for test_name in remaining_tests:
                test_lines = test_to_lines[test_name]
                new_lines = test_lines - covered_lines
                
                if len(new_lines) > best_new_coverage:
                    best_new_coverage = len(new_lines)
                    best_test = test_name
            
            if best_test is None:
                # No more coverage to add, pick any remaining test
                best_test = remaining_tests.pop()
                optimal_order.append(best_test)
                break
            
            # Add best test to order
            optimal_order.append(best_test)
            covered_lines.update(test_to_lines[best_test])
            remaining_tests.remove(best_test)
        
        return optimal_order
    
    # =========================================================================
    # ANALYSIS METHODS
    # =========================================================================
    
    def analyze_test_redundancy(
        self,
        hierarchical: HierarchicalCoverage
    ) -> Dict[str, any]:
        """
        Analyze test redundancy in the suite
        
        Args:
            hierarchical: HierarchicalCoverage with per-test data
        
        Returns:
            Dictionary with redundancy analysis
        """
        total_tests = len(hierarchical.per_test)
        essential_count = len(hierarchical.essential_tests)
        redundant_count = len(hierarchical.redundant_tests)
        
        # Calculate average redundancy
        avg_redundancy = sum(t.redundancy_score for t in hierarchical.per_test) / total_tests if total_tests > 0 else 0
        
        # Calculate average unique contribution
        avg_unique = sum(t.unique_contribution_percent for t in hierarchical.per_test) / total_tests if total_tests > 0 else 0
        
        return {
            "total_tests": total_tests,
            "essential_tests": essential_count,
            "redundant_tests": redundant_count,
            "average_redundancy_score": round(avg_redundancy, 3),
            "average_unique_contribution": round(avg_unique, 2),
            "optimization_potential": redundant_count > 0,
            "recommended_action": self._get_redundancy_recommendation(
                redundant_count, total_tests
            )
        }
    
    def _get_redundancy_recommendation(
        self,
        redundant_count: int,
        total_tests: int
    ) -> str:
        """Get recommendation based on redundancy analysis"""
        if redundant_count == 0:
            return "Test suite is efficient - no redundant tests"
        
        redundancy_ratio = redundant_count / total_tests
        
        if redundancy_ratio > 0.3:
            return f"High redundancy detected - consider removing {redundant_count} redundant tests"
        elif redundancy_ratio > 0.1:
            return f"Moderate redundancy - review {redundant_count} tests for potential removal"
        else:
            return f"Low redundancy - {redundant_count} tests could be optimized"
    
    def calculate_coverage_convergence(
        self,
        hierarchical: HierarchicalCoverage
    ) -> Dict[str, any]:
        """
        Calculate how quickly coverage converges
        
        Useful for determining when to stop adding tests.
        
        Args:
            hierarchical: HierarchicalCoverage with differential data
        
        Returns:
            Dictionary with convergence analysis
        """
        if not hierarchical.differential:
            return {}
        
        # Get coverage at different points
        test_names = list(hierarchical.differential.keys())
        coverages = [hierarchical.differential[name] for name in test_names]
        
        # Calculate convergence rate
        if len(coverages) >= 2:
            # Rate of change in coverage
            deltas = [coverages[i+1] - coverages[i] for i in range(len(coverages)-1)]
            
            # Find 90% coverage point
            target_coverage = hierarchical.merged.line.percentage * 0.9
            tests_to_90 = 0
            for i, cov in enumerate(coverages):
                if cov >= target_coverage:
                    tests_to_90 = i + 1
                    break
            
            return {
                "initial_coverage": round(coverages[0], 2),
                "final_coverage": round(coverages[-1], 2),
                "coverage_gain": round(coverages[-1] - coverages[0], 2),
                "average_delta": round(sum(deltas) / len(deltas), 2) if deltas else 0,
                "tests_to_90_percent": tests_to_90,
                "converged": deltas[-1] < 1.0 if deltas else False
            }
        
        return {}
    
    def suggest_test_removal(
        self,
        hierarchical: HierarchicalCoverage,
        coverage_threshold: float = 95.0
    ) -> List[str]:
        """
        Suggest tests that could be removed without losing coverage
        
        Args:
            hierarchical: HierarchicalCoverage with per-test data
            coverage_threshold: Minimum coverage to maintain (%)
        
        Returns:
            List of test names that could be removed
        """
        removable = []
        
        for test in hierarchical.redundant_tests:
            # Find the test object
            test_obj = None
            for pt in hierarchical.per_test:
                if pt.test_name == test:
                    test_obj = pt
                    break
            
            if test_obj and test_obj.unique_contribution_percent < 0.5:
                removable.append(test)
        
        return removable
    
    # =========================================================================
    # UTILITY METHODS
    # =========================================================================
    
    def get_merge_statistics(
        self,
        hierarchical: HierarchicalCoverage
    ) -> MergeStatistics:
        """
        Get statistics about the merge operation
        
        Args:
            hierarchical: HierarchicalCoverage result
        
        Returns:
            MergeStatistics
        """
        stats = MergeStatistics()
        
        stats.total_tests = len(hierarchical.per_test)
        stats.total_lines = hierarchical.merged.line.total_lines
        stats.total_branches = hierarchical.merged.branch.total_branches
        
        # Calculate average overlap
        if hierarchical.per_test:
            avg_overlap = sum(
                len(t.overlapping_lines) / (len(t.unique_lines) + len(t.overlapping_lines))
                if (len(t.unique_lines) + len(t.overlapping_lines)) > 0 else 0
                for t in hierarchical.per_test
            ) / len(hierarchical.per_test)
            
            stats.overlap_percentage = avg_overlap * 100.0
        
        return stats


# =============================================================================
# CONVENIENCE FUNCTIONS
# =============================================================================

def merge_coverage_simple(
    coverages: List[ModuleCoverage]
) -> ModuleCoverage:
    """
    Quick merge without tracking
    
    Args:
        coverages: List of ModuleCoverage objects
    
    Returns:
        Merged ModuleCoverage
    """
    merger = CoverageMerger()
    return merger.merge_simple(coverages)


def merge_coverage_with_tracking(
    test_coverages: Dict[str, ModuleCoverage],
    test_durations: Optional[Dict[str, float]] = None
) -> HierarchicalCoverage:
    """
    Merge with full per-test tracking
    
    Args:
        test_coverages: Dictionary mapping test name to coverage
        test_durations: Dictionary mapping test name to duration (optional)
    
    Returns:
        HierarchicalCoverage with detailed breakdown
    """
    merger = CoverageMerger()
    return merger.merge_with_tracking(test_coverages, test_durations)
