"""
CocoTB results parser

Parses CocoTB results.xml files (JUnit XML format) into TestResult objects.

Author: TB Eval Team
Version: 0.1.0
"""

import xml.etree.ElementTree as ET
from pathlib import Path
from typing import List, Optional, Dict, Any
from datetime import datetime

from ..models import TestResult, TestOutcome, AssertionStats, TestArtifacts


class CocoTBResultsParser:
    """
    Parser for CocoTB results.xml (JUnit XML format)
    
    CocoTB generates JUnit XML with structure:
    <testsuites>
      <testsuite>
        <testcase name="test_name" classname="module" time="1.23">
          <failure message="..." type="...">traceback</failure>
          <system-out>stdout content</system-out>
          <system-err>stderr content</system-err>
        </testcase>
      </testsuite>
    </testsuites>
    """
    
    def __init__(self):
        """Initialize parser"""
        pass
    
    def parse_file(self, xml_path: Path) -> List[TestResult]:
        """
        Parse results.xml file
        
        Args:
            xml_path: Path to results.xml
        
        Returns:
            List of TestResult objects
        
        Raises:
            FileNotFoundError: If file doesn't exist
            ET.ParseError: If XML is malformed
        """
        if not xml_path.exists():
            raise FileNotFoundError(f"Results file not found: {xml_path}")
        
        try:
            tree = ET.parse(xml_path)
            root = tree.getroot()
            return self.parse_xml(root)
        
        except ET.ParseError as e:
            raise ET.ParseError(f"Failed to parse XML: {e}")
    
    def parse_string(self, xml_content: str) -> List[TestResult]:
        """
        Parse XML from string
        
        Args:
            xml_content: XML content as string
        
        Returns:
            List of TestResult objects
        """
        root = ET.fromstring(xml_content)
        return self.parse_xml(root)
    
    def parse_xml(self, root: ET.Element) -> List[TestResult]:
        """
        Parse XML element tree
        
        Args:
            root: Root XML element (should be <testsuites> or <testsuite>)
        
        Returns:
            List of TestResult objects
        """
        results = []
        
        # Handle both <testsuites> and <testsuite> as root
        if root.tag == 'testsuites':
            # Find all testsuite elements
            for testsuite in root.findall('.//testsuite'):
                results.extend(self._parse_testsuite(testsuite))
        
        elif root.tag == 'testsuite':
            results.extend(self._parse_testsuite(root))
        
        else:
            raise ValueError(f"Unexpected root element: {root.tag}")
        
        return results
    
    def _parse_testsuite(self, testsuite: ET.Element) -> List[TestResult]:
        """
        Parse a <testsuite> element
        
        Args:
            testsuite: testsuite XML element
        
        Returns:
            List of TestResult objects from this suite
        """
        results = []
        
        # Find all testcase elements
        for testcase in testsuite.findall('testcase'):
            result = self._parse_testcase(testcase)
            results.append(result)
        
        return results
    
    def _parse_testcase(self, testcase: ET.Element) -> TestResult:
        """
        Parse a <testcase> element
        
        Args:
            testcase: testcase XML element
        
        Returns:
            TestResult object
        """
        # Extract basic attributes
        name = testcase.get('name', 'unknown')
        classname = testcase.get('classname', '')
        time_str = testcase.get('time', '0')
        
        # Parse duration
        try:
            duration_seconds = float(time_str)
            duration_ms = duration_seconds * 1000
        except ValueError:
            duration_ms = 0.0
        
        # Build full name
        if classname:
            full_name = f"{classname}.{name}"
        else:
            full_name = name
        
        # Determine outcome and extract details
        outcome, message, details, traceback = self._determine_outcome(testcase)
        
        # Extract output
        stdout = self._extract_cdata(testcase.find('system-out'))
        stderr = self._extract_cdata(testcase.find('system-err'))
        
        # Parse assertions from output (if available)
        assertions = self._parse_assertions(stdout, outcome)
        
        # Create TestResult
        result = TestResult(
            name=name,
            full_name=full_name,
            outcome=outcome,
            duration_ms=duration_ms,
            message=message,
            details=details,
            traceback=traceback,
            stdout=stdout,
            stderr=stderr,
            assertions=assertions,
            artifacts=TestArtifacts(),
        )
        
        return result
    
    def _determine_outcome(
        self,
        testcase: ET.Element
    ) -> tuple[TestOutcome, Optional[str], Optional[str], Optional[str]]:
        """
        Determine test outcome from testcase element
        
        Args:
            testcase: testcase XML element
        
        Returns:
            Tuple of (outcome, message, details, traceback)
        """
        # Check for failure
        failure = testcase.find('failure')
        if failure is not None:
            message = failure.get('message', 'Test failed')
            failure_type = failure.get('type', 'Failure')
            traceback = self._extract_cdata(failure)
            
            return (
                TestOutcome.FAILED,
                f"{failure_type}: {message}",
                traceback,
                traceback,
            )
        
        # Check for error
        error = testcase.find('error')
        if error is not None:
            message = error.get('message', 'Test error')
            error_type = error.get('type', 'Error')
            traceback = self._extract_cdata(error)
            
            return (
                TestOutcome.ERROR,
                f"{error_type}: {message}",
                traceback,
                traceback,
            )
        
        # Check for skipped
        skipped = testcase.find('skipped')
        if skipped is not None:
            message = skipped.get('message', 'Test skipped')
            return (
                TestOutcome.SKIPPED,
                message,
                None,
                None,
            )
        
        # No failure/error/skipped = passed
        return (TestOutcome.PASSED, None, None, None)
    
    def _extract_cdata(self, element: Optional[ET.Element]) -> Optional[str]:
        """
        Extract text content from element (including CDATA)
        
        Args:
            element: XML element
        
        Returns:
            Text content or None
        """
        if element is None:
            return None
        
        # Get text content
        text = element.text or ''
        
        # Also get tail text (text after nested elements)
        for child in element:
            if child.tail:
                text += child.tail
        
        # Strip leading/trailing whitespace but preserve internal formatting
        text = text.strip()
        
        return text if text else None
    
    def _parse_assertions(
        self,
        stdout: Optional[str],
        outcome: TestOutcome
    ) -> AssertionStats:
        """
        Parse assertion statistics from stdout
        
        CocoTB doesn't provide explicit assertion counts,
        so we estimate based on outcome and output.
        
        Args:
            stdout: Standard output content
            outcome: Test outcome
        
        Returns:
            AssertionStats object
        """
        stats = AssertionStats()
        
        if not stdout:
            # No output - assume minimal assertions
            if outcome == TestOutcome.PASSED:
                stats.total = 1
                stats.passed = 1
            elif outcome == TestOutcome.FAILED:
                stats.total = 1
                stats.failed = 1
            return stats
        
        # Try to parse assertion-like patterns from output
        import re
        
        # Look for assert statements
        assert_pattern = re.compile(r'\bassert\b', re.IGNORECASE)
        assertions_found = len(assert_pattern.findall(stdout))
        
        if assertions_found > 0:
            stats.total = assertions_found
            if outcome == TestOutcome.PASSED:
                stats.passed = assertions_found
            elif outcome == TestOutcome.FAILED:
                # Assume last assertion failed
                stats.passed = assertions_found - 1
                stats.failed = 1
        else:
            # No explicit assertions found - use outcome as proxy
            if outcome == TestOutcome.PASSED:
                stats.total = 1
                stats.passed = 1
            elif outcome == TestOutcome.FAILED:
                stats.total = 1
                stats.failed = 1
        
        return stats


