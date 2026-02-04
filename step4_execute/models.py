"""
Data models for Step 4: Test Execution

This module contains all data structures used throughout test execution:
- Execution status and outcomes
- Test results and reports
- Process management structures
- Exit codes

Author: TB Eval Team
Version: 0.1.0
"""

from dataclasses import dataclass, field, asdict
from enum import Enum
from typing import List, Optional, Dict, Any, Set
from datetime import datetime
from pathlib import Path
import json


# =============================================================================
# ENUMS
# =============================================================================

class ExecutionStatus(Enum):
    """Overall execution status"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    TIMEOUT = "timeout"
    CANCELLED = "cancelled"
    ERROR = "error"
    PARTIAL = "partial"  # Completed some, not all


class TestOutcome(Enum):
    """Individual test outcome"""
    PASSED = "passed"
    FAILED = "failed"
    ERROR = "error"
    SKIPPED = "skipped"
    TIMEOUT = "timeout"
    CRASHED = "crashed"
    
    @property
    def symbol(self) -> str:
        """Get symbol for CLI display"""
        symbols = {
            TestOutcome.PASSED: "✓",
            TestOutcome.FAILED: "✗",
            TestOutcome.ERROR: "⚠",
            TestOutcome.SKIPPED: "○",
            TestOutcome.TIMEOUT: "⏱",
            TestOutcome.CRASHED: "💥",
        }
        return symbols.get(self, "?")
    
    @property
    def is_success(self) -> bool:
        """Check if outcome represents success"""
        return self == TestOutcome.PASSED
    
    @property
    def is_failure(self) -> bool:
        """Check if outcome represents failure"""
        return self in [TestOutcome.FAILED, TestOutcome.ERROR, 
                       TestOutcome.TIMEOUT, TestOutcome.CRASHED]


class OutputFormat(Enum):
    """Test output format"""
    JUNIT_XML = "junit_xml"
    VUNIT_JSON = "vunit_json"
    COCOTB_XML = "cocotb_xml"
    CONSOLE = "console"
    UNKNOWN = "unknown"


class CoverageFormat(Enum):
    """Coverage data format"""
    VERILATOR_DAT = "verilator_dat"
    QUESTA_UCDB = "questa_ucdb"
    LCOV = "lcov"
    GCOV = "gcov"
    UNKNOWN = "unknown"


# =============================================================================
# EXIT CODES
# =============================================================================

class ExitCode(Enum):
    """Exit codes for Step 4 execution"""
    # Success
    SUCCESS = 0
    
    # Test failures (1-9)
    TESTS_FAILED = 1
    TESTS_TIMED_OUT = 2
    TESTS_ERRORED = 3
    TESTS_PARTIAL = 4  # Some tests didn't run
    
    # Execution problems (10-19)
    CONFIG_ERROR = 10
    MANIFEST_ERROR = 11
    EXECUTION_ERROR = 12
    PARSER_ERROR = 13
    
    # Environment problems (20-29)
    SIMULATOR_NOT_FOUND = 20
    LICENSE_ERROR = 21
    DEPENDENCY_ERROR = 22
    FILE_NOT_FOUND = 23
    
    # User actions (30-39)
    USER_CANCELLED = 30
    DRY_RUN = 31  # Dry run completed
    
    # System problems (40-49)
    SYSTEM_ERROR = 40
    OUT_OF_RESOURCES = 41
    PERMISSION_ERROR = 42
    
    @classmethod
    def from_test_report(cls, report: 'TestReport') -> 'ExitCode':
        """Determine exit code from test report"""
        if not report.completed:
            if report.completion_reason == "user_cancelled":
                return cls.USER_CANCELLED
            elif report.completion_reason == "timeout":
                return cls.TESTS_TIMED_OUT
            elif report.completion_reason == "error":
                return cls.EXECUTION_ERROR
            return cls.TESTS_PARTIAL
        
        # Check test outcomes
        if report.summary.failed > 0:
            return cls.TESTS_FAILED
        elif report.summary.errors > 0:
            return cls.TESTS_ERRORED
        elif report.summary.timeout > 0:
            return cls.TESTS_TIMED_OUT
        elif report.summary.crashed > 0:
            return cls.TESTS_ERRORED
        
        return cls.SUCCESS


# =============================================================================
# CAPTURED OUTPUT
# =============================================================================

@dataclass
class CapturedOutput:
    """
    Captured process output
    
    Attributes:
        stdout: Standard output (may be truncated)
        stderr: Standard error (may be truncated)
        combined: Combined output in execution order
        log_file: Path to full log file
        truncated: Whether output was truncated
        size_bytes: Total output size
    """
    stdout: str = ""
    stderr: str = ""
    combined: str = ""
    log_file: Optional[str] = None
    truncated: bool = False
    size_bytes: int = 0
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


# =============================================================================
# PROCESS RESULT
# =============================================================================

@dataclass
class ProcessResult:
    """
    Result of subprocess execution
    
    Attributes:
        command: Command that was executed
        exit_code: Process exit code
        output: Captured output
        duration_ms: Execution duration
        timed_out: Whether process timed out
        killed: Whether process was killed
        signal: Signal that terminated process (if any)
        peak_memory_mb: Peak memory usage
        peak_cpu_percent: Peak CPU usage
    """
    command: List[str]
    exit_code: int
    output: CapturedOutput
    duration_ms: float
    timed_out: bool = False
    killed: bool = False
    signal: Optional[int] = None
    peak_memory_mb: Optional[float] = None
    peak_cpu_percent: Optional[float] = None
    
    @property
    def success(self) -> bool:
        """Check if process succeeded"""
        return self.exit_code == 0 and not self.timed_out
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "command": self.command,
            "exit_code": self.exit_code,
            "output": self.output.to_dict() if self.output else None,
            "duration_ms": self.duration_ms,
            "timed_out": self.timed_out,
            "killed": self.killed,
            "signal": self.signal,
            "peak_memory_mb": self.peak_memory_mb,
            "peak_cpu_percent": self.peak_cpu_percent,
        }


# =============================================================================
# TEST RESULT
# =============================================================================

@dataclass
class AssertionStats:
    """Statistics about assertions in a test"""
    total: int = 0
    passed: int = 0
    failed: int = 0
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class TestArtifacts:
    """Paths to test artifacts"""
    log_file: Optional[str] = None
    waveform_file: Optional[str] = None
    coverage_file: Optional[str] = None
    core_dump: Optional[str] = None
    additional_files: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class TestResult:
    """
    Result of a single test execution
    
    Attributes:
        name: Test name
        full_name: Fully qualified test name
        outcome: Test outcome (passed/failed/error/etc.)
        duration_ms: Test duration in milliseconds
        message: Failure/error message (if any)
        details: Additional details about failure
        stdout: Captured standard output
        stderr: Captured standard error
        log_file: Path to full log file
        attempts: Number of execution attempts (for retry)
        flaky: Whether test is marked as flaky
        assertions: Assertion statistics
        artifacts: Test artifacts (logs, waves, coverage)
        metadata: Additional test metadata
        process_result: Underlying process execution result
    """
    name: str
    full_name: str
    outcome: TestOutcome
    duration_ms: float
    
    # Failure information
    message: Optional[str] = None
    details: Optional[str] = None
    traceback: Optional[str] = None
    
    # Output
    stdout: Optional[str] = None
    stderr: Optional[str] = None
    
    # Execution info
    attempts: int = 1
    flaky: bool = False
    
    # Statistics
    assertions: AssertionStats = field(default_factory=AssertionStats)
    
    # Artifacts
    artifacts: TestArtifacts = field(default_factory=TestArtifacts)
    
    # Metadata
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    # Process info
    process_result: Optional[ProcessResult] = None
    
    # Timestamps
    start_time: Optional[str] = None
    end_time: Optional[str] = None
    
    @property
    def passed(self) -> bool:
        """Check if test passed"""
        return self.outcome.is_success
    
    @property
    def failed(self) -> bool:
        """Check if test failed"""
        return self.outcome.is_failure
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "full_name": self.full_name,
            "outcome": self.outcome.value,
            "duration_ms": self.duration_ms,
            "message": self.message,
            "details": self.details,
            "traceback": self.traceback,
            "stdout": self.stdout,
            "stderr": self.stderr,
            "attempts": self.attempts,
            "flaky": self.flaky,
            "assertions": self.assertions.to_dict(),
            "artifacts": self.artifacts.to_dict(),
            "metadata": self.metadata,
            "process_result": self.process_result.to_dict() if self.process_result else None,
            "start_time": self.start_time,
            "end_time": self.end_time,
        }


# =============================================================================
# TEST SUMMARY
# =============================================================================

@dataclass
class TestSummary:
    """
    Summary statistics for test execution
    
    Attributes:
        total_tests: Total number of tests
        completed_tests: Number of tests that completed (successfully or not)
        passed: Number of passed tests
        failed: Number of failed tests
        errors: Number of errored tests
        skipped: Number of skipped tests
        timeout: Number of timed out tests
        crashed: Number of crashed tests
        flaky: Number of flaky tests (passed after retry)
        total_duration_ms: Total execution duration
        average_duration_ms: Average test duration
    """
    total_tests: int = 0
    completed_tests: int = 0
    passed: int = 0
    failed: int = 0
    errors: int = 0
    skipped: int = 0
    timeout: int = 0
    crashed: int = 0
    flaky: int = 0
    total_duration_ms: float = 0.0
    average_duration_ms: float = 0.0
    
    @property
    def incomplete_tests(self) -> int:
        """Number of tests that didn't complete"""
        return self.total_tests - self.completed_tests
    
    @property
    def success_rate(self) -> float:
        """Calculate success rate (0.0 to 1.0)"""
        if self.completed_tests == 0:
            return 0.0
        return self.passed / self.completed_tests
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            **asdict(self),
            "incomplete_tests": self.incomplete_tests,
            "success_rate": self.success_rate,
        }


