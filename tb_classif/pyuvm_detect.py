"""
PyUVM testbench detector
"""
from pathlib import Path
from typing import Optional

from .base import BaseDetector
from ..models import DetectionResult, TBType, Language


class PyUVMDetector(BaseDetector):
    """Detects PyUVM (Python UVM) testbenches"""
    
    def __init__(self):
        super().__init__()
        self.tb_type = TBType.PYUVM
        self.language = Language.PYTHON
        self.file_extensions = ['.py']
        self.detection_patterns = [
            r'from\s+pyuvm\s+import',
            r'import\s+pyuvm',
            r'class\s+\w+\s*\(\s*uvm_component\s*\)',
            r'class\s+\w+\s*\(\s*uvm_test\s*\)',
            r'class\s+\w+\s*\(\s*uvm_env\s*\)',
            r'class\s+\w+\s*\(\s*uvm_agent\s*\)',
            r'class\s+\w+\s*\(\s*uvm_driver\s*\)',
            r'class\s+\w+\s*\(\s*uvm_monitor\s*\)',
            r'uvm_root\s*\(',
            r'ConfigDB\.'
        ]
    
    def detect(self, file_path: Path) -> Optional[DetectionResult]:
        """Detect PyUVM testbench"""
        if file_path.suffix not in self.file_extensions:
            return None
        
        content = self.read_file_safe(file_path)
        if not content:
            return None
        
        match_count = self.count_pattern_matches(content, self.detection_patterns)
        
        if match_count >= 2:  # Need pyuvm import + UVM class
            confidence = 0.90 if match_count >= 3 else 0.75
            
            return DetectionResult(
                tb_type=self.tb_type,
                confidence=confidence,
                files_detected=[str(file_path)],
                detection_method="pattern_matching",
                language=self.language,
                metadata={
                    "pattern_matches": match_count,
                    "is_uvm_framework": True,
                    "cocotb_based": "import cocotb" in content or "from cocotb" in content
                }
            )
        
        return None
