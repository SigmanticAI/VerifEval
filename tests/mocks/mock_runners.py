"""
Mock runners for testing without actual simulators

Author: TB Eval Team
Version: 0.1.0
"""

from typing import List, Dict, Any
import asyncio

from step4_execute.models import TestResult, TestOutcome
from step4_execute.runners.base import BaseRunner


class MockCocoTBRunner(BaseRunner):
    """Mock CocoTB runner for testing"""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.execution_count = 0
        self.fail_on_test = None  # Set to test name to simulate failure
    
    async def run_all_tests(self) -> List[TestResult]:
        """Mock running all tests"""
        await asyncio.sleep(0.1)  # Simulate work
        
        results = []
        for test in self.get_test_list():
            result = await self.run_single_test(test)
            results.append(result)
        
        return results
    
    async def run_single_test(self, test: Dict[str, Any]) -> TestResult:
        """Mock running single test"""
        await asyncio.sleep(0.05)  # Simulate test execution
        self.execution_count += 1
        
        # Simulate failure if requested
        if self.fail_on_test and test["name"] == self.fail_on_test:
            outcome = TestOutcome.FAILED
            message = "Simulated test failure"
        else:
            outcome = TestOutcome.PASSED
            message = None
        
        return self.create_test_result(
            test=test,
            outcome=outcome,
            duration_ms=100.0,
            message=message,
        )
    
    async def list_tests(self) -> List[str]:
        """Mock listing tests"""
        return [t["full_name"] for t in self.get_test_list()]
    
    def validate_environment(self) -> List[str]:
        """Mock validation"""
        return []


class MockVUnitRunner(BaseRunner):
    """Mock VUnit runner for testing"""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.execution_count = 0
        self.simulate_timeout = False
    
    async def run_all_tests(self) -> List[TestResult]:
        """Mock running all tests"""
        await asyncio.sleep(0.1)
        
        results = []
        for test in self.get_test_list():
            result = await self.run_single_test(test)
            results.append(result)
        
        return results
    
    async def run_single_test(self, test: Dict[str, Any]) -> TestResult:
        """Mock running single test"""
        if self.simulate_timeout:
            await asyncio.sleep(100)  # Will timeout
        else:
            await asyncio.sleep(0.05)
        
        self.execution_count += 1
        
        return self.create_test_result(
            test=test,
            outcome=TestOutcome.PASSED,
            duration_ms=50.0,
        )
    
    async def list_tests(self) -> List[str]:
        """Mock listing tests"""
        return [t["full_name"] for t in self.get_test_list()]
    
    def validate_environment(self) -> List[str]:
        """Mock validation"""
        return []
