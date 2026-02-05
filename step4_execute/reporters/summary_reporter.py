"""
Human-readable summary reporter

Generates formatted console and text summaries of test execution results.

Author: TB Eval Team
Version: 0.1.0
"""

from pathlib import Path
from typing import Optional, List, Dict, Any, TextIO
import sys
from datetime import datetime
from enum import Enum

from ..models import TestReport, TestResult, TestOutcome
from ..handlers.output_handler import OutputFormatter, ColorCode


class SummaryFormat(Enum):
    """Summary output format"""
    CONSOLE = "console"      # Colored console output
    TEXT = "text"           # Plain text
    MARKDOWN = "markdown"   # Markdown format


class SummaryVerbosity(Enum):
    """Summary verbosity level"""
    MINIMAL = "minimal"     # Just counts and pass/fail
    NORMAL = "normal"       # Standard summary
    DETAILED = "detailed"   # Include all test details
    FULL = "full"          # Everything including diagnostics


class SummaryReporter:
    """
    Generates human-readable test summaries
    
    Features:
    - Multiple output formats (console, text, markdown)
    - Configurable verbosity
    - Colored output for terminals
    - Performance metrics
    - Failure details
    - Coverage summary
    """
    
    def __init__(
        self,
        report: TestReport,
        format: SummaryFormat = SummaryFormat.CONSOLE,
        verbosity: SummaryVerbosity = SummaryVerbosity.NORMAL,
    ):
        """
        Initialize summary reporter
        
        Args:
            report: TestReport to summarize
            format: Output format
            verbosity: Verbosity level
        """
        self.report = report
        self.format = format
        self.verbosity = verbosity
        self.formatter = OutputFormatter(use_color=(format == SummaryFormat.CONSOLE))
    
    def generate(self, output: Optional[TextIO] = None) -> str:
        """
        Generate summary
        
        Args:
            output: Optional output stream (default: stdout)
        
        Returns:
            Summary string
        """
        if output is None:
            output = sys.stdout
        
        # Build summary sections
        sections = []
        
        # Header
        sections.append(self._generate_header())
        
        # Overview
        sections.append(self._generate_overview())
        
        # Test results summary
        if self.verbosity != SummaryVerbosity.MINIMAL:
            sections.append(self._generate_results_summary())
        
        # Failed tests details
        if self.verbosity in [SummaryVerbosity.DETAILED, SummaryVerbosity.FULL]:
            failed_section = self._generate_failed_tests()
            if failed_section:
                sections.append(failed_section)
        
        # Performance summary
        if self.verbosity in [SummaryVerbosity.NORMAL, SummaryVerbosity.DETAILED, SummaryVerbosity.FULL]:
            sections.append(self._generate_performance_summary())
        
        # Coverage summary
        if self.report.coverage.files and self.verbosity != SummaryVerbosity.MINIMAL:
            sections.append(self._generate_coverage_summary())
        
        # Diagnostics
        if self.verbosity == SummaryVerbosity.FULL:
            diag_section = self._generate_diagnostics()
            if diag_section:
                sections.append(diag_section)
        
        # Footer
        sections.append(self._generate_footer())
        
        # Join sections
        summary = "\n\n".join(filter(None, sections))
        
        # Write to output
        output.write(summary)
        output.write("\n")
        
        return summary
    
    def _generate_header(self) -> str:
        """Generate report header"""
        if self.format == SummaryFormat.MARKDOWN:
            return f"# Test Execution Summary\n\n**Date:** {self.report.execution_metadata.timestamp}"
        
        lines = []
        separator = "=" * 70
        
        lines.append(self._style(separator, "bold"))
        lines.append(self._style("TEST EXECUTION SUMMARY", "bold"))
        lines.append(self._style(separator, "bold"))
        
        # Add timestamp
        if self.report.execution_metadata:
            timestamp = datetime.fromisoformat(self.report.execution_metadata.timestamp)
            lines.append(self._style(f"Date: {timestamp.strftime('%Y-%m-%d %H:%M:%S')}", "dim"))
        
        return "\n".join(lines)
    
    def _generate_overview(self) -> str:
        """Generate overview section"""
        summary = self.report.summary
        
        if self.format == SummaryFormat.MARKDOWN:
            return self._generate_overview_markdown()
        
        lines = []
        lines.append(self._style("Overview", "bold"))
        lines.append(self._style("─" * 70, "dim"))
        
        # Status
        status_str = self._format_status(self.report.status.value)
        lines.append(f"Status:          {status_str}")
        
        # Test counts
        lines.append(f"Total Tests:     {summary.total_tests}")
        lines.append(f"Completed:       {summary.completed_tests}")
        
        if summary.passed > 0:
            lines.append(f"Passed:          {self._style(str(summary.passed), 'success')}")
        
        if summary.failed > 0:
            lines.append(f"Failed:          {self._style(str(summary.failed), 'error')}")
        
        if summary.errors > 0:
            lines.append(f"Errors:          {self._style(str(summary.errors), 'error')}")
        
        if summary.skipped > 0:
            lines.append(f"Skipped:         {self._style(str(summary.skipped), 'warning')}")
        
        if summary.timeout > 0:
            lines.append(f"Timeout:         {self._style(str(summary.timeout), 'warning')}")
        
        if summary.flaky > 0:
            lines.append(f"Flaky:           {self._style(str(summary.flaky), 'warning')}")
        
        # Success rate
        success_rate = summary.success_rate * 100
        rate_str = self._format_percentage(success_rate)
        lines.append(f"Success Rate:    {rate_str}")
        
        # Duration
        duration = self._format_duration(summary.total_duration_ms)
        lines.append(f"Total Duration:  {duration}")
        
        return "\n".join(lines)
    
    def _generate_overview_markdown(self) -> str:
        """Generate overview in markdown format"""
        summary = self.report.summary
        
        lines = ["## Overview", ""]
        lines.append("| Metric | Value |")
        lines.append("|--------|-------|")
        lines.append(f"| Status | {self.report.status.value} |")
        lines.append(f"| Total Tests | {summary.total_tests} |")
        lines.append(f"| Completed | {summary.completed_tests} |")
        lines.append(f"| Passed | {summary.passed} |")
        lines.append(f"| Failed | {summary.failed} |")
        lines.append(f"| Success Rate | {summary.success_rate*100:.1f}% |")
        lines.append(f"| Duration | {self._format_duration(summary.total_duration_ms)} |")
        
        return "\n".join(lines)
    
    def _generate_results_summary(self) -> str:
        """Generate results breakdown by outcome"""
        if self.format == SummaryFormat.MARKDOWN:
            return self._generate_results_markdown()
        
        lines = []
        lines.append(self._style("Test Results", "bold"))
        lines.append(self._style("─" * 70, "dim"))
        
        # Group tests by outcome
        by_outcome = {}
        for result in self.report.results:
            outcome = result.outcome
            if outcome not in by_outcome:
                by_outcome[outcome] = []
            by_outcome[outcome].append(result)
        
        # Display counts
        for outcome in TestOutcome:
            if outcome in by_outcome:
                tests = by_outcome[outcome]
                count = len(tests)
                
                symbol = outcome.symbol
                name = outcome.value.capitalize()
                
                # Style based on outcome
                if outcome in [TestOutcome.PASSED]:
                    line = f"{self._style(symbol, 'success')} {name}: {count}"
                elif outcome in [TestOutcome.FAILED, TestOutcome.ERROR]:
                    line = f"{self._style(symbol, 'error')} {name}: {count}"
                else:
                    line = f"{self._style(symbol, 'warning')} {name}: {count}"
                
                lines.append(line)
                
                # List test names if detailed
                if self.verbosity in [SummaryVerbosity.DETAILED, SummaryVerbosity.FULL]:
                    for test in tests[:10]:  # Limit to 10
                        lines.append(f"  {self._style('•', 'dim')} {test.full_name}")
                    
                    if len(tests) > 10:
                        lines.append(f"  {self._style(f'... and {len(tests) - 10} more', 'dim')}")
        
        return "\n".join(lines)
    
    def _generate_results_markdown(self) -> str:
        """Generate results in markdown format"""
        lines = ["## Test Results", ""]
        
        # Group by outcome
        by_outcome = {}
        for result in self.report.results:
            outcome = result.outcome
            if outcome not in by_outcome:
                by_outcome[outcome] = []
            by_outcome[outcome].append(result)
        
        for outcome, tests in sorted(by_outcome.items(), key=lambda x: len(x[1]), reverse=True):
            lines.append(f"### {outcome.value.capitalize()} ({len(tests)})")
            lines.append("")
            
            if self.verbosity in [SummaryVerbosity.DETAILED, SummaryVerbosity.FULL]:
                for test in tests[:20]:
                    duration = self._format_duration(test.duration_ms)
                    lines.append(f"- `{test.full_name}` ({duration})")
                
                if len(tests) > 20:
                    lines.append(f"- *... and {len(tests) - 20} more*")
            
            lines.append("")
        
        return "\n".join(lines)
    
    def _generate_failed_tests(self) -> Optional[str]:
        """Generate detailed failure information"""
        failed = self.report.get_failed_tests()
        errored = self.report.get_errored_tests()
        
        if not failed and not errored:
            return None
        
        if self.format == SummaryFormat.MARKDOWN:
            return self._generate_failed_tests_markdown(failed, errored)
        
        lines = []
        lines.append(self._style("Failed Tests Details", "bold"))
        lines.append(self._style("─" * 70, "dim"))
        
        # Failed tests
        if failed:
            lines.append(self._style(f"Failures ({len(failed)}):", "error"))
            for test in failed[:10]:  # Limit to 10
                lines.append("")
                lines.append(f"  {self._style('✗', 'error')} {self._style(test.full_name, 'bold')}")
                
                if test.duration_ms:
                    duration = self._format_duration(test.duration_ms)
                    lines.append(f"     Duration: {duration}")
                
                if test.message:
                    # Truncate long messages
                    message = test.message[:200]
                    if len(test.message) > 200:
                        message += "..."
                    lines.append(f"     {self._style('Message:', 'dim')} {message}")
                
                if test.artifacts.log_file:
                    lines.append(f"     {self._style('Log:', 'dim')} {test.artifacts.log_file}")
            
            if len(failed) > 10:
                lines.append(f"\n  {self._style(f'... and {len(failed) - 10} more failures', 'dim')}")
        
        # Errored tests
        if errored:
            lines.append("")
            lines.append(self._style(f"Errors ({len(errored)}):", "error"))
            for test in errored[:5]:
                lines.append("")
                lines.append(f"  {self._style('⚠', 'error')} {self._style(test.full_name, 'bold')}")
                
                if test.message:
                    message = test.message[:200]
                    if len(test.message) > 200:
                        message += "..."
                    lines.append(f"     {self._style('Error:', 'dim')} {message}")
        
        return "\n".join(lines)
    
    def _generate_failed_tests_markdown(
        self,
        failed: List[TestResult],
        errored: List[TestResult]
    ) -> str:
        """Generate failed tests in markdown format"""
        lines = ["## Failed Tests", ""]
        
        if failed:
            lines.append(f"### Failures ({len(failed)})")
            lines.append("")
            
            for test in failed[:10]:
                lines.append(f"#### {test.full_name}")
                lines.append("")
                lines.append(f"- **Duration:** {self._format_duration(test.duration_ms)}")
                
                if test.message:
                    lines.append(f"- **Message:** {test.message[:200]}")
                
                if test.traceback:
                    lines.append("- **Traceback:**")
                    lines.append("```")
                    lines.append(test.traceback[:500])
                    lines.append("```")
                
                lines.append("")
        
        if errored:
            lines.append(f"### Errors ({len(errored)})")
            lines.append("")
            
            for test in errored[:5]:
                lines.append(f"- **{test.full_name}:** {test.message[:100] if test.message else 'Unknown error'}")
        
        return "\n".join(lines)
    
    def _generate_performance_summary(self) -> str:
        """Generate performance metrics"""
        summary = self.report.summary
        
        if self.format == SummaryFormat.MARKDOWN:
            return self._generate_performance_markdown()
        
        lines = []
        lines.append(self._style("Performance", "bold"))
        lines.append(self._style("─" * 70, "dim"))
        
        # Total and average
        total_duration = self._format_duration(summary.total_duration_ms)
        avg_duration = self._format_duration(summary.average_duration_ms)
        
        lines.append(f"Total Duration:   {total_duration}")
        lines.append(f"Average per Test: {avg_duration}")
        
        # Find slowest tests
        if self.report.results:
            slowest = sorted(self.report.results, key=lambda x: x.duration_ms, reverse=True)[:5]
            
            if slowest and self.verbosity in [SummaryVerbosity.DETAILED, SummaryVerbosity.FULL]:
                lines.append("")
                lines.append(self._style("Slowest Tests:", "dim"))
                
                for i, test in enumerate(slowest, 1):
                    duration = self._format_duration(test.duration_ms)
                    lines.append(f"  {i}. {test.full_name} ({duration})")
        
        return "\n".join(lines)
    
    def _generate_performance_markdown(self) -> str:
        """Generate performance in markdown"""
        summary = self.report.summary
        
        lines = ["## Performance", ""]
        lines.append(f"- **Total Duration:** {self._format_duration(summary.total_duration_ms)}")
        lines.append(f"- **Average per Test:** {self._format_duration(summary.average_duration_ms)}")
        
        # Slowest tests
        if self.report.results:
            slowest = sorted(self.report.results, key=lambda x: x.duration_ms, reverse=True)[:5]
            
            if slowest:
                lines.append("")
                lines.append("### Slowest Tests")
                lines.append("")
                
                for i, test in enumerate(slowest, 1):
                    duration = self._format_duration(test.duration_ms)
                    lines.append(f"{i}. `{test.full_name}` - {duration}")
        
        return "\n".join(lines)
    
    def _generate_coverage_summary(self) -> str:
        """Generate coverage summary"""
        coverage = self.report.coverage
        
        if self.format == SummaryFormat.MARKDOWN:
            return self._generate_coverage_markdown()
        
        lines = []
        lines.append(self._style("Coverage", "bold"))
        lines.append(self._style("─" * 70, "dim"))
        
        lines.append(f"Files Collected:  {len(coverage.files)}")
        lines.append(f"Format:           {coverage.primary_format.value}")
        lines.append(f"Per-Test:         {'Yes' if coverage.per_test else 'No'}")
        
        # Total size
        size_mb = coverage.total_size_bytes / (1024 * 1024)
        lines.append(f"Total Size:       {size_mb:.2f} MB")
        
        # Valid files
        valid = len(coverage.valid_files)
        if valid < len(coverage.files):
            lines.append(f"Valid Files:      {self._style(str(valid), 'warning')} / {len(coverage.files)}")
        else:
            lines.append(f"Valid Files:      {valid} / {len(coverage.files)}")
        
        return "\n".join(lines)
    
    def _generate_coverage_markdown(self) -> str:
        """Generate coverage in markdown"""
        coverage = self.report.coverage
        
        lines = ["## Coverage", ""]
        lines.append(f"- **Files Collected:** {len(coverage.files)}")
        lines.append(f"- **Format:** {coverage.primary_format.value}")
        lines.append(f"- **Per-Test Coverage:** {'Yes' if coverage.per_test else 'No'}")
        
        size_mb = coverage.total_size_bytes / (1024 * 1024)
        lines.append(f"- **Total Size:** {size_mb:.2f} MB")
        
        return "\n".join(lines)
    
    def _generate_diagnostics(self) -> Optional[str]:
        """Generate diagnostics section"""
        diag = self.report.diagnostics
        
        if not diag.errors and not diag.warnings:
            return None
        
        if self.format == SummaryFormat.MARKDOWN:
            return self._generate_diagnostics_markdown()
        
        lines = []
        lines.append(self._style("Diagnostics", "bold"))
        lines.append(self._style("─" * 70, "dim"))
        
        # Errors
        if diag.errors:
            lines.append(self._style(f"Errors ({len(diag.errors)}):", "error"))
            for error in diag.errors[:10]:
                lines.append(f"  {self._style('✗', 'error')} {error}")
            
            if len(diag.errors) > 10:
                lines.append(f"  {self._style(f'... and {len(diag.errors) - 10} more', 'dim')}")
        
        # Warnings
        if diag.warnings:
            if diag.errors:
                lines.append("")
            
            lines.append(self._style(f"Warnings ({len(diag.warnings)}):", "warning"))
            for warning in diag.warnings[:10]:
                lines.append(f"  {self._style('⚠', 'warning')} {warning}")
            
            if len(diag.warnings) > 10:
                lines.append(f"  {self._style(f'... and {len(diag.warnings) - 10} more', 'dim')}")
        
        return "\n".join(lines)
    
    def _generate_diagnostics_markdown(self) -> str:
        """Generate diagnostics in markdown"""
        diag = self.report.diagnostics
        
        lines = ["## Diagnostics", ""]
        
        if diag.errors:
            lines.append(f"### Errors ({len(diag.errors)})")
            lines.append("")
            for error in diag.errors[:10]:
                lines.append(f"- {error}")
            lines.append("")
        
        if diag.warnings:
            lines.append(f"### Warnings ({len(diag.warnings)})")
            lines.append("")
            for warning in diag.warnings[:10]:
                lines.append(f"- {warning}")
        
        return "\n".join(lines)
    
    def _generate_footer(self) -> str:
        """Generate footer"""
        if self.format == SummaryFormat.MARKDOWN:
            lines = ["---", ""]
            lines.append(f"Generated by TB Eval Framework v{self.report.framework_version}")
            return "\n".join(lines)
        
        lines = []
        lines.append(self._style("─" * 70, "dim"))
        
        # Exit code
        exit_code_str = self._format_exit_code(self.report.exit_code)
        lines.append(f"Exit Code: {exit_code_str}")
        
        # Report location
        if self.report.artifacts_root:
            report_file = Path(self.report.artifacts_root) / "test_report.json"
            lines.append(f"Report:    {self._style(str(report_file), 'dim')}")
        
        lines.append(self._style("=" * 70, "bold"))
        
        return "\n".join(lines)
    
    def _style(self, text: str, style: str) -> str:
        """Apply style to text"""
        if self.format != SummaryFormat.CONSOLE:
            return text
        
        style_map = {
            "bold": self.formatter.bold,
            "dim": self.formatter.dim,
            "success": self.formatter.success,
            "error": self.formatter.error,
            "warning": self.formatter.warning,
            "info": self.formatter.info,
        }
        
        style_func = style_map.get(style, lambda x: x)
        return style_func(text)
    
    def _format_status(self, status: str) -> str:
        """Format status with color"""
        status_upper = status.upper()
        
        if status in ["completed"]:
            return self._style(status_upper, "success")
        elif status in ["running", "partial"]:
            return self._style(status_upper, "warning")
        elif status in ["error", "cancelled"]:
            return self._style(status_upper, "error")
        else:
            return status_upper
    
    def _format_percentage(self, percentage: float) -> str:
        """Format percentage with color"""
        text = f"{percentage:.1f}%"
        
        if percentage >= 95:
            return self._style(text, "success")
        elif percentage >= 80:
            return self._style(text, "warning")
        else:
            return self._style(text, "error")
    
    def _format_duration(self, duration_ms: float) -> str:
        """Format duration"""
        return self.formatter.format_duration(duration_ms)
    
    def _format_exit_code(self, exit_code: int) -> str:
        """Format exit code with color"""
        text = str(exit_code)
        
        if exit_code == 0:
            return self._style(f"{text} (Success)", "success")
        elif exit_code == 30:
            return self._style(f"{text} (Cancelled)", "warning")
        else:
            return self._style(f"{text} (Failure)", "error")
    
    def save(self, output_path: Path) -> Path:
        """
        Save summary to file
        
        Args:
            output_path: Where to save summary
        
        Returns:
            Path to saved file
        """
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_path, 'w') as f:
            self.generate(f)
        
        return output_path


