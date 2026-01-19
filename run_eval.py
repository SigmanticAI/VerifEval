#!/usr/bin/env python3
"""
VerifEval - Unified Evaluation Runner

Evaluation modes:
- spec_eval: Original specification-based evaluation (existing)
- tb_eval: Testbench evaluation (VerifLLMBench methodology)

Usage:
    python run_eval.py --eval tb_eval --project tb_eval/examples/adder_single
    python run_eval.py --eval tb_eval --examples
    python run_eval.py --eval spec_eval --design fifo_sync
"""

import sys
import argparse
from pathlib import Path


def run_spec_eval(args):
    """Run the original specification-based evaluation."""
    sys.path.insert(0, str(Path(__file__).parent))
    
    from evaluator.runner import BenchmarkRunner
    
    benchmark_root = Path(__file__).parent
    results_dir = benchmark_root / 'results'
    
    runner = BenchmarkRunner(benchmark_root, results_dir)
    
    if args.all:
        runner.run_all(regenerate=args.regenerate)
    elif args.design:
        runner.run_design(args.design, regenerate=args.regenerate)
    else:
        print("Error: Please specify --all or --design for spec_eval")
        sys.exit(1)


def run_tb_eval(args):
    """
    Run testbench evaluation (VerifLLMBench methodology).
    
    Evaluates existing verification projects - NO LLM generation.
    Supports both single-file and multi-file verification.
    """
    sys.path.insert(0, str(Path(__file__).parent))
    
    from tb_eval.runner import TBEvalRunner
    from tb_eval.config import EvalConfig, EXAMPLES_DIR
    from tb_eval.coverage_analyzer import print_results_table
    
    config = EvalConfig(
        verbose=args.verbose,
        keep_work_dir=args.keep_work,
    )
    
    runner = TBEvalRunner(config=config)
    
    if args.examples:
        # Run built-in examples
        if not EXAMPLES_DIR.exists():
            print(f"Error: Examples directory not found: {EXAMPLES_DIR}")
            sys.exit(1)
        
        example_dirs = [d for d in EXAMPLES_DIR.iterdir() if d.is_dir()]
        if not example_dirs:
            print("Error: No example projects found")
            sys.exit(1)
        
        results = runner.evaluate_multiple(example_dirs, args.runs)
        
    elif args.project:
        project_path = Path(args.project)
        if not project_path.exists():
            print(f"Error: Project not found: {project_path}")
            sys.exit(1)
        results = [runner.evaluate(project_path, args.runs)]
        
    elif args.projects:
        project_paths = [Path(p) for p in args.projects]
        for p in project_paths:
            if not p.exists():
                print(f"Error: Project not found: {p}")
                sys.exit(1)
        results = runner.evaluate_multiple(project_paths, args.runs)
        
    else:
        print("Error: Please specify --project, --projects, or --examples for tb_eval")
        print("\nExample usage:")
        print("  python run_eval.py --eval tb_eval --examples")
        print("  python run_eval.py --eval tb_eval --project tb_eval/examples/adder_single")
        sys.exit(1)
    
    # Print summary table
    print_results_table(results)
    
    # Return success based on build rate
    total_success = sum(1 for r in results if r.build_success_rate == 100)
    return total_success == len(results)


def main():
    parser = argparse.ArgumentParser(
        description="VerifEval - Unified Evaluation Runner",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Evaluation Modes:
  spec_eval   - Specification-based evaluation
                Evaluates verification output against design specs
               
  tb_eval     - Testbench evaluation (VerifLLMBench methodology)
                Evaluates existing verification projects
                Measures: build success, coverage, lint
                Uses: cocotb + Verilator (open-source)

Examples:
  # Run built-in examples
  python run_eval.py --eval tb_eval --examples
  
  # Evaluate single-file verification project
  python run_eval.py --eval tb_eval --project tb_eval/examples/adder_single
  
  # Evaluate multi-file verification project
  python run_eval.py --eval tb_eval --project tb_eval/examples/fifo_multi
  
  # Evaluate multiple projects
  python run_eval.py --eval tb_eval --projects proj1/ proj2/
  
  # Run with multiple iterations for consistency
  python run_eval.py --eval tb_eval --project my_verif/ --runs 3
  
  # Run specification evaluation (original mode)
  python run_eval.py --eval spec_eval --design fifo_sync
        """
    )
    
    # Common arguments
    parser.add_argument('--eval', type=str, required=True,
                       choices=['spec_eval', 'tb_eval'],
                       help='Evaluation mode to run')
    
    # tb_eval arguments
    parser.add_argument('--project', type=str,
                       help='Path to verification project folder (tb_eval)')
    parser.add_argument('--projects', type=str, nargs='+',
                       help='Paths to multiple verification projects (tb_eval)')
    parser.add_argument('--examples', action='store_true',
                       help='Run built-in example projects (tb_eval)')
    parser.add_argument('--runs', type=int, default=1,
                       help='Number of evaluation runs (default: 1)')
    parser.add_argument('--verbose', action='store_true',
                       help='Enable verbose output')
    parser.add_argument('--keep-work', action='store_true',
                       help='Keep work directory after evaluation')
    
    # spec_eval arguments
    parser.add_argument('--all', action='store_true',
                       help='Run on all designs (spec_eval)')
    parser.add_argument('--design', type=str,
                       help='Run on specific design (spec_eval)')
    parser.add_argument('--regenerate', action='store_true',
                       help='Regenerate verification (spec_eval)')
    
    args = parser.parse_args()
    
    # Run the selected evaluation
    if args.eval == 'tb_eval':
        success = run_tb_eval(args)
        sys.exit(0 if success else 1)
    else:
        run_spec_eval(args)


if __name__ == '__main__':
    main()
