"""
CLI Module for Step 3: Build & Orchestrate
==========================================

Provides command-line interface for the build phase.

Usage:
    python -m step3_build_orchestrate <submission_dir> [options]
    
    # Or if installed:
    tbeval-build <submission_dir> [options]

Commands:
    tbeval-build ./project              # Build project
    tbeval-build ./project --compile    # Compile only
    tbeval-build ./project --list       # List discovered tests
"""

from .main import main, create_parser

__all__ = ["main", "create_parser"]
