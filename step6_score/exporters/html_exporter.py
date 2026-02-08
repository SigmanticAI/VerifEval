"""
HTML exporter for Step 7: Scoring

Generates interactive HTML dashboard with:
- Score summary with visual indicators
- Component score breakdown
- Coverage details
- Improvements and recommendations
- Interactive charts
- Responsive design

Author: TB Eval Team
Version: 0.1.0
"""

from pathlib import Path
from typing import Optional
from datetime import datetime
import json
import logging

from ..models import FinalReport, TierScore, ComponentScore

logger = logging.getLogger(__name__)


# =============================================================================
# HTML EXPORTER
# =============================================================================

class HTMLExporter:
    """
    Export scoring results to HTML dashboard
    
    Generates a self-contained HTML file with inline CSS and JavaScript.
    """
    
    def __init__(self):
        """Initialize HTML exporter"""
        pass
    
    def export(self, report: FinalReport, output_path: Path) -> None:
        """
        Export report to HTML
        
        Args:
            report: Final report to export
            output_path: Output HTML file path
        """
        logger.info(f"Generating HTML report: {output_path}")
        
        html = self._generate_html(report)
        
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(html)
        
        logger.info(f"HTML report generated: {output_path}")
    
    def _generate_html(self, report: FinalReport) -> str:
        """Generate complete HTML document"""
        return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>TB Eval Score Report - {report.submission_id}</title>
    {self._generate_css()}
</head>
<body>
    <div class="container">
        {self._generate_header(report)}
        {self._generate_score_summary(report.score)}
        {self._generate_component_breakdown(report.score)}
        {self._generate_improvements(report)}
        {self._generate_recommendations(report)}
        {self._generate_metadata(report)}
        {self._generate_footer()}
    </div>
    {self._generate_javascript(report)}
</body>
</html>"""
    
    def _generate_css(self) -> str:
        """Generate inline CSS"""
        return """<style>
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
    border-radius: 10px;
    box-shadow: 0 2px 10px rgba(0,0,0,0.1);
    overflow: hidden;
}

.header {
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    color: white;
    padding: 40px;
    text-align: center;
}

.header h1 {
    font-size: 2.5em;
    margin-bottom: 10px;
    font-weight: 700;
}

.header .submission-id {
    font-size: 1.2em;
    opacity: 0.9;
}

.section {
    padding: 40px;
    border-bottom: 1px solid #eee;
}

.section:last-child {
    border-bottom: none;
}

.section-title {
    font-size: 1.8em;
    margin-bottom: 20px;
    color: #667eea;
    font-weight: 600;
}

.score-summary {
    text-align: center;
    background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
}

.score-circle {
    width: 200px;
    height: 200px;
    margin: 30px auto;
    position: relative;
}

.score-value {
    font-size: 4em;
    font-weight: 700;
    color: #667eea;
}

.score-grade {
    font-size: 2em;
    color: #764ba2;
    margin-top: 10px;
}

.status-badge {
    display: inline-block;
    padding: 10px 30px;
    border-radius: 50px;
    font-size: 1.2em;
    font-weight: 600;
    margin-top: 20px;
}

.status-pass {
    background: #10b981;
    color: white;
}

.status-fail {
    background: #ef4444;
    color: white;
}

.tier-badge {
    display: inline-block;
    padding: 5px 15px;
    border-radius: 20px;
    font-size: 0.9em;
    font-weight: 600;
    margin-top: 10px;
}

.tier-open {
    background: #3b82f6;
    color: white;
}

.tier-pro {
    background: #8b5cf6;
    color: white;
}

.components-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
    gap: 20px;
    margin-top: 30px;
}

.component-card {
    background: #f9fafb;
    border-radius: 10px;
    padding: 20px;
    border-left: 4px solid #667eea;
}

.component-card.threshold-fail {
    border-left-color: #ef4444;
}

.component-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 15px;
}

.component-name {
    font-size: 1.1em;
    font-weight: 600;
    color: #333;
}

.component-status {
    font-size: 1.5em;
}

.component-score {
    font-size: 2em;
    font-weight: 700;
    color: #667eea;
    margin-bottom: 10px;
}

.component-details {
    font-size: 0.9em;
    color: #666;
}

.progress-bar {
    width: 100%;
    height: 8px;
    background: #e5e7eb;
    border-radius: 4px;
    overflow: hidden;
    margin: 10px 0;
}

.progress-fill {
    height: 100%;
    background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
    transition: width 0.3s ease;
}

.improvements-list {
    list-style: none;
}

.improvement-item {
    background: #f9fafb;
    border-radius: 10px;
    padding: 20px;
    margin-bottom: 15px;
    border-left: 4px solid #f59e0b;
}

.improvement-item.priority-high {
    border-left-color: #ef4444;
}

.improvement-item.priority-medium {
    border-left-color: #f59e0b;
}

.improvement-item.priority-low {
    border-left-color: #10b981;
}

.improvement-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 10px;
}

.improvement-title {
    font-size: 1.2em;
    font-weight: 600;
    color: #333;
}

