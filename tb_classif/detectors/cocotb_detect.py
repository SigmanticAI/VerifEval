"""
CocoTB testbench detector
"""
from pathlib import Path
from typing import Optional

from .base import BaseDetector
from ..models import DetectionResult, TBType, Language


class CocoTBDetector(BaseDetector):
    """Detects CocoTB Python testbenches"""
    
    def __init__(self):
        super().__init__()
        self.tb_type = TBType.COCOTB
        self.language = Language.PYTHON
        self.file_extensions = ['.py']
        self.detection_patterns = [
            r'import\s+cocotb\b',
            r'from\s+cocotb\s+import',
            r'from\s+cocotb\.',
            r'@cocotb\.test\s*\(',
            r'@cocotb\.coroutine',
            r'cocotb\.triggers',
            r'cocotb\.clock'
        ]
    
    def detect(self, file_path: Path) -> Optional[DetectionResult]:
        """Detect CocoTB testbench"""
        if file_path.suffix not in self.file_extensions:
            return None
        
        content = self.read_file_safe(file_path)
        if not content:
            return None
        
        match_count = self.count_pattern_matches(content, self.detection_patterns)
        
        if match_count >= 2:  # Need at least 2 cocotb indicators
            # Strong confidence if has @cocotb.test decorator
            confidence = 0.95 if '@cocotb.test' in content else 0.85
            
            return DetectionResult(
                tb_type=self.tb_type,
                confidence=confidence,
                files_detected=[str(file_path)],
                detection_method="pattern_matching",
                language=self.language,
                metadata={
                    "pattern_matches": match_count,
                    "has_test_decorator": '@cocotb.test' in content
                }
            )
        
        return None
