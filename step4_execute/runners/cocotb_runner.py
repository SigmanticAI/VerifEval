"""
CocoTB test runner

Executes CocoTB tests via Makefiles and collects results.

Author: TB Eval Team
Version: 0.1.0
"""

import asyncio
from pathlib import Path
from typing import List, Dict, Any, Optional, Set
import os
from collections import defaultdict

from .base import BaseRunner
from .process_manager import ProcessManager
from ..models import TestResult, TestOutcome, ProcessResult
from ..handlers.timeout_handler import TimeoutManager
from ..config import ExecutionConfig


class CocoTBRunner(BaseRunner):
    """
    Runner for CocoTB tests (Track A)
    
    Execution strategy:
    1. Group tests by MODULE (test file)
    2. For each MODULE, run: make -C <cocotb_dir> MODULE=<name>
    3. Parse results.xml to extract individual test results
    4. Locate and organize coverage files
    
    Key constraint: CocoTB runs all @cocotb.test() in a module together,
    so we can't run individual tests - must run whole modules.
    """
    
    def __init__(
        self,
        config: ExecutionConfig,
        manifest: Dict[str, Any],
        context: Any,
    ):
        """Initialize CocoTB runner"""
        super().__init__(config, manifest, context)
        
        self.process_manager = ProcessManager(
            max_output_size_mb=config.artifacts.max_log_size_mb,
        )
        
        self.timeout_manager = TimeoutManager(
            config=config.timeouts,
        )
        
        # Get CocoTB configuration from manifest
        self.execution_command = manifest.get("execution_command", ["make"])
        self.execution_env = manifest.get("execution_env", {})
        self.execution_cwd = manifest.get("execution_cwd", ".tbeval/cocotb")
        
        # Make CWD absolute
        self.cocotb_dir = Path(self.execution_cwd)
        if not self.cocotb_dir.is_absolute():
            self.cocotb_dir = self.working_dir / self.cocotb_dir
        
        # Coverage configuration
        coverage_config = manifest.get("coverage_config", {})
        self.coverage_enabled = coverage_config.get("enabled", False)
        self.coverage_output_dir = Path(coverage_config.get("output_dir", "coverage"))
        if not self.coverage_output_dir.is_absolute():
            self.coverage_output_dir = self.working_dir / self.coverage_output_dir
        
        # Group tests by module
        self.tests_by_module = self._group_tests_by_module()
    
    def _group_tests_by_module(self) -> Dict[str, List[Dict[str, Any]]]:
        """
        Group tests by their module (testbench)
        
        Returns:
            Dictionary mapping module name to list of tests
        """
        grouped = defaultdict(list)
        
        for test in self.get_test_list():
            module = test.get("testbench", test.get("library", "unknown"))
            grouped[module].append(test)
        
        return dict(grouped)
    
    def validate_environment(self) -> List[str]:
        """Validate CocoTB execution environment"""
        errors = []
        
        # Check CocoTB directory exists
        if not self.cocotb_dir.exists():
            errors.append(f"CocoTB directory not found: {self.cocotb_dir}")
        
        # Check Makefile exists
        makefile = self.cocotb_dir / "Makefile"
        if not makefile.exists():
            errors.append(f"Makefile not found: {makefile}")
        
        # Check make is available
        import shutil
        if not shutil.which("make"):
            errors.append("make command not found")
        
        # Check simulator is available
        simulator = self.execution_env.get("SIM", "unknown")
        sim_commands = {
            "verilator": "verilator",
            "modelsim": "vsim",
            "questa": "vsim",
            "vcs": "vcs",
            "icarus": "iverilog",
        }
        
        if simulator in sim_commands:
            if not shutil.which(sim_commands[simulator]):
                errors.append(f"Simulator not found: {simulator}")
        
        # Check CocoTB is importable (optional check)
        try:
            import cocotb
        except ImportError:
            errors.append("CocoTB package not installed (pip install cocotb)")
        
        return errors
    
    async def list_tests(self) -> List[str]:
        """
        List tests from manifest
        
        CocoTB doesn't have a --list option, so we use the manifest.
        
        Returns:
            List of test full names
        """
        return [test["full_name"] for test in self.get_test_list()]
    
    async def run_all_tests(self) -> List[TestResult]:
        """
        Run all CocoTB tests by module
        
        Returns:
            List of test results from all modules
        """
        # Start timeouts
        self.timeout_manager.start_global_timeout()
        self.timeout_manager.start_suite_timeout()
        
        all_results = []
        
        # Run each module
        for module_name, tests in self.tests_by_module.items():
            # Check if we should continue
            remaining_modules = len(self.tests_by_module) - len(all_results)
            if not self.timeout_manager.should_continue(remaining_modules):
                # Add incomplete results for remaining tests
                for test in tests:
                    all_results.append(
                        self.create_test_result(
                            test=test,
                            outcome=TestOutcome.SKIPPED,
                            duration_ms=0,
                            message="Skipped due to timeout budget",
                        )
                    )
                continue
            
            # Run module
            module_results = await self._run_module(module_name, tests)
            all_results.extend(module_results)
            
            # Check fail-fast
            if self.config.fail_fast and any(r.failed for r in module_results):
                # Mark remaining tests as skipped
                processed_modules = {module_name}
                for mod_name, mod_tests in self.tests_by_module.items():
                    if mod_name not in processed_modules:
                        for test in mod_tests:
                            all_results.append(
                                self.create_test_result(
                                    test=test,
                                    outcome=TestOutcome.SKIPPED,
                                    duration_ms=0,
                                    message="Skipped due to fail-fast",
                                )
                            )
                break
        
        return all_results
    
    async def run_single_test(self, test: Dict[str, Any]) -> TestResult:
        """
        Run a single test (actually runs entire module)
        
        Note: CocoTB can't run individual @cocotb.test() functions,
        so we run the entire module and extract the specific test result.
        
        Args:
            test: Test descriptor from manifest
        
        Returns:
            Test result for the specific test
        """
        module_name = test.get("testbench", test.get("library"))
        module_tests = self.tests_by_module.get(module_name, [test])
        
        # Run module
        module_results = await self._run_module(module_name, module_tests)
        
        # Find the specific test result
        for result in module_results:
            if result.full_name == test["full_name"]:
                return result
        
        # Test not found in results - create error result
        return self.create_test_result(
            test=test,
            outcome=TestOutcome.ERROR,
            duration_ms=0,
            message="Test not found in module results",
        )
    
    async def _run_module(
        self,
        module_name: str,
        tests: List[Dict[str, Any]],
    ) -> List[TestResult]:
        """
        Run a CocoTB module (test file)
        
        Args:
            module_name: Module name (e.g., "test_adder")
            tests: List of tests in this module
        
        Returns:
            List of test results for all tests in module
        """
        # Start test timeout (use max timeout from all tests in module)
        max_timeout = max(
            self.get_timeout_for_test(test) for test in tests
        )
        self.timeout_manager.start_test_timeout(max_timeout)
        
        # Build command
        cmd = self._build_make_command(module_name)
        
        # Build environment
        env = self._build_environment(module_name)
        
        # Get timeout
        timeout = self.timeout_manager.get_effective_timeout()
        
        # Prepare log file
        log_file = self.cocotb_dir / f"{module_name}_output.log"
        
        # Execute
        result = await self.process_manager.run(
            command=cmd,
            cwd=self.cocotb_dir,
            env=env,
            timeout_seconds=timeout,
            log_file=log_file,
        )
        
        # Record duration
        duration = self.timeout_manager.end_test_timeout()
        
        # Parse results.xml
        results_xml = self.cocotb_dir / "results.xml"
        
        if results_xml.exists():
            test_results = await self._parse_results_xml(
                results_xml=results_xml,
                tests=tests,
                process_result=result,
                log_file=log_file,
            )
        else:
            # No results.xml - likely a failure before tests ran
            test_results = self._create_error_results(
                tests=tests,
                process_result=result,
                log_file=log_file,
            )
        
        # Locate coverage files
        if self.coverage_enabled:
            await self._locate_coverage_files(module_name, test_results)
        
        return test_results
    
    def _build_make_command(self, module_name: str) -> List[str]:
        """
        Build make command for module
        
        Args:
            module_name: Module to run
        
        Returns:
            Command as list of strings
        """
        # Start with base command from manifest
        cmd = list(self.execution_command)
        
        # If command is just "make", add -C flag
        if cmd == ["make"]:
            cmd = ["make", "-C", str(self.cocotb_dir)]
        
        # Add MODULE parameter
        cmd.append(f"MODULE={module_name}")
        
        return cmd
    
    def _build_environment(self, module_name: str) -> Dict[str, str]:
        """
        Build environment variables for execution
        
        Args:
            module_name: Module being run
        
        Returns:
            Environment variable dictionary
        """
        env = dict(self.execution_env)
        
        # Add MODULE to environment (in addition to command line)
        env["MODULE"] = module_name
        
        # Set coverage file path if enabled
        if self.coverage_enabled:
            coverage_file = self.coverage_output_dir / f"coverage_{module_name}.dat"
            env["COVERAGE_FILE"] = str(coverage_file)
        
        return env
    
    async def _parse_results_xml(
        self,
        results_xml: Path,
        tests: List[Dict[str, Any]],
        process_result: ProcessResult,
        log_file: Path,
    ) -> List[TestResult]:
        """
        Parse CocoTB results.xml file
        
        Args:
            results_xml: Path to results.xml
            tests: Expected tests
            process_result: Process execution result
            log_file: Path to log file
        
        Returns:
            List of test results
        """
        from ..parsers.cocotb_parser import CocoTBResultsParser
        
        parser = CocoTBResultsParser()
        test_results = parser.parse_file(results_xml)
        
        # Enrich results with process info and artifacts
        for test_result in test_results:
            test_result.process_result = process_result
            test_result.artifacts.log_file = str(log_file)
            
            # Add waveform if exists
            waveform = self.cocotb_dir / "dump.vcd"
            if waveform.exists():
                test_result.artifacts.waveform_file = str(waveform)
        
        # Check for missing tests
        result_names = {r.full_name for r in test_results}
        expected_names = {t["full_name"] for t in tests}
        
        missing = expected_names - result_names
        if missing:
            # Create error results for missing tests
            for test in tests:
                if test["full_name"] in missing:
                    test_results.append(
                        self.create_test_result(
                            test=test,
                            outcome=TestOutcome.ERROR,
                            duration_ms=0,
                            message="Test not found in results.xml",
                        )
                    )
        
        return test_results
    
    def _create_error_results(
        self,
        tests: List[Dict[str, Any]],
        process_result: ProcessResult,
        log_file: Path,
    ) -> List[TestResult]:
        """
        Create error results when module fails to run
        
        Args:
            tests: Tests that were supposed to run
            process_result: Process execution result
            log_file: Path to log file
        
        Returns:
            List of error test results
        """
        results = []
        
        # Determine error type
        if process_result.timed_out:
            outcome = TestOutcome.TIMEOUT
            message = "Module execution timed out"
        elif process_result.exit_code != 0:
            outcome = TestOutcome.ERROR
            message = f"Module execution failed (exit code {process_result.exit_code})"
        else:
            outcome = TestOutcome.ERROR
            message = "Module executed but produced no results"
        
        # Get error details from stderr
        details = process_result.output.stderr[:1000] if process_result.output.stderr else None
        
        # Create error result for each test
        for test in tests:
            result = self.create_test_result(
                test=test,
                outcome=outcome,
                duration_ms=process_result.duration_ms / len(tests),  # Divide duration
                message=message,
                details=details,
            )
            result.process_result = process_result
            result.artifacts.log_file = str(log_file)
            results.append(result)
        
        return results
    
    async def _locate_coverage_files(
        self,
        module_name: str,
        test_results: List[TestResult],
    ) -> None:
        """
        Locate and attach coverage files to test results
        
        Args:
            module_name: Module name
            test_results: Test results to enrich
        """
        # Expected coverage file path
        coverage_file = self.coverage_output_dir / f"coverage_{module_name}.dat"
        
        # Alternative: coverage.dat in cocotb_dir
        if not coverage_file.exists():
            coverage_file = self.cocotb_dir / "coverage.dat"
        
        if coverage_file.exists():
            # Attach to all tests from this module
            for result in test_results:
                result.artifacts.coverage_file = str(coverage_file)
        
        # Also check for Verilator coverage in obj_dir
        obj_dir_coverage = self.cocotb_dir / "obj_dir" / "coverage.dat"
        if obj_dir_coverage.exists() and not coverage_file.exists():
            for result in test_results:
                result.artifacts.coverage_file = str(obj_dir_coverage)
    
    async def run_module_with_retry(
        self,
        module_name: str,
        tests: List[Dict[str, Any]],
    ) -> List[TestResult]:
        """
        Run module with retry logic
        
        Args:
            module_name: Module name
            tests: Tests in module
        
        Returns:
            List of test results (potentially after retry)
        """
        for attempt in range(1, self.config.retry.max_attempts + 1):
            results = await self._run_module(module_name, tests)
            
            # Check if any tests failed/errored
            failed_tests = [r for r in results if r.outcome.is_failure]
            
            if not failed_tests:
                # All passed
                if attempt > 1:
                    # Mark as flaky if passed after retry
                    for result in results:
                        result.flaky = True
                        result.attempts = attempt
                return results
            
            # Check if should retry
            should_retry = any(
                self.config.retry.should_retry(r.outcome.value, attempt)
                for r in failed_tests
            )
            
            if not should_retry or attempt >= self.config.retry.max_attempts:
                # Update attempt count
                for result in results:
                    result.attempts = attempt
                return results
            
            # Wait before retry
            delay = self.config.retry.get_delay(attempt)
            await asyncio.sleep(delay)
        
        # Should not reach here, but return last results
        return results
    
    async def cleanup_module_artifacts(self, module_name: str) -> None:
        """
        Clean up module artifacts
        
        Args:
            module_name: Module to clean up
        """
        # Clean up CocoTB generated files
        cleanup_files = [
            self.cocotb_dir / "results.xml",
            self.cocotb_dir / "dump.vcd",
            self.cocotb_dir / "dump.fst",
            self.cocotb_dir / f"{module_name}_output.log",
        ]
        
        for file in cleanup_files:
            if file.exists():
                try:
                    file.unlink()
                except Exception:
                    pass  # Best effort
        
        # Clean up sim_build directory
        sim_build = self.cocotb_dir / "sim_build"
        if sim_build.exists():
            import shutil
            try:
                shutil.rmtree(sim_build)
            except Exception:
                pass