.priority-badge {
    padding: 5px 15px;
    border-radius: 20px;
    font-size: 0.85em;
    font-weight: 600;
}

.priority-high {
    background: #fee2e2;
    color: #ef4444;
}

.priority-medium {
    background: #fef3c7;
    color: #f59e0b;
}

.priority-low {
    background: #d1fae5;
    color: #10b981;
}

.improvement-metrics {
    display: flex;
    gap: 20px;
    margin: 10px 0;
    font-size: 0.9em;
    color: #666;
}

.improvement-actions {
    margin-top: 15px;
}

.improvement-actions h4 {
    font-size: 0.9em;
    color: #666;
    margin-bottom: 8px;
}

.improvement-actions ul {
    list-style: none;
    padding-left: 0;
}

.improvement-actions li {
    padding: 5px 0;
    padding-left: 20px;
    position: relative;
}

.improvement-actions li:before {
    content: "•";
    position: absolute;
    left: 0;
    color: #667eea;
    font-weight: bold;
}

.recommendations-list {
    list-style: none;
}

.recommendation-item {
    background: #eff6ff;
    border-radius: 10px;
    padding: 20px;
    margin-bottom: 15px;
    border-left: 4px solid #3b82f6;
}

.recommendation-category {
    font-size: 0.9em;
    font-weight: 600;
    color: #3b82f6;
    text-transform: uppercase;
    letter-spacing: 0.5px;
    margin-bottom: 5px;
}

.recommendation-message {
    font-size: 1.1em;
    color: #333;
    margin-bottom: 10px;
}

.recommendation-details {
    font-size: 0.9em;
    color: #666;
}

.metadata-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
    gap: 20px;
}

.metadata-item {
    background: #f9fafb;
    border-radius: 10px;
    padding: 15px;
}

.metadata-label {
    font-size: 0.85em;
    color: #666;
    text-transform: uppercase;
    letter-spacing: 0.5px;
    margin-bottom: 5px;
}

.metadata-value {
    font-size: 1.1em;
    font-weight: 600;
    color: #333;
}

.footer {
    text-align: center;
    color: #666;
    font-size: 0.9em;
    padding: 20px;
    background: #f9fafb;
}

@media print {
    body {
        background: white;
    }
    
    .container {
        box-shadow: none;
    }
}

@media (max-width: 768px) {
    .components-grid {
        grid-template-columns: 1fr;
    }
    
    .header h1 {
        font-size: 1.8em;
    }
    
    .score-value {
        font-size: 3em;
    }
}
</style>"""
    
    def _generate_header(self, report: FinalReport) -> str:
        """Generate header section"""
        return f"""<div class="header">
    <h1>TB Eval Score Report</h1>
    <div class="submission-id">{report.submission_id}</div>
    <div style="margin-top: 10px; opacity: 0.8;">
        Generated: {report.generated_at.strftime('%Y-%m-%d %H:%M:%S')}
    </div>
</div>"""
    
    def _generate_score_summary(self, score: TierScore) -> str:
        """Generate score summary section"""
        percentage = score.percentage
        status = "pass" if score.pass_threshold else "fail"
        tier_class = "tier-open" if score.tier.value == "open_source" else "tier-pro"
        
        return f"""<div class="section score-summary">
    <div class="score-circle">
        <svg viewBox="0 0 200 200">
            <circle cx="100" cy="100" r="90" fill="none" stroke="#e5e7eb" stroke-width="20"/>
            <circle cx="100" cy="100" r="90" fill="none" stroke="url(#gradient)" stroke-width="20"
                stroke-dasharray="{percentage * 5.65} 565" stroke-linecap="round"
                transform="rotate(-90 100 100)"/>
            <defs>
                <linearGradient id="gradient" x1="0%" y1="0%" x2="100%" y2="0%">
                    <stop offset="0%" style="stop-color:#667eea"/>
                    <stop offset="100%" style="stop-color:#764ba2"/>
                </linearGradient>
            </defs>
        </svg>
    </div>
    <div class="score-value">{percentage:.1f}%</div>
    <div class="score-grade">Grade: {score.grade.value}</div>
    <div class="status-badge status-{status}">
        {'✓ PASS' if score.pass_threshold else '✗ FAIL'}
    </div>
    <div class="tier-badge {tier_class}">
        {score.tier.display_name}
    </div>
</div>"""
    
    def _generate_component_breakdown(self, score: TierScore) -> str:
        """Generate component breakdown section"""
        cards = []
        
        for name, component in score.components.items():
            status = "✓" if component.threshold_met else "✗"
            threshold_class = "" if component.threshold_met else "threshold-fail"
            
            cards.append(f"""<div class="component-card {threshold_class}">
    <div class="component-header">
        <div class="component-name">{component.component_type.display_name}</div>
        <div class="component-status">{status}</div>
    </div>
    <div class="component-score">{component.percentage:.1f}%</div>
    <div class="progress-bar">
        <div class="progress-fill" style="width: {component.percentage}%"></div>
    </div>
    <div class="component-details">
        <div>Weight: {component.weight:.0%}</div>
        <div>Contribution: {component.weighted_contribution:.4f}</div>
    </div>
