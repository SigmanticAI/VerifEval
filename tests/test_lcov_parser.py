"""
Test LCOV coverage parser
"""

from pathlib import Path
import tempfile


def create_sample_lcov_file(path: Path) -> None:
    """Create a sample LCOV .info file for testing"""
    content = """TN:test_adder
SF:rtl/adder.sv
FN:8,adder
FNDA:1000,adder
FNF:1
FNH:1
DA:8,1000
DA:9,1000
DA:10,1000
DA:11,1000
DA:12,1000
DA:13,850
DA:14,850
DA:15,850
DA:16,750
DA:17,750
DA:18,1000
DA:19,150
DA:20,150
DA:21,0
DA:22,0
LF:15
LH:13
BRDA:13,0,0,850
BRDA:13,0,1,150
BRDA:16,1,0,750
BRDA:16,1,1,250
BRF:4
BRH:4
end_of_record
SF:rtl/full_adder.sv
FN:5,full_adder
FNDA:8000,full_adder
DA:5,8000
DA:6,8000
DA:7,8000
DA:8,8000
DA:9,8000
DA:10,8000
LF:6
LH:6
BRF:0
BRH:0
end_of_record
"""
    path.write_text(content)


def test_can_parse():
    """Test LCOV format detection"""
    from step5_coverage.parsers.lcov_parser import LCOVParser
    
    parser = LCOVParser()
    
    # Test with .info extension and LCOV content
    with tempfile.NamedTemporaryFile(suffix='.info', delete=False) as f:
        f.write(b"TN:test\nSF:test.sv\nDA:10,5\nend_of_record\n")
        temp_path = Path(f.name)
    
    try:
        assert parser.can_parse(temp_path)
    finally:
        temp_path.unlink()
    
    # Test with .lcov extension
    with tempfile.NamedTemporaryFile(suffix='.lcov', delete=False) as f:
        f.write(b"SF:test.c\nDA:10,5\n")
        temp_path = Path(f.name)
    
    try:
        assert parser.can_parse(temp_path)
    finally:
        temp_path.unlink()
    
    # Test with wrong extension
    with tempfile.NamedTemporaryFile(suffix='.txt', delete=False) as f:
        f.write(b"SF:test.c\nDA:10,5\n")
        temp_path = Path(f.name)
    
    try:
        assert not parser.can_parse(temp_path)
    finally:
        temp_path.unlink()


def test_get_format():
    """Test format identifier"""
    from step5_coverage.parsers.lcov_parser import LCOVParser
    from step5_coverage.models import CoverageFormat
    
    parser = LCOVParser()
    assert parser.get_format() == CoverageFormat.LCOV_INFO


def test_parse_python():
    """Test Python-based parsing"""
    from step5_coverage.parsers.lcov_parser import LCOVParser
    
    parser = LCOVParser()
    
    with tempfile.NamedTemporaryFile(suffix='.info', delete=False) as f:
        temp_path = Path(f.name)
    
    try:
        create_sample_lcov_file(temp_path)
        
        result = parser._parse_with_python(temp_path)
        
        assert result.success
        assert result.coverage is not None
        
        # Check parsed data
        module = result.coverage
        assert len(module.files) == 2
        assert "rtl/adder.sv" in module.files
        assert "rtl/full_adder.sv" in module.files
        
        # Check adder.sv
        adder = module.files["rtl/adder.sv"]
        assert len(adder.lines) == 15
        assert adder.lines[8].hit_count == 1000
        assert adder.lines[21].hit_count == 0
        
        # Check branches
        assert len(adder.branches) == 4
        
        # Check full_adder.sv
        full_adder = module.files["rtl/full_adder.sv"]
        assert len(full_adder.lines) == 6
        assert full_adder.lines[5].hit_count == 8000
        
    finally:
        temp_path.unlink()


def test_parse_file():
    """Test complete parse_file method"""
    from step5_coverage.parsers.lcov_parser import LCOVParser
    
    parser = LCOVParser()
    
    with tempfile.NamedTemporaryFile(suffix='.info', delete=False) as f:
        temp_path = Path(f.name)
    
    try:
        create_sample_lcov_file(temp_path)
        
        result = parser.parse_file(temp_path)
        
        assert result.success
        assert result.coverage is not None
        assert result.parse_time_ms >= 0
        
        # Verify metrics
        adder = result.coverage.files["rtl/adder.sv"]
        
        # Line coverage: 13 of 15 = 86.7%
        assert adder.total_lines == 15
        assert adder.covered_lines == 13
        assert 86.0 < adder.line_coverage_percent < 87.0
        
        # Branch coverage: 4 of 4 = 100%
        assert adder.total_branches == 4
        assert adder.branch_coverage_percent == 100.0
        
    finally:
        temp_path.unlink()


