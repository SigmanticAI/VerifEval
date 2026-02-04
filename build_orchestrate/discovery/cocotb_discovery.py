"""
CocoTB Test Discovery
=====================

Discovers CocoTB tests from Python source files by finding
@cocotb.test() decorators.

Author: TB Eval Team
Version: 0.1.0
"""

import ast
import re
from pathlib import Path
from typing import List, Optional, Dict, Any

from .base import BaseTestDiscovery, DiscoveryResult
from ..models import TestCase, TestStatus


class CocoTBTestDiscovery(BaseTestDiscovery):
    """
    Discovers CocoTB tests from Python files
    
    Finds functions decorated with @cocotb.test()
    
    Usage:
        discovery = CocoTBTestDiscovery(submission_dir)
        result = discovery.discover(python_files)
    """
    
    # Regex pattern for @cocotb.test() decorator
    COCOTB_TEST_PATTERN = re.compile(
        r'@cocotb\.test\s*\(([^)]*)\)\s*\n\s*(?:async\s+)?def\s+(\w+)',
        re.MULTILINE
    )
    
    # Pattern for simple decorator
    COCOTB_SIMPLE_PATTERN = re.compile(
        r'@cocotb\.test\s*\n\s*(?:async\s+)?def\s+(\w+)',
        re.MULTILINE
    )
    
    def __init__(
        self,
        submission_dir: Path,
        module_name: Optional[str] = None,
    ):
        """
        Initialize CocoTB test discovery
        
        Args:
            submission_dir: Path to submission directory
            module_name: Default module name for tests
        """
        super().__init__(submission_dir)
        self.module_name = module_name
    
    def get_discovery_method(self) -> str:
        return "cocotb_decorator_parsing"
    
    def discover(self, source_files: List[Path]) -> DiscoveryResult:
        """
        Discover CocoTB tests from Python files
        
        Args:
            source_files: List of Python files to scan
        
        Returns:
            DiscoveryResult with discovered tests
        """
        result = DiscoveryResult(
            discovery_method=self.get_discovery_method(),
        )
        
        # Filter to Python files
        py_files = [f for f in source_files if f.suffix == '.py']
        result.source_files = [str(f) for f in py_files]
        
        for file_path in py_files:
            try:
                content = self.read_file_safe(file_path)
                if content:
                    tests = self._parse_file(file_path, content)
                    result.tests.extend(tests)
            except Exception as e:
                result.warnings.append(f"Failed to parse {file_path}: {str(e)}")
        
        return result
    
    def _parse_file(self, file_path: Path, content: str) -> List[TestCase]:
        """Parse a single Python file for CocoTB tests"""
        tests = []
        module = self.module_name or file_path.stem
        
        # Try regex-based parsing (handles more cases)
        # Pattern with arguments
        for match in self.COCOTB_TEST_PATTERN.finditer(content):
            args_str = match.group(1)
            func_name = match.group(2)
            
            # Parse decorator arguments
            attributes = self._parse_decorator_args(args_str)
            
            tests.append(TestCase(
                name=func_name,
                full_name=f"{module}.{func_name}",
                testbench=module,
                library="cocotb",
                test_type="cocotb",
                status=TestStatus.READY,
                attributes=attributes,
            ))
        
        # Pattern without arguments
        for match in self.COCOTB_SIMPLE_PATTERN.finditer(content):
            func_name = match.group(1)
            
            # Check if already found with args pattern
            if not any(t.name == func_name for t in tests):
                tests.append(TestCase(
                    name=func_name,
                    full_name=f"{module}.{func_name}",
                    testbench=module,
                    library="cocotb",
                    test_type="cocotb",
                    status=TestStatus.READY,
                ))
        
        return tests
    
    def _parse_decorator_args(self, args_str: str) -> Dict[str, Any]:
        """Parse @cocotb.test(...) arguments"""
        attributes = {}
        
        if not args_str.strip():
            return attributes
        
        # Simple parsing for common arguments
        # timeout_time, timeout_unit, expect_fail, expect_error, skip
        
        patterns = {
            'timeout_time': r'timeout_time\s*=\s*(\d+)',
            'timeout_unit': r'timeout_unit\s*=\s*["\'](\w+)["\']',
            'expect_fail': r'expect_fail\s*=\s*(True|False)',
            'expect_error': r'expect_error\s*=\s*(\w+)',
            'skip': r'skip\s*=\s*(True|False)',
        }
        
        for key, pattern in patterns.items():
            match = re.search(pattern, args_str)
            if match:
                value = match.group(1)
                if value in ('True', 'False'):
                    value = value == 'True'
                elif value.isdigit():
                    value = int(value)
                attributes[key] = value
        
        return attributes
    
    def _parse_file_ast(self, file_path: Path, content: str) -> List[TestCase]:
        """
        Parse using AST (more accurate but stricter)
        
        Falls back to regex if AST parsing fails.
        """
        tests = []
        module = self.module_name or file_path.stem
        
        try:
            tree = ast.parse(content)
            
            for node in ast.walk(tree):
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    # Check decorators
                    for decorator in node.decorator_list:
                        if self._is_cocotb_test_decorator(decorator):
                            tests.append(TestCase(
                                name=node.name,
                                full_name=f"{module}.{node.name}",
                                testbench=module,
                                library="cocotb",
                                test_type="cocotb",
                                status=TestStatus.READY,
                            ))
                            break
            
        except SyntaxError:
            # Fall back to regex
            return self._parse_file(file_path, content)
        
        return tests
    
    def _is_cocotb_test_decorator(self, decorator: ast.AST) -> bool:
        """Check if decorator is @cocotb.test"""
        if isinstance(decorator, ast.Call):
            func = decorator.func
        else:
            func = decorator
        
        if isinstance(func, ast.Attribute):
            if func.attr == 'test':
                if isinstance(func.value, ast.Name) and func.value.id == 'cocotb':
                    return True
        
        return False
