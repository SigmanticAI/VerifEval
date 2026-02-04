"""
VUnit output parser

Parses VUnit console output into TestResult objects.

VUnit doesn't produce structured output by default, so we parse
the human-readable console output.

Author: TB Eval Team
Version: 0.1.0
"""

import re
from typing import List, Optional, Dict, Any, Tuple
from enum import Enum
from dataclasses import dataclass

from ..models import TestResult, TestOutcome, AssertionStats, TestArtifacts


class VUnitOutputFormat(Enum):
    """VUnit output format variants"""
    STANDARD = "standard"       # Normal VUnit output
    VERBOSE = "verbose"         # With -v flag
    MINIMAL = "minimal"         # With -q flag


@dataclass
class VUnitTestBlock:
    """Represents a test block in VUnit output"""
    test_name: str
    outcome: str
    duration_seconds: float
    failure_messages: List[str]
    output_lines: List[str]


class VUnitOutputParser:
    """
    Parser for VUnit console output
    
    Parses output patterns like:
    
    Running test: work.tb_adder.test_basic
    pass (0.5 seconds)
    
    Running test: work.tb_adder.test_overflow
    fail (1.2 seconds)
      Assertion failed at line 45: Expected 255, got 0
      Error: Test failed
    
    ==== Summary ====
    pass  2 of 3
    fail  1 of 3
    """
    
    def __init__(self):
        """Initialize parser with regex patterns"""
        
        # Pattern for "Running test: <name>"
        self.test_start_pattern = re.compile(
            r'^Running test:\s+(.+?)(?:\s+\(.*?\))?\s*$',
            re.MULTILINE
        )
        
        # Pattern for test result line: "pass (1.23 seconds)"
        self.test_result_pattern = re.compile(
            r'^(pass|fail|error|skipped?)\s+\(([0-9.]+)\s+seconds?\)',
            re.MULTILINE | re.IGNORECASE
        )
        
        # Alternative result pattern: "pass work.tb.test (1.23 seconds)"
        self.alt_result_pattern = re.compile(
            r'^(pass|fail|error|skipped?)\s+(.+?)\s+\(([0-9.]+)\s+seconds?\)',
            re.MULTILINE | re.IGNORECASE
        )
        
        # Pattern for summary lines
        self.summary_pattern = re.compile(
            r'^(pass|fail|error|skipped?)\s+(\d+)\s+of\s+(\d+)',
            re.MULTILINE | re.IGNORECASE
        )
        
        # Pattern for assertion errors
        self.assertion_pattern = re.compile(
            r'(?:assertion|error|failure|fatal).*?(?:at|on|in)\s+.*?line\s+(\d+)',
            re.IGNORECASE
        )
        
        # Pattern for VHDL assertion failures
        self.vhdl_assert_pattern = re.compile(
            r'Assertion\s+(?:violation|failure|error)',
            re.IGNORECASE
        )
    
    def parse(self, console_output: str) -> List[TestResult]:
        """
        Parse VUnit console output
        
        Args:
            console_output: Complete console output from VUnit
        
        Returns:
            List of TestResult objects
        """
        # Try to extract test blocks
        test_blocks = self._extract_test_blocks(console_output)
        
        if test_blocks:
            # Parse from structured blocks
            results = [self._parse_test_block(block) for block in test_blocks]
        else:
            # Fall back to summary parsing
            results = self._parse_from_summary(console_output)
        
        return results
    
    def _extract_test_blocks(self, output: str) -> List[VUnitTestBlock]:
        """
        Extract individual test blocks from output
        
        Args:
            output: Console output
        
        Returns:
            List of test blocks
        """
        blocks = []
        lines = output.split('\n')
        
        current_test = None
        current_outcome = None
        current_duration = None
        current_failures = []
        current_output = []
        
        i = 0
        while i < len(lines):
            line = lines[i].rstrip()
            
            # Check for test start
            match = self.test_start_pattern.match(line)
            if match:
                # Save previous test if exists
                if current_test:
                    blocks.append(VUnitTestBlock(
                        test_name=current_test,
                        outcome=current_outcome or 'error',
                        duration_seconds=current_duration or 0.0,
                        failure_messages=current_failures,
                        output_lines=current_output,
                    ))
                
                # Start new test
                current_test = match.group(1).strip()
                current_outcome = None
                current_duration = None
                current_failures = []
                current_output = []
                i += 1
                continue
            
            # Check for test result
            result_match = self.test_result_pattern.match(line)
            if result_match and current_test:
                current_outcome = result_match.group(1).lower()
                current_duration = float(result_match.group(2))
                i += 1
                
                # Collect failure messages (indented lines following fail)
                if current_outcome in ['fail', 'error']:
                    while i < len(lines):
                        next_line = lines[i]
                        # Check if line is indented (failure message)
                        if next_line and (next_line.startswith('  ') or next_line.startswith('\t')):
                            current_failures.append(next_line.strip())
                            i += 1
                        else:
                            break
                continue
            
            # Collect output lines for current test
            if current_test and not line.startswith('===='):
                current_output.append(line)
            
            i += 1
        
        # Save last test
        if current_test:
            blocks.append(VUnitTestBlock(
                test_name=current_test,
                outcome=current_outcome or 'error',
                duration_seconds=current_duration or 0.0,
                failure_messages=current_failures,
                output_lines=current_output,
            ))
        
        return blocks
    
    def _parse_test_block(self, block: VUnitTestBlock) -> TestResult:
        """
        Parse a test block into TestResult
        
        Args:
            block: VUnit test block
        
        Returns:
            TestResult object
        """
        # Map VUnit outcome to TestOutcome
        outcome_map = {
            'pass': TestOutcome.PASSED,
            'fail': TestOutcome.FAILED,
            'error': TestOutcome.ERROR,
            'skipped': TestOutcome.SKIPPED,
            'skip': TestOutcome.SKIPPED,
        }
        
        outcome = outcome_map.get(block.outcome.lower(), TestOutcome.ERROR)
        
        # Build failure message
        message = None
        details = None
        traceback = None
        
        if block.failure_messages:
            message = block.failure_messages[0]
            if len(block.failure_messages) > 1:
                details = '\n'.join(block.failure_messages)
                traceback = details
        
        # Parse assertions
        assertions = self._parse_assertions_from_output(
            '\n'.join(block.output_lines),
            outcome
        )
        
        # Split test name into name and full_name
        name = block.test_name.split('.')[-1] if '.' in block.test_name else block.test_name
        
        # Create TestResult
        result = TestResult(
            name=name,
            full_name=block.test_name,
            outcome=outcome,
            duration_ms=block.duration_seconds * 1000,
            message=message,
            details=details,
            traceback=traceback,
            stdout='\n'.join(block.output_lines) if block.output_lines else None,
            assertions=assertions,
            artifacts=TestArtifacts(),
        )
        
        return result
    
    def _parse_from_summary(self, output: str) -> List[TestResult]:
        """
        Parse results from summary section only
        
        Used as fallback when test blocks can't be extracted.
        
        Args:
            output: Console output
        
        Returns:
            List of TestResult objects
        """
        results = []
        
        # Find summary section
        summary_start = output.find('==== Summary ====')
        if summary_start == -1:
            # No summary found - try alternative summary format
            return self._parse_alternative_summary(output)
        
        summary_section = output[summary_start:]
        
        # Extract results from summary
        for match in self.alt_result_pattern.finditer(summary_section):
            outcome_str = match.group(1).lower()
            test_name = match.group(2).strip()
            duration = float(match.group(3))
            
            # Map outcome
            outcome_map = {
                'pass': TestOutcome.PASSED,
                'fail': TestOutcome.FAILED,
                'error': TestOutcome.ERROR,
                'skipped': TestOutcome.SKIPPED,
                'skip': TestOutcome.SKIPPED,
            }
            outcome = outcome_map.get(outcome_str, TestOutcome.ERROR)
            
            # Extract short name
            name = test_name.split('.')[-1] if '.' in test_name else test_name
            
            result = TestResult(
                name=name,
                full_name=test_name,
                outcome=outcome,
                duration_ms=duration * 1000,
                assertions=AssertionStats(
                    total=1,
                    passed=1 if outcome == TestOutcome.PASSED else 0,
                    failed=1 if outcome == TestOutcome.FAILED else 0,
                ),
                artifacts=TestArtifacts(),
            )
            
            results.append(result)
        
        return results
    
    def _parse_alternative_summary(self, output: str) -> List[TestResult]:
        """
        Parse alternative summary format
        
        Some VUnit versions may have different output format.
        
        Args:
            output: Console output
        
        Returns:
            List of TestResult objects
        """
        # This is a minimal parser for when we can't extract detailed info
        # Just count pass/fail from summary lines
        
        results = []
        
        # Look for summary statistics
        total_tests = 0
        for match in self.summary_pattern.finditer(output):
            total_tests = int(match.group(3))
            break
        
        if total_tests == 0:
            # Can't parse - return empty list
            return []
        
        # Create generic results based on counts
        # This is not ideal but better than nothing
        pass_count = 0
        fail_count = 0
        
        for match in self.summary_pattern.finditer(output):
            outcome = match.group(1).lower()
            count = int(match.group(2))
            
            if outcome == 'pass':
                pass_count = count
            elif outcome == 'fail':
                fail_count = count
        
        # Create generic test results
        for i in range(pass_count):
            results.append(TestResult(
                name=f"test_{i+1}",
                full_name=f"unknown.test_{i+1}",
                outcome=TestOutcome.PASSED,
                duration_ms=0,
                message="Parsed from summary only",
                artifacts=TestArtifacts(),
            ))
        
        for i in range(fail_count):
            results.append(TestResult(
                name=f"test_fail_{i+1}",
                full_name=f"unknown.test_fail_{i+1}",
                outcome=TestOutcome.FAILED,
                duration_ms=0,
                message="Parsed from summary only",
                artifacts=TestArtifacts(),
            ))
        
        return results
    
    def _parse_assertions_from_output(
        self,
        output: str,
        outcome: TestOutcome
    ) -> AssertionStats:
        """
        Parse assertion statistics from test output
        
        Args:
            output: Test output
            outcome: Test outcome
        
        Returns:
            AssertionStats object
        """
        stats = AssertionStats()
        
        # Count assertion failures
        assertion_failures = len(self.assertion_pattern.findall(output))
        vhdl_assertions = len(self.vhdl_assert_pattern.findall(output))
        
        total_assertions = assertion_failures + vhdl_assertions
        
        if total_assertions > 0:
            stats.total = total_assertions
            if outcome == TestOutcome.PASSED:
                stats.passed = total_assertions
            elif outcome == TestOutcome.FAILED:
                # Assume at least one failed
                stats.failed = max(1, assertion_failures)
                stats.passed = total_assertions - stats.failed
        else:
            # No explicit assertions found
            if outcome == TestOutcome.PASSED:
                stats.total = 1
                stats.passed = 1
            elif outcome == TestOutcome.FAILED:
                stats.total = 1
                stats.failed = 1
        
        return stats
    
    def parse_summary_statistics(self, output: str) -> Dict[str, int]:
        """
        Parse summary statistics from output
        
        Args:
            output: Console output
        
        Returns:
            Dictionary with test counts by outcome
        """
        stats = {
            'total': 0,
            'pass': 0,
            'fail': 0,
            'error': 0,
            'skipped': 0,
        }
        
        # Extract from summary
        for match in self.summary_pattern.finditer(output):
            outcome = match.group(1).lower()
            count = int(match.group(2))
            total = int(match.group(3))
            
            stats['total'] = total
            if outcome in stats:
                stats[outcome] = count
        
        return stats


