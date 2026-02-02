"""
Simulator Configuration Module
==============================

This module provides simulator-specific configuration and management:
- Questa/ModelSim (commercial, UVM support)
- Verilator (open source, fast simulation)
- GHDL (open source, VHDL)

Main Components:
- BaseSimulator: Abstract base class for simulators
- QuestaSimulator: Questa/ModelSim integration
- LicenseManager: License detection and validation

Usage:
    from step3_build_orchestrate.simulators import QuestaSimulator
    
    questa = QuestaSimulator(config)
    if questa.is_available():
        questa.configure_vunit(vu)
"""

from .base import BaseSimulator, SimulatorCapabilities
from .questa import QuestaSimulator, QuestaInstallation
from .license import (
    LicenseManager,
    LicenseCheckResult,
    FlexLMLicenseChecker,
)

# Verilator and GHDL will be added
# from .verilator import VerilatorSimulator
# from .ghdl import GHDLSimulator

__all__ = [
    # Base
    "BaseSimulator",
    "SimulatorCapabilities",
    # Questa
    "QuestaSimulator",
    "QuestaInstallation",
    # License
    "LicenseManager",
    "LicenseCheckResult",
    "FlexLMLicenseChecker",
]
