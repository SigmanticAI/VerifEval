"""
Test coverage merger
"""

from pathlib import Path


def create_test_coverages():
    """Create test coverage data for multiple tests"""
    from step5_coverage.models import (
        ModuleCoverage,
        FileCoverage,
        LineCoverageData,
        BranchData,
    )
    
    coverages = {}
    
    # Test 1: Covers lines 10-15
    module1 = ModuleCoverage(module_name="test1")
    file1 = FileCoverage(file_path="test.sv")
    for i in range(10, 16):
        file1.lines[i] = LineCoverageData(line_number=i, hit_count=5)
    file1.branches.append(BranchData(15, 0, 0, 5, 0))
    module1.files["test.sv"] = file1
    coverages["test1"] = module1
    
    # Test 2: Covers lines 13-20 (overlap with test1 on 13-15)
    module2 = ModuleCoverage(module_name="test2")
    file2 = FileCoverage(file_path="test.sv")
    for i in range(13, 21):
        file2.lines[i] = LineCoverageData(line_number=i, hit_count=3)
    file2.branches.append(BranchData(18, 0, 0, 3, 0))
    module2.files["test.sv"] = file2
    coverages["test2"] = module2
    
    # Test 3: Covers lines 25-30 (no overlap)
    module3 = ModuleCoverage(module_name="test3")
    file3 = FileCoverage(file_path="test.sv")
    for i in range(25, 31):
        file3.lines[i] = LineCoverageData(line_number=i, hit_count=2)
    module3.files["test.sv"] = file3
    coverages["test3"] = module3
    
    # Test 4: Only covers lines 13-15 (completely redundant with test1+test2)
    module4 = ModuleCoverage(module_name="test4")
    file4 = FileCoverage(file_path="test.sv")
    for i in range(13, 16):
        file4.lines[i] = LineCoverageData(line_number=i, hit_count=1)
    module4.files["test.sv"] = file4
    coverages["test4"] = module4
    
    return coverages


def test_simple_merge():
    """Test simple merging without tracking"""
    from step5_coverage.metrics.merger import CoverageMerger
    
    coverages_dict = create_test_coverages()
    coverages_list = list(coverages_dict.values())
    
    merger = CoverageMerger()
    merged = merger.merge_simple(coverages_list)
    
    assert merged is not None
    assert "test.sv" in merged.files
    
    # Should have all unique lines: 10-20, 25-30 = 17 lines
    assert len(merged.files["test.sv"].lines) == 17
    
    # Lines 13-15 should have combined hit counts
    # test1: 5, test2: 3, test4: 1 = 9
    assert merged.files["test.sv"].lines[13].hit_count == 9


def test_merge_with_tracking():
    """Test merge with per-test tracking"""
    from step5_coverage.metrics.merger import CoverageMerger
    
    coverages = create_test_coverages()
    durations = {
        "test1": 1000.0,
        "test2": 1500.0,
        "test3": 800.0,
        "test4": 500.0,
    }
    
    merger = CoverageMerger()
    hierarchical = merger.merge_with_tracking(coverages, durations)
    
    assert hierarchical is not None
    assert hierarchical.merged is not None
    assert len(hierarchical.per_test) == 4
    
    # Check merged metrics
    assert hierarchical.merged.line.total_lines == 17
    
    # Check per-test data exists
    for per_test in hierarchical.per_test:
        assert per_test.test_name in coverages
        assert per_test.test_duration_ms > 0
        assert per_test.coverage_standalone is not None


def test_unique_coverage_identification():
    """Test unique coverage identification"""
    from step5_coverage.metrics.merger import CoverageMerger
    
    coverages = create_test_coverages()
    durations = {"test1": 1000.0, "test2": 1000.0, "test3": 1000.0, "test4": 1000.0}
    
    merger = CoverageMerger()
    hierarchical = merger.merge_with_tracking(coverages, durations)
    
    # Find test1 results
    test1 = next(t for t in hierarchical.per_test if t.test_name == "test1")
    
    # test1 covers 10-15, unique are 10-12 (3 lines)
    assert len(test1.unique_lines) == 3
    
    # Overlapping are 13-15 (3 lines, shared with test2 and test4)
    assert len(test1.overlapping_lines) == 3
    
    # Find test3 results
    test3 = next(t for t in hierarchical.per_test if t.test_name == "test3")
    
    # test3 covers 25-30, all unique (6 lines)
    assert len(test3.unique_lines) == 6
    assert len(test3.overlapping_lines) == 0