class VUnitErrorParser:
    """
    Parser for VUnit errors and compilation issues
    
    Extracts information about:
    - Compilation errors
    - Simulator crashes
    - VUnit framework errors
    """
    
    def __init__(self):
        """Initialize error parser"""
        
        # Compilation error patterns
        self.compile_error_pattern = re.compile(
            r'(?:ERROR|Error|error).*?:\s*(.+?)(?:\n|$)',
            re.MULTILINE
        )
        
        # VHDL compilation errors
        self.vhdl_error_pattern = re.compile(
            r'\*\*\s*Error.*?:\s*(.+?)$',
            re.MULTILINE
        )
        
        # SystemVerilog compilation errors
        self.sv_error_pattern = re.compile(
            r'Error-\[.*?\]\s*(.+?)$',
            re.MULTILINE
        )
        
        # Simulator crash pattern
        self.crash_pattern = re.compile(
            r'(?:crash|segmentation fault|core dump)',
            re.IGNORECASE
        )
    
    def has_compilation_error(self, output: str) -> bool:
        """
        Check if output contains compilation errors
        
        Args:
            output: Console output
        
        Returns:
            True if compilation errors found
        """
        return bool(
            self.compile_error_pattern.search(output) or
            self.vhdl_error_pattern.search(output) or
            self.sv_error_pattern.search(output)
        )
    
    def has_simulator_crash(self, output: str) -> bool:
        """
        Check if simulator crashed
        
        Args:
            output: Console output
        
        Returns:
            True if crash detected
        """
        return bool(self.crash_pattern.search(output))
    
    def extract_errors(self, output: str) -> List[str]:
        """
        Extract error messages from output
        
        Args:
            output: Console output
        
        Returns:
            List of error messages
        """
        errors = []
        
        # Extract compilation errors
        for match in self.compile_error_pattern.finditer(output):
            errors.append(match.group(1).strip())
        
        # Extract VHDL errors
        for match in self.vhdl_error_pattern.finditer(output):
            errors.append(match.group(1).strip())
        
        # Extract SV errors
        for match in self.sv_error_pattern.finditer(output):
            errors.append(match.group(1).strip())
        
        # Check for crash
        if self.has_simulator_crash(output):
            errors.append("Simulator crashed")
        
        return errors


