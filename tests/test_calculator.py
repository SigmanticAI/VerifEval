"""
Test coverage calculator
"""

from pathlib import Path
import tempfile


def create_test_module_coverage():
    """Create test coverage data"""
    from step5_coverage.models import (
        ModuleCoverage,
        FileCoverage,
        LineCoverageData,
        BranchData,
        ToggleData,
    )
    
    module = ModuleCoverage(module_name="test_module")
    
    # Create file with mixed coverage
    file1 = FileCoverage(file_path="test1.sv")
    
    # Lines: 10 total, 8 covered
    for i in range(10, 20):
        hits = 5 if i < 18 else 0  # Lines 18-19 uncovered
        file1.lines[i] = LineCoverageData(line_number=i, hit_count=hits)
    
    # Branches: 4 total, 3 covered
    file1.branches = [
        BranchData(line_number=15, block_number=0, branch_number=0, taken_count=5, not_taken_count=3),
        BranchData(line_number=15, block_number=0, branch_number=1, taken_count=2, not_taken_count=1),
        BranchData(line_number=17, block_number=1, branch_number=0, taken_count=4, not_taken_count=0),
        BranchData(line_number=17, block_number=1, branch_number=1, taken_count=0, not_taken_count=0),  # Uncovered
    ]
    
    module.files["test1.sv"] = file1
    
    # Create file with full coverage
    file2 = FileCoverage(file_path="test2.sv")
    for i in range(20, 25):
        file2.lines[i] = LineCoverageData(line_number=i, hit_count=10)
    
    module.files["test2.sv"] = file2
    
    # Add toggle coverage
    toggle1 = ToggleData(signal_name="clk", bit_width=1)
    toggle1.toggles_0to1[0] = 100
    toggle1.toggles_1to0[0] = 100
    module.toggles["clk"] = toggle1
    
    toggle2 = ToggleData(signal_name="data", bit_width=8)
    for i in range(6):  # Only 6 of 8 bits fully toggled
        toggle2.toggles_0to1[i] = 10
        toggle2.toggles_1to0[i] = 10
    module.toggles["data"] = toggle2
    
    return module


def test_calculator_creation():
    """Test CoverageCalculator creation"""
    from step5_coverage.metrics.calculator import CoverageCalculator
    
    calc = CoverageCalculator()
    assert calc is not None
    assert calc.weights is not None
    assert calc.thresholds is not None


def test_line_coverage_calculation():
    """Test line coverage calculation"""
    from step5_coverage.metrics.calculator import CoverageCalculator
    
    module = create_test_module_coverage()
    calc = CoverageCalculator()
    
    line_metrics = calc.calculate_line_coverage(module)
    
    # 15 total lines (10 from file1, 5 from file2)
    assert line_metrics.total_lines == 15
    
    # 13 covered (8 from file1, 5 from file2)
    assert line_metrics.covered_lines == 13
    
    # 13/15 = 86.67%
    assert 86.0 < line_metrics.percentage < 87.0
    
    # Should have uncovered lines
    assert len(line_metrics.uncovered_lines) > 0


def test_branch_coverage_calculation():
    """Test branch coverage calculation"""
    from step5_coverage.metrics.calculator import CoverageCalculator
    
    module = create_test_module_coverage()
    calc = CoverageCalculator()
    
    branch_metrics = calc.calculate_branch_coverage(module)
    
    # 4 total branches
    assert branch_metrics.total_branches == 4
    
    # 2 fully covered (both directions taken)
    assert branch_metrics.covered_branches == 2
    
    # 1 partially covered
    assert branch_metrics.partially_covered == 1
    
    # 2/4 = 50%
    assert branch_metrics.percentage == 50.0


def test_toggle_coverage_calculation():
    """Test toggle coverage calculation"""
    from step5_coverage.metrics.calculator import CoverageCalculator
    
    module = create_test_module_coverage()
    calc = CoverageCalculator()
    
    toggle_metrics = calc.calculate_toggle_coverage(module)
    
    # 2 total signals
    assert toggle_metrics.total_signals == 2
    
    # 1 fully toggled (clk)
    assert toggle_metrics.fully_toggled_signals == 1
    
    # 1 partially toggled (data - only 6/8 bits)
    assert toggle_metrics.partially_toggled == 1
    
    # 1/2 = 50%
    assert toggle_metrics.percentage == 50.0


