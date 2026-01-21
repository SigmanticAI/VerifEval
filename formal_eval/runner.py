"""
Formal-Eval Runner.

Main entry point for formal verification evaluation.
Evaluates existing SVA-based verification projects.

NO LLM generation - assumes formal verification files already exist.
"""

import sys
import argparse
from pathlib import Path
from typing import List

from .config import FormalConfig, FormalProject, EXAMPLES_DIR, WORK_DIR
from .checker import FormalChecker, parse_formal_project, FormalResult
from .analyzer import FormalMetrics, ProjectResults, save_results, print_results_table


class FormalEvalRunner:
    """
    Main formal verification evaluation runner.
    
    Supports both single-file and multi-file SVA projects.
    Collects metrics based on FVEval paper:
    - Syntax success rate
    - Proof rate (assertions proven)
    - Cover rate (cover points reached)
    """
    
    def __init__(self, config: FormalConfig = None):
        self.config = config or FormalConfig()
        self.checker = FormalChecker(config=self.config)
    
    def evaluate(self, project_path: Path, num_runs: int = 1) -> ProjectResults:
        """
        Evaluate a formal verification project.
        
        Args:
            project_path: Path to verification folder
            num_runs: Number of evaluation runs
            
        Returns:
            ProjectResults with aggregated metrics
        """
        
        # Parse project structure
        project = parse_formal_project(project_path)
        
        if not project.design_files and not project.assertion_files:
            raise ValueError(f"No Verilog/SystemVerilog files found in {project_path}")
        
        results = ProjectResults(project_name=project.name)
        
        print(f"\n{'='*50}")
        print(f"Evaluating: {project.name}")
        print(f"{'='*50}")
        print(f"  Design files: {[f.name for f in project.design_files]}")
        print(f"  Assertion files: {[f.name for f in project.assertion_files]}")
        print(f"  Type: {'Multi-file' if project.is_multi_file else 'Single-file'}")
        
        for run_id in range(1, num_runs + 1):
            if num_runs > 1:
                print(f"\n--- Run {run_id}/{num_runs} ---")
            
            # Run formal verification
            formal_result = self.checker.check(project, run_id)
            
            # Convert to metrics
            metrics = FormalMetrics(
                parse_success=formal_result.parse_success,
                synth_success=formal_result.synth_success,
                synth_warnings=formal_result.synth_warnings,
                assertions_found=formal_result.assertions_found,
                assertions_proven=formal_result.assertions_proven,
                assertions_failed=formal_result.assertions_failed,
                assertions_unknown=formal_result.assertions_unknown,
                cover_points_found=formal_result.cover_points_found,
                cover_points_reached=formal_result.cover_points_reached,
            )
            
            results.add_run(metrics)
            
            # Print status
            if formal_result.parse_success:
                print(f"  ✓ Parse successful")
            else:
                print(f"  ✗ Parse failed")
                for err in formal_result.parse_errors[:3]:
                    print(f"      {err[:80]}")
                continue
            
            if formal_result.synth_success:
                print(f"  ✓ Synthesis successful")
            else:
                print(f"  ✗ Synthesis failed")
                for err in formal_result.synth_errors[:3]:
                    print(f"      {err[:80]}")
                continue
            
            # Print formal results
            print(f"  Assertions: {formal_result.assertions_found} found")
            if formal_result.assertions_proven > 0:
                print(f"    ✓ {formal_result.assertions_proven} proven")
            if formal_result.assertions_failed > 0:
                print(f"    ✗ {formal_result.assertions_failed} failed")
            if formal_result.assertions_unknown > 0:
                print(f"    ? {formal_result.assertions_unknown} unknown")
            
            print(f"  Proof Rate: {formal_result.proof_rate:.1f}%")
            print(f"  Score: {metrics.overall_score:.1f}/100")
        
        return results
    
    def evaluate_multiple(self, project_paths: List[Path], 
                          num_runs: int = 1) -> List[ProjectResults]:
        """Evaluate multiple formal verification projects."""
        
        all_results = []
        
        for path in project_paths:
            try:
                results = self.evaluate(path, num_runs)
                all_results.append(results)
                print(results.summary())
            except Exception as e:
                print(f"\n✗ Error evaluating {path}: {e}")
        
        return all_results


def main():
    """CLI entry point for formal_eval."""
    
    parser = argparse.ArgumentParser(
        description="Formal-Eval: Formal Verification Evaluation (FVEval methodology)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Evaluate a single formal verification project
  python -m formal_eval.runner --project path/to/verif
  
  # Evaluate with multiple runs
  python -m formal_eval.runner --project path/to/verif --runs 3
  
  # Evaluate multiple projects
  python -m formal_eval.runner --projects path/to/proj1 path/to/proj2
  
  # Run built-in examples
  python -m formal_eval.runner --examples
        """
    )
    
    parser.add_argument('--project', type=Path,
                        help='Path to formal verification project folder')
    parser.add_argument('--projects', type=Path, nargs='+',
                        help='Paths to multiple formal verification projects')
    parser.add_argument('--runs', type=int, default=1,
                        help='Number of evaluation runs (default: 1)')
    parser.add_argument('--examples', action='store_true',
                        help='Run built-in example projects')
    parser.add_argument('--verbose', action='store_true',
                        help='Enable verbose output')
    parser.add_argument('--keep-work', action='store_true',
                        help='Keep work directory after evaluation')
    parser.add_argument('--depth', type=int, default=20,
                        help='Bounded model checking depth (default: 20)')
    parser.add_argument('--output', type=Path,
                        help='Output directory for results JSON')
    
    args = parser.parse_args()
    
    # Build config
    config = FormalConfig(
        verbose=args.verbose,
        keep_work_dir=args.keep_work,
        bounded_depth=args.depth,
    )
    
    runner = FormalEvalRunner(config=config)
    
    # Determine what to evaluate
    if args.examples:
        # Run built-in examples
        if not EXAMPLES_DIR.exists():
            print(f"Examples directory not found: {EXAMPLES_DIR}")
            sys.exit(1)
        
        example_dirs = [d for d in EXAMPLES_DIR.iterdir() if d.is_dir()]
        if not example_dirs:
            print("No example projects found")
            sys.exit(1)
        
        results = runner.evaluate_multiple(example_dirs, args.runs)
        
    elif args.project:
        results = [runner.evaluate(args.project, args.runs)]
        
    elif args.projects:
        results = runner.evaluate_multiple(args.projects, args.runs)
        
    else:
        parser.print_help()
        print("\nError: Specify --project, --projects, or --examples")
        sys.exit(1)
    
    # Print summary table
    print_results_table(results)
    
    # Save results if requested
    if args.output:
        for r in results:
            output_path = args.output / f"{r.project_name}_formal_results.json"
            save_results(r, output_path)
            print(f"\nResults saved to: {output_path}")


if __name__ == '__main__':
    main()


