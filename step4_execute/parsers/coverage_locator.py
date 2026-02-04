"""
Coverage file locator

Locates and validates coverage files after test execution.
Supports multiple coverage formats and organization strategies.

Author: TB Eval Team
Version: 0.1.0
"""

import os
from pathlib import Path
from typing import List, Optional, Dict, Any, Set, Tuple
from datetime import datetime
import re

from ..models import CoverageFile, CoverageFormat, CoverageInfo


class CoverageLocator:
    """
    Locates coverage files after test execution
    
    Supports multiple coverage formats:
    - Verilator: coverage.dat
    - Questa/ModelSim: *.ucdb
    - VCS: *.vdb
    - LCOV: *.info, *.lcov
    - GCOV: *.gcda, *.gcno
    """
    
    # File extension to format mapping
    FORMAT_EXTENSIONS = {
        '.dat': CoverageFormat.VERILATOR_DAT,
        '.ucdb': CoverageFormat.QUESTA_UCDB,
        '.vdb': CoverageFormat.QUESTA_UCDB,  # VCS also uses similar format
        '.info': CoverageFormat.LCOV,
        '.lcov': CoverageFormat.LCOV,
        '.gcda': CoverageFormat.GCOV,
        '.gcno': CoverageFormat.GCOV,
    }
    
    # Common coverage file names
    COMMON_NAMES = [
        'coverage.dat',           # Verilator default
        'coverage.ucdb',          # Questa default
        'coverage.info',          # LCOV default
        'coverage.lcov',
        'cov.dat',
        'sim_coverage.dat',
    ]
    
    def __init__(self, working_dir: Path):
        """
        Initialize coverage locator
        
        Args:
            working_dir: Working directory to search from
        """
        self.working_dir = Path(working_dir)
    
    def locate_all(
        self,
        search_dirs: Optional[List[Path]] = None,
        test_names: Optional[List[str]] = None,
        max_depth: int = 3,
    ) -> CoverageInfo:
        """
        Locate all coverage files
        
        Args:
            search_dirs: Directories to search (default: [working_dir])
            test_names: Known test names for per-test matching
            max_depth: Maximum directory depth to search
        
        Returns:
            CoverageInfo with located files
        """
        if search_dirs is None:
            search_dirs = [self.working_dir]
        
        # Convert to absolute paths
        search_dirs = [Path(d).resolve() if not Path(d).is_absolute() 
                      else Path(d) for d in search_dirs]
        
        # Find all coverage files
        all_files = []
        for search_dir in search_dirs:
            if search_dir.exists():
                files = self._find_coverage_files(search_dir, max_depth)
                all_files.extend(files)
        
        # Deduplicate by path
        unique_files = {}
        for file_path in all_files:
            unique_files[str(file_path)] = file_path
        
        # Create CoverageFile objects
        coverage_files = []
        for file_path in unique_files.values():
            cov_file = self._create_coverage_file(file_path, test_names)
            if cov_file:
                coverage_files.append(cov_file)
        
        # Determine primary format
        primary_format = self._determine_primary_format(coverage_files)
        
        # Check if per-test or aggregate
        per_test = self._is_per_test_coverage(coverage_files)
        
        # Build CoverageInfo
        coverage_info = CoverageInfo(
            files=coverage_files,
            primary_format=primary_format,
            per_test=per_test,
            collection_method="automatic",
        )
        
        return coverage_info
    
    def locate_for_test(
        self,
        test_name: str,
        search_dirs: Optional[List[Path]] = None,
    ) -> Optional[CoverageFile]:
        """
        Locate coverage file for specific test
        
        Args:
            test_name: Test name
            search_dirs: Directories to search
        
        Returns:
            CoverageFile or None
        """
        if search_dirs is None:
            search_dirs = [self.working_dir]
        
        # Try common patterns
        patterns = [
            f"coverage_{test_name}.dat",
            f"coverage_{test_name}.ucdb",
            f"{test_name}_coverage.dat",
            f"{test_name}.dat",
            f"cov_{test_name}.dat",
        ]
        
        for search_dir in search_dirs:
            search_dir = Path(search_dir)
            if not search_dir.exists():
                continue
            
            # Try exact matches
            for pattern in patterns:
                file_path = search_dir / pattern
                if file_path.exists():
                    return self._create_coverage_file(file_path, [test_name])
            
            # Try pattern matching
            for file_path in search_dir.glob("*coverage*"):
                if test_name in file_path.name:
                    return self._create_coverage_file(file_path, [test_name])
        
        return None
    
    def _find_coverage_files(
        self,
        search_dir: Path,
        max_depth: int,
        current_depth: int = 0,
    ) -> List[Path]:
        """
        Recursively find coverage files
        
        Args:
            search_dir: Directory to search
            max_depth: Maximum depth
            current_depth: Current recursion depth
        
        Returns:
            List of coverage file paths
        """
        if not search_dir.exists() or current_depth > max_depth:
            return []
        
        files = []
        
        try:
            for item in search_dir.iterdir():
                if item.is_file():
                    if self._is_coverage_file(item):
                        files.append(item)
                
                elif item.is_dir():
                    # Skip hidden directories and common exclusions
                    if item.name.startswith('.'):
                        continue
                    if item.name in ['__pycache__', 'node_modules', 'venv']:
                        continue
                    
                    # Recurse
                    sub_files = self._find_coverage_files(
                        item,
                        max_depth,
                        current_depth + 1
                    )
                    files.extend(sub_files)
        
        except PermissionError:
            pass  # Skip directories we can't access
        
        return files
    
    def _is_coverage_file(self, file_path: Path) -> bool:
        """
        Check if file is a coverage file
        
        Args:
            file_path: File to check
        
        Returns:
            True if coverage file
        """
        # Check extension
        if file_path.suffix.lower() in self.FORMAT_EXTENSIONS:
            return True
        
        # Check common names
        if file_path.name.lower() in self.COMMON_NAMES:
            return True
        
        # Check if filename contains "coverage" or "cov"
        name_lower = file_path.name.lower()
        if 'coverage' in name_lower or 'cov' in name_lower:
            # But exclude some false positives
            if not any(excl in name_lower for excl in ['.log', '.txt', '.md']):
                return True
        
        return False
    
    def _create_coverage_file(
        self,
        file_path: Path,
        test_names: Optional[List[str]] = None,
    ) -> Optional[CoverageFile]:
        """
        Create CoverageFile object
        
        Args:
            file_path: Path to coverage file
            test_names: Known test names for matching
        
        Returns:
            CoverageFile or None if invalid
        """
        if not file_path.exists():
            return None
        
        # Determine format
        format = self._detect_format(file_path)
        
        # Validate file
        is_valid = self._validate_coverage_file(file_path, format)
        
        # Try to determine test name
        test_name = self._extract_test_name(file_path, test_names)
        
        # Get file metadata
        stat = file_path.stat()
        created_time = datetime.fromtimestamp(stat.st_mtime).isoformat()
        
        return CoverageFile(
            test_name=test_name,
            file_path=str(file_path),
            format=format,
            size_bytes=stat.st_size,
            valid=is_valid,
            created_time=created_time,
        )
    
    def _detect_format(self, file_path: Path) -> CoverageFormat:
        """
        Detect coverage file format
        
        Args:
            file_path: Coverage file path
        
        Returns:
            CoverageFormat
        """
        # Check extension first
        suffix = file_path.suffix.lower()
        if suffix in self.FORMAT_EXTENSIONS:
            return self.FORMAT_EXTENSIONS[suffix]
        
        # Try to detect from content
        try:
            with open(file_path, 'rb') as f:
                header = f.read(1024)
            
            # Check for text-based formats
            try:
                header_text = header.decode('utf-8', errors='ignore')
                
                # LCOV format
                if 'TN:' in header_text or 'SF:' in header_text:
                    return CoverageFormat.LCOV
                
                # Verilator text format (rare)
                if 'Verilator' in header_text or 'VLCOV' in header_text:
                    return CoverageFormat.VERILATOR_DAT
            
            except UnicodeDecodeError:
                pass  # Binary format
        
        except Exception:
            pass
        
        return CoverageFormat.UNKNOWN
    
    def _validate_coverage_file(
        self,
        file_path: Path,
        format: CoverageFormat
    ) -> bool:
        """
        Validate coverage file
        
        Args:
            file_path: Coverage file path
            format: Coverage format
        
        Returns:
            True if valid
        """
        if not file_path.exists():
            return False
        
        # Check file is not empty
        if file_path.stat().st_size == 0:
            return False
        
        # Format-specific validation
        if format == CoverageFormat.VERILATOR_DAT:
            return self._validate_verilator_dat(file_path)
        
        elif format == CoverageFormat.LCOV:
            return self._validate_lcov(file_path)
        
        elif format == CoverageFormat.QUESTA_UCDB:
            return self._validate_questa_ucdb(file_path)
        
        # Unknown format - assume valid if file exists and has size
        return True
    
    def _validate_verilator_dat(self, file_path: Path) -> bool:
        """Validate Verilator .dat file"""
        try:
            with open(file_path, 'rb') as f:
                # Read first few bytes
                header = f.read(100)
                
                # Verilator coverage files are binary
                # Check for reasonable header
                if len(header) < 10:
                    return False
                
                # Basic sanity check - should have some null bytes (binary)
                # but also some printable chars
                has_nulls = b'\x00' in header
                has_printable = any(32 <= b < 127 for b in header)
                
                return has_nulls or has_printable
        
        except Exception:
            return False
    
    def _validate_lcov(self, file_path: Path) -> bool:
        """Validate LCOV .info file"""
        try:
            with open(file_path, 'r') as f:
                content = f.read(1000)
            
            # LCOV files should have specific markers
            required_markers = ['TN:', 'SF:', 'end_of_record']
            has_marker = any(marker in content for marker in required_markers)
            
            return has_marker
        
        except Exception:
            return False
    
    def _validate_questa_ucdb(self, file_path: Path) -> bool:
        """Validate Questa UCDB file"""
        try:
            with open(file_path, 'rb') as f:
                header = f.read(100)
            
            # UCDB files are binary database files
            # Check for reasonable binary content
            return len(header) > 0 and b'\x00' in header
        
        except Exception:
            return False
    
    def _extract_test_name(
        self,
        file_path: Path,
        test_names: Optional[List[str]] = None,
    ) -> Optional[str]:
        """
        Extract test name from file path
        
        Args:
            file_path: Coverage file path
            test_names: Known test names to match against
        
        Returns:
            Test name or None
        """
        filename = file_path.stem  # Name without extension
        
        # If we have known test names, try to match
        if test_names:
            for test_name in test_names:
                if test_name in filename:
                    return test_name
        
        # Try common patterns
        patterns = [
            r'coverage_(.+)',
            r'(.+)_coverage',
            r'cov_(.+)',
            r'(.+)_cov',
            r'(.+)\.cov',
        ]
        
        for pattern in patterns:
            match = re.match(pattern, filename)
            if match:
                candidate = match.group(1)
                # Clean up the candidate
                candidate = candidate.replace('_', '.')
                return candidate
        
        # If filename doesn't match common patterns, it might be aggregate
        return None
    
    def _determine_primary_format(
        self,
        coverage_files: List[CoverageFile]
    ) -> CoverageFormat:
        """
        Determine primary coverage format
        
        Args:
            coverage_files: List of coverage files
        
        Returns:
            Primary format
        """
        if not coverage_files:
            return CoverageFormat.UNKNOWN
        
        # Count formats
        format_counts = {}
        for cov_file in coverage_files:
            format_counts[cov_file.format] = format_counts.get(cov_file.format, 0) + 1
        
        # Return most common format
        primary = max(format_counts.items(), key=lambda x: x[1])
        return primary[0]
    
    def _is_per_test_coverage(
        self,
        coverage_files: List[CoverageFile]
    ) -> bool:
        """
        Determine if coverage is per-test or aggregate
        
        Args:
            coverage_files: List of coverage files
        
        Returns:
            True if per-test coverage
        """
        # If we have test names for coverage files, it's per-test
        files_with_tests = sum(1 for f in coverage_files if f.test_name is not None)
        
        # If more than half have test names, consider it per-test
        if len(coverage_files) > 0:
            ratio = files_with_tests / len(coverage_files)
            return ratio > 0.5
        
        return False


