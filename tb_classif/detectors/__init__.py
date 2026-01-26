"""
Testbench Type Detectors
========================

This module contains detectors for identifying testbench types:

- CocoTBDetector: Detects Python CocoTB testbenches
- PyUVMDetector: Detects PyUVM (Python UVM) testbenches  
- UVMSVDetector: Detects SystemVerilog UVM testbenches
- VUnitDetector: Detects VUnit framework usage
- HDLDetector: Generic HDL testbench detection (fallback)

Detection Priority (most specific first):
1. PyUVM (Python UVM implementation)
2. CocoTB (Python testbench)
3. UVM-SV (SystemVerilog UVM - requires commercial sim)
4. VUnit (Python + VHDL/SV framework)
5. Generic HDL (plain SystemVerilog/VHDL)

Usage:
    from step2_classify_route.detectors import CocoTBDetector
    
    detector = CocoTBDetector()
    result = detector.detect(Path("test_adder.py"))
    if result:
        print(f"Detected: {result.tb_type}")
"""

from .base import BaseDetector
from .cocotb_detector import CocoTBDetector
from .pyuvm_detector import PyUVMDetector
from .uvm_sv_detector import UVMSVDetector
from .vunit_detector import VUnitDetector
from .hdl_detector import HDLDetector

__all__ = [
    "BaseDetector",
    "CocoTBDetector",
    "PyUVMDetector",
    "UVMSVDetector",
    "VUnitDetector",
    "HDLDetector",
]

# Detector registry in priority order
DETECTOR_REGISTRY = [
    PyUVMDetector,
    CocoTBDetector,
    UVMSVDetector,
    VUnitDetector,
    HDLDetector,
]
