"""
Command-line interface for Step 7: Scoring & Export

Usage:
    python -m step7_score [options]
    
Examples:
    # Basic scoring (auto-detect tier)
    python -m step7_score
    
    # With config file
    python -m step7_score --config .tbeval.yaml
    
    # Force Tier 1 (open-source)
    python -m step7_score --tier tier1
    
    # Force Tier 2 (professional)
    python -m step7_score --tier tier2
    
    # Export multiple formats
    python -m step7_score --export html --export junit
    
    # Verbose mode
    python -m step7_score --verbose

Author: TB Eval Team
Version: 0.1.0
"""

import sys
import argparse
import logging
from pathlib import Path
from typing import Optional, List
import time

from . import __version__
from .config import ScoreCalculationConfig
from .models import ScoringTier
from .scorers.tier1_scorer import Tier1Scorer
from .questa.license_checker import check_questa_availability, print_questa_status


# =============================================================================
# LOGGING SETUP
# =============================================================================

def setup_logging(verbose: bool = False, debug: bool = False, quiet: bool = False) -> None:
    """
    Setup logging configuration
    
    Args:
        verbose: Enable verbose output
        debug: Enable debug output
        quiet: Minimal output
    """
    if quiet:
        level = logging.ERROR
        format_str = '%(message)s'
    elif debug:
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
        prog='python -m step7_score',
        description='Scoring and export for TB Eval framework (Step 7)',
        epilog='For more information, see: https://github.com/tbeval/step7_score',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    # Version
    parser.add_argument(
        '--version',
        action='version',
        version=f'step7_score {__version__}'
    )
    
    # Input files
    input_group = parser.add_argument_group('input files')
    input_group.add_argument(
        '--config',
        '-c',
        type=Path,
        metavar='PATH',
        help='Path to .tbeval.yaml configuration file'
    )
    input_group.add_argument(
        '--test-report',
        type=Path,
        metavar='PATH',
        help='Path to test_report.json from Step 4'
    )
    input_group.add_argument(
        '--coverage-report',
        type=Path,
        metavar='PATH',
        help='Path to coverage_report.json from Step 5'
    )
    input_group.add_argument(
        '--quality-report',
        type=Path,
        metavar='PATH',
        help='Path to quality_report.json from Step 2'
    )
    
    # Tier selection
    tier_group = parser.add_argument_group('tier selection')
    tier_group.add_argument(
        '--tier',
        choices=['auto', 'tier1', 'tier2'],
        default='auto',
        help='Scoring tier (default: auto-detect based on Questa availability)'
    )
    tier_group.add_argument(
        '--force-tier1',
        action='store_true',
        help='Force Tier 1 (open-source) even if Questa available'
    )
    tier_group.add_argument(
        '--force-tier2',
        action='store_true',
        help='Force Tier 2 (professional) - fail if Questa not available'
    )
    
    # Output options
    output_group = parser.add_argument_group('output options')
    output_group.add_argument(
        '--output',
        '-o',
        type=Path,
        metavar='DIR',
        help='Output directory for reports (default: .tbeval/score)'
    )
    output_group.add_argument(
        '--submission-id',
        type=str,
        metavar='ID',
        help='Submission identifier (default: auto-detect from directory)'
    )
    output_group.add_argument(
        '--export',
        action='append',
        choices=['json', 'html', 'junit', 'csv'],
        help='Export formats (can specify multiple times, default: json + html)'
    )
    output_group.add_argument(
        '--no-json',
        action='store_true',
        help='Skip JSON export (not recommended)'
    )
    output_group.add_argument(
        '--no-html',
        action='store_true',
        help='Skip HTML export'
    )
    
    # Threshold options
    threshold_group = parser.add_argument_group('threshold options')
    threshold_group.add_argument(
        '--fail-on-threshold',
        action='store_true',
        help='Exit with error if passing grade not achieved'
    )
    threshold_group.add_argument(
        '--passing-grade',
        choices=['A', 'B', 'C', 'D'],
        default='C',
        help='Minimum passing grade (default: C = 70%%)'
    )
    
    # Display options
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
    display_group.add_argument(
        '--no-summary',
        action='store_true',
        help='Skip summary output'
    )
    
    # Diagnostic options
    diag_group = parser.add_argument_group('diagnostic options')
    diag_group.add_argument(
        '--check-config',
        action='store_true',
        help='Validate configuration and exit'
    )
    diag_group.add_argument(
        '--check-questa',
        action='store_true',
        help='Check Questa availability and exit'
    )
    diag_group.add_argument(
        '--dry-run',
        action='store_true',
        help='Validate inputs without running scoring'
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
        
        # Show paths
        print(f"\n{Colors.BOLD}Input Files:{Colors.RESET}")
        print(f"  Test report:     {config.test_report_path}")
        print(f"    Exists: {'✓' if config.test_report_path and config.test_report_path.exists() else '✗'}")
        
        print(f"  Coverage report: {config.coverage_report_path}")
        print(f"    Exists: {'✓' if config.coverage_report_path and config.coverage_report_path.exists() else '✗'}")
        
        print(f"  Quality report:  {config.quality_report_path}")
        print(f"    Exists: {'✓' if config.quality_report_path and config.quality_report_path.exists() else '✗'}")
        
        # Show weights
        print(f"\n{Colors.BOLD}Tier 1 Weights:{Colors.RESET}")
        for name, weight in config.tier1_weights.to_dict().items():
            print(f"  {name:25s} {weight:.2f}")
        
        print(f"\n{Colors.BOLD}Grade Thresholds:{Colors.RESET}")
        for grade, threshold in config.grade_thresholds.to_dict().items():
            if grade != "passing_grade" and grade != "passing_percentage":
                print(f"  {grade}: {threshold}%")
        print(f"  Passing: {config.grade_thresholds.passing_grade}")
        
        # Validate
        issues = config.validate()
        if issues:
            print(f"\n{Colors.BOLD}Validation Issues:{Colors.RESET}")
            for issue in issues:
                print_warning(issue)
            return 1
        
        print_success("\nConfiguration is valid")
        return 0
    
    except Exception as e:
        print_error(f"Configuration error: {e}")
        return 1


def cmd_check_questa(args: argparse.Namespace) -> int:
    """
    Check Questa availability
    
    Args:
        args: Parsed arguments
    
    Returns:
        Exit code
    """
    print_questa_status()
    
    caps = check_questa_availability()
    return 0 if caps.tier2_available else 1


def create_config(args: argparse.Namespace) -> ScoreCalculationConfig:
    """
    Create configuration from CLI arguments
    
    Args:
        args: Parsed arguments
    
    Returns:
        ScoreCalculationConfig
    """
    # Build CLI overrides
    cli_overrides = {}
    
    if args.output:
        cli_overrides['output_dir'] = args.output
    
    if args.fail_on_threshold:
        cli_overrides['fail_on_threshold'] = True
    
    if args.debug:
        cli_overrides['debug'] = True
    
    # Create config
    if args.config:
        config = ScoreCalculationConfig.from_yaml(
            args.config,
            cli_overrides=cli_overrides
        )
    else:
        # Create from CLI arguments
        config = ScoreCalculationConfig(
            submission_dir=Path.cwd(),
            test_report_path=args.test_report,
            coverage_report_path=args.coverage_report,
            quality_report_path=args.quality_report,
        )
        
        # Apply CLI overrides
        if args.output:
            config.export_config.output_dir = Path(args.output)
    
    # Override tier if specified
    if args.force_tier1 or args.tier == 'tier1':
        config.auto_detect_tier = False
        config.force_tier = ScoringTier.OPEN_SOURCE
    elif args.force_tier2 or args.tier == 'tier2':
        config.auto_detect_tier = False
        config.force_tier = ScoringTier.PROFESSIONAL
    
    return config


def determine_tier(config: ScoreCalculationConfig, args: argparse.Namespace) -> ScoringTier:
    """
    Determine which scoring tier to use
    
    Args:
        config: Configuration
        args: CLI arguments
    
    Returns:
        ScoringTier
    """
    # Check for forced tier
    if config.force_tier:
        return config.force_tier
    
    # Auto-detect based on Questa
    if config.auto_detect_tier:
        caps = check_questa_availability(config.questa_config)
        if caps.tier2_available:
            return ScoringTier.PROFESSIONAL
        else:
            return ScoringTier.OPEN_SOURCE
    
    return ScoringTier.OPEN_SOURCE


def run_scoring(args: argparse.Namespace) -> int:
    """
    Run scoring
    
    Args:
        args: Parsed arguments
    
    Returns:
        Exit code
    """
    start_time = time.time()
    
    try:
        # Create configuration
        config = create_config(args)
        
        if not args.quiet:
            print_header("TB Eval - Step 7: Scoring")
            print(f"Submission: {config.submission_dir}")
        
        # Dry run check
        if args.dry_run:
            print_info("Dry run mode - validating inputs only")
            issues = config.validate()
            if issues:
                for issue in issues:
                    print_warning(issue)
                return 1
            print_success("Validation passed")
            return 0
        
        # Determine tier
        tier = determine_tier(config, args)
        
        if not args.quiet:
            if tier == ScoringTier.PROFESSIONAL:
                print_info(f"Using Tier 2 (Professional) scoring with Questa")
            else:
                print_info(f"Using Tier 1 (Open Source) scoring")
        
        # Run scoring based on tier
        if tier == ScoringTier.PROFESSIONAL:
            # Tier 2 not implemented yet
            print_error("Tier 2 scoring not yet implemented")
            print_info("Falling back to Tier 1")
            tier = ScoringTier.OPEN_SOURCE
        
        # Tier 1 scoring
        if tier == ScoringTier.OPEN_SOURCE:
            scorer = Tier1Scorer(config)
            
            if not args.quiet:
                print_info("Calculating score...")
            
            tier_score = scorer.calculate_score()
            
            # Generate report
            submission_id = args.submission_id or config.submission_dir.name
            total_duration_ms = (time.time() - start_time) * 1000
            
            report = scorer.generate_report(
                submission_id=submission_id,
                tier_score=tier_score,
                total_duration_ms=total_duration_ms
            )
            
            # Save reports
            output_dir = config.export_config.output_dir
            output_dir.mkdir(parents=True, exist_ok=True)
            
            # Determine export formats
            export_formats = args.export or ['json', 'html']
            if args.no_json:
                export_formats = [f for f in export_formats if f != 'json']
            if args.no_html:
                export_formats = [f for f in export_formats if f != 'html']
            
            # Always save JSON (required)
            if 'json' not in export_formats:
                export_formats.insert(0, 'json')
            
            # Export in requested formats
            for fmt in export_formats:
                if fmt == 'json':
                    json_path = output_dir / "final_score.json"
                    report.save(json_path)
                    if not args.quiet:
                        print_success(f"JSON report: {json_path}")
                
                elif fmt == 'html':
                    print_warning("HTML export not yet implemented")
                
                elif fmt == 'junit':
                    print_warning("JUnit export not yet implemented")
                
                elif fmt == 'csv':
                    print_warning("CSV export not yet implemented")
            
            # Save summary
            if not args.no_summary:
                summary_path = output_dir / "score_summary.txt"
                summary_path.write_text(scorer.get_summary())
                if not args.quiet:
                    print_success(f"Summary: {summary_path}")
            
            # Display summary
            if not args.quiet and not args.no_summary:
                print("\n" + scorer.get_summary())
            
            # Display top improvements
            if not args.quiet and report.improvements:
                print_header("Top Improvements")
                for i, imp in enumerate(report.improvements[:3], 1):
                    print(f"\n{i}. {imp.component.display_name}")
                    print(f"   Priority: {Colors.BOLD}{imp.priority.upper()}{Colors.RESET}")
                    print(f"   Impact:   {imp.impact:.4f} score points")
                    print(f"   Action:   {imp.actions[0] if imp.actions else 'N/A'}")
            
            # Display recommendations
            if not args.quiet and report.recommendations:
                print_header("Recommendations")
                for i, rec in enumerate(report.recommendations[:3], 1):
                    print(f"\n{i}. [{rec.category}]")
                    print(f"   {rec.message}")
            
            # Final result
            print(f"\n{'=' * 60}")
            if tier_score.pass_threshold:
                print_success(
                    f"PASS - Score: {tier_score.percentage:.2f}% "
                    f"(Grade: {tier_score.grade.value})"
                )
            else:
                print_error(
                    f"FAIL - Score: {tier_score.percentage:.2f}% "
                    f"(Grade: {tier_score.grade.value})"
                )
            print('=' * 60)
            
            # Return exit code
            if args.fail_on_threshold and not tier_score.pass_threshold:
                return 1
            
            return 0
    
    except Exception as e:
        print_error(f"Scoring failed: {e}")
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
        debug=args.debug,
        quiet=args.quiet
    )
    
    # Disable colors if requested or not a TTY
    if args.no_color or not sys.stdout.isatty():
        Colors.disable()
    
    # Handle special commands
    if args.check_config:
        return cmd_check_config(args)
    
    if args.check_questa:
        return cmd_check_questa(args)
    
    # Validate required arguments
    if not args.config:
        if not args.test_report or not args.coverage_report:
            parser.error(
                "Either --config or both --test-report and --coverage-report required"
            )
    
    # Run scoring
    return run_scoring(args)


if __name__ == '__main__':
    sys.exit(main())
