#!/usr/bin/env python3
"""
Step 3 CLI: Build & Orchestrate
===============================

Full command-line interface for the build phase with:
- Rich progress output
- Colored status messages
- JSON output mode
- Comprehensive error reporting

Author: TB Eval Team
Version: 0.1.0
"""

import argparse
import json
import os
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict, Any

from ..orchestrator import (
    VUnitOrchestrator,
    OrchestratorPhase,
    OrchestratorState,
    PhaseResult,
    build_project,
)
from ..models import (
    BuildStatus,
    BuildManifest,
    SimulatorType,
    FailureMode,
)
from ..config import BuildConfigManager


# =============================================================================
# TERMINAL COLORS AND FORMATTING
# =============================================================================

class Colors:
    """ANSI color codes for terminal output"""
    # Basic colors
    BLACK = '\033[30m'
    RED = '\033[31m'
    GREEN = '\033[32m'
    YELLOW = '\033[33m'
    BLUE = '\033[34m'
    MAGENTA = '\033[35m'
    CYAN = '\033[36m'
    WHITE = '\033[37m'
    
    # Bright colors
    BRIGHT_RED = '\033[91m'
    BRIGHT_GREEN = '\033[92m'
    BRIGHT_YELLOW = '\033[93m'
    BRIGHT_BLUE = '\033[94m'
    BRIGHT_MAGENTA = '\033[95m'
    BRIGHT_CYAN = '\033[96m'
    
    # Styles
    BOLD = '\033[1m'
    DIM = '\033[2m'
    ITALIC = '\033[3m'
    UNDERLINE = '\033[4m'
    
    # Reset
    RESET = '\033[0m'
    ENDC = '\033[0m'
    
    @classmethod
    def disable(cls):
        """Disable all colors"""
        for attr in dir(cls):
            if not attr.startswith('_') and attr.isupper():
                setattr(cls, attr, '')


class Symbols:
    """Unicode symbols for status indicators"""
    CHECK = '✓'
    CROSS = '✗'
    WARNING = '⚠'
    INFO = 'ℹ'
    ARROW = '→'
    BULLET = '•'
    SPINNER = ['⠋', '⠙', '⠹', '⠸', '⠼', '⠴', '⠦', '⠧', '⠇', '⠏']
    PROGRESS = ['▱▱▱▱▱', '▰▱▱▱▱', '▰▰▱▱▱', '▰▰▰▱▱', '▰▰▰▰▱', '▰▰▰▰▰']
    BOX_TOP = '┌─'
    BOX_BOTTOM = '└─'
    BOX_SIDE = '│'


def supports_color() -> bool:
    """Check if terminal supports color"""
    if not sys.stdout.isatty():
        return False
    if os.environ.get('NO_COLOR'):
        return False
    if os.environ.get('TERM') == 'dumb':
        return False
    return True


def color(text: str, *colors: str) -> str:
    """Apply colors to text if supported"""
    if not supports_color():
        return text
    color_codes = ''.join(colors)
    return f"{color_codes}{text}{Colors.RESET}"


def format_duration(ms: float) -> str:
    """Format duration in human readable form"""
    if ms < 1000:
        return f"{ms:.0f}ms"
    elif ms < 60000:
        return f"{ms/1000:.1f}s"
    else:
        minutes = int(ms / 60000)
        seconds = (ms % 60000) / 1000
        return f"{minutes}m {seconds:.0f}s"


def format_count(count: int, singular: str, plural: str = None) -> str:
    """Format count with singular/plural"""
    if plural is None:
        plural = singular + 's'
    return f"{count} {singular if count == 1 else plural}"


# =============================================================================
# PROGRESS DISPLAY
# =============================================================================

