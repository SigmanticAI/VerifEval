"""
Test base parser functionality
"""

from pathlib import Path
import tempfile
from typing import Optional, List


def test_parse_result():
    """Test ParseResult class"""
    from step5_coverage.parsers.base import ParseResult
    
    result = ParseResult(success=True)
    assert result.success
    assert not result.has_errors
    assert not result.has_warnings
    
    result.add_warning("Test warning")
    assert result.has_warnings
    assert len(result.warnings) == 1
    
    result.add_error("Test error")
    assert result.has_errors
    assert not result.success  # Error should set success to False


def test_merge_result():
    """Test MergeResult class"""
    from step5_coverage.parsers.base import MergeResult
    
    result = MergeResult(success=True)
    assert result.success
    
    result.add_error("Merge failed")
    assert not result.success
    assert "Merge failed" in result.errors


def test_concrete_parser():
    """Test concrete parser implementation"""
    from step5_coverage.parsers.base import BaseParser, ParseResult
    from step5_coverage.models import CoverageFormat, ModuleCoverage
    from step5_coverage.config import ParserConfig
    
    # Create a concrete test parser
    class TestParser(BaseParser):
        def can_parse(self, file_path: Path) -> bool:
            return file_path.suffix == ".test"
        
        def get_format(self) -> CoverageFormat:
            return CoverageFormat.UNKNOWN
        
        def _parse_with_python(self, file_path: Path) -> ParseResult:
            result = ParseResult(success=True)
            result.coverage = ModuleCoverage(
                module_name="test_module",
                source_files=[str(file_path)]
            )
            return result
        
        def _get_external_tool_path(self) -> Optional[Path]:
            return None
    
    # Test parser
    parser = TestParser()
    
    # Test can_parse
    assert parser.can_parse(Path("test.test"))
    assert not parser.can_parse(Path("test.other"))
    
    # Test get_format
    assert parser.get_format() == CoverageFormat.UNKNOWN


def test_file_validation():
    """Test file validation"""
    from step5_coverage.parsers.base import BaseParser, ParseResult
    from step5_coverage.models import CoverageFormat, ModuleCoverage
    
    class TestParser(BaseParser):
        def can_parse(self, file_path: Path) -> bool:
            return file_path.suffix == ".test"
        
        def get_format(self) -> CoverageFormat:
            return CoverageFormat.UNKNOWN
        
        def _parse_with_python(self, file_path: Path) -> ParseResult:
            result = ParseResult(success=True)
            result.coverage = ModuleCoverage(module_name="test")
            return result
        
        def _get_external_tool_path(self) -> Optional[Path]:
            return None
    
    parser = TestParser()
    
    # Test non-existent file
    assert not parser.validate_file(Path("nonexistent.test"))
    assert len(parser.errors) > 0
    assert "not found" in parser.errors[0].lower()
    
    # Test with actual file
    with tempfile.NamedTemporaryFile(suffix=".test", delete=False) as f:
        f.write(b"test data")
        temp_path = Path(f.name)
    
    try:
        parser.reset_errors()
        assert parser.validate_file(temp_path)
        assert len(parser.errors) == 0
    finally:
        temp_path.unlink()
    
    # Test empty file
    with tempfile.NamedTemporaryFile(suffix=".test", delete=False) as f:
        temp_path = Path(f.name)
    
    try:
        parser.reset_errors()
        assert not parser.validate_file(temp_path)
        assert any("empty" in e.lower() for e in parser.errors)
    finally:
        temp_path.unlink()


def test_parse_file():
    """Test parse_file method"""
    from step5_coverage.parsers.base import BaseParser, ParseResult
    from step5_coverage.models import CoverageFormat, ModuleCoverage
    
    class TestParser(BaseParser):
        def can_parse(self, file_path: Path) -> bool:
            return file_path.suffix == ".test"
        
        def get_format(self) -> CoverageFormat:
            return CoverageFormat.UNKNOWN
        
        def _parse_with_python(self, file_path: Path) -> ParseResult:
            result = ParseResult(success=True)
            result.coverage = ModuleCoverage(
                module_name="test_module",
                source_files=[str(file_path)]
            )
            return result
        
        def _get_external_tool_path(self) -> Optional[Path]:
            return None
    
    parser = TestParser()
    
    # Create test file
    with tempfile.NamedTemporaryFile(suffix=".test", delete=False) as f:
        f.write(b"test coverage data")
        temp_path = Path(f.name)
    
    try:
        result = parser.parse_file(temp_path)
        assert result.success
        assert result.coverage is not None
        assert result.coverage.module_name == "test_module"
        assert result.parse_time_ms >= 0
    finally:
        temp_path.unlink()


