"""
Formal-Eval: Formal Verification Evaluation Framework

Evaluates SystemVerilog Assertion (SVA) based formal verification.
Based on FVEval paper methodology using open-source tools (Yosys + Z3).

Usage:
    from formal_eval import FormalEvalRunner, FormalConfig
    
    runner = FormalEvalRunner()
    results = runner.evaluate(Path("path/to/verification"))
    print(results.summary())
"""

from .config import FormalConfig, FormalProject, EXAMPLES_DIR
from .runner import FormalEvalRunner
from .checker import FormalChecker
from .analyzer import FormalMetrics, ProjectResults

__all__ = [
    'FormalEvalRunner',
    'FormalConfig',
    'FormalProject',
    'FormalChecker',
    'FormalMetrics',
    'ProjectResults',
    'EXAMPLES_DIR',
]