# =============================================================================
# COVERAGE INFO
# =============================================================================

@dataclass
class CoverageFile:
    """Information about a coverage file"""
    test_name: Optional[str]  # None for merged/aggregate
    file_path: str
    format: CoverageFormat
    size_bytes: int
    valid: bool
    created_time: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "test_name": self.test_name,
            "file_path": self.file_path,
            "format": self.format.value,
            "size_bytes": self.size_bytes,
            "valid": self.valid,
            "created_time": self.created_time,
        }


@dataclass
class CoverageInfo:
    """
    Coverage collection information
    
    Attributes:
        files: List of coverage files
        primary_format: Primary coverage format
        merged_file: Path to merged coverage file (if created)
        per_test: Whether coverage is per-test or aggregate
        collection_method: How coverage was collected
    """
    files: List[CoverageFile] = field(default_factory=list)
    primary_format: CoverageFormat = CoverageFormat.UNKNOWN
    merged_file: Optional[str] = None
    per_test: bool = True
    collection_method: str = "automatic"
    
    @property
    def total_size_bytes(self) -> int:
        """Total size of all coverage files"""
        return sum(f.size_bytes for f in self.files)
    
    @property
    def valid_files(self) -> List[CoverageFile]:
        """Get only valid coverage files"""
        return [f for f in self.files if f.valid]
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "files": [f.to_dict() for f in self.files],
            "primary_format": self.primary_format.value,
            "merged_file": self.merged_file,
            "per_test": self.per_test,
            "collection_method": self.collection_method,
            "total_size_bytes": self.total_size_bytes,
        }


