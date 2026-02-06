"""
Data models for Step 5: Coverage Analysis

This module contains all data structures for coverage processing:
- Low-level: Line, Branch, Toggle data (individual elements)
- Mid-level: File, Module coverage (aggregated by file/module)
- High-level: Structural metrics (overall coverage metrics)
- Analysis: Per-test, hierarchical coverage (differential analysis)
- Integration: Mutation testing data (for Step 6)
- Output: Coverage report (main export)

Author: TB Eval Team
Version: 0.1.0
"""

from dataclasses import dataclass, field, asdict
from enum import Enum
from typing import Dict, List, Set, Optional, Tuple, Any
from pathlib import Path
from datetime import datetime
import json


# =============================================================================
# ENUMS
# =============================================================================

class CoverageFormat(Enum):
    """Coverage file format"""
    VERILATOR_DAT = "verilator_dat"
    LCOV_INFO = "lcov_info"
    COVERED_CDD = "covered_cdd"
    COVERED_TXT = "covered_txt"
    QUESTA_UCDB = "questa_ucdb"
    VCS_VDB = "vcs_vdb"
    UNKNOWN = "unknown"


class CoverageGranularity(Enum):
    """Coverage data granularity"""
    PER_TEST = "per_test"           # Individual test coverage
    MERGED = "merged"               # Cumulative coverage
    HIERARCHICAL = "hierarchical"   # Both per-test + merged + differential


class CoverageType(Enum):
    """Coverage metric types"""
    LINE = "line"
    BRANCH = "branch"
    TOGGLE = "toggle"
    FSM_STATE = "fsm_state"
    FSM_TRANSITION = "fsm_transition"
    CONDITION = "condition"         # Phase 2
    EXPRESSION = "expression"       # Phase 2


# =============================================================================
# LOW-LEVEL COVERAGE ELEMENTS
# =============================================================================

@dataclass
class LineCoverageData:
    """
    Single line coverage data
    
    Attributes:
        line_number: Line number in source file
        hit_count: Number of times line was executed
        source_line: Actual source code (optional, for reports)
        covered_by_tests: Set of test names that cover this line (Q13 advanced)
    """
    line_number: int
    hit_count: int
    source_line: Optional[str] = None
    covered_by_tests: Set[str] = field(default_factory=set)
    
    @property
    def is_covered(self) -> bool:
        """Check if line is covered"""
        return self.hit_count > 0
    
    def merge(self, other: 'LineCoverageData') -> None:
        """Merge with another line's coverage data"""
        self.hit_count += other.hit_count
        self.covered_by_tests.update(other.covered_by_tests)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "line": self.line_number,
            "hits": self.hit_count,
            "covered": self.is_covered,
            "source": self.source_line,
            "covered_by": list(self.covered_by_tests) if self.covered_by_tests else None,
        }


@dataclass
class BranchData:
    """
    Single branch coverage data
    
    Attributes:
        line_number: Line number where branch occurs
        block_number: Block identifier
        branch_number: Branch identifier within block
        taken_count: Number of times branch was taken
        not_taken_count: Number of times branch was not taken
        covered_by_tests: Tests that cover this branch
    """
    line_number: int
    block_number: int
    branch_number: int
    taken_count: int
    not_taken_count: int = 0
    covered_by_tests: Set[str] = field(default_factory=set)
    
    @property
    def is_fully_covered(self) -> bool:
        """Check if both directions are covered"""
        return self.taken_count > 0 and self.not_taken_count > 0
    
    @property
    def is_partially_covered(self) -> bool:
        """Check if only one direction is covered"""
        return (self.taken_count > 0) != (self.not_taken_count > 0)
    
    @property
    def is_uncovered(self) -> bool:
        """Check if neither direction is covered"""
        return self.taken_count == 0 and self.not_taken_count == 0
    
    def merge(self, other: 'BranchData') -> None:
        """Merge with another branch's coverage data"""
        self.taken_count += other.taken_count
        self.not_taken_count += other.not_taken_count
        self.covered_by_tests.update(other.covered_by_tests)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "line": self.line_number,
            "block": self.block_number,
            "branch": self.branch_number,
            "taken": self.taken_count,
            "not_taken": self.not_taken_count,
            "fully_covered": self.is_fully_covered,
        }


