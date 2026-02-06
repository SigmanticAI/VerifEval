"""
Configuration management for Step 5: Coverage Analysis

This module handles:
- Loading configuration from .tbeval.yaml coverage section
- Merging configuration with CLI arguments
- Configuration validation
- Default values and thresholds

Configuration Priority (highest to lowest):
1. CLI arguments
2. Environment variables
3. .tbeval.yaml coverage.analysis section
4. Built-in defaults

Author: TB Eval Team
Version: 0.1.0
"""

import os
import sys
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Optional, Dict, Any, List
import yaml
import warnings


# =============================================================================
# THRESHOLD CONFIGURATION
# =============================================================================

@dataclass
class CoverageThresholds:
    """
    Coverage thresholds for quality gates (Q7.1 - from .tbeval.yaml)
    
    These thresholds determine pass/fail for coverage quality gates.
    
    Attributes:
        line: Minimum line coverage percentage
        branch: Minimum branch coverage percentage
        toggle: Minimum toggle coverage percentage
        fsm: Minimum FSM coverage percentage
        overall: Minimum overall weighted coverage percentage
    """
    line: float = 80.0
    branch: float = 90.0
    toggle: float = 70.0
    fsm: float = 75.0
    overall: float = 80.0
    
    def __post_init__(self):
        """Validate thresholds are in valid range"""
        for name, value in [
            ("line", self.line),
            ("branch", self.branch),
            ("toggle", self.toggle),
            ("fsm", self.fsm),
            ("overall", self.overall),
        ]:
            if not 0.0 <= value <= 100.0:
                raise ValueError(f"Threshold {name}={value} must be between 0 and 100")
    
    def check_compliance(
        self,
        line_pct: float,
        branch_pct: float,
        toggle_pct: float,
        fsm_pct: float,
        overall_score: float
    ) -> tuple[bool, List[str]]:
        """
        Check if coverage metrics meet thresholds
        
        Args:
            line_pct: Line coverage percentage
            branch_pct: Branch coverage percentage
            toggle_pct: Toggle coverage percentage
            fsm_pct: FSM coverage percentage
            overall_score: Overall weighted score (0.0-1.0)
        
        Returns:
            Tuple of (all_met, violations_list)
        """
        violations = []
        
        if line_pct < self.line:
            violations.append(f"Line coverage {line_pct:.1f}% < {self.line}%")
        
        if branch_pct < self.branch:
            violations.append(f"Branch coverage {branch_pct:.1f}% < {self.branch}%")
        
        if toggle_pct < self.toggle:
            violations.append(f"Toggle coverage {toggle_pct:.1f}% < {self.toggle}%")
        
        if fsm_pct < self.fsm:
            violations.append(f"FSM coverage {fsm_pct:.1f}% < {self.fsm}%")
        
        overall_pct = overall_score * 100.0
        if overall_pct < self.overall:
            violations.append(f"Overall coverage {overall_pct:.1f}% < {self.overall}%")
        
        return len(violations) == 0, violations
    
    def to_dict(self) -> Dict[str, float]:
        """Convert to dictionary"""
        return {
            "line": self.line,
            "branch": self.branch,
            "toggle": self.toggle,
            "fsm": self.fsm,
            "overall": self.overall,
        }


# =============================================================================
# WEIGHT CONFIGURATION
# =============================================================================

@dataclass
class CoverageWeights:
    """
    Weights for overall coverage score calculation (Q4.2)
    
    These weights determine how much each coverage metric contributes
    to the overall weighted score used by Step 7.
    
    Attributes:
        line: Weight for line coverage
        branch: Weight for branch coverage
        toggle: Weight for toggle coverage
        fsm: Weight for FSM coverage
    """
    line: float = 0.35
    branch: float = 0.35
    toggle: float = 0.20
    fsm: float = 0.10
    
    def __post_init__(self):
        """Validate weights sum to 1.0"""
        total = self.line + self.branch + self.toggle + self.fsm
        
        if not (0.99 <= total <= 1.01):  # Allow small floating point errors
            raise ValueError(
                f"Coverage weights must sum to 1.0, got {total:.4f}\n"
                f"  line={self.line}, branch={self.branch}, "
                f"toggle={self.toggle}, fsm={self.fsm}"
            )
        
        # Normalize to exactly 1.0
        if total != 1.0:
            factor = 1.0 / total
            self.line *= factor
            self.branch *= factor
            self.toggle *= factor
            self.fsm *= factor
    
    def to_dict(self) -> Dict[str, float]:
        """Convert to dictionary"""
        return {
            "line": self.line,
            "branch": self.branch,
            "toggle": self.toggle,
            "fsm": self.fsm,
        }


