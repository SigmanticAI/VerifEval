"""
Main orchestrator for Step 7: Scoring & Export

This is the central integration layer that ties together:
- Tier detection (Questa license checking)
- Scoring (Tier 1 or Tier 2 scorer delegation)
- Export (JSON, HTML, JUnit, CSV, PDF)
- Validation (input report verification)
- Recommendation generation

TestbenchAnalyzer is the primary programmatic API for Step 7.
It can be used standalone or called from __main__.py CLI.

Data Flow:
    quality_report.json (Step 2) ──┐
    test_report.json (Step 4) ─────┼──→ TestbenchAnalyzer ──→ FinalReport ──→ Exporters
    coverage_report.json (Step 5) ─┘         │
                                             ├─ detect_tier()
                                             ├─ score()
                                             ├─ export()
                                             └─ run()  [full pipeline]

Usage:
    # Programmatic API
    from step7_score.analyzer import TestbenchAnalyzer
    from step7_score.config import ScoreCalculationConfig

    config = ScoreCalculationConfig.from_yaml(Path(".tbeval.yaml"))
    analyzer = TestbenchAnalyzer(config)
    report = analyzer.run(submission_id="student_123_fifo")

    # One-liner convenience
    from step7_score.analyzer import analyze
    report = analyze(Path("./submission"), submission_id="student_123_fifo")

Author: TB Eval Team
Version: 0.1.0
"""

import time
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional, Dict, List, Any

from .models import (
    ScoringTier,
    FinalReport,
    TierScore,
)
from .config import ScoreCalculationConfig
from .scorers.tier1_scorer import Tier1Scorer
from .scorers.tier2_scorer import Tier2Scorer
from .questa.license_checker import (
    check_questa_availability,
    QuestaCapabilities,
)
from .exporters.html_exporter import HTMLExporter
from .exporters.junit_exporter import JUnitExporter
from .exporters.csv_exporter import CSVExporter

logger = logging.getLogger(__name__)


# =============================================================================
# ANALYSIS RESULT
# =============================================================================

@dataclass
class AnalysisResult:
    """
    Complete result from an analysis run.

    Wraps the FinalReport together with operational metadata that is
    useful for callers but does not belong inside the report itself.

    Attributes:
        report: The generated FinalReport (always present on success).
        tier_used: Which scoring tier was actually used.
        tier_detection_reason: Human-readable reason for tier selection.
        exported_files: Mapping of format name to output Path.
        validation_warnings: Non-fatal warnings from input validation.
        wall_clock_ms: Total wall-clock time for the full run.
    """
    report: FinalReport
    tier_used: ScoringTier
    tier_detection_reason: str
    exported_files: Dict[str, Path] = field(default_factory=dict)
    validation_warnings: List[str] = field(default_factory=list)
    wall_clock_ms: float = 0.0

    def __str__(self) -> str:
        pct = self.report.score.percentage
        grade = self.report.score.grade.value
        status = "PASS" if self.report.score.pass_threshold else "FAIL"
        return (
            f"AnalysisResult({status} | {pct:.2f}% | Grade {grade} | "
            f"Tier={self.tier_used.value} | "
            f"exports={list(self.exported_files.keys())})"
        )


# =============================================================================
# MAIN ORCHESTRATOR
# =============================================================================

