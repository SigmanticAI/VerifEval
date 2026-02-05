"""
Step 4: Test Execution

This package handles test execution for the TB Eval framework.

Public API:
- TestExecutor: Main orchestrator
- execute_tests: Convenience function
- ExecutionConfig: Configuration management
- TestReport: Test execution report

Author: TB Eval Team
Version: 0.1.0
"""

from .executor import TestExecutor, execute_tests
from .config import ExecutionConfig, ConfigManager, load_config
from .models import TestReport, TestResult, TestOutcome, ExecutionStatus

__version__ = "0.1.0"

__all__ = [
    # Main classes
    "TestExecutor",
    "execute_tests",
    
    # Configuration
    "ExecutionConfig",
    "ConfigManager",
    "load_config",
    
    # Models
    "TestReport",
    "TestResult",
    "TestOutcome",
    "ExecutionStatus",
]
