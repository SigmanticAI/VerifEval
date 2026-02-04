"""
Configuration management for Step 4: Test Execution

This module handles:
- Loading configuration from .tbeval.yaml execution section
- Merging configuration with CLI arguments
- Loading BuildManifest from Step 3
- Environment variable handling
- Configuration validation

Author: TB Eval Team
Version: 0.1.0
"""

import os
import json
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional, Dict, Any, List
import yaml

from .models import OutputFormat, CoverageFormat


# =============================================================================
# TIMEOUT CONFIGURATION
# =============================================================================

@dataclass
class TimeoutConfig:
    """
    Timeout configuration
    
    Attributes:
        per_test_seconds: Timeout per individual test
        test_suite_seconds: Timeout for entire test suite
        global_seconds: Absolute maximum timeout
        grace_period_seconds: Grace period before SIGKILL
        escalate_to_kill: Whether to escalate from SIGTERM to SIGKILL
    """
    per_test_seconds: float = 300.0  # 5 minutes
    test_suite_seconds: float = 1800.0  # 30 minutes
    global_seconds: float = 3600.0  # 1 hour
    grace_period_seconds: float = 10.0
    escalate_to_kill: bool = True
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "per_test_seconds": self.per_test_seconds,
            "test_suite_seconds": self.test_suite_seconds,
            "global_seconds": self.global_seconds,
            "grace_period_seconds": self.grace_period_seconds,
            "escalate_to_kill": self.escalate_to_kill,
        }


# =============================================================================
# RETRY CONFIGURATION
# =============================================================================

@dataclass
class RetryConfig:
    """
    Test retry configuration
    
    Attributes:
        enabled: Whether retry is enabled
        max_attempts: Maximum retry attempts per test
        retry_on: List of outcomes to retry
        delay_between_attempts: Delay between retry attempts (seconds)
        backoff_multiplier: Backoff multiplier for delays
        mark_flaky_if_pass_after_retry: Mark test as flaky if passes after retry
    """
    enabled: bool = True
    max_attempts: int = 3
    retry_on: List[str] = field(default_factory=lambda: ["timeout", "error"])
    delay_between_attempts: float = 2.0
    backoff_multiplier: float = 1.5
    mark_flaky_if_pass_after_retry: bool = True
    
    def should_retry(self, outcome: str, attempt: int) -> bool:
        """Check if outcome should be retried"""
        if not self.enabled:
            return False
        if attempt >= self.max_attempts:
            return False
        return outcome in self.retry_on
    
    def get_delay(self, attempt: int) -> float:
        """Get delay for given attempt number"""
        return self.delay_between_attempts * (self.backoff_multiplier ** attempt)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "enabled": self.enabled,
            "max_attempts": self.max_attempts,
            "retry_on": self.retry_on,
            "delay_between_attempts": self.delay_between_attempts,
            "backoff_multiplier": self.backoff_multiplier,
            "mark_flaky_if_pass_after_retry": self.mark_flaky_if_pass_after_retry,
        }


# =============================================================================
# PARALLELISM CONFIGURATION
# =============================================================================

@dataclass
class ParallelismConfig:
    """
    Parallel execution configuration
    
    Attributes:
        strategy: Parallelism strategy ("delegate" or "step4_managed")
        max_parallel_tests: Maximum parallel tests
        vunit_parallel_jobs: Jobs for VUnit -p flag
        cocotb_parallel_suites: Parallel CocoTB test files
    """
    strategy: str = "delegate"  # "delegate" or "step4_managed"
    max_parallel_tests: int = 4
    vunit_parallel_jobs: int = 4
    cocotb_parallel_suites: int = 1
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "strategy": self.strategy,
            "max_parallel_tests": self.max_parallel_tests,
            "vunit_parallel_jobs": self.vunit_parallel_jobs,
            "cocotb_parallel_suites": self.cocotb_parallel_suites,
        }


# =============================================================================
# ARTIFACT CONFIGURATION
# =============================================================================

@dataclass
class ArtifactRetentionConfig:
    """Configuration for artifact retention"""
    logs: bool = True
    waveforms: bool = True
    coverage: bool = True


