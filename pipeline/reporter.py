"""
VerifEval Reporting Module.

Generates comprehensive evaluation reports in multiple formats:
- JSON (machine-readable)
- HTML (human-readable dashboard)
- Text (console output)
"""

import json
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List, Optional
from dataclasses import dataclass

from .evaluator import EvaluationResult, StageResult, EvaluationStage


@dataclass
class ScoreBreakdown:
    """Detailed breakdown of scores."""
    build_success: float = 0.0
    sim_success: float = 0.0
    structural_coverage: float = 0.0
    functional_coverage: float = 0.0
    lint_score: float = 0.0
    mutation_score: float = 0.0
    overall_score: float = 0.0
    
    # Weights used
    weights: Dict[str, float] = None
    
    def __post_init__(self):
        if self.weights is None:
            self.weights = {
                'build_success': 0.15,
                'sim_success': 0.25,
                'structural_coverage': 0.25,
                'functional_coverage': 0.10,
                'lint_score': 0.15,
                'mutation_score': 0.10
            }


class EvalReporter:
    """
    Generates evaluation reports from pipeline results.
    
    Implements the scoring formula from the HLD Guide:
    - Build Success (15%)
    - Sim Success (25%)
    - Structural Coverage (25%)
    - Functional Coverage (10%)
    - Lint Score (15%)
    - Mutation Score (10%)
    """
    
    def __init__(self, result: EvaluationResult):
        self.result = result
        self.score_breakdown = self._compute_score_breakdown()
    
    def _compute_score_breakdown(self) -> ScoreBreakdown:
        """Compute detailed score breakdown."""
        breakdown = ScoreBreakdown()
        
        # Extract metrics from stages
        if 'execute' in self.result.stages:
            exec_data = self.result.stages['execute'].data
            breakdown.build_success = exec_data.get('build_success_rate', 0.0)
            breakdown.sim_success = exec_data.get('sim_success_rate', 0.0)
            breakdown.structural_coverage = exec_data.get('avg_coverage', 0.0)
        
        if 'coverage' in self.result.stages:
            cov_data = self.result.stages['coverage'].data
            breakdown.functional_coverage = cov_data.get('functional_coverage', 0.0)
        
        if 'quality_gate' in self.result.stages:
            qg_data = self.result.stages['quality_gate'].data
            if not qg_data.get('skipped'):
                errors = qg_data.get('critical_errors', 0)
                warnings = qg_data.get('warnings', 0)
                breakdown.lint_score = max(0, 100 - errors * 10 - warnings)
            else:
                breakdown.lint_score = 100.0  # No lint = assume good
        
        # Mutation score (if available)
        if 'mutation' in self.result.stages:
            mut_data = self.result.stages['mutation'].data
            breakdown.mutation_score = mut_data.get('mutation_score', 0.0)
        
        # Compute overall score
        breakdown.overall_score = (
            breakdown.build_success * breakdown.weights['build_success'] +
            breakdown.sim_success * breakdown.weights['sim_success'] +
            breakdown.structural_coverage * breakdown.weights['structural_coverage'] +
            breakdown.functional_coverage * breakdown.weights['functional_coverage'] +
            breakdown.lint_score * breakdown.weights['lint_score'] +
            breakdown.mutation_score * breakdown.weights['mutation_score']
        )
        
        return breakdown
    
    def generate_json_report(self, output_path: Optional[Path] = None) -> Dict[str, Any]:
        """Generate JSON report."""
        report = {
            'report_version': '1.0',
            'generated_at': datetime.now().isoformat(),
            'project': {
                'name': self.result.project_name,
                'evaluation_timestamp': self.result.timestamp,
                'duration_ms': self.result.total_duration_ms
            },
            'scores': {
                'overall': round(self.score_breakdown.overall_score, 2),
                'breakdown': {
                    'build_success': round(self.score_breakdown.build_success, 2),
                    'sim_success': round(self.score_breakdown.sim_success, 2),
                    'structural_coverage': round(self.score_breakdown.structural_coverage, 2),
                    'functional_coverage': round(self.score_breakdown.functional_coverage, 2),
                    'lint_score': round(self.score_breakdown.lint_score, 2),
                    'mutation_score': round(self.score_breakdown.mutation_score, 2)
                },
                'weights': self.score_breakdown.weights
            },
            'stages': {},
            'success': self.result.success,
            'errors': self.result.errors,
            'warnings': self.result.warnings
        }
        
        # Add stage details
        for name, stage in self.result.stages.items():
            report['stages'][name] = {
                'success': stage.success,
                'duration_ms': stage.duration_ms,
                'data': stage.data,
                'errors': stage.errors,
                'warnings': stage.warnings
            }
        
        if output_path:
            output_path = Path(output_path)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            with open(output_path, 'w') as f:
                json.dump(report, f, indent=2)
        
        return report
    
    def generate_csv_row(self) -> Dict[str, Any]:
        """Generate a CSV-compatible row for aggregation."""
        return {
            'project_name': self.result.project_name,
            'timestamp': self.result.timestamp,
            'success': self.result.success,
            'overall_score': round(self.score_breakdown.overall_score, 2),
            'build_success': round(self.score_breakdown.build_success, 2),
            'sim_success': round(self.score_breakdown.sim_success, 2),
            'structural_coverage': round(self.score_breakdown.structural_coverage, 2),
            'lint_score': round(self.score_breakdown.lint_score, 2),
            'duration_ms': round(self.result.total_duration_ms, 2),
            'errors': len(self.result.errors),
            'warnings': len(self.result.warnings)
        }
    
    def generate_text_report(self) -> str:
        """Generate human-readable text report."""
        lines = [
            "=" * 70,
            "VERIFEVAL EVALUATION REPORT",
            "=" * 70,
            "",
            f"Project: {self.result.project_name}",
            f"Timestamp: {self.result.timestamp}",
            f"Duration: {self.result.total_duration_ms:.0f}ms",
            "",
            "-" * 70,
            "SCORES",
            "-" * 70,
            "",
            f"  OVERALL SCORE: {self.score_breakdown.overall_score:.1f}/100",
            "",
            "  Breakdown:",
            f"    Build Success:       {self.score_breakdown.build_success:6.1f}% (weight: {self.score_breakdown.weights['build_success']*100:.0f}%)",
            f"    Simulation Success:  {self.score_breakdown.sim_success:6.1f}% (weight: {self.score_breakdown.weights['sim_success']*100:.0f}%)",
            f"    Structural Coverage: {self.score_breakdown.structural_coverage:6.1f}% (weight: {self.score_breakdown.weights['structural_coverage']*100:.0f}%)",
            f"    Functional Coverage: {self.score_breakdown.functional_coverage:6.1f}% (weight: {self.score_breakdown.weights['functional_coverage']*100:.0f}%)",
            f"    Lint Score:          {self.score_breakdown.lint_score:6.1f}% (weight: {self.score_breakdown.weights['lint_score']*100:.0f}%)",
            f"    Mutation Score:      {self.score_breakdown.mutation_score:6.1f}% (weight: {self.score_breakdown.weights['mutation_score']*100:.0f}%)",
            "",
            "-" * 70,
            "STAGE RESULTS",
            "-" * 70,
            ""
        ]
        
        # Stage results
        for name, stage in self.result.stages.items():
            status = "✓ PASS" if stage.success else "✗ FAIL"
            lines.append(f"  {name.upper()}: {status} ({stage.duration_ms:.0f}ms)")
            
            if stage.errors:
                for err in stage.errors[:3]:
                    lines.append(f"    ✗ {err}")
        
        lines.append("")
        
        # Errors and warnings
        if self.result.errors:
            lines.extend([
                "-" * 70,
                f"ERRORS ({len(self.result.errors)})",
                "-" * 70,
                ""
            ])
            for err in self.result.errors[:10]:
                lines.append(f"  ✗ {err}")
            lines.append("")
        
        if self.result.warnings:
            lines.extend([
                "-" * 70,
                f"WARNINGS ({len(self.result.warnings)})",
                "-" * 70,
                ""
            ])
            for warn in self.result.warnings[:10]:
                lines.append(f"  ⚠ {warn}")
            lines.append("")
        
        # Final status
        status = "✓ EVALUATION PASSED" if self.result.success else "✗ EVALUATION FAILED"
        lines.extend([
            "=" * 70,
            f"STATUS: {status}",
            "=" * 70,
            ""
        ])
        
        return "\n".join(lines)
    
    def generate_html_report(self, output_path: Optional[Path] = None) -> str:
        """Generate HTML report for dashboard view."""
        score = self.score_breakdown.overall_score
        score_color = self._get_score_color(score)
        
        # Generate stage rows
        stage_rows = ""
        for name, stage in self.result.stages.items():
            status_class = "success" if stage.success else "error"
            status_icon = "✓" if stage.success else "✗"
            stage_rows += f"""
            <tr class="{status_class}">
                <td>{name.replace('_', ' ').title()}</td>
                <td class="status">{status_icon}</td>
                <td>{stage.duration_ms:.0f}ms</td>
            </tr>"""
        
        html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>VerifEval Report - {self.result.project_name}</title>
    <style>
        :root {{
            --bg: #0a0a0f;
            --card: #12121a;
            --text: #e0e0e0;
            --accent: {score_color};
            --success: #22c55e;
            --error: #ef4444;
            --warning: #f59e0b;
        }}
        
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        
        body {{
            font-family: 'SF Mono', 'Fira Code', monospace;
            background: var(--bg);
            color: var(--text);
            min-height: 100vh;
            padding: 2rem;
        }}
        
        .container {{
            max-width: 1200px;
            margin: 0 auto;
        }}
        
        header {{
            text-align: center;
            margin-bottom: 3rem;
        }}
        
        h1 {{
            font-size: 2.5rem;
            font-weight: 300;
            letter-spacing: 0.2em;
            margin-bottom: 0.5rem;
        }}
        
        .score-circle {{
            width: 200px;
            height: 200px;
            border-radius: 50%;
            background: conic-gradient(
                var(--accent) {score * 3.6}deg,
                #1a1a2e {score * 3.6}deg
            );
            display: flex;
            align-items: center;
            justify-content: center;
            margin: 2rem auto;
            position: relative;
        }}
        
        .score-circle::before {{
            content: '';
            position: absolute;
            width: 160px;
            height: 160px;
            background: var(--bg);
            border-radius: 50%;
        }}
        
        .score-value {{
            position: relative;
            font-size: 3rem;
            font-weight: bold;
            color: var(--accent);
        }}
        
        .cards {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            gap: 1.5rem;
            margin-bottom: 2rem;
        }}
        
        .card {{
            background: var(--card);
            border-radius: 12px;
            padding: 1.5rem;
            border: 1px solid #222;
        }}
        
        .card h3 {{
            font-size: 0.9rem;
            text-transform: uppercase;
            letter-spacing: 0.1em;
            margin-bottom: 1rem;
            color: #888;
        }}
        
        table {{
            width: 100%;
            border-collapse: collapse;
        }}
        
        td, th {{
            padding: 0.75rem;
            text-align: left;
            border-bottom: 1px solid #222;
        }}
        
        .success {{ color: var(--success); }}
        .error {{ color: var(--error); }}
        .warning {{ color: var(--warning); }}
        
        .status {{
            font-size: 1.2rem;
            text-align: center;
        }}
        
        .bar {{
            height: 8px;
            background: #1a1a2e;
            border-radius: 4px;
            overflow: hidden;
            margin-top: 0.5rem;
        }}
        
        .bar-fill {{
            height: 100%;
            background: var(--accent);
            transition: width 0.3s ease;
        }}
        
        footer {{
            text-align: center;
            margin-top: 3rem;
            color: #666;
            font-size: 0.8rem;
        }}
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>VERIFEVAL</h1>
            <p style="color: #666;">Verification Evaluation Report</p>
        </header>
        
        <div class="score-circle">
            <span class="score-value">{score:.0f}</span>
        </div>
        
        <div class="cards">
            <div class="card">
                <h3>Project Info</h3>
                <table>
                    <tr><td>Name</td><td>{self.result.project_name}</td></tr>
                    <tr><td>Timestamp</td><td>{self.result.timestamp}</td></tr>
                    <tr><td>Duration</td><td>{self.result.total_duration_ms:.0f}ms</td></tr>
                    <tr><td>Status</td><td class="{'success' if self.result.success else 'error'}">
                        {'PASSED' if self.result.success else 'FAILED'}
                    </td></tr>
                </table>
            </div>
            
            <div class="card">
                <h3>Score Breakdown</h3>
                <table>
                    <tr>
                        <td>Build Success</td>
                        <td>{self.score_breakdown.build_success:.1f}%</td>
                    </tr>
                    <tr>
                        <td>Sim Success</td>
                        <td>{self.score_breakdown.sim_success:.1f}%</td>
                    </tr>
                    <tr>
                        <td>Coverage</td>
                        <td>{self.score_breakdown.structural_coverage:.1f}%</td>
                    </tr>
                    <tr>
                        <td>Lint Score</td>
                        <td>{self.score_breakdown.lint_score:.1f}%</td>
                    </tr>
                </table>
            </div>
            
            <div class="card">
                <h3>Stage Results</h3>
                <table>
                    {stage_rows}
                </table>
            </div>
        </div>
        
        <footer>
            Generated by VerifEval • {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
        </footer>
    </div>
</body>
</html>"""
        
        if output_path:
            output_path = Path(output_path)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            with open(output_path, 'w') as f:
                f.write(html)
        
        return html
    
    def _get_score_color(self, score: float) -> str:
        """Get color based on score."""
        if score >= 80:
            return "#22c55e"  # Green
        elif score >= 60:
            return "#84cc16"  # Lime
        elif score >= 40:
            return "#f59e0b"  # Amber
        else:
            return "#ef4444"  # Red


def generate_aggregate_report(results: List[EvaluationResult],
                             output_dir: Path) -> Dict[str, Any]:
    """
    Generate aggregate report from multiple evaluation results.
    
    Args:
        results: List of evaluation results
        output_dir: Output directory for reports
        
    Returns:
        Aggregate statistics
    """
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    aggregate = {
        'total_projects': len(results),
        'successful': sum(1 for r in results if r.success),
        'failed': sum(1 for r in results if not r.success),
        'average_score': 0.0,
        'projects': []
    }
    
    scores = []
    
    for result in results:
        reporter = EvalReporter(result)
        
        # Generate individual reports
        reporter.generate_json_report(output_dir / f"{result.project_name}_report.json")
        reporter.generate_html_report(output_dir / f"{result.project_name}_report.html")
        
        # Collect stats
        scores.append(reporter.score_breakdown.overall_score)
        aggregate['projects'].append(reporter.generate_csv_row())
    
    if scores:
        aggregate['average_score'] = sum(scores) / len(scores)
    
    # Save aggregate report
    with open(output_dir / "aggregate_report.json", 'w') as f:
        json.dump(aggregate, f, indent=2)
    
    return aggregate

