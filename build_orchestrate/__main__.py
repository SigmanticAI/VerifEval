"""
Entry point for: python -m step3_build_orchestrate

Runs the Step 3 CLI.
"""

from .cli.main import main
import sys

if __name__ == "__main__":
    sys.exit(main())