class ProgressDisplay:
    """
    Handles progress display during build
    
    Supports:
    - Spinner animation
    - Phase progress
    - Status messages
    - Error/warning display
    """
    
    def __init__(self, verbose: bool = False, quiet: bool = False):
        self.verbose = verbose
        self.quiet = quiet
        self.current_phase: Optional[OrchestratorPhase] = None
        self.spinner_idx = 0
        self.start_time = time.time()
        self._last_message = ""
    
    def print_banner(self):
        """Print CLI banner"""
        if self.quiet:
            return
        
        banner = f"""
{color('╔═══════════════════════════════════════════════════════════════╗', Colors.CYAN)}
{color('║', Colors.CYAN)}          {color('TB Evaluation Framework - Step 3', Colors.BOLD)}               {color('║', Colors.CYAN)}
{color('║', Colors.CYAN)}                {color('Build & Orchestrate', Colors.DIM)}                        {color('║', Colors.CYAN)}
{color('╚═══════════════════════════════════════════════════════════════╝', Colors.CYAN)}
"""
        print(banner)
    
    def print_config_summary(self, submission_dir: Path, config: Dict[str, Any]):
        """Print configuration summary"""
        if self.quiet:
            return
        
        print(f"\n{color('Configuration:', Colors.BOLD)}")
        print(f"  {color('Submission:', Colors.DIM)} {submission_dir}")
        print(f"  {color('Simulator:', Colors.DIM)}  {config.get('simulator', 'auto')}")
        print(f"  {color('Coverage:', Colors.DIM)}   {'enabled' if config.get('coverage', True) else 'disabled'}")
        print(f"  {color('Mode:', Colors.DIM)}       {config.get('failure_mode', 'advisory')}")
        print()
    
    def phase_start(self, phase: OrchestratorPhase):
        """Called when a phase starts"""
        self.current_phase = phase
        
        if self.quiet:
            return
        
        phase_names = {
            OrchestratorPhase.CONFIG: "Loading configuration",
            OrchestratorPhase.PROJECT_SETUP: "Setting up VUnit project",
            OrchestratorPhase.SIMULATOR_CONFIG: "Configuring simulator",
            OrchestratorPhase.COMPILATION: "Compiling sources",
            OrchestratorPhase.TEST_DISCOVERY: "Discovering tests",
            OrchestratorPhase.FINALIZE: "Finalizing build",
        }
        
        name = phase_names.get(phase, phase.value)
        
        # Print phase header
        print(f"\n{color(Symbols.ARROW, Colors.CYAN)} {color(name, Colors.BOLD)}...")
    
    def phase_complete(self, result: PhaseResult):
        """Called when a phase completes"""
        if self.quiet:
            return
        
        # Status indicator
        if result.success:
            status = color(f"{Symbols.CHECK} Done", Colors.GREEN)
        else:
            status = color(f"{Symbols.CROSS} Failed", Colors.RED)
        
        # Duration
        duration = color(f"({format_duration(result.duration_ms)})", Colors.DIM)
        
        # Print result
        print(f"  {status} {duration}")
        
        # Print errors
        if result.errors:
            for error in result.errors:
                print(f"    {color(Symbols.CROSS, Colors.RED)} {color(error, Colors.RED)}")
        
        # Print warnings (verbose only or if no errors)
        if result.warnings and (self.verbose or not result.errors):
            for warning in result.warnings[:5]:  # Limit to 5
                print(f"    {color(Symbols.WARNING, Colors.YELLOW)} {color(warning, Colors.YELLOW)}")
            if len(result.warnings) > 5:
                print(f"    {color(f'... and {len(result.warnings) - 5} more warnings', Colors.DIM)}")
        
        # Print verbose data
        if self.verbose and result.data:
            for key, value in result.data.items():
                if isinstance(value, (str, int, float, bool)):
                    print(f"    {color(key + ':', Colors.DIM)} {value}")
    
    def progress(self, message: str):
        """Print progress message"""
        if self.quiet:
            return
        
        if self.verbose:
            elapsed = time.time() - self.start_time
            timestamp = color(f"[{elapsed:.1f}s]", Colors.DIM)
            print(f"  {timestamp} {message}")
        else:
            # Update spinner
            self._last_message = message
    
    def error(self, message: str, phase: Optional[OrchestratorPhase] = None):
        """Print error message"""
        phase_str = f"[{phase.value}] " if phase else ""
        print(f"{color(Symbols.CROSS, Colors.RED)} {color('Error:', Colors.RED, Colors.BOLD)} {phase_str}{message}", 
              file=sys.stderr)
    
    def warning(self, message: str, phase: Optional[OrchestratorPhase] = None):
        """Print warning message"""
        if self.quiet:
            return
        phase_str = f"[{phase.value}] " if phase else ""
        print(f"{color(Symbols.WARNING, Colors.YELLOW)} {color('Warning:', Colors.YELLOW)} {phase_str}{message}")


