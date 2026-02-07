"""
Coverage format detector

Automatically detects coverage file formats and selects appropriate parsers.

This module provides intelligent format detection across multiple coverage
file formats, supporting both single-file and batch detection.

Detection Strategy:
1. Try parsers in priority order (from config)
2. Use each parser's can_parse() method
3. Return first matching parser
4. Handle ambiguous cases (multiple matches)

Author: TB Eval Team
Version: 0.1.0
"""

from pathlib import Path
from typing import List, Dict, Optional, Tuple, Set
from dataclasses import dataclass, field
from collections import defaultdict
import logging

from .base import BaseParser
from ..models import CoverageFormat
from ..config import ParserConfig


# =============================================================================
# DETECTION RESULT
# =============================================================================

@dataclass
class DetectionResult:
    """
    Result of format detection for a single file
    
    Attributes:
        file_path: Path to the file
        detected_format: Detected coverage format (None if unknown)
        parser: Selected parser instance (None if no match)
        confidence: Confidence level (0.0 to 1.0)
        ambiguous: Whether multiple parsers matched
        matching_parsers: List of all parsers that matched
        error: Error message if detection failed
    """
    file_path: Path
    detected_format: Optional[CoverageFormat] = None
    parser: Optional[BaseParser] = None
    confidence: float = 0.0
    ambiguous: bool = False
    matching_parsers: List[BaseParser] = field(default_factory=list)
    error: Optional[str] = None
    
    @property
    def success(self) -> bool:
        """Check if detection succeeded"""
        return self.parser is not None and self.error is None
    
    @property
    def format_name(self) -> str:
        """Get format name as string"""
        if self.detected_format:
            return self.detected_format.value
        return "unknown"
    
    def to_dict(self) -> Dict[str, any]:
        """Convert to dictionary"""
        return {
            "file_path": str(self.file_path),
            "format": self.format_name,
            "confidence": self.confidence,
            "ambiguous": self.ambiguous,
            "success": self.success,
            "error": self.error,
        }


@dataclass
class BatchDetectionResult:
    """
    Result of batch format detection
    
    Attributes:
        total_files: Total number of files analyzed
        successful: Number of successfully detected files
        failed: Number of failed detections
        by_format: Files grouped by detected format
        ambiguous_files: Files with ambiguous format
        error_files: Files that caused errors
        results: List of individual detection results
    """
    total_files: int = 0
    successful: int = 0
    failed: int = 0
    by_format: Dict[str, List[Path]] = field(default_factory=lambda: defaultdict(list))
    ambiguous_files: List[Path] = field(default_factory=list)
    error_files: List[Path] = field(default_factory=list)
    results: List[DetectionResult] = field(default_factory=list)
    
    def add_result(self, result: DetectionResult) -> None:
        """Add a detection result"""
        self.results.append(result)
        self.total_files += 1
        
        if result.success:
            self.successful += 1
            self.by_format[result.format_name].append(result.file_path)
            
            if result.ambiguous:
                self.ambiguous_files.append(result.file_path)
        else:
            self.failed += 1
            self.error_files.append(result.file_path)
    
    def get_summary(self) -> Dict[str, any]:
        """Get summary statistics"""
        return {
            "total_files": self.total_files,
            "successful": self.successful,
            "failed": self.failed,
            "success_rate": (self.successful / self.total_files * 100) if self.total_files > 0 else 0,
            "formats_detected": list(self.by_format.keys()),
            "ambiguous_count": len(self.ambiguous_files),
        }
    
    def to_dict(self) -> Dict[str, any]:
        """Convert to dictionary"""
        return {
            "summary": self.get_summary(),
            "by_format": {
                fmt: [str(p) for p in paths]
                for fmt, paths in self.by_format.items()
            },
            "ambiguous_files": [str(p) for p in self.ambiguous_files],
            "error_files": [str(p) for p in self.error_files],
        }


# =============================================================================
# FORMAT DETECTOR
# =============================================================================

