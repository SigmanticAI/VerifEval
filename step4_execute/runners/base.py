"""
Base runner interface for test execution

Defines abstract interface that all runners must implement.

Author: TB Eval Team
Version: 0.1.0
"""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import List, Dict, Any, Optional

from ..models import TestResult, TestOutcome, ExecutionContext
from ..config import ExecutionConfig


class BaseRunner(ABC):
    """
    Abstract base class for test runners
    
    All test runners (CocoTB, VUnit, etc.) must implement this interface.
    """
    
    def __init__(
        self,
        config: ExecutionConfig,
        manifest: Dict[str, Any],
        context: ExecutionContext,
    ):
        """
        Initialize runner
        
        Args:
            config: Execution configuration
            manifest: Build manifest from Step 3
            context: Execution context
        """
        self.config = config
        self.manifest = manifest
        self.context = context
        
        self.working_dir = context.working_directory
        self.track = manifest.get("track_used", "Unknown")
    
    @abstractmethod
    async def run_all_tests(self) -> List[TestResult]:
        """
        Run all tests
        
        Returns:
            List of test results
        """
        pass
    
    @abstractmethod
    async def run_single_test(self, test: Dict[str, Any]) -> TestResult:
        """
        Run a single test
        
        Args:
            test: Test descriptor from manifest
        
        Returns:
            Test result
        """
        pass
    
    @abstractmethod
    async def list_tests(self) -> List[str]:
        """
        List available tests
        
        Returns:
            List of test names
        """
        pass
    
    @abstractmethod
    def validate_environment(self) -> List[str]:
        """
        Validate execution environment
        
        Returns:
            List of validation errors (empty if OK)
        """
        pass
    
    def get_test_list(self) -> List[Dict[str, Any]]:
        """Get test list from manifest"""
        return self.manifest.get("tests_discovered", {}).get("tests", [])
    
    def get_timeout_for_test(self, test: Dict[str, Any]) -> float:
        """
        Get timeout for specific test
        
        Args:
            test: Test descriptor
        
        Returns:
            Timeout in seconds
        """
        # Use test-specific timeout if available
        test_timeout_ms = test.get("timeout_ms")
        if test_timeout_ms:
            return test_timeout_ms / 1000.0
        
        # Fall back to config timeout
        return self.config.timeouts.per_test_seconds
    
    def should_run_test(self, test: Dict[str, Any]) -> bool:
        """
        Determine if test should be run based on filters
        
        Args:
            test: Test descriptor
        
        Returns:
            True if test should run
        """
        # Check test filter
        if self.config.test_filter:
            import re
            pattern = self.config.test_filter
            if not re.search(pattern, test.get("full_name", "")):
                return False
        
        # Check if rerun_failed mode
        if self.config.rerun_failed:
            # Would need to load previous results
            # For now, run all tests
            pass
        
        return True
    
    def create_test_result(
        self,
        test: Dict[str, Any],
        outcome: TestOutcome,
        duration_ms: float,
        message: Optional[str] = None,
        details: Optional[str] = None,
    ) -> TestResult:
        """
        Create TestResult with common fields populated
        
        Args:
            test: Test descriptor
            outcome: Test outcome
            duration_ms: Duration in milliseconds
            message: Optional failure message
            details: Optional additional details
        
        Returns:
            TestResult instance
        """
        return TestResult(
            name=test["name"],
            full_name=test["full_name"],
            outcome=outcome,
            duration_ms=duration_ms,
            message=message,
            details=details,
        )
