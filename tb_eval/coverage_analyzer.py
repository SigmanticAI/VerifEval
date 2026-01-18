"""
Coverage analysis and metrics computation.

Implements the coverage metrics from the VerifLLMBench paper:
- Line coverage
- Toggle coverage
- Branch coverage
- FSM coverage
- Conditional coverage
- Group (functional) coverage
"""

import json
from pathlib import Path
from dataclasses import dataclass, field
from typing import Dict, List, Optional
import statistics


@dataclass
class CoverageMetrics:
    """Coverage metrics for a single simulation run."""
    line: float = 0.0
    toggle: float = 0.0
    branch: float = 0.0
    conditional: float = 0.0
    fsm: float = 0.0
    group: float = 0.0
    
    def average(self) -> float:
        """Calculate average coverage excluding zeros (as per paper)."""
        values = [v for v in [self.line, self.toggle, self.branch, 
                              self.conditional, self.fsm, self.group] if v > 0]
        return statistics.mean(values) if values else 0.0
    
    def to_dict(self) -> Dict[str, float]:
        return {
            "line": self.line,
            "toggle": self.toggle,
            "branch": self.branch,
            "conditional": self.conditional,
            "fsm": self.fsm,
            "group": self.group,
            "average": self.average()
        }


@dataclass
class DesignMetrics:
    """Aggregated metrics for a design across multiple runs."""
    design_name: str
    num_runs: int = 0
    build_successes: int = 0
    sim_successes: int = 0
    
    # Coverage stats (min, max, avg)
    coverage_runs: List[CoverageMetrics] = field(default_factory=list)
    
    # Lint stats
    lint_errors: List[int] = field(default_factory=list)
    lint_warnings: List[int] = field(default_factory=list)
    
    @property
    def build_success_rate(self) -> float:
        return (self.build_successes / self.num_runs * 100) if self.num_runs > 0 else 0.0
    
    @property  
    def sim_success_rate(self) -> float:
        return (self.sim_successes / self.num_runs * 100) if self.num_runs > 0 else 0.0
    
    def get_coverage_stats(self, metric: str) -> Dict[str, float]:
        """Get min, max, avg for a coverage metric."""
        values = [getattr(c, metric) for c in self.coverage_runs if getattr(c, metric) > 0]
        
        if not values:
            return {"min": 0.0, "max": 0.0, "avg": 0.0}
        
        return {
            "min": min(values),
            "max": max(values),
            "avg": statistics.mean(values)
        }
    
    def get_lint_stats(self) -> Dict[str, float]:
        """Get average lint errors and warnings."""
        return {
            "avg_errors": statistics.mean(self.lint_errors) if self.lint_errors else 0.0,
            "avg_warnings": statistics.mean(self.lint_warnings) if self.lint_warnings else 0.0
        }
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "design_name": self.design_name,
            "num_runs": self.num_runs,
            "build_success_rate": self.build_success_rate,
            "sim_success_rate": self.sim_success_rate,
            "coverage": {
                "line": self.get_coverage_stats("line"),
                "toggle": self.get_coverage_stats("toggle"),
                "branch": self.get_coverage_stats("branch"),
                "conditional": self.get_coverage_stats("conditional"),
                "fsm": self.get_coverage_stats("fsm"),
                "group": self.get_coverage_stats("group"),
                "overall_average": statistics.mean([c.average() for c in self.coverage_runs]) 
                    if self.coverage_runs else 0.0
            },
            "lint": self.get_lint_stats()
        }


@dataclass
class BenchmarkResults:
    """Overall benchmark results across all designs and LLMs."""
    llm_provider: str
    designs: Dict[str, DesignMetrics] = field(default_factory=dict)
    
    def add_design_result(self, metrics: DesignMetrics):
        """Add results for a design."""
        self.designs[metrics.design_name] = metrics
    
    def get_overall_build_rate(self) -> float:
        """Get overall build success rate."""
        total_runs = sum(d.num_runs for d in self.designs.values())
        total_success = sum(d.build_successes for d in self.designs.values())
        return (total_success / total_runs * 100) if total_runs > 0 else 0.0
    
    def get_overall_coverage(self) -> float:
        """Get overall average coverage across all designs."""
        all_averages = []
        for design in self.designs.values():
            for cov in design.coverage_runs:
                avg = cov.average()
                if avg > 0:
                    all_averages.append(avg)
        return statistics.mean(all_averages) if all_averages else 0.0
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "llm_provider": self.llm_provider,
            "overall_build_rate": self.get_overall_build_rate(),
            "overall_coverage": self.get_overall_coverage(),
            "designs": {name: metrics.to_dict() for name, metrics in self.designs.items()}
        }
    
    def to_markdown_table(self) -> str:
        """Generate markdown table like in the paper (Table III)."""
        
        header = "| Design | Build | Coverage | Lint Errors/Warnings |"
        separator = "|--------|-------|----------|----------------------|"
        
        rows = []
        for name, metrics in sorted(self.designs.items()):
            build = f"{metrics.build_successes}/{metrics.num_runs}"
            
            # Get average coverage
            if metrics.coverage_runs:
                avg_cov = statistics.mean([c.average() for c in metrics.coverage_runs])
                coverage = f"{avg_cov:.1f}%"
            else:
                coverage = "N/A"
            
            lint_stats = metrics.get_lint_stats()
            lint = f"{lint_stats['avg_errors']:.0f}/{lint_stats['avg_warnings']:.0f}"
            
            rows.append(f"| {name} | {build} | {coverage} | {lint} |")
        
        # Add average row
        avg_build = f"{self.get_overall_build_rate():.0f}%"
        avg_cov = f"{self.get_overall_coverage():.1f}%"
        all_errors = sum(sum(d.lint_errors) for d in self.designs.values())
        all_warnings = sum(sum(d.lint_warnings) for d in self.designs.values())
        total_runs = sum(d.num_runs for d in self.designs.values())
        avg_lint = f"{all_errors/total_runs:.1f}/{all_warnings/total_runs:.1f}" if total_runs > 0 else "N/A"
        
        rows.append(f"| **Average** | {avg_build} | {avg_cov} | {avg_lint} |")
        
        return "\n".join([header, separator] + rows)


