#!/usr/bin/env python3
"""
Quick test script for the benchmark.
Tests evaluation on existing VerifAgent output.
"""

import sys
from pathlib import Path

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from benchmark.evaluator.metrics import (
    EvaluationResult,
    SpecificationExtractor,
    VerificationPlanner,
    CodeQualityChecker,
    CompletenessEvaluator,
)
import json


def test_fifo_evaluation():
    """Test evaluation on existing FIFO output."""
    
    print("Testing VerifAgent Benchmark Framework")
    print("=" * 70)
    
    # Paths
    benchmark_root = Path(__file__).parent
    design_dir = benchmark_root / 'designs' / 'fifo_sync'
    
    # Use one of the existing outputs
    output_root = benchmark_root.parent / 'output'
    fifo_outputs = [
        d for d in output_root.iterdir()
        if d.is_dir() and ('fifo' in d.name.lower() or 'synch' in d.name.lower())
    ]
    
    if not fifo_outputs:
        print("ERROR: No FIFO output found in output/ directory")
        print("Please run VerifAgent first to generate a FIFO verification")
        return False
    
    # Use the most recent
    output_dir = max(fifo_outputs, key=lambda d: d.stat().st_mtime)
    print(f"\nTesting with output: {output_dir.name}")
    print("-" * 70)
    
    # Load config
    eval_config_path = design_dir / 'eval_config.json'
    with open(eval_config_path) as f:
        eval_config = json.load(f)
    
    # Load generated files
    try:
        with open(output_dir / 'design_spec.json') as f:
            gen_spec = json.load(f)
        print("✓ Loaded design_spec.json")
    except Exception as e:
        print(f"✗ Failed to load design_spec.json: {e}")
        return False
    
    try:
        with open(output_dir / 'verification_plan.json') as f:
            gen_plan = json.load(f)
        print("✓ Loaded verification_plan.json")
    except Exception as e:
        print(f"✗ Failed to load verification_plan.json: {e}")
        return False
    
    # Load reference
    try:
        with open(design_dir / 'reference' / 'requirements.json') as f:
            ref_requirements = json.load(f)
        print("✓ Loaded reference requirements")
    except Exception as e:
        print(f"✗ Failed to load reference: {e}")
        return False
    
    # Run evaluations
    result = EvaluationResult(design_name='fifo_sync')
    
    print("\nRunning Evaluations:")
    print("-" * 70)
    
    # 1. Specification Extraction
    print("\n[1/4] Specification Extraction...")
    spec_score, spec_metrics = SpecificationExtractor.evaluate(
        gen_spec, gen_spec, eval_config['evaluation_criteria']
    )
    result.spec_extraction_score = spec_score
    result.metrics['specification_extraction'] = spec_metrics
    print(f"      Score: {spec_score:.2f} / 25.00")
    
    # 2. Verification Planning
    print("\n[2/4] Verification Planning...")
    plan_score, plan_metrics = VerificationPlanner.evaluate(
        gen_plan, ref_requirements, eval_config['evaluation_criteria']
    )
    result.verification_planning_score = plan_score
    result.metrics['verification_planning'] = plan_metrics
    print(f"      Score: {plan_score:.2f} / 25.00")
    
    # 3. Code Generation
    print("\n[3/4] Code Generation...")
    code_score, code_metrics = CodeQualityChecker.evaluate(
        output_dir, eval_config['evaluation_criteria']
    )
    result.code_generation_score = code_score
    result.metrics['code_generation'] = code_metrics
    print(f"      Score: {code_score:.2f} / 25.00")
    
    # 4. Verification Completeness
    print("\n[4/4] Verification Completeness...")
    complete_score, complete_metrics = CompletenessEvaluator.evaluate(
        gen_plan, ref_requirements, eval_config['evaluation_criteria']
    )
    result.verification_completeness_score = complete_score
    result.metrics['verification_completeness'] = complete_metrics
    print(f"      Score: {complete_score:.2f} / 25.00")
    
    # Calculate total
    weights = eval_config['scoring_weights']
    result.total_score = (
        spec_score * weights['specification_extraction'] / 25.0 * 100 +
        plan_score * weights['verification_planning'] / 25.0 * 100 +
        code_score * weights['code_generation'] / 25.0 * 100 +
        complete_score * weights['verification_completeness'] / 25.0 * 100
    )
    
    # Results
    print("\n" + "=" * 70)
    print("EVALUATION RESULTS")
    print("=" * 70)
    print(f"\nTotal Score: {result.total_score:.2f} / 100.00")
    
    if result.total_score >= 90:
        grade = "A - Excellent!"
    elif result.total_score >= 80:
        grade = "B - Good"
    elif result.total_score >= 70:
        grade = "C - Acceptable"
    else:
        grade = "D - Needs Improvement"
    
    print(f"Grade: {grade}")
    
    print("\nDimension Breakdown:")
    print(f"  Specification Extraction:     {spec_score:>6.2f} / 25.00")
    print(f"  Verification Planning:        {plan_score:>6.2f} / 25.00")
    print(f"  Code Generation:              {code_score:>6.2f} / 25.00")
    print(f"  Verification Completeness:    {complete_score:>6.2f} / 25.00")
    
    print("\nDetailed Metrics:")
    print(json.dumps(result.to_dict(), indent=2))
    
    print("\n" + "=" * 70)
    print("✓ Benchmark test completed successfully!")
    print("=" * 70)
    
    return True


if __name__ == '__main__':
    success = test_fifo_evaluation()
    sys.exit(0 if success else 1)