class VUnitListParser:
    """
    Parser for VUnit --list output
    
    Parses test list from: python run.py --list
    """
    
    @staticmethod
    def parse(list_output: str) -> List[str]:
        """
        Parse test list
        
        Args:
            list_output: Output from --list command
        
        Returns:
            List of test names
        """
        tests = []
        
        for line in list_output.split('\n'):
            line = line.strip()
            
            # Skip empty lines and comments
            if not line or line.startswith('#'):
                continue
            
            # Skip header lines
            if 'Listing' in line or 'Tests' in line:
                continue
            
            # Test names typically contain dots (library.testbench.test)
            if '.' in line:
                tests.append(line)
        
        return tests


# Utility functions

def parse_vunit_output(console_output: str) -> List[TestResult]:
    """
    Convenience function to parse VUnit output
    
    Args:
        console_output: Console output from VUnit
    
    Returns:
        List of TestResult objects
    """
    parser = VUnitOutputParser()
    return parser.parse(console_output)


def parse_vunit_test_list(list_output: str) -> List[str]:
    """
    Convenience function to parse VUnit test list
    
    Args:
        list_output: Output from --list command
    
    Returns:
        List of test names
    """
    return VUnitListParser.parse(list_output)


def check_vunit_errors(console_output: str) -> Tuple[bool, List[str]]:
    """
    Check for VUnit errors
    
    Args:
        console_output: Console output
    
    Returns:
        Tuple of (has_errors, error_messages)
    """
    parser = VUnitErrorParser()
    
    has_compile_error = parser.has_compilation_error(console_output)
    has_crash = parser.has_simulator_crash(console_output)
    
    has_errors = has_compile_error or has_crash
    error_messages = parser.extract_errors(console_output) if has_errors else []
    
    return has_errors, error_messages


