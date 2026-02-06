"""
Abstract base parser for coverage file formats

This module defines the interface that all coverage parsers must implement.
Parsers handle format detection, parsing, and merging of coverage files.

Design Philosophy:
- Q12 Option C: Try external tools first, fallback to Python parsing
- Robust error handling and validation
- Support for both single-file and multi-file merging (Q6.2)
- Track parse errors/warnings for diagnostics

Author: TB Eval Team
Version: 0.1.0
"""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Optional, List, Dict, Any, Set, Tuple
from dataclasses import dataclass, field
import subprocess
import logging

# Import models
from ..models import (
    ModuleCoverage,
    FileCoverage,
    CoverageFormat,
    LineCoverageData,
    BranchData,
    ToggleData,
)
from ..config import ParserConfig


# =============================================================================
# PARSER RESULT
# =============================================================================

@dataclass
class ParseResult:
    """
    Result of a coverage file parse operation
    
    Attributes:
        success: Whether parsing succeeded
        coverage: Parsed coverage data (None if failed)
        errors: List of error messages
        warnings: List of warning messages
        metadata: Additional metadata about the parse
        used_external_tool: Whether an external tool was used
        parse_time_ms: Time taken to parse (milliseconds)
    """
    success: bool
    coverage: Optional[ModuleCoverage] = None
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    used_external_tool: bool = False
    parse_time_ms: float = 0.0
    
    def add_error(self, message: str) -> None:
        """Add an error message"""
        self.errors.append(message)
        self.success = False
    
    def add_warning(self, message: str) -> None:
        """Add a warning message"""
        self.warnings.append(message)
    
    @property
    def has_warnings(self) -> bool:
        """Check if there are warnings"""
        return len(self.warnings) > 0
    
    @property
    def has_errors(self) -> bool:
        """Check if there are errors"""
        return len(self.errors) > 0


@dataclass
class MergeResult:
    """
    Result of a coverage file merge operation
    
    Attributes:
        success: Whether merging succeeded
        merged_coverage: Merged coverage data (None if failed)
        merged_file_path: Path to merged file (if created physically)
        errors: List of error messages
        warnings: List of warning messages
        used_external_tool: Whether an external tool was used
        merge_time_ms: Time taken to merge (milliseconds)
    """
    success: bool
    merged_coverage: Optional[ModuleCoverage] = None
    merged_file_path: Optional[Path] = None
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    used_external_tool: bool = False
    merge_time_ms: float = 0.0
    
    def add_error(self, message: str) -> None:
        """Add an error message"""
        self.errors.append(message)
        self.success = False
    
    def add_warning(self, message: str) -> None:
        """Add a warning message"""
        self.warnings.append(message)


# =============================================================================
# ABSTRACT BASE PARSER
# =============================================================================

