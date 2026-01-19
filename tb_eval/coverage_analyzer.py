"""
Coverage analysis and metrics for TB-Eval.

Implements the metrics from the VerifLLMBench paper:
- Build success rate
- Coverage metrics (line, toggle, branch)
- Lint errors/warnings
"""

import json
import statistics
from pathlib import Path
from dataclasses import dataclass, field
from typing import Dict, List, Optional


@dataclass
class EvalMetrics:
    """Metrics for a single evaluation run."""
    
    # Build/Sim status
    build_success: bool = False
    sim_success: bool = False
    
    # Test results
    tests_passed: int = 0
    tests_failed: int = 0
    tests_total: int = 0
    
    # Coverage (percentages)
    line_coverage: float = 0.0
    toggle_coverage: float = 0.0
    branch_coverage: float = 0.0
    
    # Lint
    lint_errors: int = 0
    lint_warnings: int = 0
    
    @property
    def average_coverage(self) -> float:
        """Average of non-zero coverage metrics (as per paper)."""
        values = [v for v in [self.line_coverage, self.toggle_coverage, 
                              self.branch_coverage] if v > 0]
        return statistics.mean(values) if values else 0.0
    
    def to_dict(self) -> Dict:
        return {
            "build_success": self.build_success,
            "sim_success": self.sim_success,
            "tests_passed": self.tests_passed,
            "tests_failed": self.tests_failed,
            "tests_total": self.tests_total,
            "line_coverage": round(self.line_coverage, 2),
            "toggle_coverage": round(self.toggle_coverage, 2),
            "branch_coverage": round(self.branch_coverage, 2),
            "average_coverage": round(self.average_coverage, 2),
            "lint_errors": self.lint_errors,
            "lint_warnings": self.lint_warnings,
        }


@dataclass
class ProjectResults:
    """Aggregated results for a verification project across multiple runs."""
    
    project_name: str
    num_runs: int = 0
    metrics: List[EvalMetrics] = field(default_factory=list)
    
    def add_run(self, metric: EvalMetrics):
        """Add a run's metrics."""
        self.metrics.append(metric)
        self.num_runs = len(self.metrics)
    
    @property
    def build_success_rate(self) -> float:
        """Percentage of runs with successful build."""
        if not self.metrics:
            return 0.0
        successes = sum(1 for m in self.metrics if m.build_success)
        return (successes / len(self.metrics)) * 100
    
    @property
    def sim_success_rate(self) -> float:
        """Percentage of runs with successful simulation."""
        if not self.metrics:
            return 0.0
        successes = sum(1 for m in self.metrics if m.sim_success)
        return (successes / len(self.metrics)) * 100
    
    @property
    def avg_coverage(self) -> float:
        """Average coverage across successful runs."""
        coverages = [m.average_coverage for m in self.metrics if m.sim_success]
        return statistics.mean(coverages) if coverages else 0.0
    
    @property
    def avg_lint_errors(self) -> float:
        """Average lint errors."""
        if not self.metrics:
            return 0.0
        return statistics.mean([m.lint_errors for m in self.metrics])
    
    @property
    def avg_lint_warnings(self) -> float:
        """Average lint warnings."""
        if not self.metrics:
            return 0.0
        return statistics.mean([m.lint_warnings for m in self.metrics])
    
    def get_coverage_stats(self, metric: str) -> Dict[str, float]:
        """Get min/max/avg for a specific coverage metric."""
        values = [getattr(m, metric) for m in self.metrics if getattr(m, metric) > 0]
        if not values:
            return {"min": 0.0, "max": 0.0, "avg": 0.0}
        return {
            "min": min(values),
            "max": max(values),
            "avg": statistics.mean(values),
        }
    
    def to_dict(self) -> Dict:
        return {
            "project_name": self.project_name,
            "num_runs": self.num_runs,
            "build_success_rate": round(self.build_success_rate, 2),
            "sim_success_rate": round(self.sim_success_rate, 2),
            "coverage": {
                "line": self.get_coverage_stats("line_coverage"),
                "toggle": self.get_coverage_stats("toggle_coverage"),
                "branch": self.get_coverage_stats("branch_coverage"),
                "average": round(self.avg_coverage, 2),
            },
            "lint": {
                "avg_errors": round(self.avg_lint_errors, 2),
                "avg_warnings": round(self.avg_lint_warnings, 2),
            },
            "runs": [m.to_dict() for m in self.metrics],
        }
    
    def summary(self) -> str:
        """Generate text summary."""
        lines = [
            f"\n{'='*50}",
            f"Project: {self.project_name}",
            f"{'='*50}",
            f"",
            f"Build Success Rate: {self.build_success_rate:.1f}%",
            f"Simulation Success Rate: {self.sim_success_rate:.1f}%",
            f"",
            f"Coverage (avg of successful runs):",
            f"  Line:   {self.get_coverage_stats('line_coverage')['avg']:.1f}%",
            f"  Toggle: {self.get_coverage_stats('toggle_coverage')['avg']:.1f}%",
            f"  Branch: {self.get_coverage_stats('branch_coverage')['avg']:.1f}%",
            f"  Overall Average: {self.avg_coverage:.1f}%",
            f"",
            f"Lint: {self.avg_lint_errors:.1f} errors, {self.avg_lint_warnings:.1f} warnings (avg)",
        ]
        
        # Test summary
        total_tests = sum(m.tests_total for m in self.metrics if m.sim_success)
        passed_tests = sum(m.tests_passed for m in self.metrics if m.sim_success)
        if total_tests > 0:
            lines.append(f"")
            lines.append(f"Tests: {passed_tests}/{total_tests} passed across all runs")
        
        return "\n".join(lines)


def save_results(results: ProjectResults, output_path: Path):
    """Save results to JSON file."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, 'w') as f:
        json.dump(results.to_dict(), f, indent=2)


def print_results_table(results: List[ProjectResults]):
    """Print results in table format like the paper."""
    
    print("\n" + "="*70)
    print("TB-EVAL RESULTS (VerifLLMBench Methodology)")
    print("="*70)
    
    # Header
    print(f"\n{'Project':<20} {'Build':<10} {'Coverage':<12} {'Lint (E/W)':<12}")
    print("-"*60)
    
    total_builds = 0
    total_runs = 0
    all_coverages = []
    
    for r in results:
        build_str = f"{r.build_success_rate:.0f}%"
        cov_str = f"{r.avg_coverage:.1f}%" if r.avg_coverage > 0 else "N/A"
        lint_str = f"{r.avg_lint_errors:.0f}/{r.avg_lint_warnings:.0f}"
        
        print(f"{r.project_name:<20} {build_str:<10} {cov_str:<12} {lint_str:<12}")
        
        total_builds += sum(1 for m in r.metrics if m.build_success)
        total_runs += r.num_runs
        if r.avg_coverage > 0:
            all_coverages.append(r.avg_coverage)
    
    # Summary row
    print("-"*60)
    overall_build = (total_builds / total_runs * 100) if total_runs > 0 else 0
    overall_cov = statistics.mean(all_coverages) if all_coverages else 0
    print(f"{'OVERALL':<20} {overall_build:.0f}%{'':<5} {overall_cov:.1f}%")
    print("="*70)
