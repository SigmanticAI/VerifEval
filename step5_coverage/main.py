"""
Command-line interface for Step 5 coverage analysis

Usage:
    python -m step5_coverage [options]
    
Examples:
    # Basic analysis
    python -m step5_coverage --test-report test_report.json
    
    # With config file
    python -m step5_coverage --config .tbeval.yaml
    
    # Specify output directory
    python -m step5_coverage --test-report test_report.json --output coverage_output/
    
    # Verbose mode
    python -m step5_coverage --test-report test_report.json --verbose
    
    # Generate HTML report
    python -m step5_coverage --test-report test_report.json --html

Author: TB Eval Team
Version: 0.1.0
"""

import sys
import argparse
import logging
from pathlib import Path
from typing import Optional

from . import __version__
from .analyzer import CoverageAnalyzer, AnalysisResult
from .config import CoverageAnalysisConfig


# =============================================================================
# LOGGING SETUP
# =============================================================================

def setup_logging(verbose: bool = False, debug: bool = False) -> None:
    """
    Setup logging configuration
    
    Args:
        verbose: Enable verbose output
        debug: Enable debug output
    """
    if debug:
        level = logging.DEBUG
        format_str = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    elif verbose:
        level = logging.INFO
        format_str = '%(levelname)s - %(message)s'
    else:
        level = logging.WARNING
        format_str = '%(message)s'
    
    logging.basicConfig(
        level=level,
        format=format_str,
        datefmt='%Y-%m-%d %H:%M:%S'
    )


# =============================================================================
# CLI ARGUMENT PARSER
# =============================================================================

