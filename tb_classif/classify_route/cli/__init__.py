"""
CLI Module for Step 2
=====================

Provides command-line interface for testbench classification.

Usage:
    python -m step2_classify_route <submission_dir> [options]
    
    # Or if installed:
    tbeval-classify <submission_dir> [options]
"""

from .main import main

__all__ = ["main"]
