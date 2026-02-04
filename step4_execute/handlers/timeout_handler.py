"""
Timeout handling for test execution

This module provides:
- Timeout tracking and enforcement
- Hierarchical timeouts (test, suite, global)
- Timeout warnings
- Graceful timeout handling

Author: TB Eval Team
Version: 0.1.0
"""

import asyncio
import time
from typing import Optional, Callable, Dict, Any
from datetime import datetime, timedelta
from dataclasses import dataclass

from ..config import TimeoutConfig


@dataclass
class TimeoutState:
    """State tracking for timeout"""
    start_time: float
    timeout_seconds: float
    warning_threshold: float = 0.8  # Warn at 80% of timeout
    warning_issued: bool = False
    
    @property
    def elapsed_seconds(self) -> float:
        """Get elapsed time in seconds"""
        return time.time() - self.start_time
    
    @property
    def remaining_seconds(self) -> float:
        """Get remaining time in seconds"""
        return max(0, self.timeout_seconds - self.elapsed_seconds)
    
    @property
    def percent_used(self) -> float:
        """Get percentage of timeout used"""
        if self.timeout_seconds == 0:
            return 0.0
        return (self.elapsed_seconds / self.timeout_seconds) * 100
    
    @property
    def should_warn(self) -> bool:
        """Check if warning should be issued"""
        if self.warning_issued:
            return False
        return self.percent_used >= (self.warning_threshold * 100)


class TimeoutManager:
    """
    Manages hierarchical timeouts
    
    Hierarchy:
    1. Per-test timeout (most specific)
    2. Test suite timeout
    3. Global timeout (hardest limit)
    
    Features:
    - Multiple timeout levels
    - Warning callbacks
    - Timeout budget tracking
    - Automatic timeout calculation
    """
    
    def __init__(
        self,
        config: TimeoutConfig,
        warning_callback: Optional[Callable[[str], None]] = None,
    ):
        """
        Initialize timeout manager
        
        Args:
            config: Timeout configuration
            warning_callback: Optional callback for timeout warnings
        """
        self.config = config
        self.warning_callback = warning_callback
        
        # Timeout states
        self.global_state: Optional[TimeoutState] = None
        self.suite_state: Optional[TimeoutState] = None
        self.test_state: Optional[TimeoutState] = None
        
        # Statistics
        self.tests_run = 0
        self.total_test_time = 0.0
    
    def start_global_timeout(self) -> None:
        """Start global timeout"""
        self.global_state = TimeoutState(
            start_time=time.time(),
            timeout_seconds=self.config.global_seconds,
        )
    
    def start_suite_timeout(self) -> None:
        """Start test suite timeout"""
        self.suite_state = TimeoutState(
            start_time=time.time(),
            timeout_seconds=self.config.test_suite_seconds,
        )
    
    def start_test_timeout(self, timeout_seconds: Optional[float] = None) -> None:
        """
        Start per-test timeout
        
        Args:
            timeout_seconds: Timeout for this test (uses default if None)
        """
        timeout = timeout_seconds or self.config.per_test_seconds
        
        self.test_state = TimeoutState(
            start_time=time.time(),
            timeout_seconds=timeout,
        )
    
    def end_test_timeout(self) -> float:
        """
        End test timeout and return duration
        
        Returns:
            Test duration in seconds
        """
        if not self.test_state:
            return 0.0
        
        duration = self.test_state.elapsed_seconds
        
        # Update statistics
        self.tests_run += 1
        self.total_test_time += duration
        
        self.test_state = None
        return duration
    
    def get_effective_timeout(self) -> Optional[float]:
        """
        Get effective timeout for current test
        
        Returns:
            Minimum of all active timeouts (most restrictive)
        """
        timeouts = []
        
        if self.test_state:
            timeouts.append(self.test_state.remaining_seconds)
        
        if self.suite_state:
            timeouts.append(self.suite_state.remaining_seconds)
        
        if self.global_state:
            timeouts.append(self.global_state.remaining_seconds)
        
        if not timeouts:
            return None
        
        return min(timeouts)
    
    def check_timeouts(self) -> Optional[str]:
        """
        Check all timeouts and issue warnings
        
        Returns:
            Timeout level that expired (None if OK)
        """
        # Check global timeout
        if self.global_state:
            if self.global_state.elapsed_seconds >= self.global_state.timeout_seconds:
                return "global"
            
            if self.global_state.should_warn:
                self._warn(
                    f"Global timeout warning: {self.global_state.percent_used:.1f}% used "
                    f"({self.global_state.remaining_seconds:.1f}s remaining)"
                )
                self.global_state.warning_issued = True
        
        # Check suite timeout
        if self.suite_state:
            if self.suite_state.elapsed_seconds >= self.suite_state.timeout_seconds:
                return "suite"
            
            if self.suite_state.should_warn:
                self._warn(
                    f"Test suite timeout warning: {self.suite_state.percent_used:.1f}% used "
                    f"({self.suite_state.remaining_seconds:.1f}s remaining)"
                )
                self.suite_state.warning_issued = True
        
        # Check test timeout
        if self.test_state:
            if self.test_state.elapsed_seconds >= self.test_state.timeout_seconds:
                return "test"
            
            if self.test_state.should_warn:
                self._warn(
                    f"Test timeout warning: {self.test_state.percent_used:.1f}% used "
                    f"({self.test_state.remaining_seconds:.1f}s remaining)"
                )
                self.test_state.warning_issued = True
        
        return None
    
    def get_time_budget(self) -> Dict[str, float]:
        """
        Get remaining time budget for all levels
        
        Returns:
            Dictionary with remaining time for each level
        """
        budget = {}
        
        if self.global_state:
            budget['global'] = self.global_state.remaining_seconds
        
        if self.suite_state:
            budget['suite'] = self.suite_state.remaining_seconds
        
        if self.test_state:
            budget['test'] = self.test_state.remaining_seconds
        
        return budget
    
    def estimate_remaining_tests(self, total_tests: int) -> Optional[int]:
        """
        Estimate how many more tests can run within timeout
        
        Args:
            total_tests: Total number of tests to run
        
        Returns:
            Estimated number of tests that can run (None if unlimited)
        """
        if self.tests_run == 0:
            return None  # No data yet
        
        # Calculate average test time
        avg_test_time = self.total_test_time / self.tests_run
        
        # Get remaining time
        effective_timeout = self.get_effective_timeout()
        if effective_timeout is None:
            return None
        
        # Estimate remaining tests
        remaining_tests = int(effective_timeout / avg_test_time)
        
        return remaining_tests
    
    def should_continue(self, remaining_tests: int) -> bool:
        """
        Determine if execution should continue
        
        Args:
            remaining_tests: Number of tests left to run
        
        Returns:
            True if should continue execution
        """
        estimated = self.estimate_remaining_tests(remaining_tests)
        
        if estimated is None:
            return True  # No timeout constraints
        
        if estimated == 0:
            self._warn("Insufficient time remaining for tests")
            return False
        
        if estimated < remaining_tests:
            self._warn(
                f"Time budget may not allow all tests "
                f"(estimated {estimated} of {remaining_tests} can complete)"
            )
        
        return True
    
    def _warn(self, message: str) -> None:
        """Issue warning via callback"""
        if self.warning_callback:
            self.warning_callback(message)


