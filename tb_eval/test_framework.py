#!/usr/bin/env python3
"""
Test script for TB-Eval framework.
Tests the pipeline without requiring LLM API keys.
"""

import sys
from pathlib import Path

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from tb_eval.config import get_design_config, DUTS_DIR, GENERATED_DIR
from tb_eval.prompt_generator import generate_cocotb_prompt
from tb_eval.simulator import VerilatorSimulator


def test_prompt_generation():
    """Test that prompts are generated correctly."""
    print("\n[1/3] Testing prompt generation...")
    
    design = get_design_config("adder_8bit")
    prompt = generate_cocotb_prompt(design)
    
    assert "adder_8bit" in prompt
    assert "cocotb" in prompt
    assert "reference model" in prompt.lower()
    
    print(f"    ✓ Generated prompt ({len(prompt)} chars)")
    print(f"    Sample: {prompt[:200]}...")
    return True


def test_dut_compilation():
    """Test that DUTs compile with Verilator."""
    print("\n[2/3] Testing DUT compilation...")
    
    import subprocess
    
    designs = ["accu", "adder_8bit", "adder_16bit", "fsm", "alu"]
    
    for name in designs:
        design = get_design_config(name)
        dut_path = DUTS_DIR / name / design.dut_file
        
        result = subprocess.run(
            ['verilator', '--lint-only', '-Wno-fatal', str(dut_path)],
            capture_output=True,
            text=True
        )
        
        if '%Error' in result.stderr:
            print(f"    ✗ {name} failed to compile")
            print(f"      {result.stderr[:200]}")
            return False
        else:
            print(f"    ✓ {name} compiles successfully")
    
    return True


def test_simulation_with_sample_tb():
    """Test simulation with the sample testbenches."""
    print("\n[3/3] Testing simulation pipeline...")
    
    simulator = VerilatorSimulator()
    
    # Test designs that have sample testbenches
    test_designs = ["adder_8bit", "accu", "fsm"]
    all_success = True
    
    for design_name in test_designs:
        work_dir = GENERATED_DIR / design_name / "test_run"
        tb_file = work_dir / f"test_{design_name}.py"
        
        if not tb_file.exists():
            print(f"    ⚠ Sample testbench not found for {design_name}")
            continue
        
        design = get_design_config(design_name)
        result = simulator.run_simulation(design, tb_file, run_id=999)
        
        status = "✓" if result.success else "✗"
        print(f"    {status} {design_name}:")
        print(f"        Build: {result.build_success}, Sim: {result.sim_success}")
        
        if result.coverage_data:
            avg_cov = sum(v for v in result.coverage_data.values() if v > 0) 
            num_metrics = sum(1 for v in result.coverage_data.values() if v > 0)
            if num_metrics > 0:
                print(f"        Coverage: {avg_cov/num_metrics:.1f}% avg")
        
        if not result.success:
            all_success = False
    
    return all_success


def main():
    """Run all framework tests."""
    print("="*60)
    print("TB-Eval Framework Test")
    print("="*60)
    
    tests = [
        ("Prompt Generation", test_prompt_generation),
        ("DUT Compilation", test_dut_compilation),
        ("Simulation Pipeline", test_simulation_with_sample_tb),
    ]
    
    results = []
    for name, test_fn in tests:
        try:
            success = test_fn()
            results.append((name, success))
        except Exception as e:
            print(f"    ✗ {name} failed with exception: {e}")
            import traceback
            traceback.print_exc()
            results.append((name, False))
    
    print("\n" + "="*60)
    print("TEST SUMMARY")
    print("="*60)
    
    for name, success in results:
        status = "✓ PASS" if success else "✗ FAIL"
        print(f"  {name}: {status}")
    
    all_passed = all(s for _, s in results)
    print("\n" + ("All tests passed!" if all_passed else "Some tests failed."))
    
    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(main())