</div>""")
        
        return f"""<div class="section">
    <h2 class="section-title">Component Scores</h2>
    <div class="components-grid">
        {''.join(cards)}
    </div>
</div>"""
    
    def _generate_improvements(self, report: FinalReport) -> str:
        """Generate improvements section"""
        if not report.improvements:
            return ""
        
        items = []
        for imp in report.improvements[:10]:
            actions_html = "".join([f"<li>{action}</li>" for action in imp.actions])
            
            items.append(f"""<li class="improvement-item priority-{imp.priority}">
    <div class="improvement-header">
        <div class="improvement-title">{imp.component.display_name}</div>
        <div class="priority-badge priority-{imp.priority}">{imp.priority.upper()}</div>
    </div>
    <div class="improvement-metrics">
        <div>Current: {imp.current_value:.1f}%</div>
        <div>Target: {imp.target_value:.1f}%</div>
        <div>Impact: +{imp.impact:.4f} points</div>
    </div>
    <div class="improvement-actions">
        <h4>Suggested Actions:</h4>
        <ul>{actions_html}</ul>
    </div>
</li>""")
        
        return f"""<div class="section">
    <h2 class="section-title">Recommended Improvements</h2>
    <ul class="improvements-list">
        {''.join(items)}
    </ul>
</div>"""
    
    def _generate_recommendations(self, report: FinalReport) -> str:
        """Generate recommendations section"""
        if not report.recommendations:
            return ""
        
        items = []
        for rec in report.recommendations:
            details = f"<div class='recommendation-details'>{rec.details}</div>" if rec.details else ""
            
            items.append(f"""<li class="recommendation-item">
    <div class="recommendation-category">{rec.category}</div>
    <div class="recommendation-message">{rec.message}</div>
    {details}
</li>""")
        
        return f"""<div class="section">
    <h2 class="section-title">General Recommendations</h2>
    <ul class="recommendations-list">
        {''.join(items)}
    </ul>
</div>"""
    
    def _generate_metadata(self, report: FinalReport) -> str:
        """Generate metadata section"""
        return f"""<div class="section">
    <h2 class="section-title">Evaluation Details</h2>
    <div class="metadata-grid">
        <div class="metadata-item">
            <div class="metadata-label">Framework Version</div>
            <div class="metadata-value">{report.framework_version}</div>
        </div>
        <div class="metadata-item">
            <div class="metadata-label">Duration</div>
            <div class="metadata-value">{report.total_duration_ms / 1000:.2f}s</div>
        </div>
        <div class="metadata-item">
            <div class="metadata-label">Steps Completed</div>
            <div class="metadata-value">{len(report.steps_completed)}/{len(report.steps_completed)}</div>
        </div>
        <div class="metadata-item">
            <div class="metadata-label">Questa Available</div>
            <div class="metadata-value">{'Yes' if report.metadata.get('questa_available') else 'No'}</div>
        </div>
    </div>
</div>"""
    
    def _generate_footer(self) -> str:
        """Generate footer"""
        return f"""<div class="footer">
    <p>Generated by TB Eval Framework v{__import__('step7_score').__version__}</p>
    <p style="margin-top: 5px; font-size: 0.85em;">
        For support and documentation, visit 
        <a href="https://github.com/tbeval" style="color: #667eea;">github.com/tbeval</a>
    </p>
</div>"""
    
    def _generate_javascript(self, report: FinalReport) -> str:
        """Generate inline JavaScript"""
        score_data = {
            "overall": report.score.overall,
            "percentage": report.score.percentage,
            "grade": report.score.grade.value,
            "pass": report.score.pass_threshold,
            "components": {
                name: {
                    "score": comp.value,
                    "percentage": comp.percentage,
                    "weight": comp.weight,
                    "threshold_met": comp.threshold_met
                }
                for name, comp in report.score.components.items()
            }
        }
        
        return f"""<script>
// Score data
const scoreData = {json.dumps(score_data, indent=2)};

// Animate progress bars on load
document.addEventListener('DOMContentLoaded', function() {{
    const progressBars = document.querySelectorAll('.progress-fill');
    
    // Animate after short delay
    setTimeout(() => {{
        progressBars.forEach(bar => {{
            const width = bar.style.width;
            bar.style.width = '0%';
            setTimeout(() => {{
                bar.style.width = width;
            }}, 100);
        }});
    }}, 500);
}});

// Print functionality
function printReport() {{
    window.print();
}}

// Console log for debugging
console.log('TB Eval Score Report');
console.log('Overall Score:', scoreData.percentage + '%');
console.log('Grade:', scoreData.grade);
console.log('Components:', scoreData.components);
</script>"""


# =============================================================================
# CONVENIENCE FUNCTIONS
# =============================================================================

def export_html(report: FinalReport, output_path: Path) -> None:
    """
    Convenience function to export HTML report
    
    Args:
        report: Final report to export
        output_path: Output HTML file path
    """
    exporter = HTMLExporter()
    exporter.export(report, output_path)
