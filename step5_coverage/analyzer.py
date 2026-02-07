"""
Main coverage analyzer orchestrator

This is the primary entry point for Step 5 coverage analysis.
It orchestrates the entire pipeline:

1. Load test_report.json from Step 4
2. Load build_manifest.json from Step 3
3. Detect and parse coverage files
4. Calculate coverage metrics
5. Merge per-test coverage (Q13 advanced tracking)
6. Generate reports (coverage_report.json)
7. Validate against thresholds

Usage:
    >>> from step5_coverage import CoverageAnalyzer
    >>> analyzer = CoverageAnalyzer.from_config_file(".tbeval.yaml")
    >>> report = analyzer.analyze()
    >>> print(f"Overall coverage: {report.structural_coverage.weighted_score:.2%}")

Author: TB Eval Team
Version: 0.1.0
"""

import json
import time
from pathlib import Path
from typing import List, Dict, Optional, Tuple
from datetime import datetime
import logging

from .models import (
    CoverageReport,
    CoverageFormat,
    ModuleCoverage,
    StructuralCoverageMetrics,
    HierarchicalCoverage,
    MutationTestingData,
    MutationTarget,
)
from .config import CoverageAnalysisConfig
from .parsers import (
    FormatDetector,
    BaseParser,
    VerilatorParser,
    LCOVParser,
    ParseResult,
)
from .metrics import (
    CoverageCalculator,
    CoverageMerger,
)


# =============================================================================
# ANALYSIS RESULT
# =============================================================================

class AnalysisResult:
    """
    Result of coverage analysis
    
    Contains both the final report and diagnostic information.
    
    Attributes:
        success: Whether analysis completed successfully
        report: Generated coverage report (None if failed)
        errors: List of error messages
        warnings: List of warning messages
        analysis_time_ms: Time taken for analysis
    """
    
    def __init__(
        self,
        success: bool = True,
        report: Optional[CoverageReport] = None,
        errors: Optional[List[str]] = None,
        warnings: Optional[List[str]] = None
    ):
        self.success = success
        self.report = report
        self.errors = errors or []
        self.warnings = warnings or []
        self.analysis_time_ms = 0.0
    
    def add_error(self, message: str) -> None:
        """Add an error message"""
        self.errors.append(message)
        self.success = False
    
    def add_warning(self, message: str) -> None:
        """Add a warning message"""
        self.warnings.append(message)
    
    @property
    def has_warnings(self) -> bool:
        """Check if there are warnings"""
        return len(self.warnings) > 0
    
    @property
    def has_errors(self) -> bool:
        """Check if there are errors"""
        return len(self.errors) > 0


# =============================================================================
# MAIN ANALYZER
# =============================================================================

