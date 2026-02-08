"""
Exporters for Step 7: Scoring

Export formats:
- JSON: Machine-readable (always available)
- HTML: Interactive dashboard (always available)
- JUnit: CI/CD integration (always available)
- CSV: Spreadsheet analysis (always available)
- PDF: Professional reports (requires reportlab)

Quick Start:
    >>> from step7_score.exporters import export_html, export_junit
    >>> from step7_score.models import FinalReport
    >>> 
    >>> report = FinalReport.load("final_score.json")
    >>> export_html(report, "report.html")
    >>> export_junit(report, "junit.xml")

Author: TB Eval Team
Version: 0.1.0
"""

from pathlib import Path
from typing import Optional
import logging

from ..models import FinalReport

logger = logging.getLogger(__name__)

# =============================================================================
# EXPORTER IMPORTS
# =============================================================================

# HTML Exporter (always available)
from .html_exporter import (
    HTMLExporter,
    export_html as _export_html,
)

# JUnit Exporter (always available)
from .junit_exporter import (
    JUnitExporter,
    export_junit as _export_junit,
)

# CSV Exporter (always available)
from .csv_exporter import (
    CSVExporter,
    export_csv as _export_csv,
)

# PDF Exporter (optional - requires reportlab)
try:
    from .pdf_exporter import (
        PDFExporter,
        export_pdf as _export_pdf,
        is_pdf_export_available as _is_pdf_available,
        REPORTLAB_AVAILABLE,
    )
    PDF_AVAILABLE = True
except ImportError:
    PDF_AVAILABLE = False
    REPORTLAB_AVAILABLE = False
    logger.debug("PDF export not available (reportlab not installed)")

# =============================================================================
# PUBLIC API
# =============================================================================

__all__ = [
    # Exporter classes
    "HTMLExporter",
    "JUnitExporter",
    "CSVExporter",
    "PDFExporter",
    
    # Convenience functions
    "export_html",
    "export_junit",
    "export_csv",
    "export_pdf",
    "export_all",
    
    # Utilities
    "is_pdf_export_available",
    "get_available_formats",
]

# =============================================================================
# CONVENIENCE FUNCTIONS
# =============================================================================

def export_html(report: FinalReport, output_path: Path) -> None:
    """
    Export report to HTML
    
    Args:
        report: Final report to export
        output_path: Output HTML file path
    
    Example:
        >>> export_html(report, Path("report.html"))
    """
    _export_html(report, output_path)


def export_junit(report: FinalReport, output_path: Path) -> None:
    """
    Export report to JUnit XML
    
    Args:
        report: Final report to export
        output_path: Output XML file path
    
    Example:
        >>> export_junit(report, Path("junit.xml"))
    """
    _export_junit(report, output_path)


def export_csv(
    report: FinalReport,
    output_path: Path,
    single_file: bool = False
) -> None:
    """
    Export report to CSV
    
    Args:
        report: Final report to export
        output_path: Output directory or CSV file path
        single_file: Export to single CSV file instead of multiple
    
    Example:
        >>> export_csv(report, Path(".tbeval/score"))  # Multiple files
        >>> export_csv(report, Path("results.csv"), single_file=True)  # Single file
    """
    _export_csv(report, output_path, single_file)


def export_pdf(
    report: FinalReport,
    output_path: Path,
    page_size: Optional[str] = "letter"
) -> None:
    """
    Export report to PDF
    
    Args:
        report: Final report to export
        output_path: Output PDF file path
        page_size: Page size ('letter' or 'A4')
    
    Raises:
        ImportError: If reportlab not installed
    
    Example:
        >>> export_pdf(report, Path("report.pdf"))
        >>> export_pdf(report, Path("report.pdf"), page_size="A4")
    """
    if not PDF_AVAILABLE:
        raise ImportError(
            "PDF export requires reportlab library. "
            "Install with: pip install reportlab"
        )
    
    from reportlab.lib.pagesizes import letter, A4
    page = A4 if page_size.lower() == "a4" else letter
    
    _export_pdf(report, output_path, page_size=page)


