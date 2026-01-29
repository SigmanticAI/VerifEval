#!/usr/bin/env python3
"""
VerifEval - Unified Evaluation Runner (Questa Version)

A benchmark framework for evaluating AI-generated hardware verification environments.
This version uses Siemens Questa for all verification tasks.

Evaluation Modes:
-----------------
- uvm_eval:    UVM testbench evaluation using Questa simulator
               Measures: build success, test pass rate, coverage metrics
               
- formal_eval: Formal verification using Questa Formal (qformal)
               Measures: assertion proof rate, cover point reachability
               
- spec_eval:   Specification-based evaluation
               Measures: spec extraction, verification planning, code quality

Prerequisites:
--------------
1. Questa installation with valid license
2. License server configured via QUESTA_LICENSE environment variable

License Configuration:
----------------------
    # Option 1: Environment variable (recommended)
    export QUESTA_LICENSE="port@server"
    
    # Option 2: Runtime configuration
    from questa.config import set_license
    set_license("port@server")

Usage:
------
    # Check license configuration
    python run_eval.py --check-license
    
    # Run UVM evaluation
    python run_eval.py --eval uvm_eval --project path/to/verif
    
    # Run formal evaluation  
    python run_eval.py --eval formal_eval --project path/to/assertions
    
    # Run specification evaluation
    python run_eval.py --eval spec_eval --design fifo_sync
    
    # Run with multiple iterations
    python run_eval.py --eval uvm_eval --project path/to/verif --runs 3
"""

import os
import sys
import argparse
import json
from pathlib import Path
from typing import List, Dict, Any, Optional

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))


def check_license() -> bool:
    """Check if Questa license is configured and valid."""
    from questa.config import get_config, check_license as questa_check, print_config
    
    config = get_config()
    print_config()
    
    if questa_check():
        print("✓ License check passed - Questa is accessible")
        return True
    else:
        print("✗ License check failed")
        print("\nTo configure the license:")
        print("  export QUESTA_LICENSE=\"port@server\"")
        print("  Example: export QUESTA_LICENSE=\"1717@license.company.com\"")
        return False


def run_uvm_eval(args) -> bool:
    """
    Run UVM testbench evaluation using Questa.
    
    This evaluates existing UVM verification projects by:
    1. Compiling with vlog (SystemVerilog + UVM)
    2. Running simulation with vsim
    3. Collecting coverage with vcover
    4. Analyzing results
    """
    from questa.simulator import QuestaSimulator, SimulationResult
    from questa.coverage import QuestaCoverageAnalyzer, CoverageResult
    from questa.config import get_config
    
    config = get_config()
    
    # Validate environment
    simulator = QuestaSimulator(config)
    valid, errors = simulator.validate_environment()
    
    if not valid:
        print("✗ Environment validation failed:")
        for err in errors:
            print(f"  - {err}")
        return False
    
    # Determine project(s) to evaluate
    projects = []
    
    if args.examples:
        # Run built-in examples
        examples_dir = Path(__file__).parent / "sample_outputs"
        if examples_dir.exists():
            projects = [d for d in examples_dir.iterdir() if d.is_dir()]
    elif args.project:
        projects = [Path(args.project)]
    elif args.projects:
        projects = [Path(p) for p in args.projects]
    else:
        print("Error: Specify --project, --projects, or --examples")
        return False
    
    # Validate projects exist
    for p in projects:
        if not p.exists():
            print(f"Error: Project not found: {p}")
            return False
    
    all_results = []
    
    for project_path in projects:
        print(f"\n{'='*60}")
        print(f"Evaluating: {project_path.name}")
        print(f"{'='*60}")
        
        # Find source files
        sv_files = list(project_path.rglob("*.sv")) + list(project_path.rglob("*.v"))
        
        if not sv_files:
            print(f"  ✗ No source files found in {project_path}")
            continue
        
        print(f"  Source files: {len(sv_files)}")
        
        # Find top module (from tb_top.sv or similar)
        top_module = None
        for f in sv_files:
            if 'tb_top' in f.name.lower() or 'top' in f.name.lower():
                content = f.read_text()
                import re
                match = re.search(r'module\s+(\w+)', content)
                if match:
                    top_module = match.group(1)
                    break
        
        if not top_module:
            # Default to tb_top
            top_module = "tb_top"
        
        print(f"  Top module: {top_module}")
        
        # Find UVM tests from verification plan
        uvm_tests = ["base_test"]  # Default
        verif_plan = project_path / "verification_plan.json"
        if verif_plan.exists():
            try:
                with open(verif_plan) as f:
                    plan = json.load(f)
                    if 'tests' in plan:
                        uvm_tests = [t.get('name', 'base_test') for t in plan['tests'][:5]]
            except Exception:
                pass
        
        # Run evaluations
        for run_id in range(1, args.runs + 1):
            if args.runs > 1:
                print(f"\n--- Run {run_id}/{args.runs} ---")
            
            for test_name in uvm_tests[:3]:  # Limit tests per run
                print(f"\n  Running test: {test_name}")
                
                result = simulator.run_uvm_test(
                    source_files=sv_files,
                    top_module=top_module,
                    uvm_test=test_name,
                    cleanup=not args.keep_work
                )
                
                # Print results
                if result.compile_success:
                    print(f"    ✓ Compile successful ({result.compile_time_sec:.1f}s)")
                else:
                    print(f"    ✗ Compile failed")
                    for err in result.compile_errors[:3]:
                        print(f"      {err[:80]}")
                    continue
                
                if result.simulation_success:
                    print(f"    ✓ Simulation successful ({result.simulation_time_sec:.1f}s)")
                    print(f"      Test: {'PASSED' if result.test_passed else 'FAILED'}")
                    print(f"      UVM Errors: {result.test_errors}")
                    print(f"      Coverage: {result.coverage_percent:.1f}%")
                else:
                    print(f"    ✗ Simulation failed")
                    for err in result.simulation_errors[:3]:
                        print(f"      {err[:80]}")
                
                all_results.append(result)
        
        # Print project summary
        _print_uvm_summary(project_path.name, all_results)
    
    return len(all_results) > 0 and all(r.passed for r in all_results)