class CocoTBSummaryParser:
    """
    Parser for CocoTB summary information from console output
    
    Extracts additional information that may not be in XML:
    - Coverage summary
    - Simulator warnings
    - Timing information
    """
    
    def __init__(self):
        """Initialize summary parser"""
        import re
        
        # Patterns for parsing console output
        self.coverage_pattern = re.compile(
            r'Coverage:\s*(\d+\.?\d*)\s*%'
        )
        
        self.test_result_pattern = re.compile(
            r'(\w+)\s+\((\d+\.?\d*)\s*s\)'
        )
    
    def parse_coverage_info(self, console_output: str) -> Optional[Dict[str, Any]]:
        """
        Parse coverage information from console output
        
        Args:
            console_output: Console output string
        
        Returns:
            Dictionary with coverage info or None
        """
        match = self.coverage_pattern.search(console_output)
        
        if match:
            coverage_percent = float(match.group(1))
            return {
                'coverage_percent': coverage_percent,
                'source': 'console_output',
            }
        
        return None
    
    def parse_test_timing(self, console_output: str) -> Dict[str, float]:
        """
        Parse test timing from console output
        
        Args:
            console_output: Console output string
        
        Returns:
            Dictionary mapping test names to durations
        """
        timings = {}
        
        for match in self.test_result_pattern.finditer(console_output):
            test_name = match.group(1)
            duration = float(match.group(2))
            timings[test_name] = duration
        
        return timings