def save_results(results: BenchmarkResults, output_dir: Path) -> Path:
    """Save benchmark results to files."""
    
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Save JSON
    json_path = output_dir / f"results_{results.llm_provider}.json"
    with open(json_path, 'w') as f:
        json.dump(results.to_dict(), f, indent=2)
    
    # Save markdown report
    md_path = output_dir / f"results_{results.llm_provider}.md"
    md_content = f"""# TB-Eval Benchmark Results

## LLM Provider: {results.llm_provider}

### Summary
- Overall Build Success Rate: {results.get_overall_build_rate():.1f}%
- Overall Average Coverage: {results.get_overall_coverage():.1f}%

### Results by Design

{results.to_markdown_table()}

### Detailed Coverage Metrics

"""
    
    for name, metrics in sorted(results.designs.items()):
        md_content += f"\n#### {name}\n\n"
        md_content += "| Metric | Min | Max | Avg |\n"
        md_content += "|--------|-----|-----|-----|\n"
        
        for metric in ["line", "toggle", "branch", "conditional", "fsm", "group"]:
            stats = metrics.get_coverage_stats(metric)
            md_content += f"| {metric.capitalize()} | {stats['min']:.1f}% | {stats['max']:.1f}% | {stats['avg']:.1f}% |\n"
    
    md_path.write_text(md_content)
    
    print(f"\nResults saved to:")
    print(f"  - {json_path}")
    print(f"  - {md_path}")
    
    return json_path


def load_results(json_path: Path) -> BenchmarkResults:
    """Load benchmark results from JSON."""
    
    with open(json_path) as f:
        data = json.load(f)
    
    results = BenchmarkResults(llm_provider=data["llm_provider"])
    
    for name, design_data in data.get("designs", {}).items():
        metrics = DesignMetrics(
            design_name=name,
            num_runs=design_data.get("num_runs", 0),
            build_successes=int(design_data.get("build_success_rate", 0) * design_data.get("num_runs", 0) / 100),
            sim_successes=int(design_data.get("sim_success_rate", 0) * design_data.get("num_runs", 0) / 100),
        )
        results.add_design_result(metrics)
    
    return results


def compare_results(results_list: List[BenchmarkResults]) -> str:
    """Generate comparison table across multiple LLMs."""
    
    # Get all design names
    all_designs = set()
    for results in results_list:
        all_designs.update(results.designs.keys())
    
    # Generate comparison table
    llm_names = [r.llm_provider for r in results_list]
    
    header = "| Design | " + " | ".join(f"{name} (Build/Cov/Lint)" for name in llm_names) + " |"
    separator = "|--------| " + " | ".join(["---"] * len(llm_names)) + " |"
    
    rows = []
    for design in sorted(all_designs):
        row_parts = [design]
        for results in results_list:
            if design in results.designs:
                metrics = results.designs[design]
                build = f"{metrics.build_successes}/{metrics.num_runs}"
                
                if metrics.coverage_runs:
                    avg_cov = statistics.mean([c.average() for c in metrics.coverage_runs])
                    coverage = f"{avg_cov:.1f}%"
                else:
                    coverage = "N/A"
                
                lint_stats = metrics.get_lint_stats()
                lint = f"{lint_stats['avg_errors']:.0f}/{lint_stats['avg_warnings']:.0f}"
                
                row_parts.append(f"{build} / {coverage} / {lint}")
            else:
                row_parts.append("N/A")
        
        rows.append("| " + " | ".join(row_parts) + " |")
    
    return "\n".join([header, separator] + rows)