# =============================================================================
# EXECUTION METADATA
# =============================================================================

@dataclass
class ExecutionMetadata:
    """
    Metadata about test execution environment and configuration
    
    Attributes:
        timestamp: Execution start timestamp
        hostname: Host machine name
        username: User who ran execution
        working_directory: Working directory
        build_manifest: Path to build manifest
        command: Command line used
        framework_version: TB Eval framework version
        python_version: Python version
        environment: Relevant environment variables
    """
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    hostname: Optional[str] = None
    username: Optional[str] = None
    working_directory: Optional[str] = None
    build_manifest: Optional[str] = None
    command: Optional[str] = None
    framework_version: str = "0.1.0"
    python_version: Optional[str] = None
    environment: Dict[str, str] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


# =============================================================================
# RESOURCE USAGE
# =============================================================================

@dataclass
class ResourceUsage:
    """Resource usage statistics"""
    peak_memory_mb: Optional[float] = None
    peak_cpu_percent: Optional[float] = None
    disk_usage_mb: Optional[float] = None
    network_usage_mb: Optional[float] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


# =============================================================================
# DIAGNOSTICS
# =============================================================================

@dataclass
class Diagnostics:
    """
    Diagnostic information about execution
    
    Attributes:
        warnings: List of warnings
        errors: List of errors (non-fatal)
        resource_usage: Resource usage statistics
        performance_notes: Performance-related notes
    """
    warnings: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    resource_usage: ResourceUsage = field(default_factory=ResourceUsage)
    performance_notes: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "warnings": self.warnings,
            "errors": self.errors,
            "resource_usage": self.resource_usage.to_dict(),
            "performance_notes": self.performance_notes,
        }


