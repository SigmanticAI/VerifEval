"""
Test Discovery Module
=====================

Discovers and enumerates test cases from various testbench types:
- UVM tests (SystemVerilog UVM classes)
- VUnit tests (VUnit test benches and tests)
- CocoTB tests (Python @cocotb.test decorators)

Main Components:
- UVMTestDiscovery: Discovers UVM test classes
- VUnitTestDiscovery: Discovers VUnit tests via VUnit API
- CocoTBTestDiscovery: Discovers CocoTB test functions

Usage:
    from step3_build_orchestrate.discovery import UVMTestDiscovery
    
    discovery = UVMTestDiscovery(submission_dir)
    tests = discovery.discover(tb_files)
    
    for test in tests:
        print(f"Found UVM test: {test.name}")
"""

from .base import BaseTestDiscovery, DiscoveryResult
from .uvm_discovery import UVMTestDiscovery, UVMTestInfo, UVMComponentInfo
from .vunit_discovery import VUnitTestDiscovery
from .cocotb_discovery import CocoTBTestDiscovery

__all__ = [
    # Base
    "BaseTestDiscovery",
    "DiscoveryResult",
    # UVM
    "UVMTestDiscovery",
    "UVMTestInfo",
    "UVMComponentInfo",
    # VUnit
    "VUnitTestDiscovery",
    # CocoTB
    "CocoTBTestDiscovery",
]
