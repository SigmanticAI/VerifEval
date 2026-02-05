"""
JUnit XML reporter

Generates JUnit XML format reports for CI/CD integration.

JUnit XML is widely supported by:
- Jenkins
- GitLab CI
- GitHub Actions
- Azure DevOps
- CircleCI
- And many other CI/CD systems

Author: TB Eval Team
Version: 0.1.0
"""

import xml.etree.ElementTree as ET
from xml.dom import minidom
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime
import re

from ..models import TestReport, TestResult, TestOutcome


class JUnitReporter:
    """
    Generates JUnit XML reports
    
    Features:
    - Full JUnit XML schema compliance
    - Test suite organization
    - System properties
    - stdout/stderr capture
    - Multiple test suite support
    - Pretty-printed XML
    """
    
    def __init__(
        self,
        report: TestReport,
        suite_name: Optional[str] = None,
        include_system_properties: bool = True,
    ):
        """
        Initialize JUnit reporter
        
        Args:
            report: TestReport to convert
            suite_name: Optional test suite name (default: auto-generated)
            include_system_properties: Whether to include system properties
        """
        self.report = report
        self.suite_name = suite_name or self._generate_suite_name()
        self.include_system_properties = include_system_properties
    
    def generate(self, output_path: Path, pretty: bool = True) -> Path:
        """
        Generate JUnit XML report
        
        Args:
            output_path: Where to save the XML file
            pretty: Whether to pretty-print the XML
        
        Returns:
            Path to generated file
        """
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Build XML tree
        root = self._build_testsuites()
        
        # Convert to string
        if pretty:
            xml_string = self._prettify(root)
        else:
            xml_string = ET.tostring(root, encoding='unicode', method='xml')
        
        # Write to file
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write('<?xml version="1.0" encoding="UTF-8"?>\n')
            f.write(xml_string)
        
        return output_path
    
    def _build_testsuites(self) -> ET.Element:
        """
        Build <testsuites> root element
        
        Returns:
            XML Element
        """
        summary = self.report.summary
        
        # Create root element
        testsuites = ET.Element('testsuites')
        testsuites.set('name', self.suite_name)
        testsuites.set('tests', str(summary.total_tests))
        testsuites.set('failures', str(summary.failed))
        testsuites.set('errors', str(summary.errors))
        testsuites.set('skipped', str(summary.skipped))
        testsuites.set('time', str(summary.total_duration_ms / 1000.0))
        
        # Add timestamp
        if self.report.execution_metadata:
            testsuites.set('timestamp', self.report.execution_metadata.timestamp)
        
        # Group tests by suite (by module/class)
        suites = self._group_tests_by_suite()
        
        # Create testsuite elements
        for suite_name, tests in suites.items():
            testsuite = self._build_testsuite(suite_name, tests)
            testsuites.append(testsuite)
        
        return testsuites
    
    def _build_testsuite(
        self,
        suite_name: str,
        tests: List[TestResult]
    ) -> ET.Element:
        """
        Build <testsuite> element
        
        Args:
            suite_name: Test suite name
            tests: Tests in this suite
        
        Returns:
            XML Element
        """
        # Calculate suite statistics
        failures = sum(1 for t in tests if t.outcome == TestOutcome.FAILED)
        errors = sum(1 for t in tests if t.outcome == TestOutcome.ERROR)
        skipped = sum(1 for t in tests if t.outcome == TestOutcome.SKIPPED)
        time = sum(t.duration_ms for t in tests) / 1000.0
        
        # Create testsuite element
        testsuite = ET.Element('testsuite')
        testsuite.set('name', suite_name)
        testsuite.set('tests', str(len(tests)))
        testsuite.set('failures', str(failures))
        testsuite.set('errors', str(errors))
        testsuite.set('skipped', str(skipped))
        testsuite.set('time', str(time))
        
        # Add timestamp
        if self.report.execution_metadata:
            testsuite.set('timestamp', self.report.execution_metadata.timestamp)
        
        # Add hostname
        if self.report.execution_metadata and self.report.execution_metadata.hostname:
            testsuite.set('hostname', self.report.execution_metadata.hostname)
        
        # Add system properties
        if self.include_system_properties:
            properties = self._build_properties()
            if properties is not None:
                testsuite.append(properties)
        
        # Add testcases
        for test in tests:
            testcase = self._build_testcase(test)
            testsuite.append(testcase)
        
        # Add system-out and system-err at suite level (if any)
        suite_stdout = self._get_suite_stdout(tests)
        if suite_stdout:
            system_out = ET.SubElement(testsuite, 'system-out')
            system_out.text = self._escape_cdata(suite_stdout)
        
        suite_stderr = self._get_suite_stderr(tests)
        if suite_stderr:
            system_err = ET.SubElement(testsuite, 'system-err')
            system_err.text = self._escape_cdata(suite_stderr)
        
        return testsuite
    
    def _build_testcase(self, test: TestResult) -> ET.Element:
        """
        Build <testcase> element
        
        Args:
            test: Test result
        
        Returns:
            XML Element
        """
        # Create testcase element
        testcase = ET.Element('testcase')
        
        # Set attributes
        testcase.set('name', test.name)
        testcase.set('classname', self._get_classname(test))
        testcase.set('time', str(test.duration_ms / 1000.0))
        
        # Add file location if available
        if test.artifacts.log_file:
            testcase.set('file', test.artifacts.log_file)
        
        # Handle test outcome
        if test.outcome == TestOutcome.FAILED:
            failure = self._build_failure(test)
            testcase.append(failure)
        
        elif test.outcome == TestOutcome.ERROR:
            error = self._build_error(test)
            testcase.append(error)
        
        elif test.outcome == TestOutcome.SKIPPED:
            skipped = self._build_skipped(test)
            testcase.append(skipped)
        
        elif test.outcome == TestOutcome.TIMEOUT:
            # Timeout is treated as error
            error = ET.SubElement(testcase, 'error')
            error.set('message', 'Test timed out')
            error.set('type', 'Timeout')
            if test.message:
                error.text = self._escape_cdata(test.message)
        
        # Add stdout
        if test.stdout:
            system_out = ET.SubElement(testcase, 'system-out')
            system_out.text = self._escape_cdata(test.stdout)
        
        # Add stderr
        if test.stderr:
            system_err = ET.SubElement(testcase, 'system-err')
            system_err.text = self._escape_cdata(test.stderr)
        
        return testcase
    
    def _build_failure(self, test: TestResult) -> ET.Element:
        """Build <failure> element"""
        failure = ET.Element('failure')
        
        # Set message
        message = test.message or "Test failed"
        failure.set('message', self._sanitize_xml(message))
        
        # Set type (try to extract from message)
        failure_type = self._extract_failure_type(test)
        failure.set('type', failure_type)
        
        # Set text content (traceback or details)
        content = test.traceback or test.details or test.message or ""
        if content:
            failure.text = self._escape_cdata(content)
        
        return failure
    
    def _build_error(self, test: TestResult) -> ET.Element:
        """Build <error> element"""
        error = ET.Element('error')
        
        # Set message
        message = test.message or "Test error"
        error.set('message', self._sanitize_xml(message))
        
        # Set type
        error_type = self._extract_error_type(test)
        error.set('type', error_type)
        
        # Set text content
        content = test.traceback or test.details or test.message or ""
        if content:
            error.text = self._escape_cdata(content)
        
        return error
    
    def _build_skipped(self, test: TestResult) -> ET.Element:
        """Build <skipped> element"""
        skipped = ET.Element('skipped')
        
        # Set message if available
        if test.message:
            skipped.set('message', self._sanitize_xml(test.message))
        
        return skipped
    
    def _build_properties(self) -> Optional[ET.Element]:
        """Build <properties> element with system properties"""
        if not self.report.execution_metadata:
            return None
        
        properties = ET.Element('properties')
        
        metadata = self.report.execution_metadata
        
        # Add standard properties
        props = {
            'framework.version': self.report.framework_version,
            'python.version': metadata.python_version,
            'hostname': metadata.hostname,
            'username': metadata.username,
            'working.directory': metadata.working_directory,
            'timestamp': metadata.timestamp,
        }
        
        # Add environment variables if available
        if metadata.environment:
            for key, value in metadata.environment.items():
                props[f'env.{key}'] = value
        
        # Create property elements
        for name, value in props.items():
            if value:
                prop = ET.SubElement(properties, 'property')
                prop.set('name', name)
                prop.set('value', str(value))
        
        return properties if len(properties) > 0 else None
    
    def _group_tests_by_suite(self) -> Dict[str, List[TestResult]]:
        """
        Group tests by suite (module/class)
        
        Returns:
            Dictionary mapping suite name to tests
        """
        suites = {}
        
        for test in self.report.results:
            suite_name = self._get_suite_name(test)
            
            if suite_name not in suites:
                suites[suite_name] = []
            
            suites[suite_name].append(test)
        
        return suites
    
    def _get_suite_name(self, test: TestResult) -> str:
        """Extract suite name from test"""
        # Try to extract from full_name
        # e.g., "work.tb_adder.test_basic" -> "work.tb_adder"
        parts = test.full_name.split('.')
        
        if len(parts) > 1:
            return '.'.join(parts[:-1])
        
        return "default"
    
    def _get_classname(self, test: TestResult) -> str:
        """Extract classname from test"""
        # Use suite name as classname
        return self._get_suite_name(test)
    
    def _extract_failure_type(self, test: TestResult) -> str:
        """Extract failure type from test"""
        if test.message:
            # Try to extract exception type
            # e.g., "AssertionError: ..." -> "AssertionError"
            match = re.match(r'^([A-Za-z_][A-Za-z0-9_]*(?:Error|Exception|Failure)):', test.message)
            if match:
                return match.group(1)
        
        return "Failure"
    
    def _extract_error_type(self, test: TestResult) -> str:
        """Extract error type from test"""
        if test.message:
            # Try to extract exception type
            match = re.match(r'^([A-Za-z_][A-Za-z0-9_]*(?:Error|Exception)):', test.message)
            if match:
                return match.group(1)
        
        return "Error"
    
    def _get_suite_stdout(self, tests: List[TestResult]) -> Optional[str]:
        """Get combined stdout for suite"""
        # Optionally combine all test stdout
        # For now, return None to avoid duplication
        return None
    
    def _get_suite_stderr(self, tests: List[TestResult]) -> Optional[str]:
        """Get combined stderr for suite"""
        # Optionally combine all test stderr
        return None
    
    def _generate_suite_name(self) -> str:
        """Generate test suite name"""
        if self.report.execution_metadata:
            # Use working directory name
            wd = self.report.execution_metadata.working_directory
            if wd:
                return Path(wd).name
        
        return "TestSuite"
    
    def _sanitize_xml(self, text: str) -> str:
        """
        Sanitize text for XML attribute
        
        Removes invalid XML characters
        
        Args:
            text: Text to sanitize
        
        Returns:
            Sanitized text
        """
        if not text:
            return ""
        
        # Remove control characters except tab, newline, carriage return
        sanitized = re.sub(r'[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]', '', text)
        
        # Limit length for attributes
        if len(sanitized) > 1000:
            sanitized = sanitized[:997] + "..."
        
        return sanitized
    
    def _escape_cdata(self, text: str) -> str:
        """
        Escape text for CDATA section
        
        Args:
            text: Text to escape
        
        Returns:
            Escaped text
        """
        if not text:
            return ""
        
        # Sanitize first
        sanitized = self._sanitize_xml(text)
        
        # XML special characters are automatically escaped by ElementTree
        return sanitized
    
    def _prettify(self, elem: ET.Element) -> str:
        """
        Pretty-print XML
        
        Args:
            elem: XML Element
        
        Returns:
            Pretty-printed XML string
        """
        # Convert to string
        rough_string = ET.tostring(elem, encoding='unicode', method='xml')
        
        # Parse with minidom for pretty printing
        try:
            reparsed = minidom.parseString(rough_string)
            pretty = reparsed.toprettyxml(indent="  ")
            
            # Remove extra blank lines
            lines = [line for line in pretty.split('\n') if line.strip()]
            
            # Remove XML declaration (we add it separately)
            if lines and lines[0].startswith('<?xml'):
                lines = lines[1:]
            
            return '\n'.join(lines)
        
        except Exception:
            # Fall back to non-pretty version
            return rough_string