# =============================================================================
# PARSER CONFIGURATION
# =============================================================================

@dataclass
class ParserConfig:
    """
    Configuration for coverage parsers (Q11, Q12)
    
    Attributes:
        priority: Parser priority order (Q11: verilator, lcov, covered)
        verilator_tool_path: Path to verilator_coverage tool
        lcov_tool_path: Path to lcov tool
        covered_tool_path: Path to covered tool
        use_external_tools: Try external tools first (Q12 Option C)
        fallback_to_python: Fall back to Python parsing if tool fails
        validate_coverage_files: Validate file integrity
        skip_invalid_files: Skip invalid files instead of failing
    """
    priority: List[str] = field(default_factory=lambda: ["verilator", "lcov", "covered"])
    
    # Tool paths (auto-detected if None)
    verilator_tool_path: Optional[str] = None
    lcov_tool_path: Optional[str] = None
    covered_tool_path: Optional[str] = None
    
    # Q12: Try external tools, fallback to Python
    use_external_tools: bool = True
    fallback_to_python: bool = True
    
    # Validation
    validate_coverage_files: bool = True
    skip_invalid_files: bool = True
    
    def __post_init__(self):
        """Validate parser configuration"""
        valid_parsers = {"verilator", "lcov", "covered", "questa", "vcs"}
        
        for parser in self.priority:
            if parser not in valid_parsers:
                warnings.warn(
                    f"Unknown parser '{parser}' in priority list. "
                    f"Valid parsers: {valid_parsers}"
                )
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return asdict(self)


# =============================================================================
# MERGING CONFIGURATION
# =============================================================================

@dataclass
class MergingConfig:
    """
    Configuration for coverage merging (Q6.1, Q6.2, Q13)
    
    Attributes:
        strategy: Merging strategy (Q6.2: tool_preferred or python_only)
        per_test_analysis: Track per-test coverage (Q4.1)
        create_merged_file: Create physical merged coverage file
        track_unique_contributions: Track unique coverage per test (Q13)
        identify_redundant_tests: Identify tests with low unique coverage
        calculate_optimal_order: Calculate optimal test execution order
        essential_threshold: Minimum % unique coverage for essential tests
        redundant_threshold: Maximum % unique coverage for redundant tests
    """
    # Q6.2: Merging strategy
    strategy: str = "tool_preferred"  # "tool_preferred" or "python_only"
    
    # Q4.1: Hierarchical coverage
    per_test_analysis: bool = True
    create_merged_file: bool = True
    
    # Q13: Advanced tracking
    track_unique_contributions: bool = True
    identify_redundant_tests: bool = True
    calculate_optimal_order: bool = True
    
    # Thresholds for test classification
    essential_threshold: float = 5.0    # % unique coverage
    redundant_threshold: float = 1.0    # % unique coverage
    
    def __post_init__(self):
        """Validate merging configuration"""
        if self.strategy not in ["tool_preferred", "python_only"]:
            raise ValueError(
                f"Invalid merge strategy '{self.strategy}'. "
                f"Must be 'tool_preferred' or 'python_only'"
            )
        
        if self.essential_threshold < self.redundant_threshold:
            raise ValueError(
                f"essential_threshold ({self.essential_threshold}) must be >= "
                f"redundant_threshold ({self.redundant_threshold})"
            )
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return asdict(self)


# =============================================================================
# REPORTING CONFIGURATION
# =============================================================================

