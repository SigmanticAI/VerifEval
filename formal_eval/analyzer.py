"""
Formal Verification Metrics and Analysis.

Implements scoring based on FVEval paper methodology:
- Syntax correctness
- Proof success rate
- Cover point reachability
"""

import json
import statistics
from pathlib import Path
from dataclasses import dataclass, field
from typing import Dict, List, Optional


@dataclass
class FormalMetrics:
    """Metrics for a single formal verification run."""
    
    # Parsing/Synthesis
    parse_success: bool = False
    synth_success: bool = False
    synth_warnings: int = 0
    
    # Assertions
    assertions_found: int = 0
    assertions_proven: int = 0
    assertions_failed: int = 0
    assertions_unknown: int = 0
    
    # Cover points
    cover_points_found: int = 0
    cover_points_reached: int = 0
    
    @property
    def proof_rate(self) -> float:
        """Percentage of assertions proven."""
        if self.assertions_found == 0:
            return 100.0  # No assertions = vacuously true
        return (self.assertions_proven / self.assertions_found) * 100
    
    @property
    def failure_rate(self) -> float:
        """Percentage of assertions that failed."""
        if self.assertions_found == 0:
            return 0.0
        return (self.assertions_failed / self.assertions_found) * 100
    
    @property
    def cover_rate(self) -> float:
        """Percentage of cover points reached."""
        if self.cover_points_found == 0:
            return 100.0  # No cover points = vacuously covered
        return (self.cover_points_reached / self.cover_points_found) * 100
    
    @property
    def overall_score(self) -> float:
        """
        Overall formal verification score (0-100).
        
        Weighted:
        - 30% Syntax (parse + synth success)
        - 50% Proof rate
        - 20% Cover rate
        """
        syntax_score = 100.0 if (self.parse_success and self.synth_success) else 0.0
        
        return (
            0.30 * syntax_score +
            0.50 * self.proof_rate +
            0.20 * self.cover_rate
        )
    
    def to_dict(self) -> Dict:
        return {
            "parse_success": self.parse_success,
            "synth_success": self.synth_success,
            "synth_warnings": self.synth_warnings,
            "assertions_found": self.assertions_found,
            "assertions_proven": self.assertions_proven,
            "assertions_failed": self.assertions_failed,
            "assertions_unknown": self.assertions_unknown,
            "cover_points_found": self.cover_points_found,
            "cover_points_reached": self.cover_points_reached,
            "proof_rate": round(self.proof_rate, 2),
            "cover_rate": round(self.cover_rate, 2),
            "overall_score": round(self.overall_score, 2),
        }


@dataclass
class ProjectResults:
    """Aggregated results for a formal verification project."""
    
    project_name: str
    num_runs: int = 0
    metrics: List[FormalMetrics] = field(default_factory=list)
    
    def add_run(self, metric: FormalMetrics):
        """Add a run's metrics."""
        self.metrics.append(metric)
        self.num_runs = len(self.metrics)
    
    @property
    def syntax_success_rate(self) -> float:
        """Percentage of runs with successful syntax."""
        if not self.metrics:
            return 0.0
        successes = sum(1 for m in self.metrics if m.parse_success and m.synth_success)
        return (successes / len(self.metrics)) * 100
    
    @property
    def avg_proof_rate(self) -> float:
        """Average proof rate across runs."""
        if not self.metrics:
            return 0.0
        return statistics.mean([m.proof_rate for m in self.metrics])
    
    @property
    def avg_cover_rate(self) -> float:
        """Average cover rate across runs."""
        if not self.metrics:
            return 0.0
        return statistics.mean([m.cover_rate for m in self.metrics])
    
    @property
    def avg_score(self) -> float:
        """Average overall score across runs."""
        if not self.metrics:
            return 0.0
        return statistics.mean([m.overall_score for m in self.metrics])
    
    @property
    def total_assertions(self) -> int:
        """Total assertions across all runs."""
        return sum(m.assertions_found for m in self.metrics)
    
    @property
    def total_proven(self) -> int:
        """Total proven assertions across all runs."""
        return sum(m.assertions_proven for m in self.metrics)
    
    def to_dict(self) -> Dict:
        return {
            "project_name": self.project_name,
            "num_runs": self.num_runs,
            "syntax_success_rate": round(self.syntax_success_rate, 2),
            "avg_proof_rate": round(self.avg_proof_rate, 2),
            "avg_cover_rate": round(self.avg_cover_rate, 2),
            "avg_score": round(self.avg_score, 2),
            "total_assertions": self.total_assertions,
            "total_proven": self.total_proven,
            "runs": [m.to_dict() for m in self.metrics],
        }
    
    def summary(self) -> str:
        """Generate text summary."""
        lines = [
            f"\n{'='*50}",
            f"Project: {self.project_name}",
            f"{'='*50}",
            f"",
            f"Syntax Success Rate: {self.syntax_success_rate:.1f}%",
            f"",
            f"Assertions:",
            f"  Found: {self.total_assertions}",
            f"  Proven: {self.total_proven}",
            f"  Proof Rate: {self.avg_proof_rate:.1f}%",
            f"",
            f"Cover Points:",
            f"  Cover Rate: {self.avg_cover_rate:.1f}%",
            f"",
            f"Overall Score: {self.avg_score:.1f}/100",
        ]
        
        return "\n".join(lines)


def save_results(results: ProjectResults, output_path: Path):
    """Save results to JSON file."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, 'w') as f:
        json.dump(results.to_dict(), f, indent=2)


def print_results_table(results: List[ProjectResults]):
    """Print results in table format."""
    
    print("\n" + "="*70)
    print("FORMAL-EVAL RESULTS (FVEval Methodology)")
    print("="*70)
    
    # Header
    print(f"\n{'Project':<20} {'Syntax':<10} {'Proof%':<12} {'Score':<10}")
    print("-"*60)
    
    total_assertions = 0
    total_proven = 0
    all_scores = []
    
    for r in results:
        syntax_str = f"{r.syntax_success_rate:.0f}%"
        proof_str = f"{r.avg_proof_rate:.1f}%"
        score_str = f"{r.avg_score:.1f}"
        
        print(f"{r.project_name:<20} {syntax_str:<10} {proof_str:<12} {score_str:<10}")
        
        total_assertions += r.total_assertions
        total_proven += r.total_proven
        all_scores.append(r.avg_score)
    
    # Summary row
    print("-"*60)
    overall_proof = (total_proven / total_assertions * 100) if total_assertions > 0 else 0
    overall_score = statistics.mean(all_scores) if all_scores else 0
    print(f"{'OVERALL':<20} {'':<10} {overall_proof:.1f}%{'':<6} {overall_score:.1f}")
    print("="*70)




