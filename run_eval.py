#!/usr/bin/env python3
"""
VerifEval - Unified Evaluation Runner

Allows selection between different evaluation modes:
- spec_eval: Original specification-based evaluation (existing)
- tb_eval: Testbench generation benchmark (VerifLLMBench methodology)
- folder_eval: Evaluate a folder containing verification files

Usage:
    python run_eval.py --eval tb_eval --all
    python run_eval.py --eval spec_eval --design fifo_sync
    python run_eval.py --eval folder_eval --folder path/to/verif
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
    """Run the testbench generation benchmark (VerifLLMBench methodology)."""
    sys.path.insert(0, str(Path(__file__).parent))
    
    from tb_eval.runner import TBEvalRunner
    from tb_eval.config import BenchmarkConfig, get_all_design_names
    
    config = BenchmarkConfig(
        max_iterations=args.max_iterations,
        num_test_runs=args.runs
    )
    
    runner = TBEvalRunner(config=config, llm_provider=args.llm)
    
    if args.all:
        runner.run_all(num_runs=args.runs)
    elif args.designs:
        runner.run_all(designs=args.designs, num_runs=args.runs)
    elif args.design:
        runner.run_all(designs=[args.design], num_runs=args.runs)
    else:
        print("Error: Please specify --all, --design, or --designs for tb_eval")
        print(f"Available designs: {', '.join(get_all_design_names())}")
        sys.exit(1)


def run_folder_eval(args):
    """Run evaluation on a verification folder."""
    sys.path.insert(0, str(Path(__file__).parent))
    
    from tb_eval.folder_evaluator import FolderEvaluator
    from tb_eval.config import BenchmarkConfig
    
    if not args.folder:
        print("Error: Please specify --folder for folder_eval")
        sys.exit(1)
    
    folder_path = Path(args.folder)
    if not folder_path.exists():
        print(f"Error: Folder does not exist: {folder_path}")
        sys.exit(1)
    
    config = BenchmarkConfig(num_test_runs=args.runs)
    evaluator = FolderEvaluator(config=config)
    
    print(f"\n{'='*60}")
    print(f"FOLDER EVALUATION: {folder_path.name}")
    print(f"{'='*60}")
    
    # Check if it's a single folder or contains multiple folders
    subfolders = [f for f in folder_path.iterdir() if f.is_dir()]
    has_verif_files = any(f.suffix in ['.py', '.v', '.sv'] for f in folder_path.iterdir() if f.is_file())
    
    if has_verif_files:
        # Single folder with verification files
        results = evaluator.evaluate(folder_path, num_runs=args.runs)
        all_results = {folder_path.name: results}
    else:
        # Multiple subfolders
        folder_paths = [f for f in subfolders if any(
            sf.suffix in ['.py', '.v', '.sv'] for sf in f.iterdir() if sf.is_file()
        )]
        
        if not folder_paths:
            print("Error: No verification files found in folder or subfolders")
            sys.exit(1)
        
        all_results = evaluator.evaluate_multiple(folder_paths)
    
    # Print report
    report = evaluator.generate_report(all_results)
    print(report)
    
    # Return success status
    total_success = sum(
        1 for results in all_results.values() 
        for r in results if r.success
    )
    total_runs = sum(len(results) for results in all_results.values())
    
    return total_success == total_runs


def main():
    parser = argparse.ArgumentParser(
        description="VerifEval - Unified Evaluation Runner",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Evaluation Modes:
  spec_eval   - Original specification-based evaluation
                Evaluates verification output against design specs
               
  tb_eval     - Testbench generation benchmark (VerifLLMBench)
                Generates testbenches using LLMs and measures coverage
                Uses cocotb + Verilator (open-source)
                
  folder_eval - Evaluate existing verification folder
                Takes a folder with DUT + testbench files and runs evaluation

Examples:
  # Run testbench evaluation on all designs
  python run_eval.py --eval tb_eval --all
  
  # Run testbench evaluation on specific design with OpenAI
  python run_eval.py --eval tb_eval --design accu --llm openai
  
  # Run specification evaluation
  python run_eval.py --eval spec_eval --design fifo_sync
  
  # Evaluate a verification folder
  python run_eval.py --eval folder_eval --folder tb_eval/test_verif/fifo_sc
  
  # Quick test with fewer runs
  python run_eval.py --eval tb_eval --design adder_8bit --runs 2
        """
    )
    
    # Common arguments
    parser.add_argument('--eval', type=str, required=True,
                       choices=['spec_eval', 'tb_eval', 'folder_eval'],
                       help='Evaluation mode to run')
    parser.add_argument('--all', action='store_true',
                       help='Run on all designs')
    parser.add_argument('--design', type=str,
                       help='Run on specific design')
    parser.add_argument('--designs', type=str, nargs='+',
                       help='Run on multiple specific designs (tb_eval only)')
    parser.add_argument('--folder', type=str,
                       help='Path to verification folder (folder_eval only)')
    
    # tb_eval specific arguments
    parser.add_argument('--llm', type=str, default='anthropic',
                       choices=['anthropic', 'openai'],
                       help='LLM provider for tb_eval (default: anthropic)')
    parser.add_argument('--runs', type=int, default=1,
                       help='Number of test runs (default: 1)')
    parser.add_argument('--max-iterations', type=int, default=4,
                       help='Max iterations for syntax fixing in tb_eval (default: 4)')
    
    # spec_eval specific arguments
    parser.add_argument('--regenerate', action='store_true',
                       help='Regenerate verification for spec_eval')
    
    # List options
    parser.add_argument('--list', action='store_true',
                       help='List available designs for the selected eval mode')
    
    args = parser.parse_args()
    
    # Handle --list
    if args.list:
        if args.eval == 'tb_eval':
            from tb_eval.config import get_all_design_names, get_design_config
            print("Available designs for tb_eval:")
            for name in get_all_design_names():
                design = get_design_config(name)
                print(f"  {name}: {design.description[:60]}...")
        elif args.eval == 'folder_eval':
            print("folder_eval accepts any folder with verification files.")
            print("The folder should contain:")
            print("  - DUT files (.v, .sv)")
            print("  - Testbench files (test_*.py)")
            print("  - Optional: Makefile, support files")
        else:
            print("Available designs for spec_eval:")
            designs_dir = Path(__file__).parent / 'designs'
            for d in designs_dir.iterdir():
                if d.is_dir():
                    print(f"  {d.name}")
        return
    
    # Run the selected evaluation
    if args.eval == 'tb_eval':
        run_tb_eval(args)
    elif args.eval == 'folder_eval':
        success = run_folder_eval(args)
        sys.exit(0 if success else 1)
    else:
        run_spec_eval(args)


if __name__ == '__main__':
    main()