def _print_uvm_summary(project_name: str, results: List[Any]):
    """Print UVM evaluation summary."""
    print(f"\n{'='*60}")
    print(f"UVM EVAL RESULTS: {project_name}")
    print(f"{'='*60}")
    
    if not results:
        print("No results to display")
        return
    
    # Calculate aggregates
    compile_success = sum(1 for r in results if r.compile_success)
    sim_success = sum(1 for r in results if r.simulation_success)
    test_passed = sum(1 for r in results if r.test_passed)
    
    coverages = [r.coverage_percent for r in results if r.coverage_percent > 0]
    avg_coverage = sum(coverages) / len(coverages) if coverages else 0
    
    print(f"\nCompile Success Rate: {compile_success}/{len(results)} ({compile_success/len(results)*100:.0f}%)")
    print(f"Simulation Success Rate: {sim_success}/{len(results)} ({sim_success/len(results)*100:.0f}%)")
    print(f"Test Pass Rate: {test_passed}/{len(results)} ({test_passed/len(results)*100:.0f}%)")
    print(f"Average Coverage: {avg_coverage:.1f}%")
    print(f"{'='*60}")


def run_formal_eval(args) -> bool:
    """
    Run formal verification evaluation using Questa Formal.
    
    Evaluates SVA assertions by:
    1. Compiling with formal options
    2. Running qformal or vsim -formal
    3. Collecting proof/cover results
    """
    from questa.formal import QuestaFormalChecker, FormalResult
    from questa.config import get_config
    
    config = get_config()
    checker = QuestaFormalChecker(config)
    
    # Determine project(s) to evaluate
    projects = []
    
    if args.examples:
        examples_dir = Path(__file__).parent / "formal_eval" / "examples"
        if examples_dir.exists():
            projects = [d for d in examples_dir.iterdir() if d.is_dir()]
    elif args.project:
        projects = [Path(args.project)]
    elif args.projects:
        projects = [Path(p) for p in args.projects]
    else:
        print("Error: Specify --project, --projects, or --examples")
        return False
    
    all_results = []
    
    for project_path in projects:
        print(f"\n{'='*60}")
        print(f"Formal Verification: {project_path.name}")
        print(f"{'='*60}")
        
        for run_id in range(1, args.runs + 1):
            if args.runs > 1:
                print(f"\n--- Run {run_id}/{args.runs} ---")
            
            result = checker.verify_project(
                project_dir=project_path,
                max_depth=args.depth,
                cleanup=not args.keep_work
            )
            
            # Print results
            if result.parse_success:
                print(f"  ✓ Parse successful")
            else:
                print(f"  ✗ Parse failed")
                for err in result.parse_errors[:3]:
                    print(f"    {err[:80]}")
                continue
            
            print(f"  Assertions: {result.total_assertions} found")
            if result.proven_assertions > 0:
                print(f"    ✓ {result.proven_assertions} proven")
            if result.failed_assertions > 0:
                print(f"    ✗ {result.failed_assertions} failed")
            if result.unknown_assertions > 0:
                print(f"    ? {result.unknown_assertions} unknown")
            
            print(f"  Proof Rate: {result.proof_rate:.1f}%")
            print(f"  Score: {result.overall_score:.1f}/100")
            
            all_results.append(result)
    
    # Print summary
    _print_formal_summary(all_results)
    
    return len(all_results) > 0


