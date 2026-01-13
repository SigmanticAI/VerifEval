#!/usr/bin/env python3
"""
Scoring and reporting system for benchmark results.
Generates comparison reports and visualizations.
"""

import json
import argparse
from pathlib import Path
from typing import Dict, List
from collections import defaultdict
import sys


class BenchmarkScorer:
    """Analyzes and reports on benchmark results."""
    
    def __init__(self, results_dir: Path):
        self.results_dir = results_dir
    
    def load_results(self) -> Dict[str, List[Dict]]:
        """Load all result files organized by design."""
        results_by_design = defaultdict(list)
        
        for result_file in self.results_dir.glob('*.json'):
            try:
                with open(result_file) as f:
                    result = json.load(f)
                    design_name = result['design_name']
                    result['_file'] = result_file.name
                    results_by_design[design_name].append(result)
            except Exception as e:
                print(f"Warning: Failed to load {result_file}: {e}")
        
        # Sort by timestamp (newest first)
        for design in results_by_design:
            results_by_design[design].sort(
                key=lambda r: r['_file'], 
                reverse=True
            )
        
        return dict(results_by_design)
    
    def generate_report(self, output_file: Path = None):
        """Generate comprehensive benchmark report."""
        results = self.load_results()
        
        if not results:
            print("No results found to report.")
            return
        
        report = self._build_report(results)
        
        # Print to console
        print(report)
        
        # Save to file if requested
        if output_file:
            output_file.write_text(report)
            print(f"\nReport saved to: {output_file}")
    
    def _build_report(self, results: Dict[str, List[Dict]]) -> str:
        """Build formatted report text."""
        lines = []
        
        # Header
        lines.append("=" * 80)
        lines.append("VERIFAGENT BENCHMARK REPORT")
        lines.append("=" * 80)
        lines.append("")
        
        # Overall statistics
        lines.append("OVERALL STATISTICS")
        lines.append("-" * 80)
        
        all_scores = []
        all_dimension_scores = defaultdict(list)
        
        for design_name, design_results in results.items():
            # Use most recent result
            latest = design_results[0]
            all_scores.append(latest['total_score'])
            
            for dim, score in latest['dimension_scores'].items():
                all_dimension_scores[dim].append(score)
        
        if all_scores:
            avg_score = sum(all_scores) / len(all_scores)
            lines.append(f"Designs Evaluated: {len(results)}")
            lines.append(f"Average Score: {avg_score:.2f} / 100")
            lines.append(f"Best Score: {max(all_scores):.2f}")
            lines.append(f"Worst Score: {min(all_scores):.2f}")
            lines.append("")
        
        # Dimension breakdown
        lines.append("DIMENSION SCORES (Average)")
        lines.append("-" * 80)
        
        for dim_name, scores in all_dimension_scores.items():
            avg = sum(scores) / len(scores) if scores else 0
            lines.append(f"{dim_name.replace('_', ' ').title():<40} {avg:>8.2f} / 25.00")
        lines.append("")
        
        # Per-design results
        lines.append("PER-DESIGN RESULTS")
        lines.append("-" * 80)
        
        for design_name in sorted(results.keys()):
            design_results = results[design_name]
            latest = design_results[0]
            
            lines.append(f"\n{design_name.upper()}")
            lines.append("  " + "-" * 76)
            lines.append(f"  Total Score: {latest['total_score']:.2f} / {latest['max_score']}")
            
            # Dimension scores
            lines.append("  Dimension Breakdown:")
            for dim, score in latest['dimension_scores'].items():
                lines.append(f"    - {dim.replace('_', ' ').title():<35} {score:>6.2f} / 25.00")
            
            # Bug detection
            if latest['bug_detection']['total'] > 0:
                bd = latest['bug_detection']
                lines.append(f"  Bug Detection: {bd['detected']}/{bd['total']} (bonus: +{bd['bonus_score']:.2f})")
            
            # Errors and warnings
            if latest['errors']:
                lines.append("  Errors:")
                for error in latest['errors']:
                    lines.append(f"    ✗ {error}")
            
            if latest['warnings']:
                lines.append("  Warnings:")
                for warning in latest['warnings']:
                    lines.append(f"    ⚠ {warning}")
            
            # Detailed metrics
            if latest.get('metrics'):
                lines.append("  Detailed Metrics:")
                self._append_metrics(lines, latest['metrics'], indent=4)
        
        lines.append("")
        lines.append("=" * 80)
        
        return "\n".join(lines)
    
    def _append_metrics(self, lines: List[str], metrics: Dict, indent: int = 0):
        """Recursively append metrics to report."""
        prefix = " " * indent
        
        for key, value in metrics.items():
            if isinstance(value, dict):
                lines.append(f"{prefix}{key}:")
                self._append_metrics(lines, value, indent + 2)
            elif isinstance(value, list):
                if len(value) <= 5:
                    lines.append(f"{prefix}{key}: {value}")
                else:
                    lines.append(f"{prefix}{key}: [{len(value)} items]")
            else:
                lines.append(f"{prefix}{key}: {value}")
    
    def compare_runs(self, design_name: str):
        """Compare multiple runs of the same design."""
        results = self.load_results()
        
        if design_name not in results:
            print(f"No results found for design: {design_name}")
            return
        
        design_results = results[design_name]
        
        if len(design_results) < 2:
            print(f"Only one run found for {design_name}")
            return
        
        print(f"\nCOMPARISON: {design_name}")
        print("=" * 80)
        print(f"\n{'Run':<30} {'Score':>10} {'Spec':>8} {'Plan':>8} {'Code':>8} {'Comp':>8}")
        print("-" * 80)
        
        for i, result in enumerate(design_results):
            dims = result['dimension_scores']
            print(f"{result['_file']:<30} "
                  f"{result['total_score']:>10.2f} "
                  f"{dims['specification_extraction']:>8.2f} "
                  f"{dims['verification_planning']:>8.2f} "
                  f"{dims['code_generation']:>8.2f} "
                  f"{dims['verification_completeness']:>8.2f}")
        
        print("=" * 80 + "\n")
    
    def leaderboard(self):
        """Show leaderboard of designs by score."""
        results = self.load_results()
        
        if not results:
            print("No results to display.")
            return
        
        # Get latest result for each design
        scores = []
        for design_name, design_results in results.items():
            latest = design_results[0]
            scores.append((design_name, latest['total_score']))
        
        # Sort by score descending
        scores.sort(key=lambda x: x[1], reverse=True)
        
        print("\nLEADERBOARD")
        print("=" * 80)
        print(f"{'Rank':<6} {'Design':<40} {'Score':>10} {'Grade':>10}")
        print("-" * 80)
        
        for i, (design_name, score) in enumerate(scores, 1):
            grade = self._get_grade(score)
            print(f"{i:<6} {design_name:<40} {score:>10.2f} {grade:>10}")
        
        print("=" * 80 + "\n")
    
    def _get_grade(self, score: float) -> str:
        """Convert score to letter grade."""
        if score >= 90:
            return "A"
        elif score >= 80:
            return "B"
        elif score >= 70:
            return "C"
        elif score >= 60:
            return "D"
        else:
            return "F"


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description='Analyze benchmark results')
    parser.add_argument('--results-dir', type=Path,
                       default=Path(__file__).parent.parent / 'results',
                       help='Results directory')
    parser.add_argument('--report', action='store_true',
                       help='Generate full report')
    parser.add_argument('--leaderboard', action='store_true',
                       help='Show leaderboard')
    parser.add_argument('--compare', type=str,
                       help='Compare runs for specific design')
    parser.add_argument('--output', type=Path,
                       help='Output file for report')
    
    args = parser.parse_args()
    
    scorer = BenchmarkScorer(args.results_dir)
    
    if args.report:
        scorer.generate_report(args.output)
    elif args.leaderboard:
        scorer.leaderboard()
    elif args.compare:
        scorer.compare_runs(args.compare)
    else:
        # Default: show leaderboard
        scorer.leaderboard()


if __name__ == '__main__':
    main()