class TestbenchAnalyzer:
    """
    Main orchestrator for testbench evaluation scoring and export.

    This class is the **single entry-point** for the entire Step 7
    pipeline.  It coordinates:

    1. **Input validation** – verify that upstream JSON reports exist and
       are parseable before any scoring begins.
    2. **Tier detection** – check Questa availability (or honour a forced
       tier from config) and select the appropriate scorer.
    3. **Scoring** – delegate to ``Tier1Scorer`` or ``Tier2Scorer``,
       which in turn run all component scorers and produce a
       ``FinalReport``.
    4. **Export** – write the report to every format enabled in the
       ``ExportConfig`` (JSON is mandatory; HTML / JUnit / CSV / PDF are
       optional).

    The class is intentionally **stateless across runs** – each call to
    ``run()`` is independent.  State that survives a run (the last
    result) is cached for convenience but never relied upon internally.

    Typical usage::

        config = ScoreCalculationConfig.from_yaml(Path(".tbeval.yaml"))
        analyzer = TestbenchAnalyzer(config)
        result = analyzer.run(submission_id="student_42_alu")

        print(result.report.score.percentage)  # 87.35
        print(result.exported_files)           # {'json': PosixPath(...), ...}
    """

    # -----------------------------------------------------------------
    # Construction
    # -----------------------------------------------------------------

    def __init__(self, config: ScoreCalculationConfig):
        """
        Initialise the analyser with a validated configuration.

        Args:
            config: Fully-constructed ``ScoreCalculationConfig``.  This
                    is typically built via ``from_yaml`` or ``from_cli``.
        """
        self.config = config
        self._questa_caps: Optional[QuestaCapabilities] = None
        self._last_result: Optional[AnalysisResult] = None

        logger.debug(
            "TestbenchAnalyzer initialised "
            f"(submission_dir={config.submission_dir}, "
            f"auto_detect_tier={config.auto_detect_tier})"
        )

    # -----------------------------------------------------------------
    # Full pipeline
    # -----------------------------------------------------------------

    def run(self, submission_id: Optional[str] = None) -> AnalysisResult:
        """
        Execute the full scoring + export pipeline.

        This is the recommended entry-point for most callers.  It runs
        validation → tier detection → scoring → export in sequence and
        returns a rich ``AnalysisResult``.

        Args:
            submission_id: Human-readable identifier for this submission.
                If ``None``, the name of ``config.submission_dir`` is
                used.

        Returns:
            ``AnalysisResult`` containing the ``FinalReport``, the tier
            that was used, all exported file paths, and timing info.

        Raises:
            ValueError: If critical input files are missing or
                unparseable **and** no fallback is possible.
        """
        wall_start = time.time()

        # Resolve submission id
        if submission_id is None:
            submission_id = self.config.submission_dir.name or "submission"

        logger.info(
            f"Starting analysis for '{submission_id}' "
            f"(dir={self.config.submission_dir})"
        )

        # 1. Validate inputs
        warnings = self.validate_inputs()
        if warnings:
            for w in warnings:
                logger.warning(f"Input validation: {w}")

        # 2. Detect tier
        tier, reason = self.detect_tier()
        logger.info(f"Tier selected: {tier.value} ({reason})")

        # 3. Score
        report = self.score(submission_id=submission_id, tier=tier)

        # 4. Export
        exported = self.export(report)

        # 5. Build result
        wall_ms = (time.time() - wall_start) * 1000.0
        result = AnalysisResult(
            report=report,
            tier_used=tier,
            tier_detection_reason=reason,
            exported_files=exported,
            validation_warnings=warnings,
            wall_clock_ms=wall_ms,
        )

        self._last_result = result

        logger.info(
            f"Analysis complete: {report.score.percentage:.2f}% "
            f"(Grade {report.score.grade.value}) "
            f"in {wall_ms:.0f} ms"
        )

        return result

    # -----------------------------------------------------------------
    # Input validation
    # -----------------------------------------------------------------

    def validate_inputs(self) -> List[str]:
        """
        Validate that upstream JSON reports exist and are readable.

        Returns a list of human-readable warning strings.  An empty list
        means everything looks good.  Warnings are **non-fatal** – the
        pipeline will still attempt to run with whatever data is
        available.

        Returns:
            List of warning strings (empty if all OK).
        """
        warnings: List[str] = []

        # Delegate to config-level validation first
        warnings.extend(self.config.validate())

        # Additionally, try to parse each report to catch JSON errors
        # early, before the scorers blow up with confusing tracebacks.
        for label, path in [
            ("coverage_report", self.config.coverage_report_path),
            ("test_report", self.config.test_report_path),
            ("quality_report", self.config.quality_report_path),
        ]:
            if path and path.exists():
                try:
                    import json
                    with open(path) as f:
                        json.load(f)
                except (json.JSONDecodeError, OSError) as exc:
                    warnings.append(
                        f"{label} ({path}) is not valid JSON: {exc}"
                    )

        return warnings

    # -----------------------------------------------------------------
    # Tier detection
    # -----------------------------------------------------------------

    def detect_tier(self) -> tuple:
        """
        Determine which scoring tier to use.

        The decision logic is:

        1. If ``config.force_tier`` is set, use it unconditionally.
        2. If ``config.auto_detect_tier`` is ``True`` (the default),
           probe for Questa availability and choose accordingly.
        3. Otherwise fall back to Tier 1 (open-source).

        Returns:
            A ``(ScoringTier, reason_string)`` tuple.
        """
        # Forced tier
        if self.config.force_tier is not None:
            reason = f"forced via configuration (force_tier={self.config.force_tier.value})"
            return self.config.force_tier, reason

        # Auto-detect
        if self.config.auto_detect_tier:
            caps = self._get_questa_capabilities()
            if caps.tier2_available:
                reason = (
                    f"Questa detected (version={caps.questa_version}, "
                    f"license={caps.license_type})"
                )
                return ScoringTier.PROFESSIONAL, reason
            else:
                reason = "Questa not available – using open-source tier"
                return ScoringTier.OPEN_SOURCE, reason

        # Default
        reason = "auto-detect disabled, defaulting to open-source tier"
        return ScoringTier.OPEN_SOURCE, reason

    # -----------------------------------------------------------------
    # Scoring
    # -----------------------------------------------------------------

    def score(
        self,
        submission_id: str,
        tier: Optional[ScoringTier] = None,
    ) -> FinalReport:
        """
        Run the appropriate tier scorer and produce a ``FinalReport``.

        This method is useful when you want scoring **without** the
        automatic export step (e.g. in tests, or when you want to
        inspect the report before writing it out).

        Args:
            submission_id: Identifier for this submission.
            tier: Tier to use.  If ``None``, ``detect_tier()`` is called
                automatically.

        Returns:
            A fully-populated ``FinalReport``.

        Raises:
            ValueError: If required input reports are missing.
        """
        if tier is None:
            tier, _ = self.detect_tier()

        score_start = time.time()

        if tier == ScoringTier.PROFESSIONAL:
            report = self._score_tier2(submission_id, score_start)
        else:
            report = self._score_tier1(submission_id, score_start)

        return report

    def _score_tier1(
        self,
        submission_id: str,
        start_time: float,
    ) -> FinalReport:
        """
        Delegate scoring to ``Tier1Scorer``.

        Args:
            submission_id: Submission identifier.
            start_time: ``time.time()`` when scoring began (for duration
                calculation).

        Returns:
            ``FinalReport`` from Tier 1 scorer.
        """
        logger.info("Running Tier 1 (open-source) scoring")

        scorer = Tier1Scorer(self.config)
        tier_score = scorer.calculate_score()

        duration_ms = (time.time() - start_time) * 1000.0
        report = scorer.generate_report(
            submission_id=submission_id,
            tier_score=tier_score,
            total_duration_ms=duration_ms,
        )

        return report

    def _score_tier2(
        self,
        submission_id: str,
        start_time: float,
    ) -> FinalReport:
        """
        Delegate scoring to ``Tier2Scorer`` with automatic fallback.

        If Tier 2 scoring fails (e.g. Questa licence expired between
        detection and actual use), the method logs a warning and falls
        back to Tier 1 scoring so the pipeline never hard-fails on a
        licence issue alone.

        Args:
            submission_id: Submission identifier.
            start_time: ``time.time()`` when scoring began.

        Returns:
            ``FinalReport`` from Tier 2 scorer (or Tier 1 on fallback).
        """
        logger.info("Running Tier 2 (professional) scoring")

        try:
            scorer = Tier2Scorer(self.config)
            tier_score = scorer.calculate_score()

            duration_ms = (time.time() - start_time) * 1000.0
            report = scorer.generate_report(
                submission_id=submission_id,
                tier_score=tier_score,
                total_duration_ms=duration_ms,
            )
            return report

        except Exception as exc:
            logger.warning(
                f"Tier 2 scoring failed ({exc}); "
                f"falling back to Tier 1"
            )
            return self._score_tier1(submission_id, start_time)

    # -----------------------------------------------------------------
    # Export
    # -----------------------------------------------------------------

    def export(self, report: FinalReport) -> Dict[str, Path]:
        """
        Write the report to all configured export formats.

        JSON is **always** written (it is the canonical on-disk
        representation).  Other formats are controlled by
        ``config.export_config``.

        Args:
            report: The ``FinalReport`` to export.

        Returns:
            Dict mapping format name (``"json"``, ``"html"``, …) to the
            ``Path`` that was written.  Formats that failed are omitted
            from the dict (with a warning logged).
        """
        export_cfg = self.config.export_config
        output_dir = export_cfg.output_dir
        output_dir.mkdir(parents=True, exist_ok=True)

        exported: Dict[str, Path] = {}

        # JSON – mandatory
        exported["json"] = self._export_json(report, output_dir)

        # HTML
        if export_cfg.generate_html:
            path = self._export_html(report, output_dir)
            if path:
                exported["html"] = path

        # JUnit XML
        if export_cfg.generate_junit:
            path = self._export_junit(report, output_dir)
            if path:
                exported["junit"] = path

        # CSV
        if export_cfg.generate_csv:
            path = self._export_csv(report, output_dir)
            if path:
                exported["csv"] = path

        # PDF
        if export_cfg.generate_pdf:
            path = self._export_pdf(report, output_dir)
            if path:
                exported["pdf"] = path

        logger.info(
            f"Exported {len(exported)} format(s): "
            f"{', '.join(exported.keys())}"
        )

        return exported

    # -- individual exporters -----------------------------------------

    def _export_json(
        self,
        report: FinalReport,
        output_dir: Path,
    ) -> Path:
        """
        Export the canonical JSON report.

        This always succeeds (or raises) because JSON is mandatory.
        """
        path = output_dir / "final_score.json"
        report.save(path)
        logger.info(f"JSON report saved: {path}")
        return path

    def _export_html(
        self,
        report: FinalReport,
        output_dir: Path,
    ) -> Optional[Path]:
        """Export HTML dashboard."""
        path = output_dir / "score_report.html"
        try:
            exporter = HTMLExporter()
            exporter.export(report, path)
            logger.info(f"HTML report saved: {path}")
            return path
        except Exception as exc:
            logger.warning(f"HTML export failed: {exc}")
            return None

    def _export_junit(
        self,
        report: FinalReport,
        output_dir: Path,
    ) -> Optional[Path]:
        """Export JUnit XML for CI/CD."""
        path = output_dir / "junit.xml"
        try:
            exporter = JUnitExporter()
            exporter.export(report, path)
            logger.info(f"JUnit report saved: {path}")
            return path
        except Exception as exc:
            logger.warning(f"JUnit export failed: {exc}")
            return None

    def _export_csv(
        self,
        report: FinalReport,
        output_dir: Path,
    ) -> Optional[Path]:
        """Export CSV spreadsheets."""
        csv_dir = output_dir / "csv"
        try:
            exporter = CSVExporter()
            exporter.export(report, csv_dir)
            logger.info(f"CSV reports saved: {csv_dir}")
            return csv_dir
        except Exception as exc:
            logger.warning(f"CSV export failed: {exc}")
            return None

    def _export_pdf(
        self,
        report: FinalReport,
        output_dir: Path,
    ) -> Optional[Path]:
        """Export professional PDF report."""
        path = output_dir / "score_report.pdf"
        try:
            from .exporters.pdf_exporter import PDFExporter, REPORTLAB_AVAILABLE

            if not REPORTLAB_AVAILABLE:
                logger.warning(
                    "PDF export skipped: reportlab not installed "
                    "(pip install reportlab)"
                )
                return None

            exporter = PDFExporter()
            exporter.export(report, path)
            logger.info(f"PDF report saved: {path}")
            return path
        except ImportError:
            logger.warning(
                "PDF export skipped: reportlab not installed"
            )
            return None
        except Exception as exc:
            logger.warning(f"PDF export failed: {exc}")
            return None

    # -----------------------------------------------------------------
    # Questa capability caching
    # -----------------------------------------------------------------

    def _get_questa_capabilities(self) -> QuestaCapabilities:
        """
        Return Questa capabilities, caching across calls.

        The licence check involves subprocess calls so we only do it
        once per ``TestbenchAnalyzer`` instance.
        """
        if self._questa_caps is None:
            self._questa_caps = check_questa_availability(
                self.config.questa_config
            )
        return self._questa_caps

    # -----------------------------------------------------------------
    # Summary helpers
    # -----------------------------------------------------------------

    def get_summary(self) -> str:
        """
        Return a human-readable summary of the last analysis run.

        Returns:
            Multi-line summary string, or a message if ``run()`` has
            not been called yet.
        """
        if self._last_result is None:
            return "No analysis has been run yet."

        result = self._last_result
        report = result.report
        score = report.score

        lines = [
            "=" * 60,
            "TB EVAL ANALYSIS SUMMARY",
            "=" * 60,
            "",
            f"  Submission:  {report.submission_id}",
            f"  Tier:        {result.tier_used.display_name}",
            f"  Reason:      {result.tier_detection_reason}",
            "",
            f"  Score:       {score.overall:.4f} ({score.percentage:.2f}%)",
            f"  Grade:       {score.grade.value}",
            f"  Pass:        {'YES' if score.pass_threshold else 'NO'}",
            "",
            "  Components:",
        ]

        sorted_components = sorted(
            score.components.items(),
            key=lambda item: item[1].weight,
            reverse=True,
        )
        for name, comp in sorted_components:
            status = "✓" if comp.threshold_met else "✗"
            lines.append(
                f"    {status} {comp.component_type.display_name:25s} "
                f"{comp.percentage:6.2f}%  "
                f"(w={comp.weight:.2f})"
            )

        if result.exported_files:
            lines.append("")
            lines.append("  Exports:")
            for fmt, path in result.exported_files.items():
                lines.append(f"    {fmt:8s} → {path}")

        if result.validation_warnings:
            lines.append("")
            lines.append("  Warnings:")
            for w in result.validation_warnings:
                lines.append(f"    ⚠ {w}")

        lines.append("")
        lines.append(f"  Duration:    {result.wall_clock_ms:.0f} ms")
        lines.append("=" * 60)

        return "\n".join(lines)

    # -----------------------------------------------------------------
    # Properties
    # -----------------------------------------------------------------

    @property
    def last_result(self) -> Optional[AnalysisResult]:
        """The result from the most recent ``run()`` call, or ``None``."""
        return self._last_result