@dataclass
class ToggleData:
    """
    Signal toggle coverage data
    
    Attributes:
        signal_name: Signal/wire/reg name
        bit_width: Number of bits in signal
        toggles_0to1: Bit index -> count of 0→1 transitions
        toggles_1to0: Bit index -> count of 1→0 transitions
    """
    signal_name: str
    bit_width: int
    toggles_0to1: Dict[int, int] = field(default_factory=dict)
    toggles_1to0: Dict[int, int] = field(default_factory=dict)
    
    @property
    def fully_toggled_bits(self) -> int:
        """Count bits that toggled in both directions"""
        count = 0
        for bit in range(self.bit_width):
            if (self.toggles_0to1.get(bit, 0) > 0 and 
                self.toggles_1to0.get(bit, 0) > 0):
                count += 1
        return count
    
    @property
    def toggle_coverage_percent(self) -> float:
        """Calculate toggle coverage percentage"""
        if self.bit_width == 0:
            return 0.0
        return (self.fully_toggled_bits / self.bit_width) * 100.0
    
    def merge(self, other: 'ToggleData') -> None:
        """Merge with another signal's toggle data"""
        for bit, count in other.toggles_0to1.items():
            self.toggles_0to1[bit] = self.toggles_0to1.get(bit, 0) + count
        for bit, count in other.toggles_1to0.items():
            self.toggles_1to0[bit] = self.toggles_1to0.get(bit, 0) + count
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.signal_name,
            "width": self.bit_width,
            "coverage": self.toggle_coverage_percent,
            "fully_toggled": self.fully_toggled_bits,
        }


# =============================================================================
# MID-LEVEL: FILE/MODULE AGGREGATION
# =============================================================================

@dataclass
class FileCoverage:
    """
    Coverage for a single source file
    
    Attributes:
        file_path: Path to source file
        lines: Line coverage data (line_number -> LineCoverageData)
        branches: Branch coverage data
    """
    file_path: str
    lines: Dict[int, LineCoverageData] = field(default_factory=dict)
    branches: List[BranchData] = field(default_factory=list)
    
    @property
    def total_lines(self) -> int:
        return len(self.lines)
    
    @property
    def covered_lines(self) -> int:
        return sum(1 for line in self.lines.values() if line.is_covered)
    
    @property
    def line_coverage_percent(self) -> float:
        if self.total_lines == 0:
            return 0.0
        return (self.covered_lines / self.total_lines) * 100.0
    
    @property
    def total_branches(self) -> int:
        return len(self.branches)
    
    @property
    def covered_branches(self) -> int:
        return sum(1 for b in self.branches if b.is_fully_covered)
    
    @property
    def branch_coverage_percent(self) -> float:
        if self.total_branches == 0:
            return 100.0  # No branches = 100% coverage
        return (self.covered_branches / self.total_branches) * 100.0
    
    @property
    def uncovered_lines(self) -> List[int]:
        """Get list of uncovered line numbers"""
        return sorted([num for num, line in self.lines.items() if not line.is_covered])
    
    def merge(self, other: 'FileCoverage') -> None:
        """Merge with another file's coverage data"""
        # Merge lines
        for line_num, line_data in other.lines.items():
            if line_num in self.lines:
                self.lines[line_num].merge(line_data)
            else:
                self.lines[line_num] = line_data
        
        # Merge branches (match by line/block/branch ID)
        for other_branch in other.branches:
            matching_branch = None
            for self_branch in self.branches:
                if (self_branch.line_number == other_branch.line_number and
                    self_branch.block_number == other_branch.block_number and
                    self_branch.branch_number == other_branch.branch_number):
                    matching_branch = self_branch
                    break
            
            if matching_branch:
                matching_branch.merge(other_branch)
            else:
                self.branches.append(other_branch)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "file": self.file_path,
            "lines": {
                "total": self.total_lines,
                "covered": self.covered_lines,
                "percentage": self.line_coverage_percent,
                "uncovered": self.uncovered_lines[:50],  # Limit output
            },
            "branches": {
                "total": self.total_branches,
                "covered": self.covered_branches,
                "percentage": self.branch_coverage_percent,
            },
        }


