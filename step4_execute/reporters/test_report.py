"""
Test report generation and management

Handles creation, validation, and manipulation of test execution reports.

Author: TB Eval Team
Version: 0.1.0
"""

import json
from pathlib import Path
from typing import Optional, Dict, Any, List, Set
from datetime import datetime
from dataclasses import asdict

from ..models import (
    TestReport,
    TestResult,
    TestOutcome,
    ExecutionStatus,
    TestSummary,
    CoverageInfo,
)


class TestReportGenerator:
    """
    Generates and enriches test reports
    
    Features:
    - Structured JSON generation
    - Schema validation
    - Report enrichment
    - Historical comparison
    """
    
    SCHEMA_VERSION = "1.0"
    
    def __init__(self, report: TestReport):
        """
        Initialize report generator
        
        Args:
            report: TestReport to generate from
        """
        self.report = report
    
    def generate(
        self,
        output_path: Path,
        pretty: bool = True,
        include_metadata: bool = True,
    ) -> Path:
        """
        Generate JSON report file
        
        Args:
            output_path: Where to save the report
            pretty: Whether to pretty-print JSON
            include_metadata: Whether to include detailed metadata
        
        Returns:
            Path to generated report
        """
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Build report dictionary
        report_dict = self._build_report_dict(include_metadata)
        
        # Write to file
        indent = 2 if pretty else None
        with open(output_path, 'w') as f:
            json.dump(report_dict, f, indent=indent, default=str)
        
        return output_path
    
    def _build_report_dict(self, include_metadata: bool) -> Dict[str, Any]:
        """
        Build report dictionary
        
        Args:
            include_metadata: Whether to include metadata
        
        Returns:
            Report dictionary
        """
        # Start with basic report
        report_dict = self.report.to_dict()
        
        # Add schema information
        report_dict["$schema"] = f"https://tbeval.org/schemas/test_report/v{self.SCHEMA_VERSION}"
        report_dict["generated_at"] = datetime.now().isoformat()
        
        # Add metadata if requested
        if include_metadata:
            report_dict["metadata"] = self._build_metadata()
        
        # Add convenience fields
        report_dict["summary"]["success"] = self.report.summary.passed == self.report.summary.total_tests
        report_dict["summary"]["has_failures"] = self.report.summary.failed > 0
        report_dict["summary"]["incomplete"] = self.report.summary.incomplete_tests > 0
        
        return report_dict
    
    def _build_metadata(self) -> Dict[str, Any]:
        """Build additional metadata"""
        return {
            "report_version": self.SCHEMA_VERSION,
            "generator": "TB Eval Framework Step 4",
            "generator_version": self.report.framework_version,
            "report_type": "test_execution",
            "schema_url": f"https://tbeval.org/schemas/test_report/v{self.SCHEMA_VERSION}.json",
        }
    
    def generate_summary_only(self, output_path: Path) -> Path:
        """
        Generate summary-only report (without individual test details)
        
        Args:
            output_path: Where to save summary
        
        Returns:
            Path to generated summary
        """
        summary_dict = {
            "schema_version": self.SCHEMA_VERSION,
            "timestamp": self.report.execution_metadata.timestamp,
            "status": self.report.status.value,
            "summary": self.report.summary.to_dict(),
            "coverage": {
                "files_count": len(self.report.coverage.files),
                "total_size_bytes": self.report.coverage.total_size_bytes,
                "primary_format": self.report.coverage.primary_format.value,
            },
            "exit_code": self.report.exit_code,
        }
        
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_path, 'w') as f:
            json.dump(summary_dict, f, indent=2)
        
        return output_path


