"""
VUnit test runner

Executes VUnit tests via run.py and collects results.

Author: TB Eval Team
Version: 0.1.0
"""

import asyncio
from pathlib import Path
from typing import List, Dict, Any, Optional
import re

from .base import BaseRunner
from .process_manager import ProcessManager
from ..models import TestResult, TestOutcome, ProcessResult
from ..handlers.timeout_handler import TimeoutManager
from ..config import ExecutionConfig


class VUnitRunner(BaseRunner):
    """
    Runner for VUnit tests (Track B)
    
    Execution strategy:
    1. Validate run.py exists
    2. Run "python run.py --list" to enumerate tests
    3. Run "python run.py -p N" to execute all tests (delegate parallelism)
    4. Parse console output to extract results
    
    Future enhancement: Support step4_managed parallelism
    """
    
    def __init__(
        self,
        config: ExecutionConfig,
        manifest: Dict[str, Any],
        context: Any,
    ):
        """Initialize VUnit runner"""
        super().__init__(config, manifest, context)
        
        self.process_manager = ProcessManager(
            max_output_size_mb=config.artifacts.max_log_size_mb,
        )
        
        self.timeout_manager = TimeoutManager(
            config=config.timeouts,
        )
        
        # Get VUnit configuration from manifest
        vunit_config = manifest.get("vunit_project", {})
        self.run_py_path = Path(vunit_config.get("run_py_path", ".tbeval/vunit_project/run.py"))
        self.output_path = Path(vunit_config.get("output_path", ".tbeval/vunit_out"))
        
        # Make paths absolute relative to working directory
        if not self.run_py_path.is_absolute():
            self.run_py_path = self.working_dir / self.run_py_path
        
        if not self.output_path.is_absolute():
            self.output_path = self.working_dir / self.output_path
    
    def validate_environment(self) -> List[str]:
        """Validate VUnit execution environment"""
        errors = []
        
        # Check run.py exists
        if not self.run_py_path.exists():
            errors.append(f"VUnit run.py not found: {self.run_py_path}")
        
        # Check Python is available
        import shutil
        if not shutil.which("python") and not shutil.which("python3"):
            errors.append("Python interpreter not found")
        
        # Check VUnit is importable (optional - run.py will fail if not)
        try:
            import vunit
        except ImportError:
            errors.append("VUnit package not installed (pip install vunit-hdl)")
        
        return errors
    
    async def list_tests(self) -> List[str]:
        """
        List tests using VUnit's --list option
        
        Returns:
            List of test names (e.g., "work.tb_adder.test_basic")
        """
        cmd = ["python", str(self.run_py_path), "--list"]
        
        result = await self.process_manager.run(
            command=cmd,
            cwd=self.working_dir,
            timeout_seconds=30.0,  # Short timeout for listing
        )
        
        if result.exit_code != 0:
            raise RuntimeError(
                f"Failed to list VUnit tests: {result.output.stderr}"
            )
        
        # Parse test list from stdout
        tests = []
        for line in result.output.stdout.splitlines():
            line = line.strip()
            if line and not line.startswith('#'):
                tests.append(line)
        
        return tests
    
    async def run_all_tests(self) -> List[TestResult]:
        """
        Run all VUnit tests with delegated parallelism
        
        Returns:
            List of test results
        """
        # Start timeouts
        self.timeout_manager.start_global_timeout()
        self.timeout_manager.start_suite_timeout()
        
        # Build command
        cmd = self._build_run_command()
        
        # Get timeout
        timeout = self.timeout_manager.get_effective_timeout()
        
        # Execute
        log_file = self.output_path / "vunit_output.log"
        
        result = await self.process_manager.run(
            command=cmd,
            cwd=self.working_dir,
            timeout_seconds=timeout,
            log_file=log_file,
        )
        
        # Parse results from console output
        from ..parsers.vunit_parser import VUnitOutputParser
        
        parser = VUnitOutputParser()
        test_results = parser.parse(result.output.combined)
        
        # Enrich results with process info
        for test_result in test_results:
            test_result.process_result = result
            test_result.artifacts.log_file = str(log_file)
        
        return test_results
    
    async def run_single_test(self, test: Dict[str, Any]) -> TestResult:
        """
        Run a single VUnit test
        
        Args:
            test: Test descriptor from manifest
        
        Returns:
            Test result
        """
        self.timeout_manager.start_test_timeout(
            timeout_seconds=self.get_timeout_for_test(test)
        )
        
        # Build command for single test
        cmd = self._build_run_command(test_name=test["full_name"])
        
        # Get timeout
        timeout = self.timeout_manager.get_effective_timeout()
        
        # Execute
        log_file = self.output_path / f"{test['name']}.log"
        
        result = await self.process_manager.run(
            command=cmd,
            cwd=self.working_dir,
            timeout_seconds=timeout,
            log_file=log_file,
        )
        
        # Record duration
        duration = self.timeout_manager.end_test_timeout()
        
        # Parse result
        from ..parsers.vunit_parser import VUnitOutputParser
        
        parser = VUnitOutputParser()
        test_results = parser.parse(result.output.combined)
        
        # Should have exactly one result
        if not test_results:
            # Test didn't run - create error result
            return self.create_test_result(
                test=test,
                outcome=TestOutcome.ERROR,
                duration_ms=duration * 1000,
                message="Test did not execute",
                details=result.output.stderr,
            )
        
        test_result = test_results[0]
        test_result.process_result = result
        test_result.artifacts.log_file = str(log_file)
        
        return test_result
    
    def _build_run_command(
        self,
        test_name: Optional[str] = None,
    ) -> List[str]:
        """
        Build VUnit run command
        
        Args:
            test_name: Specific test to run (None = all tests)
        
        Returns:
            Command as list of strings
        """
        cmd = ["python", str(self.run_py_path)]
        
        # Parallelism (only if running all tests)
        if test_name is None and self.config.parallelism.strategy == "delegate":
            jobs = self.config.parallelism.vunit_parallel_jobs
            cmd.extend(["-p", str(jobs)])
        
        # Verbosity
        if self.config.output.verbosity == "verbose":
            cmd.append("-v")
        
        # Output directory
        cmd.extend(["--output-path", str(self.output_path)])
        
        # Specific test
        if test_name:
            cmd.append(test_name)
        
        return cmd