@dataclass
class ReportingConfig:
    """
    Configuration for report generation (Q5.2)
    
    Attributes:
        output_dir: Output directory for coverage reports
        generate_coverage_report: Generate coverage_report.json
        generate_summary_txt: Generate human-readable summary
        enrich_test_report: Add coverage to test_report.json (Q1.2)
        json_detail_level: Detail level for JSON output (Q5.2)
        identify_hotspots: Identify critical uncovered regions
        list_uncovered_lines: Include uncovered line list
        max_uncovered_lines: Maximum uncovered lines to list
        export_mutation_targets: Export mutation testing targets (Q5.1)
        max_mutation_targets: Maximum mutation targets to export
    """
    # Output directory
    output_dir: Path = Path(".tbeval/coverage")
    
    # Output files (Q1.2)
    generate_coverage_report: bool = True
    generate_summary_txt: bool = True
    enrich_test_report: bool = True
    
    # Detail level (Q5.2: summary, normal, full)
    json_detail_level: str = "full"
    
    # Analysis features
    identify_hotspots: bool = True
    list_uncovered_lines: bool = True
    max_uncovered_lines: int = 50
    
    # Step 6 integration (Q5.1)
    export_mutation_targets: bool = True
    max_mutation_targets: int = 100
    
    def __post_init__(self):
        """Validate reporting configuration"""
        if self.json_detail_level not in ["summary", "normal", "full"]:
            raise ValueError(
                f"Invalid json_detail_level '{self.json_detail_level}'. "
                f"Must be 'summary', 'normal', or 'full'"
            )
        
        # Ensure output_dir is a Path
        if isinstance(self.output_dir, str):
            self.output_dir = Path(self.output_dir)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        data = asdict(self)
        data["output_dir"] = str(self.output_dir)
        return data


# =============================================================================
# MAIN CONFIGURATION
# =============================================================================

