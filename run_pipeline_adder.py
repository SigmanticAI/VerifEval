#!/usr/bin/env python3
"""Run complete pipeline on adder example"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from tb_classif.orchestrator import ClassifierRouter

def main():
    submission_dir = Path("/home/saislam/VerifEval/test_submission_adder")
    
    print("=" * 70)
    print("VerifEval Pipeline - Adder Example (Verilator Compatible)")
    print("=" * 70)
    
    # Step 2: Classification
    print("\n[Step 2] Classifying testbench...")
    router = ClassifierRouter(submission_dir)
    routing = router.classify_and_route()
    
    print(f"\n  TB Type: {routing.tb_type}")
    print(f"  Track: {routing.track}")
    print(f"  Simulator: {routing.chosen_simulator}")
    print(f"  Confidence: {routing.confidence:.1%}")
    print(f"  Quality Gate: {'✓ Passed' if routing.quality_gate_passed else '⚠ Failed'}")
    
    # Save routing
    router.save_routing(routing)
    print(f"\n  ✓ Saved: route.json")
    
    if routing.errors:
        print(f"\n  Errors:")
        for err in routing.errors:
            print(f"    - {err}")
        return 1
    
    if routing.warnings:
        print(f"\n  Warnings:")
        for warn in routing.warnings:
            print(f"    - {warn}")
    
    print("\n" + "=" * 70)
    print("Step 2: COMPLETED ✓")
    print("=" * 70)
    
    print("\nNext steps would be:")
    print("  [Step 3] Build & Orchestrate - Setup VUnit project")
    print("  [Step 4] Execute Tests - Run tests with Verilator")
    print("  [Step 5] Coverage Analysis - Parse coverage data")
    print("  [Step 6] Score & Export - Generate final report")
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