@dataclass
class ArtifactConfig:
    """
    Artifact management configuration
    
    Attributes:
        retention: Retention settings by test outcome
        max_log_size_mb: Maximum log file size
        max_waveform_size_mb: Maximum waveform file size
        compress_logs: Whether to compress log files
        compress_after_days: Days before compression
        delete_after_days: Days before deletion
        organize_by_outcome: Organize by pass/fail
        organize_by_date: Organize by date
        organize_by_test: Organize by test name
    """
    # Retention by outcome
    passing_tests: ArtifactRetentionConfig = field(
        default_factory=lambda: ArtifactRetentionConfig(
            logs=False,
            waveforms=False,
            coverage=True
        )
    )
    failing_tests: ArtifactRetentionConfig = field(
        default_factory=lambda: ArtifactRetentionConfig(
            logs=True,
            waveforms=True,
            coverage=True
        )
    )
    error_tests: ArtifactRetentionConfig = field(
        default_factory=lambda: ArtifactRetentionConfig(
            logs=True,
            waveforms=True,
            coverage=True
        )
    )
    
    # Limits
    max_log_size_mb: int = 10
    max_waveform_size_mb: int = 100
    
    # Compression and cleanup
    compress_logs: bool = False
    compress_after_days: int = 1
    delete_after_days: int = 7
    
    # Organization
    organize_by_outcome: bool = True
    organize_by_date: bool = True
    organize_by_test: bool = True
    
    def should_keep(self, outcome: str, artifact_type: str) -> bool:
        """Determine if artifact should be kept"""
        if outcome == "passed":
            retention = self.passing_tests
        elif outcome == "failed":
            retention = self.failing_tests
        else:
            retention = self.error_tests
        
        return getattr(retention, artifact_type, True)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "retention": {
                "passing": {
                    "logs": self.passing_tests.logs,
                    "waveforms": self.passing_tests.waveforms,
                    "coverage": self.passing_tests.coverage,
                },
                "failing": {
                    "logs": self.failing_tests.logs,
                    "waveforms": self.failing_tests.waveforms,
                    "coverage": self.failing_tests.coverage,
                },
                "error": {
                    "logs": self.error_tests.logs,
                    "waveforms": self.error_tests.waveforms,
                    "coverage": self.error_tests.coverage,
                },
            },
            "limits": {
                "max_log_size_mb": self.max_log_size_mb,
                "max_waveform_size_mb": self.max_waveform_size_mb,
            },
            "compression": {
                "enabled": self.compress_logs,
                "after_days": self.compress_after_days,
                "delete_after_days": self.delete_after_days,
            },
            "organization": {
                "by_outcome": self.organize_by_outcome,
                "by_date": self.organize_by_date,
                "by_test": self.organize_by_test,
            },
        }


# =============================================================================
# COVERAGE CONFIGURATION (Step 4 specific)
# =============================================================================

@dataclass
class CoverageCollectionConfig:
    """
    Coverage collection configuration for Step 4
    
    Note: This is different from Step 3's coverage config.
    Step 4 only locates and organizes coverage, doesn't process it.
    
    Attributes:
        enabled: Whether to collect coverage
        granularity: "per_test" or "aggregate"
        locate_files: Whether to actively search for coverage files
        organize_files: Whether to organize coverage files
        validate_files: Whether to validate coverage files
        name_pattern: Naming pattern for coverage files
    """
    enabled: bool = True
    granularity: str = "per_test"  # "per_test" or "aggregate"
    locate_files: bool = True
    organize_files: bool = True
    validate_files: bool = True
    name_pattern: str = "coverage_{test_name}.dat"
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "enabled": self.enabled,
            "granularity": self.granularity,
            "locate_files": self.locate_files,
            "organize_files": self.organize_files,
            "validate_files": self.validate_files,
            "name_pattern": self.name_pattern,
        }


# =============================================================================
# OUTPUT CONFIGURATION
# =============================================================================

@dataclass
class OutputConfig:
    """
    Output and reporting configuration
    
    Attributes:
        verbosity: Output verbosity ("minimal", "normal", "verbose")
        stream_output: Whether to stream test output in real-time
        show_progress: Whether to show progress bar
        color: Whether to use colored output
        report_format: Primary report format
        export_junit: Whether to export JUnit XML
        export_html: Whether to export HTML report
    """
    verbosity: str = "normal"  # "minimal", "normal", "verbose"
    stream_output: bool = False
    show_progress: bool = True
    color: bool = True
    report_format: str = "json"
    export_junit: bool = False
    export_html: bool = False
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "verbosity": self.verbosity,
            "stream_output": self.stream_output,
            "show_progress": self.show_progress,
            "color": self.color,
            "report_format": self.report_format,
            "export_junit": self.export_junit,
            "export_html": self.export_html,
        }