class CompactSummaryReporter:
    """
    Generates compact one-line summaries
    
    Useful for CI/CD logs or status lines.
    """
    
    def __init__(self, report: TestReport):
        """
        Initialize compact reporter
        
        Args:
            report: TestReport to summarize
        """
        self.report = report
        self.formatter = OutputFormatter(use_color=True)
    
    def generate(self) -> str:
        """
        Generate compact one-line summary
        
        Returns:
            One-line summary string
        """
        summary = self.report.summary
        
        # Build status parts
        parts = []
        
        # Pass/Fail counts
        if summary.passed > 0:
            parts.append(self.formatter.success(f"{summary.passed} passed"))
        
        if summary.failed > 0:
            parts.append(self.formatter.error(f"{summary.failed} failed"))
        
        if summary.errors > 0:
            parts.append(self.formatter.error(f"{summary.errors} errors"))
        
        if summary.skipped > 0:
            parts.append(self.formatter.warning(f"{summary.skipped} skipped"))
        
        # Duration
        duration = self.formatter.format_duration(summary.total_duration_ms)
        parts.append(self.formatter.dim(f"in {duration}"))
        
        # Join parts
        summary_line = ", ".join(parts)
        
        # Add overall status symbol
        if summary.failed == 0 and summary.errors == 0:
            symbol = self.formatter.success("✓")
        else:
            symbol = self.formatter.error("✗")
        
        return f"{symbol} {summary_line}"


