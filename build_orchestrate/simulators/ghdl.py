"""
GHDL Simulator Integration (Skeleton)
=====================================

Full implementation coming in next iteration.
"""

from typing import Optional, Dict, Any, List
from .base import BaseSimulator, SimulatorCapabilities, SimulatorVersion, SimulatorFeature
from ..models import GHDLConfig


class GHDLSimulator(BaseSimulator):
    """GHDL simulator integration - SKELETON"""
    
    def __init__(self, config: Optional[GHDLConfig] = None):
        super().__init__()
        self.config = config or GHDLConfig()
    
    def get_name(self) -> str:
        return "GHDL"
    
    def detect_installation(self) -> bool:
        import shutil
        return shutil.which("ghdl") is not None
    
    def get_version(self) -> Optional[SimulatorVersion]:
        # TODO: Implement
        return None
    
    def get_capabilities(self) -> SimulatorCapabilities:
        return SimulatorCapabilities(
            supported_features={
                SimulatorFeature.VHDL,
                SimulatorFeature.WAVEFORM_VCD,
                SimulatorFeature.WAVEFORM_FST,
            },
            vunit_simulator_name="ghdl",
            supported_languages=["vhdl"],
        )
    
    def configure_vunit(self, vu: Any) -> None:
        # GHDL is natively supported by VUnit
        vu.set_compile_option("ghdl.a_flags", [f"--std={self.config.std}"])
    
    def get_compile_options(self) -> Dict[str, List[str]]:
        return {
            "ghdl.a_flags": [f"--std={self.config.std}"]
        }
    
    def get_sim_options(self) -> Dict[str, List[str]]:
        return {}