# =============================================================================
# BUILD SUMMARY
# =============================================================================

class BuildSummary:
    """Generates and displays build summary"""
    
    def __init__(self, manifest: BuildManifest, verbose: bool = False):
        self.manifest = manifest
        self.verbose = verbose
    
    def print_summary(self):
        """Print complete build summary"""
        m = self.manifest
        
        # Header
        print("\n" + "=" * 65)
        print(color(" BUILD SUMMARY", Colors.BOLD))
        print("=" * 65)
        
        # Status
        status_color = {
            BuildStatus.SUCCESS: Colors.GREEN,
            BuildStatus.WARNING: Colors.YELLOW,
            BuildStatus.FAILURE: Colors.RED,
            BuildStatus.PENDING: Colors.DIM,
        }.get(m.build_status, Colors.WHITE)
        
        status_symbol = {
            BuildStatus.SUCCESS: Symbols.CHECK,
            BuildStatus.WARNING: Symbols.WARNING,
            BuildStatus.FAILURE: Symbols.CROSS,
        }.get(m.build_status, Symbols.INFO)
        
        print(f"\n  {color('Status:', Colors.DIM)}     {color(status_symbol + ' ' + m.build_status.value.upper(), status_color, Colors.BOLD)}")
        print(f"  {color('Duration:', Colors.DIM)}   {format_duration(m.duration_ms)}")
        print(f"  {color('Timestamp:', Colors.DIM)}  {m.timestamp}")
        
        # VUnit Project
        if m.vunit_project:
            print(f"\n  {color('VUnit Project:', Colors.BOLD)}")
            print(f"    {color('Run script:', Colors.DIM)} {m.vunit_project.run_py_path}")
            print(f"    {color('Generated:', Colors.DIM)}  {'Yes' if m.vunit_project.generated else 'No (existing)'}")
        
        # Compilation
        if m.compilation:
            print(f"\n  {color('Compilation:', Colors.BOLD)}")
            comp_status = color(Symbols.CHECK + " Success", Colors.GREEN) if m.compilation.is_success() else color(Symbols.CROSS + " Failed", Colors.RED)
            print(f"    {color('Status:', Colors.DIM)}   {comp_status}")
            print(f"    {color('Files:', Colors.DIM)}    {m.compilation.total_files}")
            
            if m.compilation.total_errors > 0:
                print(f"    {color('Errors:', Colors.DIM)}   {color(str(m.compilation.total_errors), Colors.RED)}")
            if m.compilation.total_warnings > 0:
                print(f"    {color('Warnings:', Colors.DIM)} {color(str(m.compilation.total_warnings), Colors.YELLOW)}")
        
        # Tests
        if m.tests_discovered:
            print(f"\n  {color('Tests Discovered:', Colors.BOLD)}")
            test_count = m.tests_discovered.total_count
            ready_count = m.tests_discovered.ready_count
            
            if test_count > 0:
                print(f"    {color('Total:', Colors.DIM)}  {test_count}")
                print(f"    {color('Ready:', Colors.DIM)}  {color(str(ready_count), Colors.GREEN)}")
                
                if m.tests_discovered.skipped_count > 0:
                    print(f"    {color('Skipped:', Colors.DIM)} {color(str(m.tests_discovered.skipped_count), Colors.YELLOW)}")
                
                # Show first few tests if verbose
                if self.verbose and m.tests_discovered.tests:
                    print(f"\n    {color('Test list:', Colors.DIM)}")
                    for test in m.tests_discovered.tests[:10]:
                        print(f"      {Symbols.BULLET} {test.full_name}")
                    if len(m.tests_discovered.tests) > 10:
                        print(f"      {color(f'... and {len(m.tests_discovered.tests) - 10} more', Colors.DIM)}")
            else:
                print(f"    {color('No tests discovered', Colors.YELLOW)}")
        
        # Coverage
        if m.coverage_config:
            print(f"\n  {color('Coverage:', Colors.BOLD)}")
            if m.coverage_config.enabled:
                types = ", ".join(t.value for t in m.coverage_config.types)
                print(f"    {color('Enabled:', Colors.DIM)} Yes")
                print(f"    {color('Types:', Colors.DIM)}   {types}")
            else:
                print(f"    {color('Enabled:', Colors.DIM)} No")
        
        # Errors
        if m.errors:
            print(f"\n  {color('Errors:', Colors.RED, Colors.BOLD)} ({len(m.errors)})")
            for error in m.errors:
                print(f"    {color(Symbols.CROSS, Colors.RED)} {error}")
        
        # Warnings
        if m.warnings:
            print(f"\n  {color('Warnings:', Colors.YELLOW, Colors.BOLD)} ({len(m.warnings)})")
            for warning in m.warnings[:10]:
                print(f"    {color(Symbols.WARNING, Colors.YELLOW)} {warning}")
            if len(m.warnings) > 10:
                print(f"    {color(f'... and {len(m.warnings) - 10} more', Colors.DIM)}")
        
        # Footer
        print("\n" + "=" * 65)
        
        # Final verdict
        if m.is_ready_for_execution():
            print(color(f"\n{Symbols.CHECK} Build successful - ready for test execution", Colors.GREEN, Colors.BOLD))
            print(f"  {color('Next step:', Colors.DIM)} tbeval-run {m.submission_dir}")
        elif m.build_status == BuildStatus.WARNING:
            print(color(f"\n{Symbols.WARNING} Build completed with warnings", Colors.YELLOW, Colors.BOLD))
            print(f"  {color('Review warnings above before proceeding', Colors.DIM)}")
        else:
            print(color(f"\n{Symbols.CROSS} Build failed - see errors above", Colors.RED, Colors.BOLD))
        
        print()
    
    def print_json(self):
        """Print JSON output"""
        print(self.manifest.to_json(indent=2))