@dataclass
class ModuleCoverage:
    """
    Coverage for a Verilog/VHDL module
    
    Attributes:
        module_name: Name of the module
        source_files: List of source files in this module
        files: File coverage data (file_path -> FileCoverage)
        toggles: Toggle coverage data (signal_name -> ToggleData)
    """
    module_name: str
    source_files: List[str] = field(default_factory=list)
    files: Dict[str, FileCoverage] = field(default_factory=dict)
    toggles: Dict[str, ToggleData] = field(default_factory=dict)
    
    @property
    def line_coverage_percent(self) -> float:
        """Calculate overall line coverage for module"""
        if not self.files:
            return 0.0
        
        total_lines = sum(f.total_lines for f in self.files.values())
        if total_lines == 0:
            return 0.0
        
        covered_lines = sum(f.covered_lines for f in self.files.values())
        return (covered_lines / total_lines) * 100.0
    
    @property
    def branch_coverage_percent(self) -> float:
        """Calculate overall branch coverage for module"""
        if not self.files:
            return 100.0
        
        total_branches = sum(f.total_branches for f in self.files.values())
        if total_branches == 0:
            return 100.0
        
        covered_branches = sum(f.covered_branches for f in self.files.values())
        return (covered_branches / total_branches) * 100.0
    
    @property
    def toggle_coverage_percent(self) -> float:
        """Calculate average toggle coverage for module"""
        if not self.toggles:
            return 0.0
        
        return sum(t.toggle_coverage_percent for t in self.toggles.values()) / len(self.toggles)
    
    def merge(self, other: 'ModuleCoverage') -> None:
        """Merge with another module's coverage data"""
        # Merge files
        for file_path, file_cov in other.files.items():
            if file_path in self.files:
                self.files[file_path].merge(file_cov)
            else:
                self.files[file_path] = file_cov
        
        # Merge toggles
        for signal_name, toggle_data in other.toggles.items():
            if signal_name in self.toggles:
                self.toggles[signal_name].merge(toggle_data)
            else:
                self.toggles[signal_name] = toggle_data
        
        # Merge source file list
        self.source_files = list(set(self.source_files + other.source_files))
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.module_name,
            "line_coverage": self.line_coverage_percent,
            "branch_coverage": self.branch_coverage_percent,
            "toggle_coverage": self.toggle_coverage_percent,
            "files": [f.to_dict() for f in self.files.values()],
        }


# =============================================================================
# HIGH-LEVEL: STRUCTURAL COVERAGE METRICS
# =============================================================================

@dataclass
class LineCoverageMetrics:
    """
    Aggregated line coverage metrics
    
    Attributes:
        total_lines: Total executable lines
        covered_lines: Lines that were executed
        percentage: Coverage percentage
        uncovered_lines: List of uncovered line locations
    """
    total_lines: int = 0
    covered_lines: int = 0
    percentage: float = 0.0
    uncovered_lines: List[Dict[str, Any]] = field(default_factory=list)
    
    def calculate(self) -> None:
        """Calculate percentage from counts"""
        if self.total_lines > 0:
            self.percentage = (self.covered_lines / self.total_lines) * 100.0
        else:
            self.percentage = 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "total": self.total_lines,
            "covered": self.covered_lines,
            "percentage": round(self.percentage, 2),
            "uncovered_count": len(self.uncovered_lines),
        }


@dataclass
class BranchCoverageMetrics:
    """
    Aggregated branch coverage metrics
    
    Attributes:
        total_branches: Total branches
        covered_branches: Fully covered branches (both directions)
        partially_covered: Partially covered branches (one direction)
        percentage: Coverage percentage
        uncovered_branches: List of uncovered branch locations
    """
    total_branches: int = 0
    covered_branches: int = 0
    partially_covered: int = 0
    percentage: float = 0.0
    uncovered_branches: List[Dict[str, Any]] = field(default_factory=list)
    
    def calculate(self) -> None:
        """Calculate percentage from counts"""
        if self.total_branches > 0:
            self.percentage = (self.covered_branches / self.total_branches) * 100.0
        else:
            self.percentage = 100.0  # No branches = 100%
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "total": self.total_branches,
            "covered": self.covered_branches,
            "partially_covered": self.partially_covered,
            "percentage": round(self.percentage, 2),
        }