def test_complete_metrics_calculation():
    """Test complete metrics calculation"""
    from step5_coverage.metrics.calculator import CoverageCalculator
    
    module = create_test_module_coverage()
    calc = CoverageCalculator()
    
    metrics = calc.calculate_metrics(module)
    
    assert metrics.line.percentage > 0
    assert metrics.branch.percentage > 0
    assert metrics.toggle.percentage > 0
    assert metrics.fsm.percentage == 100.0  # No FSMs
    assert metrics.weighted_score > 0
    
    # Check weighted score calculation
    # Line: ~86.7% * 0.35 = ~30.3
    # Branch: 50% * 0.35 = 17.5
    # Toggle: 50% * 0.20 = 10.0
    # FSM: 100% * 0.10 = 10.0
    # Total: ~67.8%
    expected_score = (
        metrics.line.percentage * 0.35 +
        metrics.branch.percentage * 0.35 +
        metrics.toggle.percentage * 0.20 +
        metrics.fsm.percentage * 0.10
    ) / 100.0
    
    assert abs(metrics.weighted_score - expected_score) < 0.01


def test_hotspot_identification():
    """Test uncovered hotspot identification"""
    from step5_coverage.metrics.calculator import CoverageCalculator
    from step5_coverage.models import (
        ModuleCoverage,
        FileCoverage,
        LineCoverageData,
    )
    
    # Create module with large uncovered region
    module = ModuleCoverage(module_name="test")
    file = FileCoverage(file_path="test.sv")
    
    # Covered lines: 10-15
    for i in range(10, 16):
        file.lines[i] = LineCoverageData(line_number=i, hit_count=5)
    
    # Large uncovered region: 16-25 (10 lines)
    for i in range(16, 26):
        file.lines[i] = LineCoverageData(line_number=i, hit_count=0)
    
    # Covered lines: 26-30
    for i in range(26, 31):
        file.lines[i] = LineCoverageData(line_number=i, hit_count=5)
    
    module.files["test.sv"] = file
    
    calc = CoverageCalculator()
    hotspots = calc.identify_hotspots(module, min_region_size=3)
    
    # Should find one hotspot
    assert len(hotspots) == 1
    
    hotspot = hotspots[0]
    assert hotspot.start_line == 16
    assert hotspot.end_line == 25
    assert hotspot.line_count == 10
    assert hotspot.priority == "high"  # 10+ lines
    assert hotspot.is_critical


def test_per_file_metrics():
    """Test per-file metrics calculation"""
    from step5_coverage.metrics.calculator import CoverageCalculator
    
    module = create_test_module_coverage()
    calc = CoverageCalculator()
    
    per_file = calc.calculate_per_file_metrics(module)
    
    assert "test1.sv" in per_file
    assert "test2.sv" in per_file
    
    # test1.sv: 8/10 = 80%
    assert per_file["test1.sv"]["lines_total"] == 10
    assert per_file["test1.sv"]["lines_covered"] == 8
    assert per_file["test1.sv"]["line_coverage"] == 80.0
    
    # test2.sv: 5/5 = 100%
    assert per_file["test2.sv"]["line_coverage"] == 100.0


def test_metrics_validation():
    """Test metrics validation against thresholds"""
    from step5_coverage.metrics.calculator import CoverageCalculator
    from step5_coverage.config import CoverageThresholds
    
    module = create_test_module_coverage()
    
    # Strict thresholds
    thresholds = CoverageThresholds(
        line=90.0,
        branch=80.0,
        toggle=80.0,
        overall=85.0
    )
    
    calc = CoverageCalculator(thresholds=thresholds)
    metrics = calc.calculate_metrics(module)
    
    passed, violations = calc.validate_metrics(metrics)
    
    # Should fail (our test data has ~86% line, 50% branch, 50% toggle)
    assert not passed
    assert len(violations) > 0
    
    # Check that violations are reported
    violations_text = ' '.join(violations)
    assert 'branch' in violations_text.lower() or 'toggle' in violations_text.lower()


