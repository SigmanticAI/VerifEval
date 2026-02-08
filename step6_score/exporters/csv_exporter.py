"""
CSV exporter for Step 7: Scoring

Generates CSV format reports for spreadsheet analysis.

Exports multiple CSV files:
- summary.csv: Overall score summary
- components.csv: Component breakdown
- improvements.csv: Improvement recommendations
- recommendations.csv: General recommendations

Author: TB Eval Team
Version: 0.1.0
"""

from pathlib import Path
from typing import Optional, List, Dict, Any
import csv
import logging

from ..models import FinalReport, TierScore, ComponentScore, Improvement, Recommendation

logger = logging.getLogger(__name__)


# =============================================================================
# CSV EXPORTER
# =============================================================================

class CSVExporter:
    """
    Export scoring results to CSV format
    
    Generates multiple CSV files for different aspects of the report.
    """
    
    def __init__(self):
        """Initialize CSV exporter"""
        pass
    
    def export(self, report: FinalReport, output_path: Path) -> None:
        """
        Export report to CSV files
        
        Args:
            report: Final report to export
            output_path: Output directory or base filename
        """
        logger.info(f"Generating CSV reports: {output_path}")
        
        output_path = Path(output_path)
        
        # Determine if output_path is a directory or file
        if output_path.suffix == '.csv':
            # Single file - use parent directory
            base_dir = output_path.parent
            base_name = output_path.stem
        else:
            # Directory
            base_dir = output_path
            base_name = "score"
        
        base_dir.mkdir(parents=True, exist_ok=True)
        
        # Export different CSV files
        self._export_summary(report, base_dir / f"{base_name}_summary.csv")
        self._export_components(report.score, base_dir / f"{base_name}_components.csv")
        self._export_improvements(report.improvements, base_dir / f"{base_name}_improvements.csv")
        self._export_recommendations(report.recommendations, base_dir / f"{base_name}_recommendations.csv")
        
        logger.info(f"CSV reports generated in: {base_dir}")
    
    def _export_summary(self, report: FinalReport, output_path: Path) -> None:
        """Export summary CSV"""
        rows = [
            ["Metric", "Value"],
            ["Submission ID", report.submission_id],
            ["Generated At", report.generated_at.isoformat()],
            ["Framework Version", report.framework_version],
            ["", ""],
            ["Overall Score", f"{report.score.overall:.4f}"],
            ["Percentage", f"{report.score.percentage:.2f}%"],
            ["Grade", report.score.grade.value],
            ["Pass Threshold", "Yes" if report.score.pass_threshold else "No"],
            ["Tier", report.score.tier.display_name],
            ["", ""],
            ["Total Duration (s)", f"{report.total_duration_ms / 1000:.2f}"],
            ["Steps Completed", len(report.steps_completed)],
            ["Total Improvements", len(report.improvements)],
            ["Total Recommendations", len(report.recommendations)],
            ["", ""],
            ["Questa Available", "Yes" if report.metadata.get("questa_available") else "No"],
        ]
        
        # Add component summary
        rows.append(["", ""])
        rows.append(["Component Scores", ""])
        for name, component in report.score.components.items():
            rows.append([
                component.component_type.display_name,
                f"{component.percentage:.2f}%"
            ])
        
        self._write_csv(output_path, rows)
    
    def _export_components(self, score: TierScore, output_path: Path) -> None:
        """Export components CSV"""
        rows = [
            [
                "Component",
                "Type",
                "Score",
                "Percentage",
                "Grade",
                "Weight",
                "Contribution",
                "Threshold Met",
                "Threshold Value"
            ]
        ]
        
        for name, component in score.components.items():
            rows.append([
                component.component_type.display_name,
                component.component_type.value,
                f"{component.value:.4f}",
                f"{component.percentage:.2f}",
                component.grade.value,
                f"{component.weight:.2f}",
                f"{component.weighted_contribution:.4f}",
                "Yes" if component.threshold_met else "No",
                f"{component.threshold_value:.2f}" if component.threshold_value else ""
            ])
        
        self._write_csv(output_path, rows)
    
    def _export_improvements(self, improvements: List[Improvement], output_path: Path) -> None:
        """Export improvements CSV"""
        rows = [
            [
                "Rank",
                "Component",
                "Priority",
                "Current Value",
                "Target Value",
                "Impact",
                "Actions"
            ]
        ]
        
        for i, imp in enumerate(improvements, 1):
            # Combine actions into single string
            actions = "; ".join(imp.actions) if imp.actions else ""
            
            rows.append([
                i,
                imp.component.display_name,
                imp.priority,
                f"{imp.current_value:.2f}",
                f"{imp.target_value:.2f}",
                f"{imp.impact:.4f}",
                actions
            ])
        
        self._write_csv(output_path, rows)
    
    def _export_recommendations(self, recommendations: List[Recommendation], output_path: Path) -> None:
        """Export recommendations CSV"""
        rows = [
            [
                "Rank",
                "Category",
                "Message",
                "Details",
                "References"
            ]
        ]
        
        for i, rec in enumerate(recommendations, 1):
            # Combine references into single string
            refs = "; ".join(rec.references) if rec.references else ""
            
            rows.append([
                i,
                rec.category,
                rec.message,
                rec.details or "",
                refs
            ])
        
        self._write_csv(output_path, rows)
    
    def _write_csv(self, output_path: Path, rows: List[List[Any]]) -> None:
        """
        Write rows to CSV file
        
        Args:
            output_path: Output CSV file path
            rows: List of rows (each row is a list of values)
        """
        with open(output_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerows(rows)
        
        logger.debug(f"CSV written: {output_path}")
    
    def export_single_file(self, report: FinalReport, output_path: Path) -> None:
        """
        Export all data to a single CSV file with sections
        
        Args:
            report: Final report to export
            output_path: Output CSV file path
        """
        logger.info(f"Generating single CSV report: {output_path}")
        
        rows = []
        
        # Summary section
        rows.append(["SUMMARY"])
        rows.append(["Submission ID", report.submission_id])
        rows.append(["Generated At", report.generated_at.isoformat()])
        rows.append(["Overall Score", f"{report.score.overall:.4f}"])
        rows.append(["Percentage", f"{report.score.percentage:.2f}%"])
        rows.append(["Grade", report.score.grade.value])
        rows.append(["Pass", "Yes" if report.score.pass_threshold else "No"])
        rows.append(["Tier", report.score.tier.display_name])
        rows.append([])
        
        # Components section
        rows.append(["COMPONENTS"])
        rows.append(["Component", "Score", "Percentage", "Weight", "Contribution", "Threshold Met"])
        for name, component in report.score.components.items():
            rows.append([
                component.component_type.display_name,
                f"{component.value:.4f}",
                f"{component.percentage:.2f}",
                f"{component.weight:.2f}",
                f"{component.weighted_contribution:.4f}",
                "Yes" if component.threshold_met else "No"
            ])
        rows.append([])
        
        # Improvements section
        rows.append(["IMPROVEMENTS"])
        rows.append(["Component", "Priority", "Current", "Target", "Impact"])
        for imp in report.improvements:
            rows.append([
                imp.component.display_name,
                imp.priority,
                f"{imp.current_value:.2f}",
                f"{imp.target_value:.2f}",
                f"{imp.impact:.4f}"
            ])
        rows.append([])
        
        # Recommendations section
        rows.append(["RECOMMENDATIONS"])
        rows.append(["Category", "Message"])
        for rec in report.recommendations:
            rows.append([
                rec.category,
                rec.message
            ])
        
        self._write_csv(output_path, rows)
        logger.info(f"Single CSV report generated: {output_path}")


# =============================================================================
# CONVENIENCE FUNCTIONS
# =============================================================================

def export_csv(report: FinalReport, output_path: Path, single_file: bool = False) -> None:
    """
    Convenience function to export CSV report(s)
    
    Args:
        report: Final report to export
        output_path: Output directory or file path
        single_file: Export to single CSV file instead of multiple files
    
    Example:
        >>> from pathlib import Path
        >>> # Multiple files
        >>> export_csv(report, Path(".tbeval/score"))
        >>> # Single file
        >>> export_csv(report, Path(".tbeval/score/results.csv"), single_file=True)
    """
    exporter = CSVExporter()
    
    if single_file:
        exporter.export_single_file(report, output_path)
    else:
        exporter.export(report, output_path)


# =============================================================================
# EXAMPLE USAGE
# =============================================================================

if __name__ == "__main__":
    import sys
    from ..models import FinalReport
    
    # Setup logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(levelname)s - %(message)s'
    )
    
    if len(sys.argv) < 2:
        print("Usage: python -m step7_score.exporters.csv_exporter <final_score.json> [--single]")
        sys.exit(1)
    
    score_file = Path(sys.argv[1])
    single_file = "--single" in sys.argv
    
    if not score_file.exists():
        print(f"Error: Score file not found: {score_file}")
        sys.exit(1)
    
    try:
        # Load report
        report = FinalReport.load(score_file)
        
        # Export to CSV
        if single_file:
            output_path = score_file.parent / "results.csv"
            export_csv(report, output_path, single_file=True)
            print(f"✓ CSV exported to: {output_path}")
        else:
            output_dir = score_file.parent / "csv"
            export_csv(report, output_dir)
            print(f"✓ CSV files exported to: {output_dir}")
        
    except Exception as e:
        print(f"✗ Error exporting CSV: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
