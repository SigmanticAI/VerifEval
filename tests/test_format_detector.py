"""
Test format detector
"""

from pathlib import Path
import tempfile


def test_detection_result():
    """Test DetectionResult class"""
    from step5_coverage.parsers.format_detector import DetectionResult
    from step5_coverage.models import CoverageFormat
    
    # Successful detection
    result = DetectionResult(
        file_path=Path("test.dat"),
        detected_format=CoverageFormat.VERILATOR_DAT,
        confidence=1.0
    )
    
    assert result.success
    assert result.format_name == "verilator_dat"
    
    # Failed detection
    result = DetectionResult(
        file_path=Path("test.dat"),
        error="No parser found"
    )
    
    assert not result.success
    assert result.format_name == "unknown"


def test_batch_detection_result():
    """Test BatchDetectionResult class"""
    from step5_coverage.parsers.format_detector import (
        BatchDetectionResult,
        DetectionResult
    )
    from step5_coverage.models import CoverageFormat
    
    batch = BatchDetectionResult()
    
    # Add successful result
    result1 = DetectionResult(
        file_path=Path("test1.dat"),
        detected_format=CoverageFormat.VERILATOR_DAT,
        confidence=1.0
    )
    result1.parser = object()  # Mock parser
    batch.add_result(result1)
    
    # Add failed result
    result2 = DetectionResult(
        file_path=Path("test2.txt"),
        error="Unknown format"
    )
    batch.add_result(result2)
    
    assert batch.total_files == 2
    assert batch.successful == 1
    assert batch.failed == 1
    
    summary = batch.get_summary()
    assert summary["success_rate"] == 50.0


def test_format_detector_creation():
    """Test FormatDetector creation"""
    from step5_coverage.parsers.format_detector import FormatDetector
    
    # Create with default parsers
    detector = FormatDetector()
    
    assert detector is not None
    assert len(detector.parsers) > 0
    
    # Check available formats
    formats = detector.get_available_formats()
    assert len(formats) > 0


def test_detect_verilator():
    """Test Verilator format detection"""
    from step5_coverage.parsers.format_detector import FormatDetector
    from step5_coverage.models import CoverageFormat
    
    detector = FormatDetector()
    
    # Create Verilator .dat file
    content = """# Verilator coverage database
SF:test.sv
DA:10,5
end_of_record
"""
    
    with tempfile.NamedTemporaryFile(suffix='.dat', delete=False, mode='w') as f:
        f.write(content)
        temp_path = Path(f.name)
    
    try:
        result = detector.detect(temp_path)
        
        assert result.success
        assert result.detected_format == CoverageFormat.VERILATOR_DAT
        assert result.parser is not None
        assert result.confidence > 0
        
    finally:
        temp_path.unlink()


def test_detect_lcov():
    """Test LCOV format detection"""
    from step5_coverage.parsers.format_detector import FormatDetector
    from step5_coverage.models import CoverageFormat
    
    detector = FormatDetector()
    
    # Create LCOV .info file
    content = """TN:test
SF:test.c
DA:10,5
end_of_record
"""
    
    with tempfile.NamedTemporaryFile(suffix='.info', delete=False, mode='w') as f:
        f.write(content)
        temp_path = Path(f.name)
    
    try:
        result = detector.detect(temp_path)
        
        assert result.success
        assert result.detected_format == CoverageFormat.LCOV_INFO
        assert result.parser is not None
        
    finally:
        temp_path.unlink()


def test_detect_unknown_format():
    """Test detection of unknown format"""
    from step5_coverage.parsers.format_detector import FormatDetector
    
    detector = FormatDetector()
    
    # Create file with unknown format
    with tempfile.NamedTemporaryFile(suffix='.txt', delete=False, mode='w') as f:
        f.write("This is not a coverage file")
        temp_path = Path(f.name)
    
    try:
        result = detector.detect(temp_path)
        
        assert not result.success
        assert result.detected_format is None
        assert result.parser is None
        assert result.error is not None
        
    finally:
        temp_path.unlink()


def test_batch_detection():
    """Test batch format detection"""
    from step5_coverage.parsers.format_detector import FormatDetector
    
    detector = FormatDetector()
    
    # Create multiple files
    files = []
    
    # Verilator file
    with tempfile.NamedTemporaryFile(suffix='.dat', delete=False, mode='w') as f:
        f.write("# Verilator coverage\nSF:test.sv\nDA:10,5\n")
        files.append(Path(f.name))
    
    # LCOV file
    with tempfile.NamedTemporaryFile(suffix='.info', delete=False, mode='w') as f:
        f.write("SF:test.c\nDA:10,5\n")
        files.append(Path(f.name))
    
    # Unknown file
    with tempfile.NamedTemporaryFile(suffix='.txt', delete=False, mode='w') as f:
        f.write("Unknown format")
        files.append(Path(f.name))
    
    try:
        batch_result = detector.detect_batch(files)
        
        assert batch_result.total_files == 3
        assert batch_result.successful == 2
        assert batch_result.failed == 1
        
        summary = batch_result.get_summary()
        assert summary["success_rate"] > 60.0
        
    finally:
        for f in files:
            f.unlink()


