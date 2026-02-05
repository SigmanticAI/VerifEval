"""
Command-line interface for Step 4: Test Execution

Provides the main CLI entry point for executing tests.

Usage:
    tbeval-run [OPTIONS] <submission_dir>
    python -m step4_execute [OPTIONS] <submission_dir>

Author: TB Eval Team
Version: 0.1.0
"""

import sys
import asyncio
import argparse
from pathlib import Path
from typing import Optional, Dict, Any
import textwrap

from ..executor import TestExecutor, execute_tests
from ..config import ExecutionConfig, ConfigManager, create_default_config_file
from ..models import ExitCode
from ..handlers.output_handler import OutputFormatter


# Version information
VERSION = "0.1.0"
PROG_NAME = "tbeval-run"


def create_parser() -> argparse.ArgumentParser:
    """
    Create argument parser
    
    Returns:
        Configured ArgumentParser
    """
    parser = argparse.ArgumentParser(
        prog=PROG_NAME,
        description="TB Eval Framework - Test Execution",
        epilog=textwrap.dedent("""
            Examples:
              # Run all tests
              %(prog)s /path/to/submission
              
              # Run with specific manifest
              %(prog)s --manifest build_manifest.json /path/to/submission
              
              # Dry run (list tests)
              %(prog)s --dry-run /path/to/submission
              
              # Run with filter
              %(prog)s --filter "test_basic" /path/to/submission
              
              # Verbose output with fail-fast
              %(prog)s -v --fail-fast /path/to/submission
              
              # Run with custom timeout
              %(prog)s --timeout 300 /path/to/submission
        """),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    
    # Positional arguments
    parser.add_argument(
        "submission_dir",
        type=Path,
        help="Path to submission directory",
    )
    
    # Configuration
    config_group = parser.add_argument_group("Configuration")
    config_group.add_argument(
        "--manifest",
        type=Path,
        metavar="PATH",
        help="Path to build manifest (default: auto-detect)",
    )
    config_group.add_argument(
        "--config",
        type=Path,
        metavar="PATH",
        help="Path to .tbeval.yaml config file (default: auto-detect)",
    )
    config_group.add_argument(
        "--output",
        "-o",
        type=Path,
        metavar="DIR",
        help="Output directory for results (default: .tbeval/test_runs)",
    )
    
    # Execution control
    exec_group = parser.add_argument_group("Execution Control")
    exec_group.add_argument(
        "--dry-run",
        action="store_true",
        help="List tests without executing them",
    )
    exec_group.add_argument(
        "--filter",
        "-f",
        type=str,
        metavar="PATTERN",
        help="Run only tests matching regex pattern",
    )
    exec_group.add_argument(
        "--rerun-failed",
        action="store_true",
        help="Re-run only previously failed tests",
    )
    exec_group.add_argument(
        "--fail-fast",
        action="store_true",
        help="Stop on first test failure",
    )
    
    # Timeouts
    timeout_group = parser.add_argument_group("Timeouts")
    timeout_group.add_argument(
        "--timeout",
        "-t",
        type=float,
        metavar="SECONDS",
        help="Per-test timeout in seconds (default: 300)",
    )
    timeout_group.add_argument(
        "--suite-timeout",
        type=float,
        metavar="SECONDS",
        help="Test suite timeout in seconds (default: 1800)",
    )
    timeout_group.add_argument(
        "--global-timeout",
        type=float,
        metavar="SECONDS",
        help="Global execution timeout in seconds (default: 3600)",
    )
    
    # Retry
    retry_group = parser.add_argument_group("Retry Configuration")
    retry_group.add_argument(
        "--retry",
        action="store_true",
        default=None,
        help="Enable test retry on failure (default: enabled)",
    )
    retry_group.add_argument(
        "--no-retry",
        dest="retry",
        action="store_false",
        help="Disable test retry",
    )
    retry_group.add_argument(
        "--retry-count",
        type=int,
        metavar="N",
        help="Maximum retry attempts (default: 3)",
    )
    
    # Parallelism
    parallel_group = parser.add_argument_group("Parallelism")
    parallel_group.add_argument(
        "--parallel",
        "-p",
        type=int,
        metavar="N",
        help="Number of parallel tests/jobs (default: 4)",
    )
    
    # Output control
    output_group = parser.add_argument_group("Output Control")
    output_group.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Verbose output",
    )
    output_group.add_argument(
        "--quiet",
        "-q",
        action="store_true",
        help="Minimal output",
    )
    output_group.add_argument(
        "--no-color",
        action="store_true",
        help="Disable colored output",
    )
    output_group.add_argument(
        "--stream",
        action="store_true",
        help="Stream test output in real-time",
    )
    
    # Report formats
    report_group = parser.add_argument_group("Report Formats")
    report_group.add_argument(
        "--format",
        choices=["json", "yaml"],
        default="json",
        help="Primary report format (default: json)",
    )
    report_group.add_argument(
        "--junit",
        type=Path,
        metavar="FILE",
        help="Export JUnit XML report",
    )
    report_group.add_argument(
        "--html",
        type=Path,
        metavar="FILE",
        help="Export HTML report",
    )
    
    # Advanced options
    advanced_group = parser.add_argument_group("Advanced Options")
    advanced_group.add_argument(
        "--cleanup",
        action="store_true",
        help="Cleanup artifacts for passing tests",
    )
    advanced_group.add_argument(
        "--debug",
        action="store_true",
        help="Enable debug mode (detailed error traces)",
    )
    advanced_group.add_argument(
        "--no-coverage",
        dest="coverage",
        action="store_false",
        default=True,
        help="Disable coverage collection",
    )
    
    # Utility commands
    util_group = parser.add_argument_group("Utility Commands")
    util_group.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {VERSION}",
        help="Show version and exit",
    )
    util_group.add_argument(
        "--generate-config",
        type=Path,
        metavar="FILE",
        help="Generate default .tbeval.yaml config file and exit",
    )
    
    return parser