# =============================================================================
# CONVENIENCE FUNCTIONS
# =============================================================================

def analyze(
    submission_dir: Path,
    submission_id: Optional[str] = None,
    config_file: Optional[Path] = None,
    **config_overrides: Any,
) -> FinalReport:
    """
    One-liner convenience function for external consumers.

    Builds a configuration, creates a ``TestbenchAnalyzer``, runs the
    full pipeline, and returns the ``FinalReport``.

    Args:
        submission_dir: Root directory of the submission.
        submission_id: Human-readable identifier (defaults to dir name).
        config_file: Path to ``.tbeval.yaml``.  If ``None``, the
            function looks for one inside ``submission_dir``.
        **config_overrides: Forwarded as CLI overrides to
            ``ScoreCalculationConfig.from_yaml``.

    Returns:
        The ``FinalReport`` produced by the analysis.

    Example::

        from step7_score.analyzer import analyze
        report = analyze(Path("./student_submission"))
        print(report.score.percentage)
    """
    submission_dir = Path(submission_dir)

    # Find config file
    if config_file is None:
        for name in [".tbeval.yaml", ".tbeval.yml", "tbeval.yaml"]:
            candidate = submission_dir / name
            if candidate.exists():
                config_file = candidate
                break

    # Build config
    if config_file and config_file.exists():
        config = ScoreCalculationConfig.from_yaml(
            config_file,
            cli_overrides=config_overrides,
        )
    else:
        config = ScoreCalculationConfig(
            submission_dir=submission_dir,
            **{
                k: v
                for k, v in config_overrides.items()
                if k in ScoreCalculationConfig.__dataclass_fields__
            },
        )
        # Make sure submission_dir is set
        config.submission_dir = submission_dir

    # Run
    analyzer = TestbenchAnalyzer(config)
    result = analyzer.run(submission_id=submission_id)
    return result.report


def analyze_from_config(
    config: ScoreCalculationConfig,
    submission_id: Optional[str] = None,
) -> FinalReport:
    """
    Analyse using a pre-built configuration object.

    This is the preferred entry-point when the caller has already
    constructed a ``ScoreCalculationConfig`` (e.g. from a test fixture
    or from ``__main__.py``).

    Args:
        config: Pre-built configuration.
        submission_id: Optional override for the submission identifier.

    Returns:
        The ``FinalReport`` produced by the analysis.
    """
    analyzer = TestbenchAnalyzer(config)
    result = analyzer.run(submission_id=submission_id)
    return result.report
