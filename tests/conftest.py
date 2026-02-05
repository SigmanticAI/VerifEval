"""
Shared pytest fixtures for integration tests

Author: TB Eval Team
Version: 0.1.0
"""

import pytest
import tempfile
import shutil
from pathlib import Path
from datetime import datetime
import json

from step4_execute.models import (
    TestReport,
    TestResult,
    TestOutcome,
    TestSummary,
    ExecutionMetadata,
    ExecutionStatus,
    CoverageInfo,
    CoverageFile,
    CoverageFormat,
)
from step4_execute.config import ExecutionConfig


@pytest.fixture
def temp_dir():
    """Create temporary directory for tests"""
    temp = tempfile.mkdtemp()
    yield Path(temp)
    shutil.rmtree(temp, ignore_errors=True)


@pytest.fixture
def sample_submission_dir(temp_dir):
    """Create sample submission directory structure"""
    submission = temp_dir / "submission"
    submission.mkdir()
    
    # Create directory structure
    (submission / "rtl").mkdir()
    (submission / "tb").mkdir()
    (submission / ".tbeval").mkdir()
    
    # Create dummy files
    (submission / "rtl" / "adder.sv").write_text("// DUT")
    (submission / "tb" / "test_adder.py").write_text("# Test")
    
    return submission


@pytest.fixture
def sample_manifest(temp_dir):
    """Create sample build manifest"""
    manifest = {
        "schema_version": "1.0",
        "framework_version": "0.1.0",
        "build_status": "success",
        "timestamp": datetime.now().isoformat(),
        "duration_ms": 5000,
        "track_used": "A",
        "submission_dir": str(temp_dir / "submission"),
        "vunit_project": {
            "run_py_path": ".tbeval/vunit_project/run.py",
            "generated": True,
        },
        "simulator_config": {
            "simulator_type": "verilator",
            "available": True,
        },
        "compilation": {
            "status": "success",
            "total_files": 5,
        },
        "tests_discovered": {
            "tests": [
                {
                    "name": "test_basic",
                    "full_name": "test_adder.test_basic",
                    "testbench": "test_adder",
                    "library": "cocotb",
                    "test_type": "cocotb",
                    "status": "ready",
                    "timeout_ms": 30000,
                },
                {
                    "name": "test_overflow",
                    "full_name": "test_adder.test_overflow",
                    "testbench": "test_adder",
                    "library": "cocotb",
                    "test_type": "cocotb",
                    "status": "ready",
                    "timeout_ms": 30000,
                },
            ],
            "total_count": 2,
            "ready_count": 2,
        },
        "execution_command": ["make", "-C", ".tbeval/cocotb"],
        "execution_env": {
            "SIM": "verilator",
            "MODULE": "test_adder",
        },
        "execution_cwd": ".tbeval/cocotb",
    }
    
    return manifest


@pytest.fixture
def sample_manifest_file(temp_dir, sample_manifest):
    """Create sample manifest file"""
    manifest_path = temp_dir / "build_manifest.json"
    with open(manifest_path, 'w') as f:
        json.dump(sample_manifest, f, indent=2)
    return manifest_path


@pytest.fixture
def sample_test_results():
    """Create sample test results"""
    return [
        TestResult(
            name="test_basic",
            full_name="test_adder.test_basic",
            outcome=TestOutcome.PASSED,
            duration_ms=1234.5,
            message=None,
        ),
        TestResult(
            name="test_overflow",
            full_name="test_adder.test_overflow",
            outcome=TestOutcome.FAILED,
            duration_ms=567.8,
            message="Assertion failed: Expected 0, got 256",
            traceback="Traceback (most recent call last):\n  ...",
        ),
        TestResult(
            name="test_skip",
            full_name="test_adder.test_skip",
            outcome=TestOutcome.SKIPPED,
            duration_ms=0,
            message="Test skipped",
        ),
    ]


@pytest.fixture
def sample_test_report(sample_test_results):
    """Create sample test report"""
    report = TestReport()
    
    # Add metadata
    report.execution_metadata = ExecutionMetadata(
        timestamp=datetime.now().isoformat(),
        hostname="test-host",
        username="test-user",
        working_directory="/tmp/test",
        python_version="3.9.0",
    )
    
    # Add results
    report.results = sample_test_results
    
    # Update summary
    report.summary = TestSummary(
        total_tests=3,
        completed_tests=3,
        passed=1,
        failed=1,
        skipped=1,
        total_duration_ms=1802.3,
    )
    
    # Add coverage
    report.coverage = CoverageInfo(
        files=[
            CoverageFile(
                test_name="test_basic",
                file_path="/tmp/coverage.dat",
                format=CoverageFormat.VERILATOR_DAT,
                size_bytes=12345,
                valid=True,
            )
        ],
        primary_format=CoverageFormat.VERILATOR_DAT,
        per_test=True,
    )
    
    report.status = ExecutionStatus.COMPLETED
    report.finalize()
    
    return report


@pytest.fixture
def sample_config(temp_dir):
    """Create sample execution config"""
    config = ExecutionConfig(
        submission_dir=temp_dir / "submission",
        output_dir=temp_dir / "output",
        dry_run=False,
        fail_fast=False,
    )
    
    # Set reasonable timeouts for testing
    config.timeouts.per_test_seconds = 10
    config.timeouts.test_suite_seconds = 60
    config.timeouts.global_seconds = 120
    
    return config


@pytest.fixture
def mock_verilator(monkeypatch):
    """Mock verilator availability"""
    def mock_which(cmd):
        if cmd == "verilator":
            return "/usr/bin/verilator"
        return None
    
    import shutil
    monkeypatch.setattr(shutil, "which", mock_which)


@pytest.fixture
def mock_vunit(monkeypatch):
    """Mock VUnit availability"""
    def mock_import():
        pass
    
    # Mock VUnit import
    import sys
    from unittest.mock import MagicMock
    sys.modules['vunit'] = MagicMock()