@dataclass
class ToggleCoverageMetrics:
    """
    Aggregated toggle coverage metrics
    
    Attributes:
        total_signals: Total signals
        fully_toggled_signals: Signals with full toggle coverage
        partially_toggled: Signals with partial toggle coverage
        percentage: Coverage percentage
        untoggled_signals: List of untoggled signal names
    """
    total_signals: int = 0
    fully_toggled_signals: int = 0
    partially_toggled: int = 0
    percentage: float = 0.0
    untoggled_signals: List[str] = field(default_factory=list)
    
    def calculate(self) -> None:
        """Calculate percentage from counts"""
        if self.total_signals > 0:
            self.percentage = (self.fully_toggled_signals / self.total_signals) * 100.0
        else:
            self.percentage = 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "total": self.total_signals,
            "fully_toggled": self.fully_toggled_signals,
            "partially_toggled": self.partially_toggled,
            "percentage": round(self.percentage, 2),
        }


@dataclass
class FSMCoverageMetrics:
    """
    FSM coverage metrics (Phase 2 - placeholder for now)
    
    Attributes:
        total_states: Total FSM states
        covered_states: Covered states
        total_transitions: Total state transitions
        covered_transitions: Covered transitions
        percentage: Coverage percentage
    """
    total_states: int = 0
    covered_states: int = 0
    total_transitions: int = 0
    covered_transitions: int = 0
    percentage: float = 100.0  # Default to 100% if no FSMs
    
    def calculate(self) -> None:
        """Calculate percentage from counts"""
        if self.total_states > 0:
            state_pct = (self.covered_states / self.total_states) * 100.0
        else:
            state_pct = 100.0
        
        if self.total_transitions > 0:
            trans_pct = (self.covered_transitions / self.total_transitions) * 100.0
        else:
            trans_pct = 100.0
        
        self.percentage = (state_pct + trans_pct) / 2.0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "states": {
                "total": self.total_states,
                "covered": self.covered_states,
            },
            "transitions": {
                "total": self.total_transitions,
                "covered": self.covered_transitions,
            },
            "percentage": round(self.percentage, 2),
        }