class TestReportValidator:
    """
    Validates test report structure and content
    """
    
    REQUIRED_FIELDS = [
        "schema_version",
        "framework_version",
        "status",
        "summary",
        "results",
    ]
    
    REQUIRED_SUMMARY_FIELDS = [
        "total_tests",
        "completed_tests",
        "passed",
        "failed",
    ]
    
    REQUIRED_TEST_RESULT_FIELDS = [
        "name",
        "full_name",
        "outcome",
        "duration_ms",
    ]
    
    @classmethod
    def validate(cls, report_dict: Dict[str, Any]) -> tuple[bool, List[str]]:
        """
        Validate report structure
        
        Args:
            report_dict: Report dictionary
        
        Returns:
            Tuple of (is_valid, list_of_errors)
        """
        errors = []
        
        # Check required top-level fields
        for field in cls.REQUIRED_FIELDS:
            if field not in report_dict:
                errors.append(f"Missing required field: {field}")
        
        # Validate summary
        if "summary" in report_dict:
            summary = report_dict["summary"]
            for field in cls.REQUIRED_SUMMARY_FIELDS:
                if field not in summary:
                    errors.append(f"Missing required summary field: {field}")
            
            # Validate counts
            if "total_tests" in summary and "completed_tests" in summary:
                if summary["completed_tests"] > summary["total_tests"]:
                    errors.append("completed_tests cannot exceed total_tests")
            
            if "passed" in summary and "failed" in summary and "total_tests" in summary:
                if summary["passed"] + summary["failed"] > summary["total_tests"]:
                    errors.append("Sum of passed and failed exceeds total_tests")
        
        # Validate results
        if "results" in report_dict:
            results = report_dict["results"]
            if not isinstance(results, list):
                errors.append("results must be a list")
            else:
                for idx, result in enumerate(results):
                    for field in cls.REQUIRED_TEST_RESULT_FIELDS:
                        if field not in result:
                            errors.append(f"Result {idx}: missing field {field}")
                    
                    # Validate outcome
                    if "outcome" in result:
                        valid_outcomes = [o.value for o in TestOutcome]
                        if result["outcome"] not in valid_outcomes:
                            errors.append(f"Result {idx}: invalid outcome {result['outcome']}")
        
        # Validate schema version
        if "schema_version" in report_dict:
            try:
                version = float(report_dict["schema_version"])
                if version > 2.0:
                    errors.append(f"Unsupported schema version: {version}")
            except (ValueError, TypeError):
                errors.append(f"Invalid schema version format: {report_dict['schema_version']}")
        
        is_valid = len(errors) == 0
        return is_valid, errors
    
    @classmethod
    def validate_file(cls, report_path: Path) -> tuple[bool, List[str]]:
        """
        Validate report file
        
        Args:
            report_path: Path to report file
        
        Returns:
            Tuple of (is_valid, list_of_errors)
        """
        errors = []
        
        # Check file exists
        if not report_path.exists():
            return False, ["File does not exist"]
        
        # Try to parse JSON
        try:
            with open(report_path) as f:
                report_dict = json.load(f)
        except json.JSONDecodeError as e:
            return False, [f"Invalid JSON: {e}"]
        except Exception as e:
            return False, [f"Failed to read file: {e}"]
        
        # Validate structure
        return cls.validate(report_dict)


class TestReportLoader:
    """
    Loads test reports from files
    """
    
    @staticmethod
    def load(report_path: Path) -> TestReport:
        """
        Load test report from file
        
        Args:
            report_path: Path to report file
        
        Returns:
            TestReport object
        
        Raises:
            FileNotFoundError: If file doesn't exist
            ValueError: If report is invalid
        """
        if not report_path.exists():
            raise FileNotFoundError(f"Report not found: {report_path}")
        
        # Validate first
        is_valid, errors = TestReportValidator.validate_file(report_path)
        if not is_valid:
            raise ValueError(f"Invalid report: {', '.join(errors)}")
        
        # Load report
        return TestReport.load(report_path)
    
    @staticmethod
    def load_summary(report_path: Path) -> TestSummary:
        """
        Load only summary from report
        
        Args:
            report_path: Path to report file
        
        Returns:
            TestSummary object
        """
        with open(report_path) as f:
            report_dict = json.load(f)
        
        summary_dict = report_dict.get("summary", {})
        
        return TestSummary(
            total_tests=summary_dict.get("total_tests", 0),
            completed_tests=summary_dict.get("completed_tests", 0),
            passed=summary_dict.get("passed", 0),
            failed=summary_dict.get("failed", 0),
            errors=summary_dict.get("errors", 0),
            skipped=summary_dict.get("skipped", 0),
            timeout=summary_dict.get("timeout", 0),
            crashed=summary_dict.get("crashed", 0),
            flaky=summary_dict.get("flaky", 0),
            total_duration_ms=summary_dict.get("total_duration_ms", 0.0),
            average_duration_ms=summary_dict.get("average_duration_ms", 0.0),
        )


