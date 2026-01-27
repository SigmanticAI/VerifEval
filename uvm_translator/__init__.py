"""
UVM-SV to Python/cocotb Translator Module.

This module provides LLM-based translation of traditional UVM SystemVerilog 
testbenches to Python-based verification using cocotb/pyuvm frameworks.

This enables open-source evaluation of UVM testbenches without commercial simulators.

Components:
- parser: Extract UVM components from SystemVerilog files
- analyzer: Analyze UVM testbench structure and dependencies
- translator: LLM-based translation engine
- templates: Python/cocotb templates for common UVM patterns
- validator: Validate generated Python code
"""

from .parser import UVMParser, UVMComponent, UVMComponentType
from .analyzer import UVMAnalyzer, UVMTestbenchStructure
from .translator import UVMTranslator, TranslationResult
from .validator import TranslationValidator, ValidationResult

__all__ = [
    'UVMParser',
    'UVMComponent', 
    'UVMComponentType',
    'UVMAnalyzer',
    'UVMTestbenchStructure',
    'UVMTranslator',
    'TranslationResult',
    'TranslationValidator',
    'ValidationResult',
]

__version__ = '1.0.0'

