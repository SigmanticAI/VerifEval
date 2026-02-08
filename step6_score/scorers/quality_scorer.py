"""
Quality scorer for Step 7: Scoring

Scores code quality component based on:
- Linting results (syntax, best practices)
- Style compliance (formatting, naming)
- Code complexity (cyclomatic complexity, nesting)
- Documentation completeness (comments, docstrings)

Used by both Tier 1 and Tier 2 scoring systems.

Author: TB Eval Team
Version: 0.1.0
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Dict, List, Any
import logging

from ..models import (
    ComponentScore,
    ComponentType,
    QualityMetrics,
    Improvement,
)

logger = logging.getLogger(__name__)


# =============================================================================
# CONFIGURATION
# =============================================================================

@dataclass
class QualityScoringConfig:
    """
    Configuration for quality scoring
    
    Attributes:
        weight: Weight for this component in overall score
        min_overall_score: Minimum overall quality score
        max_style_violations: Maximum allowed style violations
        require_linting_pass: Require linting to pass
        complexity_weight: Weight for complexity in quality score
        documentation_weight: Weight for documentation in quality score
    """
    weight: float = 0.15  # Default Tier 1 weight (0.10 for Tier 2)
    min_overall_score: float = 0.70
    max_style_violations: int = 20
    require_linting_pass: bool = True
    complexity_weight: float = 0.40
    documentation_weight: float = 0.30


# =============================================================================
# QUALITY SCORER
# =============================================================================

class QualityScorer:
    """
    Score code quality component
    
    This scorer evaluates testbench quality based on static analysis
    metrics from Step 2 (quality_report.json).
    
    Scoring algorithm:
    1. Load quality metrics from report
    2. Use existing overall score from Step 2
    3. Validate against thresholds
    4. Generate recommendations for improvement
    5. Create ComponentScore
    """
    
    def __init__(
        self,
        config: Optional[QualityScoringConfig] = None,
        quality_report_path: Optional[Path] = None
    ):
        """
        Initialize quality scorer
        
        Args:
            config: Scoring configuration
            quality_report_path: Path to quality_report.json (optional)
        """
        self.config = config or QualityScoringConfig()
        self.quality_report_path = quality_report_path
        self.quality_metrics: Optional[QualityMetrics] = None
    
    def score(
        self,
        quality_report_path: Optional[Path] = None
    ) -> ComponentScore:
        """
        Calculate quality component score
        
        Args:
            quality_report_path: Path to quality_report.json from Step 2
        
        Returns:
            ComponentScore for code quality
        
        Raises:
            FileNotFoundError: If quality report not found (returns default)
            ValueError: If quality report format is invalid
        """
        # Use provided path or configured path
        report_path = quality_report_path or self.quality_report_path
        
        # Quality report is optional - use defaults if not available
        if not report_path or not Path(report_path).exists():
            logger.warning("Quality report not found, using default neutral score")
            return self._create_default_score()
        
        logger.info(f"Scoring quality from: {report_path}")
        
        try:
            # Load quality metrics
            self.quality_metrics = QualityMetrics.from_quality_report(report_path)
            
            # Calculate score (use overall score from Step 2)
            score_value = self.quality_metrics.overall_score
            
            # Validate thresholds
            threshold_met = self._check_thresholds()
            
            # Generate raw metrics dictionary
            raw_metrics = self._get_raw_metrics()
            
            # Generate recommendations
            recommendations = self._generate_recommendations()
            
            # Generate details
            details = self._generate_details()
            
            # Create component score
            component_score = ComponentScore(
                component_type=ComponentType.CODE_QUALITY,
                value=score_value,
                weight=self.config.weight,
                raw_metrics=raw_metrics,
                threshold_met=threshold_met,
                threshold_value=self.config.min_overall_score,
                details=details,
                recommendations=recommendations,
            )
            
            logger.info(
                f"Quality score: {score_value:.4f} "
                f"({component_score.percentage:.2f}%) - "
                f"{'PASS' if threshold_met else 'FAIL'}"
            )
            
            return component_score
        
        except Exception as e:
            logger.error(f"Error scoring quality: {e}")
            return self._create_default_score()
    
    def _create_default_score(self) -> ComponentScore:
        """
        Create default score when quality report unavailable
        
        Returns:
            ComponentScore with neutral default values
        """
        logger.info("Creating default quality score (0.75 neutral)")
        
        return ComponentScore(
            component_type=ComponentType.CODE_QUALITY,
            value=0.75,  # Neutral default
            weight=self.config.weight,
            raw_metrics={
                "default": True,
                "message": "Quality report not available"
            },
            threshold_met=True,  # Don't fail if report missing
            threshold_value=self.config.min_overall_score,
            details="Quality report not available - using default neutral score (75%)",
            recommendations=["Run static quality checks (Step 2) for detailed quality analysis"],
        )
    
    def _check_thresholds(self) -> bool:
        """
        Check if quality meets all thresholds
        
        Returns:
            True if all thresholds are met
        """
        if not self.quality_metrics:
            return False
        
        checks = []
        
        # Overall score threshold
        checks.append(
            self.quality_metrics.overall_score >= self.config.min_overall_score
        )
        
        # Linting pass requirement
        if self.config.require_linting_pass:
            checks.append(self.quality_metrics.linting_passed)
        
        # Style violations limit
        checks.append(
            self.quality_metrics.style_violations <= self.config.max_style_violations
        )
        
        return all(checks)
    
    def _get_raw_metrics(self) -> Dict[str, Any]:
        """
        Get raw quality metrics
        
        Returns:
            Dictionary of raw metrics
        """
        if not self.quality_metrics:
            return {}
        
        return {
            "overall_score": self.quality_metrics.overall_score,
            "linting_passed": self.quality_metrics.linting_passed,
            "style_violations": self.quality_metrics.style_violations,
            "complexity_score": self.quality_metrics.complexity_score,
            "documentation_score": self.quality_metrics.documentation_score,
            "source_report": self.quality_metrics.source_report,
        }
    
    def _generate_details(self) -> str:
        """
        Generate human-readable details
        
        Returns:
            Details string
        """
        if not self.quality_metrics:
            return "Quality metrics not available"
        
        m = self.quality_metrics
        
        details = (
            f"Code Quality: {m.overall_score * 100:.2f}%\n"
            f"  Linting:       {'PASS' if m.linting_passed else 'FAIL'}\n"
            f"  Violations:    {m.style_violations}\n"
            f"  Complexity:    {m.complexity_score * 100:.2f}%\n"
            f"  Documentation: {m.documentation_score * 100:.2f}%"
        )
        
        return details
    
    def _generate_recommendations(self) -> List[str]:
        """
        Generate recommendations for improving quality
        
        Returns:
            List of recommendation strings
        """
        if not self.quality_metrics:
            return []
        
        recommendations = []
        m = self.quality_metrics
        
        # Linting recommendations
        if not m.linting_passed:
            recommendations.append(
                "Fix linting errors. Run linter and address all reported issues."
            )
        
        # Style violations recommendations
        if m.style_violations > self.config.max_style_violations:
            excess = m.style_violations - self.config.max_style_violations
            recommendations.append(
                f"Reduce style violations by {excess} to meet threshold of {self.config.max_style_violations}. "
                f"Use auto-formatter and follow style guide."
            )
        elif m.style_violations > 0:
            recommendations.append(
                f"Fix {m.style_violations} style violation(s) for cleaner code. "
                f"Consider using black, yapf, or verible-verilog-format."
            )
        
        # Complexity recommendations
        if m.complexity_score < 0.70:
            recommendations.append(
                "Reduce code complexity. Refactor complex functions, reduce nesting depth, "
                "and extract reusable components."
            )
        
        # Documentation recommendations
        if m.documentation_score < 0.70:
            recommendations.append(
                "Improve documentation. Add docstrings to functions/classes, "
                "include inline comments for complex logic, and update README."
            )
        
        # Overall score recommendation
        if m.overall_score < self.config.min_overall_score:
            gap = (self.config.min_overall_score - m.overall_score) * 100
            recommendations.append(
                f"Improve overall code quality by {gap:.1f}% to meet {self.config.min_overall_score * 100:.0f}% threshold. "
                f"Focus on linting, style, and documentation."
            )
        
        # If quality is good, suggest best practices
        if not recommendations:
            if m.overall_score < 0.90:
                recommendations.append(
                    "Quality meets all thresholds. Consider aiming for 90%+ for excellent quality."
                )
        
        return recommendations
    
    def generate_improvements(self) -> List[Improvement]:
        """
        Generate actionable improvements for quality
        
        Returns:
            List of Improvement objects with specific actions
        """
        if not self.quality_metrics:
            return []
        
        improvements = []
        m = self.quality_metrics
        
        # Linting improvement
        if not m.linting_passed:
            improvements.append(Improvement(
                component=ComponentType.CODE_QUALITY,
                priority="high",
                current_value=0.0,  # Failing
                target_value=100.0,  # Must pass
                impact=0.15,  # Significant impact
                actions=[
                    "Run linting tool: pylint, flake8, or verilator --lint-only",
                    "Fix all reported errors and warnings",
                    "Configure linter to match project style guide",
                    "Add pre-commit hook to prevent future violations",
                ]
            ))
        
        # Style violations improvement
        if m.style_violations > self.config.max_style_violations:
            current_pct = max(0, 100 - m.style_violations * 2)  # Rough estimate
            target_pct = 100 - self.config.max_style_violations * 2
            impact = (m.style_violations - self.config.max_style_violations) * 0.005
            
            improvements.append(Improvement(
                component=ComponentType.CODE_QUALITY,
                priority="medium" if impact > 0.05 else "low",
                current_value=current_pct,
                target_value=target_pct,
                impact=min(impact, 0.10),
                actions=[
                    "Run auto-formatter: black, yapf, or verible-verilog-format",
                    "Fix naming convention violations (snake_case for Python)",
                    "Add missing whitespace around operators",
                    "Remove trailing whitespace and fix indentation",
                ]
            ))
        
        # Complexity improvement
        if m.complexity_score < 0.70:
            impact = (0.70 - m.complexity_score) * self.config.complexity_weight * self.config.weight
            improvements.append(Improvement(
                component=ComponentType.CODE_QUALITY,
                priority="medium" if impact > 0.03 else "low",
                current_value=m.complexity_score * 100,
                target_value=70.0,
                impact=impact,
                actions=[
                    "Refactor functions with cyclomatic complexity > 10",
                    "Reduce nesting depth (max 3-4 levels)",
                    "Extract complex logic into helper functions",
                    "Simplify conditional expressions",
                ]
            ))
        
        # Documentation improvement
        if m.documentation_score < 0.70:
            impact = (0.70 - m.documentation_score) * self.config.documentation_weight * self.config.weight
            improvements.append(Improvement(
                component=ComponentType.CODE_QUALITY,
                priority="low",
                current_value=m.documentation_score * 100,
                target_value=70.0,
                impact=impact,
                actions=[
                    "Add docstrings to all public functions/classes",
                    "Document complex algorithms with inline comments",
                    "Update README with usage examples",
                    "Add comments for non-obvious design decisions",
                ]
            ))
        
        # Sort by impact (highest first)
        improvements.sort(key=lambda x: x.impact, reverse=True)
        
        return improvements
    
    def get_quality_breakdown(self) -> Dict[str, Any]:
        """
        Get detailed quality breakdown for reporting
        
        Returns:
            Dictionary with quality breakdown
        """
        if not self.quality_metrics:
            return {
                "available": False,
                "message": "Quality report not available"
            }
        
        m = self.quality_metrics
        
        return {
            "available": True,
            "overall": {
                "score": m.overall_score,
                "percentage": m.overall_score * 100.0,
                "threshold": self.config.min_overall_score,
                "meets_threshold": m.overall_score >= self.config.min_overall_score,
            },
            "linting": {
                "passed": m.linting_passed,
                "required": self.config.require_linting_pass,
                "meets_threshold": m.linting_passed or not self.config.require_linting_pass,
            },
            "style": {
                "violations": m.style_violations,
                "threshold": self.config.max_style_violations,
                "meets_threshold": m.style_violations <= self.config.max_style_violations,
            },
            "complexity": {
                "score": m.complexity_score,
                "percentage": m.complexity_score * 100.0,
            },
            "documentation": {
                "score": m.documentation_score,
                "percentage": m.documentation_score * 100.0,
            },
        }


# =============================================================================
# CONVENIENCE FUNCTIONS
# =============================================================================

def score_quality(
    quality_report_path: Optional[Path] = None,
    weight: float = 0.15,
    thresholds: Optional[Dict[str, Any]] = None
) -> ComponentScore:
    """
    Convenience function to score quality
    
    Args:
        quality_report_path: Path to quality_report.json
        weight: Weight for this component (default: 0.15 for Tier 1)
        thresholds: Optional threshold overrides
    
    Returns:
        ComponentScore for code quality
    
    Example:
        >>> score = score_quality(
        ...     Path(".tbeval/quality/quality_report.json"),
        ...     weight=0.10  # Tier 2 weight
        ... )
        >>> print(f"Quality: {score.percentage:.2f}%")
    """
    # Create config with thresholds
    config = QualityScoringConfig(weight=weight)
    
    if thresholds:
        config.min_overall_score = thresholds.get("min_overall_score", config.min_overall_score)
        config.max_style_violations = thresholds.get("max_style_violations", config.max_style_violations)
        config.require_linting_pass = thresholds.get("require_linting_pass", config.require_linting_pass)
    
    # Create scorer and calculate score
    scorer = QualityScorer(config=config)
    return scorer.score(quality_report_path)


def get_quality_metrics(quality_report_path: Path) -> QualityMetrics:
    """
    Load quality metrics from report
    
    Args:
        quality_report_path: Path to quality_report.json
    
    Returns:
        QualityMetrics object
    
    Example:
        >>> metrics = get_quality_metrics(Path("quality_report.json"))
        >>> print(f"Linting: {'PASS' if metrics.linting_passed else 'FAIL'}")
    """
    return QualityMetrics.from_quality_report(quality_report_path)


# =============================================================================
# EXAMPLE USAGE
# =============================================================================

if __name__ == "__main__":
    import sys
    import json
    
    # Setup logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(levelname)s - %(message)s'
    )
    
    print("=" * 60)
    print("QUALITY SCORING")
    print("=" * 60)
    
    # Check if quality report provided
    quality_report = None
    if len(sys.argv) > 1:
        quality_report = Path(sys.argv[1])
        if not quality_report.exists():
            print(f"Warning: Quality report not found: {quality_report}")
            quality_report = None
    
    # Create scorer
    config = QualityScoringConfig(
        weight=0.15,
        min_overall_score=0.70,
        max_style_violations=20,
        require_linting_pass=True,
    )
    
    scorer = QualityScorer(config=config)
    
    # Calculate score
    try:
        score = scorer.score(quality_report)
        
        print(f"\nComponent Score:")
        print(f"  Value:       {score.value:.4f}")
        print(f"  Percentage:  {score.percentage:.2f}%")
        print(f"  Grade:       {score.grade.value}")
        print(f"  Weight:      {score.weight}")
        print(f"  Contribution: {score.weighted_contribution:.4f}")
        print(f"  Threshold Met: {'✓ YES' if score.threshold_met else '✗ NO'}")
        
        print(f"\nDetails:")
        print(score.details)
        
        if score.recommendations:
            print(f"\nRecommendations:")
            for i, rec in enumerate(score.recommendations, 1):
                print(f"  {i}. {rec}")
        
        # Get quality breakdown
        breakdown = scorer.get_quality_breakdown()
        print(f"\nQuality Breakdown:")
        print(json.dumps(breakdown, indent=2))
        
        # Generate improvements
        improvements = scorer.generate_improvements()
        if improvements:
            print(f"\nActionable Improvements:")
            for i, imp in enumerate(improvements, 1):
                print(f"\n{i}. {imp.component.display_name}")
                print(f"   Priority: {imp.priority.upper()}")
                print(f"   Current:  {imp.current_value:.2f}%")
                print(f"   Target:   {imp.target_value:.2f}%")
                print(f"   Impact:   {imp.impact:.4f} score points")
                print(f"   Actions:")
                for action in imp.actions:
                    print(f"     • {action}")
        
        # Export to JSON
        output = {
            "component_score": score.to_dict(),
            "breakdown": breakdown,
            "improvements": [imp.to_dict() for imp in improvements],
        }
        
        output_path = Path("quality_score.json")
        with open(output_path, 'w') as f:
            json.dump(output, f, indent=2)
        
        print(f"\n✓ Score exported to: {output_path}")
        
        sys.exit(0 if score.threshold_met else 1)
    
    except Exception as e:
        print(f"\n✗ Error scoring quality: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
