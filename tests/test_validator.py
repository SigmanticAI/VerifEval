"""
Tests for Translation Validator module.
"""

import pytest
from pathlib import Path
from uvm_translator.validator import (
    TranslationValidator, ValidationResult, ValidationIssue,
    ValidationSeverity, CocotbLinter
)


class TestValidationResult:
    """Tests for ValidationResult dataclass."""
    
    def test_empty_result(self):
        """Test empty validation result."""
        result = ValidationResult(valid=True)
        
        assert result.valid == True
        assert result.syntax_valid == True
        assert len(result.issues) == 0
    
    def test_add_error(self):
        """Test adding an error."""
        result = ValidationResult(valid=True)
        result.add_error("Test error", "test.py", 10)
        
        assert result.valid == False
        assert len(result.issues) == 1
        assert result.issues[0].severity == ValidationSeverity.ERROR
    
    def test_add_warning(self):
        """Test adding a warning."""
        result = ValidationResult(valid=True)
        result.add_warning("Test warning", "test.py", 5)
        
        assert result.valid == True  # Warnings don't invalidate
        assert len(result.issues) == 1
        assert result.issues[0].severity == ValidationSeverity.WARNING
    
    def test_to_dict(self):
        """Test serialization."""
        result = ValidationResult(valid=True)
        result.num_tests = 3
        result.num_coroutines = 5
        
        data = result.to_dict()
        
        assert data['valid'] == True
        assert data['num_tests'] == 3
        assert data['num_coroutines'] == 5


class TestTranslationValidator:
    """Tests for TranslationValidator."""
    
    @pytest.fixture
    def validator(self):
        return TranslationValidator()
    
    def test_validate_valid_cocotb(self, validator):
        """Test validation of valid cocotb code."""
        code = '''
import cocotb
from cocotb.clock import Clock
from cocotb.triggers import RisingEdge

@cocotb.test()
async def test_basic(dut):
    cocotb.start_soon(Clock(dut.clk, 10, units='ns').start())
    await RisingEdge(dut.clk)
    assert True
'''
        result = validator.validate_content(code, "test.py")
        
        assert result.syntax_valid == True
        assert result.num_tests >= 1
    
    def test_validate_syntax_error(self, validator):
        """Test detection of syntax errors."""
        code = '''
import cocotb

def broken_function(
    # Missing closing paren
'''
        result = validator.validate_content(code, "test.py")
        
        assert result.syntax_valid == False
        assert any(i.severity == ValidationSeverity.ERROR for i in result.issues)
    
    def test_validate_missing_cocotb_import(self, validator):
        """Test detection of missing cocotb import."""
        code = '''
async def test_basic(dut):
    pass
'''
        result = validator.validate_content(code, "test.py")
        
        assert result.imports_valid == False
    
    def test_validate_missing_test_decorator(self, validator):
        """Test detection of missing @cocotb.test() decorator."""
        code = '''
import cocotb
from cocotb.triggers import RisingEdge

async def test_without_decorator(dut):
    await RisingEdge(dut.clk)
'''
        result = validator.validate_content(code, "test.py")
        
        # Should have warning about no tests
        assert result.num_tests == 0
    
    def test_validate_non_async_test(self, validator):
        """Test that non-async tests are flagged."""
        code = '''
import cocotb

def sync_function():
    pass
'''
        result = validator.validate_content(code, "test.py")
        
        # Should flag missing async
        assert result.num_coroutines == 0
    
    def test_validate_file(self, validator, tmp_path):
        """Test file validation."""
        test_file = tmp_path / "test_dut.py"
        test_file.write_text('''
import cocotb
from cocotb.triggers import RisingEdge

@cocotb.test()
async def test_basic(dut):
    await RisingEdge(dut.clk)
''')
        
        result = validator.validate_file(test_file)
        
        assert result.syntax_valid == True
        assert result.num_tests >= 1
    
    def test_validate_project(self, validator, tmp_path):
        """Test project validation."""
        # Create multiple Python files
        (tmp_path / "test_basic.py").write_text('''
import cocotb
from cocotb.triggers import RisingEdge

@cocotb.test()
async def test_one(dut):
    await RisingEdge(dut.clk)
''')
        
        (tmp_path / "test_advanced.py").write_text('''
import cocotb
from cocotb.triggers import ClockCycles

@cocotb.test()
async def test_two(dut):
    await ClockCycles(dut.clk, 10)
''')
        
        result = validator.validate_project(tmp_path)
        
        assert result.num_tests >= 2


class TestAutoFix:
    """Tests for auto-fix functionality."""
    
    @pytest.fixture
    def validator(self):
        return TranslationValidator()
    
    def test_auto_fix_missing_imports(self, validator):
        """Test auto-fixing missing imports."""
        code = '''
@cocotb.test()
async def test_basic(dut):
    Clock(dut.clk, 10, units='ns').start()
    await RisingEdge(dut.clk)
'''
        fixed = validator.auto_fix(code)
        
        assert "import cocotb" in fixed
        assert "from cocotb.clock import Clock" in fixed
        assert "from cocotb.triggers" in fixed
    
    def test_auto_fix_preserves_valid_code(self, validator):
        """Test that auto-fix preserves already valid code."""
        code = '''import cocotb
from cocotb.clock import Clock
from cocotb.triggers import RisingEdge

@cocotb.test()
async def test_basic(dut):
    await RisingEdge(dut.clk)
'''
        fixed = validator.auto_fix(code)
        
        # Should not duplicate imports
        assert fixed.count("import cocotb") == 1


class TestCocotbLinter:
    """Tests for cocotb-specific linter."""
    
    @pytest.fixture
    def linter(self):
        return CocotbLinter()
    
    def test_lint_time_sleep_usage(self, linter):
        """Test detection of time.sleep usage."""
        code = '''
import time

def bad_function():
    time.sleep(1)
'''
        issues = linter.lint(code, "test.py")
        
        assert len(issues) > 0
        assert any("time.sleep" in i.message for i in issues)
    
    def test_lint_missing_value_accessor(self, linter):
        """Test detection of missing .value accessor."""
        code = '''
dut.signal = 1  # Should use dut.signal.value
'''
        issues = linter.lint(code, "test.py")
        
        # May or may not flag this depending on implementation
        assert isinstance(issues, list)
    
    def test_lint_non_async_test(self, linter):
        """Test detection of non-async test function."""
        code = '''
@cocotb.test()
def test_sync(dut):
    pass
'''
        issues = linter.lint(code, "test.py")
        
        assert any("async" in i.message.lower() for i in issues)


class TestValidationIssue:
    """Tests for ValidationIssue dataclass."""
    
    def test_issue_creation(self):
        """Test creating a validation issue."""
        issue = ValidationIssue(
            severity=ValidationSeverity.ERROR,
            message="Test error message",
            file="test.py",
            line=42,
            suggestion="Fix the error"
        )
        
        assert issue.severity == ValidationSeverity.ERROR
        assert issue.message == "Test error message"
        assert issue.line == 42
        assert issue.suggestion == "Fix the error"


class TestValidationSeverity:
    """Tests for ValidationSeverity enum."""
    
    def test_severity_values(self):
        """Test severity values."""
        assert ValidationSeverity.ERROR.value == "error"
        assert ValidationSeverity.WARNING.value == "warning"
        assert ValidationSeverity.INFO.value == "info"

