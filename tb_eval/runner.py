"""
Main benchmark runner for TB-Eval.

Implements the full VerifLLMBench methodology:
1. For each design
2. Generate testbench using LLM
3. Iterate to fix syntax errors (up to 4 times)
4. Run simulation with coverage
5. Collect and analyze metrics
"""

import sys
import argparse
from pathlib import Path
from typing import List, Optional
import time

from .config import (
    BenchmarkConfig, 
    DesignConfig,
    DESIGNS, 
    get_design_config,
    get_all_design_names,
    RESULTS_DIR
)
from .llm_generator import TestbenchGenerator, GenerationResult
from .simulator import VerilatorSimulator, SimulationResult
from .coverage_analyzer import (
    CoverageMetrics,
    DesignMetrics,
    BenchmarkResults,
    save_results
)


class TBEvalRunner:
    """Main benchmark runner."""
    
    def __init__(self, 
                 config: BenchmarkConfig = None,
                 llm_provider: str = "anthropic"):
        self.config = config or BenchmarkConfig()
        self.llm_provider = llm_provider
        self.generator = TestbenchGenerator(config=self.config, provider=llm_provider)
        self.simulator = VerilatorSimulator(config=self.config)
        self.results = BenchmarkResults(llm_provider=llm_provider)
    
    def run_design(self, design_name: str, 
                   num_runs: int = None) -> DesignMetrics:
        """
        Run benchmark on a single design.
        
        Following the paper:
        - Generate testbench with LLM
        - Fix syntax errors iteratively (up to 4 iterations)
        - Run simulation and collect coverage
        - Run lint checks
        """
        
        num_runs = num_runs or self.config.num_test_runs
        design = get_design_config(design_name)
        
        print(f"\n{'='*60}")
        print(f"Benchmarking design: {design_name}")
        print(f"{'='*60}")
        
        metrics = DesignMetrics(design_name=design_name, num_runs=num_runs)
        
        for run_id in range(1, num_runs + 1):
            print(f"\n--- Run {run_id}/{num_runs} ---")
            
            # Step 1: Generate testbench
            gen_result = self.generator.generate_testbench(design, run_id)
            
            if not gen_result.success:
                print(f"    ✗ Generation failed: {gen_result.error_message}")
                metrics.lint_errors.append(0)
                metrics.lint_warnings.append(0)
                continue
            
            # Get the testbench file path
            from .config import GENERATED_DIR
            tb_file = GENERATED_DIR / design_name / f"run_{run_id}" / f"test_{design_name}.py"
            
            if not tb_file.exists():
                print(f"    ✗ Testbench file not found: {tb_file}")
                continue
            
            # Step 2: Run simulation
            sim_result = self.simulator.run_simulation(design, tb_file, run_id)
            
            # Record lint stats
            metrics.lint_errors.append(sim_result.lint_errors)
            metrics.lint_warnings.append(sim_result.lint_warnings)
            
            if sim_result.build_success:
                metrics.build_successes += 1
                print(f"    ✓ Build successful")
            else:
                print(f"    ✗ Build failed: {sim_result.build_errors[:2]}")  # Show first 2 errors
                continue
            
            if sim_result.sim_success:
                metrics.sim_successes += 1
                print(f"    ✓ Simulation successful")
                
                # Record coverage
                if sim_result.coverage_data:
                    cov = CoverageMetrics(
                        line=sim_result.coverage_data.get("line", 0.0),
                        toggle=sim_result.coverage_data.get("toggle", 0.0),
                        branch=sim_result.coverage_data.get("branch", 0.0),
                        conditional=sim_result.coverage_data.get("conditional", 0.0),
                        fsm=sim_result.coverage_data.get("fsm", 0.0),
                        group=sim_result.coverage_data.get("group", 0.0),
                    )
                    metrics.coverage_runs.append(cov)
                    print(f"    Coverage: {cov.average():.1f}%")
            else:
                print(f"    ✗ Simulation failed: {sim_result.sim_errors[:2]}")
            
            # Print test results
            if sim_result.test_results:
                passed = sum(1 for v in sim_result.test_results.values() if v)
                total = len(sim_result.test_results)
                print(f"    Tests: {passed}/{total} passed")
        
        # Print summary
        print(f"\n{design_name} Summary:")
        print(f"  Build success rate: {metrics.build_success_rate:.1f}%")
        print(f"  Simulation success rate: {metrics.sim_success_rate:.1f}%")
        
        if metrics.coverage_runs:
            avg_cov = sum(c.average() for c in metrics.coverage_runs) / len(metrics.coverage_runs)
            print(f"  Average coverage: {avg_cov:.1f}%")
        
        lint_stats = metrics.get_lint_stats()
        print(f"  Avg lint errors/warnings: {lint_stats['avg_errors']:.1f}/{lint_stats['avg_warnings']:.1f}")
        
        return metrics
    
    def run_all(self, designs: List[str] = None, 
                num_runs: int = None) -> BenchmarkResults:
        """
        Run benchmark on all (or specified) designs.
        """
        
        designs = designs or get_all_design_names()
        
        print(f"\n{'#'*60}")
        print(f"TB-Eval Benchmark")
        print(f"LLM Provider: {self.llm_provider}")
        print(f"Designs: {', '.join(designs)}")
        print(f"Runs per design: {num_runs or self.config.num_test_runs}")
        print(f"{'#'*60}")
        
        start_time = time.time()
        
        for design_name in designs:
            try:
                metrics = self.run_design(design_name, num_runs)
                self.results.add_design_result(metrics)
            except Exception as e:
                print(f"\nError benchmarking {design_name}: {e}")
                import traceback
                traceback.print_exc()
        
        elapsed = time.time() - start_time
        
        # Print final summary
        self._print_summary(elapsed)
        
        # Save results
        save_results(self.results, RESULTS_DIR)
        
        return self.results
    
    def _print_summary(self, elapsed_time: float):
        """Print final benchmark summary."""
        
        print(f"\n{'='*60}")
        print("BENCHMARK SUMMARY")
        print(f"{'='*60}")
        
        print(f"\nLLM Provider: {self.llm_provider}")
        print(f"Time elapsed: {elapsed_time:.1f}s")
        
        print(f"\nOverall Build Success Rate: {self.results.get_overall_build_rate():.1f}%")
        print(f"Overall Average Coverage: {self.results.get_overall_coverage():.1f}%")
        
        print(f"\n{self.results.to_markdown_table()}")


