"""
Verilator Simulator Integration (Skeleton)
==========================================

Full implementation coming in next iteration.
"""

from typing import Optional, Dict, Any, List
from .base import BaseSimulator, SimulatorCapabilities, SimulatorVersion, SimulatorFeature
from ..models import VerilatorConfig


class VerilatorSimulator(BaseSimulator):
    """Verilator simulator integration - SKELETON"""
    
    def __init__(self, config: Optional[VerilatorConfig] = None):
        super().__init__()
        self.config = config or VerilatorConfig()
    
    def get_name(self) -> str:
        return "Verilator"
    
    def detect_installation(self) -> bool:
        # TODO: Implement
        import shutil
        return shutil.which("verilator") is not None
    
    def get_version(self) -> Optional[SimulatorVersion]:
        # TODO: Implement
        return None
    
    def get_capabilities(self) -> SimulatorCapabilities:
        return SimulatorCapabilities(
            supported_features={
                SimulatorFeature.SYSTEMVERILOG,
                SimulatorFeature.VERILOG,
                SimulatorFeature.COVERAGE_LINE,
                SimulatorFeature.COVERAGE_TOGGLE,
                SimulatorFeature.WAVEFORM_VCD,
                SimulatorFeature.COCOTB_INTEGRATION,
            },
            vunit_simulator_name="",  # VUnit doesn't directly support Verilator
            supported_languages=["systemverilog", "verilog"],
        )
    
    def configure_vunit(self, vu: Any) -> None:
        # TODO: Implement (Verilator requires special handling with VUnit)
        pass
    
    def get_compile_options(self) -> Dict[str, List[str]]:
        return {}
    
    def get_sim_options(self) -> Dict[str, List[str]]:
        return {}
