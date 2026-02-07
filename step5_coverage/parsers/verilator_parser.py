Verilator coverage parser

Parses Verilator coverage.dat files and generates coverage metrics.

Verilator Coverage Format:
- Binary/text hybrid format (mostly text)
- Records: C, L, B, T, FN, FNDA, etc.
- Can be converted to LCOV format via verilator_coverage tool

Implementation Strategy (Q12 Option C):
1. Try verilator_coverage --write-info (generates LCOV)
2. Fall back to direct .dat parsing

Author: TB Eval Team
Version: 0.1.0
"""

import re
import tempfile
import shutil
from pathlib import Path
from typing import Optional, List, Dict, Set, Tuple
from dataclasses import dataclass

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
# VERILATOR FORMAT CONSTANTS
# =============================================================================

# Verilator .dat file signatures
VERILATOR_SIGNATURES = [
    b"Verilator coverage",
    b"# Verilator",
    b"coverage database",
]

# Record type prefixes in .dat format
RECORD_TYPES = {
    'C': 'coverage_line',      # Coverage record
    'L': 'line',               # Line coverage
    'B': 'branch',             # Branch coverage  
    'T': 'toggle',             # Toggle coverage
    'FN': 'function_name',     # Function name
    'FNDA': 'function_data',   # Function data
    'SF': 'source_file',       # Source file
    'end_of_record': 'eor',    # End of record
}

LCOV_RECORD_TYPES = {
    'TN': 'test_name',         # Test name
    'SF': 'source_file',       # Source file path
    'FN': 'function_name',     # Function definition (line, name)
    'FNDA': 'function_data',   # Function execution count
    'FNF': 'functions_found',  # Total functions
    'FNH': 'functions_hit',    # Functions executed
    'DA': 'line_data',         # Line coverage (line, hits)
    'LF': 'lines_found',       # Total lines
    'LH': 'lines_hit',         # Lines executed
    'BRDA': 'branch_data',     # Branch coverage (line, block, branch, taken)
    'BRF': 'branches_found',   # Total branches
    'BRH': 'branches_hit',     # Branches taken
    'end_of_record': 'eor',    # End of record marker
}



# =============================================================================
# VERILATOR PARSER
# =============================================================================

class VerilatorParser(BaseParser):
    """
    Parser for Verilator coverage.dat format (Q11 - highest priority)
    
    Verilator generates coverage data in a proprietary .dat format that
    can be processed by the verilator_coverage tool.
    
    Format Details:
    - Text-based with binary sections
    - Line coverage: Lines executed and hit counts
    - Branch coverage: Branch decisions taken/not taken
    - Toggle coverage: Signal bit transitions (0->1, 1->0)
    
    External Tool: verilator_coverage
    - Convert to LCOV: verilator_coverage --write-info output.info input.dat
    - Merge files: verilator_coverage --write merged.dat file1.dat file2.dat
    - Annotate: verilator_coverage --annotate output_dir input.dat
    """
    
    def __init__(self, config: Optional[ParserConfig] = None):
        """Initialize Verilator parser"""
        super().__init__(config)
        self._verilator_tool: Optional[Path] = None
        self._tool_checked = False
    
    # =========================================================================
    # ABSTRACT METHOD IMPLEMENTATIONS
    # =========================================================================
    
    def can_parse(self, file_path: Path) -> bool:
        """
        Check if file is Verilator coverage format
        
        Detection strategy:
        1. Check file extension (.dat)
        2. Check for Verilator signatures in header
        
        Args:
            file_path: Path to coverage file
        
        Returns:
            True if file appears to be Verilator format
        """
        file_path = Path(file_path)
        
        # Check extension
        if file_path.suffix.lower() != '.dat':
            return False
        
        # Check for Verilator signatures
        try:
            with open(file_path, 'rb') as f:
                header = f.read(512)  # Read first 512 bytes
                
                # Check for any Verilator signature
                for signature in VERILATOR_SIGNATURES:
                    if signature in header:
                        return True
                
                # Also check for common record types in text mode
                header_text = header.decode('utf-8', errors='ignore')
                if any(marker in header_text for marker in ['SF:', 'FN:', 'FNDA:', 'DA:']):
                    # Might be LCOV format from verilator_coverage --write-info
                    # We can handle this too
                    return True
        
        except Exception as e:
            self.logger.debug(f"Error checking file format: {e}")
            return False
        
        return False
    
    def get_format(self) -> CoverageFormat:
        """Return Verilator format identifier"""
        return CoverageFormat.VERILATOR_DAT
    
    def _get_external_tool_path(self) -> Optional[Path]:
        """
        Find verilator_coverage tool
        
        Checks:
        1. Config-specified path
        2. System PATH
        
        Returns:
            Path to verilator_coverage tool, or None if not found
        """
        if self._tool_checked:
            return self._verilator_tool
        
        self._tool_checked = True
        
        # Check config
        if self.config.verilator_tool_path:
            tool_path = Path(self.config.verilator_tool_path)
            if tool_path.exists():
                self._verilator_tool = tool_path
                return self._verilator_tool
        
        # Check system PATH
        self._verilator_tool = self.find_tool_in_path("verilator_coverage")
        
        if self._verilator_tool:
            self.logger.info(f"Found verilator_coverage: {self._verilator_tool}")
        else:
            self.logger.debug("verilator_coverage tool not found")
        
        return self._verilator_tool
    
    # =========================================================================
    # TOOL-BASED PARSING (Q12 - preferred method)
    # =========================================================================
    
    def _parse_with_tool(self, file_path: Path) -> Optional[ParseResult]:
        """
        Parse using verilator_coverage tool
        
        Strategy:
        1. Convert .dat to LCOV format: verilator_coverage --write-info
        2. Parse the LCOV output
        
        Args:
            file_path: Path to Verilator .dat file
        
        Returns:
            ParseResult if successful, None if tool unavailable/failed
        """
        tool_path = self._get_external_tool_path()
        if not tool_path:
            return None
        
        self.logger.debug(f"Parsing {file_path} with verilator_coverage tool")
        
        # Create temporary file for LCOV output
        with tempfile.NamedTemporaryFile(mode='w', suffix='.info', delete=False) as tmp:
            lcov_path = Path(tmp.name)
        
        try:
            # Run verilator_coverage --write-info
            result = self.run_external_tool(
                [
                    str(tool_path),
                    '--write-info', str(lcov_path),
                    str(file_path)
                ],
                timeout=60
            )
            
            if result.returncode != 0:
                self.logger.debug(f"verilator_coverage failed: {result.stderr}")
                return None
            
            if not lcov_path.exists() or lcov_path.stat().st_size == 0:
                self.logger.debug("verilator_coverage produced no output")
                return None
            
            # Parse the generated LCOV file
            parse_result = self._parse_lcov_output(lcov_path)
            
            if parse_result.success:
                self.logger.debug("Successfully parsed verilator_coverage output")
            
            return parse_result
        
        except Exception as e:
            self.logger.debug(f"Tool-based parsing failed: {e}")
            return None
        
        finally:
            # Cleanup temporary file
            if lcov_path.exists():
                lcov_path.unlink()
    
    def _parse_lcov_output(self, lcov_path: Path) -> ParseResult:
        """
        Parse LCOV format output from verilator_coverage
        
        LCOV format:
        TN:<test name>
        SF:<source file>
        FN:<line>,<function name>
        FNDA:<execution count>,<function name>
        DA:<line>,<hit count>
        BRDA:<line>,<block>,<branch>,<taken>
        end_of_record
        
        Args:
            lcov_path: Path to LCOV file
        
        Returns:
            ParseResult with parsed coverage
        """
        result = ParseResult(success=True)
        
        try:
            module = ModuleCoverage(module_name="verilator_coverage")
            current_file: Optional[FileCoverage] = None
            current_file_path: Optional[str] = None
            
            with open(lcov_path, 'r') as f:
                for line_num, line in enumerate(f, 1):
                    line = line.strip()
                    
                    if not line or line.startswith('#'):
                        continue
                    
                    # Parse record type
                    if ':' not in line:
                        continue
                    
                    record_type, record_data = line.split(':', 1)
                    
                    # Source file
                    if record_type == 'SF':
                        current_file_path = record_data
                        current_file = FileCoverage(file_path=current_file_path)
                        module.files[current_file_path] = current_file
                    
                    # Line coverage: DA:<line>,<hits>
                    elif record_type == 'DA' and current_file:
                        parts = record_data.split(',')
                        if len(parts) >= 2:
                            try:
                                line_no = int(parts[0])
                                hits = int(parts[1])
                                current_file.lines[line_no] = LineCoverageData(
                                    line_number=line_no,
                                    hit_count=hits
                                )
                            except ValueError:
                                result.add_warning(f"Invalid DA record at line {line_num}")
                    
                    # Branch coverage: BRDA:<line>,<block>,<branch>,<taken>
                    elif record_type == 'BRDA' and current_file:
                        parts = record_data.split(',')
                        if len(parts) >= 4:
                            try:
                                line_no = int(parts[0])
                                block = int(parts[1])
                                branch = int(parts[2])
                                taken = int(parts[3]) if parts[3] != '-' else 0
                                
                                current_file.branches.append(BranchData(
                                    line_number=line_no,
                                    block_number=block,
                                    branch_number=branch,
                                    taken_count=taken,
                                    not_taken_count=0  # LCOV doesn't track not-taken separately
                                ))
                            except ValueError:
                                result.add_warning(f"Invalid BRDA record at line {line_num}")
                    
                    # End of record
                    elif record_type == 'end_of_record':
                        current_file = None
                        current_file_path = None
            
            if not module.files:
                result.add_error("No coverage data found in LCOV output")
                return result
            
            result.coverage = module
            result.success = True
        
        except Exception as e:
            result.add_error(f"Failed to parse LCOV output: {e}")
        
        return result
    
    # =========================================================================
    # PYTHON-BASED PARSING (Q12 - fallback method)
    # =========================================================================
    
    def _parse_with_python(self, file_path: Path) -> ParseResult:
        """
        Parse Verilator .dat file using pure Python
        
        This is the fallback when verilator_coverage tool is unavailable.
        
        Verilator .dat format (LCOV-compatible):
        - Text-based with colon-separated records
        - Format: RECORD_TYPE:data
        - Main types: SF (source file), DA (line data), BRDA (branch data)
        
        Args:
            file_path: Path to Verilator .dat file
        
        Returns:
            ParseResult with parsed coverage
        """
        self.logger.debug(f"Parsing {file_path} with Python parser")
        
        result = ParseResult(success=True)
        
        try:
            module = ModuleCoverage(module_name="verilator_parsed")
            
            # Read file
            lines = self.read_file_lines(file_path)
            if not lines:
                result.add_error("Failed to read file or file is empty")
                return result
            
            current_file: Optional[FileCoverage] = None
            current_file_path: Optional[str] = None
            
            for line_num, line in enumerate(lines, 1):
                line = line.strip()
                
                # Skip empty lines and comments
                if not line or line.startswith('#'):
                    continue
                
                # Check for colon separator (LCOV format)
                if ':' not in line:
                    # Skip lines without colons (malformed or non-data lines)
                    continue
                
                # Split into record type and data (LCOV style - consistent with detection)
                try:
                    record_type, record_data = line.split(':', 1)
                except ValueError:
                    result.add_warning(f"Malformed record at line {line_num}: {line}")
                    continue
                
                # Source File: SF:<path>
                if record_type == 'SF':
                    current_file_path = record_data
                    current_file = FileCoverage(file_path=current_file_path)
                    module.files[current_file_path] = current_file
                    if current_file_path not in module.source_files:
                        module.source_files.append(current_file_path)
                
                # Test Name: TN:<name>
                elif record_type == 'TN':
                    # Store test name in metadata (optional)
                    if not module.module_name or module.module_name == "verilator_parsed":
                        module.module_name = record_data or "verilator_coverage"
                
                # Function Name: FN:<line>,<name>
                elif record_type == 'FN':
                    # Store function info (for future Phase 2 functional coverage)
                    pass
                
                # Function Data: FNDA:<count>,<name>
                elif record_type == 'FNDA':
                    # Store function coverage (for future Phase 2 functional coverage)
                    pass
                
                # Line Data: DA:<line>,<hits>[,<checksum>]
                elif record_type == 'DA' and current_file:
                    data_parts = record_data.split(',')
                    if len(data_parts) >= 2:
                        try:
                            line_no = int(data_parts[0])
                            hits = int(data_parts[1])
                            
                            current_file.lines[line_no] = LineCoverageData(
                                line_number=line_no,
                                hit_count=hits
                            )
                        except ValueError as e:
                            result.add_warning(f"Invalid DA record at line {line_num}: {line}")
                    else:
                        result.add_warning(f"Incomplete DA record at line {line_num}: {line}")
                
                # Branch Data: BRDA:<line>,<block>,<branch>,<taken>
                elif record_type == 'BRDA' and current_file:
                    data_parts = record_data.split(',')
                    if len(data_parts) >= 4:
                        try:
                            line_no = int(data_parts[0])
                            block = int(data_parts[1])
                            branch = int(data_parts[2])
                            # Handle '-' for not executed branches
                            taken = int(data_parts[3]) if data_parts[3] != '-' else 0
                            
                            current_file.branches.append(BranchData(
                                line_number=line_no,
                                block_number=block,
                                branch_number=branch,
                                taken_count=taken,
                                not_taken_count=0  # LCOV doesn't track not-taken separately
                            ))
                        except ValueError as e:
                            result.add_warning(f"Invalid BRDA record at line {line_num}: {line}")
                    else:
                        result.add_warning(f"Incomplete BRDA record at line {line_num}: {line}")
                
                # Lines Found: LF:<count>
                elif record_type == 'LF':
                    # Line count validation (optional)
                    pass
                
                # Lines Hit: LH:<count>
                elif record_type == 'LH':
                    # Line hit count validation (optional)
                    pass
                
                # Branches Found: BRF:<count>
                elif record_type == 'BRF':
                    # Branch count validation (optional)
                    pass
                
                # Branches Hit: BRH:<count>
                elif record_type == 'BRH':
                    # Branch hit count validation (optional)
                    pass
                
                # Functions Found: FNF:<count>
                elif record_type == 'FNF':
                    # Function count (Phase 2)
                    pass
                
                # Functions Hit: FNH:<count>
                elif record_type == 'FNH':
                    # Function hit count (Phase 2)
                    pass
                
                # End of record
                elif record_type == 'end_of_record':
                    current_file = None
                    current_file_path = None
                
                # Unknown record type
                else:
                    # Don't warn on every unknown type, just log for debugging
                    self.logger.debug(f"Unknown record type at line {line_num}: {record_type}")
            
            # Validate we got some data
            if not module.files:
                result.add_error("No coverage data found in .dat file")
                return result
            
            # Final validation: check if we have any actual coverage data
            has_data = False
            for file_cov in module.files.values():
                if file_cov.lines or file_cov.branches:
                    has_data = True
                    break
            
            if not has_data:
                result.add_error("Coverage file contains source files but no coverage data")
                return result
            
            result.coverage = module
            result.success = True
        
        except Exception as e:
            result.add_error(f"Python parsing failed: {e}")
            import traceback
            self.logger.debug(f"Parse exception: {traceback.format_exc()}")
        
        return result
    # =========================================================================
    # MERGING (Q6.2)
    # =========================================================================
    
    def _merge_with_tool(self, coverage_files: List[Path]) -> Optional[MergeResult]:
        """
        Merge Verilator .dat files using verilator_coverage tool
        
        Command: verilator_coverage --write merged.dat file1.dat file2.dat ...
        
        Args:
            coverage_files: List of .dat files to merge
        
        Returns:
            MergeResult if successful, None if tool unavailable/failed
        """
        tool_path = self._get_external_tool_path()
        if not tool_path:
            return None
        
        self.logger.debug(f"Merging {len(coverage_files)} files with verilator_coverage tool")
        
        # Create temporary file for merged output
        with tempfile.NamedTemporaryFile(suffix='.dat', delete=False) as tmp:
            merged_path = Path(tmp.name)
        
        try:
            # Build command: verilator_coverage --write merged.dat file1.dat file2.dat
            cmd = [
                str(tool_path),
                '--write', str(merged_path)
            ] + [str(f) for f in coverage_files]
            
            # Run merge
            result = self.run_external_tool(cmd, timeout=120)
            
            if result.returncode != 0:
                self.logger.debug(f"verilator_coverage merge failed: {result.stderr}")
                return None
            
            if not merged_path.exists() or merged_path.stat().st_size == 0:
                self.logger.debug("verilator_coverage merge produced no output")
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
    
    def get_verilator_version(self) -> Optional[str]:
        """
        Get Verilator version from verilator_coverage tool
        
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
                # Format: "Verilator 5.006 2023-01-15"
                match = re.search(r'Verilator\s+(\S+)', result.stdout)
                if match:
                    return match.group(1)
        
        except Exception:
            pass
        
        return None
    
    def export_to_lcov(self, dat_file: Path, lcov_output: Path) -> bool:
        """
        Export Verilator .dat to LCOV format
        
        Useful for integration with other tools that expect LCOV.
        
        Args:
            dat_file: Input .dat file
            lcov_output: Output .info file path
        
        Returns:
            True if successful
        """
        tool_path = self._get_external_tool_path()
        if not tool_path:
            self.logger.warning("Cannot export to LCOV: verilator_coverage not available")
            return False
        
        try:
            result = self.run_external_tool(
                [
                    str(tool_path),
                    '--write-info', str(lcov_output),
                    str(dat_file)
                ],
                timeout=60
            )
            
            return result.returncode == 0 and lcov_output.exists()
        
        except Exception as e:
            self.logger.error(f"Failed to export to LCOV: {e}")
            return False
    
    def annotate_coverage(
        self,
        dat_file: Path,
        output_dir: Path,
        annotate_all: bool = True
    ) -> bool:
        """
        Generate annotated source files with coverage
        
        Uses: verilator_coverage --annotate output_dir input.dat
        
        Args:
            dat_file: Input .dat file
            output_dir: Output directory for annotated files
            annotate_all: Include all source files (not just covered)
        
        Returns:
            True if successful
        """
        tool_path = self._get_external_tool_path()
        if not tool_path:
            self.logger.warning("Cannot annotate: verilator_coverage not available")
            return False
        
        try:
            output_dir.mkdir(parents=True, exist_ok=True)
            
            cmd = [
                str(tool_path),
                '--annotate', str(output_dir)
            ]
            
            if annotate_all:
                cmd.append('--annotate-all')
            
            cmd.append(str(dat_file))
            
            result = self.run_external_tool(cmd, timeout=120)
            
            return result.returncode == 0
        
        except Exception as e:
            self.logger.error(f"Failed to annotate coverage: {e}")
            return False
    
    def validate_dat_file(self, file_path: Path) -> Tuple[bool, List[str]]:
        """
        Validate Verilator .dat file integrity
        
        Checks:
        - File format
        - Has required sections
        - No obvious corruption
        
        Args:
            file_path: Path to .dat file
        
        Returns:
            Tuple of (is_valid, error_messages)
        """
        errors = []
        
        # Basic validation from base class
        if not self.validate_file(file_path):
            return False, self.errors
        
        # Check for required sections
        try:
            lines = self.read_file_lines(file_path)
            
            has_source_file = False
            has_data = False
            
            for line in lines[:100]:  # Check first 100 lines
                if line.startswith('SF:'):
                    has_source_file = True
                if line.startswith('DA:') or line.startswith('BRDA:'):
                    has_data = True
            
            if not has_source_file:
                errors.append("No source file (SF:) records found")
            
            if not has_data:
                errors.append("No coverage data (DA:/BRDA:) records found")
        
        except Exception as e:
            errors.append(f"Error reading file: {e}")
        
        return len(errors) == 0, errors


# =============================================================================
# CONVENIENCE FUNCTIONS
# =============================================================================

def create_verilator_parser(config: Optional[ParserConfig] = None) -> VerilatorParser:
    """
    Create a VerilatorParser instance
    
    Args:
        config: Parser configuration (optional)
    
    Returns:
        VerilatorParser instance
    """
    return VerilatorParser(config)


def is_verilator_coverage_available() -> bool:
    """
    Check if verilator_coverage tool is available
    
    Returns:
        True if tool is in PATH
    """
    parser = VerilatorParser()
    return parser._get_external_tool_path() is not None


def get_verilator_coverage_version() -> Optional[str]:
    """
    Get verilator_coverage version
    
    Returns:
        Version string, or None if not available
    """
    parser = VerilatorParser()
    return parser.get_verilator_version()