# Utility functions

def generate_summary(
    report: TestReport,
    format: SummaryFormat = SummaryFormat.CONSOLE,
    verbosity: SummaryVerbosity = SummaryVerbosity.NORMAL,
    output: Optional[TextIO] = None,
) -> str:
    """
    Convenience function to generate summary
    
    Args:
        report: TestReport to summarize
        format: Output format
        verbosity: Verbosity level
        output: Optional output stream
    
    Returns:
        Summary string
    """
    reporter = SummaryReporter(report, format, verbosity)
    return reporter.generate(output)


def print_summary(
    report: TestReport,
    verbosity: SummaryVerbosity = SummaryVerbosity.NORMAL,
):
    """
    Print summary to console
    
    Args:
        report: TestReport to summarize
        verbosity: Verbosity level
    """
    reporter = SummaryReporter(report, SummaryFormat.CONSOLE, verbosity)
    reporter.generate(sys.stdout)


def save_summary(
    report: TestReport,
    output_path: Path,
    format: SummaryFormat = SummaryFormat.TEXT,
    verbosity: SummaryVerbosity = SummaryVerbosity.NORMAL,
) -> Path:
    """
    Save summary to file
    
    Args:
        report: TestReport to summarize
        output_path: Where to save
        format: Output format
        verbosity: Verbosity level
    
    Returns:
        Path to saved file
    """
    reporter = SummaryReporter(report, format, verbosity)
    return reporter.save(output_path)


