"""
Test coverage analyzer
"""

from pathlib import Path
import tempfile
import json


def create_test_environment():
    """Create test environment with test_report and coverage files"""
    tmpdir = Path(tempfile.mkdtemp())
    
    # Create test_report.json
    test_report = {
        "schema_version": "1.0",
        "status": "completed",
        "results": [
            {
                "name": "test_basic",
                "outcome": "passed",
                "duration_ms": 1000.0,
                "artifacts": {
                    "coverage_file": str(tmpdir / "coverage_test_basic.dat")
                }
            },
            {
                "name": "test_overflow",
                "outcome": "passed",
                "duration_ms": 1500.0,
                "artifacts": {
                    "coverage_file": str(tmpdir / "coverage_test_overflow.dat")
                }
            }
        ]
    }
    
    test_report_path = tmpdir / "test_report.json"
    with open(test_report_path, 'w') as f:
        json.dump(test_report, f)
    
    # Create build_manifest.json
    build_manifest = {
        "schema_version": "1.0",
        "build_status": "success"
    }
    
    build_manifest_path = tmpdir / "build_manifest.json"
    with open(build_manifest_path, 'w') as f:
        json.dump(build_manifest, f)
    
    # Create coverage files
    coverage1 = """# Verilator coverage
SF:test.sv
DA:10,5
DA:11,3
DA:12,0
end_of_record
"""
    
    coverage2 = """# Verilator coverage
SF:test.sv
DA:13,7
DA:14,2
DA:15,1
end_of_record
"""
    
    cov1_path = tmpdir / "coverage_test_basic.dat"
    cov1_path.write_text(coverage1)
    
    cov2_path = tmpdir / "coverage_test_overflow.dat"
    cov2_path.write_text(coverage2)
    
    return tmpdir, test_report_path, build_manifest_path


def test_analyzer_creation():
    """Test CoverageAnalyzer creation"""
    from step5_coverage import CoverageAnalyzer
    from step5_coverage.config import CoverageAnalysisConfig
    
    tmpdir, test_report_path, build_manifest_path = create_test_environment()
    
    try:
        config = CoverageAnalysisConfig(
            test_report_path=test_report_path,
            build_manifest_path=build_manifest_path
        )
        
        analyzer = CoverageAnalyzer(config)
        assert analyzer is not None
        assert analyzer.config is not None
        
    finally:
        import shutil
        shutil.rmtree(tmpdir)


def test_from_test_report():
    """Test creating analyzer from test report"""
    from step5_coverage import CoverageAnalyzer
    
    tmpdir, test_report_path, build_manifest_path = create_test_environment()
    
    try:
        analyzer = CoverageAnalyzer.from_test_report(
            test_report_path,
            build_manifest_path
        )
        
        assert analyzer is not None
        
    finally:
        import shutil
        shutil.rmtree(tmpdir)


def test_load_test_report():
    """Test loading test report"""
    from step5_coverage import CoverageAnalyzer, AnalysisResult
    
    tmpdir, test_report_path, build_manifest_path = create_test_environment()
    
    try:
        analyzer = CoverageAnalyzer.from_test_report(
            test_report_path,
            build_manifest_path
        )
        
        result = AnalysisResult()
        success = analyzer._load_test_report(result)
        
        assert success
        assert analyzer.test_report_data is not None
        assert "results" in analyzer.test_report_data
        
    finally:
        import shutil
        shutil.rmtree(tmpdir)


def test_find_coverage_files():
    """Test finding coverage files"""
    from step5_coverage import CoverageAnalyzer, AnalysisResult
    
    tmpdir, test_report_path, build_manifest_path = create_test_environment()
    
    try:
        analyzer = CoverageAnalyzer.from_test_report(
            test_report_path,
            build_manifest_path
        )
        
        result = AnalysisResult()
        analyzer._load_test_report(result)
        success = analyzer._find_coverage_files(result)
        
        assert success
        assert len(analyzer.coverage_files) == 2
        
    finally:
        import shutil
        shutil.rmtree(tmpdir)


def test_complete_analysis():
    """Test complete analysis pipeline"""
    from step5_coverage import CoverageAnalyzer
    
    tmpdir, test_report_path, build_manifest_path = create_test_environment()
    
    try:
        analyzer = CoverageAnalyzer.from_test_report(
            test_report_path,
            build_manifest_path
        )
        
        result = analyzer.analyze()
        
        assert result is not None
        assert result.success
        assert result.report is not None
        assert result.report.structural_coverage is not None
        
        # Check that metrics were calculated
        metrics = result.report.structural_coverage
        assert metrics.line.total_lines > 0
        
    finally:
        import shutil
        shutil.rmtree(tmpdir)


def test_save_report():
    """Test saving coverage report"""
    from step5_coverage import CoverageAnalyzer
    
    tmpdir, test_report_path, build_manifest_path = create_test_environment()
    
    try:
        analyzer = CoverageAnalyzer.from_test_report(
            test_report_path,
            build_manifest_path
        )
        
        result = analyzer.analyze()
        
        if result.success:
            output_path = tmpdir / "coverage_report.json"
            saved_path = analyzer.save_report(result.report, output_path)
            
            assert saved_path.exists()
            assert saved_path.stat().st_size > 0
        
    finally:
        import shutil
        shutil.rmtree(tmpdir)


def test_generate_summary():
    """Test generating summary"""
    from step5_coverage import CoverageAnalyzer
    
    tmpdir, test_report_path, build_manifest_path = create_test_environment()
    
    try:
        analyzer = CoverageAnalyzer.from_test_report(
            test_report_path,
            build_manifest_path
        )
        
        result = analyzer.analyze()
        
        if result.success:
            summary = analyzer.generate_summary(result.report)
            
            assert isinstance(summary, str)
            assert len(summary) > 0
            assert "Coverage Summary" in summary
        
    finally:
        import shutil
        shutil.rmtree(tmpdir)


def test_convenience_functions():
    """Test convenience functions"""
    from step5_coverage import analyze_coverage, quick_analyze
    
    tmpdir, test_report_path, build_manifest_path = create_test_environment()
    
    try:
        # Test analyze_coverage
        result = analyze_coverage(test_report_path, build_manifest_path)
        assert result is not None
        
        # Test quick_analyze
        report = quick_analyze(test_report_path)
        assert report is not None
        
    finally:
        import shutil
        shutil.rmtree(tmpdir)


if __name__ == "__main__":
    print("Testing coverage analyzer...")
    
    test_analyzer_creation()
    print("✓ Analyzer creation")
    
    test_from_test_report()
    print("✓ From test report")
    
    test_load_test_report()
    print("✓ Load test report")
    
    test_find_coverage_files()
    print("✓ Find coverage files")
    
    test_complete_analysis()
    print("✓ Complete analysis")
    
    test_save_report()
    print("✓ Save report")
    
    test_generate_summary()
    print("✓ Generate summary")
    
    test_convenience_functions()
    print("✓ Convenience functions")
    
    print("\n✅ All analyzer tests passed!")