def test_merge_python():
    """Test Python-based merging"""
    from step5_coverage.parsers.lcov_parser import LCOVParser
    
    parser = LCOVParser()
    
    file1_content = """TN:test1
SF:test.sv
DA:10,5
DA:20,3
end_of_record
"""
    
    file2_content = """TN:test2
SF:test.sv
DA:10,7
DA:30,2
end_of_record
"""
    
    files = []
    for content in [file1_content, file2_content]:
        with tempfile.NamedTemporaryFile(suffix='.info', delete=False, mode='w') as f:
            f.write(content)
            files.append(Path(f.name))
    
    try:
        result = parser.merge_coverage(files)
        
        assert result.success
        assert result.merged_coverage is not None
        
        # Check merged data
        test_file = result.merged_coverage.files["test.sv"]
        
        # Line 10: 5 + 7 = 12
        assert test_file.lines[10].hit_count == 12
        
        # Line 20: only in file1 = 3
        assert test_file.lines[20].hit_count == 3
        
        # Line 30: only in file2 = 2
        assert test_file.lines[30].hit_count == 2
        
    finally:
        for f in files:
            f.unlink()


def test_validation():
    """Test count validation"""
    from step5_coverage.parsers.lcov_parser import LCOVParser
    
    parser = LCOVParser()
    
    # File with mismatched counts
    content = """SF:test.sv
DA:10,5
DA:20,0
LF:3
LH:1
end_of_record
"""
    
    with tempfile.NamedTemporaryFile(suffix='.info', delete=False, mode='w') as f:
        f.write(content)
        temp_path = Path(f.name)
    
    try:
        result = parser._parse_with_python(temp_path)
        
        # Should succeed but with warnings
        assert result.success
        assert result.has_warnings
        
        # Should have warnings about mismatched counts
        warnings_text = ' '.join(result.warnings)
        assert 'mismatch' in warnings_text.lower()
        
    finally:
        temp_path.unlink()


def test_extract_summary():
    """Test summary extraction"""
    from step5_coverage.parsers.lcov_parser import LCOVParser
    
    parser = LCOVParser()
    
    with tempfile.NamedTemporaryFile(suffix='.info', delete=False) as f:
        temp_path = Path(f.name)
    
    try:
        create_sample_lcov_file(temp_path)
        
        summary = parser.extract_summary(temp_path)
        
        assert summary is not None
        assert 'lines_found' in summary
        assert 'lines_hit' in summary
        assert 'line_percentage' in summary
        
        # Should have 21 total lines (15 + 6)
        assert summary['lines_found'] == 21
        # Should have 19 hit lines (13 + 6)
        assert summary['lines_hit'] == 19
        
    finally:
        temp_path.unlink()


def test_with_checksums():
    """Test parsing with line checksums"""
    from step5_coverage.parsers.lcov_parser import LCOVParser
    
    parser = LCOVParser()
    
    content = """SF:test.c
DA:10,5,abc123
DA:11,3,def456
DA:12,0,ghi789
LF:3
LH:2
end_of_record
"""
    
    with tempfile.NamedTemporaryFile(suffix='.info', delete=False, mode='w') as f:
        f.write(content)
        temp_path = Path(f.name)
    
    try:
        result = parser.parse_file(temp_path)
        
        assert result.success
        
        file_cov = result.coverage.files["test.c"]
        assert len(file_cov.lines) == 3
        assert file_cov.lines[10].hit_count == 5
        assert file_cov.lines[12].hit_count == 0
        
    finally:
        temp_path.unlink()


def test_convenience_functions():
    """Test convenience functions"""
    from step5_coverage.parsers.lcov_parser import (
        create_lcov_parser,
        is_lcov_available,
    )
    
    parser = create_lcov_parser()
    assert parser is not None
    
    available = is_lcov_available()
    assert isinstance(available, bool)


if __name__ == "__main__":
    print("Testing LCOV parser...")
    
    test_can_parse()
    print("✓ Format detection")
    
    test_get_format()
    print("✓ Format identifier")
    
    test_parse_python()
    print("✓ Python parsing")
    
    test_parse_file()
    print("✓ Parse file")
    
    test_merge_python()
    print("✓ Python merging")
    
    test_validation()
    print("✓ Count validation")
    
    test_extract_summary()
    print("✓ Summary extraction")
    
    test_with_checksums()
    print("✓ Checksum handling")
    
    test_convenience_functions()
    print("✓ Convenience functions")
    
    print("\n✅ All LCOV parser tests passed!")