# =============================================================================
# RESOURCE CONFIGURATION
# =============================================================================

@dataclass
class ResourceConfig:
    """
    Resource monitoring and limits
    
    Attributes:
        monitor_enabled: Whether to monitor resource usage
        warn_memory_mb: Warn if memory exceeds this
        warn_cpu_percent: Warn if CPU exceeds this
        enforce_limits: Whether to enforce hard limits (requires privileges)
        max_memory_per_test_mb: Hard memory limit per test
        max_cpu_time_seconds: Hard CPU time limit
    """
    monitor_enabled: bool = True
    warn_memory_mb: int = 4096
    warn_cpu_percent: int = 200
    enforce_limits: bool = False
    max_memory_per_test_mb: int = 8192
    max_cpu_time_seconds: int = 3600
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "monitor_enabled": self.monitor_enabled,
            "warn_memory_mb": self.warn_memory_mb,
            "warn_cpu_percent": self.warn_cpu_percent,
            "enforce_limits": self.enforce_limits,
            "max_memory_per_test_mb": self.max_memory_per_test_mb,
            "max_cpu_time_seconds": self.max_cpu_time_seconds,
        }


# =============================================================================
# TEST ORDERING CONFIGURATION
# =============================================================================

@dataclass
class TestOrderingConfig:
    """
    Test execution ordering configuration
    
    Attributes:
        strategy: Ordering strategy ("manifest", "alphabetical", "fastest_first", 
                                     "failed_first", "smart")
        use_historical_data: Whether to use historical test durations
        failed_tests_first: Whether to run failed tests first
    """
    strategy: str = "smart"  # "manifest", "alphabetical", "fastest_first", "failed_first", "smart"
    use_historical_data: bool = True
    failed_tests_first: bool = True
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "strategy": self.strategy,
            "use_historical_data": self.use_historical_data,
            "failed_tests_first": self.failed_tests_first,
        }


# =============================================================================
# MAIN EXECUTION CONFIGURATION
# =============================================================================

@dataclass
class ExecutionConfig:
    """
    Complete execution configuration for Step 4
    
    Configuration priority (highest to lowest):
    1. CLI arguments
    2. Environment variables
    3. .tbeval.yaml execution section
    4. BuildManifest hints
    5. Built-in defaults
    
    Attributes:
        submission_dir: Path to submission directory
        manifest_path: Path to build manifest from Step 3
        output_dir: Output directory for execution artifacts
        
        timeouts: Timeout configuration
        retry: Retry configuration
        parallelism: Parallelism configuration
        artifacts: Artifact management
        coverage: Coverage collection
        output: Output and reporting
        resources: Resource monitoring
        test_ordering: Test ordering strategy
        
        # Execution control
        dry_run: Whether to do dry run
        fail_fast: Stop on first failure
        test_filter: Filter pattern for test names
        rerun_failed: Only run previously failed tests
        
        # Advanced
        save_partial_results: Save results even if interrupted
        cleanup_on_success: Cleanup artifacts for passing tests
        debug_mode: Enable debug output
    """
    # Paths
    submission_dir: Path = Path(".")
    manifest_path: Optional[Path] = None
    output_dir: Path = Path(".tbeval/test_runs")
    
    # Configuration sections
    timeouts: TimeoutConfig = field(default_factory=TimeoutConfig)
    retry: RetryConfig = field(default_factory=RetryConfig)
    parallelism: ParallelismConfig = field(default_factory=ParallelismConfig)
    artifacts: ArtifactConfig = field(default_factory=ArtifactConfig)
    coverage: CoverageCollectionConfig = field(default_factory=CoverageCollectionConfig)
    output: OutputConfig = field(default_factory=OutputConfig)
    resources: ResourceConfig = field(default_factory=ResourceConfig)
    test_ordering: TestOrderingConfig = field(default_factory=TestOrderingConfig)
    
    # Execution control
    dry_run: bool = False
    fail_fast: bool = False
    test_filter: Optional[str] = None
    rerun_failed: bool = False
    
    # Advanced options
    save_partial_results: bool = True
    cleanup_on_success: bool = False
    debug_mode: bool = False
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "submission_dir": str(self.submission_dir),
            "manifest_path": str(self.manifest_path) if self.manifest_path else None,
            "output_dir": str(self.output_dir),
            "timeouts": self.timeouts.to_dict(),
            "retry": self.retry.to_dict(),
            "parallelism": self.parallelism.to_dict(),
            "artifacts": self.artifacts.to_dict(),
            "coverage": self.coverage.to_dict(),
            "output": self.output.to_dict(),
            "resources": self.resources.to_dict(),
            "test_ordering": self.test_ordering.to_dict(),
            "dry_run": self.dry_run,
            "fail_fast": self.fail_fast,
            "test_filter": self.test_filter,
            "rerun_failed": self.rerun_failed,
            "save_partial_results": self.save_partial_results,
            "cleanup_on_success": self.cleanup_on_success,
            "debug_mode": self.debug_mode,
        }