@dataclass
class CoverageAnalysisConfig:
    """
    Main configuration for Step 5 coverage analysis
    
    This is the primary configuration class used throughout the coverage
    analysis pipeline.
    
    Attributes:
        test_report_path: Path to test_report.json from Step 4
        build_manifest_path: Path to build_manifest.json from Step 3 (Q1.3)
        submission_dir: Root submission directory
        thresholds: Coverage quality gate thresholds
        weights: Coverage metric weights for scoring
        parsers: Parser configuration
        merging: Coverage merging configuration
        reporting: Report generation configuration
        fail_on_threshold: Fail analysis if thresholds not met (Q7.1)
        debug_mode: Enable debug logging
    """
    # Input paths (Q1.3 - needs both test_report and build_manifest)
    test_report_path: Path
    build_manifest_path: Path
    submission_dir: Path = Path(".")
    
    # Sub-configurations
    thresholds: CoverageThresholds = field(default_factory=CoverageThresholds)
    weights: CoverageWeights = field(default_factory=CoverageWeights)
    parsers: ParserConfig = field(default_factory=ParserConfig)
    merging: MergingConfig = field(default_factory=MergingConfig)
    reporting: ReportingConfig = field(default_factory=ReportingConfig)
    
    # Execution control
    fail_on_threshold: bool = False  # Q7.1: Don't fail, just warn
    debug_mode: bool = False
    
    def __post_init__(self):
        """Validate and normalize paths"""
        # Convert strings to Path objects
        if isinstance(self.test_report_path, str):
            self.test_report_path = Path(self.test_report_path)
        if isinstance(self.build_manifest_path, str):
            self.build_manifest_path = Path(self.build_manifest_path)
        if isinstance(self.submission_dir, str):
            self.submission_dir = Path(self.submission_dir)
        
        # Validate required files exist
        if not self.test_report_path.exists():
            raise FileNotFoundError(
                f"Test report not found: {self.test_report_path}"
            )
        
        if not self.build_manifest_path.exists():
            raise FileNotFoundError(
                f"Build manifest not found: {self.build_manifest_path}"
            )
    
    @classmethod
    def from_yaml(
        cls,
        yaml_path: Path,
        test_report_path: Path,
        build_manifest_path: Path,
        cli_overrides: Optional[Dict[str, Any]] = None
    ) -> 'CoverageAnalysisConfig':
        """
        Load configuration from .tbeval.yaml
        
        Args:
            yaml_path: Path to .tbeval.yaml
            test_report_path: Path to test_report.json
            build_manifest_path: Path to build_manifest.json
            cli_overrides: CLI argument overrides (optional)
        
        Returns:
            CoverageAnalysisConfig instance
        
        Example:
            >>> config = CoverageAnalysisConfig.from_yaml(
            ...     Path(".tbeval.yaml"),
            ...     Path("test_report.json"),
            ...     Path("build_manifest.json")
            ... )
        """
        # Load YAML file
        if not yaml_path.exists():
            warnings.warn(f"Config file not found: {yaml_path}, using defaults")
            yaml_data = {}
        else:
            with open(yaml_path) as f:
                yaml_data = yaml.safe_load(f) or {}
        
        # Extract coverage section
        coverage_section = yaml_data.get("coverage", {})
        analysis_section = coverage_section.get("analysis", {})
        
        # Build configuration
        config = cls._build_from_sections(
            analysis_section,
            test_report_path,
            build_manifest_path,
            yaml_path.parent,
            cli_overrides or {}
        )
        
        return config
    
    @classmethod
    def _build_from_sections(
        cls,
        analysis_section: Dict[str, Any],
        test_report_path: Path,
        build_manifest_path: Path,
        submission_dir: Path,
        cli_overrides: Dict[str, Any]
    ) -> 'CoverageAnalysisConfig':
        """Build configuration from YAML sections and CLI overrides"""
        
        # Thresholds
        threshold_data = analysis_section.get("thresholds", {})
        thresholds = CoverageThresholds(
            line=cli_overrides.get("line_threshold") or threshold_data.get("line", 80.0),
            branch=cli_overrides.get("branch_threshold") or threshold_data.get("branch", 90.0),
            toggle=cli_overrides.get("toggle_threshold") or threshold_data.get("toggle", 70.0),
            fsm=cli_overrides.get("fsm_threshold") or threshold_data.get("fsm", 75.0),
            overall=cli_overrides.get("overall_threshold") or threshold_data.get("overall", 80.0),
        )
        
        # Weights
        weight_data = analysis_section.get("weights", {})
        weights = CoverageWeights(
            line=weight_data.get("line", 0.35),
            branch=weight_data.get("branch", 0.35),
            toggle=weight_data.get("toggle", 0.20),
            fsm=weight_data.get("fsm", 0.10),
        )
        
        # Parsers
        parser_data = analysis_section.get("parsers", [])
        if isinstance(parser_data, list):
            parser_priority = parser_data
        else:
            parser_priority = ["verilator", "lcov", "covered"]
        
        parsers = ParserConfig(
            priority=parser_priority,
            use_external_tools=analysis_section.get("use_external_tools", True),
            fallback_to_python=analysis_section.get("fallback_to_python", True),
        )
        
        # Merging
        merge_data = analysis_section.get("merging", {})
        merging = MergingConfig(
            strategy=merge_data.get("strategy", "tool_preferred"),
            per_test_analysis=merge_data.get("per_test_analysis", True),
            create_merged_file=merge_data.get("create_merged_file", True),
            track_unique_contributions=merge_data.get("track_unique_contributions", True),
            identify_redundant_tests=merge_data.get("identify_redundant_tests", True),
        )
        
        # Reporting
        report_data = analysis_section.get("reporting", {})
        output_dir = cli_overrides.get("output_dir") or report_data.get("output_dir", ".tbeval/coverage")
        
        reporting = ReportingConfig(
            output_dir=Path(output_dir),
            json_detail_level=cli_overrides.get("detail_level") or report_data.get("json_detail_level", "full"),
            identify_hotspots=report_data.get("identify_hotspots", True),
            export_mutation_targets=report_data.get("export_mutation_targets", True),
        )
        
        # Create config
        return cls(
            test_report_path=test_report_path,
            build_manifest_path=build_manifest_path,
            submission_dir=submission_dir,
            thresholds=thresholds,
            weights=weights,
            parsers=parsers,
            merging=merging,
            reporting=reporting,
            fail_on_threshold=cli_overrides.get("fail_on_threshold", False),
            debug_mode=cli_overrides.get("debug", False),
        )
    
    @classmethod
    def from_cli(
        cls,
        test_report: str,
        build_manifest: Optional[str] = None,
        config_file: Optional[str] = None,
        **kwargs
    ) -> 'CoverageAnalysisConfig':
        """
        Create configuration from CLI arguments
        
        Args:
            test_report: Path to test_report.json
            build_manifest: Path to build_manifest.json (optional, auto-detect)
            config_file: Path to .tbeval.yaml (optional, auto-detect)
            **kwargs: Additional CLI overrides
        
        Returns:
            CoverageAnalysisConfig instance
        
        Example:
            >>> config = CoverageAnalysisConfig.from_cli(
            ...     test_report="test_report.json",
            ...     line_threshold=85.0
            ... )
        """
        test_report_path = Path(test_report)
        
        # Auto-detect build_manifest if not provided
        if build_manifest is None:
            manifest_path = test_report_path.parent / "build_manifest.json"
            if not manifest_path.exists():
                manifest_path = Path(".tbeval/build_manifest.json")
        else:
            manifest_path = Path(build_manifest)
        
        # Auto-detect config file if not provided
        if config_file is None:
            for name in [".tbeval.yaml", ".tbeval.yml", "tbeval.yaml"]:
                config_path = Path(name)
                if config_path.exists():
                    break
            else:
                config_path = Path(".tbeval.yaml")
        else:
            config_path = Path(config_file)
        
        # Load from YAML with CLI overrides
        return cls.from_yaml(
            config_path,
            test_report_path,
            manifest_path,
            cli_overrides=kwargs
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Serialize configuration to dictionary
        
        Returns:
            Dictionary representation
        """
        return {
            "paths": {
                "test_report": str(self.test_report_path),
                "build_manifest": str(self.build_manifest_path),
                "submission_dir": str(self.submission_dir),
            },
            "thresholds": self.thresholds.to_dict(),
            "weights": self.weights.to_dict(),
            "parsers": self.parsers.to_dict(),
            "merging": self.merging.to_dict(),
            "reporting": self.reporting.to_dict(),
            "execution": {
                "fail_on_threshold": self.fail_on_threshold,
                "debug_mode": self.debug_mode,
            },
        }
    
    def to_yaml(self, path: Path) -> None:
        """
        Save configuration to YAML file
        
        Args:
            path: Output YAML file path
        """
        data = {
            "coverage": {
                "analysis": {
                    "thresholds": self.thresholds.to_dict(),
                    "weights": self.weights.to_dict(),
                    "parsers": self.parsers.priority,
                    "merging": self.merging.to_dict(),
                    "reporting": self.reporting.to_dict(),
                }
            }
        }
        
        with open(path, 'w') as f:
            yaml.dump(data, f, default_flow_style=False, sort_keys=False)
    
    def validate(self) -> List[str]:
        """
        Validate configuration
        
        Returns:
            List of validation warnings/errors
        """
        issues = []
        
        # Check paths exist
        if not self.test_report_path.exists():
            issues.append(f"Test report not found: {self.test_report_path}")
        
        if not self.build_manifest_path.exists():
            issues.append(f"Build manifest not found: {self.build_manifest_path}")
        
        # Check threshold consistency
        if self.thresholds.overall > 100.0:
            issues.append(f"Overall threshold {self.thresholds.overall}% > 100%")
        
        # Check weights sum to 1.0
        weight_sum = (self.weights.line + self.weights.branch + 
                     self.weights.toggle + self.weights.fsm)
        if not (0.99 <= weight_sum <= 1.01):
            issues.append(f"Weights sum to {weight_sum:.4f}, should be 1.0")
        
        return issues


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def load_config_from_yaml(yaml_path: Path) -> CoverageAnalysisConfig:
    """
    Convenience function to load configuration from YAML
    
    Args:
        yaml_path: Path to .tbeval.yaml
    
    Returns:
        CoverageAnalysisConfig instance
    
    Raises:
        FileNotFoundError: If test_report.json or build_manifest.json not found
    """
    # Auto-detect test_report.json and build_manifest.json
    yaml_dir = yaml_path.parent
    
    test_report_path = yaml_dir / ".tbeval" / "test_runs" / "test_report.json"
    if not test_report_path.exists():
        test_report_path = yaml_dir / "test_report.json"
    
    build_manifest_path = yaml_dir / ".tbeval" / "build_manifest.json"
    if not build_manifest_path.exists():
        build_manifest_path = yaml_dir / "build_manifest.json"
    
    return CoverageAnalysisConfig.from_yaml(
        yaml_path,
        test_report_path,
        build_manifest_path
    )


def create_default_config_file(output_path: Path) -> None:
    """
    Create a default .tbeval.yaml with coverage analysis section
    
    Args:
        output_path: Where to write the config file
    
    Example:
        >>> create_default_config_file(Path(".tbeval.yaml"))
    """
    default_config = {
        "coverage": {
            "analysis": {
                "enabled": True,
                "auto_analyze": True,
                
                "parsers": ["verilator", "lcov", "covered"],
                
                "thresholds": {
                    "line": 80.0,
                    "branch": 90.0,
                    "toggle": 70.0,
                    "fsm": 75.0,
                    "overall": 80.0,
                },
                
                "weights": {
                    "line": 0.35,
                    "branch": 0.35,
                    "toggle": 0.20,
                    "fsm": 0.10,
                },
                
                "merging": {
                    "strategy": "tool_preferred",
                    "per_test_analysis": True,
                    "create_merged_file": True,
                    "track_unique_contributions": True,
                    "identify_redundant_tests": True,
                },
                
                "reporting": {
                    "output_dir": ".tbeval/coverage",
                    "json_detail_level": "full",
                    "identify_hotspots": True,
                    "export_mutation_targets": True,
                },
                
                "fail_on_threshold": False,
            }
        }
    }
    
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_path, 'w') as f:
        yaml.dump(default_config, f, default_flow_style=False, sort_keys=False)
    
    print(f"Created default configuration: {output_path}")


# =============================================================================
# ENVIRONMENT VARIABLE SUPPORT
# =============================================================================

def load_config_from_env() -> Dict[str, Any]:
    """
    Load configuration overrides from environment variables
    
    Environment variables:
        TBEVAL_COV_LINE_THRESHOLD: Line coverage threshold
        TBEVAL_COV_BRANCH_THRESHOLD: Branch coverage threshold
        TBEVAL_COV_TOGGLE_THRESHOLD: Toggle coverage threshold
        TBEVAL_COV_DEBUG: Enable debug mode
    
    Returns:
        Dictionary of configuration overrides
    """
    overrides = {}
    
    # Thresholds
    if "TBEVAL_COV_LINE_THRESHOLD" in os.environ:
        overrides["line_threshold"] = float(os.environ["TBEVAL_COV_LINE_THRESHOLD"])
    
    if "TBEVAL_COV_BRANCH_THRESHOLD" in os.environ:
        overrides["branch_threshold"] = float(os.environ["TBEVAL_COV_BRANCH_THRESHOLD"])
    
    if "TBEVAL_COV_TOGGLE_THRESHOLD" in os.environ:
        overrides["toggle_threshold"] = float(os.environ["TBEVAL_COV_TOGGLE_THRESHOLD"])
    
    # Debug mode
    if "TBEVAL_COV_DEBUG" in os.environ:
        overrides["debug"] = os.environ["TBEVAL_COV_DEBUG"].lower() in ["1", "true", "yes"]
    
    # Output directory
    if "TBEVAL_COV_OUTPUT" in os.environ:
        overrides["output_dir"] = os.environ["TBEVAL_COV_OUTPUT"]
    
    return overrides