class CocoTBXMLValidator:
    """
    Validates CocoTB results.xml for completeness and correctness
    """
    
    @staticmethod
    def validate_file(xml_path: Path) -> tuple[bool, List[str]]:
        """
        Validate results.xml file
        
        Args:
            xml_path: Path to results.xml
        
        Returns:
            Tuple of (is_valid, list_of_issues)
        """
        issues = []
        
        # Check file exists
        if not xml_path.exists():
            return False, ["File does not exist"]
        
        # Check file is not empty
        if xml_path.stat().st_size == 0:
            return False, ["File is empty"]
        
        # Try to parse XML
        try:
            tree = ET.parse(xml_path)
            root = tree.getroot()
        except ET.ParseError as e:
            return False, [f"XML parse error: {e}"]
        
        # Validate structure
        if root.tag not in ['testsuites', 'testsuite']:
            issues.append(f"Unexpected root element: {root.tag}")
        
        # Check for testcases
        testcases = root.findall('.//testcase')
        if not testcases:
            issues.append("No testcase elements found")
        
        # Validate each testcase
        for idx, testcase in enumerate(testcases):
            if not testcase.get('name'):
                issues.append(f"Testcase {idx} missing 'name' attribute")
            
            if not testcase.get('time'):
                issues.append(f"Testcase {idx} missing 'time' attribute")
        
        is_valid = len(issues) == 0
        return is_valid, issues
    
    @staticmethod
    def validate_content(xml_path: Path, expected_tests: List[str]) -> tuple[bool, List[str]]:
        """
        Validate that XML contains expected tests
        
        Args:
            xml_path: Path to results.xml
            expected_tests: List of expected test names
        
        Returns:
            Tuple of (is_valid, list_of_issues)
        """
        issues = []
        
        # Parse XML
        try:
            parser = CocoTBResultsParser()
            results = parser.parse_file(xml_path)
        except Exception as e:
            return False, [f"Failed to parse: {e}"]
        
        # Extract test names
        found_tests = {r.name for r in results}
        expected_set = set(expected_tests)
        
        # Check for missing tests
        missing = expected_set - found_tests
        if missing:
            issues.append(f"Missing tests: {', '.join(sorted(missing))}")
        
        # Check for unexpected tests
        unexpected = found_tests - expected_set
        if unexpected:
            issues.append(f"Unexpected tests: {', '.join(sorted(unexpected))}")
        
        is_valid = len(issues) == 0
        return is_valid, issues


# Utility functions

def parse_cocotb_results(xml_path: Path) -> List[TestResult]:
    """
    Convenience function to parse CocoTB results.xml
    
    Args:
        xml_path: Path to results.xml
    
    Returns:
        List of TestResult objects
    """
    parser = CocoTBResultsParser()
    return parser.parse_file(xml_path)


def validate_cocotb_results(
    xml_path: Path,
    expected_tests: Optional[List[str]] = None
) -> tuple[bool, List[str]]:
    """
    Convenience function to validate CocoTB results.xml
    
    Args:
        xml_path: Path to results.xml
        expected_tests: Optional list of expected test names
    
    Returns:
        Tuple of (is_valid, list_of_issues)
    """
    # Basic validation
    is_valid, issues = CocoTBXMLValidator.validate_file(xml_path)
    
    if not is_valid:
        return False, issues
    
    # Content validation if expected tests provided
    if expected_tests:
        is_valid, content_issues = CocoTBXMLValidator.validate_content(
            xml_path, expected_tests
        )
        issues.extend(content_issues)
    
    return is_valid, issues


# Example usage and testing
if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python cocotb_parser.py <results.xml>")
        sys.exit(1)
    
    xml_file = Path(sys.argv[1])
    
    # Validate
    print(f"Validating {xml_file}...")
    is_valid, issues = validate_cocotb_results(xml_file)
    
    if not is_valid:
        print("❌ Validation failed:")
        for issue in issues:
            print(f"  - {issue}")
        sys.exit(1)
    
    print("✓ Validation passed")
    
    # Parse
    print(f"\nParsing {xml_file}...")
    try:
        parser = CocoTBResultsParser()
        results = parser.parse_file(xml_file)
        
        print(f"\n{'=' * 60}")
        print(f"Found {len(results)} tests:")
        print(f"{'=' * 60}")
        
        for result in results:
            symbol = result.outcome.symbol
            duration = result.duration_ms / 1000
            
            print(f"{symbol} {result.full_name} ({duration:.3f}s)")
            
            if result.message:
                print(f"  Message: {result.message}")
            
            if result.traceback:
                print(f"  Traceback:")
                for line in result.traceback.split('\n')[:5]:
                    print(f"    {line}")
                if len(result.traceback.split('\n')) > 5:
                    print("    ...")
        
        # Summary
        print(f"\n{'=' * 60}")
        passed = sum(1 for r in results if r.outcome == TestOutcome.PASSED)
        failed = sum(1 for r in results if r.outcome == TestOutcome.FAILED)
        error = sum(1 for r in results if r.outcome == TestOutcome.ERROR)
        skipped = sum(1 for r in results if r.outcome == TestOutcome.SKIPPED)
        
        print(f"Summary:")
        print(f"  Passed:  {passed}")
        print(f"  Failed:  {failed}")
        print(f"  Error:   {error}")
        print(f"  Skipped: {skipped}")
        print(f"{'=' * 60}")
    
    except Exception as e:
        print(f"❌ Parse error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