# =============================================================================
# ARGUMENT PARSER
# =============================================================================

def create_parser() -> argparse.ArgumentParser:
    """Create argument parser for Step 3 CLI"""
    
    parser = argparse.ArgumentParser(
        prog="tbeval-build",
        description="""
Step 3: Build & Orchestrate

Compiles sources and prepares for test execution using VUnit.
This step:
  1. Loads configuration from route.json and .tbeval.yaml
  2. Detects or generates VUnit project
  3. Configures simulator (Questa, Verilator, GHDL)
  4. Compiles all sources
  5. Discovers tests
  6. Generates build manifest
        """,
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s ./my_project                    Build project
  %(prog)s ./my_project --simulator questa Use Questa simulator
  %(prog)s ./my_project --no-coverage      Disable coverage
  %(prog)s ./my_project --compile-only     Compile without test discovery
  %(prog)s ./my_project --list             List tests without building
  %(prog)s ./my_project -v                 Verbose output
  %(prog)s ./my_project --json             JSON output for scripting

For more information: https://github.com/your-org/tb-eval-framework
        """
    )
    
    # Positional arguments
    parser.add_argument(
        "submission_dir",
        type=Path,
        help="Path to submission directory"
    )
    
    # Input options
    input_group = parser.add_argument_group("Input Options")
    input_group.add_argument(
        "--route", "-r",
        type=Path,
        default=None,
        metavar="FILE",
        help="Path to route.json (default: <submission_dir>/route.json)"
    )
    input_group.add_argument(
        "--config", "-c",
        type=Path,
        default=None,
        metavar="FILE",
        help="Path to .tbeval.yaml configuration file"
    )
    
    # Output options
    output_group = parser.add_argument_group("Output Options")
    output_group.add_argument(
        "--output", "-o",
        type=Path,
        default=None,
        metavar="DIR",
        help="Output directory (default: <submission_dir>/.tbeval)"
    )
    output_group.add_argument(
        "--manifest",
        type=Path,
        default=None,
        metavar="FILE",
        help="Path for build manifest (default: <output>/build_manifest.json)"
    )
    
    # Simulator options
    sim_group = parser.add_argument_group("Simulator Options")
    sim_group.add_argument(
        "--simulator", "-s",
        choices=["questa", "modelsim", "verilator", "ghdl", "auto"],
        default=None,
        help="Simulator to use (overrides config)"
    )
    sim_group.add_argument(
        "--questa-path",
        type=Path,
        default=None,
        metavar="PATH",
        help="Path to Questa installation"
    )
    sim_group.add_argument(
        "--license-server",
        type=str,
        default=None,
        metavar="SERVER",
        help="License server (e.g., 1234@server.com)"
    )
    
    # Build options
    build_group = parser.add_argument_group("Build Options")
    build_group.add_argument(
        "--coverage/--no-coverage",
        dest="coverage",
        default=None,
        action=argparse.BooleanOptionalAction,
        help="Enable/disable coverage collection"
    )
    build_group.add_argument(
        "--clean",
        action="store_true",
        help="Force clean build (remove existing artifacts)"
    )
    build_group.add_argument(
        "--parallel", "-p",
        type=int,
        default=None,
        metavar="N",
        help="Number of parallel compilation jobs"
    )
    build_group.add_argument(
        "--failure-mode",
        choices=["blocking", "advisory"],
        default=None,
        help="How to handle build failures"
    )
    
    # Mode options
    mode_group = parser.add_argument_group("Mode Options")
    mode_group.add_argument(
        "--compile-only",
        action="store_true",
        help="Compile only, skip test discovery"
    )
    mode_group.add_argument(
        "--list",
        action="store_true",
        help="List discovered tests without full build"
    )
    mode_group.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be done without executing"
    )
    
    # Output format options
    format_group = parser.add_argument_group("Output Format")
    format_group.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Verbose output"
    )
    format_group.add_argument(
        "--quiet", "-q",
        action="store_true",
        help="Quiet mode (minimal output)"
    )
    format_group.add_argument(
        "--json",
        action="store_true",
        help="Output JSON only (for scripting)"
    )
    format_group.add_argument(
        "--no-color",
        action="store_true",
        help="Disable colored output"
    )
    
    # Version
    parser.add_argument(
        "--version",
        action="version",
        version="%(prog)s 0.1.0 (TB Eval Framework)"
    )
    
    return parser


# =============================================================================
# MAIN FUNCTION
# =============================================================================

def main(argv: Optional[List[str]] = None) -> int:
    """
    Main CLI entry point
    
    Args:
        argv: Command line arguments (default: sys.argv[1:])
    
    Returns:
        Exit code (0 for success, non-zero for failure)
    """
    # Parse arguments
    parser = create_parser()
    args = parser.parse_args(argv)
    
    # Handle color settings
    if args.no_color or args.json:
        Colors.disable()
    
    # Create progress display
    progress = ProgressDisplay(
        verbose=args.verbose,
        quiet=args.quiet or args.json
    )
    
    # Validate submission directory
    if not args.submission_dir.exists():
        progress.error(f"Submission directory not found: {args.submission_dir}")
        return 2
    
    if not args.submission_dir.is_dir():
        progress.error(f"Path is not a directory: {args.submission_dir}")
        return 2
    
    # Check for route.json
    route_path = args.route or (args.submission_dir / "route.json")
    if not route_path.exists() and not args.dry_run:
        progress.error(f"route.json not found: {route_path}")
        progress.error("Run Step 2 (tbeval-classify) first")
        return 2
    
    # Build configuration overrides
    overrides = {}
    
    if args.simulator:
        overrides["simulator"] = args.simulator
    if args.coverage is not None:
        if args.coverage:
            overrides["coverage"] = True
        else:
            overrides["no_coverage"] = True
    if args.clean:
        overrides["clean"] = True
    if args.parallel:
        overrides["parallel"] = args.parallel
    if args.failure_mode:
        overrides["failure_mode"] = args.failure_mode
    if args.questa_path:
        overrides["questa_path"] = str(args.questa_path)
    if args.license_server:
        overrides["license_server"] = args.license_server
    
    # Print banner
    if not args.json:
        progress.print_banner()
    
    # Dry run mode
    if args.dry_run:
        print(color("\nDry run mode - showing configuration:\n", Colors.CYAN))
        print(f"  Submission: {args.submission_dir}")
        print(f"  Route JSON: {route_path}")
        print(f"  Output: {args.output or args.submission_dir / '.tbeval'}")
        print(f"  Overrides: {json.dumps(overrides, indent=4)}")
        return 0
    
    # Print configuration summary
    if not args.json and not args.quiet:
        config_summary = {
            "simulator": overrides.get("simulator", "auto"),
            "coverage": overrides.get("coverage", True),
            "failure_mode": overrides.get("failure_mode", "advisory"),
        }
        progress.print_config_summary(args.submission_dir, config_summary)
    
    # Create orchestrator
    try:
        orchestrator = VUnitOrchestrator(
            submission_dir=args.submission_dir,
            route_json_path=route_path,
            config_overrides=overrides,
            output_dir=args.output,
        )
        
        # Set up callbacks
        if not args.json:
            orchestrator.callbacks.on_phase_start = progress.phase_start
            orchestrator.callbacks.on_phase_complete = progress.phase_complete
            orchestrator.callbacks.on_progress = progress.progress
            orchestrator.callbacks.on_error = progress.error
            orchestrator.callbacks.on_warning = progress.warning
        
        # Determine what to run
        if args.list:
            # List tests only - run through test discovery
            manifest = orchestrator.run_until(OrchestratorPhase.TEST_DISCOVERY)
        elif args.compile_only:
            # Compile only - stop before test discovery
            manifest = orchestrator.run_until(OrchestratorPhase.COMPILATION)
        else:
            # Full build
            manifest = orchestrator.run()
        
        # Handle manifest path override
        if args.manifest:
            manifest.save(args.manifest)
        
    except KeyboardInterrupt:
        print(color("\n\nBuild cancelled by user.", Colors.YELLOW))
        return 130
    
    except Exception as e:
        if args.verbose:
            import traceback
            traceback.print_exc()
        progress.error(f"Build failed with exception: {str(e)}")
        return 3
    
    # Output results
    summary = BuildSummary(manifest, verbose=args.verbose)
    
    if args.json:
        summary.print_json()
    else:
        summary.print_summary()
    
    # List mode - print test list
    if args.list and manifest.tests_discovered:
        if not args.json:
            print(color("\nDiscovered Tests:", Colors.BOLD))
            print("-" * 40)
            for test in manifest.tests_discovered.tests:
                status_icon = color(Symbols.CHECK, Colors.GREEN) if test.status.value == "ready" else color(Symbols.BULLET, Colors.DIM)
                print(f"  {status_icon} {test.full_name}")
            print("-" * 40)
            print(f"Total: {len(manifest.tests_discovered.tests)} tests")
    
    # Return appropriate exit code
    if manifest.is_success():
        return 0
    elif manifest.build_status == BuildStatus.WARNING:
        return 0  # Warnings don't fail
    else:
        return 1


# =============================================================================
# ENTRY POINT
# =============================================================================

if __name__ == "__main__":
    sys.exit(main())
