"""
Quality Gate Module
===================

Static analysis and linting for HDL files.

Supported Tools:
- Verible: SystemVerilog/Verilog linting and syntax checking
- GHDL: VHDL syntax checking
- Questa: Simualtion and coverage metrics

The quality gate can operate in three modes:
- blocking: Fails pipeline on critical errors
- advisory: Reports issues but continues
- disabled: Skips quality checks entirely

Usage:
    from step2_classify_route.quality_gate import VeribleLinter
    
    linter = VeribleLinter(
        files=[Path("adder.sv")],
        root_dir=Path("./project")
    )
    report = linter.run_checks()
    
    if report.has_critical_errors():
        print("Quality gate failed!")
"""

from .base import BaseQualityGate
from .verible_linter import VeribleLinter
from .ghdl_checker import GHDLChecker

__all__ = [
    "BaseQualityGate",
    "VeribleLinter",
    "GHDLChecker",
    "QuestaChecker",
]
