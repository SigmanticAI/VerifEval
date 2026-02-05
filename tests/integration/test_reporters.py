"""
Integration tests for report generators

Author: TB Eval Team
Version: 0.1.0
"""

import pytest
from pathlib import Path

from step4_execute.reporters import (
    TestReportGenerator,
    TestReportValidator,
    TestReportComparator,
    TestReportAnalyzer,
    generate_junit,
    generate_html,
)


class TestReportGeneration:
    """Test report generation"""
    
    def test_generate_json_report(self, temp_dir, sample_test_report):
        """Test JSON report generation"""
        output_path = temp_dir / "report.json"
        
        generator = TestReportGenerator(sample_test_report)
        generated_path = generator.generate(output_path)
        
        assert generated_path.exists()
        assert generated_path == output_path
        
        # Validate structure
        is_valid, errors = TestReportValidator.validate_file(generated_path)
        assert is_valid, f"Report invalid: {errors}"
    
    def test_generate_summary_only(self, temp_dir, sample_test_report):
        """Test summary-only generation"""
        output_path = temp_dir / "summary.json"
        
        generator = TestReportGenerator(sample_test_report)
        summary_path = generator.generate_summary_only(output_path)
        
        assert summary_path.exists()
        
        import json
        with open(summary_path) as f:
            summary = json.load(f)
        
        assert "summary" in summary
        assert summary["summary"]["total_tests"] == 3


class TestReportComparison:
    """Test report comparison"""
    
    def test_compare_reports(self, temp_dir, sample_test_report):
        """Test comparing two reports"""
        # Create baseline report
        baseline = sample_test_report
        
        # Create modified current report
        current = sample_test_report
        current.summary.passed = 2
        current.summary.failed = 0
        
        # Compare
        comparator = TestReportComparator(baseline, current)
        comparison = comparator.compare()
        
        # Verify comparison results
        assert "summary_changes" in comparison
        assert "test_changes" in comparison
        assert comparison["summary_changes"]["passed"]["delta"] == 1


class TestReportAnalysis:
    """Test report analysis"""
    
    def test_analyze_report(self, sample_test_report):
        """Test analyzing report"""
        analyzer = TestReportAnalyzer(sample_test_report)
        analysis = analyzer.analyze()
        
        # Verify analysis contains expected sections
        assert "quality_metrics" in analysis
        assert "test_health" in analysis
        assert "failure_analysis" in analysis
        assert "recommendations" in analysis
        
        # Check metrics
        metrics = analysis["quality_metrics"]
        assert "pass_rate" in metrics
        assert 0 <= metrics["pass_rate"] <= 1


class TestMultiFormatExport:
    """Test exporting to multiple formats"""
    
    def test_export_all_formats(self, temp_dir, sample_test_report):
        """Test exporting to all supported formats"""
        # JSON
        json_path = temp_dir / "report.json"
        sample_test_report.save(json_path)
        assert json_path.exists()
        
        # JUnit XML
        junit_path = temp_dir / "results.xml"
        generate_junit(sample_test_report, junit_path)
        assert junit_path.exists()
        
        # HTML
        html_path = temp_dir / "report.html"
        generate_html(sample_test_report, html_path)
        assert html_path.exists()
        
        # Verify all files were created
        assert len(list(temp_dir.glob("*"))) == 3


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