class CoverageAnalyzer:
    """
    Main coverage analysis orchestrator
    
    This class coordinates the entire Step 5 pipeline:
    - Loading test results and manifests
    - Parsing coverage files
    - Calculating metrics
    - Generating reports
    
    The analyzer implements the Q&A requirements:
    - Q1.3: Loads both test_report.json and build_manifest.json
    - Q4.1: Generates hierarchical coverage
    - Q4.2: Calculates mandatory metrics for Step 7
    - Q5.1: Generates mutation testing data for Step 6
    - Q5.2: Provides agent-friendly output
    - Q6.1/Q6.2: Merges coverage
    - Q13: Advanced per-test tracking
    """
    
    def __init__(self, config: CoverageAnalysisConfig):
        """
        Initialize analyzer
        
        Args:
            config: Coverage analysis configuration
        """
        self.config = config
        self.logger = logging.getLogger(__name__)
        
        # Initialize components
        self.detector = FormatDetector(config=config.parsers)
        self.calculator = CoverageCalculator(
            weights=config.weights,
            thresholds=config.thresholds
        )
        self.merger = CoverageMerger(calculator=self.calculator)
        
        # State
        self.test_report_data: Optional[Dict] = None
        self.build_manifest_data: Optional[Dict] = None
        self.coverage_files: List[Path] = []
        self.parsed_coverages: Dict[str, ModuleCoverage] = {}
    
    # =========================================================================
    # FACTORY METHODS
    # =========================================================================
    
    @classmethod
    def from_config_file(
        cls,
        config_path: Path,
        test_report_path: Optional[Path] = None,
        build_manifest_path: Optional[Path] = None,
        **overrides
    ) -> 'CoverageAnalyzer':
        """
        Create analyzer from configuration file
        
        Args:
            config_path: Path to .tbeval.yaml
            test_report_path: Path to test_report.json (optional, auto-detect)
            build_manifest_path: Path to build_manifest.json (optional, auto-detect)
            **overrides: Configuration overrides
        
        Returns:
            CoverageAnalyzer instance
        """
        # Auto-detect paths if not provided
        config_dir = config_path.parent
        
        if test_report_path is None:
            test_report_path = config_dir / ".tbeval" / "test_runs" / "test_report.json"
            if not test_report_path.exists():
                test_report_path = config_dir / "test_report.json"
        
        if build_manifest_path is None:
            build_manifest_path = config_dir / ".tbeval" / "build_manifest.json"
            if not build_manifest_path.exists():
                build_manifest_path = config_dir / "build_manifest.json"
        
        config = CoverageAnalysisConfig.from_yaml(
            config_path,
            test_report_path,
            build_manifest_path,
            cli_overrides=overrides
        )
        
        return cls(config)
    
    @classmethod
    def from_test_report(
        cls,
        test_report_path: Path,
        build_manifest_path: Optional[Path] = None
    ) -> 'CoverageAnalyzer':
        """
        Create analyzer from test report
        
        Args:
            test_report_path: Path to test_report.json
            build_manifest_path: Path to build_manifest.json (optional)
        
        Returns:
            CoverageAnalyzer instance
        """
        if build_manifest_path is None:
            # Try to find build_manifest.json near test_report
            build_manifest_path = test_report_path.parent / "build_manifest.json"
            if not build_manifest_path.exists():
                build_manifest_path = test_report_path.parent.parent / "build_manifest.json"
        
        config = CoverageAnalysisConfig(
            test_report_path=test_report_path,
            build_manifest_path=build_manifest_path,
            submission_dir=test_report_path.parent
        )
        
        return cls(config)
    
    # =========================================================================
    # MAIN ANALYSIS METHOD
    # =========================================================================
    
    def analyze(self) -> AnalysisResult:
        """
        Run complete coverage analysis pipeline
        
        Returns:
            AnalysisResult with coverage report
        """
        start_time = time.time()
        result = AnalysisResult()
        
        try:
            self.logger.info("Starting coverage analysis")
            
            # Step 1: Load test report (Q1.3)
            if not self._load_test_report(result):
                return result
            
            # Step 2: Load build manifest (Q1.3)
            if not self._load_build_manifest(result):
                return result
            
            # Step 3: Find coverage files
            if not self._find_coverage_files(result):
                return result
            
            # Step 4: Parse coverage files
            if not self._parse_coverage_files(result):
                return result
            
            # Step 5: Calculate metrics and merge
            if not self._calculate_and_merge(result):
                return result
            
            # Step 6: Generate report
            if not self._generate_report(result):
                return result
            
            # Step 7: Validate thresholds
            self._validate_thresholds(result)
            
            result.analysis_time_ms = (time.time() - start_time) * 1000.0
            self.logger.info(f"Analysis completed in {result.analysis_time_ms:.1f}ms")
            
        except Exception as e:
            result.add_error(f"Unexpected error during analysis: {e}")
            self.logger.exception("Analysis failed with exception")
        
        return result
    
    # =========================================================================
    # PIPELINE STEPS
    # =========================================================================
    
    def _load_test_report(self, result: AnalysisResult) -> bool:
        """
        Load test_report.json from Step 4 (Q1.3)
        
        Args:
            result: AnalysisResult to populate
        
        Returns:
            True if successful
        """
        try:
            if not self.config.test_report_path.exists():
                result.add_error(f"Test report not found: {self.config.test_report_path}")
                return False
            
            with open(self.config.test_report_path) as f:
                self.test_report_data = json.load(f)
            
            # Validate schema
            if "schema_version" not in self.test_report_data:
                result.add_warning("Test report missing schema_version")
            
            if "results" not in self.test_report_data:
                result.add_error("Test report missing 'results' field")
                return False
            
            self.logger.info(f"Loaded test report with {len(self.test_report_data['results'])} tests")
            return True
        
        except json.JSONDecodeError as e:
            result.add_error(f"Failed to parse test report JSON: {e}")
            return False
        except Exception as e:
            result.add_error(f"Failed to load test report: {e}")
            return False
    
    def _load_build_manifest(self, result: AnalysisResult) -> bool:
        """
        Load build_manifest.json from Step 3 (Q1.3)
        
        Args:
            result: AnalysisResult to populate
        
        Returns:
            True if successful
        """
        try:
            if not self.config.build_manifest_path.exists():
                result.add_error(f"Build manifest not found: {self.config.build_manifest_path}")
                return False
            
            with open(self.config.build_manifest_path) as f:
                self.build_manifest_data = json.load(f)
            
            # Validate schema
            if "schema_version" not in self.build_manifest_data:
                result.add_warning("Build manifest missing schema_version")
            
            self.logger.info("Loaded build manifest")
            return True
        
        except json.JSONDecodeError as e:
            result.add_error(f"Failed to parse build manifest JSON: {e}")
            return False
        except Exception as e:
            result.add_error(f"Failed to load build manifest: {e}")
            return False
    
    def _find_coverage_files(self, result: AnalysisResult) -> bool:
        """
        Find coverage files from test report
        
        Coverage files are listed in test_report.json under:
        - results[].artifacts.coverage_file (per-test)
        - coverage.merged_file (merged)
        
        Args:
            result: AnalysisResult to populate
        
        Returns:
            True if successful
        """
        coverage_files = []
        
        # Check for per-test coverage files
        for test_result in self.test_report_data.get("results", []):
            artifacts = test_result.get("artifacts", {})
            coverage_file = artifacts.get("coverage_file")
            
            if coverage_file:
                file_path = Path(coverage_file)
                if file_path.exists():
                    coverage_files.append(file_path)
                else:
                    result.add_warning(f"Coverage file not found: {coverage_file}")
        
        # Check for merged coverage file
        coverage_section = self.test_report_data.get("coverage", {})
        merged_file = coverage_section.get("merged_file")
        
        if merged_file:
            file_path = Path(merged_file)
            if file_path.exists():
                coverage_files.append(file_path)
            else:
                result.add_warning(f"Merged coverage file not found: {merged_file}")
        
        # Remove duplicates
        self.coverage_files = list(set(coverage_files))
        
        if not self.coverage_files:
            result.add_error("No coverage files found in test report")
            return False
        
        self.logger.info(f"Found {len(self.coverage_files)} coverage files")
        return True
    
    def _parse_coverage_files(self, result: AnalysisResult) -> bool:
        """
        Parse all coverage files
        
        Args:
            result: AnalysisResult to populate
        
        Returns:
            True if at least one file was parsed successfully
        """
        successful = 0
        failed = 0
        
        for coverage_file in self.coverage_files:
            # Detect format
            detection_result = self.detector.detect(coverage_file)
            
            if not detection_result.success:
                result.add_warning(f"Could not detect format: {coverage_file}")
                failed += 1
                continue
            
            # Parse file
            parser = detection_result.parser
            parse_result = parser.parse_file(coverage_file)
            
            if not parse_result.success:
                result.add_warning(
                    f"Failed to parse {coverage_file}: {parse_result.errors}"
                )
                failed += 1
                continue
            
            # Store parsed coverage
            # Try to match to test name
            test_name = self._extract_test_name_from_path(coverage_file)
            self.parsed_coverages[test_name] = parse_result.coverage
            
            successful += 1
            
            # Add parse warnings to result
            if parse_result.has_warnings:
                for warning in parse_result.warnings:
                    result.add_warning(f"{coverage_file}: {warning}")
        
        self.logger.info(f"Parsed {successful}/{len(self.coverage_files)} coverage files")
        
        if successful == 0:
            result.add_error("No coverage files were successfully parsed")
            return False
        
        if failed > 0:
            result.add_warning(f"Failed to parse {failed} coverage files")
        
        return True
    
    def _extract_test_name_from_path(self, file_path: Path) -> str:
        """
        Extract test name from coverage file path
        
        Args:
            file_path: Path to coverage file
        
        Returns:
            Test name (derived from filename)
        """
        # Common patterns:
        # coverage_test_basic.dat -> test_basic
        # coverage_test_overflow.dat -> test_overflow
        # test_adder.info -> test_adder
        
        name = file_path.stem  # Remove extension
        
        # Remove "coverage_" prefix if present
        if name.startswith("coverage_"):
            name = name[9:]  # len("coverage_") = 9
        
        return name
    
    def _calculate_and_merge(self, result: AnalysisResult) -> bool:
        """
        Calculate metrics and merge coverage
        
        Args:
            result: AnalysisResult to populate
        
        Returns:
            True if successful
        """
        try:
            # Get test durations from test report
            test_durations = self._extract_test_durations()
            
            # Merge with tracking (Q13 - advanced tracking)
            if self.config.merging.per_test_analysis and len(self.parsed_coverages) > 1:
                self.logger.info("Merging coverage with per-test tracking")
                self.hierarchical = self.merger.merge_with_tracking(
                    self.parsed_coverages,
                    test_durations,
                    essential_threshold=self.config.merging.essential_threshold,
                    redundant_threshold=self.config.merging.redundant_threshold
                )
            else:
                # Simple merge
                self.logger.info("Merging coverage (simple mode)")
                merged_module = self.merger.merge_simple(
                    list(self.parsed_coverages.values())
                )
                
                # Create hierarchical structure with just merged data
                self.hierarchical = HierarchicalCoverage()
                self.hierarchical.merged = self.calculator.calculate_metrics(merged_module)
            
            return True
        
        except Exception as e:
            result.add_error(f"Failed to calculate/merge coverage: {e}")
            return False
    
    def _extract_test_durations(self) -> Dict[str, float]:
        """
        Extract test durations from test report
        
        Returns:
            Dictionary mapping test name to duration in ms
        """
        durations = {}
        
        for test_result in self.test_report_data.get("results", []):
            test_name = test_result.get("name", "unknown")
            duration_ms = test_result.get("duration_ms", 1000.0)
            durations[test_name] = duration_ms
        
        return durations
    
    def _generate_report(self, result: AnalysisResult) -> bool:
        """
        Generate coverage report (Q1.2 - new coverage_report.json)
        
        Args:
            result: AnalysisResult to populate
        
        Returns:
            True if successful
        """
        try:
            # Create report
            report = CoverageReport(
                schema_version="1.0",
                generated_at=datetime.now().isoformat(),
                framework_version="0.1.0",
                source_test_report=str(self.config.test_report_path),
                source_build_manifest=str(self.config.build_manifest_path),
            )
            
            # Detect primary coverage format
            if self.coverage_files:
                first_file = self.coverage_files[0]
                detection = self.detector.detect(first_file)
                if detection.success:
                    report.coverage_format = detection.format_name
            
            # Add coverage file list
            report.coverage_files = [str(f) for f in self.coverage_files]
            
            # Add structural coverage metrics (Q4.2 - mandatory for Step 7)
            report.structural_coverage = self.hierarchical.merged
            
            # Add hierarchical coverage (Q4.1)
            if self.config.merging.per_test_analysis:
                report.hierarchical = self.hierarchical
            
            # Add module breakdown
            if self.parsed_coverages:
                # Use first parsed coverage for module details
                first_coverage = list(self.parsed_coverages.values())[0]
                report.modules = first_coverage.files  # Simplified
            
            # Generate mutation testing data (Q5.1 - for Step 6)
            if self.config.reporting.export_mutation_targets:
                report.mutation_data = self._generate_mutation_data()
            
            # Add metadata
            report.analysis_metadata = {
                "total_tests": len(self.parsed_coverages),
                "coverage_files_parsed": len(self.coverage_files),
                "analysis_time_ms": result.analysis_time_ms,
            }
            
            # Add tools used
            report.tools_used = self._get_tools_used()
            
            result.report = report
            return True
        
        except Exception as e:
            result.add_error(f"Failed to generate report: {e}")
            return False
    
    def _generate_mutation_data(self) -> MutationTestingData:
        """
        Generate mutation testing data for Step 6 (Q5.1)
        
        Returns:
            MutationTestingData with targets
        """
        mutation_data = MutationTestingData()
        
        # Get merged coverage
        metrics = self.hierarchical.merged
        
        # Identify uncovered lines
        for uncovered in metrics.line.uncovered_lines[:50]:
            target = MutationTarget(
                file_path=uncovered.get("file", "unknown"),
                line=uncovered.get("line", 0),
                reason="uncovered",
                priority="high",
                current_coverage=0.0
            )
            mutation_data.uncovered_lines.append(target)
        
        # Identify weakly covered branches
        for branch_info in metrics.branch.uncovered_branches[:50]:
            target = MutationTarget(
                file_path=branch_info.get("file", "unknown"),
                line=branch_info.get("line", 0),
                reason="weakly_covered_branch",
                priority="medium",
                current_coverage=0.5
            )
            mutation_data.weakly_covered_branches.append(target)
        
        # Identify untoggled signals
        for signal in metrics.toggle.untoggled_signals[:30]:
            target = MutationTarget(
                file_path="unknown",  # Signal location not tracked in current model
                line=0,
                reason="untoggled_signal",
                priority="low",
                current_coverage=0.0
            )
            target.suggested_mutations = ["toggle_inversion"]
            mutation_data.untoggled_signals.append(target)
        
        return mutation_data
    
    def _get_tools_used(self) -> List[str]:
        """
        Get list of tools used during analysis
        
        Returns:
            List of tool names
        """
        tools = []
        
        # Check which parsers were used
        for parser in self.detector.parsers:
            tool_path = parser._get_external_tool_path()
            if tool_path:
                tools.append(parser.__class__.__name__)
        
        return tools
    
    def _validate_thresholds(self, result: AnalysisResult) -> None:
        """
        Validate coverage against thresholds (Q7.1)
        
        Args:
            result: AnalysisResult to populate
        """
        if not result.report:
            return
        
        metrics = result.report.structural_coverage
        
        passed, violations = self.calculator.validate_metrics(metrics)
        
        result.report.thresholds_met = passed
        result.report.threshold_violations = violations
        
        if not passed:
            if self.config.fail_on_threshold:
                result.add_error("Coverage thresholds not met")
            else:
                for violation in violations:
                    result.add_warning(f"Threshold violation: {violation}")
    
    # =========================================================================
    # SAVE/EXPORT METHODS
    # =========================================================================
    
    def save_report(
        self,
        report: CoverageReport,
        output_path: Optional[Path] = None
    ) -> Path:
        """
        Save coverage report to file
        
        Args:
            report: CoverageReport to save
            output_path: Output path (optional, uses config if not provided)
        
        Returns:
            Path where report was saved
        """
        if output_path is None:
            output_dir = self.config.reporting.output_dir
            output_dir.mkdir(parents=True, exist_ok=True)
            output_path = output_dir / "coverage_report.json"
        
        report.save(output_path)
        self.logger.info(f"Saved coverage report to {output_path}")
        
        return output_path
    
    def generate_summary(
        self,
        report: CoverageReport,
        output_path: Optional[Path] = None
    ) -> str:
        """
        Generate human-readable summary
        
        Args:
            report: CoverageReport
            output_path: Optional path to save summary
        
        Returns:
            Summary text
        """
        summary = self.calculator.get_coverage_summary(report.structural_coverage)
        
        if output_path:
            output_path = Path(output_path)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_text(summary)
            self.logger.info(f"Saved summary to {output_path}")
        
        return summary
    
    def enrich_test_report(
        self,
        report: CoverageReport
    ) -> bool:
        """
        Enrich test_report.json with coverage data (Q1.2)
        
        Adds coverage summary to the test report.
        
        Args:
            report: CoverageReport with coverage data
        
        Returns:
            True if successful
        """
        try:
            # Add coverage section to test report
            self.test_report_data["coverage"] = report.to_summary_dict()
            
            # Save enriched test report
            enriched_path = self.config.test_report_path.parent / "enriched_test_report.json"
            with open(enriched_path, 'w') as f:
                json.dump(self.test_report_data, f, indent=2)
            
            self.logger.info(f"Enriched test report saved to {enriched_path}")
            return True
        
        except Exception as e:
            self.logger.error(f"Failed to enrich test report: {e}")
            return False
    
    # =========================================================================
    # DIAGNOSTIC METHODS
    # =========================================================================
    
    def get_diagnostics(self) -> Dict[str, any]:
        """
        Get diagnostic information about the analyzer state
        
        Returns:
            Dictionary with diagnostic information
        """
        return {
            "config": {
                "test_report": str(self.config.test_report_path),
                "build_manifest": str(self.config.build_manifest_path),
                "output_dir": str(self.config.reporting.output_dir),
            },
            "state": {
                "test_report_loaded": self.test_report_data is not None,
                "build_manifest_loaded": self.build_manifest_data is not None,
                "coverage_files_found": len(self.coverage_files),
                "coverages_parsed": len(self.parsed_coverages),
            },
            "parsers": {
                "available_parsers": len(self.detector.parsers),
                "available_formats": [f.value for f in self.detector.get_available_formats()],
            },
        }


# =============================================================================
# CONVENIENCE FUNCTIONS
# =============================================================================

def analyze_coverage(
    test_report_path: Path,
    build_manifest_path: Optional[Path] = None,
    config_path: Optional[Path] = None
) -> AnalysisResult:
    """
    Convenience function to run coverage analysis
    
    Args:
        test_report_path: Path to test_report.json
        build_manifest_path: Path to build_manifest.json (optional)
        config_path: Path to .tbeval.yaml (optional)
    
    Returns:
        AnalysisResult
    """
    if config_path and config_path.exists():
        analyzer = CoverageAnalyzer.from_config_file(
            config_path,
            test_report_path,
            build_manifest_path
        )
    else:
        analyzer = CoverageAnalyzer.from_test_report(
            test_report_path,
            build_manifest_path
        )
    
    return analyzer.analyze()


def quick_analyze(test_report_path: Path) -> Optional[CoverageReport]:
    """
    Quick analysis with defaults
    
    Args:
        test_report_path: Path to test_report.json
    
    Returns:
        CoverageReport if successful, None otherwise
    """
    result = analyze_coverage(test_report_path)
    
    if result.success:
        return result.report
    
    return None
