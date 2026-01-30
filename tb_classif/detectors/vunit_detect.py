"""
VUnit framework detector
"""
from pathlib import Path
from typing import Optional
import re

from .base import BaseDetector
from ..models import DetectionResult, TBType, Language


class VUnitDetector(BaseDetector):
    """Detects VUnit framework usage"""
    
    def __init__(self):
        super().__init__()
        self.tb_type = TBType.VUNIT
        self.file_extensions = ['.py', '.vhd', '.vhdl']
    
    def detect(self, file_path: Path) -> Optional[DetectionResult]:
        """Detect VUnit usage"""
        if file_path.suffix == '.py':
            return self._detect_vunit_python(file_path)
        elif file_path.suffix in ['.vhd', '.vhdl']:
            return self._detect_vunit_vhdl(file_path)
        return None
    
    def _detect_vunit_python(self, file_path: Path) -> Optional[DetectionResult]:
        """Detect VUnit Python run script"""
        content = self.read_file_safe(file_path)
        if not content:
            return None
        
        patterns = [
            r'from\s+vunit\s+import',
            r'import\s+VUnit',
            r'VUnit\.from_argv',
            r'VUnit\.from_args',
            r'\.add_library\s*\(',
            r'\.test_bench\s*\('
        ]
        
        match_count = self.count_pattern_matches(content, patterns)
        
        if match_count >= 2:
            return DetectionResult(
                tb_type=self.tb_type,
                confidence=0.95,
                files_detected=[str(file_path)],
                detection_method="vunit_python_runner",
                language=Language.PYTHON,
                metadata={
                    "is_runner_script": True,
                    "pattern_matches": match_count
                }
            )
        
        return None
    
    def _detect_vunit_vhdl(self, file_path: Path) -> Optional[DetectionResult]:
        """Detect VUnit VHDL testbench"""
        content = self.read_file_safe(file_path)
        if not content:
            return None
        
        patterns = [
            r'library\s+vunit_lib',
            r'use\s+vunit_lib\.',
            r'runner_cfg',
            r'test_runner_setup',
            r'test_runner_cleanup',
            r'run\s*\(\s*["\']'
        ]
        
        match_count = self.count_pattern_matches(content, patterns)
        
        if match_count >= 3:
            return DetectionResult(
                tb_type=self.tb_type,
                confidence=0.90,
                files_detected=[str(file_path)],
                detection_method="vunit_vhdl_testbench",
                language=Language.VHDL,
                metadata={
                    "is_vhdl_testbench": True,
                    "pattern_matches": match_count
                }
            )
        
        return None
