"""
Questa Simulator Integration Module.

This module provides integration with Siemens Questa/QuestaSim for:
- UVM testbench simulation and evaluation
- SystemVerilog Assertions (SVA) formal verification
- Functional coverage collection and analysis

Requires:
- Questa license (configured via QUESTA_LICENSE environment variable or config)
- Questa tools installed (vlib, vlog, vopt, vsim, vcover)
"""

from .config import QuestaConfig, get_config, set_license
from .simulator import QuestaSimulator
from .coverage import QuestaCoverageAnalyzer
from .formal import QuestaFormalChecker

__all__ = [
    'QuestaConfig',
    'get_config',
    'set_license',
    'QuestaSimulator',
    'QuestaCoverageAnalyzer',
    'QuestaFormalChecker',
]

__version__ = '1.0.0'

