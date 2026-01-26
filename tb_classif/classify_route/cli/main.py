#!/usr/bin/env python3
"""
Main CLI for Step 2: Classify and Route
"""
import argparse
import json
import sys
from pathlib import Path
from typing import Optional

from ..orchestrator import ClassifierRouter
from ..config import ConfigManager, ProjectConfig
from ..models import TBType, Track


# ANSI color codes for terminal output
class Colors:
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'


def color_text(text: str, color: str) -> str:
    """Apply color to text if terminal supports it"""
    if sys.stdout.isatty():
        return f"{color}{text}{Colors.ENDC}"
    return text


def print_banner():
    """Print CLI banner"""
    banner = """
╔═══════════════════════════════════════════════════════════════╗
║          TB Evaluation Framework - Step 2                     ║
║              Classify & Route Submission                      ║
╚═══════════════════════════════════════════════════════════════╝
"""
    print(color_text(banner, Colors.CYAN))


def print_routing_summary(routing, verbose: bool = False):
    """Print human-readable routing summary"""
    print("\n" + "=" * 60)
    print(color_text(" ROUTING DECISION", Colors.BOLD))
    print("=" * 60)
    
    # TB Type with color coding
    tb_color = Colors.GREEN if routing.tb_type != TBType.UNKNOWN.value else Colors.RED
    print(f"\n  TB Type:        {color_text(routing.tb_type, tb_color)}")
    
    # Track
    track_names = {"A": "CocoTB/Python", "B": "VUnit/HDL", "C": "Commercial Required"}
    track_desc = track_names.get(routing.track, routing.track)
    print(f"  Track:          {routing.track} ({track_desc})")
    
    # Simulator
    print(f"  Simulator:      {routing.chosen_simulator}")
    
    # Confidence with color
    conf_color = Colors.GREEN if routing.confidence >= 0.8 else (
        Colors.YELLOW if routing.confidence >= 0.5 else Colors.RED
    )
    print(f"  Confidence:     {color_text(f'{routing.confidence:.1%}', conf_color)}")
    
    # Detection method
    print(f"  Detection:      {routing.detection_method}")
    
    # Entrypoint
    if routing.entrypoint:
        print(f"  Entrypoint:     {routing.entrypoint}")
    
    # Quality gate
    qg_status = "✓ Passed" if routing.quality_gate_passed else "✗ Failed"
    qg_color = Colors.GREEN if routing.quality_gate_passed else Colors.RED
    print(f"\n  Quality Gate:   {color_text(qg_status, qg_color)}")
    
    # Files
    print(f"\n  DUT Files:      {len(routing.dut_files)}")
    if verbose:
        for f in routing.dut_files:
            print(f"                  - {f}")
    
    print(f"  TB Files:       {len(routing.tb_files)}")
    if verbose:
        for f in routing.tb_files:
            print(f"                  - {f}")
    
    # Errors
    if routing.errors:
        print(f"\n  {color_text('ERRORS:', Colors.RED)}")
        for err in routing.errors:
            print(f"    {color_text('✗', Colors.RED)} {err}")
    
    # Warnings
    if routing.warnings:
        print(f"\n  {color_text('WARNINGS:', Colors.YELLOW)}")
        for warn in routing.warnings:
            print(f"    {color_text('⚠', Colors.YELLOW)} {warn}")
    
    # Recommendations
    if routing.recommendations:
        print(f"\n  {color_text('RECOMMENDATIONS:', Colors.CYAN)}")
        for rec in routing.recommendations:
            print(f"    {rec}")
    
    print("\n" + "=" * 60)
    
    # Final verdict
    if routing.is_valid():
        print(color_text("\n✓ Routing successful - ready for execution\n", Colors.GREEN))
    else:
        print(color_text("\n✗ Routing failed - see errors above\n", Colors.RED))


def print_quality_summary(quality_report):
    """Print quality report summary"""
    if not quality_report:
        return
    
    print("\n" + "-" * 60)
    print(color_text(" QUALITY GATE RESULTS", Colors.BOLD))
    print("-" * 60)
    
    status_color = {
        "pass": Colors.GREEN,
        "warning": Colors.YELLOW,
        "fail": Colors.RED,
        "skipped": Colors.CYAN
    }
    
    print(f"\n  Linter:         {quality_report.linter}")
    print(f"  Status:         {color_text(quality_report.status.upper(), status_color.get(quality_report.status, Colors.ENDC))}")
    print(f"  Files Checked:  {quality_report.files_checked}/{quality_report.total_files}")
    print(f"  Violations:     {quality_report.total_violations}")
    
    if quality_report.critical_errors > 0:
        print(f"  Critical:       {color_text(str(quality_report.critical_errors), Colors.RED)}")
    if quality_report.warnings > 0:
        print(f"  Warnings:       {color_text(str(quality_report.warnings), Colors.YELLOW)}")
    if quality_report.style_issues > 0:
        print(f"  Style Issues:   {quality_report.style_issues}")
    
    print("-" * 60)


