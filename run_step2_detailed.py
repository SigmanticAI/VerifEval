#!/usr/bin/env python3
"""Run Step 2: Classification on submission with details"""
import sys
import json
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
    print(f"DUT Files: {len(routing.dut_files)}")
    print(f"TB Files: {len(routing.tb_files)}")
    
    if routing.errors:
        print(f"\nErrors ({len(routing.errors)}):")
        for err in routing.errors:
            print(f"  - {err}")
    
    if routing.warnings:
        print(f"\nWarnings ({len(routing.warnings)}):")
        for warn in routing.warnings:
            print(f"  - {warn}")
    
    # Save results regardless of quality gate
    router.save_routing(routing)
    print(f"\n✓ Routing saved to {submission_dir / 'route.json'}")
    
    # Check if quality report exists
    quality_report_path = submission_dir / 'quality_report.json'
    if quality_report_path.exists():
        print(f"✓ Quality report saved to {quality_report_path}")
        with open(quality_report_path) as f:
            qr = json.load(f)
            if 'lint_results' in qr:
                print(f"\nLint Results:")
                for file_path, results in qr['lint_results'].items():
                    if results.get('errors'):
                        print(f"  {Path(file_path).name}: {len(results['errors'])} errors")
                        for err in results['errors'][:3]:  # Show first 3
                            print(f"    - {err}")
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
