"""
HTML report generator

Generates interactive HTML reports with charts and statistics.

Author: TB Eval Team
Version: 0.1.0
"""

from pathlib import Path
from typing import Optional, Dict, Any, List
from datetime import datetime
import json
import base64

from ..models import TestReport, TestResult, TestOutcome


class HTMLReporter:
    """
    Generates interactive HTML reports
    
    Features:
    - Self-contained HTML (no external dependencies)
    - Interactive charts (Chart.js embedded)
    - Test result filtering and sorting
    - Expandable failure details
    - Performance metrics
    - Coverage summary
    - Mobile-responsive design
    """
    
    def __init__(
        self,
        report: TestReport,
        title: Optional[str] = None,
        include_charts: bool = True,
        include_details: bool = True,
    ):
        """
        Initialize HTML reporter
        
        Args:
            report: TestReport to generate from
            title: Optional custom title
            include_charts: Whether to include charts
            include_details: Whether to include detailed test results
        """
        self.report = report
        self.title = title or "Test Execution Report"
        self.include_charts = include_charts
        self.include_details = include_details
    
    def generate(self, output_path: Path) -> Path:
        """
        Generate HTML report
        
        Args:
            output_path: Where to save HTML file
        
        Returns:
            Path to generated file
        """
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Build HTML
        html = self._build_html()
        
        # Write to file
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(html)
        
        return output_path
    
    def _build_html(self) -> str:
        """Build complete HTML document"""
        return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{self._escape_html(self.title)}</title>
    <style>
        {self._get_css()}
    </style>
</head>
<body>
    <div class="container">
        {self._build_header()}
        {self._build_summary()}
        {self._build_charts() if self.include_charts else ''}
        {self._build_test_results() if self.include_details else ''}
        {self._build_coverage()}
        {self._build_footer()}
    </div>
    
    <script>
        {self._get_chartjs() if self.include_charts else ''}
        {self._get_javascript()}
    </script>
