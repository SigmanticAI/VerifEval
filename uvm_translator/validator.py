"""
Translation Validator.

Validates generated Python/cocotb code for syntax correctness,
required imports, and basic structural validity.
"""

import ast
import re
import sys
from pathlib import Path
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any
from enum import Enum


class ValidationSeverity(Enum):
    """Severity levels for validation issues."""
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


@dataclass
class ValidationIssue:
    """A single validation issue."""
    severity: ValidationSeverity
    message: str
    file: str = ""
    line: int = 0
    suggestion: Optional[str] = None


@dataclass
class ValidationResult:
    """Result of validating translated code."""
    valid: bool
    syntax_valid: bool = True
    imports_valid: bool = True
    cocotb_valid: bool = True
    
    issues: List[ValidationIssue] = field(default_factory=list)
    
    # Statistics
    num_tests: int = 0
    num_coroutines: int = 0
    imports_found: List[str] = field(default_factory=list)
    
    def add_error(self, message: str, file: str = "", line: int = 0, suggestion: str = None):
        """Add an error issue."""
        self.issues.append(ValidationIssue(
            severity=ValidationSeverity.ERROR,
            message=message,
            file=file,
            line=line,
            suggestion=suggestion
        ))
        self.valid = False
    
    def add_warning(self, message: str, file: str = "", line: int = 0, suggestion: str = None):
        """Add a warning issue."""
        self.issues.append(ValidationIssue(
            severity=ValidationSeverity.WARNING,
            message=message,
            file=file,
            line=line,
            suggestion=suggestion
        ))
    
    def add_info(self, message: str, file: str = "", line: int = 0):
        """Add an info issue."""
        self.issues.append(ValidationIssue(
            severity=ValidationSeverity.INFO,
            message=message,
            file=file,
            line=line
        ))
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'valid': self.valid,
            'syntax_valid': self.syntax_valid,
            'imports_valid': self.imports_valid,
            'cocotb_valid': self.cocotb_valid,
            'num_tests': self.num_tests,
            'num_coroutines': self.num_coroutines,
            'imports_found': self.imports_found,
            'issues': [
                {
                    'severity': i.severity.value,
                    'message': i.message,
                    'file': i.file,
                    'line': i.line,
                    'suggestion': i.suggestion
                }
                for i in self.issues
            ]
        }