class JUnitValidator:
    """
    Validates JUnit XML files
    """
    
    @staticmethod
    def validate(xml_path: Path) -> tuple[bool, List[str]]:
        """
        Validate JUnit XML file
        
        Args:
            xml_path: Path to XML file
        
        Returns:
            Tuple of (is_valid, list_of_errors)
        """
        errors = []
        
        # Check file exists
        if not xml_path.exists():
            return False, ["File does not exist"]
        
        # Try to parse XML
        try:
            tree = ET.parse(xml_path)
            root = tree.getroot()
        except ET.ParseError as e:
            return False, [f"XML parse error: {e}"]
        
        # Validate structure
        if root.tag not in ['testsuites', 'testsuite']:
            errors.append(f"Unexpected root element: {root.tag}")
        
        # Validate required attributes
        if root.tag == 'testsuites':
            required_attrs = ['tests']
            for attr in required_attrs:
                if attr not in root.attrib:
                    errors.append(f"Missing required attribute: {attr}")
            
            # Check for testsuite children
            testsuites = root.findall('testsuite')
            if not testsuites:
                errors.append("No testsuite elements found")
        
        # Validate testcases
        testcases = root.findall('.//testcase')
        for idx, testcase in enumerate(testcases):
            if 'name' not in testcase.attrib:
                errors.append(f"Testcase {idx}: missing 'name' attribute")
            
            if 'classname' not in testcase.attrib:
                errors.append(f"Testcase {idx}: missing 'classname' attribute")
        
        is_valid = len(errors) == 0
        return is_valid, errors


