"""
Generic HDL testbench detector for plain SV/VHDL
"""
from pathlib import Path
from typing import Optional
import re

from .base_detect import BaseDetector
from ..models import DetectionResult, TBType, Language


class HDLDetector(BaseDetector):
    """Detects plain SystemVerilog and VHDL testbenches"""
    
    def detect(self, file_path: Path) -> Optional[DetectionResult]:
        """Detect plain HDL testbench"""
        if file_path.suffix in ['.sv', '.v']:
            return self._detect_systemverilog_tb(file_path)
        elif file_path.suffix in ['.vhd', '.vhdl']:
            return self._detect_vhdl_tb(file_path)
        return None
    
    def _detect_systemverilog_tb(self, file_path: Path) -> Optional[DetectionResult]:
        """Detect SystemVerilog testbench"""
        content = self.read_file_safe(file_path)
        if not content:
            return None
        
        # Look for testbench indicators
        tb_patterns = [
            r'module\s+\w*tb\w*',
            r'module\s+\w*test\w*',
            r'\bprogram\s+\w+',
            r'\binitial\s+begin',
            r'\$display',
            r'\$monitor',
            r'\$finish',
            r'\$stop',
            r'`timescale',
            r'#\d+',  # Time delays
        ]
        
        match_count = self.count_pattern_matches(content, tb_patterns)
        
        # Must have module/program + at least 2 other TB indicators
        has_module = bool(re.search(r'\b(module|program)\s+\w+', content))
        has_tb_name = bool(re.search(r'(module|program)\s+\w*(tb|test)\w*', content, re.IGNORECASE))
        
        if has_module and match_count >= 3:
            confidence = 0.80 if has_tb_name else 0.60
            
            return DetectionResult(
                tb_type=TBType.SYSTEMVERILOG,
                confidence=confidence,
                files_detected=[str(file_path)],
                detection_method="hdl_pattern_matching",
                language=Language.SYSTEMVERILOG,
                metadata={
                    "pattern_matches": match_count,
                    "has_tb_naming": has_tb_name
                }
            )
        
        return None
    
    def _detect_vhdl_tb(self, file_path: Path) -> Optional[DetectionResult]:
        """Detect VHDL testbench"""
        content = self.read_file_safe(file_path)
        if not content:
            return None
        
        tb_patterns = [
            r'entity\s+\w*tb\w*\s+is',
            r'entity\s+\w*test\w*\s+is',
            r'architecture\s+\w+\s+of\s+\w*tb',
            r'\bprocess\b',
            r'\bwait\s+for\s+\d+',
            r'\breport\s+',
            r'\bassert\s+',
            r'end\s+process',
        ]
        
        match_count = self.count_pattern_matches(content, tb_patterns)
        
        has_entity = bool(re.search(r'\bentity\s+\w+\s+is\b', content, re.IGNORECASE))
        has_tb_name = bool(re.search(r'entity\s+\w*(tb|test)\w*\s+is', content, re.IGNORECASE))
        
        if has_entity and match_count >= 3:
            confidence = 0.80 if has_tb_name else 0.60
            
            return DetectionResult(
                tb_type=TBType.VHDL,
                confidence=confidence,
                files_detected=[str(file_path)],
                detection_method="hdl_pattern_matching",
                language=Language.VHDL,
                metadata={
                    "pattern_matches": match_count,
                    "has_tb_naming": has_tb_name
                }
            )
        
        return None