class CocoTBModuleOrchestrator:
    """
    Orchestrates parallel execution of CocoTB modules
    
    This is for future "step4_managed" parallelism strategy.
    Currently, CocoTB runner executes modules sequentially.
    """
    
    def __init__(
        self,
        runner: CocoTBRunner,
        max_parallel: int = 2,
    ):
        """
        Initialize orchestrator
        
        Args:
            runner: CocoTB runner instance
            max_parallel: Maximum parallel modules
        """
        self.runner = runner
        self.max_parallel = max_parallel
        self.semaphore = asyncio.Semaphore(max_parallel)
    
    async def run_modules_parallel(
        self,
        modules: Dict[str, List[Dict[str, Any]]],
    ) -> List[TestResult]:
        """
        Run multiple modules in parallel
        
        Args:
            modules: Dictionary of module_name -> tests
        
        Returns:
            All test results
        """
        tasks = []
        
        for module_name, tests in modules.items():
            task = self._run_module_semaphore(module_name, tests)
            tasks.append(task)
        
        # Wait for all modules
        results_lists = await asyncio.gather(*tasks)
        
        # Flatten results
        all_results = []
        for results in results_lists:
            all_results.extend(results)
        
        return all_results
    
    async def _run_module_semaphore(
        self,
        module_name: str,
        tests: List[Dict[str, Any]],
    ) -> List[TestResult]:
        """Run module with semaphore to limit parallelism"""
        async with self.semaphore:
            return await self.runner._run_module(module_name, tests)
