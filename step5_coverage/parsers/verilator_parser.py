"""
Verilator coverage parser

Parses Verilator coverage.dat files (Q11 - highest priority parser)

Verilator Coverage Format:
- Native format: Binary/text hybrid .dat files
- Annotated format: LCOV-like format from verilator_coverage --annotate
- Coverage types: Line, branch, toggle

Strategy (Q12 Option C):
1. Try verilator_coverage tool (preferred - faster, more accurate)
2. Fall back to Python parsing of .dat format

Author: TB Eval Team
Version: 0.1.0
"""

from pathlib import Path
from typing import Optional, List, Dict, Any, Set, Tuple
import tempfile
import shutil
import json
import re
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
# VERILATOR COVERAGE PARSER
# =============================================================================

class VerilatorParser(BaseParser):
    """
    Parser for Verilator coverage.dat format (Q11 - highest priority)
    
    Verilator generates coverage data in a proprietary .dat format.
    The best way to parse it is using verilator_coverage tool.
    
    Features:
    - Line coverage
    - Branch coverage  
    - Toggle coverage
    - Merge support via verilator_coverage --write
    
    Usage:
        >>> parser = VerilatorParser()
        >>> result = parser.parse_file(Path("coverage.dat"))
        >>> if result.success:
        ...     print(f"Line coverage: {result.coverage.line_coverage_percent}%")
    """
    
    def __init__(self, config: Optional[ParserConfig] = None):
        """
        Initialize Verilator parser
        
        Args:
            config: Parser configuration
        """
        super().__init__(config)
        self._verilator_version: Optional[str] = None
    
    # =========================================================================
    # ABSTRACT METHOD IMPLEMENTATIONS
    # =========================================================================
    
    def can_parse(self, file_path: Path) -> bool:
        """
        Check if file is Verilator coverage.dat format
        
        Detection strategy:
        1. Check file extension (.dat)
        2. Check for Verilator magic markers in file
        
        Args:
            file_path: Path to coverage file
        
        Returns:
            True if file is Verilator coverage format
        """
        file_path = Path(file_path)
        
        # Check extension
        if file_path.suffix not in [".dat", ".info"]:
            return False
        
        # For .info files, might be LCOV format
        if file_path.suffix == ".info":
            # Only accept if it's from Verilator
            return self._is_verilator_info_file(file_path)
        
        # Check file content for Verilator markers
        try:
            with open(file_path, 'rb') as f:
                # Read first 512 bytes
                header = f.read(512)
                
                # Check for Verilator-specific markers
                # Verilator coverage files often contain these strings
                markers = [
                    b'Verilator',
                    b'coverage',
                    b'vlcov',  # Verilator coverage internal format
                    b'SF:',    # Source File marker (LCOV-like)
                    b'FNDA:',  # Function Data marker
                ]
                
                if any(marker in header for marker in markers):
                    return True
                
                # Check if it's a text-based .dat file
                try:
                    text_header = header.decode('utf-8', errors='ignore')
                    if 'TN:' in text_header or 'SF:' in text_header:
                        return True
                except:
                    pass
        
        except Exception as e:
            self.logger.debug(f"Error checking file format: {e}")
            return False
        
        return False
    
    def get_format(self) -> CoverageFormat:
        """Get coverage format identifier"""
        return CoverageFormat.VERILATOR_DAT
    
    def _get_external_tool_path(self) -> Optional[Path]:
        """
        Get path to verilator_coverage tool
        
        Checks:
        1. Config-specified path
        2. System PATH (verilator_coverage)
        3. Common installation locations
        
        Returns:
            Path to verilator_coverage tool, or None if not found
        """
        # Check config first
        if self.config.verilator_tool_path:
            tool_path = Path(self.config.verilator_tool_path)
            if tool_path.exists():
                return tool_path
        
        # Check system PATH
        tool_path = self.find_tool_in_path("verilator_coverage")
        if tool_path:
            return tool_path
        
        # Check common installation locations
        common_paths = [
            Path("/usr/bin/verilator_coverage"),
            Path("/usr/local/bin/verilator_coverage"),
            Path.home() / ".local/bin/verilator_coverage",
        ]
        
        for path in common_paths:
            if path.exists():
                return path
        
        return None
    
    def _parse_with_tool(self, file_path: Path) -> Optional[ParseResult]:
        """
        Parse Verilator coverage using verilator_coverage tool (Q12 - preferred)
        
        Strategy:
        1. Run verilator_coverage --annotate to generate human-readable output
        2. Parse the annotated output files
        
        Args:
            file_path: Path to coverage.dat file
        
        Returns:
            ParseResult if successful, None if tool unavailable/failed
        """
        tool_path = self._get_external_tool_path()
        if not tool_path:
            self.logger.debug("verilator_coverage tool not found")
            return None
        
        # Get Verilator version
        if self._verilator_version is None:
            self._verilator_version = self._get_verilator_version(tool_path)
        
        result = ParseResult(success=True)
        
        try:
            # Create temporary directory for annotated output
            with tempfile.TemporaryDirectory() as tmpdir:
                tmpdir = Path(tmpdir)
                
                # Run verilator_coverage --annotate
                self.logger.debug(f"Running verilator_coverage on {file_path}")
                
                cmd = [
                    str(tool_path),
                    "--annotate", str(tmpdir),
                    "--annotate-all",
                    str(file_path)
                ]
                
                proc_result = self.run_external_tool(cmd, timeout=60)
                
                if proc_result.returncode != 0:
                    result.add_error(f"verilator_coverage failed: {proc_result.stderr}")
                    return None
                
                # Parse annotated output
                module = self._parse_annotated_output(tmpdir, file_path)
                
                if module is None:
                    result.add_error("Failed to parse annotated output")
                    return None
                
                result.coverage = module
                result.metadata["verilator_version"] = self._verilator_version
                result.metadata["annotate_dir"] = str(tmpdir)
        
        except Exception as e:
            self.logger.error(f"Tool parsing failed: {e}", exc_info=True)
            result.add_error(f"Tool execution failed: {e}")
            return None
        
        return result
    
    def _parse_with_python(self, file_path: Path) -> ParseResult:
        """
        Parse Verilator coverage using pure Python (Q12 - fallback)
        
        Parses the .dat file directly without external tools.
        The .dat format is text-based and similar to LCOV format.
        
        Args:
            file_path: Path to coverage.dat file
        
        Returns:
            ParseResult with parsed coverage data
        """
        result = ParseResult(success=True)
        
        try:
            module = ModuleCoverage(
                module_name=file_path.stem,
                source_files=[]
            )
            
            lines = self.read_file_lines(file_path)
            if not lines:
                result.add_error("Failed to read file or file is empty")
                return result
            
            # Parse lines
            current_file: Optional[str] = None
            current_file_cov: Optional[FileCoverage] = None
            
            for line_num, line in enumerate(lines, 1):
                line = line.strip()
                
                # Skip empty lines and comments
                if not line or line.startswith('#'):
                    continue
                
                # Parse record type
                if ':' not in line:
                    continue
                
                parts = line.split(':', 1)
                if len(parts) != 2:
                    continue
                
                record_type = parts[0]
                record_data = parts[1]
                
                # TN: Test Name
                if record_type == 'TN':
                    result.metadata["test_name"] = record_data
                
                # SF: Source File
                elif record_type == 'SF':
                    current_file = record_data
                    if current_file not in module.files:
                        current_file_cov = FileCoverage(file_path=current_file)
                        module.files[current_file] = current_file_cov
                        if current_file not in module.source_files:
                            module.source_files.append(current_file)
                    else:
                        current_file_cov = module.files[current_file]
                
                # FN: Function (line, name)
                elif record_type == 'FN':
                    # Function definition - we track these but don't create separate coverage
                    pass
                
                # FNDA: Function Data (execution_count, function_name)
                elif record_type == 'FNDA':
                    # Function coverage - we track at line level
                    pass
                
                # FNF: Functions Found
                elif record_type == 'FNF':
                    result.metadata["functions_found"] = int(record_data)
                
                # FNH: Functions Hit
                elif record_type == 'FNH':
                    result.metadata["functions_hit"] = int(record_data)
                
                # DA: Line Data (line_number, hit_count)
                elif record_type == 'DA' and current_file_cov:
                    self._parse_line_data(record_data, current_file_cov, result)
                
                # BRDA: Branch Data (line, block, branch, taken)
                elif record_type == 'BRDA' and current_file_cov:
                    self._parse_branch_data(record_data, current_file_cov, result)
                
                # BRF: Branches Found
                elif record_type == 'BRF':
                    result.metadata["branches_found"] = int(record_data)
                
                # BRH: Branches Hit
                elif record_type == 'BRH':
                    result.metadata["branches_hit"] = int(record_data)
                
                # LF: Lines Found
                elif record_type == 'LF':
                    if current_file_cov:
                        result.metadata[f"{current_file}_lines_found"] = int(record_data)
                
                # LH: Lines Hit
                elif record_type == 'LH':
                    if current_file_cov:
                        result.metadata[f"{current_file}_lines_hit"] = int(record_data)
                
                # end_of_record
                elif record_type == 'end_of_record':
                    current_file = None
                    current_file_cov = None
            
            if not module.files:
                result.add_warning("No coverage data found in file")
            
            result.coverage = module
        
        except Exception as e:
            self.logger.error(f"Python parsing failed: {e}", exc_info=True)
            result.add_error(f"Parsing failed: {e}")
        
        return result
    
    def _merge_with_tool(self, coverage_files: List[Path]) -> Optional[MergeResult]:
        """
        Merge Verilator coverage files using verilator_coverage tool (Q6.2 - preferred)
        
        Uses: verilator_coverage --write merged.dat file1.dat file2.dat ...
        
        Args:
            coverage_files: List of .dat files to merge
        
        Returns:
            MergeResult if successful, None if tool unavailable/failed
        """
        tool_path = self._get_external_tool_path()
        if not tool_path:
            return None
        
        result = MergeResult(success=True)
        
        try:
            # Create temporary merged file
            with tempfile.NamedTemporaryFile(
                suffix=".dat",
                delete=False,
                dir=tempfile.gettempdir()
            ) as merged_file:
                merged_path = Path(merged_file.name)
            
            # Run verilator_coverage --write
            self.logger.debug(f"Merging {len(coverage_files)} files with verilator_coverage")
            
            cmd = [
                str(tool_path),
                "--write", str(merged_path),
                *[str(f) for f in coverage_files]
            ]
            
            proc_result = self.run_external_tool(cmd, timeout=120)
            
            if proc_result.returncode != 0:
                result.add_error(f"verilator_coverage merge failed: {proc_result.stderr}")
                merged_path.unlink(missing_ok=True)
                return None
            
            # Verify merged file was created
            if not merged_path.exists() or merged_path.stat().st_size == 0:
                result.add_error("Merged file not created or is empty")
                merged_path.unlink(missing_ok=True)
                return None
            
            # Parse the merged file
            parse_result = self.parse_file(merged_path)
            
            if not parse_result.success:
                result.add_error("Failed to parse merged file")
                result.errors.extend(parse_result.errors)
                merged_path.unlink(missing_ok=True)
                return None
            
            result.merged_coverage = parse_result.coverage
            result.merged_file_path = merged_path
            result.metadata["merged_file"] = str(merged_path)
            result.metadata["num_files_merged"] = len(coverage_files)
        
        except Exception as e:
            self.logger.error(f"Tool merge failed: {e}", exc_info=True)
            result.add_error(f"Merge failed: {e}")
            return None
        
        return result
    
    # =========================================================================
    # HELPER METHODS
    # =========================================================================
    
    def _is_verilator_info_file(self, file_path: Path) -> bool:
        """
        Check if .info file is from Verilator
        
        Args:
            file_path: Path to .info file
        
        Returns:
            True if file is Verilator-generated
        """
        try:
            # Check first few lines for Verilator markers
            with open(file_path, 'r') as f:
                for i, line in enumerate(f):
                    if i > 10:  # Check first 10 lines
                        break
                    if 'verilator' in line.lower() or 'vlcov' in line.lower():
                        return True
        except:
            pass
        
        return False
    
    def _get_verilator_version(self, tool_path: Path) -> Optional[str]:
        """
        Get Verilator version
        
        Args:
            tool_path: Path to verilator_coverage tool
        
        Returns:
            Version string, or None if unable to determine
        """
        try:
            result = self.run_external_tool([str(tool_path), "--version"], timeout=5)
            
            if result.returncode == 0:
                # Parse version from output
                # Example: "Verilator Coverage 5.006"
                match = re.search(r'(\d+\.\d+)', result.stdout)
                if match:
                    return match.group(1)
        
        except Exception as e:
            self.logger.debug(f"Failed to get Verilator version: {e}")
        
        return None
    
    def _parse_annotated_output(
        self,
        annotate_dir: Path,
        source_file: Path
    ) -> Optional[ModuleCoverage]:
        """
        Parse verilator_coverage --annotate output
        
        The annotate directory contains:
        - annotated.txt: Summary file
        - <source_file>.v: Annotated source files
        
        Args:
            annotate_dir: Directory containing annotated output
            source_file: Original coverage file (for module name)
        
        Returns:
            ModuleCoverage if successful, None otherwise
        """
        module = ModuleCoverage(
            module_name=source_file.stem,
            source_files=[]
        )
        
        # Look for annotated files
        annotated_files = list(annotate_dir.glob("*.v")) + list(annotate_dir.glob("*.sv"))
        
        if not annotated_files:
            self.logger.warning("No annotated files found")
            return None
        
        # Parse each annotated file
        for ann_file in annotated_files:
            file_cov = self._parse_annotated_file(ann_file)
            if file_cov:
                module.files[file_cov.file_path] = file_cov
                if file_cov.file_path not in module.source_files:
                    module.source_files.append(file_cov.file_path)
        
        return module if module.files else None
    
    def _parse_annotated_file(self, ann_file: Path) -> Optional[FileCoverage]:
        """
        Parse a single annotated source file
        
        Verilator annotated format:
        %000001  <hit_count>  <line>
        
        Args:
            ann_file: Path to annotated file
        
        Returns:
            FileCoverage if successful, None otherwise
        """
        # Extract original source file name (remove .v/.sv suffix if doubled)
        source_name = ann_file.name
        
        file_cov = FileCoverage(file_path=source_name)
        
        try:
            lines = self.read_file_lines(ann_file)
            
            for line_num, line in enumerate(lines, 1):
                # Annotated lines start with coverage count
                # Format: %<line_number> <hit_count> <source_line>
                match = re.match(r'%(\d+)\s+(\d+)\s+(.*)', line)
                if match:
                    line_number = int(match.group(1))
                    hit_count = int(match.group(2))
                    source_line = match.group(3)
                    
                    file_cov.lines[line_number] = LineCoverageData(
                        line_number=line_number,
                        hit_count=hit_count,
                        source_line=source_line.strip()
                    )
        
        except Exception as e:
            self.logger.error(f"Failed to parse annotated file {ann_file}: {e}")
            return None
        
        return file_cov if file_cov.lines else None
    
    def _parse_line_data(
        self,
        data: str,
        file_cov: FileCoverage,
        result: ParseResult
    ) -> None:
        """
        Parse DA (Data/Line coverage) record
        
        Format: DA:<line_number>,<hit_count>[,<checksum>]
        Example: DA:10,1000
        
        Args:
            data: Record data after "DA:"
            file_cov: FileCoverage to add line to
            result: ParseResult for error reporting
        """
        try:
            parts = data.split(',')
            if len(parts) < 2:
                result.add_warning(f"Invalid DA record: {data}")
                return
            
            line_number = int(parts[0])
            hit_count = int(parts[1])
            
            file_cov.lines[line_number] = LineCoverageData(
                line_number=line_number,
                hit_count=hit_count
            )
        
        except ValueError as e:
            result.add_warning(f"Failed to parse DA record '{data}': {e}")
    
    def _parse_branch_data(
        self,
        data: str,
        file_cov: FileCoverage,
        result: ParseResult
    ) -> None:
        """
        Parse BRDA (Branch Data) record
        
        Format: BRDA:<line>,<block>,<branch>,<taken>
        Example: BRDA:15,0,0,850
                BRDA:15,0,1,150
        
        Args:
            data: Record data after "BRDA:"
            file_cov: FileCoverage to add branch to
            result: ParseResult for error reporting
        """
        try:
            parts = data.split(',')
            if len(parts) < 4:
                result.add_warning(f"Invalid BRDA record: {data}")
                return
            
            line_number = int(parts[0])
            block_number = int(parts[1])
            branch_number = int(parts[2])
            taken = parts[3]
            
            # Handle "-" for never taken
            taken_count = 0 if taken == '-' else int(taken)
            
            # For Verilator, we get separate records for each branch direction
            # We need to combine them
            # Look for existing branch entry
            existing_branch = None
            for branch in file_cov.branches:
                if (branch.line_number == line_number and
                    branch.block_number == block_number and
                    branch.branch_number == branch_number):
                    existing_branch = branch
                    break
            
            if existing_branch:
                # This is the alternate direction
                existing_branch.not_taken_count = taken_count
            else:
                # Create new branch entry
                file_cov.branches.append(BranchData(
                    line_number=line_number,
                    block_number=block_number,
                    branch_number=branch_number,
                    taken_count=taken_count,
                    not_taken_count=0  # Will be filled by next record
                ))
        
        except ValueError as e:
            result.add_warning(f"Failed to parse BRDA record '{data}': {e}")
    
    # =========================================================================
    # VERILATOR-SPECIFIC FEATURES
    # =========================================================================
    
    def extract_toggle_coverage(self, file_path: Path) -> Dict[str, ToggleData]:
        """
        Extract toggle coverage from Verilator coverage file
        
        Toggle coverage requires special processing with verilator_coverage.
        
        Args:
            file_path: Path to coverage.dat file
        
        Returns:
            Dictionary of signal_name -> ToggleData
        """
        tool_path = self._get_external_tool_path()
        if not tool_path:
            self.logger.warning("Cannot extract toggle coverage without verilator_coverage tool")
            return {}
        
        toggles: Dict[str, ToggleData] = {}
        
        try:
            # Run verilator_coverage with toggle report
            cmd = [
                str(tool_path),
                "--rank",
                "--annotate-min", "1",
                str(file_path)
            ]
            
            result = self.run_external_tool(cmd, timeout=60)
            
            if result.returncode == 0:
                # Parse toggle information from output
                # This is format-specific and may need adjustment
                # based on actual Verilator output
                pass
        
        except Exception as e:
            self.logger.error(f"Failed to extract toggle coverage: {e}")
        
        return toggles
    
    def get_coverage_summary(self, file_path: Path) -> Dict[str, Any]:
        """
        Get coverage summary using verilator_coverage
        
        Args:
            file_path: Path to coverage.dat file
        
        Returns:
            Dictionary with coverage summary statistics
        """
        tool_path = self._get_external_tool_path()
        if not tool_path:
            return {}
        
        summary = {}
        
        try:
            cmd = [str(tool_path), "--rank", str(file_path)]
            result = self.run_external_tool(cmd, timeout=30)
            
            if result.returncode == 0:
                # Parse summary from output
                # Example output:
                # Lines: 85.7% (18/21)
                # Branches: 100.0% (4/4)
                
                for line in result.stdout.split('\n'):
                    if 'Lines:' in line:
                        match = re.search(r'(\d+\.\d+)%\s+\((\d+)/(\d+)\)', line)
                        if match:
                            summary['line_percent'] = float(match.group(1))
                            summary['lines_hit'] = int(match.group(2))
                            summary['lines_total'] = int(match.group(3))
                    
                    elif 'Branches:' in line:
                        match = re.search(r'(\d+\.\d+)%\s+\((\d+)/(\d+)\)', line)
                        if match:
                            summary['branch_percent'] = float(match.group(1))
                            summary['branches_hit'] = int(match.group(2))
                            summary['branches_total'] = int(match.group(3))
        
        except Exception as e:
            self.logger.error(f"Failed to get coverage summary: {e}")
        
        return summary


# =============================================================================
# CONVENIENCE FUNCTIONS
# =============================================================================

def parse_verilator_coverage(file_path: Path) -> ParseResult:
    """
    Convenience function to parse a Verilator coverage file
    
    Args:
        file_path: Path to coverage.dat file
    
    Returns:
        ParseResult with coverage data
    
    Example:
        >>> result = parse_verilator_coverage(Path("coverage.dat"))
        >>> if result.success:
        ...     print(f"Coverage: {result.coverage.line_coverage_percent}%")
    """
    parser = VerilatorParser()
    return parser.parse_file(file_path)


def merge_verilator_coverage(coverage_files: List[Path]) -> MergeResult:
    """
    Convenience function to merge Verilator coverage files
    
    Args:
        coverage_files: List of .dat files to merge
    
    Returns:
        MergeResult with merged coverage data
    
    Example:
        >>> files = [Path("test1.dat"), Path("test2.dat")]
        >>> result = merge_verilator_coverage(files)
        >>> if result.success:
        ...     print(f"Merged coverage: {result.merged_coverage.line_coverage_percent}%")
    """
    parser = VerilatorParser()
    return parser.merge_coverage(coverage_files)
