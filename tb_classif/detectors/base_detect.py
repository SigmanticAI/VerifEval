"""
Base detector interface
"""
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Optional, List
import re

from ..models import DetectionResult, TBType, Language


class BaseDetector(ABC):
    """Base class for testbench type detectors"""
    
    def __init__(self):
        self.detection_patterns: List[str] = []
        self.file_extensions: List[str] = []
        self.tb_type: TBType = TBType.UNKNOWN
        self.language: Language = Language.SYSTEMVERILOG
    
    @abstractmethod
    def detect(self, file_path: Path) -> Optional[DetectionResult]:
        """
        Detect if file matches this TB type
        Returns DetectionResult if detected, None otherwise
        """
        pass
    
    def read_file_safe(self, file_path: Path, max_lines: int = 200) -> Optional[str]:
        """Safely read file content with limits"""
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                lines = []
                for i, line in enumerate(f):
                    if i >= max_lines:
                        break
                    lines.append(line)
                return ''.join(lines)
        except Exception as e:
            print(f"Warning: Could not read {file_path}: {e}")
            return None
    
    def matches_patterns(self, content: str, patterns: List[str]) -> bool:
        """Check if content matches any of the patterns"""
        for pattern in patterns:
            if re.search(pattern, content, re.MULTILINE | re.IGNORECASE):
                return True
        return False
    
    def count_pattern_matches(self, content: str, patterns: List[str]) -> int:
        """Count how many patterns match"""
        count = 0
        for pattern in patterns:
            if re.search(pattern, content, re.MULTILINE | re.IGNORECASE):
                count += 1
        return count