# Example usage and testing
if __name__ == "__main__":
    # Example VUnit output
    sample_output = """
Starting test: work.tb_adder.all_tests
Running test: work.tb_adder.test_basic
pass (0.5 seconds)

Running test: work.tb_adder.test_overflow
pass (1.2 seconds)

Running test: work.tb_adder.test_edge_cases
fail (0.8 seconds)
  Assertion violation: Expected 255, got 0
  Error at line 45 in tb_adder.vhd

==== Summary ====
pass  2 of 3
fail  1 of 3
=================
Total time was 2.5 seconds
Elapsed time was 2.5 seconds
==== Summary ====
pass  work.tb_adder.test_basic (0.5 seconds)
pass  work.tb_adder.test_overflow (1.2 seconds)
fail  work.tb_adder.test_edge_cases (0.8 seconds)
==== 2 of 3 passed ====
"""
    
    print("Parsing VUnit output...")
    print("=" * 60)
    
    parser = VUnitOutputParser()
    results = parser.parse(sample_output)
    
    for result in results:
        symbol = result.outcome.symbol
        duration = result.duration_ms / 1000
        
        print(f"{symbol} {result.full_name} ({duration:.3f}s)")
        
        if result.message:
            print(f"  Message: {result.message}")
        
        if result.details:
            print(f"  Details: {result.details[:100]}...")
    
    print("=" * 60)
    print(f"Total: {len(results)} tests")
    
    # Test error detection
    error_output = """
** Error: (vcom-11) Could not find work.package_name.
** Error: tb_adder.vhd(42): Type mismatch in assignment
"""
    
    print("\nChecking for errors...")
    has_errors, errors = check_vunit_errors(error_output)
    
    if has_errors:
        print("Errors found:")
        for error in errors:
            print(f"  - {error}")