def build_config_overrides(args: argparse.Namespace) -> Dict[str, Any]:
    """
    Build configuration overrides from CLI arguments
    
    Args:
        args: Parsed arguments
    
    Returns:
        Dictionary of configuration overrides
    """
    overrides = {}
    
    # Output directory
    if args.output:
        overrides["output"] = args.output
    
    # Execution control
    if args.dry_run:
        overrides["dry_run"] = True
    
    if args.filter:
        overrides["filter"] = args.filter
    
    if args.rerun_failed:
        overrides["rerun_failed"] = True
    
    if args.fail_fast:
        overrides["fail_fast"] = True
    
    # Timeouts
    if args.timeout:
        overrides["timeout"] = args.timeout
    
    if args.suite_timeout:
        overrides["suite_timeout"] = args.suite_timeout
    
    if args.global_timeout:
        overrides["global_timeout"] = args.global_timeout
    
    # Retry
    if args.retry is not None:
        overrides["retry"] = args.retry
    
    if args.retry_count:
        overrides["retry_count"] = args.retry_count
    
    # Parallelism
    if args.parallel:
        overrides["parallel"] = args.parallel
    
    # Output control
    if args.verbose:
        overrides["verbose"] = True
    
    if args.quiet:
        overrides["quiet"] = True
    
    if args.no_color:
        overrides["no_color"] = True
    
    if args.stream:
        overrides["stream"] = True
    
    # Report formats
    if args.format:
        overrides["format"] = args.format
    
    if args.junit:
        overrides["junit"] = args.junit
    
    if args.html:
        overrides["html"] = args.html
    
    # Advanced
    if args.cleanup:
        overrides["cleanup"] = True
    
    if args.debug:
        overrides["debug"] = True
    
    if not args.coverage:
        overrides["coverage"] = False
    
    return overrides


def validate_arguments(args: argparse.Namespace) -> Optional[str]:
    """
    Validate parsed arguments
    
    Args:
        args: Parsed arguments
    
    Returns:
        Error message if validation fails, None otherwise
    """
    # Check submission directory exists
    if not args.submission_dir.exists():
        return f"Submission directory not found: {args.submission_dir}"
    
    if not args.submission_dir.is_dir():
        return f"Not a directory: {args.submission_dir}"
    
    # Check manifest if specified
    if args.manifest and not args.manifest.exists():
        return f"Manifest file not found: {args.manifest}"
    
    # Check config if specified
    if args.config and not args.config.exists():
        return f"Config file not found: {args.config}"
    
    # Validate timeout values
    if args.timeout and args.timeout <= 0:
        return "Timeout must be positive"
    
    if args.suite_timeout and args.suite_timeout <= 0:
        return "Suite timeout must be positive"
    
    if args.global_timeout and args.global_timeout <= 0:
        return "Global timeout must be positive"
    
    # Validate retry count
    if args.retry_count and args.retry_count < 1:
        return "Retry count must be at least 1"
    
    # Validate parallel count
    if args.parallel and args.parallel < 1:
        return "Parallel count must be at least 1"
    
    # Check conflicting options
    if args.verbose and args.quiet:
        return "Cannot use --verbose and --quiet together"
    
    return None


async def main() -> int:
    """
    Main entry point
    
    Returns:
        Exit code
    """
    # Create parser
    parser = create_parser()
    
    # Parse arguments
    args = parser.parse_args()
    
    # Handle utility commands
    if args.generate_config:
        create_default_config_file(args.generate_config)
        return 0
    
    # Validate arguments
    error = validate_arguments(args)
    if error:
        parser.error(error)
        return ExitCode.CONFIG_ERROR.value
    
    # Build config overrides
    config_overrides = build_config_overrides(args)
    
    # Create formatter for output
    formatter = OutputFormatter(use_color=not args.no_color)
    
    try:
        # Execute tests
        report = await execute_tests(
            submission_dir=args.submission_dir,
            config_overrides=config_overrides,
            manifest_path=args.manifest,
        )
        
        # Print final status
        print()
        if report.exit_code == 0:
            print(formatter.success("✓ All tests passed"))
        elif report.exit_code == ExitCode.DRY_RUN.value:
            print(formatter.info("ℹ Dry run completed"))
        elif report.exit_code == ExitCode.USER_CANCELLED.value:
            print(formatter.warning("⚠ Execution cancelled by user"))
        else:
            print(formatter.error("✗ Tests failed"))
        
        # Print report location
        if report.artifacts_root:
            report_file = Path(report.artifacts_root) / "test_report.json"
            print(f"\nReport: {formatter.dim(str(report_file))}")
        
        return report.exit_code
    
    except FileNotFoundError as e:
        print(formatter.error(f"Error: {e}"))
        return ExitCode.FILE_NOT_FOUND.value
    
    except ValueError as e:
        print(formatter.error(f"Configuration error: {e}"))
        return ExitCode.CONFIG_ERROR.value
    
    except KeyboardInterrupt:
        print(formatter.warning("\n\nInterrupted by user"))
        return ExitCode.USER_CANCELLED.value
    
    except Exception as e:
        print(formatter.error(f"Unexpected error: {e}"))
        
        if args.debug:
            import traceback
            traceback.print_exc()
        
        return ExitCode.SYSTEM_ERROR.value


def sync_main() -> int:
    """
    Synchronous wrapper for main
    
    Returns:
        Exit code
    """
    return asyncio.run(main())


# Entry point when run as script
if __name__ == "__main__":
    sys.exit(sync_main())