class JUnitMerger:
    """
    Merges multiple JUnit XML files
    
    Useful for combining test results from multiple runs.
    """
    
    @staticmethod
    def merge(xml_paths: List[Path], output_path: Path) -> Path:
        """
        Merge multiple JUnit XML files
        
        Args:
            xml_paths: Paths to XML files to merge
            output_path: Where to save merged file
        
        Returns:
            Path to merged file
        """
        # Create root testsuites element
        merged_root = ET.Element('testsuites')
        merged_root.set('name', 'MergedTestSuites')
        
        total_tests = 0
        total_failures = 0
        total_errors = 0
        total_skipped = 0
        total_time = 0.0
        
        # Load and merge each file
        for xml_path in xml_paths:
            if not xml_path.exists():
                continue
            
            try:
                tree = ET.parse(xml_path)
                root = tree.getroot()
                
                # Handle both testsuites and testsuite roots
                if root.tag == 'testsuites':
                    for testsuite in root.findall('testsuite'):
                        merged_root.append(testsuite)
                        
                        # Accumulate stats
                        total_tests += int(testsuite.get('tests', '0'))
                        total_failures += int(testsuite.get('failures', '0'))
                        total_errors += int(testsuite.get('errors', '0'))
                        total_skipped += int(testsuite.get('skipped', '0'))
                        total_time += float(testsuite.get('time', '0'))
                
                elif root.tag == 'testsuite':
                    merged_root.append(root)
                    
                    total_tests += int(root.get('tests', '0'))
                    total_failures += int(root.get('failures', '0'))
                    total_errors += int(root.get('errors', '0'))
                    total_skipped += int(root.get('skipped', '0'))
                    total_time += float(root.get('time', '0'))
            
            except Exception as e:
                print(f"Warning: Failed to merge {xml_path}: {e}")
                continue
        
        # Set merged statistics
        merged_root.set('tests', str(total_tests))
        merged_root.set('failures', str(total_failures))
        merged_root.set('errors', str(total_errors))
        merged_root.set('skipped', str(total_skipped))
        merged_root.set('time', str(total_time))
        
        # Write merged file
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        tree = ET.ElementTree(merged_root)
        tree.write(output_path, encoding='utf-8', xml_declaration=True)
        
        return output_path