@dataclass
class StructuralCoverageMetrics:
    """
    Complete structural coverage metrics (Q4.2 - mandatory for Step 7 scoring)
    
    This is the primary coverage data consumed by Step 7 for scoring.
    
    Attributes:
        line: Line coverage metrics
        branch: Branch coverage metrics
        toggle: Toggle coverage metrics
        fsm: FSM coverage metrics
        weighted_score: Weighted overall score (0.0 to 1.0)
        uncovered_hotspots: Critical uncovered regions
    """
    line: LineCoverageMetrics = field(default_factory=LineCoverageMetrics)
    branch: BranchCoverageMetrics = field(default_factory=BranchCoverageMetrics)
    toggle: ToggleCoverageMetrics = field(default_factory=ToggleCoverageMetrics)
    fsm: FSMCoverageMetrics = field(default_factory=FSMCoverageMetrics)
    
    weighted_score: float = 0.0
    uncovered_hotspots: List[Dict[str, Any]] = field(default_factory=list)
    
    def calculate_all(self) -> None:
        """Calculate all percentages"""
        self.line.calculate()
        self.branch.calculate()
        self.toggle.calculate()
        self.fsm.calculate()
    
    def calculate_weighted_score(self, weights: Optional[Dict[str, float]] = None) -> float:
        """
        Calculate weighted overall score (Q4.2)
        
        Args:
            weights: Coverage type weights (default from Q7.1)
        
        Returns:
            Weighted score (0.0 to 1.0)
        """
        if weights is None:
            weights = {
                "line": 0.35,
                "branch": 0.35,
                "toggle": 0.20,
                "fsm": 0.10,
            }
        
        self.weighted_score = (
            self.line.percentage * weights["line"] +
            self.branch.percentage * weights["branch"] +
            self.toggle.percentage * weights["toggle"] +
            self.fsm.percentage * weights["fsm"]
        ) / 100.0  # Normalize to 0.0-1.0
        
        return self.weighted_score
    
    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary"""
        return {
            "line": self.line.to_dict(),
            "branch": self.branch.to_dict(),
            "toggle": self.toggle.to_dict(),
            "fsm": self.fsm.to_dict(),
            "weighted_score": round(self.weighted_score, 4),
            "uncovered_hotspots": self.uncovered_hotspots[:20],  # Limit output
        }


# =============================================================================
# ANALYSIS: PER-TEST + HIERARCHICAL COVERAGE (Q4.1, Q13)
# =============================================================================

@dataclass
class PerTestCoverage:
    """
    Coverage contributed by a single test (Q13 - advanced tracking)
    
    Attributes:
        test_name: Short test name
        test_full_name: Fully qualified test name
        test_duration_ms: Test execution duration
        coverage_standalone: Coverage metrics for this test alone
        unique_contribution_percent: Percentage of unique coverage
        unique_lines: Lines only this test covers
        unique_branches: Branches only this test covers
        overlapping_lines: Lines other tests also cover
        redundancy_score: Redundancy metric (0.0 = unique, 1.0 = redundant)
        efficiency_score: Coverage per second
    """
    test_name: str
    test_full_name: str
    test_duration_ms: float
    
    # Standalone coverage
    coverage_standalone: StructuralCoverageMetrics = field(default_factory=StructuralCoverageMetrics)
    
    # Unique contribution (Q13)
    unique_contribution_percent: float = 0.0
    unique_lines: Set[int] = field(default_factory=set)
    unique_branches: Set[Tuple[int, int, int]] = field(default_factory=set)  # (line, block, branch)
    
    # Overlap analysis
    overlapping_lines: Set[int] = field(default_factory=set)
    redundancy_score: float = 0.0
    
    # Value metrics
    efficiency_score: float = 0.0
    
    def calculate_metrics(self, total_unique_lines: int) -> None:
        """
        Calculate derived metrics
        
        Args:
            total_unique_lines: Total unique lines across all tests
        """
        # Unique contribution percentage
        if total_unique_lines > 0:
            self.unique_contribution_percent = (len(self.unique_lines) / total_unique_lines) * 100.0
        
        # Redundancy score
        total_lines = len(self.unique_lines) + len(self.overlapping_lines)
        if total_lines > 0:
            self.redundancy_score = len(self.overlapping_lines) / total_lines
        
        # Efficiency score (unique coverage per second)
        if self.test_duration_ms > 0:
            self.efficiency_score = self.unique_contribution_percent / (self.test_duration_ms / 1000.0)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "test_name": self.test_name,
            "test_full_name": self.test_full_name,
            "duration_ms": self.test_duration_ms,
            "coverage": self.coverage_standalone.to_dict(),
            "unique_contribution": {
                "percent": round(self.unique_contribution_percent, 2),
                "unique_lines": len(self.unique_lines),
                "unique_branches": len(self.unique_branches),
            },
            "efficiency_score": round(self.efficiency_score, 4),
            "redundancy_score": round(self.redundancy_score, 4),
        }


@dataclass
class HierarchicalCoverage:
    """
    Hierarchical coverage structure (Q4.1)
    
    Provides three views:
    1. Merged: Cumulative coverage across all tests
    2. Per-test: Individual test contributions
    3. Differential: Incremental coverage as tests are added
    
    Attributes:
        merged: Merged coverage metrics
        per_test: Per-test coverage breakdown
        differential: Test name -> cumulative coverage after adding this test
        essential_tests: Tests with significant unique coverage
        redundant_tests: Tests adding <1% new coverage
        optimal_test_order: Greedy ordering for maximum coverage
    """
    merged: StructuralCoverageMetrics = field(default_factory=StructuralCoverageMetrics)
    per_test: List[PerTestCoverage] = field(default_factory=list)
    differential: Dict[str, float] = field(default_factory=dict)
    
    # Test value analysis
    essential_tests: List[str] = field(default_factory=list)
    redundant_tests: List[str] = field(default_factory=list)
    optimal_test_order: List[str] = field(default_factory=list)
    
    def identify_test_value(self, essential_threshold: float = 5.0, 
                           redundant_threshold: float = 1.0) -> None:
        """
        Classify tests by value
        
        Args:
            essential_threshold: Minimum % unique coverage for essential tests
            redundant_threshold: Maximum % unique coverage for redundant tests
        """
        self.essential_tests = [
            t.test_name for t in self.per_test
            if t.unique_contribution_percent > essential_threshold
        ]
        
        self.redundant_tests = [
            t.test_name for t in self.per_test
            if t.unique_contribution_percent < redundant_threshold
        ]
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "merged": self.merged.to_dict(),
            "per_test": [t.to_dict() for t in self.per_test],
            "differential": self.differential,
            "analysis": {
                "essential_tests": self.essential_tests,
                "redundant_tests": self.redundant_tests,
                "optimal_order": self.optimal_test_order,
            },
        }


# =============================================================================
# INTEGRATION: MUTATION TESTING DATA (Q5.1 - for Step 6)
# =============================================================================

@dataclass
class MutationTarget:
    """
    Information for mutation testing (Step 6)
    
    Identifies weak spots in the test suite for targeted mutation testing.
    
    Attributes:
        file_path: Source file path
        line: Line number
        reason: Why this is a mutation target
        priority: Priority level (high/medium/low)
        current_coverage: Current coverage level (0.0-1.0)
        suggested_mutations: Mutation operators to try
        context: Code context around this line
    """
    file_path: str
    line: int
    reason: str
    priority: str
    current_coverage: float = 0.0
    suggested_mutations: List[str] = field(default_factory=list)
    context: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "file": self.file_path,
            "line": self.line,
            "reason": self.reason,
            "priority": self.priority,
            "coverage": round(self.current_coverage, 2),
            "suggested_mutations": self.suggested_mutations,
        }


@dataclass
class MutationTestingData:
    """
    Data export for Step 6 mutation testing (Q5.1)
    
    Helps Mcy target weak spots in test suite.
    
    Attributes:
        uncovered_lines: Lines with zero coverage
        weakly_covered_branches: Branches with only one direction covered
        untoggled_signals: Signals that never toggled
        files_by_priority: Files ranked by mutation priority
    """
    uncovered_lines: List[MutationTarget] = field(default_factory=list)
    weakly_covered_branches: List[MutationTarget] = field(default_factory=list)
    untoggled_signals: List[MutationTarget] = field(default_factory=list)
    files_by_priority: List[Dict[str, Any]] = field(default_factory=list)
    
    @property
    def total_targets(self) -> int:
        """Total number of mutation targets"""
        return (len(self.uncovered_lines) + 
                len(self.weakly_covered_branches) + 
                len(self.untoggled_signals))
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "summary": {
                "total_targets": self.total_targets,
                "uncovered_lines": len(self.uncovered_lines),
                "weak_branches": len(self.weakly_covered_branches),
                "untoggled_signals": len(self.untoggled_signals),
            },
            "targets": {
                "uncovered_lines": [t.to_dict() for t in self.uncovered_lines[:50]],
                "weak_branches": [t.to_dict() for t in self.weakly_covered_branches[:50]],
                "untoggled_signals": [t.to_dict() for t in self.untoggled_signals[:50]],
            },
            "files_by_priority": self.files_by_priority[:20],
        }


# =============================================================================
# OUTPUT: COVERAGE REPORT (Q1.2 - new coverage_report.json)
# =============================================================================

@dataclass
class CoverageReport:
    """
    Complete coverage analysis report (main output of Step 5)
    
    This is the primary output consumed by Step 7 for scoring.
    
    Outputs:
    - coverage_report.json (full detail)
    - Enriches test_report.json (adds coverage summary)
    
    Attributes:
        schema_version: Report schema version
        generated_at: Generation timestamp
        framework_version: TB Eval version
        source_test_report: Path to test_report.json
        source_build_manifest: Path to build_manifest.json
        coverage_format: Format of coverage files
        coverage_files: List of coverage file paths
        structural_coverage: Main structural coverage metrics
        hierarchical: Hierarchical coverage breakdown (optional)
        modules: Per-module coverage breakdown
        mutation_data: Mutation testing targets (optional)
        thresholds_met: Whether thresholds are met
        threshold_violations: List of violations
        analysis_metadata: Analysis metadata
        tools_used: Tools used for analysis
    """
    schema_version: str = "1.0"
    generated_at: str = field(default_factory=lambda: datetime.now().isoformat())
    framework_version: str = "0.1.0"
    
    # Source information (Q1.3)
    source_test_report: str = ""
    source_build_manifest: str = ""
    coverage_format: str = ""
    coverage_files: List[str] = field(default_factory=list)
    
    # Main metrics (Q4.2 - mandatory for Step 7)
    structural_coverage: StructuralCoverageMetrics = field(default_factory=StructuralCoverageMetrics)
    
    # Optional detailed data
    hierarchical: Optional[HierarchicalCoverage] = None
    modules: Dict[str, ModuleCoverage] = field(default_factory=dict)
    mutation_data: Optional[MutationTestingData] = None
    
    # Validation
    thresholds_met: bool = True
    threshold_violations: List[str] = field(default_factory=list)
    
    # Metadata
    analysis_metadata: Dict[str, Any] = field(default_factory=dict)
    tools_used: List[str] = field(default_factory=list)
    
    def to_summary_dict(self) -> Dict[str, Any]:
        """
        Generate minimal summary for agents (Q5.2)
        
        Returns:
            Minimal summary for agent consumption
        """
        return {
            "overall_score": round(self.structural_coverage.weighted_score, 4),
            "line_coverage": round(self.structural_coverage.line.percentage, 2),
            "branch_coverage": round(self.structural_coverage.branch.percentage, 2),
            "toggle_coverage": round(self.structural_coverage.toggle.percentage, 2),
            "pass": self.thresholds_met,
            "uncovered_critical": len(self.structural_coverage.uncovered_hotspots),
            "full_report": "coverage_report.json"
        }
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Full serialization for coverage_report.json
        
        Returns:
            Complete dictionary representation
        """
        return {
            "schema_version": self.schema_version,
            "generated_at": self.generated_at,
            "framework_version": self.framework_version,
            "sources": {
                "test_report": self.source_test_report,
                "build_manifest": self.source_build_manifest,
                "coverage_format": self.coverage_format,
                "coverage_files": self.coverage_files,
            },
            "structural_coverage": self.structural_coverage.to_dict(),
            "hierarchical": self.hierarchical.to_dict() if self.hierarchical else None,
            "modules": {
                name: module.to_dict() 
                for name, module in self.modules.items()
            },
            "mutation_data": self.mutation_data.to_dict() if self.mutation_data else None,
            "validation": {
                "thresholds_met": self.thresholds_met,
                "violations": self.threshold_violations,
            },
            "metadata": {
                **self.analysis_metadata,
                "tools_used": self.tools_used,
            },
        }
    
    def to_json(self, indent: int = 2) -> str:
        """Serialize to JSON string"""
        return json.dumps(self.to_dict(), indent=indent)
    
    def save(self, path: Path) -> None:
        """Save report to file"""
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(self.to_json())
    
    @classmethod
    def load(cls, path: Path) -> 'CoverageReport':
        """Load report from file (simplified - full implementation would reconstruct objects)"""
        data = json.loads(Path(path).read_text())
        
        # Simplified reconstruction
        report = cls(
            schema_version=data.get("schema_version", "1.0"),
            generated_at=data.get("generated_at", ""),
            framework_version=data.get("framework_version", "0.1.0"),
            source_test_report=data.get("sources", {}).get("test_report", ""),
            source_build_manifest=data.get("sources", {}).get("build_manifest", ""),
        )
        
        # TODO: Full reconstruction of nested objects
        
        return report


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def merge_module_coverage(modules: List[ModuleCoverage]) -> ModuleCoverage:
    """
    Merge multiple module coverage objects (Q6.1 - merging)
    
    Args:
        modules: List of ModuleCoverage objects to merge
    
    Returns:
        Merged ModuleCoverage
    """
    if not modules:
        return ModuleCoverage(module_name="empty", source_files=[])
    
    merged = ModuleCoverage(
        module_name=modules[0].module_name,
        source_files=modules[0].source_files.copy()
    )
    
    for module in modules[1:]:
        merged.merge(module)
    
    return merged


def calculate_differential_coverage(per_test_coverage: List[PerTestCoverage]) -> Dict[str, float]:
    """
    Calculate differential coverage (Q4.1)
    
    Shows cumulative coverage as tests are added in order.
    
    Args:
        per_test_coverage: List of per-test coverage data
    
    Returns:
        Dictionary mapping test name to cumulative coverage percentage
    """
    differential = {}
    cumulative_lines: Set[int] = set()
    
    for test_cov in per_test_coverage:
        # Add this test's lines to cumulative set
        cumulative_lines.update(test_cov.unique_lines)
        cumulative_lines.update(test_cov.overlapping_lines)
        
        # Calculate cumulative percentage
        # (This is simplified - full implementation needs total_lines from somewhere)
        differential[test_cov.test_name] = len(cumulative_lines)
    
    return differential