def test_merge_coverage():
    """Test merge_coverage method"""
    from step5_coverage.parsers.base import BaseParser, ParseResult
    from step5_coverage.models import (
        CoverageFormat,
        ModuleCoverage,
        FileCoverage,
        LineCoverageData
    )
    
    class TestParser(BaseParser):
        def can_parse(self, file_path: Path) -> bool:
            return file_path.suffix == ".test"
        
        def get_format(self) -> CoverageFormat:
            return CoverageFormat.UNKNOWN
        
        def _parse_with_python(self, file_path: Path) -> ParseResult:
            # Create coverage with different lines based on filename
            result = ParseResult(success=True)
            module = ModuleCoverage(module_name="test")
            file_cov = FileCoverage(file_path="test.sv")
            
            # Different coverage for different files
            if "file1" in str(file_path):
                file_cov.lines[10] = LineCoverageData(line_number=10, hit_count=5)
                file_cov.lines[20] = LineCoverageData(line_number=20, hit_count=3)
            elif "file2" in str(file_path):
                file_cov.lines[10] = LineCoverageData(line_number=10, hit_count=7)
                file_cov.lines[30] = LineCoverageData(line_number=30, hit_count=2)
            
            module.files["test.sv"] = file_cov
            result.coverage = module
            return result
        
        def _get_external_tool_path(self) -> Optional[Path]:
            return None
    
    parser = TestParser()
    
    # Create test files
    files = []
    for name in ["file1.test", "file2.test"]:
        with tempfile.NamedTemporaryFile(suffix=".test", delete=False) as f:
            f.write(b"test data")
            files.append(Path(f.name))
    
    try:
        result = parser.merge_coverage(files)
        assert result.success
        assert result.merged_coverage is not None
        
        # Check merged lines
        merged_file = result.merged_coverage.files["test.sv"]
        assert len(merged_file.lines) == 3  # Lines 10, 20, 30
        assert merged_file.lines[10].hit_count == 12  # 5 + 7
        assert merged_file.lines[20].hit_count == 3
        assert merged_file.lines[30].hit_count == 2
    finally:
        for f in files:
            f.unlink()


def test_helper_methods():
    """Test helper methods"""
    from step5_coverage.parsers.base import BaseParser, ParseResult
    from step5_coverage.models import CoverageFormat, ModuleCoverage
    
    class TestParser(BaseParser):
        def can_parse(self, file_path: Path) -> bool:
            return True
        
        def get_format(self) -> CoverageFormat:
            return CoverageFormat.UNKNOWN
        
        def _parse_with_python(self, file_path: Path) -> ParseResult:
            return ParseResult(success=True)
        
        def _get_external_tool_path(self) -> Optional[Path]:
            return None
    
    parser = TestParser()
    
    # Test read_file_lines
    with tempfile.NamedTemporaryFile(mode='w', delete=False) as f:
        f.write("line1\nline2\nline3\n")
        temp_path = Path(f.name)
    
    try:
        lines = parser.read_file_lines(temp_path)
        assert len(lines) == 3
        assert lines[0] == "line1"
        assert lines[2] == "line3"
    finally:
        temp_path.unlink()
    
    # Test check_file_contains
    with tempfile.NamedTemporaryFile(mode='w', delete=False) as f:
        f.write("This file contains coverage data\n")
        temp_path = Path(f.name)
    
    try:
        assert parser.check_file_contains(temp_path, ["coverage"])
        assert not parser.check_file_contains(temp_path, ["nonexistent"])
    finally:
        temp_path.unlink()


def test_diagnostics():
    """Test diagnostics"""
    from step5_coverage.parsers.base import BaseParser, ParseResult
    from step5_coverage.models import CoverageFormat
    
    class TestParser(BaseParser):
        def can_parse(self, file_path: Path) -> bool:
            return True
        
        def get_format(self) -> CoverageFormat:
            return CoverageFormat.UNKNOWN
        
        def _parse_with_python(self, file_path: Path) -> ParseResult:
            return ParseResult(success=True)
        
        def _get_external_tool_path(self) -> Optional[Path]:
            return None
    
    parser = TestParser()
    parser.errors.append("Test error")
    parser.warnings.append("Test warning")
    
    diag = parser.get_diagnostics()
    assert "parser_class" in diag
    assert "format" in diag
    assert "external_tool_available" in diag
    assert diag["errors"] == ["Test error"]
    assert diag["warnings"] == ["Test warning"]


if __name__ == "__main__":
    print("Testing base parser...")
    
    test_parse_result()
    print("✓ ParseResult")
    
    test_merge_result()
    print("✓ MergeResult")
    
    test_concrete_parser()
    print("✓ Concrete parser")
    
    test_file_validation()
    print("✓ File validation")
    
    test_parse_file()
    print("✓ Parse file")
    
    test_merge_coverage()
    print("✓ Merge coverage")
    
    test_helper_methods()
    print("✓ Helper methods")
    
    test_diagnostics()
    print("✓ Diagnostics")
    
    print("\n✅ All base parser tests passed!")