</body>
</html>"""
    
    def _get_css(self) -> str:
        """Get embedded CSS"""
        return """
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
            line-height: 1.6;
            color: #333;
            background: #f5f5f5;
            padding: 20px;
        }
        
        .container {
            max-width: 1200px;
            margin: 0 auto;
            background: white;
            border-radius: 8px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
            overflow: hidden;
        }
        
        .header {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 30px;
            text-align: center;
        }
        
        .header h1 {
            font-size: 2em;
            margin-bottom: 10px;
        }
        
        .header .timestamp {
            opacity: 0.9;
            font-size: 0.9em;
        }
        
        .summary {
            padding: 30px;
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
        }
        
        .stat-card {
            background: #f8f9fa;
            border-radius: 8px;
            padding: 20px;
            text-align: center;
            border-left: 4px solid #667eea;
        }
        
        .stat-card.passed {
            border-left-color: #10b981;
        }
        
        .stat-card.failed {
            border-left-color: #ef4444;
        }
        
        .stat-card.skipped {
            border-left-color: #f59e0b;
        }
        
        .stat-card .label {
            font-size: 0.9em;
            color: #6b7280;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }
        
        .stat-card .value {
            font-size: 2em;
            font-weight: bold;
            margin-top: 5px;
        }
        
        .stat-card.passed .value {
            color: #10b981;
        }
        
        .stat-card.failed .value {
            color: #ef4444;
        }
        
        .stat-card.skipped .value {
            color: #f59e0b;
        }
        
        .section {
            padding: 30px;
            border-top: 1px solid #e5e7eb;
        }
        
        .section-title {
            font-size: 1.5em;
            margin-bottom: 20px;
            color: #1f2937;
        }
        
        .charts {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            gap: 30px;
        }
        
        .chart-container {
            position: relative;
            height: 300px;
        }
        
        .progress-bar {
            width: 100%;
            height: 30px;
            background: #e5e7eb;
            border-radius: 15px;
            overflow: hidden;
            margin: 20px 0;
        }
        
        .progress-fill {
            height: 100%;
            background: linear-gradient(90deg, #10b981 0%, #059669 100%);
            transition: width 1s ease;
            display: flex;
            align-items: center;
            justify-content: center;
            color: white;
            font-weight: bold;
            font-size: 0.9em;
        }
        
        .test-results {
            margin-top: 20px;
        }
        
        .filter-bar {
            display: flex;
            gap: 10px;
            margin-bottom: 20px;
            flex-wrap: wrap;
        }
        
        .filter-btn {
            padding: 8px 16px;
            border: 1px solid #d1d5db;
            background: white;
            border-radius: 6px;
            cursor: pointer;
            transition: all 0.2s;
        }
        
        .filter-btn:hover {
            background: #f3f4f6;
        }
        
        .filter-btn.active {
            background: #667eea;
            color: white;
            border-color: #667eea;
        }
        
        .test-table {
            width: 100%;
            border-collapse: collapse;
            margin-top: 20px;
        }
        
        .test-table th {
            background: #f9fafb;
            padding: 12px;
            text-align: left;
            font-weight: 600;
            border-bottom: 2px solid #e5e7eb;
        }
        
        .test-table td {
            padding: 12px;
            border-bottom: 1px solid #e5e7eb;
        }
        
        .test-table tr:hover {
            background: #f9fafb;
        }
        
        .test-row {
            cursor: pointer;
        }
        
        .test-row.hidden {
            display: none;
        }
        
        .status-badge {
            display: inline-block;
            padding: 4px 12px;
            border-radius: 12px;
            font-size: 0.85em;
            font-weight: 600;
            text-transform: uppercase;
        }
        
        .status-badge.passed {
            background: #d1fae5;
            color: #065f46;
        }
        
        .status-badge.failed {
            background: #fee2e2;
            color: #991b1b;
        }
        
        .status-badge.error {
            background: #fef3c7;
            color: #92400e;
        }
        
        .status-badge.skipped {
            background: #e5e7eb;
            color: #374151;
        }
        
        .status-badge.timeout {
            background: #fed7aa;
            color: #9a3412;
        }
        
        .test-details {
            padding: 20px;
            background: #f9fafb;
            margin-top: 10px;
            border-radius: 6px;
            display: none;
        }
        
        .test-details.expanded {
            display: block;
        }
        
        .test-details pre {
            background: #1f2937;
            color: #f3f4f6;
            padding: 15px;
            border-radius: 6px;
            overflow-x: auto;
            font-size: 0.9em;
            line-height: 1.5;
        }
        
        .footer {
            padding: 20px 30px;
            background: #f9fafb;
            text-align: center;
            color: #6b7280;
            font-size: 0.9em;
        }
        
        @media (max-width: 768px) {
            .summary {
                grid-template-columns: 1fr;
            }
            
            .charts {
                grid-template-columns: 1fr;
            }
            
            .filter-bar {
                flex-direction: column;
            }
            
            .test-table {
                font-size: 0.9em;
            }
        }
        """
    
    def _build_header(self) -> str:
        """Build header section"""
        timestamp = "Unknown"
        if self.report.execution_metadata:
            try:
                dt = datetime.fromisoformat(self.report.execution_metadata.timestamp)
                timestamp = dt.strftime("%B %d, %Y at %I:%M %p")
            except:
                timestamp = self.report.execution_metadata.timestamp
        
        status_class = self._get_status_class()
        status_text = self.report.status.value.upper()
        
        return f"""
        <div class="header">
            <h1>{self._escape_html(self.title)}</h1>
            <div class="timestamp">{timestamp}</div>
            <div style="margin-top: 10px;">
                <span class="status-badge {status_class}">{status_text}</span>
            </div>
        </div>
        """
    
    def _build_summary(self) -> str:
        """Build summary statistics section"""
        summary = self.report.summary
        
        success_rate = summary.success_rate * 100
        duration = self._format_duration(summary.total_duration_ms)
        
        return f"""
        <div class="summary">
            <div class="stat-card">
                <div class="label">Total Tests</div>
                <div class="value">{summary.total_tests}</div>
            </div>
            <div class="stat-card passed">
                <div class="label">Passed</div>
                <div class="value">{summary.passed}</div>
            </div>
            <div class="stat-card failed">
                <div class="label">Failed</div>
                <div class="value">{summary.failed}</div>
            </div>
            <div class="stat-card skipped">
                <div class="label">Skipped</div>
                <div class="value">{summary.skipped}</div>
            </div>
            <div class="stat-card">
                <div class="label">Success Rate</div>
                <div class="value">{success_rate:.1f}%</div>
            </div>
            <div class="stat-card">
                <div class="label">Duration</div>
                <div class="value" style="font-size: 1.5em;">{duration}</div>
            </div>
        </div>
        
        <div class="section">
            <div class="progress-bar">
                <div class="progress-fill" style="width: {success_rate}%">
                    {success_rate:.1f}%
                </div>
            </div>
        </div>
        """
    
    def _build_charts(self) -> str:
        """Build charts section"""
        return f"""
        <div class="section">
            <h2 class="section-title">Charts</h2>
            <div class="charts">
                <div class="chart-container">
                    <canvas id="outcomeChart"></canvas>
                </div>
                <div class="chart-container">
                    <canvas id="durationChart"></canvas>
                </div>
            </div>
        </div>
        """
    
    def _build_test_results(self) -> str:
        """Build test results table"""
        if not self.report.results:
            return ""
        
        # Sort tests by outcome (failed first, then others)
        sorted_results = sorted(
            self.report.results,
            key=lambda x: (
                0 if x.outcome == TestOutcome.FAILED else
                1 if x.outcome == TestOutcome.ERROR else
                2 if x.outcome == TestOutcome.TIMEOUT else
                3 if x.outcome == TestOutcome.SKIPPED else
                4
            )
        )
        
        rows = []
        for idx, test in enumerate(sorted_results):
            rows.append(self._build_test_row(idx, test))
        
        return f"""
        <div class="section">
            <h2 class="section-title">Test Results</h2>
            
            <div class="filter-bar">
                <button class="filter-btn active" onclick="filterTests('all')">All</button>
                <button class="filter-btn" onclick="filterTests('passed')">Passed</button>
                <button class="filter-btn" onclick="filterTests('failed')">Failed</button>
                <button class="filter-btn" onclick="filterTests('error')">Errors</button>
                <button class="filter-btn" onclick="filterTests('skipped')">Skipped</button>
            </div>
            
            <div class="test-results">
                <table class="test-table">
                    <thead>
                        <tr>
                            <th style="width: 50px;">#</th>
                            <th>Test Name</th>
                            <th style="width: 120px;">Status</th>
                            <th style="width: 100px;">Duration</th>
                        </tr>
                    </thead>
                    <tbody>
                        {''.join(rows)}
                    </tbody>
                </table>
            </div>
        </div>
        """
    
    def _build_test_row(self, idx: int, test: TestResult) -> str:
        """Build single test row"""
        outcome_lower = test.outcome.value.lower()
        duration = self._format_duration(test.duration_ms)
        
        # Build details section
        details = ""
        if test.message or test.traceback:
            details_content = []
            
            if test.message:
                details_content.append(f"<strong>Message:</strong><br>{self._escape_html(test.message)}")
            
            if test.traceback:
                details_content.append(f"<strong>Traceback:</strong><pre>{self._escape_html(test.traceback[:1000])}</pre>")
            
            if test.artifacts.log_file:
                details_content.append(f"<strong>Log File:</strong> {self._escape_html(test.artifacts.log_file)}")
            
            details = f"""
            <tr class="test-details" id="details-{idx}" data-outcome="{outcome_lower}">
                <td colspan="4">
                    <div class="test-details">
                        {'<br><br>'.join(details_content)}
                    </div>
                </td>
            </tr>
            """
        
        return f"""
        <tr class="test-row" onclick="toggleDetails({idx})" data-outcome="{outcome_lower}">
            <td>{idx + 1}</td>
            <td>{self._escape_html(test.full_name)}</td>
            <td><span class="status-badge {outcome_lower}">{test.outcome.value}</span></td>
            <td>{duration}</td>
        </tr>
        {details}
        """
    
    def _build_coverage(self) -> str:
        """Build coverage summary section"""
        if not self.report.coverage.files:
            return ""
        
        coverage = self.report.coverage
        size_mb = coverage.total_size_bytes / (1024 * 1024)
        
        return f"""
        <div class="section">
            <h2 class="section-title">Coverage Summary</h2>
            <div class="summary" style="grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));">
                <div class="stat-card">
                    <div class="label">Files</div>
                    <div class="value">{len(coverage.files)}</div>
                </div>
                <div class="stat-card">
                    <div class="label">Format</div>
                    <div class="value" style="font-size: 1.2em;">{coverage.primary_format.value}</div>
                </div>
                <div class="stat-card">
                    <div class="label">Total Size</div>
                    <div class="value" style="font-size: 1.2em;">{size_mb:.1f} MB</div>
                </div>
                <div class="stat-card">
                    <div class="label">Per-Test</div>
                    <div class="value" style="font-size: 1.2em;">{'Yes' if coverage.per_test else 'No'}</div>
                </div>
            </div>
        </div>
        """
    
    def _build_footer(self) -> str:
        """Build footer section"""
        return f"""
        <div class="footer">
            Generated by TB Eval Framework v{self.report.framework_version} | 
            Exit Code: {self.report.exit_code}
        </div>
        """
    
    def _get_chartjs(self) -> str:
        """Get Chart.js library (minified)"""
        # Embedded Chart.js 3.x minified
        # In production, you might want to use a CDN or full embedded version
        # For brevity, here's a simplified version indicator
        return """
        // Chart.js would be embedded here
        // For now, using a simple canvas-based implementation
        
        function createPieChart(canvasId, data, labels, colors) {
            const canvas = document.getElementById(canvasId);
            if (!canvas) return;
            
            const ctx = canvas.getContext('2d');
            const total = data.reduce((a, b) => a + b, 0);
            
            if (total === 0) return;
            
            const centerX = canvas.width / 2;
            const centerY = canvas.height / 2;
            const radius = Math.min(centerX, centerY) - 20;
            
            let currentAngle = -Math.PI / 2;
            
            data.forEach((value, index) => {
                const sliceAngle = (value / total) * 2 * Math.PI;
                
                // Draw slice
                ctx.beginPath();
                ctx.moveTo(centerX, centerY);
                ctx.arc(centerX, centerY, radius, currentAngle, currentAngle + sliceAngle);
                ctx.closePath();
                ctx.fillStyle = colors[index];
                ctx.fill();
                
                currentAngle += sliceAngle;
            });
            
            // Draw legend
            const legendY = canvas.height - 60;
            let legendX = 20;
            
            labels.forEach((label, index) => {
                if (data[index] > 0) {
                    ctx.fillStyle = colors[index];
                    ctx.fillRect(legendX, legendY, 15, 15);
                    ctx.fillStyle = '#333';
                    ctx.font = '12px Arial';
                    ctx.fillText(label + ': ' + data[index], legendX + 20, legendY + 12);
                    legendX += 120;
                }
            });
        }
        
        function createBarChart(canvasId, tests) {
            const canvas = document.getElementById(canvasId);
            if (!canvas) return;
            
            const ctx = canvas.getContext('2d');
            
            // Get top 5 slowest tests
            const sorted = tests.sort((a, b) => b.duration - a.duration).slice(0, 5);
            
            if (sorted.length === 0) return;
            
            const maxDuration = Math.max(...sorted.map(t => t.duration));
            const barHeight = 30;
            const barSpacing = 20;
            const leftMargin = 200;
            const chartWidth = canvas.width - leftMargin - 50;
            
            sorted.forEach((test, index) => {
                const y = 30 + index * (barHeight + barSpacing);
                const barWidth = (test.duration / maxDuration) * chartWidth;
                
                // Draw bar
                ctx.fillStyle = '#667eea';
                ctx.fillRect(leftMargin, y, barWidth, barHeight);
                
                // Draw label
                ctx.fillStyle = '#333';
                ctx.font = '12px Arial';
                ctx.textAlign = 'right';
                ctx.fillText(test.name.slice(0, 30), leftMargin - 10, y + barHeight / 2 + 5);
                
                // Draw duration
                ctx.textAlign = 'left';
                ctx.fillText(test.duration.toFixed(2) + 's', leftMargin + barWidth + 5, y + barHeight / 2 + 5);
            });
        }
        """
    
    def _get_javascript(self) -> str:
        """Get JavaScript code"""
        # Prepare data for charts
        summary = self.report.summary
        
        outcome_data = [summary.passed, summary.failed, summary.errors, summary.skipped]
        outcome_labels = ['Passed', 'Failed', 'Errors', 'Skipped']
        outcome_colors = ['#10b981', '#ef4444', '#f59e0b', '#6b7280']
        
        # Get test duration data
        test_data = [
            {
                'name': t.name,
                'duration': t.duration_ms / 1000.0
            }
            for t in self.report.results
        ]
        
        return f"""
        // Chart data
        const outcomeData = {json.dumps(outcome_data)};
        const outcomeLabels = {json.dumps(outcome_labels)};
        const outcomeColors = {json.dumps(outcome_colors)};
        const testData = {json.dumps(test_data)};
        
        // Initialize charts
        window.addEventListener('DOMContentLoaded', function() {{
            createPieChart('outcomeChart', outcomeData, outcomeLabels, outcomeColors);
            createBarChart('durationChart', testData);
        }});
        
        // Filter functionality
        function filterTests(filter) {{
            const rows = document.querySelectorAll('.test-row');
            const buttons = document.querySelectorAll('.filter-btn');
            
            // Update button states
            buttons.forEach(btn => btn.classList.remove('active'));
            event.target.classList.add('active');
            
            // Filter rows
            rows.forEach(row => {{
                const outcome = row.dataset.outcome;
                const detailsRow = document.getElementById('details-' + row.rowIndex);
                
                if (filter === 'all' || outcome === filter) {{
                    row.classList.remove('hidden');
                    if (detailsRow) detailsRow.classList.remove('hidden');
                }} else {{
                    row.classList.add('hidden');
                    if (detailsRow) detailsRow.classList.add('hidden');
                }}
            }});
        }}
        
        // Toggle test details
        function toggleDetails(index) {{
            const details = document.getElementById('details-' + index);
            if (details) {{
                const detailsDiv = details.querySelector('.test-details');
                if (detailsDiv.classList.contains('expanded')) {{
                    detailsDiv.classList.remove('expanded');
                }} else {{
                    detailsDiv.classList.add('expanded');
                }}
            }}
        }}
        """
    
    def _get_status_class(self) -> str:
        """Get CSS class for status"""
        if self.report.status.value == "completed":
            if self.report.summary.failed == 0 and self.report.summary.errors == 0:
                return "passed"
            else:
                return "failed"
        elif self.report.status.value in ["error", "cancelled"]:
            return "failed"
        else:
            return "skipped"
    
    def _format_duration(self, ms: float) -> str:
        """Format duration"""
        if ms < 1000:
            return f"{ms:.0f}ms"
        elif ms < 60000:
            return f"{ms/1000:.2f}s"
        else:
            minutes = int(ms / 60000)
            seconds = (ms % 60000) / 1000
            return f"{minutes}m {seconds:.0f}s"
    
    def _escape_html(self, text: str) -> str:
        """Escape HTML special characters"""
        if not text:
            return ""
        
        return (text
            .replace('&', '&amp;')
            .replace('<', '&lt;')
            .replace('>', '&gt;')
            .replace('"', '&quot;')
            .replace("'", '&#39;'))


# Utility functions

def generate_html(report: TestReport, output_path: Path) -> Path:
    """
    Convenience function to generate HTML report
    
    Args:
        report: TestReport to convert
        output_path: Where to save HTML
    
    Returns:
        Path to generated file
    """
    reporter = HTMLReporter(report)
    return reporter.generate(output_path)


# Example usage
if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 3:
        print("Usage: python html_reporter.py <report.json> <output.html>")
        sys.exit(1)
    
    from ..reporters.test_report import TestReportLoader
    
    report_path = Path(sys.argv[1])
    output_path = Path(sys.argv[2])
    
    print(f"Loading report from: {report_path}")
    report = TestReportLoader.load(report_path)
    
    print(f"Generating HTML report...")
    html_path = generate_html(report, output_path)
    
    print(f"✓ HTML report generated: {html_path}")
    print(f"\nOpen in browser:")
    print(f"  file://{html_path.absolute()}")
