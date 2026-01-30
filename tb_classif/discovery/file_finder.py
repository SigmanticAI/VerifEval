"""
File discovery and categorization
"""
from pathlib import Path
from typing import List, Dict, Set
import re

from ..models import ProjectConfig


class FileFinder:
    """Discovers and categorizes project files"""
    
    def __init__(self, root_dir: Path, config: ProjectConfig):
        self.root_dir = Path(root_dir)
        self.config = config
        
        # File extension mappings
        self.hdl_extensions = {'.sv', '.v', '.vhd', '.vhdl', '.svh'}
        self.python_extensions = {'.py'}
        self.all_extensions = self.hdl_extensions | self.python_extensions
    
    def find_dut_files(self) -> List[Path]:
        """Find DUT (Design Under Test) files"""
        dut_files = []
        
        # Search designated DUT directories
        for dut_dir_name in self.config.dut_directories:
            dut_dir = self.root_dir / dut_dir_name
            if dut_dir.exists() and dut_dir.is_dir():
                dut_files.extend(self._find_hdl_files(dut_dir))
        
        # If no DUT directories found, search root but exclude TB directories
        if not dut_files:
            tb_dir_names = set(self.config.tb_directories)
            for ext in self.hdl_extensions:
                for file_path in self.root_dir.rglob(f'*{ext}'):
                    # Exclude files in testbench directories
                    if not any(tb_dir in file_path.parts for tb_dir in tb_dir_names):
                        # Exclude files with 'tb' or 'test' in name
                        if not self._is_testbench_file(file_path):
                            dut_files.append(file_path)
        
        return sorted(set(dut_files))
    
    def find_testbench_files(self) -> List[Path]:
        """Find testbench files"""
        tb_files = []
        
        # Search designated TB directories
        for tb_dir_name in self.config.tb_directories:
            tb_dir = self.root_dir / tb_dir_name
            if tb_dir.exists() and tb_dir.is_dir():
                # Find both HDL and Python files
                tb_files.extend(self._find_all_relevant_files(tb_dir))
        
        # Also search root for files with 'test' or 'tb' in name
        if not tb_files:
            for ext in self.all_extensions:
                for file_path in self.root_dir.rglob(f'*{ext}'):
                    if self._is_testbench_file(file_path):
                        tb_files.append(file_path)
        
        return sorted(set(tb_files))
    
    def find_all_project_files(self) -> Dict[str, List[Path]]:
        """Find all project files categorized"""
        return {
            'dut': self.find_dut_files(),
            'testbench': self.find_testbench_files(),
            'python': self._find_python_files(self.root_dir),
            'systemverilog': self._find_sv_files(self.root_dir),
            'vhdl': self._find_vhdl_files(self.root_dir)
        }
    
    def _find_hdl_files(self, directory: Path) -> List[Path]:
        """Find HDL files in directory"""
        files = []
        for ext in self.hdl_extensions:
            files.extend(directory.rglob(f'*{ext}'))
        return files
    
    def _find_all_relevant_files(self, directory: Path) -> List[Path]:
        """Find all relevant files (HDL + Python)"""
        files = []
        for ext in self.all_extensions:
            files.extend(directory.rglob(f'*{ext}'))
        return files
    
    def _find_python_files(self, directory: Path) -> List[Path]:
        """Find Python files"""
        return list(directory.rglob('*.py'))
    
    def _find_sv_files(self, directory: Path) -> List[Path]:
        """Find SystemVerilog files"""
        files = []
        for ext in ['.sv', '.v', '.svh']:
            files.extend(directory.rglob(f'*{ext}'))
        return files
    
    def _find_vhdl_files(self, directory: Path) -> List[Path]:
        """Find VHDL files"""
        files = []
        for ext in ['.vhd', '.vhdl']:
            files.extend(directory.rglob(f'*{ext}'))
        return files
    
    def _is_testbench_file(self, file_path: Path) -> bool:
        """Check if file appears to be a testbench"""
        name_lower = file_path.stem.lower()
        
        # Check for common TB naming patterns
        tb_patterns = [
            r'.*tb.*',
            r'.*test.*',
            r'.*_tb$',
            r'^tb_.*',
            r'.*_test$',
            r'^test_.*',
            r'.*testbench.*'
        ]
        
        for pattern in tb_patterns:
            if re.match(pattern, name_lower):
                return True
        
        return False
    
    def validate_files_exist(self, file_list: List[Path]) -> Dict[str, bool]:
        """Validate that files exist and are readable"""
        results = {}
        for file_path in file_list:
            full_path = self.root_dir / file_path if not file_path.is_absolute() else file_path
            results[str(file_path)] = full_path.exists() and full_path.is_file()
        return results