def test_metrics_comparison():
    """Test comparing two sets of metrics"""
    from step5_coverage.metrics.calculator import CoverageCalculator
    from step5_coverage.models import StructuralCoverageMetrics
    
    calc = CoverageCalculator()
    
    # Create before metrics
    before = StructuralCoverageMetrics()
    before.line.total_lines = 100
    before.line.covered_lines = 70
    before.line.calculate()
    before.branch.total_branches = 50
    before.branch.covered_branches = 30
    before.branch.calculate()
    before.calculate_weighted_score()
    
    # Create after metrics (improved)
    after = StructuralCoverageMetrics()
    after.line.total_lines = 100
    after.line.covered_lines = 85
    after.line.calculate()
    after.branch.total_branches = 50
    after.branch.covered_branches = 40
    after.branch.calculate()
    after.calculate_weighted_score()
    
    # Compare
    deltas = calc.compare_metrics(before, after)
    
    assert deltas["line_delta"] == 15.0  # 85% - 70%
    assert deltas["branch_delta"] == 20.0  # 80% - 60%
    
    # Check improvement analysis
    improvement = calc.calculate_improvement(before, after)
    assert improvement["improved"]
    assert not improvement["regressed"]


def test_coverage_gaps():
    """Test coverage gap identification"""
    from step5_coverage.metrics.calculator import CoverageCalculator
    from step5_coverage.models import (
        ModuleCoverage,
        FileCoverage,
        LineCoverageData,
    )
    
    module = ModuleCoverage(module_name="test")
    
    # Uncovered file
    file1 = FileCoverage(file_path="uncovered.sv")
    for i in range(10, 20):
        file1.lines[i] = LineCoverageData(line_number=i, hit_count=0)
    module.files["uncovered.sv"] = file1
    
    # Partially covered file
    file2 = FileCoverage(file_path="partial.sv")
    for i in range(10, 20):
        hits = 5 if i < 13 else 0  # Only 3/10 covered = 30%
        file2.lines[i] = LineCoverageData(line_number=i, hit_count=hits)
    module.files["partial.sv"] = file2
    
    calc = CoverageCalculator()
    gaps = calc.calculate_coverage_gaps(module)
    
    assert "uncovered.sv" in gaps["uncovered_files"]
    assert "partial.sv" in gaps["partially_covered_files"]


def test_coverage_summary():
    """Test coverage summary generation"""
    from step5_coverage.metrics.calculator import CoverageCalculator
    
    module = create_test_module_coverage()
    calc = CoverageCalculator()
    
    metrics = calc.calculate_metrics(module)
    summary = calc.get_coverage_summary(metrics)
    
    assert "Coverage Summary" in summary
    assert "Line:" in summary
    assert "Branch:" in summary
    assert "Overall:" in summary
    assert "%" in summary


def test_convenience_functions():
    """Test convenience functions"""
    from step5_coverage.metrics.calculator import (
        calculate_coverage,
        quick_summary,
    )
    
    module = create_test_module_coverage()
    
    # Test calculate_coverage
    metrics = calculate_coverage(module)
    assert metrics is not None
    assert metrics.line.percentage > 0
    
    # Test quick_summary
    summary = quick_summary(module)
    assert isinstance(summary, str)
    assert len(summary) > 0


if __name__ == "__main__":
    print("Testing coverage calculator...")
    
    test_calculator_creation()
    print("✓ Calculator creation")
    
    test_line_coverage_calculation()
    print("✓ Line coverage calculation")
    
    test_branch_coverage_calculation()
    print("✓ Branch coverage calculation")
    
    test_toggle_coverage_calculation()
    print("✓ Toggle coverage calculation")
    
    test_complete_metrics_calculation()
    print("✓ Complete metrics calculation")
    
    test_hotspot_identification()
    print("✓ Hotspot identification")
    
    test_per_file_metrics()
    print("✓ Per-file metrics")
    
    test_metrics_validation()
    print("✓ Metrics validation")
    
    test_metrics_comparison()
    print("✓ Metrics comparison")
    
    test_coverage_gaps()
    print("✓ Coverage gaps")
    
    test_coverage_summary()
    print("✓ Coverage summary")
    
    test_convenience_functions()
    print("✓ Convenience functions")
    
    print("\n✅ All calculator tests passed!")