class FormatDetector:
    """
    Automatic coverage format detection
    
    The detector tries each parser in priority order and returns the first
    matching parser. It can detect:
    - Verilator .dat files
    - LCOV .info/.lcov files
    - Covered .cdd files (when implemented)
    - Other formats as parsers are added
    
    Usage:
        >>> detector = FormatDetector([verilator_parser, lcov_parser])
        >>> result = detector.detect(Path("coverage.dat"))
        >>> if result.success:
        ...     coverage = result.parser.parse_file(result.file_path)
    """
    
    def __init__(
        self,
        parsers: Optional[List[BaseParser]] = None,
        config: Optional[ParserConfig] = None
    ):
        """
        Initialize format detector
        
        Args:
            parsers: List of parser instances to try (optional)
            config: Parser configuration (optional)
        """
        self.config = config or ParserConfig()
        self.logger = logging.getLogger(__name__)
        
        # Initialize parsers if not provided
        if parsers is None:
            parsers = self._create_default_parsers()
        
        # Sort parsers by priority from config
        self.parsers = self._sort_parsers_by_priority(parsers)
        
        # Statistics
        self.detections_attempted = 0
        self.detections_successful = 0
        self.detections_failed = 0
    
    def _create_default_parsers(self) -> List[BaseParser]:
        """
        Create default set of parsers based on availability
        
        Returns:
            List of parser instances
        """
        parsers = []
        
        # Try to import and instantiate available parsers
        try:
            from .verilator_parser import VerilatorParser
            parsers.append(VerilatorParser(self.config))
        except ImportError:
            self.logger.debug("VerilatorParser not available")
        
        try:
            from .lcov_parser import LCOVParser
            parsers.append(LCOVParser(self.config))
        except ImportError:
            self.logger.debug("LCOVParser not available")
        
        try:
            from .covered_parser import CoveredParser
            parsers.append(CoveredParser(self.config))
        except ImportError:
            self.logger.debug("CoveredParser not available")
        
        if not parsers:
            self.logger.warning("No parsers available for format detection")
        
        return parsers
    
    def _sort_parsers_by_priority(self, parsers: List[BaseParser]) -> List[BaseParser]:
        """
        Sort parsers by priority from config
        
        Args:
            parsers: List of parser instances
        
        Returns:
            Sorted list of parsers
        """
        priority_map = {name: idx for idx, name in enumerate(self.config.priority)}
        
        def get_priority(parser: BaseParser) -> int:
            # Get format name and map to priority
            format_name = parser.get_format().value
            # Extract base name (e.g., "verilator_dat" -> "verilator")
            base_name = format_name.split('_')[0]
            return priority_map.get(base_name, 999)  # Unknown parsers go last
        
        return sorted(parsers, key=get_priority)
    
    # =========================================================================
    # SINGLE FILE DETECTION
    # =========================================================================
    
    def detect(self, file_path: Path) -> DetectionResult:
        """
        Detect format of a single coverage file
        
        Args:
            file_path: Path to coverage file
        
        Returns:
            DetectionResult with detected format and parser
        """
        self.detections_attempted += 1
        file_path = Path(file_path)
        
        result = DetectionResult(file_path=file_path)
        
        # Check file exists
        if not file_path.exists():
            result.error = f"File not found: {file_path}"
            self.detections_failed += 1
            return result
        
        if not file_path.is_file():
            result.error = f"Not a file: {file_path}"
            self.detections_failed += 1
            return result
        
        # Try each parser
        matching_parsers = []
        
        for parser in self.parsers:
            try:
                if parser.can_parse(file_path):
                    matching_parsers.append(parser)
                    
                    # Use first match if not checking for ambiguity
                    if not matching_parsers:
                        result.parser = parser
                        result.detected_format = parser.get_format()
            
            except Exception as e:
                self.logger.debug(f"Parser {parser.__class__.__name__} failed on {file_path}: {e}")
                continue
        
        # Analyze results
        if not matching_parsers:
            result.error = f"No parser could handle file: {file_path}"
            self.detections_failed += 1
        
        elif len(matching_parsers) == 1:
            # Single match - perfect
            result.parser = matching_parsers[0]
            result.detected_format = matching_parsers[0].get_format()
            result.confidence = 1.0
            result.matching_parsers = matching_parsers
            self.detections_successful += 1
        
        else:
            # Multiple matches - ambiguous
            result.parser = matching_parsers[0]  # Use first by priority
            result.detected_format = matching_parsers[0].get_format()
            result.confidence = 0.5
            result.ambiguous = True
            result.matching_parsers = matching_parsers
            self.detections_successful += 1
            
            self.logger.warning(
                f"Ambiguous format for {file_path}: "
                f"matched by {[p.__class__.__name__ for p in matching_parsers]}"
            )
        
        return result
    
    def detect_with_fallback(
        self,
        file_path: Path,
        fallback_format: Optional[CoverageFormat] = None
    ) -> DetectionResult:
        """
        Detect format with fallback to specified format
        
        Args:
            file_path: Path to coverage file
            fallback_format: Format to use if detection fails
        
        Returns:
            DetectionResult
        """
        result = self.detect(file_path)
        
        if not result.success and fallback_format:
            # Find parser for fallback format
            for parser in self.parsers:
                if parser.get_format() == fallback_format:
                    result.parser = parser
                    result.detected_format = fallback_format
                    result.confidence = 0.3  # Low confidence
                    result.error = None
                    break
        
        return result
    
    # =========================================================================
    # BATCH DETECTION
    # =========================================================================
    
    def detect_batch(self, file_paths: List[Path]) -> BatchDetectionResult:
        """
        Detect formats for multiple files
        
        Args:
            file_paths: List of paths to coverage files
        
        Returns:
            BatchDetectionResult with all detection results
        """
        batch_result = BatchDetectionResult()
        
        for file_path in file_paths:
            result = self.detect(file_path)
            batch_result.add_result(result)
        
        return batch_result
    
    def detect_directory(
        self,
        directory: Path,
        recursive: bool = True,
        patterns: Optional[List[str]] = None
    ) -> BatchDetectionResult:
        """
        Detect coverage files in a directory
        
        Args:
            directory: Directory to search
            recursive: Search recursively
            patterns: File patterns to match (e.g., ["*.dat", "*.info"])
        
        Returns:
            BatchDetectionResult
        """
        directory = Path(directory)
        
        if not directory.exists():
            self.logger.error(f"Directory not found: {directory}")
            return BatchDetectionResult()
        
        # Default patterns for coverage files
        if patterns is None:
            patterns = [
                "*.dat",      # Verilator
                "*.info",     # LCOV
                "*.lcov",     # LCOV
                "*.cdd",      # Covered
                "coverage*",  # Generic
            ]
        
        # Find files
        files = []
        
        if recursive:
            for pattern in patterns:
                files.extend(directory.rglob(pattern))
        else:
            for pattern in patterns:
                files.extend(directory.glob(pattern))
        
        # Remove duplicates
        files = list(set(files))
        
        self.logger.info(f"Found {len(files)} potential coverage files in {directory}")
        
        # Detect formats
        return self.detect_batch(files)
    
    # =========================================================================
    # GROUPING AND FILTERING
    # =========================================================================
    
    def group_by_format(
        self,
        file_paths: List[Path]
    ) -> Dict[CoverageFormat, List[Path]]:
        """
        Group files by detected format
        
        Args:
            file_paths: List of file paths
        
        Returns:
            Dictionary mapping format to list of files
        """
        grouped: Dict[CoverageFormat, List[Path]] = defaultdict(list)
        
        for file_path in file_paths:
            result = self.detect(file_path)
            if result.success and result.detected_format:
                grouped[result.detected_format].append(file_path)
        
        return dict(grouped)
    
    def filter_by_format(
        self,
        file_paths: List[Path],
        target_format: CoverageFormat
    ) -> List[Path]:
        """
        Filter files by specific format
        
        Args:
            file_paths: List of file paths
            target_format: Format to filter for
        
        Returns:
            List of files matching the format
        """
        matching_files = []
        
        for file_path in file_paths:
            result = self.detect(file_path)
            if result.success and result.detected_format == target_format:
                matching_files.append(file_path)
        
        return matching_files
    
    # =========================================================================
    # PARSER ACCESS
    # =========================================================================
    
    def get_parser_for_format(self, format: CoverageFormat) -> Optional[BaseParser]:
        """
        Get parser instance for specific format
        
        Args:
            format: Coverage format
        
        Returns:
            Parser instance, or None if not available
        """
        for parser in self.parsers:
            if parser.get_format() == format:
                return parser
        return None
    
    def get_available_formats(self) -> List[CoverageFormat]:
        """
        Get list of available coverage formats
        
        Returns:
            List of supported formats
        """
        return [parser.get_format() for parser in self.parsers]
    
    def has_parser_for(self, format: CoverageFormat) -> bool:
        """
        Check if parser is available for format
        
        Args:
            format: Coverage format
        
        Returns:
            True if parser is available
        """
        return self.get_parser_for_format(format) is not None
    
    # =========================================================================
    # STATISTICS
    # =========================================================================
    
    def get_statistics(self) -> Dict[str, any]:
        """
        Get detection statistics
        
        Returns:
            Dictionary with statistics
        """
        return {
            "detections_attempted": self.detections_attempted,
            "detections_successful": self.detections_successful,
            "detections_failed": self.detections_failed,
            "success_rate": (
                self.detections_successful / self.detections_attempted * 100
                if self.detections_attempted > 0 else 0
            ),
            "available_parsers": len(self.parsers),
            "available_formats": [f.value for f in self.get_available_formats()],
        }
    
    def reset_statistics(self) -> None:
        """Reset detection statistics"""
        self.detections_attempted = 0
        self.detections_successful = 0
        self.detections_failed = 0
    
    # =========================================================================
    # DIAGNOSTICS
    # =========================================================================
    
    def diagnose_file(self, file_path: Path) -> Dict[str, any]:
        """
        Get detailed diagnostic information for a file
        
        Args:
            file_path: Path to file
        
        Returns:
            Dictionary with diagnostic information
        """
        file_path = Path(file_path)
        
        diagnostics = {
            "file_path": str(file_path),
            "exists": file_path.exists(),
            "is_file": file_path.is_file() if file_path.exists() else False,
            "size_bytes": file_path.stat().st_size if file_path.exists() else 0,
            "extension": file_path.suffix,
            "parsers_tested": [],
        }
        
        if not file_path.exists():
            return diagnostics
        
        # Test each parser
        for parser in self.parsers:
            parser_info = {
                "parser_class": parser.__class__.__name__,
                "format": parser.get_format().value,
                "can_parse": False,
                "error": None,
            }
            
            try:
                parser_info["can_parse"] = parser.can_parse(file_path)
            except Exception as e:
                parser_info["error"] = str(e)
            
            diagnostics["parsers_tested"].append(parser_info)
        
        return diagnostics
    
    def __repr__(self) -> str:
        """String representation"""
        return (
            f"FormatDetector("
            f"parsers={len(self.parsers)}, "
            f"formats={[p.get_format().value for p in self.parsers]}"
            f")"
        )