class TestReportComparator:
    """
    Compares test reports to identify changes
    """
    
    def __init__(self, baseline_report: TestReport, current_report: TestReport):
        """
        Initialize comparator
        
        Args:
            baseline_report: Baseline report (e.g., previous run)
            current_report: Current report
        """
        self.baseline = baseline_report
        self.current = current_report
    
    def compare(self) -> Dict[str, Any]:
        """
        Compare reports
        
        Returns:
            Dictionary with comparison results
        """
        return {
            "summary_changes": self._compare_summaries(),
            "test_changes": self._compare_tests(),
            "new_failures": self._find_new_failures(),
            "fixed_tests": self._find_fixed_tests(),
            "new_tests": self._find_new_tests(),
            "removed_tests": self._find_removed_tests(),
            "flaky_tests": self._find_flaky_tests(),
            "performance_changes": self._compare_performance(),
        }
    
    def _compare_summaries(self) -> Dict[str, Any]:
        """Compare summary statistics"""
        baseline_sum = self.baseline.summary
        current_sum = self.current.summary
        
        return {
            "total_tests": {
                "baseline": baseline_sum.total_tests,
                "current": current_sum.total_tests,
                "delta": current_sum.total_tests - baseline_sum.total_tests,
            },
            "passed": {
                "baseline": baseline_sum.passed,
                "current": current_sum.passed,
                "delta": current_sum.passed - baseline_sum.passed,
            },
            "failed": {
                "baseline": baseline_sum.failed,
                "current": current_sum.failed,
                "delta": current_sum.failed - baseline_sum.failed,
            },
            "success_rate": {
                "baseline": baseline_sum.success_rate,
                "current": current_sum.success_rate,
                "delta": current_sum.success_rate - baseline_sum.success_rate,
            },
            "duration_ms": {
                "baseline": baseline_sum.total_duration_ms,
                "current": current_sum.total_duration_ms,
                "delta": current_sum.total_duration_ms - baseline_sum.total_duration_ms,
                "percent_change": self._percent_change(
                    baseline_sum.total_duration_ms,
                    current_sum.total_duration_ms
                ),
            },
        }
    
    def _compare_tests(self) -> Dict[str, Any]:
        """Compare individual tests"""
        baseline_tests = {r.full_name: r for r in self.baseline.results}
        current_tests = {r.full_name: r for r in self.current.results}
        
        common_tests = set(baseline_tests.keys()) & set(current_tests.keys())
        
        changes = []
        for test_name in common_tests:
            baseline_test = baseline_tests[test_name]
            current_test = current_tests[test_name]
            
            if baseline_test.outcome != current_test.outcome:
                changes.append({
                    "test": test_name,
                    "baseline_outcome": baseline_test.outcome.value,
                    "current_outcome": current_test.outcome.value,
                    "changed_from": baseline_test.outcome.value,
                    "changed_to": current_test.outcome.value,
                })
        
        return {
            "total_changes": len(changes),
            "changes": changes,
        }
    
    def _find_new_failures(self) -> List[str]:
        """Find tests that newly failed"""
        baseline_tests = {r.full_name: r for r in self.baseline.results}
        current_tests = {r.full_name: r for r in self.current.results}
        
        new_failures = []
        for test_name, current_test in current_tests.items():
            if current_test.outcome.is_failure:
                baseline_test = baseline_tests.get(test_name)
                if baseline_test and baseline_test.outcome.is_success:
                    new_failures.append(test_name)
        
        return new_failures
    
    def _find_fixed_tests(self) -> List[str]:
        """Find tests that were fixed"""
        baseline_tests = {r.full_name: r for r in self.baseline.results}
        current_tests = {r.full_name: r for r in self.current.results}
        
        fixed = []
        for test_name, current_test in current_tests.items():
            if current_test.outcome.is_success:
                baseline_test = baseline_tests.get(test_name)
                if baseline_test and baseline_test.outcome.is_failure:
                    fixed.append(test_name)
        
        return fixed
    
    def _find_new_tests(self) -> List[str]:
        """Find newly added tests"""
        baseline_names = {r.full_name for r in self.baseline.results}
        current_names = {r.full_name for r in self.current.results}
        
        return list(current_names - baseline_names)
    
    def _find_removed_tests(self) -> List[str]:
        """Find removed tests"""
        baseline_names = {r.full_name for r in self.baseline.results}
        current_names = {r.full_name for r in self.current.results}
        
        return list(baseline_names - current_names)
    
    def _find_flaky_tests(self) -> List[str]:
        """Find potentially flaky tests"""
        # Tests that are marked flaky in either report
        flaky = []
        
        for result in self.current.results:
            if result.flaky:
                flaky.append(result.full_name)
        
        for result in self.baseline.results:
            if result.flaky and result.full_name not in flaky:
                flaky.append(result.full_name)
        
        return flaky
    
    def _compare_performance(self) -> Dict[str, Any]:
        """Compare performance metrics"""
        baseline_tests = {r.full_name: r for r in self.baseline.results}
        current_tests = {r.full_name: r for r in self.current.results}
        
        common_tests = set(baseline_tests.keys()) & set(current_tests.keys())
        
        slower_tests = []
        faster_tests = []
        
        for test_name in common_tests:
            baseline_duration = baseline_tests[test_name].duration_ms
            current_duration = current_tests[test_name].duration_ms
            
            if baseline_duration > 0:
                change = self._percent_change(baseline_duration, current_duration)
                
                if change > 10:  # More than 10% slower
                    slower_tests.append({
                        "test": test_name,
                        "baseline_ms": baseline_duration,
                        "current_ms": current_duration,
                        "percent_change": change,
                    })
                elif change < -10:  # More than 10% faster
                    faster_tests.append({
                        "test": test_name,
                        "baseline_ms": baseline_duration,
                        "current_ms": current_duration,
                        "percent_change": change,
                    })
        
        return {
            "slower_tests": sorted(slower_tests, key=lambda x: x["percent_change"], reverse=True),
            "faster_tests": sorted(faster_tests, key=lambda x: x["percent_change"]),
        }
    
    @staticmethod
    def _percent_change(baseline: float, current: float) -> float:
        """Calculate percent change"""
        if baseline == 0:
            return 0.0
        return ((current - baseline) / baseline) * 100


