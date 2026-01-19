"""
TB-Eval Runner.

Main entry point for testbench evaluation based on VerifLLMBench methodology.
Evaluates existing verification projects (single-file or multi-file).

NO LLM generation - assumes verification files already exist.
"""

import sys
import argparse
from pathlib import Path
from typing import List, Optional

from .config import EvalConfig, VerificationProject, EXAMPLES_DIR, WORK_DIR
from .simulator import Simulator, parse_verification_project, SimulationResult
from .coverage_analyzer import EvalMetrics, ProjectResults, save_results, print_results_table


class TBEvalRunner:
    """
    Main evaluation runner.
    
    Supports both single-file and multi-file verification projects.
    Collects metrics per the VerifLLMBench paper:
    - Build success rate
    - Coverage (line, toggle, branch)
    - Lint errors/warnings
    """
    
    def __init__(self, config: EvalConfig = None):
        self.config = config or EvalConfig()
        self.simulator = Simulator(config=self.config)
    
    def evaluate(self, project_path: Path, num_runs: int = 1) -> ProjectResults:
        """
        Evaluate a verification project.
        
        Args:
            project_path: Path to verification folder
            num_runs: Number of evaluation runs (for consistency checking)
            
        Returns:
            ProjectResults with aggregated metrics
        """
        
        # Parse project structure
        project = parse_verification_project(project_path)
        
        if not project.dut_files:
            raise ValueError(f"No DUT files (.v/.sv) found in {project_path}")
        if not project.tb_files:
            raise ValueError(f"No testbench files (test_*.py) found in {project_path}")
        
        results = ProjectResults(project_name=project.name)
        
        print(f"\n{'='*50}")
        print(f"Evaluating: {project.name}")
        print(f"{'='*50}")
        print(f"  DUT files: {[f.name for f in project.dut_files]}")
        print(f"  TB files: {[f.name for f in project.tb_files]}")
        if project.support_files:
            print(f"  Support files: {[f.name for f in project.support_files]}")
        print(f"  Type: {'Multi-file' if project.is_multi_file else 'Single-file'}")
        
        for run_id in range(1, num_runs + 1):
            if num_runs > 1:
                print(f"\n--- Run {run_id}/{num_runs} ---")
            
            # Run simulation
            sim_result = self.simulator.run(project, run_id)
            
            # Convert to metrics
            metrics = EvalMetrics(
                build_success=sim_result.build_success,
                sim_success=sim_result.sim_success,
                tests_passed=sim_result.tests_passed,
                tests_failed=sim_result.tests_failed,
                tests_total=sim_result.tests_total,
                line_coverage=sim_result.line_coverage,
                toggle_coverage=sim_result.toggle_coverage,
                branch_coverage=sim_result.branch_coverage,
                lint_errors=sim_result.lint_errors,
                lint_warnings=sim_result.lint_warnings,
            )
            
            results.add_run(metrics)
            
            # Print status
            if sim_result.build_success:
                print(f"  ✓ Build successful")
            else:
                print(f"  ✗ Build failed")
                for err in sim_result.build_errors[:3]:
                    print(f"      {err[:80]}")
                continue
            
            if sim_result.sim_success:
                print(f"  ✓ Simulation successful")
                print(f"    Tests: {sim_result.tests_passed}/{sim_result.tests_total} passed")
                print(f"    Coverage: {sim_result.average_coverage:.1f}%")
            else:
                print(f"  ✗ Simulation failed")
                for err in sim_result.sim_errors[:3]:
                    print(f"      {err[:80]}")
        
        return results
    
    def evaluate_multiple(self, project_paths: List[Path], 
                          num_runs: int = 1) -> List[ProjectResults]:
        """Evaluate multiple verification projects."""
        
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
    """CLI entry point for tb_eval."""
    
    parser = argparse.ArgumentParser(
        description="TB-Eval: Testbench Evaluation (VerifLLMBench methodology)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Evaluate a single verification project
  python -m tb_eval.runner --project path/to/verif
  
  # Evaluate with multiple runs for consistency
  python -m tb_eval.runner --project path/to/verif --runs 3
  
  # Evaluate multiple projects
  python -m tb_eval.runner --projects path/to/verif1 path/to/verif2
  
  # Run built-in examples
  python -m tb_eval.runner --examples
        """
    )
    
    parser.add_argument('--project', type=Path,
                        help='Path to verification project folder')
    parser.add_argument('--projects', type=Path, nargs='+',
                        help='Paths to multiple verification projects')
    parser.add_argument('--runs', type=int, default=1,
                        help='Number of evaluation runs (default: 1)')
    parser.add_argument('--examples', action='store_true',
                        help='Run built-in example projects')
    parser.add_argument('--verbose', action='store_true',
                        help='Enable verbose output')
    parser.add_argument('--keep-work', action='store_true',
                        help='Keep work directory after evaluation')
    parser.add_argument('--output', type=Path,
                        help='Output directory for results JSON')
    
    args = parser.parse_args()
    
    # Build config
    config = EvalConfig(
        verbose=args.verbose,
        keep_work_dir=args.keep_work,
    )
    
    runner = TBEvalRunner(config=config)
    
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
            output_path = args.output / f"{r.project_name}_results.json"
            save_results(r, output_path)
            print(f"\nResults saved to: {output_path}")


if __name__ == '__main__':
    main()