# =============================================================================
# CONVENIENCE FUNCTIONS
# =============================================================================

def create_detector(
    parsers: Optional[List[BaseParser]] = None,
    config: Optional[ParserConfig] = None
) -> FormatDetector:
    """
    Create a FormatDetector with default parsers
    
    Args:
        parsers: Custom parser list (optional)
        config: Parser configuration (optional)
    
    Returns:
        FormatDetector instance
    """
    return FormatDetector(parsers, config)


def detect_format(file_path: Path) -> Optional[CoverageFormat]:
    """
    Quick format detection for a single file
    
    Args:
        file_path: Path to coverage file
    
    Returns:
        Detected format, or None if unknown
    """
    detector = create_detector()
    result = detector.detect(file_path)
    return result.detected_format


def detect_and_parse(file_path: Path) -> Optional[any]:
    """
    Detect format and parse file in one step
    
    Args:
        file_path: Path to coverage file
    
    Returns:
        ParseResult from appropriate parser, or None if detection failed
    """
    detector = create_detector()
    result = detector.detect(file_path)
    
    if result.success and result.parser:
        return result.parser.parse_file(file_path)
    
    return None


def group_coverage_files(
    file_paths: List[Path]
) -> Dict[CoverageFormat, List[Path]]:
    """
    Group coverage files by format
    
    Args:
        file_paths: List of file paths
    
    Returns:
        Dictionary mapping format to file list
    """
    detector = create_detector()
    return detector.group_by_format(file_paths)
