"""
Base Test Discovery Interface
=============================

Abstract base class for all test discovery implementations.

Author: TB Eval Team
Version: 0.1.0
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional, Dict, Any
import time

from ..models import TestCase, TestStatus, TestDiscoveryResult


@dataclass
class DiscoveryResult:
    """
    Result of test discovery operation
    
    Attributes:
        tests: List of discovered test cases
        source_files: Files that were scanned
        discovery_method: Method used for discovery
        duration_ms: Time taken for discovery
        errors: Errors encountered during discovery
        warnings: Warnings generated during discovery
        metadata: Additional discovery metadata
    """
    tests: List[TestCase] = field(default_factory=list)
    source_files: List[str] = field(default_factory=list)
    discovery_method: str = "unknown"
    duration_ms: float = 0.0
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    @property
    def test_count(self) -> int:
        """Get total number of tests"""
        return len(self.tests)
    
    @property
    def ready_count(self) -> int:
        """Get number of tests ready to run"""
        return sum(1 for t in self.tests if t.status == TestStatus.READY)
    
    def to_test_discovery_result(self) -> TestDiscoveryResult:
        """Convert to TestDiscoveryResult model"""
        return TestDiscoveryResult(
            tests=self.tests,
            total_count=self.test_count,
            ready_count=self.ready_count,
            skipped_count=sum(1 for t in self.tests if t.status == TestStatus.SKIPPED),
            discovery_method=self.discovery_method,
            duration_ms=self.duration_ms,
        )
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "tests": [t.to_dict() for t in self.tests],
            "source_files": self.source_files,
            "discovery_method": self.discovery_method,
            "duration_ms": self.duration_ms,
            "test_count": self.test_count,
            "ready_count": self.ready_count,
            "errors": self.errors,
            "warnings": self.warnings,
            "metadata": self.metadata,
        }


class BaseTestDiscovery(ABC):
    """
    Abstract base class for test discovery
    
    All discovery implementations must inherit from this class
    and implement the discover() method.
    """
    
    def __init__(self, submission_dir: Path):
        """
        Initialize discovery
        
        Args:
            submission_dir: Path to submission directory
        """
        self.submission_dir = Path(submission_dir)
    
    @abstractmethod
    def discover(self, source_files: List[Path]) -> DiscoveryResult:
        """
        Discover tests from source files
        
        Args:
            source_files: List of source files to scan
        
        Returns:
            DiscoveryResult with discovered tests
        """
        pass
    
    @abstractmethod
    def get_discovery_method(self) -> str:
        """Get name of discovery method"""
        pass
    
    def read_file_safe(self, file_path: Path) -> Optional[str]:
        """
        Safely read file content
        
        Args:
            file_path: Path to file
        
        Returns:
            File content or None if error
        """
        try:
            return file_path.read_text(encoding='utf-8', errors='ignore')
        except Exception as e:
            return None
    
    def timed_discover(self, source_files: List[Path]) -> DiscoveryResult:
        """
        Run discovery with timing
        
        Args:
            source_files: Files to scan
        
        Returns:
            DiscoveryResult with timing information
        """
        start_time = time.time()
        result = self.discover(source_files)
        result.duration_ms = (time.time() - start_time) * 1000
        return result
