"""
UVM SystemVerilog detector
"""
from pathlib import Path
from typing import Optional

from .base import BaseDetector
from ..models import DetectionResult, TBType, Language
import re

class UVMSVDetector(BaseDetector):
    """Detects traditional SystemVerilog UVM testbenches"""
    
    def __init__(self):
        super().__init__()
        self.tb_type = TBType.UVM_SV
        self.language = Language.SYSTEMVERILOG
        self.file_extensions = ['.sv', '.svh']
        self.detection_patterns = [
            r'import\s+uvm_pkg\s*::',
            r'`include\s+["\']uvm_macros\.svh["\']',
            r'class\s+\w+\s+extends\s+uvm_test',
            r'class\s+\w+\s+extends\s+uvm_env',
            r'class\s+\w+\s+extends\s+uvm_agent',
            r'class\s+\w+\s+extends\s+uvm_driver',
            r'class\s+\w+\s+extends\s+uvm_monitor',
            r'class\s+\w+\s+extends\s+uvm_scoreboard',
            r'`uvm_component_utils',
            r'`uvm_object_utils',
            r'uvm_config_db',
            r'run_test\s*\('
        ]
    
    def detect(self, file_path: Path) -> Optional[DetectionResult]:
        """Detect UVM-SV testbench"""
        if file_path.suffix not in self.file_extensions:
            return None
        
        content = self.read_file_safe(file_path)
        if not content:
            return None
        
        # Look for UVM package import (strong indicator)
        has_uvm_import = bool(re.search(r'import\s+uvm_pkg', content))
        has_uvm_include = bool(re.search(r'`include\s+["\']uvm_macros\.svh["\']', content))
        
        match_count = self.count_pattern_matches(content, self.detection_patterns)
        
        if (has_uvm_import or has_uvm_include) and match_count >= 2:
            confidence = 0.95 if match_count >= 4 else 0.85
            
            return DetectionResult(
                tb_type=self.tb_type,
                confidence=confidence,
                files_detected=[str(file_path)],
                detection_method="pattern_matching",
                language=self.language,
                metadata={
                    "pattern_matches": match_count,
                    "has_uvm_import": has_uvm_import,
                    "has_uvm_macros": has_uvm_include,
                    "requires_commercial_sim": True,
                    "open_source_alternative": "pyuvm"
                }
            )
        
        return None
