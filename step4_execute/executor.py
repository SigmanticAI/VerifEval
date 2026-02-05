"""
Main test executor orchestrator

Coordinates the entire test execution process:
- Loads configuration and manifest
- Selects and initializes appropriate runner
- Executes tests with timeout/retry
- Collects coverage
- Generates test report

Author: TB Eval Team
Version: 0.1.0
"""

import asyncio
import signal
import sys
from pathlib import Path
from typing import List, Optional, Dict, Any
from datetime import datetime
import json
import os
import socket

from .config import ExecutionConfig, ConfigManager
from .models import (
    TestReport,
    TestResult,
    TestSummary,
    ExecutionStatus,
    ExecutionMetadata,
    ExecutionContext,
    Diagnostics,
    ExitCode,
    TestOutcome,
)
from .runners import VUnitRunner, CocoTBRunner
from .parsers.coverage_locator import CoverageLocator, CoverageValidator
from .handlers.output_handler import OutputFormatter, StreamingOutputHandler, OutputLevel
from .handlers.timeout_handler import TimeoutManager


class TestExecutor:
    """
    Main test execution orchestrator
    
    This is the central coordinator for Step 4 execution.
    
    Workflow:
    1. Load manifest and configuration
    2. Validate environment
    3. Select runner (CocoTB or VUnit)
    4. Execute tests
    5. Collect coverage
    6. Generate report
    """
    
    def __init__(
        self,
        submission_dir: Path,
        config: Optional[ExecutionConfig] = None,
        manifest_path: Optional[Path] = None,
    ):
        """
        Initialize test executor
        
        Args:
            submission_dir: Path to submission directory
            config: Execution configuration (loaded if None)
            manifest_path: Path to build manifest (auto-detected if None)
        """
        self.submission_dir = Path(submission_dir).resolve()
        
        # Load configuration if not provided
        if config is None:
            config_manager = ConfigManager(self.submission_dir)
            config = config_manager.load(manifest_path)
        
        self.config = config
        
        # Load build manifest
        self.manifest = self._load_manifest(manifest_path or config.manifest_path)
        
        # Initialize components
        self.formatter = OutputFormatter(use_color=config.output.color)
        self.output_handler = self._create_output_handler()
        self.timeout_manager = TimeoutManager(
            config=config.timeouts,
            warning_callback=self._on_timeout_warning,
        )
        
        # Execution state
        self.report = TestReport()
        self.runner: Optional[Any] = None
        self.interrupted = False
        self.start_time: Optional[datetime] = None
        
        # Setup signal handlers
        self._setup_signal_handlers()
    
    def _load_manifest(self, manifest_path: Optional[Path]) -> Dict[str, Any]:
        """
        Load build manifest from Step 3
        
        Args:
            manifest_path: Path to manifest (auto-detected if None)
        
        Returns:
            Manifest dictionary
        
        Raises:
            FileNotFoundError: If manifest not found
            ValueError: If manifest is invalid
        """
        # Try to find manifest
        if manifest_path is None:
            # Try common locations
            candidates = [
                self.submission_dir / ".tbeval" / "build_manifest.json",
                self.submission_dir / "build_manifest.json",
            ]
            
            for candidate in candidates:
                if candidate.exists():
                    manifest_path = candidate
                    break
        
        if manifest_path is None or not Path(manifest_path).exists():
            raise FileNotFoundError(
                f"Build manifest not found. "
                f"Please run Step 3 (build) first or specify manifest path."
            )
        
        # Load and validate manifest
        try:
            with open(manifest_path) as f:
                manifest = json.load(f)
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid manifest JSON: {e}")
        
        # Basic validation
        required_fields = ["schema_version", "build_status", "track_used"]
        missing = [f for f in required_fields if f not in manifest]
        
        if missing:
            raise ValueError(f"Manifest missing required fields: {missing}")
        
        # Check build was successful
        if manifest.get("build_status") != "success":
            raise ValueError(
                f"Build was not successful (status: {manifest.get('build_status')}). "
                f"Cannot execute tests."
            )
        
        return manifest
    
    def _create_output_handler(self) -> StreamingOutputHandler:
        """Create output handler based on config"""
        # Map verbosity
        level_map = {
            "minimal": OutputLevel.MINIMAL,
            "normal": OutputLevel.NORMAL,
            "verbose": OutputLevel.VERBOSE,
            "debug": OutputLevel.DEBUG,
        }
        level = level_map.get(self.config.output.verbosity, OutputLevel.NORMAL)
        
        return StreamingOutputHandler(
            level=level,
            formatter=self.formatter,
            output_stream=sys.stdout,
            show_timestamps=False,
        )
    
    def _setup_signal_handlers(self):
        """Setup signal handlers for graceful shutdown"""
        def signal_handler(signum, frame):
            self._on_interrupt(signum)
        
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
    
    def _on_interrupt(self, signum: int):
        """Handle interrupt signal"""
        if not self.interrupted:
            self.interrupted = True
            signal_name = signal.Signals(signum).name
            
            print(f"\n{self.formatter.warning(f'Received {signal_name} - shutting down gracefully...')}")
            print(self.formatter.dim("(Press Ctrl+C again to force quit)"))
        else:
            # Second interrupt - force quit
            print(f"\n{self.formatter.error('Forcing shutdown...')}")
            sys.exit(130)  # 128 + SIGINT
    
    def _on_timeout_warning(self, message: str):
        """Handle timeout warning"""
        print(f"{self.formatter.warning('⏱ ' + message)}")
    
    async def execute(self) -> TestReport:
        """
        Execute all tests and generate report
        
        Returns:
            TestReport with execution results
        
        Raises:
            RuntimeError: If execution fails critically
        """
        self.start_time = datetime.now()
        
        try:
            # Initialize report metadata
            self._initialize_report()
            
            # Print header
            self._print_header()
            
            # Validate environment
            if not await self._validate_environment():
                self.report.status = ExecutionStatus.ERROR
                self.report.completion_reason = "environment_validation_failed"
                return self.report
            
            # Dry run check
            if self.config.dry_run:
                return await self._dry_run()
            
            # Initialize runner
            self._initialize_runner()
            
            # Start global timeout
            self.timeout_manager.start_global_timeout()
            
            # Execute tests
            self.report.status = ExecutionStatus.RUNNING
            await self._execute_tests()
            
            # Collect coverage
            if self.config.coverage.enabled:
                await self._collect_coverage()
            
            # Finalize report
            self._finalize_report()
            
            # Save report
            await self._save_report()
            
            return self.report
        
        except KeyboardInterrupt:
            return await self._handle_interruption()
        
        except Exception as e:
            return await self._handle_error(e)
    
    def _initialize_report(self):
        """Initialize test report with metadata"""
        # Execution metadata
        self.report.execution_metadata = ExecutionMetadata(
            timestamp=datetime.now().isoformat(),
            hostname=socket.gethostname(),
            username=os.environ.get('USER', os.environ.get('USERNAME')),
            working_directory=str(self.submission_dir),
            build_manifest=str(self.config.manifest_path) if self.config.manifest_path else None,
            command=' '.join(sys.argv),
            framework_version=self.report.framework_version,
            python_version=f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
            environment={
                k: v for k, v in os.environ.items()
                if k.startswith('TB') or k in ['SIM', 'COVERAGE']
            },
        )
        
        # Initialize summary with test count
        tests = self.manifest.get("tests_discovered", {}).get("tests", [])
        self.report.summary.total_tests = len(tests)
        
        # Artifact directories
        output_dir = self.config.output_dir
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        run_dir = output_dir / f"run_{timestamp}"
        
        self.report.artifacts_root = str(run_dir)
        self.report.logs_directory = str(run_dir / "logs")
        self.report.waveforms_directory = str(run_dir / "waveforms")
        self.report.coverage_directory = str(run_dir / "coverage")
        
        # Create directories
        for directory in [
            self.report.logs_directory,
            self.report.waveforms_directory,
            self.report.coverage_directory,
        ]:
            Path(directory).mkdir(parents=True, exist_ok=True)
    
    def _print_header(self):
        """Print execution header"""
        print(f"\n{self.formatter.bold('=' * 70)}")
        print(f"{self.formatter.bold('TB Eval Framework - Step 4: Test Execution')}")
        print(f"{self.formatter.bold('=' * 70)}\n")
        
        # Submission info
        print(f"Submission: {self.formatter.bold(str(self.submission_dir))}")
        print(f"Track:      {self.formatter.bold(self.manifest.get('track_used', 'Unknown'))}")
        
        # Test count
        total_tests = self.report.summary.total_tests
        print(f"Tests:      {self.formatter.bold(str(total_tests))}")
        
        # Configuration
        if self.config.dry_run:
            print(f"\n{self.formatter.warning('DRY RUN MODE - No tests will be executed')}")
        
        if self.config.test_filter:
            print(f"Filter:     {self.formatter.info(self.config.test_filter)}")
        
        print(f"\n{self.formatter.dim('─' * 70)}\n")
    
    async def _validate_environment(self) -> bool:
        """
        Validate execution environment
        
        Returns:
            True if environment is valid
        """
        print(f"{self.formatter.info('Validating environment...')}")
        
        validation_errors = []
        
        # Check working directory
        if not self.submission_dir.exists():
            validation_errors.append(f"Submission directory not found: {self.submission_dir}")
        
        # Runner will validate simulator, etc.
        # We'll check that in _initialize_runner
        
        if validation_errors:
            print(f"{self.formatter.error('✗ Environment validation failed:')}")
            for error in validation_errors:
                print(f"  {self.formatter.error('•')} {error}")
            
            self.report.diagnostics.errors.extend(validation_errors)
            return False
        
        print(f"{self.formatter.success('✓ Environment validation passed')}\n")
        return True
    
    def _initialize_runner(self):
        """Initialize appropriate test runner"""
        track = self.manifest.get("track_used", "Unknown")
        
        # Create execution context
        context = ExecutionContext(
            working_directory=self.submission_dir,
            environment=dict(os.environ),
            timeout=self.config.timeouts.global_seconds,
            cleanup_on_success=self.config.cleanup_on_success,
            track=track,
            manifest=self.manifest,
        )
        
        # Select runner based on track
        if track == "A":
            # CocoTB runner
            self.runner = CocoTBRunner(
                config=self.config,
                manifest=self.manifest,
                context=context,
            )
            runner_name = "CocoTB"
        
        elif track == "B":
            # VUnit runner
            self.runner = VUnitRunner(
                config=self.config,
                manifest=self.manifest,
                context=context,
            )
            runner_name = "VUnit"
        
        else:
            raise ValueError(f"Unknown track: {track}")
        
        print(f"{self.formatter.info(f'Initialized {runner_name} runner')}")
        
        # Validate runner environment
        errors = self.runner.validate_environment()
        if errors:
            print(f"{self.formatter.error('✗ Runner validation failed:')}")
            for error in errors:
                print(f"  {self.formatter.error('•')} {error}")
            
            self.report.diagnostics.errors.extend(errors)
            raise RuntimeError("Runner validation failed")
        
        print(f"{self.formatter.success('✓ Runner validation passed')}\n")
    
    async def _dry_run(self) -> TestReport:
        """
        Perform dry run (list tests without executing)
        
        Returns:
            TestReport with test list
        """
        print(f"{self.formatter.info('Dry run - listing tests:')}\n")
        
        # Initialize runner just for listing
        self._initialize_runner()
        
        # List tests
        test_list = await self.runner.list_tests()
        
        print(f"Found {len(test_list)} tests:\n")
        for test_name in test_list:
            print(f"  {self.formatter.dim('•')} {test_name}")
        
        # Create dummy results
        for test_name in test_list:
            self.report.results.append(TestResult(
                name=test_name.split('.')[-1],
                full_name=test_name,
                outcome=TestOutcome.SKIPPED,
                duration_ms=0,
                message="Dry run - not executed",
            ))
        
        self.report.status = ExecutionStatus.COMPLETED
        self.report.completed = True
        self.report.completion_reason = "dry_run"
        self.report.exit_code = ExitCode.DRY_RUN.value
        
        return self.report
    
    async def _execute_tests(self):
        """Execute all tests"""
        tests = self.manifest.get("tests_discovered", {}).get("tests", [])
        
        # Filter tests
        tests_to_run = [t for t in tests if self.runner.should_run_test(t)]
        
        if len(tests_to_run) < len(tests):
            skipped = len(tests) - len(tests_to_run)
            print(f"{self.formatter.warning(f'Skipping {skipped} tests due to filters')}\n")
        
        print(f"{self.formatter.bold(f'Running {len(tests_to_run)} tests...')}\n")
        
        # Execute tests
        try:
            if self.config.parallelism.strategy == "delegate":
                # Let runner handle parallelism
                results = await self.runner.run_all_tests()
            else:
                # Step 4 managed execution
                results = await self._run_tests_managed(tests_to_run)
            
            # Add results to report
            for result in results:
                self.report.add_result(result)
                self._print_test_result(result)
            
            # Check if interrupted
            if self.interrupted:
                # Mark remaining tests as incomplete
                completed_names = {r.full_name for r in results}
                for test in tests_to_run:
                    if test["full_name"] not in completed_names:
                        self.report.incomplete_tests.append(test["full_name"])
        
        except Exception as e:
            self.report.diagnostics.errors.append(f"Test execution error: {e}")
            raise
    
    async def _run_tests_managed(self, tests: List[Dict[str, Any]]) -> List[TestResult]:
        """
        Run tests with Step 4 managed parallelism
        
        Args:
            tests: Tests to run
        
        Returns:
            List of test results
        """
        results = []
        
        for test in tests:
            # Check for interruption
            if self.interrupted:
                break
            
            # Check timeout budget
            if not self.timeout_manager.should_continue(len(tests) - len(results)):
                self.report.diagnostics.warnings.append(
                    "Stopped due to timeout budget"
                )
                break
            
            # Run test with retry
            result = await self._run_test_with_retry(test)
            results.append(result)
            
            # Check fail-fast
            if self.config.fail_fast and result.failed:
                self.report.diagnostics.warnings.append(
                    f"Stopped due to fail-fast after {result.full_name}"
                )
                break
        
        return results
    
    async def _run_test_with_retry(self, test: Dict[str, Any]) -> TestResult:
        """
        Run test with retry logic
        
        Args:
            test: Test descriptor
        
        Returns:
            TestResult (possibly after retry)
        """
        for attempt in range(1, self.config.retry.max_attempts + 1):
            # Run test
            result = await self.runner.run_single_test(test)
            result.attempts = attempt
            
            # Check if passed
            if result.passed:
                if attempt > 1:
                    result.flaky = True
                    self.report.diagnostics.warnings.append(
                        f"Test {test['full_name']} passed after {attempt} attempts (flaky)"
                    )
                return result
            
            # Check if should retry
            if not self.config.retry.should_retry(result.outcome.value, attempt):
                return result
            
            # Wait before retry
            if attempt < self.config.retry.max_attempts:
                delay = self.config.retry.get_delay(attempt)
                print(f"  {self.formatter.warning(f'Retrying in {delay}s...')}")
                await asyncio.sleep(delay)
        
        return result
    
    def _print_test_result(self, result: TestResult):
        """Print test result"""
        symbol = result.outcome.symbol
        duration = self.formatter.format_duration(result.duration_ms)
        
        # Build status line
        status_line = f"{symbol} {result.full_name} ({duration})"
        
        # Color based on outcome
        if result.passed:
            status_line = self.formatter.success(status_line)
        elif result.failed:
            status_line = self.formatter.error(status_line)
        else:
            status_line = self.formatter.warning(status_line)
        
        print(status_line)
        
        # Print failure message if failed
        if result.message and result.failed:
            print(f"  {self.formatter.dim('└─')} {result.message[:100]}")
        
        # Print flaky indicator
        if result.flaky:
            print(f"  {self.formatter.warning('⚠ Flaky test - passed after retry')}")
    
    async def _collect_coverage(self):
        """Collect and organize coverage files"""
        print(f"\n{self.formatter.info('Collecting coverage...')}")
        
        try:
            # Locate coverage files
            coverage_dir = Path(self.report.coverage_directory)
            
            locator = CoverageLocator(self.submission_dir)
            
            # Search in common locations
            search_dirs = [
                self.submission_dir,
                coverage_dir,
            ]
            
            # Add simulator-specific directories
            if self.manifest.get("track_used") == "A":
                # CocoTB
                cocotb_dir = Path(self.manifest.get("execution_cwd", ".tbeval/cocotb"))
                if not cocotb_dir.is_absolute():
                    cocotb_dir = self.submission_dir / cocotb_dir
                search_dirs.append(cocotb_dir)
                search_dirs.append(cocotb_dir / "obj_dir")  # Verilator
            
            # Get test names
            test_names = [r.name for r in self.report.results]
            
            # Locate coverage
            coverage_info = locator.locate_all(
                search_dirs=search_dirs,
                test_names=test_names,
            )
            
            # Validate coverage
            is_valid, issues = CoverageValidator.validate_coverage_info(
                coverage_info,
                expected_tests=test_names,
            )
            
            if not is_valid:
                for issue in issues:
                    self.report.diagnostics.warnings.append(f"Coverage: {issue}")
            
            # Update report
            self.report.coverage = coverage_info
            
            # Print summary
            print(f"{self.formatter.success(f'✓ Found {len(coverage_info.files)} coverage files')}")
            if coverage_info.files:
                print(f"  Format: {coverage_info.primary_format.value}")
                print(f"  Total size: {coverage_info.total_size_bytes / 1024:.1f} KB")
        
        except Exception as e:
            error_msg = f"Coverage collection failed: {e}"
            self.report.diagnostics.errors.append(error_msg)
            print(f"{self.formatter.error(f'✗ {error_msg}')}")
    
    def _finalize_report(self):
        """Finalize test report"""
        # Set completion status
        if self.interrupted:
            self.report.status = ExecutionStatus.CANCELLED
            self.report.completed = False
            self.report.completion_reason = "user_cancelled"
        
        elif self.report.summary.completed_tests < self.report.summary.total_tests:
            self.report.status = ExecutionStatus.PARTIAL
            self.report.completed = False
            self.report.completion_reason = "timeout_or_error"
        
        else:
            self.report.status = ExecutionStatus.COMPLETED
            self.report.completed = True
        
        # Call finalize to set exit code
        self.report.finalize()
        
        # Print summary
        self._print_summary()
    
    def _print_summary(self):
        """Print execution summary"""
        print(f"\n{self.formatter.bold('─' * 70)}")
        print(f"{self.formatter.bold('Execution Summary')}")
        print(f"{self.formatter.bold('─' * 70)}\n")
        
        # Results
        summary = self.report.summary
        
        print(f"Total tests:     {summary.total_tests}")
        print(f"Completed:       {summary.completed_tests}")
        
        if summary.passed > 0:
            print(f"Passed:          {self.formatter.success(str(summary.passed))}")
        
        if summary.failed > 0:
            print(f"Failed:          {self.formatter.error(str(summary.failed))}")
        
        if summary.errors > 0:
            print(f"Errors:          {self.formatter.error(str(summary.errors))}")
        
        if summary.skipped > 0:
            print(f"Skipped:         {self.formatter.warning(str(summary.skipped))}")
        
        if summary.timeout > 0:
            print(f"Timeout:         {self.formatter.warning(str(summary.timeout))}")
        
        if summary.flaky > 0:
            print(f"Flaky:           {self.formatter.warning(str(summary.flaky))}")
        
        # Success rate
        success_rate = summary.success_rate * 100
        if success_rate == 100.0:
            rate_str = self.formatter.success(f"{success_rate:.1f}%")
        elif success_rate >= 80.0:
            rate_str = self.formatter.warning(f"{success_rate:.1f}%")
        else:
            rate_str = self.formatter.error(f"{success_rate:.1f}%")
        
        print(f"Success rate:    {rate_str}")
        
        # Duration
        duration = self.formatter.format_duration(summary.total_duration_ms)
        print(f"Total duration:  {duration}")
        
        # Coverage
        if self.report.coverage.files:
            print(f"Coverage files:  {len(self.report.coverage.files)}")
        
        print(f"\n{self.formatter.bold('─' * 70)}\n")
    
    async def _save_report(self):
        """Save test report to file"""
        output_path = Path(self.report.artifacts_root) / "test_report.json"
        
        try:
            self.report.save(output_path)
            print(f"Report saved: {self.formatter.dim(str(output_path))}")
        
        except Exception as e:
            error_msg = f"Failed to save report: {e}"
            self.report.diagnostics.errors.append(error_msg)
            print(f"{self.formatter.error(error_msg)}")
    
    async def _handle_interruption(self) -> TestReport:
        """Handle keyboard interrupt"""
        print(f"\n{self.formatter.warning('Execution interrupted by user')}")
        
        self.report.status = ExecutionStatus.CANCELLED
        self.report.completed = False
        self.report.completion_reason = "user_cancelled"
        
        # Save partial results if configured
        if self.config.save_partial_results:
            print(f"{self.formatter.info('Saving partial results...')}")
            self._finalize_report()
            await self._save_report()
        
        return self.report
    
    async def _handle_error(self, error: Exception) -> TestReport:
        """Handle execution error"""
        import traceback
        
        error_msg = f"Execution error: {error}"
        
        print(f"\n{self.formatter.error(f'✗ {error_msg}')}")
        
        if self.config.debug_mode:
            traceback.print_exc()
        
        self.report.status = ExecutionStatus.ERROR
        self.report.completed = False
        self.report.completion_reason = "error"
        self.report.diagnostics.errors.append(error_msg)
        
        # Save partial results
        if self.config.save_partial_results:
            self._finalize_report()
            await self._save_report()
        
        return self.report


