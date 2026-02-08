"""
PDF exporter for Step 7: Scoring

Generates professional PDF reports with:
- Title page
- Executive summary
- Score breakdown
- Component details
- Improvements and recommendations
- Charts and visualizations

Requires: reportlab library

Author: TB Eval Team
Version: 0.1.0
"""

from pathlib import Path
from typing import Optional, List, Tuple
from datetime import datetime
import logging

from ..models import FinalReport, TierScore, ComponentScore, Improvement

logger = logging.getLogger(__name__)

# Check for reportlab availability
try:
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import letter, A4
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import inch
    from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT, TA_JUSTIFY
    from reportlab.platypus import (
        SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
        PageBreak, Image, KeepTogether
    )
    from reportlab.graphics.shapes import Drawing
    from reportlab.graphics.charts.piecharts import Pie
    from reportlab.graphics.charts.barcharts import VerticalBarChart
    
    REPORTLAB_AVAILABLE = True
except ImportError:
    REPORTLAB_AVAILABLE = False
    logger.warning("reportlab not installed - PDF export not available")


# =============================================================================
# PDF EXPORTER
# =============================================================================

class PDFExporter:
    """
    Export scoring results to PDF
    
    Generates a professional PDF report with multiple sections.
    """
    
    def __init__(self, page_size=letter):
        """
        Initialize PDF exporter
        
        Args:
            page_size: Page size (letter or A4)
        """
        if not REPORTLAB_AVAILABLE:
            raise ImportError(
                "reportlab library required for PDF export. "
                "Install with: pip install reportlab"
            )
        
        self.page_size = page_size
        self.width = page_size[0]
        self.height = page_size[1]
        
        # Styles
        self.styles = getSampleStyleSheet()
        self._create_custom_styles()
        
        # Colors
        self.colors = {
            'primary': colors.HexColor('#667eea'),
            'secondary': colors.HexColor('#764ba2'),
            'success': colors.HexColor('#10b981'),
            'warning': colors.HexColor('#f59e0b'),
            'danger': colors.HexColor('#ef4444'),
            'gray': colors.HexColor('#6b7280'),
            'light_gray': colors.HexColor('#f3f4f6'),
        }
    
    def _create_custom_styles(self) -> None:
        """Create custom paragraph styles"""
        # Title style
        self.styles.add(ParagraphStyle(
            name='CustomTitle',
            parent=self.styles['Title'],
            fontSize=32,
            textColor=colors.HexColor('#667eea'),
            spaceAfter=30,
            alignment=TA_CENTER,
            fontName='Helvetica-Bold'
        ))
        
        # Heading1
        self.styles.add(ParagraphStyle(
            name='CustomHeading1',
            parent=self.styles['Heading1'],
            fontSize=20,
            textColor=colors.HexColor('#667eea'),
            spaceAfter=12,
            spaceBefore=12,
            fontName='Helvetica-Bold'
        ))
        
        # Heading2
        self.styles.add(ParagraphStyle(
            name='CustomHeading2',
            parent=self.styles['Heading2'],
            fontSize=16,
            textColor=colors.HexColor('#764ba2'),
            spaceAfter=10,
            spaceBefore=10,
            fontName='Helvetica-Bold'
        ))
        
        # Score style
        self.styles.add(ParagraphStyle(
            name='ScoreStyle',
            parent=self.styles['Normal'],
            fontSize=48,
            textColor=colors.HexColor('#667eea'),
            alignment=TA_CENTER,
            fontName='Helvetica-Bold'
        ))
        
        # Grade style
        self.styles.add(ParagraphStyle(
            name='GradeStyle',
            parent=self.styles['Normal'],
            fontSize=36,
            textColor=colors.HexColor('#764ba2'),
            alignment=TA_CENTER,
            fontName='Helvetica-Bold'
        ))
    
    def export(self, report: FinalReport, output_path: Path) -> None:
        """
        Export report to PDF
        
        Args:
            report: Final report to export
            output_path: Output PDF file path
        """
        logger.info(f"Generating PDF report: {output_path}")
        
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Create PDF document
        doc = SimpleDocTemplate(
            str(output_path),
            pagesize=self.page_size,
            rightMargin=0.75*inch,
            leftMargin=0.75*inch,
            topMargin=0.75*inch,
            bottomMargin=0.75*inch,
        )
        
        # Build content
        story = []
        
        # Title page
        story.extend(self._create_title_page(report))
        story.append(PageBreak())
        
        # Executive summary
        story.extend(self._create_executive_summary(report))
        story.append(PageBreak())
        
        # Component breakdown
        story.extend(self._create_component_breakdown(report.score))
        story.append(PageBreak())
        
        # Improvements
        if report.improvements:
            story.extend(self._create_improvements_section(report.improvements))
            story.append(PageBreak())
        
        # Recommendations
        if report.recommendations:
            story.extend(self._create_recommendations_section(report.recommendations))
        
        # Build PDF
        doc.build(story)
        
        logger.info(f"PDF report generated: {output_path}")
    
    def _create_title_page(self, report: FinalReport) -> List:
        """Create title page"""
        elements = []
        
        # Spacer
        elements.append(Spacer(1, 2*inch))
        
        # Title
        elements.append(Paragraph(
            "TB Eval Score Report",
            self.styles['CustomTitle']
        ))
        
        elements.append(Spacer(1, 0.5*inch))
        
        # Submission ID
        elements.append(Paragraph(
            f"<font size=18><b>{report.submission_id}</b></font>",
            self.styles['Normal']
        ))
        
        elements.append(Spacer(1, 1*inch))
        
        # Score display
        elements.append(Paragraph(
            f"{report.score.percentage:.1f}%",
            self.styles['ScoreStyle']
        ))
        
        elements.append(Spacer(1, 0.25*inch))
        
        # Grade display
        grade_color = self._get_grade_color(report.score.grade.value)
        elements.append(Paragraph(
            f"<font color='{grade_color}'>Grade: {report.score.grade.value}</font>",
            self.styles['GradeStyle']
        ))
        
        elements.append(Spacer(1, 0.5*inch))
        
        # Pass/Fail badge
        if report.score.pass_threshold:
            badge_text = "<font color='#10b981' size=24><b>✓ PASS</b></font>"
        else:
            badge_text = "<font color='#ef4444' size=24><b>✗ FAIL</b></font>"
        
        elements.append(Paragraph(badge_text, self.styles['Normal']))
        
        elements.append(Spacer(1, 1*inch))
        
        # Metadata
        info_data = [
            ['Tier:', report.score.tier.display_name],
            ['Generated:', report.generated_at.strftime('%Y-%m-%d %H:%M:%S')],
            ['Framework:', f'v{report.framework_version}'],
            ['Duration:', f'{report.total_duration_ms / 1000:.2f}s'],
        ]
        
        info_table = Table(info_data, colWidths=[2*inch, 3*inch])
        info_table.setStyle(TableStyle([
            ('FONT', (0, 0), (-1, -1), 'Helvetica', 11),
            ('FONT', (0, 0), (0, -1), 'Helvetica-Bold', 11),
            ('TEXTCOLOR', (0, 0), (0, -1), self.colors['gray']),
            ('ALIGN', (0, 0), (0, -1), 'RIGHT'),
            ('ALIGN', (1, 0), (1, -1), 'LEFT'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ]))
        
        elements.append(info_table)
        
        return elements
    
    def _create_executive_summary(self, report: FinalReport) -> List:
        """Create executive summary section"""
        elements = []
        
        elements.append(Paragraph(
            "Executive Summary",
            self.styles['CustomHeading1']
        ))
        
        elements.append(Spacer(1, 0.25*inch))
        
        # Summary table
        summary_data = [
            ['Overall Score', f"{report.score.percentage:.2f}%"],
            ['Grade', report.score.grade.value],
            ['Pass Threshold', 'Met' if report.score.pass_threshold else 'Not Met'],
            ['Tier', report.score.tier.display_name],
            ['Components Evaluated', str(len(report.score.components))],
        ]
        
        summary_table = Table(summary_data, colWidths=[2.5*inch, 2.5*inch])
        summary_table.setStyle(TableStyle([
            ('FONT', (0, 0), (-1, -1), 'Helvetica', 12),
            ('FONT', (0, 0), (0, -1), 'Helvetica-Bold', 12),
            ('BACKGROUND', (0, 0), (-1, 0), self.colors['light_gray']),
            ('TEXTCOLOR', (0, 0), (0, -1), self.colors['primary']),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('GRID', (0, 0), (-1, -1), 0.5, self.colors['gray']),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, self.colors['light_gray']]),
        ]))
        
        elements.append(summary_table)
        
        elements.append(Spacer(1, 0.5*inch))
        
        # Component scores chart
        if report.score.components:
            elements.append(Paragraph(
                "Component Scores",
                self.styles['CustomHeading2']
            ))
            
            elements.append(Spacer(1, 0.25*inch))
            
            chart = self._create_component_chart(report.score)
            if chart:
                elements.append(chart)
        
        return elements
    
    def _create_component_chart(self, score: TierScore) -> Optional[Drawing]:
        """Create component scores bar chart"""
        if not score.components:
            return None
        
        drawing = Drawing(400, 200)
        
        # Prepare data
        comp_names = []
        comp_scores = []
        
        for name, component in sorted(
            score.components.items(),
            key=lambda x: x[1].weight,
            reverse=True
        ):
            comp_names.append(component.component_type.display_name[:15])
            comp_scores.append(component.percentage)
        
        # Create bar chart
        chart = VerticalBarChart()
        chart.x = 50
        chart.y = 50
        chart.height = 125
        chart.width = 300
        chart.data = [comp_scores]
        chart.categoryAxis.categoryNames = comp_names
        chart.categoryAxis.labels.angle = 45
        chart.categoryAxis.labels.fontSize = 8
        chart.valueAxis.valueMin = 0
        chart.valueAxis.valueMax = 100
        chart.valueAxis.valueStep = 20
        
        # Bar colors
        chart.bars[0].fillColor = self.colors['primary']
        
        drawing.add(chart)
        
        return drawing
    
    def _create_component_breakdown(self, score: TierScore) -> List:
        """Create component breakdown section"""
        elements = []
        
        elements.append(Paragraph(
            "Component Breakdown",
            self.styles['CustomHeading1']
        ))
        
        elements.append(Spacer(1, 0.25*inch))
        
        # Sort by weight (highest first)
        sorted_components = sorted(
            score.components.items(),
            key=lambda x: x[1].weight,
            reverse=True
        )
        
        for name, component in sorted_components:
            comp_elements = self._create_component_detail(component)
            elements.extend(comp_elements)
            elements.append(Spacer(1, 0.25*inch))
        
        return elements
    
    def _create_component_detail(self, component: ComponentScore) -> List:
        """Create detail section for a component"""
        elements = []
        
        # Component header
        elements.append(Paragraph(
            f"<b>{component.component_type.display_name}</b>",
            self.styles['CustomHeading2']
        ))
        
        # Component table
        status = '✓ Pass' if component.threshold_met else '✗ Fail'
        status_color = '#10b981' if component.threshold_met else '#ef4444'
        
        comp_data = [
            ['Score', f"{component.percentage:.2f}%"],
            ['Grade', component.grade.value],
            ['Weight', f"{component.weight:.0%}"],
            ['Contribution', f"{component.weighted_contribution:.4f}"],
            ['Status', f"<font color='{status_color}'><b>{status}</b></font>"],
        ]
        
        comp_table = Table(comp_data, colWidths=[1.5*inch, 3*inch])
        comp_table.setStyle(TableStyle([
            ('FONT', (0, 0), (-1, -1), 'Helvetica', 10),
            ('FONT', (0, 0), (0, -1), 'Helvetica-Bold', 10),
            ('ALIGN', (0, 0), (0, -1), 'RIGHT'),
            ('ALIGN', (1, 0), (1, -1), 'LEFT'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ]))
        
        elements.append(comp_table)
        
        # Recommendations
        if component.recommendations:
            elements.append(Spacer(1, 0.1*inch))
            elements.append(Paragraph(
                "<b>Recommendations:</b>",
                self.styles['Normal']
            ))
            
            for rec in component.recommendations[:3]:
                elements.append(Paragraph(
                    f"• {rec}",
                    self.styles['Normal']
                ))
        
        return elements
    
    def _create_improvements_section(self, improvements: List[Improvement]) -> List:
        """Create improvements section"""
        elements = []
        
        elements.append(Paragraph(
            "Recommended Improvements",
            self.styles['CustomHeading1']
        ))
        
        elements.append(Spacer(1, 0.25*inch))
        
        # Show top 10 improvements
        for i, imp in enumerate(improvements[:10], 1):
            imp_elements = self._create_improvement_detail(i, imp)
            elements.extend(imp_elements)
            elements.append(Spacer(1, 0.2*inch))
        
        return elements
    
    def _create_improvement_detail(self, rank: int, improvement: Improvement) -> List:
        """Create detail for an improvement"""
        elements = []
        
        # Priority badge color
        priority_colors = {
            'high': '#ef4444',
            'medium': '#f59e0b',
            'low': '#10b981',
        }
        priority_color = priority_colors.get(improvement.priority, '#6b7280')
        
        # Header
        header_text = (
            f"<b>{rank}. {improvement.component.display_name}</b> "
            f"<font color='{priority_color}'>[{improvement.priority.upper()}]</font>"
        )
        elements.append(Paragraph(header_text, self.styles['Normal']))
        
        # Metrics
        metrics_text = (
            f"Current: {improvement.current_value:.1f}% → "
            f"Target: {improvement.target_value:.1f}% "
            f"(Impact: +{improvement.impact:.4f} points)"
        )
        elements.append(Paragraph(
            f"<font size=9>{metrics_text}</font>",
            self.styles['Normal']
        ))
        
        # Actions
        if improvement.actions:
            elements.append(Paragraph(
                "<font size=9><b>Actions:</b></font>",
                self.styles['Normal']
            ))
            
            for action in improvement.actions[:3]:
                elements.append(Paragraph(
                    f"<font size=9>  • {action}</font>",
                    self.styles['Normal']
                ))
        
        return elements
    
    def _create_recommendations_section(self, recommendations) -> List:
        """Create recommendations section"""
        elements = []
        
        elements.append(Paragraph(
            "General Recommendations",
            self.styles['CustomHeading1']
        ))
        
        elements.append(Spacer(1, 0.25*inch))
        
        for i, rec in enumerate(recommendations, 1):
            elements.append(Paragraph(
                f"<b>{i}. [{rec.category}]</b>",
                self.styles['Normal']
            ))
            
            elements.append(Paragraph(
                rec.message,
                self.styles['Normal']
            ))
            
            if rec.details:
                elements.append(Paragraph(
                    f"<i>{rec.details}</i>",
                    self.styles['Normal']
                ))
            
            elements.append(Spacer(1, 0.15*inch))
        
        return elements
    
    def _get_grade_color(self, grade: str) -> str:
        """Get color for grade"""
        grade_colors = {
            'A': '#10b981',
            'B': '#3b82f6',
            'C': '#f59e0b',
            'D': '#f97316',
            'F': '#ef4444',
        }
        return grade_colors.get(grade, '#6b7280')


# =============================================================================
# CONVENIENCE FUNCTIONS
# =============================================================================

def export_pdf(report: FinalReport, output_path: Path, page_size=letter) -> None:
    """
    Convenience function to export PDF report
    
    Args:
        report: Final report to export
        output_path: Output PDF file path
        page_size: Page size (letter or A4)
    
    Raises:
        ImportError: If reportlab not installed
    
    Example:
        >>> from pathlib import Path
        >>> export_pdf(report, Path(".tbeval/score/report.pdf"))
    """
    exporter = PDFExporter(page_size=page_size)
    exporter.export(report, output_path)


def is_pdf_export_available() -> bool:
    """
    Check if PDF export is available
    
    Returns:
        True if reportlab is installed
    """
    return REPORTLAB_AVAILABLE


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
    
    if not REPORTLAB_AVAILABLE:
        print("Error: reportlab not installed")
        print("Install with: pip install reportlab")
        sys.exit(1)
    
    if len(sys.argv) < 2:
        print("Usage: python -m step7_score.exporters.pdf_exporter <final_score.json>")
        sys.exit(1)
    
    score_file = Path(sys.argv[1])
    
    if not score_file.exists():
        print(f"Error: Score file not found: {score_file}")
        sys.exit(1)
    
    try:
        # Load report
        report = FinalReport.load(score_file)
        
        # Export to PDF
        output_path = score_file.parent / "report.pdf"
        export_pdf(report, output_path)
        
        print(f"✓ PDF exported to: {output_path}")
        
    except Exception as e:
        print(f"✗ Error exporting PDF: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