class CoverageOrganizer:
    """
    Organizes coverage files by test and merges information
    """
    
    def __init__(self, output_dir: Path):
        """
        Initialize organizer
        
        Args:
            output_dir: Output directory for organized coverage
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
    
    def organize_by_test(
        self,
        coverage_info: CoverageInfo,
    ) -> CoverageInfo:
        """
        Organize coverage files by test name
        
        Args:
            coverage_info: Coverage info with files
        
        Returns:
            Updated CoverageInfo with organized paths
        """
        organized_files = []
        
        for cov_file in coverage_info.files:
            # Determine destination
            if cov_file.test_name:
                dest_dir = self.output_dir / "per_test"
                dest_name = f"{cov_file.test_name}{Path(cov_file.file_path).suffix}"
            else:
                dest_dir = self.output_dir / "aggregate"
                dest_name = Path(cov_file.file_path).name
            
            dest_dir.mkdir(parents=True, exist_ok=True)
            dest_path = dest_dir / dest_name
            
            # Copy or move file
            try:
                import shutil
                shutil.copy2(cov_file.file_path, dest_path)
                
                # Update file path
                cov_file.file_path = str(dest_path)
                organized_files.append(cov_file)
            
            except Exception:
                # If copy fails, keep original
                organized_files.append(cov_file)
        
        coverage_info.files = organized_files
        return coverage_info
    
    def merge_coverage_files(
        self,
        coverage_files: List[CoverageFile],
        output_name: str = "merged_coverage",
    ) -> Optional[Path]:
        """
        Merge multiple coverage files
        
        Note: This is a placeholder. Actual merging requires
        format-specific tools (verilator_coverage, lcov, etc.)
        
        Args:
            coverage_files: Files to merge
            output_name: Output file name
        
        Returns:
            Path to merged file or None
        """
        if not coverage_files:
            return None
        
        # Get primary format
        primary_format = coverage_files[0].format
        
        # Check all files are same format
        if not all(f.format == primary_format for f in coverage_files):
            # Can't merge different formats
            return None
        
        output_path = self.output_dir / f"{output_name}{self._get_extension(primary_format)}"
        
        # Format-specific merging would go here
        # For now, just return path where merged file would be
        
        return output_path
    
    def _get_extension(self, format: CoverageFormat) -> str:
        """Get file extension for format"""
        extensions = {
            CoverageFormat.VERILATOR_DAT: '.dat',
            CoverageFormat.QUESTA_UCDB: '.ucdb',
            CoverageFormat.LCOV: '.info',
            CoverageFormat.GCOV: '.gcda',
        }
        return extensions.get(format, '.dat')


class CoverageValidator:
    """
    Validates coverage completeness and quality
    """
    
    @staticmethod
    def validate_coverage_info(
        coverage_info: CoverageInfo,
        expected_tests: Optional[List[str]] = None,
    ) -> Tuple[bool, List[str]]:
        """
        Validate coverage information
        
        Args:
            coverage_info: Coverage info to validate
            expected_tests: Expected test names
        
        Returns:
            Tuple of (is_valid, list_of_issues)
        """
        issues = []
        
        # Check if any files found
        if not coverage_info.files:
            issues.append("No coverage files found")
            return False, issues
        
        # Check for invalid files
        invalid_files = [f for f in coverage_info.files if not f.valid]
        if invalid_files:
            issues.append(f"Found {len(invalid_files)} invalid coverage files")
        
        # Check if expected tests have coverage
        if expected_tests and coverage_info.per_test:
            covered_tests = {f.test_name for f in coverage_info.files if f.test_name}
            missing_tests = set(expected_tests) - covered_tests
            
            if missing_tests:
                issues.append(
                    f"Missing coverage for {len(missing_tests)} tests: "
                    f"{', '.join(list(missing_tests)[:5])}"
                )
        
        # Check for empty files
        empty_files = [f for f in coverage_info.files if f.size_bytes == 0]
        if empty_files:
            issues.append(f"Found {len(empty_files)} empty coverage files")
        
        # Check for unknown formats
        unknown_files = [
            f for f in coverage_info.files
            if f.format == CoverageFormat.UNKNOWN
        ]
        if unknown_files:
            issues.append(f"Found {len(unknown_files)} files with unknown format")
        
        is_valid = len(issues) == 0
        return is_valid, issues
    
    @staticmethod
    def check_coverage_completeness(
        coverage_info: CoverageInfo,
        test_results: List[Any],  # List[TestResult]
    ) -> Tuple[bool, List[str]]:
        """
        Check if coverage is complete for all passed tests
        
        Args:
            coverage_info: Coverage info
            test_results: Test results
        
        Returns:
            Tuple of (is_complete, list_of_issues)
        """
        issues = []
        
        # Get passed tests
        from ..models import TestOutcome
        passed_tests = [
            r.name for r in test_results
            if r.outcome == TestOutcome.PASSED
        ]
        
        if not passed_tests:
            return True, []  # No passed tests, nothing to check
        
        # Check coverage
        if coverage_info.per_test:
            covered_tests = {f.test_name for f in coverage_info.files if f.test_name}
            missing = set(passed_tests) - covered_tests
            
            if missing:
                issues.append(
                    f"Missing coverage for {len(missing)} passed tests"
                )
        
        else:
            # Aggregate coverage - just check if we have any
            if not coverage_info.files:
                issues.append("No aggregate coverage found")
        
        is_complete = len(issues) == 0
        return is_complete, issues


# Utility functions

def locate_coverage(
    working_dir: Path,
    search_dirs: Optional[List[Path]] = None,
    test_names: Optional[List[str]] = None,
) -> CoverageInfo:
    """
    Convenience function to locate coverage
    
    Args:
        working_dir: Working directory
        search_dirs: Additional directories to search
        test_names: Known test names
    
    Returns:
        CoverageInfo
    """
    locator = CoverageLocator(working_dir)
    return locator.locate_all(search_dirs, test_names)


def validate_coverage(
    coverage_info: CoverageInfo,
    expected_tests: Optional[List[str]] = None,
) -> Tuple[bool, List[str]]:
    """
    Convenience function to validate coverage
    
    Args:
        coverage_info: Coverage info
        expected_tests: Expected test names
    
    Returns:
        Tuple of (is_valid, list_of_issues)
    """
    return CoverageValidator.validate_coverage_info(coverage_info, expected_tests)


# Example usage and testing
if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python coverage_locator.py <working_dir>")
        sys.exit(1)
    
    working_dir = Path(sys.argv[1])
    
    print(f"Searching for coverage in: {working_dir}")
    print("=" * 60)
    
    # Locate coverage
    locator = CoverageLocator(working_dir)
    coverage_info = locator.locate_all()
    
    print(f"Found {len(coverage_info.files)} coverage files")
    print(f"Primary format: {coverage_info.primary_format.value}")
    print(f"Per-test coverage: {coverage_info.per_test}")
    print()
    
    # List files
    for cov_file in coverage_info.files:
        status = "✓" if cov_file.valid else "✗"
        test = cov_file.test_name or "aggregate"
        size_kb = cov_file.size_bytes / 1024
        
        print(f"{status} {test:30} {cov_file.format.value:15} {size_kb:8.2f} KB")
        print(f"   {cov_file.file_path}")
    
    # Validate
    print()
    print("=" * 60)
    print("Validation:")
    is_valid, issues = validate_coverage(coverage_info)
    
    if is_valid:
        print("✓ Coverage is valid")
    else:
        print("✗ Coverage has issues:")
        for issue in issues:
            print(f"  - {issue}")