class TestReportAnalyzer:
    """
    Analyzes test reports for insights
    """
    
    def __init__(self, report: TestReport):
        """
        Initialize analyzer
        
        Args:
            report: TestReport to analyze
        """
        self.report = report
    
    def analyze(self) -> Dict[str, Any]:
        """
        Perform comprehensive analysis
        
        Returns:
            Analysis results
        """
        return {
            "quality_metrics": self._calculate_quality_metrics(),
            "test_health": self._assess_test_health(),
            "failure_analysis": self._analyze_failures(),
            "performance_analysis": self._analyze_performance(),
            "coverage_analysis": self._analyze_coverage(),
            "recommendations": self._generate_recommendations(),
        }
    
    def _calculate_quality_metrics(self) -> Dict[str, Any]:
        """Calculate quality metrics"""
        summary = self.report.summary
        
        return {
            "pass_rate": summary.success_rate,
            "completion_rate": summary.completed_tests / summary.total_tests if summary.total_tests > 0 else 0,
            "failure_rate": summary.failed / summary.total_tests if summary.total_tests > 0 else 0,
            "error_rate": summary.errors / summary.total_tests if summary.total_tests > 0 else 0,
            "flaky_rate": summary.flaky / summary.completed_tests if summary.completed_tests > 0 else 0,
            "timeout_rate": summary.timeout / summary.total_tests if summary.total_tests > 0 else 0,
        }
    
    def _assess_test_health(self) -> Dict[str, Any]:
        """Assess overall test health"""
        metrics = self._calculate_quality_metrics()
        
        # Determine health status
        if metrics["pass_rate"] >= 0.95 and metrics["flaky_rate"] < 0.05:
            health = "excellent"
        elif metrics["pass_rate"] >= 0.80:
            health = "good"
        elif metrics["pass_rate"] >= 0.60:
            health = "fair"
        else:
            health = "poor"
        
        return {
            "status": health,
            "pass_rate": metrics["pass_rate"],
            "issues": self._identify_health_issues(metrics),
        }
    
    def _identify_health_issues(self, metrics: Dict[str, float]) -> List[str]:
        """Identify health issues"""
        issues = []
        
        if metrics["pass_rate"] < 0.80:
            issues.append("Low pass rate")
        
        if metrics["flaky_rate"] > 0.10:
            issues.append("High flaky test rate")
        
        if metrics["timeout_rate"] > 0.05:
            issues.append("High timeout rate")
        
        if metrics["error_rate"] > 0.05:
            issues.append("High error rate")
        
        if metrics["completion_rate"] < 0.95:
            issues.append("Tests not completing")
        
        return issues
    
    def _analyze_failures(self) -> Dict[str, Any]:
        """Analyze failure patterns"""
        failed_tests = self.report.get_failed_tests()
        errored_tests = self.report.get_errored_tests()
        
        # Group by error message
        failure_groups = {}
        for test in failed_tests + errored_tests:
            if test.message:
                # Simplify message for grouping
                key = test.message[:50]
                if key not in failure_groups:
                    failure_groups[key] = []
                failure_groups[key].append(test.full_name)
        
        return {
            "total_failures": len(failed_tests) + len(errored_tests),
            "unique_failure_types": len(failure_groups),
            "failure_groups": [
                {"message": msg, "count": len(tests), "tests": tests[:5]}
                for msg, tests in sorted(failure_groups.items(), key=lambda x: len(x[1]), reverse=True)
            ],
        }
    
    def _analyze_performance(self) -> Dict[str, Any]:
        """Analyze performance metrics"""
        results = self.report.results
        
        if not results:
            return {}
        
        durations = [r.duration_ms for r in results]
        durations.sort()
        
        return {
            "total_duration_ms": self.report.summary.total_duration_ms,
            "average_duration_ms": self.report.summary.average_duration_ms,
            "median_duration_ms": durations[len(durations) // 2],
            "min_duration_ms": min(durations),
            "max_duration_ms": max(durations),
            "slowest_tests": [
                {"name": r.full_name, "duration_ms": r.duration_ms}
                for r in sorted(results, key=lambda x: x.duration_ms, reverse=True)[:5]
            ],
        }
    
    def _analyze_coverage(self) -> Dict[str, Any]:
        """Analyze coverage collection"""
        return {
            "enabled": self.report.coverage.files is not None and len(self.report.coverage.files) > 0,
            "file_count": len(self.report.coverage.files),
            "total_size_bytes": self.report.coverage.total_size_bytes,
            "per_test": self.report.coverage.per_test,
            "format": self.report.coverage.primary_format.value,
            "valid_files": len(self.report.coverage.valid_files),
        }
    
    def _generate_recommendations(self) -> List[str]:
        """Generate recommendations based on analysis"""
        recommendations = []
        
        metrics = self._calculate_quality_metrics()
        
        # Pass rate recommendations
        if metrics["pass_rate"] < 0.80:
            recommendations.append("Investigate and fix failing tests to improve pass rate")
        
        # Flaky test recommendations
        if metrics["flaky_rate"] > 0.10:
            recommendations.append("Address flaky tests - consider increasing timeouts or fixing race conditions")
        
        # Timeout recommendations
        if metrics["timeout_rate"] > 0.05:
            recommendations.append("Review test timeouts - some tests may need longer execution time")
        
        # Performance recommendations
        perf = self._analyze_performance()
        if perf and perf["max_duration_ms"] > 300000:  # 5 minutes
            recommendations.append("Some tests are very slow - consider optimization or splitting")
        
        # Coverage recommendations
        cov = self._analyze_coverage()
        if not cov["enabled"]:
            recommendations.append("Enable coverage collection for better code quality metrics")
        
        return recommendations


# Utility functions

def generate_report(report: TestReport, output_path: Path) -> Path:
    """
    Convenience function to generate report
    
    Args:
        report: TestReport to generate from
        output_path: Output file path
    
    Returns:
        Path to generated report
    """
    generator = TestReportGenerator(report)
    return generator.generate(output_path)


def validate_report(report_path: Path) -> tuple[bool, List[str]]:
    """
    Convenience function to validate report
    
    Args:
        report_path: Path to report file
    
    Returns:
        Tuple of (is_valid, list_of_errors)
    """
    return TestReportValidator.validate_file(report_path)


def compare_reports(
    baseline_path: Path,
    current_path: Path
) -> Dict[str, Any]:
    """
    Convenience function to compare reports
    
    Args:
        baseline_path: Path to baseline report
        current_path: Path to current report
    
    Returns:
        Comparison results
    """
    baseline = TestReportLoader.load(baseline_path)
    current = TestReportLoader.load(current_path)
    
    comparator = TestReportComparator(baseline, current)
    return comparator.compare()


def analyze_report(report_path: Path) -> Dict[str, Any]:
    """
    Convenience function to analyze report
    
    Args:
        report_path: Path to report file
    
    Returns:
        Analysis results
    """
    report = TestReportLoader.load(report_path)
    analyzer = TestReportAnalyzer(report)
    return analyzer.analyze()


# Example usage and testing
if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("Usage:")
        print("  python test_report.py validate <report.json>")
        print("  python test_report.py analyze <report.json>")
        print("  python test_report.py compare <baseline.json> <current.json>")
        sys.exit(1)
    
    command = sys.argv[1]
    
    if command == "validate":
        report_path = Path(sys.argv[2])
        is_valid, errors = validate_report(report_path)
        
        if is_valid:
            print("✓ Report is valid")
        else:
            print("✗ Report has errors:")
            for error in errors:
                print(f"  - {error}")
            sys.exit(1)
    
    elif command == "analyze":
        report_path = Path(sys.argv[2])
        analysis = analyze_report(report_path)
        
        print("Report Analysis")
        print("=" * 60)
        
        # Quality metrics
        metrics = analysis["quality_metrics"]
        print(f"\nQuality Metrics:")
        print(f"  Pass rate:       {metrics['pass_rate']*100:.1f}%")
        print(f"  Completion rate: {metrics['completion_rate']*100:.1f}%")
        print(f"  Flaky rate:      {metrics['flaky_rate']*100:.1f}%")
        
        # Test health
        health = analysis["test_health"]
        print(f"\nTest Health: {health['status'].upper()}")
        if health["issues"]:
            print("  Issues:")
            for issue in health["issues"]:
                print(f"    - {issue}")
        
        # Recommendations
        if analysis["recommendations"]:
            print("\nRecommendations:")
            for rec in analysis["recommendations"]:
                print(f"  • {rec}")
    
    elif command == "compare":
        baseline_path = Path(sys.argv[2])
        current_path = Path(sys.argv[3])
        
        comparison = compare_reports(baseline_path, current_path)
        
        print("Report Comparison")
        print("=" * 60)
        
        # Summary changes
        summary = comparison["summary_changes"]
        print(f"\nPassed: {summary['passed']['baseline']} → {summary['passed']['current']} (Δ{summary['passed']['delta']:+d})")
        print(f"Failed: {summary['failed']['baseline']} → {summary['failed']['current']} (Δ{summary['failed']['delta']:+d})")
        
        # New failures
        if comparison["new_failures"]:
            print(f"\n✗ New Failures ({len(comparison['new_failures'])}):")
            for test in comparison["new_failures"][:5]:
                print(f"  - {test}")
        
        # Fixed tests
        if comparison["fixed_tests"]:
            print(f"\n✓ Fixed Tests ({len(comparison['fixed_tests'])}):")
            for test in comparison["fixed_tests"][:5]:
                print(f"  - {test}")
        
        # Performance
        perf = comparison["performance_changes"]
        if perf["slower_tests"]:
            print(f"\n⚠ Slower Tests:")
            for test in perf["slower_tests"][:3]:
                print(f"  - {test['test']}: {test['percent_change']:+.1f}%")
