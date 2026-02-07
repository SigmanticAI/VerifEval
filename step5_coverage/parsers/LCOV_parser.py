"""
LCOV coverage parser

Parses LCOV tracefile format (.info/.lcov files).

LCOV Format:
- Standard code coverage tracefile format
- Used by lcov/gcov tools
- Text-based with colon-separated records
- Widely supported by coverage tools

Record Types:
- TN:    Test name
- SF:    Source file
- FN:    Function name (line, name)
- FNDA:  Function data (execution count, name)
- DA:    Line data (line, hits[, checksum])
- BRDA:  Branch data (line, block, branch, taken)
- LF/LH: Lines found/hit
- FNF/FNH: Functions found/hit
- BRF/BRH: Branches found/hit

External Tools:
- lcov: Coverage data manipulation
- genhtml: HTML report generation

Implementation Strategy (Q12 Option C):
1. Try lcov --add-tracefile for merging (preferred)
2. Fall back to Python parsing and merging

Author: TB Eval Team
Version: 0.1.0
"""

import re
import tempfile
from pathlib import Path
from typing import Optional, List, Dict, Set, Tuple
from dataclasses import dataclass, field

from .base import BaseParser, ParseResult, MergeResult
from ..models import (
    CoverageFormat,
    ModuleCoverage,
    FileCoverage,
    LineCoverageData,
    BranchData,
    ToggleData,
)
from ..config import ParserConfig


# =============================================================================
# LCOV FORMAT CONSTANTS
# =============================================================================

# LCOV file extensions
LCOV_EXTENSIONS = ['.info', '.lcov']

# LCOV record type markers
LCOV_MARKERS = [
    'TN:', 'SF:', 'FN:', 'FNDA:', 'FNF:', 'FNH:',
    'DA:', 'LF:', 'LH:',
    'BRDA:', 'BRF:', 'BRH:',
    'end_of_record'
]

# LCOV record types
@dataclass
class LCOVRecordType:
    """LCOV record type definitions"""
    TEST_NAME = 'TN'
    SOURCE_FILE = 'SF'
    FUNCTION_NAME = 'FN'
    FUNCTION_DATA = 'FNDA'
    FUNCTIONS_FOUND = 'FNF'
    FUNCTIONS_HIT = 'FNH'
    LINE_DATA = 'DA'
    LINES_FOUND = 'LF'
    LINES_HIT = 'LH'
    BRANCH_DATA = 'BRDA'
    BRANCHES_FOUND = 'BRF'
    BRANCHES_HIT = 'BRH'
    END_OF_RECORD = 'end_of_record'


# =============================================================================
# LCOV PARSER
# =============================================================================

