"""
Entry point for running step4_execute as a module

Usage: python -m step4_execute <submission_dir>

Author: TB Eval Team
Version: 0.1.0
"""

import sys
import asyncio
from pathlib import Path

from .cli.main import main as cli_main


if __name__ == "__main__":
    sys.exit(asyncio.run(cli_main()))