def test_group_by_format():
    """Test grouping files by format"""
    from step5_coverage.parsers.format_detector import FormatDetector
    from step5_coverage.models import CoverageFormat
    
    detector = FormatDetector()
    
    files = []
    
    # Create two Verilator files
    for i in range(2):
        with tempfile.NamedTemporaryFile(suffix='.dat', delete=False, mode='w') as f:
            f.write(f"# Verilator coverage\nSF:test{i}.sv\nDA:10,5\n")
            files.append(Path(f.name))
    
    # Create one LCOV file
    with tempfile.NamedTemporaryFile(suffix='.info', delete=False, mode='w') as f:
        f.write("SF:test.c\nDA:10,5\n")
        files.append(Path(f.name))
    
    try:
        grouped = detector.group_by_format(files)
        
        assert len(grouped) == 2
        assert CoverageFormat.VERILATOR_DAT in grouped
        assert CoverageFormat.LCOV_INFO in grouped
        assert len(grouped[CoverageFormat.VERILATOR_DAT]) == 2
        assert len(grouped[CoverageFormat.LCOV_INFO]) == 1
        
    finally:
        for f in files:
            f.unlink()


def test_filter_by_format():
    """Test filtering files by format"""
    from step5_coverage.parsers.format_detector import FormatDetector
    from step5_coverage.models import CoverageFormat
    
    detector = FormatDetector()
    
    files = []
    
    # Create mixed files
    with tempfile.NamedTemporaryFile(suffix='.dat', delete=False, mode='w') as f:
        f.write("# Verilator coverage\nSF:test.sv\nDA:10,5\n")
        files.append(Path(f.name))
    
    with tempfile.NamedTemporaryFile(suffix='.info', delete=False, mode='w') as f:
        f.write("SF:test.c\nDA:10,5\n")
        files.append(Path(f.name))
    
    try:
        # Filter for Verilator only
        verilator_files = detector.filter_by_format(
            files,
            CoverageFormat.VERILATOR_DAT
        )
        
        assert len(verilator_files) == 1
        assert verilator_files[0].suffix == '.dat'
        
    finally:
        for f in files:
            f.unlink()


def test_get_parser_for_format():
    """Test getting parser for specific format"""
    from step5_coverage.parsers.format_detector import FormatDetector
    from step5_coverage.models import CoverageFormat
    
    detector = FormatDetector()
    
    # Get Verilator parser
    parser = detector.get_parser_for_format(CoverageFormat.VERILATOR_DAT)
    
    assert parser is not None
    assert parser.get_format() == CoverageFormat.VERILATOR_DAT


def test_statistics():
    """Test detection statistics"""
    from step5_coverage.parsers.format_detector import FormatDetector
    
    detector = FormatDetector()
    
    # Create and detect files
    files = []
    
    with tempfile.NamedTemporaryFile(suffix='.dat', delete=False, mode='w') as f:
        f.write("# Verilator coverage\nSF:test.sv\nDA:10,5\n")
        files.append(Path(f.name))
    
    with tempfile.NamedTemporaryFile(suffix='.txt', delete=False, mode='w') as f:
        f.write("Unknown")
        files.append(Path(f.name))
    
    try:
        for file in files:
            detector.detect(file)
        
        stats = detector.get_statistics()
        
        assert stats["detections_attempted"] == 2
        assert stats["detections_successful"] == 1
        assert stats["detections_failed"] == 1
        assert stats["success_rate"] == 50.0
        
    finally:
        for f in files:
            f.unlink()


def test_diagnose_file():
    """Test file diagnostics"""
    from step5_coverage.parsers.format_detector import FormatDetector
    
    detector = FormatDetector()
    
    with tempfile.NamedTemporaryFile(suffix='.dat', delete=False, mode='w') as f:
        f.write("# Verilator coverage\nSF:test.sv\nDA:10,5\n")
        temp_path = Path(f.name)
    
    try:
        diagnostics = detector.diagnose_file(temp_path)
        
        assert diagnostics["exists"]
        assert diagnostics["is_file"]
        assert diagnostics["extension"] == ".dat"
        assert len(diagnostics["parsers_tested"]) > 0
        
        # At least one parser should match
        assert any(p["can_parse"] for p in diagnostics["parsers_tested"])
        
    finally:
        temp_path.unlink()


def test_convenience_functions():
    """Test convenience functions"""
    from step5_coverage.parsers.format_detector import (
        create_detector,
        detect_format,
        group_coverage_files,
    )
    from step5_coverage.models import CoverageFormat
    
    # Test create_detector
    detector = create_detector()
    assert detector is not None
    
    # Test detect_format
    with tempfile.NamedTemporaryFile(suffix='.dat', delete=False, mode='w') as f:
        f.write("# Verilator coverage\nSF:test.sv\nDA:10,5\n")
        temp_path = Path(f.name)
    
    try:
        format = detect_format(temp_path)
        assert format == CoverageFormat.VERILATOR_DAT
    finally:
        temp_path.unlink()


if __name__ == "__main__":
    print("Testing format detector...")
    
    test_detection_result()
    print("✓ DetectionResult")
    
    test_batch_detection_result()
    print("✓ BatchDetectionResult")
    
    test_format_detector_creation()
    print("✓ FormatDetector creation")
    
    test_detect_verilator()
    print("✓ Verilator detection")
    
    test_detect_lcov()
    print("✓ LCOV detection")
    
    test_detect_unknown_format()
    print("✓ Unknown format handling")
    
    test_batch_detection()
    print("✓ Batch detection")
    
    test_group_by_format()
    print("✓ Group by format")
    
    test_filter_by_format()
    print("✓ Filter by format")
    
    test_get_parser_for_format()
    print("✓ Get parser for format")
    
    test_statistics()
    print("✓ Statistics tracking")
    
    test_diagnose_file()
    print("✓ File diagnostics")
    
    test_convenience_functions()
    print("✓ Convenience functions")
    
    print("\n✅ All format detector tests passed!")