class LCOVParser(BaseParser):
    """
    Parser for LCOV tracefile format (Q11 - priority #2)
    
    LCOV is a standard coverage format used by:
    - gcov/lcov (GNU coverage tools)
    - Verilator (can export to LCOV)
    - Many other coverage tools
    
    Format Specification:
        http://ltp.sourceforge.net/coverage/lcov/geninfo.1.php
    
    Example:
        TN:test_name
        SF:/path/to/source.c
        FN:10,function_name
        FNDA:5,function_name
        FNF:1
        FNH:1
        DA:10,5
        DA:11,3
        DA:12,0
        LF:3
        LH:2
        BRDA:11,0,0,2
        BRDA:11,0,1,1
        BRF:2
        BRH:2
        end_of_record
    
    External Tools:
    - lcov: Coverage manipulation (merge, filter, etc.)
    - genhtml: Generate HTML reports
    """
    
    def __init__(self, config: Optional[ParserConfig] = None):
        """Initialize LCOV parser"""
        super().__init__(config)
        self._lcov_tool: Optional[Path] = None
        self._genhtml_tool: Optional[Path] = None
        self._tool_checked = False
    
    # =========================================================================
    # ABSTRACT METHOD IMPLEMENTATIONS
    # =========================================================================
    
    def can_parse(self, file_path: Path) -> bool:
        """
        Check if file is LCOV format
        
        Detection strategy:
        1. Check file extension (.info, .lcov)
        2. Check for LCOV record markers in content
        
        Args:
            file_path: Path to coverage file
        
        Returns:
            True if file appears to be LCOV format
        """
        file_path = Path(file_path)
        
        # Check extension
        if file_path.suffix.lower() not in LCOV_EXTENSIONS:
            return False
        
        # Check for LCOV markers in content
        if self.check_file_contains(file_path, LCOV_MARKERS):
            return True
        
        return False
    
    def get_format(self) -> CoverageFormat:
        """Return LCOV format identifier"""
        return CoverageFormat.LCOV_INFO
    
    def _get_external_tool_path(self) -> Optional[Path]:
        """
        Find lcov tool
        
        Checks:
        1. Config-specified path
        2. System PATH
        
        Returns:
            Path to lcov tool, or None if not found
        """
        if self._tool_checked:
            return self._lcov_tool
        
        self._tool_checked = True
        
        # Check config
        if self.config.lcov_tool_path:
            tool_path = Path(self.config.lcov_tool_path)
            if tool_path.exists():
                self._lcov_tool = tool_path
                self._genhtml_tool = self.find_tool_in_path("genhtml")
                return self._lcov_tool
        
        # Check system PATH
        self._lcov_tool = self.find_tool_in_path("lcov")
        if self._lcov_tool:
            self._genhtml_tool = self.find_tool_in_path("genhtml")
            self.logger.info(f"Found lcov: {self._lcov_tool}")
        else:
            self.logger.debug("lcov tool not found")
        
        return self._lcov_tool
    
    # =========================================================================
    # TOOL-BASED PARSING (Q12 - preferred method)
    # =========================================================================
    
    def _parse_with_tool(self, file_path: Path) -> Optional[ParseResult]:
        """
        Parse using lcov tool
        
        For LCOV files, the tool doesn't add much value for parsing
        (it's already in the right format), but we can use it for
        validation and filtering.
        
        Args:
            file_path: Path to LCOV file
        
        Returns:
            ParseResult if successful, None if tool unavailable/failed
        """
        tool_path = self._get_external_tool_path()
        if not tool_path:
            return None
        
        self.logger.debug(f"Validating {file_path} with lcov tool")
        
        # Use lcov to validate the file
        # lcov --summary will parse and summarize the file
        try:
            result = self.run_external_tool(
                [
                    str(tool_path),
                    '--summary', str(file_path)
                ],
                timeout=30
            )
            
            if result.returncode != 0:
                self.logger.debug(f"lcov validation failed: {result.stderr}")
                return None
            
            # File is valid, parse it with Python
            # (lcov tool doesn't output in a different format, 
            # so we still use Python parsing)
            return None  # Fall back to Python parsing
        
        except Exception as e:
            self.logger.debug(f"Tool-based validation failed: {e}")
            return None
    
    # =========================================================================
    # PYTHON-BASED PARSING (Q12 - main method for LCOV)
    # =========================================================================
    
    def _parse_with_python(self, file_path: Path) -> ParseResult:
        """
        Parse LCOV file using pure Python
        
        LCOV format is text-based and straightforward to parse.
        
        Args:
            file_path: Path to LCOV file
        
        Returns:
            ParseResult with parsed coverage
        """
        self.logger.debug(f"Parsing {file_path} with Python parser")
        
        result = ParseResult(success=True)
        
        try:
            module = ModuleCoverage(module_name="lcov_coverage")
            
            # Read file
            lines = self.read_file_lines(file_path)
            if not lines:
                result.add_error("Failed to read file or file is empty")
                return result
            
            current_file: Optional[FileCoverage] = None
            current_file_path: Optional[str] = None
            test_names: List[str] = []
            
            # Validation counters
            expected_lines_found: Optional[int] = None
            expected_lines_hit: Optional[int] = None
            expected_branches_found: Optional[int] = None
            expected_branches_hit: Optional[int] = None
            
            for line_num, line in enumerate(lines, 1):
                line = line.strip()
                
                # Skip empty lines and comments
                if not line or line.startswith('#'):
                    continue
                
                # Check for colon separator
                if ':' not in line:
                    continue
                
                # Split into record type and data
                try:
                    record_type, record_data = line.split(':', 1)
                except ValueError:
                    result.add_warning(f"Malformed record at line {line_num}: {line}")
                    continue
                
                # Test Name: TN:<name>
                if record_type == LCOVRecordType.TEST_NAME:
                    test_name = record_data or "unknown_test"
                    test_names.append(test_name)
                    # Use first test name as module name
                    if module.module_name == "lcov_coverage" and test_name:
                        module.module_name = test_name
                
                # Source File: SF:<path>
                elif record_type == LCOVRecordType.SOURCE_FILE:
                    current_file_path = record_data
                    current_file = FileCoverage(file_path=current_file_path)
                    module.files[current_file_path] = current_file
                    if current_file_path not in module.source_files:
                        module.source_files.append(current_file_path)
                    
                    # Reset validation counters for new file
                    expected_lines_found = None
                    expected_lines_hit = None
                    expected_branches_found = None
                    expected_branches_hit = None
                
                # Function Name: FN:<line>,<name>
                elif record_type == LCOVRecordType.FUNCTION_NAME:
                    # Store function info (Phase 2 - functional coverage)
                    pass
                
                # Function Data: FNDA:<count>,<name>
                elif record_type == LCOVRecordType.FUNCTION_DATA:
                    # Store function coverage (Phase 2)
                    pass
                
                # Functions Found: FNF:<count>
                elif record_type == LCOVRecordType.FUNCTIONS_FOUND:
                    # Store for validation (Phase 2)
                    pass
                
                # Functions Hit: FNH:<count>
                elif record_type == LCOVRecordType.FUNCTIONS_HIT:
                    # Store for validation (Phase 2)
                    pass
                
                # Line Data: DA:<line>,<hits>[,<checksum>]
                elif record_type == LCOVRecordType.LINE_DATA and current_file:
                    data_parts = record_data.split(',')
                    if len(data_parts) >= 2:
                        try:
                            line_no = int(data_parts[0])
                            hits = int(data_parts[1])
                            # Optional checksum in data_parts[2] (ignored for now)
                            
                            current_file.lines[line_no] = LineCoverageData(
                                line_number=line_no,
                                hit_count=hits
                            )
                        except ValueError:
                            result.add_warning(f"Invalid DA record at line {line_num}: {line}")
                    else:
                        result.add_warning(f"Incomplete DA record at line {line_num}: {line}")
                
                # Lines Found: LF:<count>
                elif record_type == LCOVRecordType.LINES_FOUND:
                    try:
                        expected_lines_found = int(record_data)
                    except ValueError:
                        result.add_warning(f"Invalid LF value at line {line_num}: {record_data}")
                
                # Lines Hit: LH:<count>
                elif record_type == LCOVRecordType.LINES_HIT:
                    try:
                        expected_lines_hit = int(record_data)
                    except ValueError:
                        result.add_warning(f"Invalid LH value at line {line_num}: {record_data}")
                
                # Branch Data: BRDA:<line>,<block>,<branch>,<taken>
                elif record_type == LCOVRecordType.BRANCH_DATA and current_file:
                    data_parts = record_data.split(',')
                    if len(data_parts) >= 4:
                        try:
                            line_no = int(data_parts[0])
                            block = int(data_parts[1])
                            branch = int(data_parts[2])
                            # Handle '-' for not executed branches
                            taken_str = data_parts[3]
                            taken = int(taken_str) if taken_str != '-' else 0
                            
                            current_file.branches.append(BranchData(
                                line_number=line_no,
                                block_number=block,
                                branch_number=branch,
                                taken_count=taken,
                                not_taken_count=0  # LCOV doesn't track separately
                            ))
                        except ValueError:
                            result.add_warning(f"Invalid BRDA record at line {line_num}: {line}")
                    else:
                        result.add_warning(f"Incomplete BRDA record at line {line_num}: {line}")
                
                # Branches Found: BRF:<count>
                elif record_type == LCOVRecordType.BRANCHES_FOUND:
                    try:
                        expected_branches_found = int(record_data)
                    except ValueError:
                        result.add_warning(f"Invalid BRF value at line {line_num}: {record_data}")
                
                # Branches Hit: BRH:<count>
                elif record_type == LCOVRecordType.BRANCHES_HIT:
                    try:
                        expected_branches_hit = int(record_data)
                    except ValueError:
                        result.add_warning(f"Invalid BRH value at line {line_num}: {record_data}")
                
                # End of record
                elif record_type == LCOVRecordType.END_OF_RECORD:
                    # Validate counts for current file
                    if current_file:
                        self._validate_file_counts(
                            current_file,
                            expected_lines_found,
                            expected_lines_hit,
                            expected_branches_found,
                            expected_branches_hit,
                            result
                        )
                    
                    current_file = None
                    current_file_path = None
                
                # Unknown record type
                else:
                    self.logger.debug(f"Unknown record type at line {line_num}: {record_type}")
            
            # Validate we got some data
            if not module.files:
                result.add_error("No coverage data found in LCOV file")
                return result
            
            # Check if we have actual coverage data
            has_data = False
            for file_cov in module.files.values():
                if file_cov.lines or file_cov.branches:
                    has_data = True
                    break
            
            if not has_data:
                result.add_error("LCOV file contains source files but no coverage data")
                return result
            
            # Store test names in metadata
            result.metadata['test_names'] = test_names
            result.metadata['files_parsed'] = len(module.files)
            
            result.coverage = module
            result.success = True
        
        except Exception as e:
            result.add_error(f"Python parsing failed: {e}")
            import traceback
            self.logger.debug(f"Parse exception: {traceback.format_exc()}")
        
        return result
    
    def _validate_file_counts(
        self,
        file_cov: FileCoverage,
        expected_lines_found: Optional[int],
        expected_lines_hit: Optional[int],
        expected_branches_found: Optional[int],
        expected_branches_hit: Optional[int],
        result: ParseResult
    ) -> None:
        """
        Validate file coverage counts against expected values
        
        Args:
            file_cov: File coverage to validate
            expected_lines_found: Expected LF value
            expected_lines_hit: Expected LH value
            expected_branches_found: Expected BRF value
            expected_branches_hit: Expected BRH value
            result: ParseResult to add warnings to
        """
        # Validate line counts
        if expected_lines_found is not None:
            actual_lines_found = len(file_cov.lines)
            if actual_lines_found != expected_lines_found:
                result.add_warning(
                    f"Line count mismatch in {file_cov.file_path}: "
                    f"expected {expected_lines_found}, found {actual_lines_found}"
                )
        
        if expected_lines_hit is not None:
            actual_lines_hit = sum(1 for line in file_cov.lines.values() if line.is_covered)
            if actual_lines_hit != expected_lines_hit:
                result.add_warning(
                    f"Line hit count mismatch in {file_cov.file_path}: "
                    f"expected {expected_lines_hit}, found {actual_lines_hit}"
                )
        
        # Validate branch counts
        if expected_branches_found is not None:
            actual_branches_found = len(file_cov.branches)
            if actual_branches_found != expected_branches_found:
                result.add_warning(
                    f"Branch count mismatch in {file_cov.file_path}: "
                    f"expected {expected_branches_found}, found {actual_branches_found}"
                )
        
        if expected_branches_hit is not None:
            actual_branches_hit = sum(1 for b in file_cov.branches if b.taken_count > 0)
            if actual_branches_hit != expected_branches_hit:
                result.add_warning(
                    f"Branch hit count mismatch in {file_cov.file_path}: "
                    f"expected {expected_branches_hit}, found {actual_branches_hit}"
                )
    
    # =========================================================================
    # MERGING (Q6.2)
    # =========================================================================
    
    def _merge_with_tool(self, coverage_files: List[Path]) -> Optional[MergeResult]:
        """
        Merge LCOV files using lcov tool
        
        Command: lcov --add-tracefile file1.info --add-tracefile file2.info -o merged.info
        
        Args:
            coverage_files: List of .info files to merge
        
        Returns:
            MergeResult if successful, None if tool unavailable/failed
        """
        tool_path = self._get_external_tool_path()
        if not tool_path:
            return None
        
        self.logger.debug(f"Merging {len(coverage_files)} files with lcov tool")
        
        # Create temporary file for merged output
        with tempfile.NamedTemporaryFile(suffix='.info', delete=False) as tmp:
            merged_path = Path(tmp.name)
        
        try:
            # Build command: lcov --add-tracefile f1 --add-tracefile f2 -o merged
            cmd = [str(tool_path)]
            
            for file_path in coverage_files:
                cmd.extend(['--add-tracefile', str(file_path)])
            
            cmd.extend(['-o', str(merged_path)])
            
            # Suppress stdout noise
            cmd.append('--quiet')
            
            # Run merge
            result = self.run_external_tool(cmd, timeout=120)
            
            if result.returncode != 0:
                self.logger.debug(f"lcov merge failed: {result.stderr}")
                return None
            
            if not merged_path.exists() or merged_path.stat().st_size == 0:
                self.logger.debug("lcov merge produced no output")
                return None
            
            # Parse the merged file
            parse_result = self.parse_file(merged_path)
            
            merge_result = MergeResult(
                success=parse_result.success,
                merged_coverage=parse_result.coverage,
                merged_file_path=merged_path,
                errors=parse_result.errors,
                warnings=parse_result.warnings,
                used_external_tool=True
            )
            
            return merge_result
        
        except Exception as e:
            self.logger.debug(f"Tool-based merging failed: {e}")
            if merged_path.exists():
                merged_path.unlink()
            return None
    
    # =========================================================================
    # ADDITIONAL METHODS
    # =========================================================================
    
    def get_lcov_version(self) -> Optional[str]:
        """
        Get lcov version
        
        Returns:
            Version string, or None if tool unavailable
        """
        tool_path = self._get_external_tool_path()
        if not tool_path:
            return None
        
        try:
            result = self.run_external_tool(
                [str(tool_path), '--version'],
                timeout=5
            )
            
            if result.returncode == 0:
                # Extract version from output
                # Format: "lcov: LCOV version 1.15"
                match = re.search(r'LCOV version\s+(\S+)', result.stdout)
                if match:
                    return match.group(1)
        
        except Exception:
            pass
        
        return None
    
    def filter_coverage(
        self,
        input_file: Path,
        output_file: Path,
        include_patterns: Optional[List[str]] = None,
        exclude_patterns: Optional[List[str]] = None
    ) -> bool:
        """
        Filter LCOV coverage by file patterns
        
        Uses: lcov -e/-r for filtering
        
        Args:
            input_file: Input LCOV file
            output_file: Output LCOV file
            include_patterns: Patterns to include (e.g., ["*/src/*"])
            exclude_patterns: Patterns to exclude (e.g., ["*/test/*"])
        
        Returns:
            True if successful
        """
        tool_path = self._get_external_tool_path()
        if not tool_path:
            self.logger.warning("Cannot filter: lcov tool not available")
            return False
        
        try:
            cmd = [str(tool_path)]
            
            # Extract (include) patterns
            if include_patterns:
                cmd.extend(['-e', str(input_file)] + include_patterns)
                cmd.extend(['-o', str(output_file)])
            
            # Remove (exclude) patterns
            elif exclude_patterns:
                cmd.extend(['-r', str(input_file)] + exclude_patterns)
                cmd.extend(['-o', str(output_file)])
            
            else:
                self.logger.warning("No filter patterns provided")
                return False
            
            result = self.run_external_tool(cmd, timeout=60)
            
            return result.returncode == 0 and output_file.exists()
        
        except Exception as e:
            self.logger.error(f"Failed to filter coverage: {e}")
            return False
    
    def generate_html_report(
        self,
        lcov_file: Path,
        output_dir: Path,
        title: Optional[str] = None
    ) -> bool:
        """
        Generate HTML coverage report using genhtml
        
        Args:
            lcov_file: Input LCOV file
            output_dir: Output directory for HTML files
            title: Report title (optional)
        
        Returns:
            True if successful
        """
        if not self._genhtml_tool:
            self._genhtml_tool = self.find_tool_in_path("genhtml")
        
        if not self._genhtml_tool:
            self.logger.warning("Cannot generate HTML: genhtml tool not available")
            return False
        
        try:
            output_dir.mkdir(parents=True, exist_ok=True)
            
            cmd = [
                str(self._genhtml_tool),
                str(lcov_file),
                '-o', str(output_dir),
                '--quiet'
            ]
            
            if title:
                cmd.extend(['--title', title])
            
            result = self.run_external_tool(cmd, timeout=120)
            
            return result.returncode == 0
        
        except Exception as e:
            self.logger.error(f"Failed to generate HTML report: {e}")
            return False
    
    def extract_summary(self, lcov_file: Path) -> Optional[Dict[str, Any]]:
        """
        Extract summary statistics from LCOV file
        
        Returns:
            Dictionary with summary stats, or None if failed
        """
        tool_path = self._get_external_tool_path()
        if not tool_path:
            # Fall back to parsing
            return self._extract_summary_python(lcov_file)
        
        try:
            result = self.run_external_tool(
                [str(tool_path), '--summary', str(lcov_file)],
                timeout=30
            )
            
            if result.returncode != 0:
                return None
            
            # Parse summary output
            # Format: "lines......: 85.7% (12 of 14 lines)"
            summary = {}
            
            for line in result.stdout.splitlines():
                if 'lines' in line.lower():
                    match = re.search(r'(\d+\.\d+)%.*\((\d+) of (\d+)', line)
                    if match:
                        summary['line_percentage'] = float(match.group(1))
                        summary['lines_hit'] = int(match.group(2))
                        summary['lines_found'] = int(match.group(3))
                
                elif 'functions' in line.lower():
                    match = re.search(r'(\d+\.\d+)%.*\((\d+) of (\d+)', line)
                    if match:
                        summary['function_percentage'] = float(match.group(1))
                        summary['functions_hit'] = int(match.group(2))
                        summary['functions_found'] = int(match.group(3))
                
                elif 'branches' in line.lower():
                    match = re.search(r'(\d+\.\d+)%.*\((\d+) of (\d+)', line)
                    if match:
                        summary['branch_percentage'] = float(match.group(1))
                        summary['branches_hit'] = int(match.group(2))
                        summary['branches_found'] = int(match.group(3))
            
            return summary if summary else None
        
        except Exception as e:
            self.logger.debug(f"Failed to extract summary with tool: {e}")
            return self._extract_summary_python(lcov_file)
    
    def _extract_summary_python(self, lcov_file: Path) -> Optional[Dict[str, Any]]:
        """Extract summary using Python parsing"""
        parse_result = self.parse_file(lcov_file)
        
        if not parse_result.success or not parse_result.coverage:
            return None
        
        module = parse_result.coverage
        
        total_lines = 0
        hit_lines = 0
        total_branches = 0
        hit_branches = 0
        
        for file_cov in module.files.values():
            total_lines += len(file_cov.lines)
            hit_lines += sum(1 for line in file_cov.lines.values() if line.is_covered)
            total_branches += len(file_cov.branches)
            hit_branches += sum(1 for b in file_cov.branches if b.taken_count > 0)
        
        return {
            'lines_found': total_lines,
            'lines_hit': hit_lines,
            'line_percentage': (hit_lines / total_lines * 100) if total_lines > 0 else 0,
            'branches_found': total_branches,
            'branches_hit': hit_branches,
            'branch_percentage': (hit_branches / total_branches * 100) if total_branches > 0 else 0,
        }


# =============================================================================
# CONVENIENCE FUNCTIONS
# =============================================================================

def create_lcov_parser(config: Optional[ParserConfig] = None) -> LCOVParser:
    """
    Create an LCOVParser instance
    
    Args:
        config: Parser configuration (optional)
    
    Returns:
        LCOVParser instance
    """
    return LCOVParser(config)


def is_lcov_available() -> bool:
    """
    Check if lcov tool is available
    
    Returns:
        True if tool is in PATH
    """
    parser = LCOVParser()
    return parser._get_external_tool_path() is not None


def get_lcov_version() -> Optional[str]:
    """
    Get lcov version
    
    Returns:
        Version string, or None if not available
    """
    parser = LCOVParser()
    return parser.get_lcov_version()
