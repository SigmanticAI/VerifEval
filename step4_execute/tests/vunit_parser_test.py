"""
Unit tests for VUnit parser

Author: TB Eval Team
Version: 0.1.0
"""

import unittest
from ..parsers.vunit_parser import (
    VUnitOutputParser,
    VUnitErrorParser,
    VUnitListParser,
    parse_vunit_output,
    check_vunit_errors,
)
from ..models import TestOutcome


class TestVUnitOutputParser(unittest.TestCase):
    """Test cases for VUnit output parser"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.parser = VUnitOutputParser()
    
    def test_parse_passed_test(self):
        """Test parsing a passed test"""
        output = """
Running test: work.tb_adder.test_basic
pass (0.5 seconds)
"""
        
        results = self.parser.parse(output)
        
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].name, "test_basic")
        self.assertEqual(results[0].full_name, "work.tb_adder.test_basic")
        self.assertEqual(results[0].outcome, TestOutcome.PASSED)
        self.assertAlmostEqual(results[0].duration_ms, 500.0)
    
    def test_parse_failed_test(self):
        """Test parsing a failed test"""
        output = """
Running test: work.tb_adder.test_overflow
fail (1.2 seconds)
  Assertion violation: Expected 255, got 0
  Error at line 45
"""
        
        results = self.parser.parse(output)
        
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].outcome, TestOutcome.FAILED)
        self.assertIn("Assertion violation", results[0].message)
        self.assertIn("Error at line 45", results[0].details)
    
    def test_parse_multiple_tests(self):
        """Test parsing multiple tests"""
        output = """
Running test: work.tb_adder.test_basic
pass (0.5 seconds)

Running test: work.tb_adder.test_overflow
pass (1.2 seconds)

Running test: work.tb_adder.test_edge_cases
fail (0.8 seconds)
  Test failed
"""
        
        results = self.parser.parse(output)
        
        self.assertEqual(len(results), 3)
        self.assertEqual(results[0].outcome, TestOutcome.PASSED)
        self.assertEqual(results[1].outcome, TestOutcome.PASSED)
        self.assertEqual(results[2].outcome, TestOutcome.FAILED)
    
    def test_parse_summary_format(self):
        """Test parsing from summary section"""
        output = """
==== Summary ====
pass  work.tb_adder.test_basic (0.5 seconds)
pass  work.tb_adder.test_overflow (1.2 seconds)
fail  work.tb_adder.test_edge_cases (0.8 seconds)
==== 2 of 3 passed ====
"""
        
        results = self.parser.parse(output)
        
        self.assertEqual(len(results), 3)
        self.assertEqual(results[0].full_name, "work.tb_adder.test_basic")
        self.assertEqual(results[2].outcome, TestOutcome.FAILED)


class TestVUnitErrorParser(unittest.TestCase):
    """Test cases for VUnit error parser"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.parser = VUnitErrorParser()
    
    def test_detect_compilation_error(self):
        """Test detecting compilation errors"""
        output = """
** Error: (vcom-11) Could not find work.package_name.
** Error: tb_adder.vhd(42): Type mismatch
"""
        
        has_error = self.parser.has_compilation_error(output)
        self.assertTrue(has_error)
        
        errors = self.parser.extract_errors(output)
        self.assertGreater(len(errors), 0)
    
    def test_detect_simulator_crash(self):
        """Test detecting simulator crash"""
        output = """
Running simulation...
Segmentation fault (core dumped)
"""
        
        has_crash = self.parser.has_simulator_crash(output)
        self.assertTrue(has_crash)


class TestVUnitListParser(unittest.TestCase):
    """Test cases for VUnit list parser"""
    
    def test_parse_test_list(self):
        """Test parsing test list"""
        output = """
Listing tests:
work.tb_adder.test_basic
work.tb_adder.test_overflow
work.tb_subtractor.test_simple
"""
        
        tests = VUnitListParser.parse(output)
        
        self.assertEqual(len(tests), 3)
        self.assertIn("work.tb_adder.test_basic", tests)
        self.assertIn("work.tb_subtractor.test_simple", tests)


if __name__ == "__main__":
    unittest.main()