class BaseParser(ABC):
    """
    Abstract base class for coverage parsers
    
    All coverage format parsers must inherit from this class and implement:
    - can_parse(): Check if parser can handle a file
    - parse_file(): Parse a single coverage file
    - merge_coverage(): Merge multiple coverage files
    - get_format(): Return the coverage format
    
    The parser follows Q12 Option C:
    1. Try external tool (if available and enabled)
    2. Fall back to Python parsing (if enabled)
    
    Attributes:
        config: Parser configuration
        logger: Logger instance
        errors: List of accumulated errors
        warnings: List of accumulated warnings
    """
    
    def __init__(self, config: Optional[ParserConfig] = None):
        """
        Initialize parser
        
        Args:
            config: Parser configuration (uses defaults if None)
        """
        self.config = config or ParserConfig()
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        self.errors: List[str] = []
        self.warnings: List[str] = []
    
    # =========================================================================
    # ABSTRACT METHODS (must be implemented by subclasses)
    # =========================================================================
    
    @abstractmethod
    def can_parse(self, file_path: Path) -> bool:
        """
        Check if this parser can handle the given file
        
        This should be a fast check (e.g., file extension, magic bytes)
        without fully parsing the file.
        
        Args:
            file_path: Path to coverage file
        
        Returns:
            True if parser can handle this file format
        """
        pass
    
    @abstractmethod
    def get_format(self) -> CoverageFormat:
        """
        Get the coverage format this parser handles
        
        Returns:
            CoverageFormat enum value
        """
        pass
    
    @abstractmethod
    def _parse_with_python(self, file_path: Path) -> ParseResult:
        """
        Parse coverage file using pure Python implementation
        
        This is the fallback method when external tools are unavailable
        or when use_external_tools is False.
        
        Args:
            file_path: Path to coverage file
        
        Returns:
            ParseResult with coverage data
        """
        pass
    
    @abstractmethod
    def _get_external_tool_path(self) -> Optional[Path]:
        """
        Get path to external coverage tool (if available)
        
        Should check:
        1. Config-specified path
        2. System PATH
        
        Returns:
            Path to tool, or None if not found
        """
        pass
    
    # =========================================================================
    # OPTIONAL METHODS (can be overridden for tool-specific implementation)
    # =========================================================================
    
    def _parse_with_tool(self, file_path: Path) -> Optional[ParseResult]:
        """
        Parse coverage file using external tool (Q12 - preferred method)
        
        Default implementation returns None (no tool support).
        Subclasses should override to implement tool-based parsing.
        
        Args:
            file_path: Path to coverage file
        
        Returns:
            ParseResult if successful, None if tool unavailable/failed
        """
        return None
    
    def _merge_with_tool(self, coverage_files: List[Path]) -> Optional[MergeResult]:
        """
        Merge coverage files using external tool (Q6.2 - preferred method)
        
        Default implementation returns None (no tool support).
        Subclasses should override to implement tool-based merging.
        
        Args:
            coverage_files: List of coverage files to merge
        
        Returns:
            MergeResult if successful, None if tool unavailable/failed
        """
        return None
    
    def _merge_with_python(self, coverage_files: List[Path]) -> MergeResult:
        """
        Merge coverage files using Python implementation (Q6.2 - fallback)
        
        Default implementation: parse each file and merge ModuleCoverage objects.
        Subclasses can override for format-specific optimizations.
        
        Args:
            coverage_files: List of coverage files to merge
        
        Returns:
            MergeResult with merged coverage data
        """
        import time
        start_time = time.time()
        
        result = MergeResult(success=True)
        merged: Optional[ModuleCoverage] = None
        
        for file_path in coverage_files:
            # Parse individual file
            parse_result = self.parse_file(file_path)
            
            if not parse_result.success:
                result.add_error(f"Failed to parse {file_path}: {parse_result.errors}")
                continue
            
            if parse_result.coverage is None:
                result.add_warning(f"No coverage data in {file_path}")
                continue
            
            # Merge with accumulated data
            if merged is None:
                merged = parse_result.coverage
            else:
                merged.merge(parse_result.coverage)
        
        if merged is None:
            result.add_error("No coverage data to merge")
            return result
        
        result.merged_coverage = merged
        result.merge_time_ms = (time.time() - start_time) * 1000.0
        result.success = True
        
        return result
    
    # =========================================================================
    # PUBLIC API METHODS
    # =========================================================================
    
    def parse_file(self, file_path: Path) -> ParseResult:
        """
        Parse a single coverage file (Q12 Option C implementation)
        
        Strategy:
        1. Validate file
        2. Try external tool (if enabled and available)
        3. Fall back to Python parsing (if enabled)
        
        Args:
            file_path: Path to coverage file
        
        Returns:
            ParseResult with coverage data
        """
        import time
        start_time = time.time()
        
        self.reset_errors()
        
        # Validate file
        if not self.validate_file(file_path):
            result = ParseResult(success=False)
            result.errors = self.errors.copy()
            result.warnings = self.warnings.copy()
            return result
        
        # Q12 Option C: Try external tool first
        if self.config.use_external_tools:
            tool_path = self._get_external_tool_path()
            if tool_path is not None:
                self.logger.debug(f"Attempting to parse {file_path} with external tool")
                tool_result = self._parse_with_tool(file_path)
                
                if tool_result is not None and tool_result.success:
                    tool_result.parse_time_ms = (time.time() - start_time) * 1000.0
                    tool_result.used_external_tool = True
                    return tool_result
                
                # Tool failed
                if not self.config.fallback_to_python:
                    result = ParseResult(success=False)
                    result.add_error("External tool failed and fallback disabled")
                    if tool_result:
                        result.errors.extend(tool_result.errors)
                    return result
                
                self.logger.debug("External tool failed, falling back to Python parser")
                if tool_result and tool_result.has_warnings:
                    self.warnings.extend(tool_result.warnings)
        
        # Python parsing (fallback or primary)
        self.logger.debug(f"Parsing {file_path} with Python parser")
        result = self._parse_with_python(file_path)
        result.parse_time_ms = (time.time() - start_time) * 1000.0
        result.used_external_tool = False
        
        return result
    
    def merge_coverage(self, coverage_files: List[Path]) -> MergeResult:
        """
        Merge multiple coverage files (Q6.2 implementation)
        
        Strategy:
        1. Try external tool for merging (faster)
        2. Fall back to Python merging (parse + merge objects)
        
        Args:
            coverage_files: List of coverage files to merge
        
        Returns:
            MergeResult with merged coverage data
        """
        import time
        start_time = time.time()
        
        if not coverage_files:
            result = MergeResult(success=False)
            result.add_error("No coverage files to merge")
            return result
        
        # Single file - just parse it
        if len(coverage_files) == 1:
            parse_result = self.parse_file(coverage_files[0])
            result = MergeResult(
                success=parse_result.success,
                merged_coverage=parse_result.coverage,
                errors=parse_result.errors,
                warnings=parse_result.warnings,
            )
            result.merge_time_ms = (time.time() - start_time) * 1000.0
            return result
        
        # Q12 Option C: Try external tool first (Q6.2 - tool_preferred)
        if self.config.use_external_tools and self.config.strategy == "tool_preferred":
            tool_path = self._get_external_tool_path()
            if tool_path is not None:
                self.logger.debug(f"Attempting to merge {len(coverage_files)} files with external tool")
                tool_result = self._merge_with_tool(coverage_files)
                
                if tool_result is not None and tool_result.success:
                    tool_result.merge_time_ms = (time.time() - start_time) * 1000.0
                    tool_result.used_external_tool = True
                    return tool_result
                
                # Tool failed
                if not self.config.fallback_to_python:
                    result = MergeResult(success=False)
                    result.add_error("External tool merge failed and fallback disabled")
                    if tool_result:
                        result.errors.extend(tool_result.errors)
                    return result
                
                self.logger.debug("External tool merge failed, falling back to Python merge")
        
        # Python merging (fallback or primary)
        self.logger.debug(f"Merging {len(coverage_files)} files with Python")
        result = self._merge_with_python(coverage_files)
        result.merge_time_ms = (time.time() - start_time) * 1000.0
        result.used_external_tool = False
        
        return result
    
    # =========================================================================
    # VALIDATION METHODS
    # =========================================================================
    
    def validate_file(self, file_path: Path) -> bool:
        """
        Validate coverage file integrity
        
        Checks:
        - File exists
        - File is not empty
        - File has correct format (via can_parse)
        
        Args:
            file_path: Path to coverage file
        
        Returns:
            True if file is valid
        """
        file_path = Path(file_path)
        
        # Check existence
        if not file_path.exists():
            self.errors.append(f"File not found: {file_path}")
            return False
        
        if not file_path.is_file():
            self.errors.append(f"Not a file: {file_path}")
            return False
        
        # Check size
        if file_path.stat().st_size == 0:
            self.errors.append(f"File is empty: {file_path}")
            return False
        
        # Check readable
        try:
            with open(file_path, 'rb') as f:
                f.read(1)
        except PermissionError:
            self.errors.append(f"Permission denied: {file_path}")
            return False
        except Exception as e:
            self.errors.append(f"Cannot read file {file_path}: {e}")
            return False
        
        # Check format
        if not self.can_parse(file_path):
            self.errors.append(f"File format not supported by {self.__class__.__name__}: {file_path}")
            return False
        
        return True
    
    def validate_files(self, file_paths: List[Path]) -> Tuple[List[Path], List[Path]]:
        """
        Validate multiple coverage files
        
        Args:
            file_paths: List of file paths to validate
        
        Returns:
            Tuple of (valid_files, invalid_files)
        """
        valid_files = []
        invalid_files = []
        
        for file_path in file_paths:
            self.reset_errors()
            if self.validate_file(file_path):
                valid_files.append(file_path)
            else:
                invalid_files.append(file_path)
                if self.config.skip_invalid_files:
                    self.warnings.append(f"Skipping invalid file: {file_path}")
        
        return valid_files, invalid_files
    
    # =========================================================================
    # UTILITY METHODS
    # =========================================================================
    
    def reset_errors(self) -> None:
        """Clear accumulated errors and warnings"""
        self.errors = []
        self.warnings = []
    
    def run_external_tool(
        self,
        command: List[str],
        timeout: int = 60,
        check: bool = False
    ) -> subprocess.CompletedProcess:
        """
        Run an external tool command
        
        Helper method for subclasses to run external tools safely.
        
        Args:
            command: Command and arguments to run
            timeout: Timeout in seconds
            check: Whether to raise exception on non-zero exit
        
        Returns:
            subprocess.CompletedProcess result
        
        Raises:
            subprocess.TimeoutExpired: If command times out
            subprocess.CalledProcessError: If check=True and command fails
        """
        self.logger.debug(f"Running command: {' '.join(str(c) for c in command)}")
        
        try:
            result = subprocess.run(
                command,
                capture_output=True,
                text=True,
                timeout=timeout,
                check=check
            )
            
            if result.returncode != 0:
                self.logger.debug(f"Command failed with code {result.returncode}")
                self.logger.debug(f"stderr: {result.stderr}")
            
            return result
        
        except subprocess.TimeoutExpired as e:
            self.errors.append(f"Command timed out after {timeout}s: {' '.join(command)}")
            raise
        
        except subprocess.CalledProcessError as e:
            self.errors.append(f"Command failed: {e}")
            raise
    
    def find_tool_in_path(self, tool_name: str) -> Optional[Path]:
        """
        Find a tool in the system PATH
        
        Args:
            tool_name: Name of the tool executable
        
        Returns:
            Path to tool if found, None otherwise
        """
        import shutil
        
        tool_path = shutil.which(tool_name)
        if tool_path:
            return Path(tool_path)
        
        return None
    
    # =========================================================================
    # HELPER METHODS FOR SUBCLASSES
    # =========================================================================
    
    def read_file_lines(self, file_path: Path) -> List[str]:
        """
        Read all lines from a file
        
        Helper method for text-based parsers.
        
        Args:
            file_path: Path to file
        
        Returns:
            List of lines (without newlines)
        """
        try:
            with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
                return [line.rstrip('\n\r') for line in f]
        except Exception as e:
            self.errors.append(f"Failed to read {file_path}: {e}")
            return []
    
    def check_file_magic(self, file_path: Path, magic_bytes: bytes) -> bool:
        """
        Check if file starts with magic bytes
        
        Helper method for binary format detection.
        
        Args:
            file_path: Path to file
            magic_bytes: Expected magic bytes at start of file
        
        Returns:
            True if file starts with magic bytes
        """
        try:
            with open(file_path, 'rb') as f:
                header = f.read(len(magic_bytes))
                return header == magic_bytes
        except:
            return False
    
    def check_file_contains(self, file_path: Path, search_strings: List[str]) -> bool:
        """
        Check if file contains any of the search strings
        
        Helper method for text-based format detection.
        
        Args:
            file_path: Path to file
            search_strings: Strings to search for
        
        Returns:
            True if any search string is found
        """
        try:
            with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
                # Read first few KB for detection
                content = f.read(4096)
                return any(s in content for s in search_strings)
        except:
            return False
    
    # =========================================================================
    # DEBUGGING & DIAGNOSTICS
    # =========================================================================
    
    def get_diagnostics(self) -> Dict[str, Any]:
        """
        Get diagnostic information about parser state
        
        Useful for debugging parser issues.
        
        Returns:
            Dictionary with diagnostic information
        """
        tool_path = self._get_external_tool_path()
        
        return {
            "parser_class": self.__class__.__name__,
            "format": self.get_format().value,
            "external_tool_available": tool_path is not None,
            "external_tool_path": str(tool_path) if tool_path else None,
            "use_external_tools": self.config.use_external_tools,
            "fallback_to_python": self.config.fallback_to_python,
            "errors": self.errors,
            "warnings": self.warnings,
        }
    
    def __repr__(self) -> str:
        """String representation"""
        return f"{self.__class__.__name__}(format={self.get_format().value})"