# Utility functions

def generate_junit(report: TestReport, output_path: Path) -> Path:
    """
    Convenience function to generate JUnit XML
    
    Args:
        report: TestReport to convert
        output_path: Where to save XML
    
    Returns:
        Path to generated file
    """
    reporter = JUnitReporter(report)
    return reporter.generate(output_path)


def validate_junit(xml_path: Path) -> tuple[bool, List[str]]:
    """
    Convenience function to validate JUnit XML
    
    Args:
        xml_path: Path to XML file
    
    Returns:
        Tuple of (is_valid, list_of_errors)
    """
    return JUnitValidator.validate(xml_path)


def merge_junit(xml_paths: List[Path], output_path: Path) -> Path:
    """
    Convenience function to merge JUnit XML files
    
    Args:
        xml_paths: Paths to files to merge
        output_path: Where to save merged file
    
    Returns:
        Path to merged file
    """
    return JUnitMerger.merge(xml_paths, output_path)


# Example usage and testing
if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 3:
        print("Usage:")
        print("  python junit_reporter.py generate <report.json> <output.xml>")
        print("  python junit_reporter.py validate <junit.xml>")
        print("  python junit_reporter.py merge <output.xml> <input1.xml> <input2.xml> ...")
        sys.exit(1)
    
    command = sys.argv[1]
    
    if command == "generate":
        from ..reporters.test_report import TestReportLoader
        
        report_path = Path(sys.argv[2])
        output_path = Path(sys.argv[3])
        
        print(f"Loading report from: {report_path}")
        report = TestReportLoader.load(report_path)
        
        print(f"Generating JUnit XML...")
        junit_path = generate_junit(report, output_path)
        
        print(f"✓ JUnit XML generated: {junit_path}")
        
        # Validate
        is_valid, errors = validate_junit(junit_path)
        if is_valid:
            print("✓ XML is valid")
        else:
            print("✗ XML validation errors:")
            for error in errors:
                print(f"  - {error}")
    
    elif command == "validate":
        xml_path = Path(sys.argv[2])
        
        print(f"Validating: {xml_path}")
        is_valid, errors = validate_junit(xml_path)
        
        if is_valid:
            print("✓ XML is valid")
        else:
            print("✗ Validation errors:")
            for error in errors:
                print(f"  - {error}")
            sys.exit(1)
    
    elif command == "merge":
        output_path = Path(sys.argv[2])
        input_paths = [Path(p) for p in sys.argv[3:]]
        
        print(f"Merging {len(input_paths)} files...")
        merged_path = merge_junit(input_paths, output_path)
        
        print(f"✓ Merged XML: {merged_path}")
        
        # Validate merged file
        is_valid, errors = validate_junit(merged_path)
        if is_valid:
            print("✓ Merged XML is valid")
        else:
            print("⚠ Merged XML has validation errors:")
            for error in errors:
                print(f"  - {error}")
    
    else:
        print(f"Unknown command: {command}")
        sys.exit(1)