def export_all(
    report: FinalReport,
    output_dir: Path,
    formats: Optional[list] = None,
    base_name: str = "report"
) -> dict:
    """
    Export report in multiple formats
    
    Args:
        report: Final report to export
        output_dir: Output directory
        formats: List of formats to export (default: all available)
        base_name: Base filename (default: "report")
    
    Returns:
        Dictionary mapping format to output path
    
    Example:
        >>> paths = export_all(report, Path(".tbeval/score"))
        >>> print(paths["html"])  # Path to HTML report
        >>> 
        >>> # Export specific formats
        >>> paths = export_all(report, Path("out"), formats=["html", "json"])
    """
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Default to all available formats
    if formats is None:
        formats = get_available_formats()
    
    results = {}
    
    # JSON (built into FinalReport)
    if "json" in formats:
        json_path = output_dir / f"{base_name}.json"
        report.save(json_path)
        results["json"] = json_path
        logger.info(f"Exported JSON: {json_path}")
    
    # HTML
    if "html" in formats:
        html_path = output_dir / f"{base_name}.html"
        try:
            export_html(report, html_path)
            results["html"] = html_path
            logger.info(f"Exported HTML: {html_path}")
        except Exception as e:
            logger.error(f"HTML export failed: {e}")
    
    # JUnit
    if "junit" in formats:
        junit_path = output_dir / "junit.xml"
        try:
            export_junit(report, junit_path)
            results["junit"] = junit_path
            logger.info(f"Exported JUnit: {junit_path}")
        except Exception as e:
            logger.error(f"JUnit export failed: {e}")
    
    # CSV
    if "csv" in formats:
        csv_dir = output_dir / "csv"
        try:
            export_csv(report, csv_dir)
            results["csv"] = csv_dir
            logger.info(f"Exported CSV: {csv_dir}")
        except Exception as e:
            logger.error(f"CSV export failed: {e}")
    
    # PDF
    if "pdf" in formats and PDF_AVAILABLE:
        pdf_path = output_dir / f"{base_name}.pdf"
        try:
            export_pdf(report, pdf_path)
            results["pdf"] = pdf_path
            logger.info(f"Exported PDF: {pdf_path}")
        except Exception as e:
            logger.error(f"PDF export failed: {e}")
    elif "pdf" in formats:
        logger.warning("PDF export requested but reportlab not installed")
    
    return results


# =============================================================================
# UTILITY FUNCTIONS
# =============================================================================

def is_pdf_export_available() -> bool:
    """
    Check if PDF export is available
    
    Returns:
        True if reportlab is installed
    
    Example:
        >>> if is_pdf_export_available():
        ...     export_pdf(report, "report.pdf")
        ... else:
        ...     print("Install reportlab for PDF export")
    """
    return PDF_AVAILABLE and REPORTLAB_AVAILABLE


def get_available_formats() -> list:
    """
    Get list of available export formats
    
    Returns:
        List of format names
    
    Example:
        >>> formats = get_available_formats()
        >>> print(formats)  # ['json', 'html', 'junit', 'csv', 'pdf']
    """
    formats = ["json", "html", "junit", "csv"]
    
    if is_pdf_export_available():
        formats.append("pdf")
    
    return formats


def print_export_info() -> None:
    """Print information about available exporters"""
    print("Available Export Formats:")
    print("  ✓ JSON  - Machine-readable structured data")
    print("  ✓ HTML  - Interactive dashboard")
    print("  ✓ JUnit - CI/CD integration (Jenkins, GitLab, GitHub Actions)")
    print("  ✓ CSV   - Spreadsheet analysis")
    
    if is_pdf_export_available():
        print("  ✓ PDF   - Professional reports")
    else:
        print("  ✗ PDF   - Not available (install reportlab)")


# =============================================================================
# BATCH EXPORT HELPER
# =============================================================================

class BatchExporter:
    """
    Helper class for batch exporting multiple reports
    
    Example:
        >>> exporter = BatchExporter(output_dir=Path("reports"))
        >>> for report in reports:
        ...     exporter.add(report, formats=["html", "json"])
        >>> exporter.export_all()
    """
    
    def __init__(self, output_dir: Path):
        """
        Initialize batch exporter
        
        Args:
            output_dir: Base output directory
        """
        self.output_dir = Path(output_dir)
        self.reports = []
    
    def add(
        self,
        report: FinalReport,
        formats: Optional[list] = None,
        subdir: Optional[str] = None
    ) -> None:
        """
        Add report to batch
        
        Args:
            report: Report to export
            formats: Export formats
            subdir: Subdirectory name (default: submission_id)
        """
        if subdir is None:
            subdir = report.submission_id
        
        self.reports.append({
            "report": report,
            "formats": formats,
            "subdir": subdir,
        })
    
    def export_all(self) -> dict:
