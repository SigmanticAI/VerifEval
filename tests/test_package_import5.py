"""
Quick test to verify step5_coverage package imports correctly
"""

def test_package_import():
    """Test that package can be imported"""
    import step5_coverage
    assert step5_coverage.__version__ == "0.1.0"


def test_model_imports():
    """Test that models can be imported"""
    from step5_coverage import (
        CoverageFormat,
        CoverageReport,
        StructuralCoverageMetrics,
        LineCoverageData,
        BranchData,
        ToggleData,
    )
    
    # Verify classes are importable
    assert CoverageFormat.VERILATOR_DAT
    assert CoverageReport
    assert StructuralCoverageMetrics


def test_create_empty_report():
    """Test convenience function"""
    from step5_coverage import create_empty_report
    
    report = create_empty_report()
    assert report.schema_version == "1.0"
    assert report.framework_version == "0.1.0"


def test_model_instantiation():
    """Test that models can be instantiated"""
    from step5_coverage import (
        LineCoverageData,
        BranchData,
        ToggleData,
        FileCoverage,
        ModuleCoverage,
        StructuralCoverageMetrics,
        CoverageReport,
    )
    
    # Create instances
    line = LineCoverageData(line_number=10, hit_count=5)
    assert line.is_covered
    
    branch = BranchData(
        line_number=20,
        block_number=1,
        branch_number=0,
        taken_count=3,
        not_taken_count=2
    )
    assert branch.is_fully_covered
    
    toggle = ToggleData(signal_name="clk", bit_width=1)
    toggle.toggles_0to1[0] = 100
    toggle.toggles_1to0[0] = 100
    assert toggle.toggle_coverage_percent == 100.0
    
    file_cov = FileCoverage(file_path="test.sv")
    file_cov.lines[10] = line
    file_cov.branches.append(branch)
    assert file_cov.line_coverage_percent == 100.0
    
    module = ModuleCoverage(module_name="test_module")
    module.files["test.sv"] = file_cov
    module.toggles["clk"] = toggle
    
    metrics = StructuralCoverageMetrics()
    metrics.line.total_lines = 100
    metrics.line.covered_lines = 85
    metrics.line.calculate()
    assert metrics.line.percentage == 85.0
    
    report = CoverageReport()
    report.structural_coverage = metrics
    assert report.schema_version == "1.0"


def test_serialization():
    """Test JSON serialization"""
    from step5_coverage import CoverageReport, StructuralCoverageMetrics
    
    report = CoverageReport()
    report.structural_coverage = StructuralCoverageMetrics()
    report.structural_coverage.line.total_lines = 100
    report.structural_coverage.line.covered_lines = 80
    report.structural_coverage.line.calculate()
    report.structural_coverage.calculate_weighted_score()
    
    # Test to_dict
    data = report.to_dict()
    assert "structural_coverage" in data
    assert data["structural_coverage"]["line"]["percentage"] == 80.0
    
    # Test to_json
    json_str = report.to_json()
    assert "structural_coverage" in json_str
    assert "80.0" in json_str or "80" in json_str
    
    # Test to_summary_dict
    summary = report.to_summary_dict()
    assert "overall_score" in summary
    assert "line_coverage" in summary
    assert summary["line_coverage"] == 80.0


def test_merge_functionality():
    """Test merging coverage data"""
    from step5_coverage import (
        LineCoverageData,
        FileCoverage,
        ModuleCoverage,
        merge_module_coverage,
    )
    
    # Create two modules with overlapping coverage
    module1 = ModuleCoverage(module_name="test")
    file1 = FileCoverage(file_path="test.sv")
    file1.lines[10] = LineCoverageData(line_number=10, hit_count=5)
    file1.lines[20] = LineCoverageData(line_number=20, hit_count=3)
    module1.files["test.sv"] = file1
    
    module2 = ModuleCoverage(module_name="test")
    file2 = FileCoverage(file_path="test.sv")
    file2.lines[10] = LineCoverageData(line_number=10, hit_count=7)  # Same line
    file2.lines[30] = LineCoverageData(line_number=30, hit_count=2)  # New line
    module2.files["test.sv"] = file2
    
    # Merge
    merged = merge_module_coverage([module1, module2])
    
    # Verify merge results
    assert len(merged.files["test.sv"].lines) == 3  # Lines 10, 20, 30
    assert merged.files["test.sv"].lines[10].hit_count == 12  # 5 + 7
    assert merged.files["test.sv"].lines[20].hit_count == 3
    assert merged.files["test.sv"].lines[30].hit_count == 2


if __name__ == "__main__":
    # Run tests
    print("Testing step5_coverage package...")
    
    test_package_import()
    print("✓ Package import")
    
    test_model_imports()
    print("✓ Model imports")
    
    test_create_empty_report()
    print("✓ Convenience functions")
    
    test_model_instantiation()
    print("✓ Model instantiation")
    
    test_serialization()
    print("✓ JSON serialization")
    
    test_merge_functionality()
    print("✓ Merge functionality")
    
    print("\n✅ All tests passed!")