class TranslationValidator:
    """
    Validates translated Python/cocotb code.
    
    Checks:
    - Python syntax validity
    - Required cocotb imports
    - cocotb test decorator usage
    - async/await consistency
    - Basic structural requirements
    """
    
    # Required cocotb imports
    REQUIRED_IMPORTS = {
        'cocotb',
    }
    
    # Recommended imports
    RECOMMENDED_IMPORTS = {
        'cocotb.clock': 'Clock',
        'cocotb.triggers': ['RisingEdge', 'FallingEdge', 'Timer', 'ClockCycles'],
    }
    
    # cocotb decorators
    COCOTB_DECORATORS = ['cocotb.test', 'cocotb.coroutine']
    
    def __init__(self):
        pass
    
    def validate_file(self, file_path: Path) -> ValidationResult:
        """
        Validate a single Python file.
        
        Args:
            file_path: Path to Python file
            
        Returns:
            ValidationResult with issues found
        """
        result = ValidationResult(valid=True)
        
        try:
            with open(file_path, 'r') as f:
                content = f.read()
        except Exception as e:
            result.add_error(f"Failed to read file: {e}", str(file_path))
            return result
        
        return self.validate_content(content, str(file_path))
    
    def validate_content(self, content: str, filename: str = "") -> ValidationResult:
        """
        Validate Python code content.
        
        Args:
            content: Python source code
            filename: Optional filename for error reporting
            
        Returns:
            ValidationResult with issues found
        """
        result = ValidationResult(valid=True)
        
        # Step 1: Check syntax
        self._validate_syntax(content, filename, result)
        
        if not result.syntax_valid:
            return result
        
        # Step 2: Check imports
        self._validate_imports(content, filename, result)
        
        # Step 3: Check cocotb structure
        self._validate_cocotb_structure(content, filename, result)
        
        # Step 4: Check async/await usage
        self._validate_async_await(content, filename, result)
        
        return result
    
    def validate_project(self, project_dir: Path) -> ValidationResult:
        """
        Validate all Python files in a translated project.
        
        Args:
            project_dir: Directory containing translated files
            
        Returns:
            Aggregated ValidationResult
        """
        result = ValidationResult(valid=True)
        
        python_files = list(project_dir.glob('*.py'))
        
        if not python_files:
            result.add_warning(f"No Python files found in {project_dir}")
            return result
        
        for file_path in python_files:
            file_result = self.validate_file(file_path)
            
            # Merge results
            result.issues.extend(file_result.issues)
            result.num_tests += file_result.num_tests
            result.num_coroutines += file_result.num_coroutines
            result.imports_found.extend(file_result.imports_found)
            
            if not file_result.valid:
                result.valid = False
            if not file_result.syntax_valid:
                result.syntax_valid = False
            if not file_result.imports_valid:
                result.imports_valid = False
            if not file_result.cocotb_valid:
                result.cocotb_valid = False
        
        # Deduplicate imports
        result.imports_found = list(set(result.imports_found))
        
        return result
    
    def _validate_syntax(self, content: str, filename: str, 
                        result: ValidationResult) -> None:
        """Validate Python syntax."""
        try:
            ast.parse(content)
        except SyntaxError as e:
            result.syntax_valid = False
            result.add_error(
                f"Syntax error: {e.msg}",
                filename,
                e.lineno or 0,
                "Fix the Python syntax error"
            )
    
    def _validate_imports(self, content: str, filename: str,
                         result: ValidationResult) -> None:
        """Validate required imports."""
        try:
            tree = ast.parse(content)
        except SyntaxError:
            return
        
        imports = set()
        
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    imports.add(alias.name)
                    result.imports_found.append(alias.name)
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    imports.add(node.module)
                    result.imports_found.append(node.module)
        
        # Check required imports
        for req in self.REQUIRED_IMPORTS:
            if not any(req in imp for imp in imports):
                result.imports_valid = False
                result.add_error(
                    f"Missing required import: {req}",
                    filename,
                    suggestion=f"Add 'import {req}' at the top of the file"
                )
        
        # Check recommended imports
        if 'cocotb.clock' not in imports and 'Clock' not in content:
            result.add_warning(
                "Missing cocotb.clock import - Clock generation may not work",
                filename,
                suggestion="Add 'from cocotb.clock import Clock'"
            )
    
    def _validate_cocotb_structure(self, content: str, filename: str,
                                   result: ValidationResult) -> None:
        """Validate cocotb test structure."""
        try:
            tree = ast.parse(content)
        except SyntaxError:
            return
        
        num_tests = 0
        num_async_functions = 0
        
        for node in ast.walk(tree):
            if isinstance(node, ast.AsyncFunctionDef):
                num_async_functions += 1
                
                # Check for cocotb.test decorator
                for decorator in node.decorator_list:
                    if isinstance(decorator, ast.Attribute):
                        if decorator.attr == 'test':
                            num_tests += 1
                    elif isinstance(decorator, ast.Call):
                        if isinstance(decorator.func, ast.Attribute):
                            if decorator.func.attr == 'test':
                                num_tests += 1
        
        result.num_tests = num_tests
        result.num_coroutines = num_async_functions
        
        if num_tests == 0:
            result.cocotb_valid = False
            result.add_warning(
                "No @cocotb.test() decorated functions found",
                filename,
                suggestion="Add @cocotb.test() decorator to test functions"
            )
        
        if num_async_functions == 0:
            result.add_error(
                "No async functions found - cocotb requires async test functions",
                filename,
                suggestion="Make test functions async (async def test_xxx(dut):)"
            )
    
    def _validate_async_await(self, content: str, filename: str,
                             result: ValidationResult) -> None:
        """Validate async/await usage."""
        try:
            tree = ast.parse(content)
        except SyntaxError:
            return
        
        for node in ast.walk(tree):
            if isinstance(node, ast.AsyncFunctionDef):
                # Check function has await statements
                has_await = False
                for child in ast.walk(node):
                    if isinstance(child, ast.Await):
                        has_await = True
                        break
                
                if not has_await:
                    result.add_warning(
                        f"Async function '{node.name}' has no await statements",
                        filename,
                        node.lineno,
                        "Add await statements for cocotb triggers"
                    )
    
    def auto_fix(self, content: str) -> str:
        """
        Attempt to auto-fix common issues in translated code.
        
        Args:
            content: Python source code
            
        Returns:
            Fixed code (or original if no fixes needed)
        """
        lines = content.split('\n')
        fixed_lines = []
        
        # Track if we've added imports
        has_cocotb_import = False
        has_clock_import = False
        has_triggers_import = False
        
        for line in lines:
            if 'import cocotb' in line:
                has_cocotb_import = True
            if 'from cocotb.clock' in line:
                has_clock_import = True
            if 'from cocotb.triggers' in line:
                has_triggers_import = True
            fixed_lines.append(line)
        
        # Add missing imports at the top
        imports_to_add = []
        
        if not has_cocotb_import:
            imports_to_add.append('import cocotb')
        if not has_clock_import and 'Clock(' in content:
            imports_to_add.append('from cocotb.clock import Clock')
        if not has_triggers_import and any(t in content for t in ['RisingEdge', 'FallingEdge', 'Timer', 'ClockCycles']):
            imports_to_add.append('from cocotb.triggers import RisingEdge, FallingEdge, Timer, ClockCycles')
        
        if imports_to_add:
            # Find first non-comment, non-empty line
            insert_idx = 0
            for i, line in enumerate(fixed_lines):
                if line.strip() and not line.strip().startswith('#') and not line.strip().startswith('"""'):
                    insert_idx = i
                    break
            
            # Insert imports
            for imp in reversed(imports_to_add):
                fixed_lines.insert(insert_idx, imp)
        
        return '\n'.join(fixed_lines)