class AsyncTimeoutContext:
    """
    Async context manager for timeout handling
    
    Usage:
        async with AsyncTimeoutContext(timeout_seconds=60) as ctx:
            await some_long_operation()
            
            if ctx.should_warn():
                print("Taking too long!")
    """
    
    def __init__(
        self,
        timeout_seconds: float,
        grace_period_seconds: float = 10.0,
        warning_callback: Optional[Callable[[str], None]] = None,
    ):
        """
        Initialize timeout context
        
        Args:
            timeout_seconds: Timeout duration
            grace_period_seconds: Grace period for cleanup
            warning_callback: Optional warning callback
        """
        self.timeout_seconds = timeout_seconds
        self.grace_period_seconds = grace_period_seconds
        self.warning_callback = warning_callback
        
        self.state: Optional[TimeoutState] = None
        self.task: Optional[asyncio.Task] = None
    
    async def __aenter__(self):
        """Enter context"""
        self.state = TimeoutState(
            start_time=time.time(),
            timeout_seconds=self.timeout_seconds,
        )
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Exit context"""
        self.state = None
        return False
    
    @property
    def elapsed(self) -> float:
        """Get elapsed time"""
        return self.state.elapsed_seconds if self.state else 0.0
    
    @property
    def remaining(self) -> float:
        """Get remaining time"""
        return self.state.remaining_seconds if self.state else 0.0
    
    def should_warn(self) -> bool:
        """Check if should warn about timeout"""
        if not self.state:
            return False
        
        if self.state.should_warn:
            if self.warning_callback:
                self.warning_callback(
                    f"Timeout warning: {self.state.percent_used:.1f}% elapsed"
                )
            self.state.warning_issued = True
            return True
        
        return False