# Convenience function for CLI

async def execute_tests(
    submission_dir: Path,
    config_overrides: Optional[Dict[str, Any]] = None,
    manifest_path: Optional[Path] = None,
) -> TestReport:
    """
    Convenience function to execute tests
    
    Args:
        submission_dir: Path to submission directory
        config_overrides: Configuration overrides from CLI
        manifest_path: Path to build manifest
    
    Returns:
        TestReport
    """
    # Load configuration
    config_manager = ConfigManager(submission_dir)
    config = config_manager.load(manifest_path, config_overrides or {})
    
    # Create executor
    executor = TestExecutor(
        submission_dir=submission_dir,
        config=config,
        manifest_path=manifest_path,
    )
    
    # Execute
    report = await executor.execute()
    
    return report


# Main entry point for testing
if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="TB Eval Test Executor")
    parser.add_argument(
        "submission_dir",
        type=Path,
        help="Path to submission directory"
    )
    parser.add_argument(
        "--manifest",
        type=Path,
        help="Path to build manifest"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="List tests without executing"
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Verbose output"
    )
    parser.add_argument(
        "--filter",
        type=str,
        help="Test filter pattern (regex)"
    )
    parser.add_argument(
        "--timeout",
        type=float,
        help="Per-test timeout in seconds"
    )
    
    args = parser.parse_args()
    
    # Build config overrides
    overrides = {
        "dry_run": args.dry_run,
    }
    
    if args.verbose:
        overrides["verbose"] = True
    
    if args.filter:
        overrides["filter"] = args.filter
    
    if args.timeout:
        overrides["timeout"] = args.timeout
    
    # Execute
    report = asyncio.run(execute_tests(
        submission_dir=args.submission_dir,
        config_overrides=overrides,
        manifest_path=args.manifest,
    ))
    
    # Exit with appropriate code
    sys.exit(report.exit_code)
