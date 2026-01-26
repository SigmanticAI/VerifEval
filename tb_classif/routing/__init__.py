"""
Routing Decision Module
=======================

Determines execution track and simulator selection based on
detected testbench type and quality gate results.

Tracks:
- Track A: CocoTB/PyUVM (Python-based testbenches)
- Track B: VUnit/HDL (SystemVerilog/VHDL with VUnit orchestration)
- Track C: Commercial simulator required (UVM-SV)

Components:
- RoutingEngine: Main routing decision logic
- ConfidenceScorer: Calculates detection confidence
- SimulatorSelector: Selects appropriate simulator

Usage:
    from step2_classify_route.routing import RoutingEngine
    
    engine = RoutingEngine(root_dir)
    routing = engine.create_routing_decision(
        detection_results=detections,
        dut_files=dut_files,
        tb_files=tb_files
    )
"""

from .engine import RoutingEngine, UVMHandler
from .confidence import ConfidenceScorer
from .simulator_selector import SimulatorSelector

__all__ = [
    "RoutingEngine",
    "UVMHandler",
    "ConfidenceScorer",
    "SimulatorSelector",
]
