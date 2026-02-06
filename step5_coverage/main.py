"""
CLI entry point for step5_coverage package

Usage:
    python -m step5_coverage [options]
    
Example:
    python -m step5_coverage --test-report test_report.json --output coverage_report.json
"""

import sys
from pathlib import Path


def main():
    """
    Main entry point for CLI execution
    
    This will delegate to the actual CLI implementation once it's ready.
    """
    print(f"step5_coverage version {__package__.__version__}")
    print("CLI not yet implemented - coming soon!")
    print()
    print("Usage:")
    print("  python -m step5_coverage --test-report <path> --output <path>")
    print()
    print("For now, use the Python API:")
    print("  >>> from step5_coverage import CoverageAnalyzer")
    print("  >>> # See package docstring for examples")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