def generate_compact_summary(report: TestReport) -> str:
    """
    Generate compact one-line summary
    
    Args:
        report: TestReport to summarize
    
    Returns:
        One-line summary
    """
    reporter = CompactSummaryReporter(report)
    return reporter.generate()


# Example usage
if __name__ == "__main__":
    import sys
    from pathlib import Path
    
    if len(sys.argv) < 2:
        print("Usage: python summary_reporter.py <report.json> [format] [verbosity]")
        print("\nFormats: console (default), text, markdown")
        print("Verbosity: minimal, normal (default), detailed, full")
        sys.exit(1)
    
    # Load report
    from ..reporters.test_report import TestReportLoader
    
    report_path = Path(sys.argv[1])
    report = TestReportLoader.load(report_path)
    
    # Parse format
    format_str = sys.argv[2] if len(sys.argv) > 2 else "console"
    format = SummaryFormat(format_str)
    
    # Parse verbosity
    verbosity_str = sys.argv[3] if len(sys.argv) > 3 else "normal"
    verbosity = SummaryVerbosity(verbosity_str)
    
    # Generate summary
    reporter = SummaryReporter(report, format, verbosity)
    reporter.generate(sys.stdout)
    
    # Also print compact summary
    print("\n")
    print(generate_compact_summary(report))