def _print_formal_summary(results: List[Any]):
    """Print formal evaluation summary."""
    print(f"\n{'='*60}")
    print("FORMAL EVAL RESULTS")
    print(f"{'='*60}")
    
    if not results:
        print("No results to display")
        return
    
    print(f"\n{'Project':<25} {'Syntax':<10} {'Proof%':<12} {'Score':<10}")
    print("-" * 60)
    
    total_assertions = 0
    total_proven = 0
    all_scores = []
    
    for r in results:
        syntax_str = "✓" if r.parse_success else "✗"
        proof_str = f"{r.proof_rate:.1f}%"
        score_str = f"{r.overall_score:.1f}"
        
        print(f"{'result':<25} {syntax_str:<10} {proof_str:<12} {score_str:<10}")
        
        total_assertions += r.total_assertions
        total_proven += r.proven_assertions
        all_scores.append(r.overall_score)
    
    print("-" * 60)
    overall_proof = (total_proven / total_assertions * 100) if total_assertions > 0 else 0
    overall_score = sum(all_scores) / len(all_scores) if all_scores else 0
    print(f"{'OVERALL':<25} {'':<10} {overall_proof:.1f}%{'':<6} {overall_score:.1f}")
    print(f"{'='*60}")


def run_spec_eval(args) -> bool:
    """
    Run specification-based evaluation.
    
    Evaluates verification output against design specifications:
    1. Specification extraction
    2. Verification planning
    3. Code generation quality
    4. Verification completeness
    """
    from evaluator.runner import BenchmarkRunner
    
    benchmark_root = Path(__file__).parent
    results_dir = benchmark_root / 'results'
    
    runner = BenchmarkRunner(benchmark_root, results_dir)
    
    try:
        if args.all:
            runner.run_all(regenerate=args.regenerate)
        elif args.design:
            runner.run_design(args.design, regenerate=args.regenerate)
        else:
            print("Error: Specify --all or --design for spec_eval")
            return False
        return True
    except Exception as e:
        print(f"Error: {e}")
        return False


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="VerifEval - Hardware Verification Benchmark (Questa Version)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Evaluation Modes:
-----------------
  uvm_eval     - UVM testbench evaluation using Questa
                 Evaluates: compile, simulation, coverage
                 
  formal_eval  - Formal verification using Questa Formal
                 Evaluates: assertion proofs, cover points
                 
  spec_eval    - Specification-based evaluation
                 Evaluates: spec extraction, planning, code quality

License Setup:
--------------
  Before running evaluations, configure your Questa license:
  
    export QUESTA_LICENSE="port@server"
    
  Or check configuration:
    python run_eval.py --check-license

Examples:
---------
  # Check license configuration
  python run_eval.py --check-license
  
  # Run UVM evaluation on a project
  python run_eval.py --eval uvm_eval --project sample_outputs/verifagent_fifo
  
  # Run formal evaluation with examples
  python run_eval.py --eval formal_eval --examples
  
  # Run specification evaluation
  python run_eval.py --eval spec_eval --design fifo_sync
  
  # Run with multiple iterations for consistency
  python run_eval.py --eval uvm_eval --project path/to/verif --runs 3
"""
    )
    
    # License check
    parser.add_argument('--check-license', action='store_true',
                       help='Check Questa license configuration')
    
    # Evaluation mode
    parser.add_argument('--eval', type=str,
                       choices=['uvm_eval', 'formal_eval', 'spec_eval'],
                       help='Evaluation mode to run')
    
    # UVM/Formal eval arguments
    parser.add_argument('--project', type=str,
                       help='Path to verification project folder')
    parser.add_argument('--projects', type=str, nargs='+',
                       help='Paths to multiple verification projects')
    parser.add_argument('--examples', action='store_true',
                       help='Run built-in example projects')
    parser.add_argument('--runs', type=int, default=1,
                       help='Number of evaluation runs (default: 1)')
    
    # Formal eval specific
    parser.add_argument('--depth', type=int, default=20,
                       help='Bounded model checking depth (formal_eval, default: 20)')
    
    # Spec eval arguments
    parser.add_argument('--all', action='store_true',
                       help='Run on all designs (spec_eval)')
    parser.add_argument('--design', type=str,
                       help='Run on specific design (spec_eval)')
    parser.add_argument('--regenerate', action='store_true',
                       help='Regenerate verification (spec_eval)')
    
    # Common arguments
    parser.add_argument('--verbose', '-v', action='store_true',
                       help='Enable verbose output')
    parser.add_argument('--keep-work', action='store_true',
                       help='Keep work directory after evaluation')
    parser.add_argument('--output', type=Path,
                       help='Output directory for results')
    
    args = parser.parse_args()
    
    # Handle license check
    if args.check_license:
        success = check_license()
        sys.exit(0 if success else 1)
    
    # Validate evaluation mode
    if not args.eval:
        parser.print_help()
        print("\n⚠️  Please specify --eval <mode> or --check-license")
        sys.exit(1)
    
    # Set verbose mode
    if args.verbose:
        from questa.config import get_config
        get_config().verbose = True
    
    # Run selected evaluation
    success = False
    
    if args.eval == 'uvm_eval':
        success = run_uvm_eval(args)
    elif args.eval == 'formal_eval':
        success = run_formal_eval(args)
    elif args.eval == 'spec_eval':
        success = run_spec_eval(args)
    
    sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()
