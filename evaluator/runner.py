#!/usr/bin/env python3
"""
Automated benchmark runner for VerifAgent.
Runs VerifAgent on reference designs and evaluates output.
"""

import sys
import json
import argparse
from pathlib import Path
from typing import Dict, Optional
import subprocess
import time

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from evaluator.metrics import (
    EvaluationResult,
    SpecificationExtractor,
    VerificationPlanner,
    CodeQualityChecker,
    CompletenessEvaluator,
)


class BenchmarkRunner:
    """Main benchmark runner."""
    
    def __init__(self, benchmark_root: Path, results_dir: Path):
        self.benchmark_root = benchmark_root
        self.designs_dir = benchmark_root / 'designs'
        self.results_dir = results_dir
        self.results_dir.mkdir(parents=True, exist_ok=True)
    
    def run_design(self, design_name: str, regenerate: bool = False) -> EvaluationResult:
        """Run benchmark on a single design."""
        print(f"\n{'='*70}")
        print(f"Evaluating design: {design_name}")
        print(f"{'='*70}\n")
        
        design_dir = self.designs_dir / design_name
        if not design_dir.exists():
            raise ValueError(f"Design not found: {design_name}")
        
        # Load configuration
        eval_config_path = design_dir / 'eval_config.json'
        if not eval_config_path.exists():
            raise ValueError(f"eval_config.json not found for {design_name}")
        
        with open(eval_config_path) as f:
            eval_config = json.load(f)
        
        # Initialize result
        result = EvaluationResult(design_name=design_name)
        
        # Find or generate verification output
        output_dir = self._find_or_generate_output(design_dir, design_name, regenerate, result)
        if not output_dir:
            result.errors.append("No verification output found or generated")
            return result
        
        print(f"Evaluating output from: {output_dir}")
        
        # Load generated artifacts
        gen_spec = self._load_json(output_dir / 'design_spec.json', result)
        gen_plan = self._load_json(output_dir / 'verification_plan.json', result)
        
        # Load reference data
        ref_requirements = self._load_json(design_dir / 'reference' / 'requirements.json', result)
        
        if not gen_spec or not gen_plan or not ref_requirements:
            result.errors.append("Missing required files for evaluation")
            return result
        
        # Evaluate each dimension
        print("\n[1/4] Evaluating specification extraction...")
        spec_score, spec_metrics = SpecificationExtractor.evaluate(
            gen_spec, gen_spec, eval_config['evaluation_criteria']
        )
        result.spec_extraction_score = spec_score
        result.metrics['specification_extraction'] = spec_metrics
        print(f"      Score: {spec_score:.2f} / 25.00")
        
        print("\n[2/4] Evaluating verification planning...")
        plan_score, plan_metrics = VerificationPlanner.evaluate(
            gen_plan, ref_requirements, eval_config['evaluation_criteria']
        )
        result.verification_planning_score = plan_score
        result.metrics['verification_planning'] = plan_metrics
        print(f"      Score: {plan_score:.2f} / 25.00")
        
        print("\n[3/4] Evaluating code generation...")
        code_score, code_metrics = CodeQualityChecker.evaluate(
            output_dir, eval_config['evaluation_criteria']
        )
        result.code_generation_score = code_score
        result.metrics['code_generation'] = code_metrics
        print(f"      Score: {code_score:.2f} / 25.00")
        
        print("\n[4/4] Evaluating verification completeness...")
        complete_score, complete_metrics = CompletenessEvaluator.evaluate(
            gen_plan, ref_requirements, eval_config['evaluation_criteria']
        )
        result.verification_completeness_score = complete_score
        result.metrics['verification_completeness'] = complete_metrics
        print(f"      Score: {complete_score:.2f} / 25.00")
        
        # Calculate total score
        weights = eval_config['scoring_weights']
        result.total_score = (
            spec_score * weights['specification_extraction'] / 25.0 * 100 +
            plan_score * weights['verification_planning'] / 25.0 * 100 +
            code_score * weights['code_generation'] / 25.0 * 100 +
            complete_score * weights['verification_completeness'] / 25.0 * 100
        )
        
        # Bug detection bonus (if enabled)
        if eval_config.get('bug_detection_test', {}).get('enabled', False):
            print("\n[Bonus] Testing bug detection...")
            bonus = self._evaluate_bug_detection(design_dir, output_dir, eval_config, result)
            result.bonus_score = bonus
            result.total_score += bonus
            print(f"        Bonus: +{bonus:.2f} points")
        
        # Save results
        self._save_results(result, design_name)
        
        print(f"\n{'='*70}")
        print(f"TOTAL SCORE: {result.total_score:.2f} / {result.max_score}")
        print(f"{'='*70}\n")
        
        return result
    
    def run_all(self, regenerate: bool = False) -> Dict[str, EvaluationResult]:
        """Run benchmark on all designs."""
        results = {}
        
        # Find all designs
        designs = [d.name for d in self.designs_dir.iterdir() if d.is_dir()]
        
        print(f"\nFound {len(designs)} designs to evaluate:")
        for design in designs:
            print(f"  - {design}")
        
        # Run each design
        for design_name in designs:
            try:
                result = self.run_design(design_name, regenerate)
                results[design_name] = result
            except Exception as e:
                print(f"\nERROR evaluating {design_name}: {e}")
                import traceback
                traceback.print_exc()
        
        # Generate summary
        self._print_summary(results)
        
        return results
    
    def _find_or_generate_output(self, design_dir: Path, design_name: str, 
                                  regenerate: bool, result: EvaluationResult) -> Optional[Path]:
        """Find existing output or generate new verification."""
        
        # Look for existing output in VerifAgent's output directory
        verifagent_output = self.benchmark_root.parent / 'output'
        
        if not regenerate and verifagent_output.exists():
            # Find most recent output for this design
            matching_dirs = [
                d for d in verifagent_output.iterdir()
                if d.is_dir() and design_name.lower() in d.name.lower()
            ]
            
            if matching_dirs:
                # Use most recently modified
                latest = max(matching_dirs, key=lambda d: d.stat().st_mtime)
                print(f"Using existing output: {latest.name}")
                return latest
        
        # Generate new verification
        print(f"Generating verification for {design_name}...")
        
        spec_file = design_dir / 'spec.md'
        if not spec_file.exists():
            result.errors.append(f"Specification file not found: {spec_file}")
            return None
        
        # Run VerifAgent (use interactive mode with spec as input)
        try:
            # Read spec
            with open(spec_file) as f:
                spec_text = f.read()
            
            # Call VerifAgent's interactive mode
            cmd = [
                sys.executable, '-m', 'verifagent.interactive',
                f'Build verification for a {design_name}'
            ]
            
            print(f"Running: {' '.join(cmd)}")
            proc = subprocess.run(
                cmd,
                cwd=self.benchmark_root.parent,
                capture_output=True,
                text=True,
                timeout=300,
            )
            
            if proc.returncode != 0:
                result.errors.append(f"VerifAgent failed: {proc.stderr}")
                return None
            
            # Find newly created output
            matching_dirs = [
                d for d in verifagent_output.iterdir()
                if d.is_dir() and design_name.lower() in d.name.lower()
            ]
            
            if matching_dirs:
                latest = max(matching_dirs, key=lambda d: d.stat().st_mtime)
                print(f"Generated output: {latest.name}")
                return latest
            
        except subprocess.TimeoutExpired:
            result.errors.append("VerifAgent timed out")
        except Exception as e:
            result.errors.append(f"Failed to run VerifAgent: {e}")
        
        return None
    
    def _load_json(self, path: Path, result: EvaluationResult) -> Optional[Dict]:
        """Load JSON file with error handling."""
        try:
            if not path.exists():
                result.warnings.append(f"File not found: {path}")
                return None
            
            with open(path) as f:
                return json.load(f)
        except Exception as e:
            result.errors.append(f"Failed to load {path}: {e}")
            return None
    
    def _evaluate_bug_detection(self, design_dir: Path, output_dir: Path, 
                                config: Dict, result: EvaluationResult) -> float:
        """Evaluate bug detection capability (simplified)."""
        bugs_dir = design_dir / 'bugs'
        
        if not bugs_dir.exists():
            return 0.0
        
        # Load bug manifest
        manifest_path = bugs_dir / 'manifest.json'
        if not manifest_path.exists():
            return 0.0
        
        with open(manifest_path) as f:
            manifest = json.load(f)
        
        bugs = manifest.get('bugs', [])
        result.total_bugs = len(bugs)
        
        # Check if assertions would catch bugs (simplified check)
        gen_plan_path = output_dir / 'verification_plan.json'
        if not gen_plan_path.exists():
            return 0.0
        
        with open(gen_plan_path) as f:
            gen_plan = json.load(f)
        
        assertions = {a['name'].lower() for a in gen_plan.get('assertions', [])}
        
        bugs_detected = 0
        for bug in bugs:
            expected_assertion = bug['expected_detection'].get('by_assertion', '').lower()
            # Check if the expected assertion exists
            if any(expected_assertion in a for a in assertions):
                bugs_detected += 1
        
        result.bugs_detected = bugs_detected
        
        max_bonus = config['bug_detection_test']['bonus_points']
        return (bugs_detected / len(bugs)) * max_bonus if bugs else 0.0
    
    def _save_results(self, result: EvaluationResult, design_name: str):
        """Save evaluation results to file."""
        timestamp = time.strftime('%Y%m%d_%H%M%S')
        result_file = self.results_dir / f'{design_name}_{timestamp}.json'
        
        with open(result_file, 'w') as f:
            json.dump(result.to_dict(), f, indent=2)
        
        print(f"\nResults saved to: {result_file}")
    
    def _print_summary(self, results: Dict[str, EvaluationResult]):
        """Print summary of all results."""
        print("\n" + "="*70)
        print("BENCHMARK SUMMARY")
        print("="*70)
        
        if not results:
            print("No results to display.")
            return
        
        print(f"\n{'Design':<30} {'Score':>10} {'Status':>10}")
        print("-"*70)
        
        total_score = 0
        total_max = 0
        
        for design_name, result in sorted(results.items()):
            status = "✓ PASS" if result.total_score >= 70 else "✗ FAIL"
            print(f"{design_name:<30} {result.total_score:>10.2f} {status:>10}")
            total_score += result.total_score
            total_max += result.max_score
        
        print("-"*70)
        avg_score = total_score / len(results)
        print(f"{'AVERAGE':<30} {avg_score:>10.2f}")
        print("="*70 + "\n")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description='Run VerifAgent benchmark')
    parser.add_argument('--design', help='Specific design to evaluate')
    parser.add_argument('--all', action='store_true', help='Evaluate all designs')
    parser.add_argument('--regenerate', action='store_true', 
                       help='Regenerate verification (ignore existing output)')
    parser.add_argument('--benchmark-root', type=Path, 
                       default=Path(__file__).parent.parent,
                       help='Benchmark root directory')
    parser.add_argument('--results-dir', type=Path,
                       default=Path(__file__).parent.parent / 'results',
                       help='Results output directory')
    
    args = parser.parse_args()
    
    runner = BenchmarkRunner(args.benchmark_root, args.results_dir)
    
    if args.all:
        runner.run_all(regenerate=args.regenerate)
    elif args.design:
        runner.run_design(args.design, regenerate=args.regenerate)
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == '__main__':
    main()

