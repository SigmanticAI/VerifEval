"""
Configuration management for Step 7: Scoring & Export

This module handles:
- Scoring weights for Tier 1 (open-source) and Tier 2 (professional)
- Grade thresholds and pass/fail criteria
- Export format configuration (JSON, HTML, JUnit, CSV, PDF)
- Questa license detection settings
- Integration with .tbeval.yaml

Configuration Priority (highest to lowest):
1. CLI arguments
2. Environment variables
3. .tbeval.yaml scoring section
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

from .models import ScoringTier, ComponentType


# =============================================================================
# SCORING WEIGHT CONFIGURATIONS
# =============================================================================

@dataclass
class Tier1Weights:
    """
    Scoring weights for Tier 1 (Open Source - Verilator only)
    
    Components:
    - structural_coverage: Line/branch/toggle from Verilator (50%)
    - test_pass_rate: Test execution pass/fail ratio (20%)
    - code_quality: Linting and style from Step 2 (15%)
    - test_efficiency: Runtime and memory optimization (10%)
    - behavioral_accuracy: Heuristic assertion coverage (5%)
    
    Attributes:
        structural_coverage: Weight for structural coverage (0.50)
        test_pass_rate: Weight for test pass rate (0.20)
        code_quality: Weight for code quality (0.15)
        test_efficiency: Weight for test efficiency (0.10)
        behavioral_accuracy: Weight for behavioral accuracy (0.05)
    """
    structural_coverage: float = 0.50
    test_pass_rate: float = 0.20
    code_quality: float = 0.15
    test_efficiency: float = 0.10
    behavioral_accuracy: float = 0.05
    
    def __post_init__(self):
        """Validate weights sum to 1.0"""
        total = (self.structural_coverage + self.test_pass_rate + 
                self.code_quality + self.test_efficiency + self.behavioral_accuracy)
        
        if not (0.99 <= total <= 1.01):
            raise ValueError(
                f"Tier 1 weights must sum to 1.0, got {total:.4f}\n"
                f"  structural_coverage={self.structural_coverage}\n"
                f"  test_pass_rate={self.test_pass_rate}\n"
                f"  code_quality={self.code_quality}\n"
                f"  test_efficiency={self.test_efficiency}\n"
                f"  behavioral_accuracy={self.behavioral_accuracy}"
            )
        
        # Normalize to exactly 1.0 if close
        if total != 1.0:
            factor = 1.0 / total
            self.structural_coverage *= factor
            self.test_pass_rate *= factor
            self.code_quality *= factor
            self.test_efficiency *= factor
            self.behavioral_accuracy *= factor
    
    def to_dict(self) -> Dict[str, float]:
        """Convert to dictionary"""
        return {
            "structural_coverage": self.structural_coverage,
            "test_pass_rate": self.test_pass_rate,
            "code_quality": self.code_quality,
            "test_efficiency": self.test_efficiency,
            "behavioral_accuracy": self.behavioral_accuracy,
        }
    
    def get_weight(self, component: ComponentType) -> float:
        """Get weight for a specific component"""
        mapping = {
            ComponentType.STRUCTURAL_COVERAGE: self.structural_coverage,
            ComponentType.TEST_PASS_RATE: self.test_pass_rate,
            ComponentType.CODE_QUALITY: self.code_quality,
            ComponentType.TEST_EFFICIENCY: self.test_efficiency,
            ComponentType.BEHAVIORAL_ACCURACY: self.behavioral_accuracy,
        }
        return mapping.get(component, 0.0)


@dataclass
class Tier2Weights:
    """
    Scoring weights for Tier 2 (Professional - Questa available)
    
    Components:
    - structural_coverage: Line/branch/toggle (25%)
    - functional_coverage: SystemVerilog covergroups (25%)
    - assertion_coverage: SVA property verification (15%)
    - uvm_conformance: UVM methodology compliance (10%)
    - multiseed_stability: Regression stability across seeds (10%)
    - code_quality: Linting and style (10%)
    - test_efficiency: Runtime optimization (5%)
    
    Attributes:
        structural_coverage: Weight for structural coverage (0.25)
        functional_coverage: Weight for functional coverage (0.25)
        assertion_coverage: Weight for assertion coverage (0.15)
        uvm_conformance: Weight for UVM conformance (0.10)
        multiseed_stability: Weight for multiseed stability (0.10)
        code_quality: Weight for code quality (0.10)
        test_efficiency: Weight for test efficiency (0.05)
    """
    structural_coverage: float = 0.25
    functional_coverage: float = 0.25
    assertion_coverage: float = 0.15
    uvm_conformance: float = 0.10
    multiseed_stability: float = 0.10
    code_quality: float = 0.10
    test_efficiency: float = 0.05
    
    def __post_init__(self):
        """Validate weights sum to 1.0"""
        total = (self.structural_coverage + self.functional_coverage + 
                self.assertion_coverage + self.uvm_conformance +
                self.multiseed_stability + self.code_quality + self.test_efficiency)
        
        if not (0.99 <= total <= 1.01):
            raise ValueError(
                f"Tier 2 weights must sum to 1.0, got {total:.4f}"
            )
        
        # Normalize to exactly 1.0 if close
        if total != 1.0:
            factor = 1.0 / total
            self.structural_coverage *= factor
            self.functional_coverage *= factor
            self.assertion_coverage *= factor
            self.uvm_conformance *= factor
            self.multiseed_stability *= factor
            self.code_quality *= factor
            self.test_efficiency *= factor
    
    def to_dict(self) -> Dict[str, float]:
        """Convert to dictionary"""
        return {
            "structural_coverage": self.structural_coverage,
            "functional_coverage": self.functional_coverage,
            "assertion_coverage": self.assertion_coverage,
            "uvm_conformance": self.uvm_conformance,
            "multiseed_stability": self.multiseed_stability,
            "code_quality": self.code_quality,
            "test_efficiency": self.test_efficiency,
        }
    
    def get_weight(self, component: ComponentType) -> float:
        """Get weight for a specific component"""
        mapping = {
            ComponentType.STRUCTURAL_COVERAGE: self.structural_coverage,
            ComponentType.FUNCTIONAL_COVERAGE: self.functional_coverage,
            ComponentType.ASSERTION_COVERAGE: self.assertion_coverage,
            ComponentType.UVM_CONFORMANCE: self.uvm_conformance,
            ComponentType.MULTISEED_STABILITY: self.multiseed_stability,
            ComponentType.CODE_QUALITY: self.code_quality,
            ComponentType.TEST_EFFICIENCY: self.test_efficiency,
        }
        return mapping.get(component, 0.0)


# =============================================================================
# GRADE THRESHOLD CONFIGURATION
# =============================================================================

@dataclass
class GradeThresholds:
    """
    Grade thresholds for scoring
    
    Defines minimum percentages for each letter grade.
    
    Attributes:
        grade_a: Minimum percentage for A (90.0%)
        grade_b: Minimum percentage for B (80.0%)
        grade_c: Minimum percentage for C (70.0%)
        grade_d: Minimum percentage for D (60.0%)
        passing_grade: Minimum grade to pass (C = 70.0%)
    """
    grade_a: float = 90.0
    grade_b: float = 80.0
    grade_c: float = 70.0
    grade_d: float = 60.0
    passing_grade: str = "C"
    
    def __post_init__(self):
        """Validate thresholds are in descending order"""
        if not (self.grade_a > self.grade_b > self.grade_c > self.grade_d >= 0.0):
            raise ValueError(
                f"Grade thresholds must be in descending order: "
                f"A({self.grade_a}) > B({self.grade_b}) > C({self.grade_c}) > D({self.grade_d})"
            )
        
        if self.passing_grade not in ["A", "B", "C", "D"]:
            raise ValueError(f"Passing grade must be A, B, C, or D, got {self.passing_grade}")
    
    @property
    def passing_percentage(self) -> float:
        """Get minimum percentage to pass"""
        return {
            "A": self.grade_a,
            "B": self.grade_b,
            "C": self.grade_c,
            "D": self.grade_d,
        }[self.passing_grade]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "A": self.grade_a,
            "B": self.grade_b,
            "C": self.grade_c,
            "D": self.grade_d,
            "passing_grade": self.passing_grade,
            "passing_percentage": self.passing_percentage,
        }


# =============================================================================
# EXPORT CONFIGURATION
# =============================================================================

@dataclass
class ExportConfig:
    """
    Configuration for report export formats
    
    Controls which output formats are generated.
    
    Attributes:
        output_dir: Output directory for reports
        generate_json: Generate JSON report (always True - required)
        generate_html: Generate HTML dashboard
        generate_junit: Generate JUnit XML for CI/CD
        generate_csv: Generate CSV for spreadsheet analysis
        generate_pdf: Generate PDF report (requires additional deps)
        json_indent: JSON indentation level
        html_template: Custom HTML template path
    """
    output_dir: Path = Path(".tbeval/score")
    
    # Output formats
    generate_json: bool = True      # Required
    generate_html: bool = True
    generate_junit: bool = True
    generate_csv: bool = False
    generate_pdf: bool = False
    
    # Format options
    json_indent: int = 2
    html_template: Optional[Path] = None
    
    def __post_init__(self):
        """Validate export configuration"""
        # JSON is mandatory
        if not self.generate_json:
            warnings.warn("JSON export is mandatory, forcing generate_json=True")
            self.generate_json = True
        
        # Ensure output_dir is Path
        if isinstance(self.output_dir, str):
            self.output_dir = Path(self.output_dir)
        
        # Validate template path if provided
        if self.html_template and not Path(self.html_template).exists():
            warnings.warn(f"HTML template not found: {self.html_template}")
            self.html_template = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "output_dir": str(self.output_dir),
            "formats": {
                "json": self.generate_json,
                "html": self.generate_html,
                "junit": self.generate_junit,
                "csv": self.generate_csv,
                "pdf": self.generate_pdf,
            },
            "options": {
                "json_indent": self.json_indent,
                "html_template": str(self.html_template) if self.html_template else None,
            },
        }


# =============================================================================
# QUESTA CONFIGURATION
# =============================================================================

@dataclass
class QuestaConfig:
    """
    Configuration for Questa integration
    
    Controls Questa license detection and feature usage.
    
    Attributes:
        auto_detect: Auto-detect Questa availability
        require_license: Fail if Questa not available (for Tier 2 enforcement)
        vcover_path: Path to vcover tool
        qverify_path: Path to qverify tool
        ucdb_merge: Enable UCDB merging for multi-seed runs
        functional_coverage: Enable functional coverage analysis
        assertion_coverage: Enable assertion coverage analysis
        uvm_analysis: Enable UVM conformance analysis
    """
    auto_detect: bool = True
    require_license: bool = False
    
    # Tool paths (auto-detect if None)
    vcover_path: Optional[Path] = None
    qverify_path: Optional[Path] = None
    
    # Feature flags
    ucdb_merge: bool = True
    functional_coverage: bool = True
    assertion_coverage: bool = True
    uvm_analysis: bool = True
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "auto_detect": self.auto_detect,
            "require_license": self.require_license,
            "tools": {
                "vcover": str(self.vcover_path) if self.vcover_path else None,
                "qverify": str(self.qverify_path) if self.qverify_path else None,
            },
            "features": {
                "ucdb_merge": self.ucdb_merge,
                "functional_coverage": self.functional_coverage,
                "assertion_coverage": self.assertion_coverage,
                "uvm_analysis": self.uvm_analysis,
            },
        }


# =============================================================================
# RECOMMENDATION CONFIGURATION
# =============================================================================

@dataclass
class RecommendationConfig:
    """
    Configuration for generating recommendations
    
    Controls what recommendations are generated in final report.
    
    Attributes:
        generate_improvements: Generate actionable improvements
        generate_recommendations: Generate general recommendations
        max_improvements: Maximum number of improvements to list
        min_impact: Minimum impact threshold for improvements
        include_references: Include external reference links
    """
    generate_improvements: bool = True
    generate_recommendations: bool = True
    max_improvements: int = 10
    min_impact: float = 0.05  # 5% minimum score impact
    include_references: bool = True
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return asdict(self)


# =============================================================================
# MAIN CONFIGURATION
# =============================================================================

@dataclass
class ScoreCalculationConfig:
    """
    Main configuration for Step 7 scoring
    
    This is the primary configuration class used throughout the scoring
    pipeline.
    
    Attributes:
        submission_dir: Root submission directory
        coverage_report_path: Path to coverage_report.json from Step 5
        test_report_path: Path to test_report.json from Step 4
        quality_report_path: Path to quality_report.json from Step 2
        tier1_weights: Tier 1 scoring weights
        tier2_weights: Tier 2 scoring weights
        grade_thresholds: Grade thresholds
        export_config: Export configuration
        questa_config: Questa configuration
        recommendation_config: Recommendation configuration
        auto_detect_tier: Auto-detect tier based on Questa availability
        force_tier: Force specific tier (overrides auto-detect)
        fail_on_threshold: Fail if passing grade not achieved
        debug_mode: Enable debug logging
    """
    # Input paths
    submission_dir: Path = Path(".")
    coverage_report_path: Optional[Path] = None
    test_report_path: Optional[Path] = None
    quality_report_path: Optional[Path] = None
    
    # Scoring configuration
    tier1_weights: Tier1Weights = field(default_factory=Tier1Weights)
    tier2_weights: Tier2Weights = field(default_factory=Tier2Weights)
    grade_thresholds: GradeThresholds = field(default_factory=GradeThresholds)
    
    # Sub-configurations
    export_config: ExportConfig = field(default_factory=ExportConfig)
    questa_config: QuestaConfig = field(default_factory=QuestaConfig)
    recommendation_config: RecommendationConfig = field(default_factory=RecommendationConfig)
    
    # Execution control
    auto_detect_tier: bool = True
    force_tier: Optional[ScoringTier] = None
    fail_on_threshold: bool = False
    debug_mode: bool = False
    
    def __post_init__(self):
        """Validate and normalize paths"""
        # Convert strings to Path objects
        if isinstance(self.submission_dir, str):
            self.submission_dir = Path(self.submission_dir)
        
        if self.coverage_report_path and isinstance(self.coverage_report_path, str):
            self.coverage_report_path = Path(self.coverage_report_path)
        
        if self.test_report_path and isinstance(self.test_report_path, str):
            self.test_report_path = Path(self.test_report_path)
        
        if self.quality_report_path and isinstance(self.quality_report_path, str):
            self.quality_report_path = Path(self.quality_report_path)
        
        # Auto-detect report paths if not provided
        self._auto_detect_report_paths()
    
    def _auto_detect_report_paths(self) -> None:
        """Auto-detect report paths in submission directory"""
        if not self.coverage_report_path:
            default_path = self.submission_dir / ".tbeval" / "coverage" / "coverage_report.json"
            if default_path.exists():
                self.coverage_report_path = default_path
        
        if not self.test_report_path:
            default_path = self.submission_dir / ".tbeval" / "test_runs" / "test_report.json"
            if default_path.exists():
                self.test_report_path = default_path
        
        if not self.quality_report_path:
            default_path = self.submission_dir / ".tbeval" / "quality" / "quality_report.json"
            if default_path.exists():
                self.quality_report_path = default_path
    
    @classmethod
    def from_yaml(
        cls,
        yaml_path: Path,
        cli_overrides: Optional[Dict[str, Any]] = None
    ) -> 'ScoreCalculationConfig':
        """
        Load configuration from .tbeval.yaml
        
        Args:
            yaml_path: Path to .tbeval.yaml
            cli_overrides: CLI argument overrides (optional)
        
        Returns:
            ScoreCalculationConfig instance
        
        Example:
            >>> config = ScoreCalculationConfig.from_yaml(
            ...     Path(".tbeval.yaml"),
            ...     cli_overrides={"fail_on_threshold": True}
            ... )
        """
        yaml_path = Path(yaml_path)
        
        # Load YAML file
        if not yaml_path.exists():
            warnings.warn(f"Config file not found: {yaml_path}, using defaults")
            yaml_data = {}
        else:
            with open(yaml_path) as f:
                yaml_data = yaml.safe_load(f) or {}
        
        # Extract scoring section
        scoring_section = yaml_data.get("scoring", {})
        
        # Build configuration
        config = cls._build_from_sections(
            scoring_section,
            yaml_path.parent,
            cli_overrides or {}
        )
        
        return config
    
    @classmethod
    def _build_from_sections(
        cls,
        scoring_section: Dict[str, Any],
        submission_dir: Path,
        cli_overrides: Dict[str, Any]
    ) -> 'ScoreCalculationConfig':
        """Build configuration from YAML sections and CLI overrides"""
        
        # Tier 1 weights
        tier1_data = scoring_section.get("tier1_weights", {})
        tier1_weights = Tier1Weights(
            structural_coverage=tier1_data.get("structural_coverage", 0.50),
            test_pass_rate=tier1_data.get("test_pass_rate", 0.20),
            code_quality=tier1_data.get("code_quality", 0.15),
            test_efficiency=tier1_data.get("test_efficiency", 0.10),
            behavioral_accuracy=tier1_data.get("behavioral_accuracy", 0.05),
        )
        
        # Tier 2 weights
        tier2_data = scoring_section.get("tier2_weights", {})
        tier2_weights = Tier2Weights(
            structural_coverage=tier2_data.get("structural_coverage", 0.25),
            functional_coverage=tier2_data.get("functional_coverage", 0.25),
            assertion_coverage=tier2_data.get("assertion_coverage", 0.15),
            uvm_conformance=tier2_data.get("uvm_conformance", 0.10),
            multiseed_stability=tier2_data.get("multiseed_stability", 0.10),
            code_quality=tier2_data.get("code_quality", 0.10),
            test_efficiency=tier2_data.get("test_efficiency", 0.05),
        )
        
        # Grade thresholds
        threshold_data = scoring_section.get("grade_thresholds", {})
        grade_thresholds = GradeThresholds(
            grade_a=threshold_data.get("A", 90.0),
            grade_b=threshold_data.get("B", 80.0),
            grade_c=threshold_data.get("C", 70.0),
            grade_d=threshold_data.get("D", 60.0),
            passing_grade=threshold_data.get("passing_grade", "C"),
        )
        
        # Export configuration
        export_data = scoring_section.get("export", {})
        export_config = ExportConfig(
            output_dir=Path(cli_overrides.get("output_dir") or export_data.get("output_dir", ".tbeval/score")),
            generate_html=export_data.get("generate_html", True),
            generate_junit=export_data.get("generate_junit", True),
            generate_csv=export_data.get("generate_csv", False),
            generate_pdf=export_data.get("generate_pdf", False),
        )
        
        # Questa configuration
        questa_data = scoring_section.get("questa", {})
        questa_config = QuestaConfig(
            auto_detect=questa_data.get("auto_detect", True),
            require_license=questa_data.get("require_license", False),
            functional_coverage=questa_data.get("functional_coverage", True),
            assertion_coverage=questa_data.get("assertion_coverage", True),
            uvm_analysis=questa_data.get("uvm_analysis", True),
        )
        
        # Recommendation configuration
        rec_data = scoring_section.get("recommendations", {})
        recommendation_config = RecommendationConfig(
            generate_improvements=rec_data.get("generate_improvements", True),
            generate_recommendations=rec_data.get("generate_recommendations", True),
            max_improvements=rec_data.get("max_improvements", 10),
        )
        
        # Create config
        return cls(
            submission_dir=submission_dir,
            tier1_weights=tier1_weights,
            tier2_weights=tier2_weights,
            grade_thresholds=grade_thresholds,
            export_config=export_config,
            questa_config=questa_config,
            recommendation_config=recommendation_config,
            fail_on_threshold=cli_overrides.get("fail_on_threshold", False),
            debug_mode=cli_overrides.get("debug", False),
        )
    
    @classmethod
    def from_cli(
        cls,
        submission_dir: str = ".",
        config_file: Optional[str] = None,
        **kwargs
    ) -> 'ScoreCalculationConfig':
        """
        Create configuration from CLI arguments
        
        Args:
            submission_dir: Submission directory path
            config_file: Path to .tbeval.yaml (optional, auto-detect)
            **kwargs: Additional CLI overrides
        
        Returns:
            ScoreCalculationConfig instance
        
        Example:
            >>> config = ScoreCalculationConfig.from_cli(
            ...     submission_dir="./student_submission",
            ...     fail_on_threshold=True
            ... )
        """
        submission_path = Path(submission_dir)
        
        # Auto-detect config file if not provided
        if config_file is None:
            for name in [".tbeval.yaml", ".tbeval.yml", "tbeval.yaml"]:
                config_path = submission_path / name
                if config_path.exists():
                    break
            else:
                config_path = Path(".tbeval.yaml")
        else:
            config_path = Path(config_file)
        
        # Load from YAML with CLI overrides
        return cls.from_yaml(config_path, cli_overrides=kwargs)
    
    def get_weights(self, tier: ScoringTier) -> Dict[str, float]:
        """
        Get weights for specified tier
        
        Args:
            tier: Scoring tier
        
        Returns:
            Dictionary of component weights
        """
        if tier == ScoringTier.OPEN_SOURCE:
            return self.tier1_weights.to_dict()
        else:
            return self.tier2_weights.to_dict()
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Serialize configuration to dictionary
        
        Returns:
            Dictionary representation
        """
        return {
            "paths": {
                "submission_dir": str(self.submission_dir),
                "coverage_report": str(self.coverage_report_path) if self.coverage_report_path else None,
                "test_report": str(self.test_report_path) if self.test_report_path else None,
                "quality_report": str(self.quality_report_path) if self.quality_report_path else None,
            },
            "tier1_weights": self.tier1_weights.to_dict(),
            "tier2_weights": self.tier2_weights.to_dict(),
            "grade_thresholds": self.grade_thresholds.to_dict(),
            "export": self.export_config.to_dict(),
            "questa": self.questa_config.to_dict(),
            "recommendations": self.recommendation_config.to_dict(),
            "execution": {
                "auto_detect_tier": self.auto_detect_tier,
                "force_tier": self.force_tier.value if self.force_tier else None,
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
            "scoring": {
                "tier1_weights": self.tier1_weights.to_dict(),
                "tier2_weights": self.tier2_weights.to_dict(),
                "grade_thresholds": self.grade_thresholds.to_dict(),
                "export": self.export_config.to_dict(),
                "questa": self.questa_config.to_dict(),
                "recommendations": self.recommendation_config.to_dict(),
            }
        }
        
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(path, 'w') as f:
            yaml.dump(data, f, default_flow_style=False, sort_keys=False)
    
    def validate(self) -> List[str]:
        """
        Validate configuration
        
        Returns:
            List of validation warnings/errors
        """
        issues = []
        
        # Check report paths exist (warnings only)
        if self.coverage_report_path and not self.coverage_report_path.exists():
            issues.append(f"Coverage report not found: {self.coverage_report_path}")
        
        if self.test_report_path and not self.test_report_path.exists():
            issues.append(f"Test report not found: {self.test_report_path}")
        
        if self.quality_report_path and not self.quality_report_path.exists():
            issues.append(f"Quality report not found: {self.quality_report_path}")
        
        # Check if at least one report is available
        if not any([
            self.coverage_report_path and self.coverage_report_path.exists(),
            self.test_report_path and self.test_report_path.exists(),
        ]):
            issues.append("No input reports found (need at least coverage or test report)")
        
        return issues


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def create_default_config_file(output_path: Path) -> None:
    """
    Create a default .tbeval.yaml with scoring section
    
    Args:
        output_path: Where to write the config file
    
    Example:
        >>> create_default_config_file(Path(".tbeval.yaml"))
    """
    default_config = {
        "scoring": {
            "tier1_weights": {
                "structural_coverage": 0.50,
                "test_pass_rate": 0.20,
                "code_quality": 0.15,
                "test_efficiency": 0.10,
                "behavioral_accuracy": 0.05,
            },
            
            "tier2_weights": {
                "structural_coverage": 0.25,
                "functional_coverage": 0.25,
                "assertion_coverage": 0.15,
                "uvm_conformance": 0.10,
                "multiseed_stability": 0.10,
                "code_quality": 0.10,
                "test_efficiency": 0.05,
            },
            
            "grade_thresholds": {
                "A": 90.0,
                "B": 80.0,
                "C": 70.0,
                "D": 60.0,
                "passing_grade": "C",
            },
            
            "export": {
                "output_dir": ".tbeval/score",
                "generate_html": True,
                "generate_junit": True,
                "generate_csv": False,
                "generate_pdf": False,
            },
            
            "questa": {
                "auto_detect": True,
                "require_license": False,
                "functional_coverage": True,
                "assertion_coverage": True,
                "uvm_analysis": True,
            },
            
            "recommendations": {
                "generate_improvements": True,
                "generate_recommendations": True,
                "max_improvements": 10,
            },
        }
    }
    
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_path, 'w') as f:
        yaml.dump(default_config, f, default_flow_style=False, sort_keys=False)
    
    print(f"Created default scoring configuration: {output_path}")


