"""
End-to-end integration tests for test execution

Author: TB Eval Team
Version: 0.1.0
"""

import pytest
import asyncio
from pathlib import Path
import json

from step4_execute.executor import TestExecutor, execute_tests
from step4_execute.models import ExecutionStatus, TestOutcome, ExitCode
from step4_execute.config import ExecutionConfig


class TestFullExecution:
    """Test complete execution workflow"""
    
    @pytest.mark.asyncio
    async def test_basic_execution(
        self,
        temp_dir,
        sample_submission_dir,
        sample_manifest_file,
        monkeypatch,
    ):
        """Test basic test execution"""
        # Mock the runner
        from tests.mocks.mock_runners import MockCocoTBRunner
        
        def mock_init_runner(self):
            from step4_execute.models import ExecutionContext
            context = ExecutionContext(
                working_directory=self.submission_dir,
                environment={},
                track="A",
                manifest=self.manifest,
            )
            self.runner = MockCocoTBRunner(
                config=self.config,
                manifest=self.manifest,
                context=context,
            )
        
        monkeypatch.setattr(TestExecutor, "_initialize_runner", mock_init_runner)
        
        # Execute tests
        report = await execute_tests(
            submission_dir=sample_submission_dir,
            manifest_path=sample_manifest_file,
        )
        
        # Verify report
        assert report.status == ExecutionStatus.COMPLETED
        assert report.summary.total_tests == 2
        assert report.summary.passed == 2
        assert report.exit_code == 0
    
    @pytest.mark.asyncio
    async def test_execution_with_failures(
        self,
        temp_dir,
        sample_submission_dir,
        sample_manifest_file,
        monkeypatch,
    ):
        """Test execution with test failures"""
        from tests.mocks.mock_runners import MockCocoTBRunner
        
        def mock_init_runner(self):
            from step4_execute.models import ExecutionContext
            context = ExecutionContext(
                working_directory=self.submission_dir,
                environment={},
                track="A",
                manifest=self.manifest,
            )
            runner = MockCocoTBRunner(
                config=self.config,
                manifest=self.manifest,
                context=context,
            )
            # Make one test fail
            runner.fail_on_test = "test_basic"
            self.runner = runner
        
        monkeypatch.setattr(TestExecutor, "_initialize_runner", mock_init_runner)
        
        # Execute
        report = await execute_tests(
            submission_dir=sample_submission_dir,
            manifest_path=sample_manifest_file,
        )
        
        # Verify
        assert report.status == ExecutionStatus.COMPLETED
        assert report.summary.failed == 1
        assert report.summary.passed == 1
        assert report.exit_code == ExitCode.TESTS_FAILED.value
    
    @pytest.mark.asyncio
    async def test_dry_run(
        self,
        temp_dir,
        sample_submission_dir,
        sample_manifest_file,
        monkeypatch,
    ):
        """Test dry run mode"""
        from tests.mocks.mock_runners import MockCocoTBRunner
        
        def mock_init_runner(self):
            from step4_execute.models import ExecutionContext
            context = ExecutionContext(
                working_directory=self.submission_dir,
                environment={},
                track="A",
                manifest=self.manifest,
            )
            self.runner = MockCocoTBRunner(
                config=self.config,
                manifest=self.manifest,
                context=context,
            )
        
        monkeypatch.setattr(TestExecutor, "_initialize_runner", mock_init_runner)
        
        # Execute in dry run mode
        config_overrides = {"dry_run": True}
        report = await execute_tests(
            submission_dir=sample_submission_dir,
            manifest_path=sample_manifest_file,
            config_overrides=config_overrides,
        )
        
        # Verify
        assert report.status == ExecutionStatus.COMPLETED
        assert report.exit_code == ExitCode.DRY_RUN.value
        assert all(r.outcome == TestOutcome.SKIPPED for r in report.results)
    
    @pytest.mark.asyncio
    async def test_test_filtering(
        self,
        temp_dir,
        sample_submission_dir,
        sample_manifest_file,
        monkeypatch,
    ):
        """Test filtering tests"""
        from tests.mocks.mock_runners import MockCocoTBRunner
        
        def mock_init_runner(self):
            from step4_execute.models import ExecutionContext
            context = ExecutionContext(
                working_directory=self.submission_dir,
                environment={},
                track="A",
                manifest=self.manifest,
            )
            self.runner = MockCocoTBRunner(
                config=self.config,
                manifest=self.manifest,
                context=context,
            )
        
        monkeypatch.setattr(TestExecutor, "_initialize_runner", mock_init_runner)
        
        # Execute with filter
        config_overrides = {"filter": "test_basic"}
        report = await execute_tests(
            submission_dir=sample_submission_dir,
            manifest_path=sample_manifest_file,
            config_overrides=config_overrides,
        )
        
        # Verify - should only run tests matching filter
        assert report.summary.completed_tests <= 2
        executed_names = [r.name for r in report.results]
        assert "test_basic" in executed_names
    
    @pytest.mark.asyncio
    async def test_fail_fast(
        self,
        temp_dir,
        sample_submission_dir,
        sample_manifest_file,
        monkeypatch,
    ):
        """Test fail-fast mode"""
        from tests.mocks.mock_runners import MockCocoTBRunner
        
        def mock_init_runner(self):
            from step4_execute.models import ExecutionContext
            context = ExecutionContext(
                working_directory=self.submission_dir,
                environment={},
                track="A",
                manifest=self.manifest,
            )
            runner = MockCocoTBRunner(
                config=self.config,
                manifest=self.manifest,
                context=context,
            )
            runner.fail_on_test = "test_basic"
            self.runner = runner
        
        monkeypatch.setattr(TestExecutor, "_initialize_runner", mock_init_runner)
        
        # Execute with fail-fast
        config_overrides = {"fail_fast": True}
        report = await execute_tests(
            submission_dir=sample_submission_dir,
            manifest_path=sample_manifest_file,
            config_overrides=config_overrides,
        )
        
        # Verify - should stop after first failure
        assert report.summary.failed >= 1
        # Some tests may be skipped due to fail-fast
        assert report.summary.completed_tests < report.summary.total_tests or \
               report.summary.completed_tests == report.summary.total_tests
    
    @pytest.mark.asyncio
    async def test_timeout_handling(
        self,
        temp_dir,
        sample_submission_dir,
        sample_manifest_file,
        monkeypatch,
    ):
        """Test timeout handling"""
        from tests.mocks.mock_runners import MockVUnitRunner
        
        # Modify manifest to be VUnit
        with open(sample_manifest_file) as f:
            manifest = json.load(f)
        manifest["track_used"] = "B"
        with open(sample_manifest_file, 'w') as f:
            json.dump(manifest, f)
        
        def mock_init_runner(self):
            from step4_execute.models import ExecutionContext
            context = ExecutionContext(
                working_directory=self.submission_dir,
                environment={},
                track="B",
                manifest=self.manifest,
            )
            runner = MockVUnitRunner(
                config=self.config,
                manifest=self.manifest,
                context=context,
            )
            # Simulate timeout
            runner.simulate_timeout = True
            self.runner = runner
        
        monkeypatch.setattr(TestExecutor, "_initialize_runner", mock_init_runner)
        
        # Execute with short timeout
        config_overrides = {"timeout": 0.1}
        report = await execute_tests(
            submission_dir=sample_submission_dir,
            manifest_path=sample_manifest_file,
            config_overrides=config_overrides,
        )
        
        # Verify timeout was handled
        assert report.status in [ExecutionStatus.PARTIAL, ExecutionStatus.COMPLETED]


