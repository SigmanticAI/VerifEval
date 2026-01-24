"""
Confidence scoring for routing decisions
"""
from typing import Dict, List
from ..models import DetectionResult, QualityReport, TBType


class ConfidenceScorer:
    """Calculates confidence scores for routing decisions"""
    
    @staticmethod
    def calculate_detection_confidence(
        detection_results: List[DetectionResult],
        quality_report: QualityReport
    ) -> float:
        """
        Calculate overall confidence based on detection and quality
        
        Formula:
        base_confidence = max(detection_confidences)
        quality_penalty = quality_issues / threshold
        final_confidence = base_confidence * (1 - quality_penalty)
        """
        if not detection_results:
            return 0.0
        
        # Get highest confidence detection
        base_confidence = max(r.confidence for r in detection_results)
        
        # Apply quality penalty
        quality_multiplier = ConfidenceScorer._calculate_quality_multiplier(quality_report)
        
        final_confidence = base_confidence * quality_multiplier
        
        return min(1.0, max(0.0, final_confidence))
    
    @staticmethod
    def _calculate_quality_multiplier(quality_report: QualityReport) -> float:
        """Calculate quality score multiplier (0.0 to 1.0)"""
        if not quality_report:
            return 1.0
        
        # Critical errors heavily penalize
        if quality_report.critical_errors > 0:
            penalty = min(0.5, quality_report.critical_errors * 0.1)
            return 1.0 - penalty
        
        # Warnings slightly penalize
        if quality_report.warnings > 10:
            penalty = min(0.2, (quality_report.warnings - 10) * 0.01)
            return 1.0 - penalty
        
        return 1.0
    
    @staticmethod
    def select_best_detection(
        detection_results: List[DetectionResult]
    ) -> DetectionResult:
        """Select the best detection result based on confidence"""
        if not detection_results:
            raise ValueError("No detection results to select from")
        
        # Sort by confidence
        sorted_results = sorted(
            detection_results,
            key=lambda r: r.confidence,
            reverse=True
        )
        
        return sorted_results[0]
    
    @staticmethod
    def explain_confidence(
        detection: DetectionResult,
        quality_report: QualityReport,
        final_confidence: float
    ) -> List[str]:
        """Generate human-readable confidence explanation"""
        explanations = []
        
        # Detection explanation
        explanations.append(
            f"Base detection confidence: {detection.confidence:.2f} "
            f"({detection.detection_method})"
        )
        
        # Quality impact
        if quality_report:
            if quality_report.critical_errors > 0:
                explanations.append(
                    f"⚠️  Quality penalty: {quality_report.critical_errors} critical errors found"
                )
            elif quality_report.warnings > 10:
                explanations.append(
                    f"⚠️  Quality warning: {quality_report.warnings} linting warnings"
                )
            else:
                explanations.append("✓ No quality issues detected")
        
        # Final score
        if final_confidence >= 0.8:
            explanations.append(f"✓ High confidence: {final_confidence:.2f}")
        elif final_confidence >= 0.5:
            explanations.append(f"⚠️  Medium confidence: {final_confidence:.2f}")
        else:
            explanations.append(f"❌ Low confidence: {final_confidence:.2f} - manual review recommended")
        
        return explanations