def load_config_from_env() -> Dict[str, Any]:
    """
    Load configuration overrides from environment variables
    
    Environment variables:
        TBEVAL_SCORE_TIER: Force scoring tier (open_source or professional)
        TBEVAL_SCORE_FAIL_ON_THRESHOLD: Fail if passing grade not met
        TBEVAL_SCORE_OUTPUT: Output directory
        TBEVAL_SCORE_DEBUG: Enable debug mode
    
    Returns:
        Dictionary of configuration overrides
    """
    overrides = {}
    
    # Tier override
    if "TBEVAL_SCORE_TIER" in os.environ:
        tier_str = os.environ["TBEVAL_SCORE_TIER"].lower()
        if tier_str in ["open_source", "professional"]:
            overrides["force_tier"] = ScoringTier(tier_str)
    
    # Fail on threshold
    if "TBEVAL_SCORE_FAIL_ON_THRESHOLD" in os.environ:
        overrides["fail_on_threshold"] = os.environ["TBEVAL_SCORE_FAIL_ON_THRESHOLD"].lower() in ["1", "true", "yes"]
    
    # Output directory
    if "TBEVAL_SCORE_OUTPUT" in os.environ:
        overrides["output_dir"] = os.environ["TBEVAL_SCORE_OUTPUT"]
    
    # Debug mode
    if "TBEVAL_SCORE_DEBUG" in os.environ:
        overrides["debug"] = os.environ["TBEVAL_SCORE_DEBUG"].lower() in ["1", "true", "yes"]
    
    return overrides


# =============================================================================
# EXAMPLE USAGE
# =============================================================================

if __name__ == "__main__":
    # Example: Create configuration from YAML
    config = ScoreCalculationConfig.from_yaml(Path(".tbeval.yaml"))
    
    print("Configuration loaded:")
    print(f"  Tier 1 weights: {config.tier1_weights.to_dict()}")
    print(f"  Tier 2 weights: {config.tier2_weights.to_dict()}")
    print(f"  Grade thresholds: {config.grade_thresholds.to_dict()}")
    print(f"  Export formats: {config.export_config.to_dict()}")
    
    # Validate
    issues = config.validate()
    if issues:
        print("\nValidation issues:")
        for issue in issues:
            print(f"  - {issue}")
    
    # Example: Create default config file
    # create_default_config_file(Path(".tbeval.yaml"))
