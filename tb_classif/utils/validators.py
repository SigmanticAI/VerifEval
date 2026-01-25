"""
Validation utilities for files and project structure
"""
from pathlib import Path
from typing import List, Dict, Tuple, Optional
import re


class FileValidator:
    """Validates individual files"""
    
    @staticmethod
    def validate_file_exists(file_path: Path) -> Tuple[bool, str]:
        """Check if file exists and is readable"""
        if not file_path.exists():
            return False, f"File does not exist: {file_path}"
        
        if not file_path.is_file():
            return False, f"Path is not a file: {file_path}"
        
        try:
            with open(file_path, 'r') as f:
                f.read(1)  # Try to read one character
            return True, ""
        except PermissionError:
            return False, f"Permission denied: {file_path}"
        except Exception as e:
            return False, f"Cannot read file: {file_path} - {str(e)}"
    
    @staticmethod
    def validate_hdl_syntax_basic(file_path: Path) -> Tuple[bool, List[str]]:
        """
        Basic syntax validation for HDL files
        Checks for:
        - Balanced parentheses, brackets, begin/end
        - Module/entity declaration
        - Basic structure
        """
        issues = []
        
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
        except Exception as e:
            return False, [f"Cannot read file: {str(e)}"]
        
        # Check for module/entity declaration
        if file_path.suffix in ['.sv', '.v']:
            if not re.search(r'\bmodule\s+\w+', content):
                issues.append("No module declaration found")
        elif file_path.suffix in ['.vhd', '.vhdl']:
            if not re.search(r'\bentity\s+\w+\s+is\b', content, re.IGNORECASE):
                issues.append("No entity declaration found")
        
        # Check balanced constructs
        balance_checks = [
            ('(', ')'),
            ('[', ']'),
            ('{', '}'),
        ]
        
        for open_char, close_char in balance_checks:
            open_count = content.count(open_char)
            close_count = content.count(close_char)
            if open_count != close_count:
                issues.append(
                    f"Unbalanced {open_char}{close_char}: "
                    f"{open_count} opening, {close_count} closing"
                )
        
        # Check begin/end balance (SystemVerilog/Verilog)
        if file_path.suffix in ['.sv', '.v']:
            begin_count = len(re.findall(r'\bbegin\b', content))
            end_count = len(re.findall(r'\bend\b', content))
            if begin_count != end_count:
                issues.append(
                    f"Unbalanced begin/end: {begin_count} begin, {end_count} end"
                )
        
        return len(issues) == 0, issues
    
    @staticmethod
    def validate_python_syntax_basic(file_path: Path) -> Tuple[bool, List[str]]:
        """Basic Python syntax validation"""
        issues = []
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                code = f.read()
            
            # Try to compile (syntax check only, doesn't execute)
            compile(code, str(file_path), 'exec')
            return True, []
        except SyntaxError as e:
            issues.append(f"Syntax error at line {e.lineno}: {e.msg}")
            return False, issues
        except Exception as e:
            issues.append(f"Validation error: {str(e)}")
            return False, issues


class ProjectValidator:
    """Validates entire project structure"""
    
    def __init__(self, root_dir: Path):
        self.root_dir = Path(root_dir)
        self.file_validator = FileValidator()
    
    def validate_project(
        self,
        dut_files: List[Path],
        tb_files: List[Path]
    ) -> Dict[str, any]:
        """
        Comprehensive project validation
        
        Returns:
            Dictionary with validation results
        """
        results = {
            'valid': True,
            'errors': [],
            'warnings': [],
            'file_validations': {},
            'statistics': {
                'total_files': len(dut_files) + len(tb_files),
                'dut_files': len(dut_files),
                'tb_files': len(tb_files),
                'files_validated': 0,
                'files_with_issues': 0
            }
        }
        
        # Validate file existence
        all_files = dut_files + tb_files
        for file_path in all_files:
            exists, msg = self.file_validator.validate_file_exists(file_path)
            if not exists:
                results['errors'].append(msg)
                results['valid'] = False
                results['file_validations'][str(file_path)] = {
                    'exists': False,
                    'readable': False,
                    'issues': [msg]
                }
            else:
                results['statistics']['files_validated'] += 1
                results['file_validations'][str(file_path)] = {
                    'exists': True,
                    'readable': True,
                    'issues': []
                }
        
        # Check for empty file lists
        if not dut_files:
            results['errors'].append("No DUT files found")
            results['valid'] = False
        
        if not tb_files:
            results['errors'].append("No testbench files found")
            results['valid'] = False
        
        # Validate HDL syntax (basic)
        for file_path in dut_files + tb_files:
            if file_path.suffix in ['.sv', '.v', '.vhd', '.vhdl']:
                valid, issues = self.file_validator.validate_hdl_syntax_basic(file_path)
                if not valid:
                    results['warnings'].extend([
                        f"{file_path}: {issue}" for issue in issues
                    ])
                    results['file_validations'][str(file_path)]['issues'].extend(issues)
                    results['statistics']['files_with_issues'] += 1
            
            elif file_path.suffix == '.py':
                valid, issues = self.file_validator.validate_python_syntax_basic(file_path)
                if not valid:
                    results['errors'].extend([
                        f"{file_path}: {issue}" for issue in issues
                    ])
                    results['valid'] = False
                    results['file_validations'][str(file_path)]['issues'].extend(issues)
                    results['statistics']['files_with_issues'] += 1
        
        return results
    
    def validate_file_paths(self, file_list: List[str]) -> Tuple[bool, List[str]]:
        """Validate that file paths are valid and within project"""
        issues = []
        
        for file_str in file_list:
            file_path = Path(file_str)
            
            # Check if absolute path is within project
            if file_path.is_absolute():
                try:
                    file_path.relative_to(self.root_dir)
                except ValueError:
                    issues.append(
                        f"File outside project directory: {file_path}"
                    )
            
            # Check for suspicious paths
            if '..' in file_path.parts:
                issues.append(
                    f"Suspicious path with '..': {file_path}"
                )
        
        return len(issues) == 0, issues
    
    def check_common_issues(self) -> List[str]:
        """Check for common project issues"""
        warnings = []
        
        # Check for mixed case filenames (can cause issues on different OS)
        all_files = list(self.root_dir.rglob('*'))
        stems = [f.stem for f in all_files if f.is_file()]
        
        # Check for duplicates with different cases
        lowercase_stems = [s.lower() for s in stems]
        if len(lowercase_stems) != len(set(lowercase_stems)):
            warnings.append(
                "Warning: Files with same name but different cases detected. "
                "This may cause issues on case-insensitive filesystems."
            )
        
        # Check for spaces in filenames
        files_with_spaces = [f for f in all_files if ' ' in f.name]
        if files_with_spaces:
            warnings.append(
                f"Warning: {len(files_with_spaces)} files contain spaces in filenames. "
                "Consider using underscores instead."
            )
        
        # Check for very long paths
        long_paths = [f for f in all_files if len(str(f)) > 200]
        if long_paths:
            warnings.append(
                f"Warning: {len(long_paths)} files have very long paths (>200 chars)"
            )
        
        return warnings