def main():
    """Main entry point for TB-Eval benchmark."""
    
    parser = argparse.ArgumentParser(
        description="TB-Eval: Testbench Generation Benchmark",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Run benchmark on all designs with default settings
  python -m tb_eval.runner --all
  
  # Run on specific design
  python -m tb_eval.runner --design accu
  
  # Use OpenAI instead of Anthropic
  python -m tb_eval.runner --all --llm openai
  
  # Run with fewer iterations for quick testing
  python -m tb_eval.runner --design adder_8bit --runs 2
        """
    )
    
    parser.add_argument('--all', action='store_true',
                       help='Run benchmark on all designs')
    parser.add_argument('--design', type=str,
                       help='Run benchmark on specific design')
    parser.add_argument('--designs', type=str, nargs='+',
                       help='Run benchmark on multiple specific designs')
    parser.add_argument('--llm', type=str, default='anthropic',
                       choices=['anthropic', 'openai'],
                       help='LLM provider to use (default: anthropic)')
    parser.add_argument('--runs', type=int, default=5,
                       help='Number of test runs per design (default: 5)')
    parser.add_argument('--max-iterations', type=int, default=4,
                       help='Max iterations for syntax error fixing (default: 4)')
    parser.add_argument('--list-designs', action='store_true',
                       help='List available designs and exit')
    
    args = parser.parse_args()
    
    if args.list_designs:
        print("Available designs:")
        for name in get_all_design_names():
            design = get_design_config(name)
            print(f"  {name}: {design.description[:60]}...")
        return
    
    if not (args.all or args.design or args.designs):
        parser.print_help()
        print("\nError: Please specify --all, --design, or --designs")
        sys.exit(1)
    
    # Build config
    config = BenchmarkConfig(
        max_iterations=args.max_iterations,
        num_test_runs=args.runs
    )
    
    # Create runner
    runner = TBEvalRunner(config=config, llm_provider=args.llm)
    
    # Run benchmark
    if args.all:
        runner.run_all(num_runs=args.runs)
    elif args.designs:
        runner.run_all(designs=args.designs, num_runs=args.runs)
    elif args.design:
        runner.run_all(designs=[args.design], num_runs=args.runs)


if __name__ == '__main__':
    main()