def test_redundancy_detection():
    """Test redundant test detection"""
    from step5_coverage.metrics.merger import CoverageMerger
    
    coverages = create_test_coverages()
    durations = {"test1": 1000.0, "test2": 1000.0, "test3": 1000.0, "test4": 1000.0}
    
    merger = CoverageMerger()
    hierarchical = merger.merge_with_tracking(
        coverages,
        durations,
        redundant_threshold=1.0  # Tests with <1% unique coverage
    )
    
    # test4 should be identified as redundant (covers only 13-15, already covered)
    assert "test4" in hierarchical.redundant_tests
    
    # test1, test2, test3 should not be redundant
    assert "test1" not in hierarchical.redundant_tests
    assert "test2" not in hierarchical.redundant_tests
    assert "test3" not in hierarchical.redundant_tests


def test_essential_test_identification():
    """Test essential test identification"""
    from step5_coverage.metrics.merger import CoverageMerger
    
    coverages = create_test_coverages()
    durations = {"test1": 1000.0, "test2": 1000.0, "test3": 1000.0, "test4": 1000.0}
    
    merger = CoverageMerger()
    hierarchical = merger.merge_with_tracking(
        coverages,
        durations,
        essential_threshold=15.0  # Tests with >15% unique coverage
    )
    
    # test3 covers 6/17 lines uniquely = ~35% - should be essential
    assert "test3" in hierarchical.essential_tests


def test_differential_coverage():
    """Test differential coverage calculation"""
    from step5_coverage.metrics.merger import CoverageMerger
    
    coverages = create_test_coverages()
    durations = {"test1": 1000.0, "test2": 1000.0, "test3": 1000.0, "test4": 1000.0}
    
    merger = CoverageMerger()
    hierarchical = merger.merge_with_tracking(coverages, durations)
    
    # Should have differential coverage for each test
    assert len(hierarchical.differential) == 4
    
    # Coverage should be monotonically increasing (or at least non-decreasing)
    prev_coverage = 0.0
    for test_name, coverage in hierarchical.differential.items():
        assert coverage >= prev_coverage
        prev_coverage = coverage


def test_optimal_order_calculation():
    """Test optimal test order calculation"""
    from step5_coverage.metrics.merger import CoverageMerger
    
    coverages = create_test_coverages()
    durations = {"test1": 1000.0, "test2": 1000.0, "test3": 1000.0, "test4": 1000.0}
    
    merger = CoverageMerger()
    hierarchical = merger.merge_with_tracking(coverages, durations)
    
    # Should have optimal order
    assert len(hierarchical.optimal_test_order) == 4
    
    # test4 should be last (it's redundant)
    assert hierarchical.optimal_test_order[-1] == "test4"
    
    # test3 should be early (lots of unique coverage)
    assert hierarchical.optimal_test_order.index("test3") < 3


def test_efficiency_scoring():
    """Test efficiency score calculation"""
    from step5_coverage.metrics.merger import CoverageMerger
    
    coverages = create_test_coverages()
    durations = {
        "test1": 1000.0,  # 6 lines in 1s = 6 lines/s
        "test2": 2000.0,  # 8 lines in 2s = 4 lines/s
        "test3": 500.0,   # 6 lines in 0.5s = 12 lines/s (most efficient)
        "test4": 1000.0,  # 3 lines in 1s = 3 lines/s
    }
    
    merger = CoverageMerger()
    hierarchical = merger.merge_with_tracking(coverages, durations)
    
    # Find test3 (should be most efficient due to unique coverage and short duration)
    test3 = next(t for t in hierarchical.per_test if t.test_name == "test3")
    
    # test3 should have highest efficiency score
    all_efficiency = [t.efficiency_score for t in hierarchical.per_test]
    assert test3.efficiency_score == max(all_efficiency)


