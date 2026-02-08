"""
JUnit XML exporter for Step 7: Scoring

Generates JUnit XML format reports for CI/CD integration.

Compatible with:
- Jenkins
- GitLab CI
- GitHub Actions
- CircleCI
- Travis CI
- Azure Pipelines

Author: TB Eval Team
Version: 0.1.0
"""

from pathlib import Path
from typing import Optional, List
from datetime import datetime
import xml.etree.ElementTree as ET
from xml.dom import minidom
import logging

from ..models import FinalReport, TierScore, ComponentScore, Improvement

logger = logging.getLogger(__name__)


# =============================================================================
# JUNIT EXPORTER
# =============================================================================

class JUnitExporter:
    """
    Export scoring results to JUnit XML format
    
    Creates XML structure:
    - testsuites: Root element
    - testsuite: One per category (components, thresholds, quality)
    - testcase: Individual checks/components
    - properties: Metadata
    - system-out: Additional details
    """
    
    def __init__(self):
        """Initialize JUnit exporter"""
        pass
    
    def export(self, report: FinalReport, output_path: Path) -> None:
        """
        Export report to JUnit XML
        
        Args:
            report: Final report to export
            output_path: Output XML file path
        """
        logger.info(f"Generating JUnit XML report: {output_path}")
        
        # Create root testsuites element
        testsuites = self._create_testsuites(report)
        
        # Pretty print XML
        xml_str = self._prettify_xml(testsuites)
        
        # Write to file
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(xml_str)
        
        logger.info(f"JUnit XML report generated: {output_path}")
    
    def _create_testsuites(self, report: FinalReport) -> ET.Element:
        """Create root testsuites element"""
        testsuites = ET.Element('testsuites')
        testsuites.set('name', 'TB Eval')
        testsuites.set('time', f"{report.total_duration_ms / 1000:.3f}")
        
        # Calculate totals
        total_tests = 0
        total_failures = 0
        total_errors = 0
        
        # Create test suites
        component_suite = self._create_component_suite(report.score)
        threshold_suite = self._create_threshold_suite(report.score)
        overall_suite = self._create_overall_suite(report)
        
        # Count tests and failures
        for suite in [component_suite, threshold_suite, overall_suite]:
            total_tests += int(suite.get('tests', 0))
            total_failures += int(suite.get('failures', 0))
            total_errors += int(suite.get('errors', 0))
            testsuites.append(suite)
        
        # Set totals
        testsuites.set('tests', str(total_tests))
        testsuites.set('failures', str(total_failures))
        testsuites.set('errors', str(total_errors))
        
        return testsuites
    
    def _create_component_suite(self, score: TierScore) -> ET.Element:
        """Create test suite for component scores"""
        suite = ET.Element('testsuite')
        suite.set('name', 'Component Scores')
        suite.set('tests', str(len(score.components)))
        
        failures = 0
        
        # Add test case for each component
        for name, component in score.components.items():
            testcase = self._create_component_testcase(name, component)
            suite.append(testcase)
            
            if not component.threshold_met:
                failures += 1
        
        suite.set('failures', str(failures))
        suite.set('errors', '0')
        
        # Add properties
        properties = ET.SubElement(suite, 'properties')
        self._add_property(properties, 'tier', score.tier.value)
        self._add_property(properties, 'overall_score', f"{score.overall:.4f}")
        self._add_property(properties, 'grade', score.grade.value)
        
        return suite
    
    def _create_component_testcase(self, name: str, component: ComponentScore) -> ET.Element:
        """Create test case for a component"""
        testcase = ET.Element('testcase')
        testcase.set('name', component.component_type.display_name)
        testcase.set('classname', f"component.{name}")
        testcase.set('time', '0')
        
        # Add system-out with details
        system_out = ET.SubElement(testcase, 'system-out')
        output_lines = [
            f"Score: {component.percentage:.2f}%",
            f"Weight: {component.weight:.2f}",
            f"Contribution: {component.weighted_contribution:.4f}",
            f"Threshold: {'Met' if component.threshold_met else 'Not Met'}",
        ]
        
        if component.details:
            output_lines.append(f"\nDetails:\n{component.details}")
        
        system_out.text = "\n".join(output_lines)
        
        # Add failure if threshold not met
        if not component.threshold_met:
            failure = ET.SubElement(testcase, 'failure')
            failure.set('type', 'ThresholdNotMet')
            failure.set('message', f"{component.component_type.display_name} score {component.percentage:.2f}% below threshold")
            
            if component.recommendations:
                failure.text = "\n".join(component.recommendations)
        
        return testcase
    
    def _create_threshold_suite(self, score: TierScore) -> ET.Element:
        """Create test suite for threshold checks"""
        suite = ET.Element('testsuite')
        suite.set('name', 'Threshold Checks')
        
        test_cases = []
        failures = 0
        
        # Overall passing threshold
        overall_case = ET.Element('testcase')
        overall_case.set('name', 'Overall Passing Grade')
        overall_case.set('classname', 'threshold.overall')
        overall_case.set('time', '0')
        
        system_out = ET.SubElement(overall_case, 'system-out')
        system_out.text = f"Score: {score.percentage:.2f}%\nGrade: {score.grade.value}\nPass: {score.pass_threshold}"
        
        if not score.pass_threshold:
            failure = ET.SubElement(overall_case, 'failure')
            failure.set('type', 'BelowPassingGrade')
            failure.set('message', f"Score {score.percentage:.2f}% below passing threshold")
            failures += 1
        
        test_cases.append(overall_case)
        
        # Individual component thresholds
        for name, component in score.components.items():
            threshold_case = ET.Element('testcase')
            threshold_case.set('name', f"{component.component_type.display_name} Threshold")
            threshold_case.set('classname', f"threshold.{name}")
            threshold_case.set('time', '0')
            
            system_out = ET.SubElement(threshold_case, 'system-out')
            system_out.text = f"Score: {component.percentage:.2f}%\nThreshold: {'Met' if component.threshold_met else 'Not Met'}"
            
            if not component.threshold_met:
                failure = ET.SubElement(threshold_case, 'failure')
                failure.set('type', 'ComponentThresholdNotMet')
                failure.set('message', f"{component.component_type.display_name} below threshold")
                failures += 1
            
            test_cases.append(threshold_case)
        
        suite.set('tests', str(len(test_cases)))
        suite.set('failures', str(failures))
        suite.set('errors', '0')
        
        for case in test_cases:
            suite.append(case)
        
        return suite
    
    def _create_overall_suite(self, report: FinalReport) -> ET.Element:
        """Create test suite for overall evaluation"""
        suite = ET.Element('testsuite')
        suite.set('name', 'Overall Evaluation')
        suite.set('tests', '1')
        
        # Single test case for overall result
        testcase = ET.Element('testcase')
        testcase.set('name', 'TB Eval Score')
        testcase.set('classname', 'overall.evaluation')
        testcase.set('time', f"{report.total_duration_ms / 1000:.3f}")
        
        # System output with summary
        system_out = ET.SubElement(testcase, 'system-out')
        output_lines = [
            f"Submission: {report.submission_id}",
            f"Score: {report.score.percentage:.2f}%",
            f"Grade: {report.score.grade.value}",
            f"Pass: {report.score.pass_threshold}",
            f"Tier: {report.score.tier.display_name}",
            f"Framework: v{report.framework_version}",
            f"Duration: {report.total_duration_ms / 1000:.2f}s",
            f"Steps: {', '.join(report.steps_completed)}",
        ]
        
        if report.improvements:
            output_lines.append(f"\nTop Improvements:")
            for imp in report.improvements[:3]:
                output_lines.append(f"  - {imp.component.display_name}: +{imp.impact:.4f} impact")
        
        system_out.text = "\n".join(output_lines)
        
        # Add failure if overall didn't pass
        if not report.score.pass_threshold:
            failure = ET.SubElement(testcase, 'failure')
            failure.set('type', 'EvaluationFailed')
            failure.set('message', f"Overall score {report.score.percentage:.2f}% below passing threshold")
            
            if report.recommendations:
                rec_text = "\n".join([f"- {rec.message}" for rec in report.recommendations[:5]])
                failure.text = f"Recommendations:\n{rec_text}"
            
            suite.set('failures', '1')
        else:
            suite.set('failures', '0')
        
        suite.set('errors', '0')
        suite.append(testcase)
        
        # Add properties
        properties = ET.SubElement(suite, 'properties')
        self._add_property(properties, 'submission_id', report.submission_id)
        self._add_property(properties, 'framework_version', report.framework_version)
        self._add_property(properties, 'tier', report.score.tier.value)
        self._add_property(properties, 'generated_at', report.generated_at.isoformat())
        
        return suite
    
    def _add_property(self, properties: ET.Element, name: str, value: str) -> None:
        """Add a property to properties element"""
        prop = ET.SubElement(properties, 'property')
        prop.set('name', name)
        prop.set('value', str(value))
    
    def _prettify_xml(self, elem: ET.Element) -> str:
        """
        Return a pretty-printed XML string
        
        Args:
            elem: XML element to prettify
        
        Returns:
            Formatted XML string with declaration
        """
        # Convert to string
        rough_string = ET.tostring(elem, encoding='unicode')
        
        # Parse and prettify
        reparsed = minidom.parseString(rough_string)
        pretty = reparsed.toprettyxml(indent="  ")
        
        # Remove extra blank lines
        lines = [line for line in pretty.split('\n') if line.strip()]
        
        return '\n'.join(lines)


# =============================================================================
# CONVENIENCE FUNCTIONS
# =============================================================================

def export_junit(report: FinalReport, output_path: Path) -> None:
    """
    Convenience function to export JUnit XML report
    
    Args:
        report: Final report to export
        output_path: Output XML file path
    
    Example:
        >>> from pathlib import Path
        >>> export_junit(report, Path(".tbeval/score/junit.xml"))
    """
    exporter = JUnitExporter()
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
        print("Usage: python -m step7_score.exporters.junit_exporter <final_score.json>")
        sys.exit(1)
    
    score_file = Path(sys.argv[1])
    
    if not score_file.exists():
        print(f"Error: Score file not found: {score_file}")
        sys.exit(1)
    
    try:
        # Load report
        report = FinalReport.load(score_file)
        
        # Export to JUnit XML
        output_path = score_file.parent / "junit.xml"
        export_junit(report, output_path)
        
        print(f"✓ JUnit XML exported to: {output_path}")
        
    except Exception as e:
        print(f"✗ Error exporting JUnit XML: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