# =============================================================================
# CONFIGURATION MANAGER
# =============================================================================

class ConfigManager:
    """
    Manages configuration loading and merging
    
    Loads configuration from multiple sources in priority order:
    1. CLI arguments (highest priority)
    2. Environment variables
    3. .tbeval.yaml execution section
    4. BuildManifest hints
    5. Built-in defaults (lowest priority)
    """
    
    CONFIG_FILENAMES = [
        ".tbeval.yaml",
        ".tbeval.yml",
        "tbeval.yaml",
    ]
    
    def __init__(self, submission_dir: Path):
        self.submission_dir = Path(submission_dir)
        self.config_path: Optional[Path] = None
        self.raw_config: Dict[str, Any] = {}
        self.manifest_data: Optional[Dict[str, Any]] = None
    
    def load(
        self,
        manifest_path: Optional[Path] = None,
        cli_overrides: Optional[Dict[str, Any]] = None,
    ) -> ExecutionConfig:
        """
        Load and merge all configuration sources
        
        Args:
            manifest_path: Path to build manifest (default: submission_dir/build_manifest.json)
            cli_overrides: Dictionary of CLI argument overrides
        
        Returns:
            Merged ExecutionConfig
        """
        # Load build manifest
        manifest_path = manifest_path or (self.submission_dir / ".tbeval" / "build_manifest.json")
        if manifest_path.exists():
            with open(manifest_path) as f:
                self.manifest_data = json.load(f)
        
        # Load .tbeval.yaml
        self._load_config_file()
        
        # Build configuration with merging
        config = self._build_config(cli_overrides or {})
        
        return config
    
    def _load_config_file(self) -> None:
        """Find and load configuration file"""
        for filename in self.CONFIG_FILENAMES:
            config_path = self.submission_dir / filename
            if config_path.exists():
                self.config_path = config_path
                with open(config_path) as f:
                    self.raw_config = yaml.safe_load(f) or {}
                return
        
        self.raw_config = {}
    
    def _build_config(self, cli_overrides: Dict[str, Any]) -> ExecutionConfig:
        """Build final configuration from all sources"""
        exec_section = self.raw_config.get("execution", {})
        
        config = ExecutionConfig(
            submission_dir=self.submission_dir,
            manifest_path=self._get_manifest_path(),
            output_dir=self._get_output_dir(cli_overrides, exec_section),
        )
        
        # Build each configuration section
        config.timeouts = self._build_timeout_config(cli_overrides, exec_section)
        config.retry = self._build_retry_config(cli_overrides, exec_section)
        config.parallelism = self._build_parallelism_config(cli_overrides, exec_section)
        config.artifacts = self._build_artifact_config(cli_overrides, exec_section)
        config.coverage = self._build_coverage_config(cli_overrides, exec_section)
        config.output = self._build_output_config(cli_overrides, exec_section)
        config.resources = self._build_resource_config(cli_overrides, exec_section)
        config.test_ordering = self._build_test_ordering_config(cli_overrides, exec_section)
        
        # Execution control
        config.dry_run = cli_overrides.get("dry_run", False)
        config.fail_fast = cli_overrides.get("fail_fast", exec_section.get("fail_fast", False))
        config.test_filter = cli_overrides.get("filter", exec_section.get("test_filter"))
        config.rerun_failed = cli_overrides.get("rerun_failed", False)
        
        # Advanced
        config.save_partial_results = exec_section.get("save_partial_results", True)
        config.cleanup_on_success = cli_overrides.get(
            "cleanup",
            exec_section.get("cleanup_on_success", False)
        )
        config.debug_mode = cli_overrides.get("debug", False)
        
        return config
    
    def _build_timeout_config(
        self,
        cli: Dict[str, Any],
        yaml: Dict[str, Any]
    ) -> TimeoutConfig:
        """Build timeout configuration"""
        timeout_section = yaml.get("timeouts", {})
        
        return TimeoutConfig(
            per_test_seconds=cli.get("timeout") or timeout_section.get("per_test_seconds", 300.0),
            test_suite_seconds=timeout_section.get("test_suite_seconds", 1800.0),
            global_seconds=timeout_section.get("global_seconds", 3600.0),
            grace_period_seconds=timeout_section.get("grace_period_seconds", 10.0),
            escalate_to_kill=timeout_section.get("escalate_to_kill", True),
        )
    
    def _build_retry_config(
        self,
        cli: Dict[str, Any],
        yaml: Dict[str, Any]
    ) -> RetryConfig:
        """Build retry configuration"""
        retry_section = yaml.get("retry", {})
        
        enabled = cli.get("retry") if cli.get("retry") is not None else retry_section.get("enabled", True)
        
        return RetryConfig(
            enabled=enabled,
            max_attempts=cli.get("retry_count") or retry_section.get("max_attempts", 3),
            retry_on=retry_section.get("retry_on", ["timeout", "error"]),
            delay_between_attempts=retry_section.get("delay_between_attempts", 2.0),
            backoff_multiplier=retry_section.get("backoff_multiplier", 1.5),
            mark_flaky_if_pass_after_retry=retry_section.get("mark_flaky_if_pass_after_retry", True),
        )
    
    def _build_parallelism_config(
        self,
        cli: Dict[str, Any],
        yaml: Dict[str, Any]
    ) -> ParallelismConfig:
        """Build parallelism configuration"""
        parallel_section = yaml.get("parallelism", {})
        
        return ParallelismConfig(
            strategy=parallel_section.get("strategy", "delegate"),
            max_parallel_tests=cli.get("parallel") or parallel_section.get("max_parallel_tests", 4),
            vunit_parallel_jobs=parallel_section.get("vunit_parallel_jobs", 4),
            cocotb_parallel_suites=parallel_section.get("cocotb_parallel_suites", 1),
        )
    
    def _build_artifact_config(
        self,
        cli: Dict[str, Any],
        yaml: Dict[str, Any]
    ) -> ArtifactConfig:
        """Build artifact configuration"""
        artifact_section = yaml.get("artifacts", {})
        retention = artifact_section.get("retention", {})
        
        return ArtifactConfig(
            passing_tests=ArtifactRetentionConfig(
                logs=retention.get("passing_tests", {}).get("logs", False),
                waveforms=retention.get("passing_tests", {}).get("waveforms", False),
                coverage=retention.get("passing_tests", {}).get("coverage", True),
            ),
            failing_tests=ArtifactRetentionConfig(
                logs=retention.get("failing_tests", {}).get("logs", True),
                waveforms=retention.get("failing_tests", {}).get("waveforms", True),
                coverage=retention.get("failing_tests", {}).get("coverage", True),
            ),
            max_log_size_mb=artifact_section.get("limits", {}).get("max_log_size_mb", 10),
            max_waveform_size_mb=artifact_section.get("limits", {}).get("max_waveform_size_mb", 100),
        )
    
    def _build_coverage_config(
        self,
        cli: Dict[str, Any],
        yaml: Dict[str, Any]
    ) -> CoverageCollectionConfig:
        """Build coverage collection configuration"""
        coverage_section = yaml.get("coverage", {}).get("collection", {})
        
        return CoverageCollectionConfig(
            enabled=coverage_section.get("enabled", True),
            granularity=coverage_section.get("granularity", "per_test"),
            locate_files=coverage_section.get("locate_files", True),
            organize_files=coverage_section.get("organize_files", True),
            validate_files=coverage_section.get("validate_files", True),
        )
    
    def _build_output_config(
        self,
        cli: Dict[str, Any],
        yaml: Dict[str, Any]
    ) -> OutputConfig:
        """Build output configuration"""
        output_section = yaml.get("output", {})
        
        verbosity = "normal"
        if cli.get("verbose"):
            verbosity = "verbose"
        elif cli.get("quiet"):
            verbosity = "minimal"
        else:
            verbosity = output_section.get("verbosity", "normal")
        
        return OutputConfig(
            verbosity=verbosity,
            stream_output=cli.get("stream") or output_section.get("stream_output", False),
            show_progress=output_section.get("show_progress", True),
            color=not cli.get("no_color", False),
            report_format=cli.get("format") or output_section.get("report_format", "json"),
            export_junit=cli.get("junit") is not None,
            export_html=cli.get("html") is not None,
        )
    
    def _build_resource_config(
        self,
        cli: Dict[str, Any],
        yaml: Dict[str, Any]
    ) -> ResourceConfig:
        """Build resource configuration"""
        resource_section = yaml.get("resources", {})
        
        return ResourceConfig(
            monitor_enabled=resource_section.get("monitor_enabled", True),
            warn_memory_mb=resource_section.get("warn_memory_mb", 4096),
            warn_cpu_percent=resource_section.get("warn_cpu_percent", 200),
        )
    
    def _build_test_ordering_config(
        self,
        cli: Dict[str, Any],
        yaml: Dict[str, Any]
    ) -> TestOrderingConfig:
        """Build test ordering configuration"""
        ordering_section = yaml.get("test_ordering", {})
        
        return TestOrderingConfig(
            strategy=ordering_section.get("strategy", "smart"),
            use_historical_data=ordering_section.get("use_historical_data", True),
            failed_tests_first=ordering_section.get("failed_tests_first", True),
        )
    
    def _get_manifest_path(self) -> Optional[Path]:
        """Get build manifest path"""
        manifest_paths = [
            self.submission_dir / ".tbeval" / "build_manifest.json",
            self.submission_dir / "build_manifest.json",
        ]
        
        for path in manifest_paths:
            if path.exists():
                return path
        
        return None
    
    def _get_output_dir(
        self,
        cli: Dict[str, Any],
        yaml: Dict[str, Any]
    ) -> Path:
        """Get output directory"""
        if cli.get("output"):
            return Path(cli["output"])
        
        if yaml.get("output_dir"):
            return Path(yaml["output_dir"])
        
        return self.submission_dir / ".tbeval" / "test_runs"
    
    def get_manifest_data(self) -> Optional[Dict[str, Any]]:
        """Get loaded manifest data"""
        return self.manifest_data


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def load_config(
    submission_dir: Path,
    manifest_path: Optional[Path] = None,
    cli_overrides: Optional[Dict[str, Any]] = None,
) -> ExecutionConfig:
    """
    Convenience function to load execution configuration
    
    Args:
        submission_dir: Path to submission directory
        manifest_path: Path to build manifest (optional)
        cli_overrides: CLI argument overrides (optional)
    
    Returns:
        ExecutionConfig with merged configuration
    """
    manager = ConfigManager(submission_dir)
    return manager.load(manifest_path, cli_overrides)


def create_default_config_file(output_path: Path) -> None:
    """
    Create a default .tbeval.yaml with execution section
    
    Args:
        output_path: Path where to write the config file
    """
    default_config = {
        "execution": {
            "timeouts": {
                "per_test_seconds": 300,
                "test_suite_seconds": 1800,
                "global_seconds": 3600,
                "grace_period_seconds": 10,
            },
            "retry": {
                "enabled": True,
                "max_attempts": 3,
                "retry_on": ["timeout", "error"],
            },
            "parallelism": {
                "strategy": "delegate",
                "max_parallel_tests": 4,
            },
            "artifacts": {
                "retention": {
                    "passing_tests": {
                        "logs": False,
                        "waveforms": False,
                        "coverage": True,
                    },
                    "failing_tests": {
                        "logs": True,
                        "waveforms": True,
                        "coverage": True,
                    },
                },
            },
            "coverage": {
                "collection": {
                    "enabled": True,
                    "granularity": "per_test",
                },
            },
            "output": {
                "verbosity": "normal",
                "show_progress": True,
                "color": True,
            },
        },
    }
    
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_path, 'w') as f:
        yaml.dump(default_config, f, default_flow_style=False, sort_keys=False)
    
    print(f"Created default configuration: {output_path}")