def test_redundancy_analysis():
    """Test redundancy analysis"""
    from step5_coverage.metrics.merger import CoverageMerger
    
    coverages = create_test_coverages()
    durations = {"test1": 1000.0, "test2": 1000.0, "test3": 1000.0, "test4": 1000.0}
    
    merger = CoverageMerger()
    hierarchical = merger.merge_with_tracking(coverages, durations)
    
    analysis = merger.analyze_test_redundancy(hierarchical)
    
    assert analysis["total_tests"] == 4
    assert analysis["redundant_tests"] >= 1  # test4 should be redundant
    assert "recommended_action" in analysis
    assert analysis["optimization_potential"]


def test_coverage_convergence():
    """Test coverage convergence analysis"""
    from step5_coverage.metrics.merger import CoverageMerger
    
    coverages = create_test_coverages()
    durations = {"test1": 1000.0, "test2": 1000.0, "test3": 1000.0, "test4": 1000.0}
    
    merger = CoverageMerger()
    hierarchical = merger.merge_with_tracking(coverages, durations)
    
    convergence = merger.calculate_coverage_convergence(hierarchical)
    
    assert "initial_coverage" in convergence
    assert "final_coverage" in convergence
    assert "coverage_gain" in convergence
    assert convergence["final_coverage"] >= convergence["initial_coverage"]


def test_test_removal_suggestions():
    """Test suggesting tests for removal"""
    from step5_coverage.metrics.merger import CoverageMerger
    
    coverages = create_test_coverages()
    durations = {"test1": 1000.0, "test2": 1000.0, "test3": 1000.0, "test4": 1000.0}
    
    merger = CoverageMerger()
    hierarchical = merger.merge_with_tracking(coverages, durations)
    
    removable = merger.suggest_test_removal(hierarchical)
    
    # test4 should be suggested for removal
    assert "test4" in removable


def test_merge_statistics():
    """Test merge statistics"""
    from step5_coverage.metrics.merger import CoverageMerger
    
    coverages = create_test_coverages()
    durations = {"test1": 1000.0, "test2": 1000.0, "test3": 1000.0, "test4": 1000.0}
    
    merger = CoverageMerger()
    hierarchical = merger.merge_with_tracking(coverages, durations)
    
    stats = merger.get_merge_statistics(hierarchical)
    
    assert stats.total_tests == 4
    assert stats.total_lines == 17
    assert stats.overlap_percentage > 0


def test_convenience_functions():
    """Test convenience functions"""
    from step5_coverage.metrics.merger import (
        merge_coverage_simple,
        merge_coverage_with_tracking,
    )
    
    coverages_dict = create_test_coverages()
    coverages_list = list(coverages_dict.values())
    
    # Test simple merge
    merged = merge_coverage_simple(coverages_list)
    assert merged is not None
    
    # Test tracked merge
    hierarchical = merge_coverage_with_tracking(coverages_dict)
    assert hierarchical is not None
    assert len(hierarchical.per_test) == 4


if __name__ == "__main__":
    print("Testing coverage merger...")
    
    test_simple_merge()
    print("✓ Simple merge")
    
    test_merge_with_tracking()
    print("✓ Merge with tracking")
    
    test_unique_coverage_identification()
    print("✓ Unique coverage identification")
    
    test_redundancy_detection()
    print("✓ Redundancy detection")
    
    test_essential_test_identification()
    print("✓ Essential test identification")
    
    test_differential_coverage()
    print("✓ Differential coverage")
    
    test_optimal_order_calculation()
    print("✓ Optimal order calculation")
    
    test_efficiency_scoring()
    print("✓ Efficiency scoring")
    
    test_redundancy_analysis()
    print("✓ Redundancy analysis")
    
    test_coverage_convergence()
    print("✓ Coverage convergence")
    
    test_test_removal_suggestions()
    print("✓ Test removal suggestions")
    
    test_merge_statistics()
    print("✓ Merge statistics")
    
    test_convenience_functions()
    print("✓ Convenience functions")
    
    print("\n✅ All merger tests passed!")
