"""
TB-Eval: Testbench Evaluation Framework

Implements the VerifLLMBench methodology for evaluating verification testbenches.
Supports both single-file and multi-file verification projects.

Usage:
    from tb_eval import TBEvalRunner, EvalConfig
    
    runner = TBEvalRunner()
    results = runner.evaluate(Path("path/to/verification"))
    print(results.summary())
"""

from .config import EvalConfig, VerificationProject, EXAMPLES_DIR
from .runner import TBEvalRunner
from .simulator import Simulator, parse_verification_project
from .coverage_analyzer import EvalMetrics, ProjectResults

__all__ = [
    'TBEvalRunner',
    'EvalConfig',
    'VerificationProject',
    'Simulator',
    'parse_verification_project',
    'EvalMetrics',
    'ProjectResults',
    'EXAMPLES_DIR',
]