class CocotbLinter:
    """
    Linter specifically for cocotb testbenches.
    
    Checks for common cocotb-specific issues and best practices.
    """
    
    def __init__(self):
        pass
    
    def lint(self, content: str, filename: str = "") -> List[ValidationIssue]:
        """
        Lint cocotb code for common issues.
        
        Returns:
            List of ValidationIssue objects
        """
        issues = []
        
        lines = content.split('\n')
        
        for i, line in enumerate(lines, 1):
            # Check for common issues
            
            # Issue: Using time.sleep instead of cocotb triggers
            if 'time.sleep' in line:
                issues.append(ValidationIssue(
                    severity=ValidationSeverity.ERROR,
                    message="Using time.sleep() instead of cocotb triggers",
                    file=filename,
                    line=i,
                    suggestion="Use 'await Timer(time, units)' instead"
                ))
            
            # Issue: Non-async test function
            if '@cocotb.test' in line:
                # Check next non-empty line for async def
                for j in range(i, min(i + 5, len(lines))):
                    next_line = lines[j - 1].strip()
                    if next_line.startswith('def ') and 'async' not in next_line:
                        issues.append(ValidationIssue(
                            severity=ValidationSeverity.ERROR,
                            message="Test function must be async",
                            file=filename,
                            line=j,
                            suggestion="Change 'def' to 'async def'"
                        ))
                        break
                    elif next_line.startswith('async def'):
                        break
            
            # Warning: Direct signal assignment without .value
            if re.search(r'dut\.\w+\s*=\s*(?!.*\.value)', line):
                if '.value' not in line and '==' not in line:
                    issues.append(ValidationIssue(
                        severity=ValidationSeverity.WARNING,
                        message="Signal assignment may need .value accessor",
                        file=filename,
                        line=i,
                        suggestion="Use 'dut.signal.value = x' for signal assignment"
                    ))
            
            # Warning: Missing clock start
            if '@cocotb.test' in line:
                # Simple heuristic: look for Clock in the function
                func_content = '\n'.join(lines[i:min(i+50, len(lines))])
                if 'Clock' not in func_content and 'clock' not in func_content.lower():
                    issues.append(ValidationIssue(
                        severity=ValidationSeverity.WARNING,
                        message="Test may be missing clock generation",
                        file=filename,
                        line=i,
                        suggestion="Add 'cocotb.start_soon(Clock(dut.clk, period, units).start())'"
                    ))
        
        return issues