def create_parser() -> argparse.ArgumentParser:
    """Create argument parser"""
    parser = argparse.ArgumentParser(
        prog="tbeval-classify",
        description="Step 2: Classify and Route RTL Testbench Submission",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s ./my_project
  %(prog)s ./my_project -o results/route.json
  %(prog)s ./my_project --quality-gate blocking -v
  %(prog)s ./my_project --no-quality-gate --json

For more information, see: https://github.com/your-repo/tb-eval
"""
    )
    
    # Positional arguments
    parser.add_argument(
        "submission_dir",
        type=Path,
        help="Path to submission directory containing RTL and testbench files"
    )
    
    # Output options
    output_group = parser.add_argument_group("Output Options")
    output_group.add_argument(
        "-o", "--output",
        type=Path,
        default=None,
        help="Output path for route.json (default: <submission_dir>/route.json)"
    )
    output_group.add_argument(
        "--quality-output",
        type=Path,
        default=None,
        help="Output path for quality_report.json"
    )
    output_group.add_argument(
        "--json",
        action="store_true",
        help="Output only JSON (no human-readable summary)"
    )
    
    # Quality gate options
    qg_group = parser.add_argument_group("Quality Gate Options")
    qg_group.add_argument(
        "--quality-gate",
        choices=["blocking", "advisory", "disabled"],
        default=None,
        help="Quality gate mode (overrides config file)"
    )
    qg_group.add_argument(
        "--no-quality-gate",
        action="store_true",
        help="Disable quality gate (shortcut for --quality-gate disabled)"
    )
    qg_group.add_argument(
        "--verible-rules",
        type=Path,
        default=None,
        help="Path to Verible rules configuration file"
    )
    
    # Configuration options
    config_group = parser.add_argument_group("Configuration")
    config_group.add_argument(
        "-c", "--config",
        type=Path,
        default=None,
        help="Path to configuration file (.tbeval.yaml)"
    )
    config_group.add_argument(
        "--simulator",
        choices=["verilator", "icarus", "ghdl", "auto"],
        default=None,
        help="Preferred simulator (overrides config/manifest)"
    )
    
    # Verbosity
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Verbose output (show file lists)"
    )
    parser.add_argument(
        "-q", "--quiet",
        action="store_true",
        help="Quiet mode (minimal output)"
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Debug mode (show stack traces)"
    )
    
    # Version
    parser.add_argument(
        "--version",
        action="version",
        version="%(prog)s 0.1.0"
    )
    
    return parser


def main(args: Optional[list] = None) -> int:
    """
    Main CLI entry point
    
    Returns:
        0 on success
        1 on routing failure
        2 on invalid arguments
        3 on unexpected error
    """
    parser = create_parser()
    parsed_args = parser.parse_args(args)
    
    # Validate submission directory
    if not parsed_args.submission_dir.exists():
        print(f"Error: Submission directory not found: {parsed_args.submission_dir}", 
              file=sys.stderr)
        return 2
    
    if not parsed_args.submission_dir.is_dir():
        print(f"Error: Path is not a directory: {parsed_args.submission_dir}",
              file=sys.stderr)
        return 2
    
    try:
        # Print banner unless quiet or json mode
        if not parsed_args.quiet and not parsed_args.json:
            print_banner()
            print(f"Analyzing: {parsed_args.submission_dir.absolute()}\n")
        
        # Load configuration
        config = ConfigManager.load_config(
            config_path=parsed_args.config,
            search_dir=parsed_args.submission_dir
        )
        
        # Apply CLI overrides
        if parsed_args.no_quality_gate:
            config.quality_gate_mode = "disabled"
        elif parsed_args.quality_gate:
            config.quality_gate_mode = parsed_args.quality_gate
        
        if parsed_args.verible_rules:
            config.verible_rules_file = str(parsed_args.verible_rules)
        
        if parsed_args.simulator:
            config.preferred_simulator = parsed_args.simulator
        
        # Run classification
        classifier = ClassifierRouter(parsed_args.submission_dir, config)
        
        run_quality = config.quality_gate_mode != "disabled"
        routing = classifier.classify_and_route(run_quality_gate=run_quality)
        
        # Save outputs
        output_path = parsed_args.output or (parsed_args.submission_dir / "route.json")
        classifier.save_routing(routing, output_path)
        
        quality_output = parsed_args.quality_output or (
            parsed_args.submission_dir / "quality_report.json"
        )
        if classifier.quality_report:
            classifier.save_quality_report(quality_output)
        
        # Output results
        if parsed_args.json:
            # JSON only mode
            print(json.dumps(routing.to_dict(), indent=2))
        elif not parsed_args.quiet:
            # Human readable output
            print_routing_summary(routing, verbose=parsed_args.verbose)
            
            if classifier.quality_report and run_quality:
                print_quality_summary(classifier.quality_report)
            
            print(f"\nOutputs saved to:")
            print(f"  - {output_path}")
            if classifier.quality_report:
                print(f"  - {quality_output}")
        
        # Return appropriate exit code
        if routing.is_valid():
            return 0
        else:
            return 1
    
    except KeyboardInterrupt:
        print("\n\nOperation cancelled by user.", file=sys.stderr)
        return 130
    
    except Exception as e:
        if parsed_args.debug:
            raise
        print(f"\nError: {str(e)}", file=sys.stderr)
        return 3


if __name__ == "__main__":
    sys.exit(main())