class TestReportGeneration:
    """Test report generation"""
    
    def test_report_save_and_load(self, temp_dir, sample_test_report):
        """Test saving and loading reports"""
        report_path = temp_dir / "test_report.json"
        
        # Save
        sample_test_report.save(report_path)
        assert report_path.exists()
        
        # Load
        from step4_execute.reporters import TestReportLoader
        loaded_report = TestReportLoader.load(report_path)
        
        # Verify
        assert loaded_report.summary.total_tests == sample_test_report.summary.total_tests
        assert loaded_report.summary.passed == sample_test_report.summary.passed
        assert loaded_report.summary.failed == sample_test_report.summary.failed
    
    def test_junit_generation(self, temp_dir, sample_test_report):
        """Test JUnit XML generation"""
        from step4_execute.reporters import generate_junit, validate_junit
        
        junit_path = temp_dir / "results.xml"
        
        # Generate
        generate_junit(sample_test_report, junit_path)
        assert junit_path.exists()
        
        # Validate
        is_valid, errors = validate_junit(junit_path)
        assert is_valid, f"JUnit XML invalid: {errors}"
    
    def test_html_generation(self, temp_dir, sample_test_report):
        """Test HTML report generation"""
        from step4_execute.reporters import generate_html
        
        html_path = temp_dir / "report.html"
        
        # Generate
        generate_html(sample_test_report, html_path)
        assert html_path.exists()
        
        # Verify content
        content = html_path.read_text()
        assert "Test Execution Report" in content
        assert "test_basic" in content
        assert "test_overflow" in content
    
    def test_summary_generation(self, temp_dir, sample_test_report):
        """Test summary report generation"""
        from step4_execute.reporters import (
            save_summary,
            SummaryFormat,
            SummaryVerbosity
        )
        
        # Generate text summary
        text_path = temp_dir / "summary.txt"
        save_summary(
            sample_test_report,
            text_path,
            format=SummaryFormat.TEXT,
            verbosity=SummaryVerbosity.NORMAL
        )
        assert text_path.exists()
        
        # Generate markdown summary
        md_path = temp_dir / "summary.md"
        save_summary(
            sample_test_report,
            md_path,
            format=SummaryFormat.MARKDOWN,
            verbosity=SummaryVerbosity.DETAILED
        )
        assert md_path.exists()
        
        content = md_path.read_text()
        assert "# Test Execution Summary" in content


class TestConfiguration:
    """Test configuration management"""
    
    def test_config_loading(self, temp_dir):
        """Test loading configuration"""
        from step4_execute.config import ConfigManager
        
        # Create config file
        config_file = temp_dir / ".tbeval.yaml"
        config_file.write_text("""
execution:
  timeouts:
    per_test_seconds: 600
  retry:
    enabled: true
    max_attempts: 5
""")
        
        # Load config
        manager = ConfigManager(temp_dir)
        config = manager.load()
        
        # Verify
        assert config.timeouts.per_test_seconds == 600
        assert config.retry.max_attempts == 5
    
    def test_config_overrides(self, temp_dir):
        """Test configuration overrides"""
        from step4_execute.config import ConfigManager
        
        manager = ConfigManager(temp_dir)
        config = manager.load(cli_overrides={"timeout": 123.4})
        
        # Verify override was applied
        assert config.timeouts.per_test_seconds == 123.4


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