# =============================================================================
# TEST REPORT (Main Output)
# =============================================================================

@dataclass
class TestReport:
    """
    Complete test execution report
    
    This is the main output of Step 4, consumed by Step 5 (Coverage).
    
    Attributes:
        schema_version: Report schema version
        framework_version: TB Eval framework version
        status: Overall execution status
        completed: Whether execution completed normally
        completion_reason: Reason if not completed normally
        
        summary: Test summary statistics
        results: Individual test results
        coverage: Coverage information
        
        execution_metadata: Execution environment metadata
        artifacts: Root directory for artifacts
        diagnostics: Diagnostic information
        
        exit_code: Exit code for this execution
    """
    # Schema
    schema_version: str = "1.0"
    framework_version: str = "0.1.0"
    
    # Status
    status: ExecutionStatus = ExecutionStatus.PENDING
    completed: bool = False
    completion_reason: Optional[str] = None
    
    # Results
    summary: TestSummary = field(default_factory=TestSummary)
    results: List[TestResult] = field(default_factory=list)
    incomplete_tests: List[str] = field(default_factory=list)
    
    # Coverage
    coverage: CoverageInfo = field(default_factory=CoverageInfo)
    
    # Metadata
    execution_metadata: ExecutionMetadata = field(default_factory=ExecutionMetadata)
    
    # Artifacts
    artifacts_root: Optional[str] = None
    logs_directory: Optional[str] = None
    waveforms_directory: Optional[str] = None
    coverage_directory: Optional[str] = None
    
    # Diagnostics
    diagnostics: Diagnostics = field(default_factory=Diagnostics)
    
    # Exit code
    exit_code: int = 0
    
    def add_result(self, result: TestResult) -> None:
        """Add a test result and update summary"""
        self.results.append(result)
        self._update_summary(result)
    
    def _update_summary(self, result: TestResult) -> None:
        """Update summary statistics with new result"""
        self.summary.completed_tests += 1
        self.summary.total_duration_ms += result.duration_ms
        
        if result.outcome == TestOutcome.PASSED:
            self.summary.passed += 1
        elif result.outcome == TestOutcome.FAILED:
            self.summary.failed += 1
        elif result.outcome == TestOutcome.ERROR:
            self.summary.errors += 1
        elif result.outcome == TestOutcome.SKIPPED:
            self.summary.skipped += 1
        elif result.outcome == TestOutcome.TIMEOUT:
            self.summary.timeout += 1
        elif result.outcome == TestOutcome.CRASHED:
            self.summary.crashed += 1
        
        if result.flaky:
            self.summary.flaky += 1
        
        # Update average
        if self.summary.completed_tests > 0:
            self.summary.average_duration_ms = (
                self.summary.total_duration_ms / self.summary.completed_tests
            )
    
    def finalize(self) -> None:
        """Finalize report - call after all tests complete"""
        self.completed = (
            self.summary.completed_tests == self.summary.total_tests
        )
        
        if not self.completed:
            self.completion_reason = "incomplete"
            self.status = ExecutionStatus.PARTIAL
        elif self.summary.failed > 0 or self.summary.errors > 0:
            self.status = ExecutionStatus.COMPLETED
        else:
            self.status = ExecutionStatus.COMPLETED
        
        # Set exit code
        self.exit_code = ExitCode.from_test_report(self).value
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return {
            "schema_version": self.schema_version,
            "framework_version": self.framework_version,
            "status": self.status.value,
            "completed": self.completed,
            "completion_reason": self.completion_reason,
            "summary": self.summary.to_dict(),
            "results": [r.to_dict() for r in self.results],
            "incomplete_tests": self.incomplete_tests,
            "coverage": self.coverage.to_dict(),
            "execution_metadata": self.execution_metadata.to_dict(),
            "artifacts": {
                "root": self.artifacts_root,
                "logs": self.logs_directory,
                "waveforms": self.waveforms_directory,
                "coverage": self.coverage_directory,
            },
            "diagnostics": self.diagnostics.to_dict(),
            "exit_code": self.exit_code,
        }
    
    def to_json(self, indent: int = 2) -> str:
        """Serialize to JSON string"""
        return json.dumps(self.to_dict(), indent=indent)
    
    def save(self, path: Path) -> None:
        """Save report to file"""
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(self.to_json())
    
    @classmethod
    def load(cls, path: Path) -> "TestReport":
        """Load report from file"""
        data = json.loads(Path(path).read_text())
        
        # Reconstruct report (simplified - full implementation would reconstruct all nested objects)
        report = cls(
            schema_version=data.get("schema_version", "1.0"),
            framework_version=data.get("framework_version", "0.1.0"),
            status=ExecutionStatus(data["status"]),
            completed=data["completed"],
            completion_reason=data.get("completion_reason"),
            exit_code=data.get("exit_code", 0),
        )
        
        return report
    
    def get_failed_tests(self) -> List[TestResult]:
        """Get all failed tests"""
        return [r for r in self.results if r.outcome == TestOutcome.FAILED]
    
    def get_errored_tests(self) -> List[TestResult]:
        """Get all errored tests"""
        return [r for r in self.results if r.outcome == TestOutcome.ERROR]
    
    def get_passed_tests(self) -> List[TestResult]:
        """Get all passed tests"""
        return [r for r in self.results if r.outcome == TestOutcome.PASSED]


# =============================================================================
# EXECUTION CONTEXT
# =============================================================================

@dataclass
class ExecutionContext:
    """
    Context for test execution
    
    Attributes:
        working_directory: Working directory for execution
        environment: Environment variables
        timeout: Timeout for this execution
        cleanup_on_success: Whether to cleanup artifacts on success
        track: Execution track ("A" or "B")
        manifest: Build manifest data
    """
    working_directory: Path
    environment: Dict[str, str] = field(default_factory=dict)
    timeout: Optional[float] = None
    cleanup_on_success: bool = False
    track: Optional[str] = None
    manifest: Optional[Dict[str, Any]] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "working_directory": str(self.working_directory),
            "environment": self.environment,
            "timeout": self.timeout,
            "cleanup_on_success": self.cleanup_on_success,
            "track": self.track,
        }