def create_parser() -> argparse.ArgumentParser:
    """
    Create argument parser for CLI
    
    Returns:
        Configured ArgumentParser
    """
    parser = argparse.ArgumentParser(
        prog='python -m step5_coverage',
        description='Coverage analysis for TB Eval framework (Step 5)',
        epilog='For more information, see: https://github.com/tbeval/step5_coverage',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    # Version
    parser.add_argument(
        '--version',
        action='version',
        version=f'step5_coverage {__version__}'
    )
    
    # Input files
    input_group = parser.add_argument_group('input files')
    input_group.add_argument(
        '--test-report',
        type=Path,
        metavar='PATH',
        help='Path to test_report.json from Step 4 (required if --config not provided)'
    )
    input_group.add_argument(
        '--build-manifest',
        type=Path,
        metavar='PATH',
        help='Path to build_manifest.json from Step 3 (auto-detected if not provided)'
    )
    input_group.add_argument(
        '--config',
        '-c',
        type=Path,
        metavar='PATH',
        help='Path to .tbeval.yaml configuration file'
    )
    
    # Output options
    output_group = parser.add_argument_group('output options')
    output_group.add_argument(
        '--output',
        '-o',
        type=Path,
        metavar='DIR',
        help='Output directory for coverage reports (default: .tbeval/coverage)'
    )
    output_group.add_argument(
        '--report-name',
        type=str,
        metavar='NAME',
        default='coverage_report.json',
        help='Output report filename (default: coverage_report.json)'
    )
    output_group.add_argument(
        '--summary',
        action='store_true',
        help='Generate human-readable summary (coverage_summary.txt)'
    )
    output_group.add_argument(
        '--html',
        action='store_true',
        help='Generate HTML report (Phase 2 - not yet implemented)'
    )
    output_group.add_argument(
        '--json-detail',
        choices=['summary', 'normal', 'full'],
        default='full',
        help='JSON output detail level (default: full)'
    )
    
    # Analysis options
    analysis_group = parser.add_argument_group('analysis options')
    analysis_group.add_argument(
        '--no-per-test',
        action='store_true',
        help='Disable per-test coverage tracking (faster but less detailed)'
    )
    analysis_group.add_argument(
        '--no-merge',
        action='store_true',
        help='Skip coverage merging (analyze individual files only)'
    )
    analysis_group.add_argument(
        '--no-hotspots',
        action='store_true',
        help='Skip uncovered hotspot identification'
    )
    analysis_group.add_argument(
        '--no-mutation',
        action='store_true',
        help='Skip mutation testing data generation'
    )
    
    # Threshold options
    threshold_group = parser.add_argument_group('threshold options')
    threshold_group.add_argument(
        '--line-threshold',
        type=float,
        metavar='PCT',
        help='Minimum line coverage percentage (default: 80.0)'
    )
    threshold_group.add_argument(
        '--branch-threshold',
        type=float,
        metavar='PCT',
        help='Minimum branch coverage percentage (default: 90.0)'
    )
    threshold_group.add_argument(
        '--toggle-threshold',
        type=float,
        metavar='PCT',
        help='Minimum toggle coverage percentage (default: 70.0)'
    )
    threshold_group.add_argument(
        '--fail-on-threshold',
        action='store_true',
        help='Exit with error if thresholds not met (default: warning only)'
    )
    
    # Output control
    display_group = parser.add_argument_group('display options')
    display_group.add_argument(
        '--verbose',
        '-v',
        action='store_true',
        help='Verbose output'
    )
    display_group.add_argument(
        '--debug',
        action='store_true',
        help='Debug output (very verbose)'
    )
    display_group.add_argument(
        '--quiet',
        '-q',
        action='store_true',
        help='Minimal output (errors only)'
    )
    display_group.add_argument(
        '--no-color',
        action='store_true',
        help='Disable colored output'
    )
    
    # Advanced options
    advanced_group = parser.add_argument_group('advanced options')
    advanced_group.add_argument(
        '--parser-priority',
        nargs='+',
        choices=['verilator', 'lcov', 'covered'],
        help='Parser priority order (default: verilator lcov covered)'
    )
    advanced_group.add_argument(
        '--essential-threshold',
        type=float,
        metavar='PCT',
        default=5.0,
        help='Minimum unique coverage for essential tests (default: 5.0)'
    )
    advanced_group.add_argument(
        '--redundant-threshold',
        type=float,
        metavar='PCT',
        default=1.0,
        help='Maximum unique coverage for redundant tests (default: 1.0)'
    )
    
    # Diagnostic options
    diag_group = parser.add_argument_group('diagnostic options')
    diag_group.add_argument(
        '--list-parsers',
        action='store_true',
        help='List available parsers and exit'
    )
    diag_group.add_argument(
        '--check-config',
        action='store_true',
        help='Validate configuration and exit'
    )
    diag_group.add_argument(
        '--dry-run',
        action='store_true',
        help='Validate inputs without running analysis'
    )
    
    return parser


# =============================================================================
# COLOR OUTPUT
# =============================================================================

class Colors:
    """ANSI color codes for terminal output"""
    RESET = '\033[0m'
    BOLD = '\033[1m'
    RED = '\033[91m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    MAGENTA = '\033[95m'
    CYAN = '\033[96m'
    
    @classmethod
    def disable(cls):
        """Disable colors"""
        cls.RESET = ''
        cls.BOLD = ''
        cls.RED = ''
        cls.GREEN = ''
        cls.YELLOW = ''
        cls.BLUE = ''
        cls.MAGENTA = ''
        cls.CYAN = ''


def print_header(text: str, color: str = Colors.CYAN) -> None:
    """Print a colored header"""
    print(f"\n{color}{Colors.BOLD}{text}{Colors.RESET}")


def print_success(text: str) -> None:
    """Print success message"""
    print(f"{Colors.GREEN}✓ {text}{Colors.RESET}")


def print_warning(text: str) -> None:
    """Print warning message"""
    print(f"{Colors.YELLOW}⚠ {text}{Colors.RESET}")


def print_error(text: str) -> None:
    """Print error message"""
    print(f"{Colors.RED}✗ {text}{Colors.RESET}", file=sys.stderr)


def print_info(text: str) -> None:
    """Print info message"""
    print(f"{Colors.BLUE}ℹ {text}{Colors.RESET}")


# =============================================================================
# CLI COMMANDS
# =============================================================================

def cmd_list_parsers(args: argparse.Namespace) -> int:
    """
    List available parsers
    
    Args:
        args: Parsed arguments
    
    Returns:
        Exit code
    """
    from .parsers import (
        VerilatorParser,
        LCOVParser,
        is_verilator_coverage_available,
        is_lcov_available,
        get_verilator_coverage_version,
        get_lcov_version,
    )
    
    print_header("Available Coverage Parsers")
    
    # Verilator
    print(f"\n{Colors.BOLD}Verilator Parser{Colors.RESET}")
    print(f"  Format: Verilator .dat files")
    if is_verilator_coverage_available():
        version = get_verilator_coverage_version()
        print_success(f"verilator_coverage available (version: {version})")
    else:
        print_warning("verilator_coverage not found (will use Python fallback)")
    
    # LCOV
    print(f"\n{Colors.BOLD}LCOV Parser{Colors.RESET}")
    print(f"  Format: LCOV .info/.lcov files")
    if is_lcov_available():
        version = get_lcov_version()
        print_success(f"lcov available (version: {version})")
    else:
        print_warning("lcov not found (will use Python fallback)")
    
    # Covered (Phase 2)
    print(f"\n{Colors.BOLD}Covered Parser{Colors.RESET}")
    print(f"  Format: Covered .cdd files")
    print_info("Phase 2 - not yet implemented")
    
    return 0


def cmd_check_config(args: argparse.Namespace) -> int:
    """
    Check configuration validity
    
    Args:
        args: Parsed arguments
    
    Returns:
        Exit code
    """
    print_header("Configuration Check")
    
    try:
        config = create_config(args)
        
        print_success("Configuration loaded successfully")
        
        # Validate paths
        print(f"\n{Colors.BOLD}Input Files:{Colors.RESET}")
        print(f"  Test report: {config.test_report_path}")
        if config.test_report_path.exists():
            print_success("  Found")
        else:
            print_error("  Not found")
            return 1
        
        print(f"  Build manifest: {config.build_manifest_path}")
        if config.build_manifest_path.exists():
            print_success("  Found")
        else:
            print_warning("  Not found (may be optional)")
        
        # Show configuration
        print(f"\n{Colors.BOLD}Thresholds:{Colors.RESET}")
        print(f"  Line:    {config.thresholds.line}%")
        print(f"  Branch:  {config.thresholds.branch}%")
        print(f"  Toggle:  {config.thresholds.toggle}%")
        print(f"  Overall: {config.thresholds.overall}%")
        
        print(f"\n{Colors.BOLD}Weights:{Colors.RESET}")
        print(f"  Line:   {config.weights.line:.2f}")
        print(f"  Branch: {config.weights.branch:.2f}")
        print(f"  Toggle: {config.weights.toggle:.2f}")
        print(f"  FSM:    {config.weights.fsm:.2f}")
        
        print_success("\nConfiguration is valid")
        return 0
    
    except Exception as e:
        print_error(f"Configuration error: {e}")
        return 1


def create_config(args: argparse.Namespace) -> CoverageAnalysisConfig:
    """
    Create configuration from CLI arguments
    
    Args:
        args: Parsed arguments
    
    Returns:
        CoverageAnalysisConfig
    """
    # Build CLI overrides
    cli_overrides = {}
    
    if args.output:
        cli_overrides['output_dir'] = args.output
    
    if args.line_threshold is not None:
        cli_overrides['line_threshold'] = args.line_threshold
    
    if args.branch_threshold is not None:
        cli_overrides['branch_threshold'] = args.branch_threshold
    
    if args.toggle_threshold is not None:
        cli_overrides['toggle_threshold'] = args.toggle_threshold
    
    if args.fail_on_threshold:
        cli_overrides['fail_on_threshold'] = True
    
    if args.debug:
        cli_overrides['debug'] = True
    
    if args.json_detail:
        cli_overrides['detail_level'] = args.json_detail
    
    # Create config
    if args.config:
        # Load from config file
        config = CoverageAnalysisConfig.from_yaml(
            args.config,
            args.test_report or Path("test_report.json"),
            args.build_manifest or Path("build_manifest.json"),
            cli_overrides=cli_overrides
        )
    else:
        # Create from CLI arguments
        if not args.test_report:
            raise ValueError("--test-report required when --config not provided")
        
        config = CoverageAnalysisConfig(
            test_report_path=args.test_report,
            build_manifest_path=args.build_manifest or args.test_report.parent / "build_manifest.json",
            submission_dir=args.test_report.parent
        )
        
        # Apply CLI overrides manually
        if args.output:
            config.reporting.output_dir = args.output
        
        if args.line_threshold is not None:
            config.thresholds.line = args.line_threshold
        
        if args.branch_threshold is not None:
            config.thresholds.branch = args.branch_threshold
        
        if args.toggle_threshold is not None:
            config.thresholds.toggle = args.toggle_threshold
        
        if args.fail_on_threshold:
            config.fail_on_threshold = True
        
        if args.no_per_test:
            config.merging.per_test_analysis = False
        
        if args.no_hotspots:
            config.reporting.identify_hotspots = False
        
        if args.no_mutation:
            config.reporting.export_mutation_targets = False
        
        if args.essential_threshold:
            config.merging.essential_threshold = args.essential_threshold
        
        if args.redundant_threshold:
            config.merging.redundant_threshold = args.redundant_threshold
    
    return config


def run_analysis(args: argparse.Namespace) -> int:
    """
    Run coverage analysis
    
    Args:
        args: Parsed arguments
    
    Returns:
        Exit code
    """
    try:
        # Create configuration
        config = create_config(args)
        
        # Create analyzer
        analyzer = CoverageAnalyzer(config)
        
        if not args.quiet:
            print_header("Coverage Analysis")
            print(f"Test report: {config.test_report_path}")
            print(f"Output dir:  {config.reporting.output_dir}")
        
        # Dry run check
        if args.dry_run:
            print_info("Dry run mode - validating inputs only")
            result = AnalysisResult(success=True)
            analyzer._load_test_report(result)
            analyzer._load_build_manifest(result)
            analyzer._find_coverage_files(result)
            
            if result.success:
                print_success(f"Validation passed - found {len(analyzer.coverage_files)} coverage files")
                return 0
            else:
                print_error("Validation failed")
                for error in result.errors:
                    print_error(f"  {error}")
                return 1
        
        # Run analysis
        if not args.quiet:
            print_info("Running analysis...")
        
        result = analyzer.analyze()
        
        # Handle result
        if result.success:
            report = result.report
            
            # Save report
            output_path = config.reporting.output_dir / args.report_name
            analyzer.save_report(report, output_path)
            
            if not args.quiet:
                print_success(f"Analysis completed in {result.analysis_time_ms:.1f}ms")
                print_success(f"Report saved to: {output_path}")
            
            # Generate summary
            if args.summary or not args.quiet:
                if not args.quiet:
                    print_header("Coverage Summary")
                
                summary = analyzer.generate_summary(report)
                print(summary)
                
                if args.summary:
                    summary_path = config.reporting.output_dir / "coverage_summary.txt"
                    summary_path.write_text(summary)
                    print_success(f"Summary saved to: {summary_path}")
            
            # Show per-test analysis
            if report.hierarchical and not args.quiet:
                print_header("Per-Test Analysis")
                
                if report.hierarchical.essential_tests:
                    print(f"\n{Colors.BOLD}Essential Tests ({len(report.hierarchical.essential_tests)}):{Colors.RESET}")
                    for test_name in report.hierarchical.essential_tests[:5]:
                        print(f"  • {test_name}")
                    if len(report.hierarchical.essential_tests) > 5:
                        print(f"  ... and {len(report.hierarchical.essential_tests) - 5} more")
                
                if report.hierarchical.redundant_tests:
                    print(f"\n{Colors.BOLD}Redundant Tests ({len(report.hierarchical.redundant_tests)}):{Colors.RESET}")
                    for test_name in report.hierarchical.redundant_tests[:5]:
                        print(f"  • {test_name}")
                    if len(report.hierarchical.redundant_tests) > 5:
                        print(f"  ... and {len(report.hierarchical.redundant_tests) - 5} more")
            
            # Show threshold violations
            if result.has_warnings and not args.quiet:
                print_header("Warnings")
                for warning in result.warnings:
                    print_warning(warning)
            
            if not report.thresholds_met:
                print_header("Threshold Violations")
                for violation in report.threshold_violations:
                    print_warning(violation)
                
                if config.fail_on_threshold:
                    return 1
            
            # Show mutation targets
            if report.mutation_data and not args.quiet:
                print_header("Mutation Testing Targets")
                print(f"Uncovered lines:     {len(report.mutation_data.uncovered_lines)}")
                print(f"Weak branches:       {len(report.mutation_data.weakly_covered_branches)}")
                print(f"Untoggled signals:   {len(report.mutation_data.untoggled_signals)}")
            
            return 0
        
        else:
            print_error("Analysis failed")
            
            for error in result.errors:
                print_error(f"  {error}")
            
            if result.has_warnings:
                for warning in result.warnings:
                    print_warning(f"  {warning}")
            
            return 1
    
    except Exception as e:
        print_error(f"Unexpected error: {e}")
        if args.debug:
            import traceback
            traceback.print_exc()
        return 1


# =============================================================================
# MAIN ENTRY POINT
# =============================================================================

def main(argv=None) -> int:
    """
    Main CLI entry point
    
    Args:
        argv: Command-line arguments (defaults to sys.argv)
    
    Returns:
        Exit code
    """
    parser = create_parser()
    args = parser.parse_args(argv)
    
    # Setup logging
    setup_logging(
        verbose=args.verbose or args.debug,
        debug=args.debug
    )
    
    # Disable colors if requested or not a TTY
    if args.no_color or not sys.stdout.isatty():
        Colors.disable()
    
    # Handle special commands
    if args.list_parsers:
        return cmd_list_parsers(args)
    
    if args.check_config:
        return cmd_check_config(args)
    
    # Validate required arguments
    if not args.config and not args.test_report:
        parser.error("--test-report required when --config not provided")
    
    # Run analysis
    return run_analysis(args)


if __name__ == '__main__':
    sys.exit(main())
