#!/usr/bin/env python3
"""Run Step 2: Classification on submission"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from tb_classif.orchestrator import ClassifierRouter

def main():
    submission_dir = Path("/home/saislam/VerifEval/test_submission_fifo")
    
    print("=" * 60)
    print("Step 2: Classify & Route")
    print("=" * 60)
    print(f"\nSubmission: {submission_dir}")
    
    # Run classification
    router = ClassifierRouter(submission_dir)
    routing = router.classify_and_route()
    
    # Print results
    print(f"\nTB Type: {routing.tb_type}")
    print(f"Track: {routing.track}")
    print(f"Simulator: {routing.chosen_simulator}")
    print(f"Confidence: {routing.confidence:.1%}")
    print(f"Quality Gate: {'✓ Passed' if routing.quality_gate_passed else '✗ Failed'}")
    
    if routing.errors:
        print(f"\nErrors:")
        for err in routing.errors:
            print(f"  - {err}")
    
    if routing.warnings:
        print(f"\nWarnings:")
        for warn in routing.warnings:
            print(f"  - {warn}")
    
    # Save results
    if routing.is_valid():
        router.save_routing(routing)
        print(f"\n✓ Routing saved to {submission_dir / 'route.json'}")
        return 0
    else:
        print("\n✗ Classification failed")
        return 1

if __name__ == "__main__":
    sys.exit(main())
