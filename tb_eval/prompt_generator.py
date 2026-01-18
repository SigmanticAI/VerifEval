"""
Prompt generator for LLM-based testbench generation.

Follows the methodology from VerifLLMBench paper, adapted for cocotb
instead of UVM since we're using Verilator (which doesn't support UVM).
"""

from typing import Dict, List, Optional
from pathlib import Path
from .config import DesignConfig, ALU_OPCODES


def generate_cocotb_prompt(design: DesignConfig) -> str:
    """
    Generate a prompt for cocotb testbench generation.
    
    This follows the paper's methodology but adapted for cocotb:
    - Transaction equivalent: test functions with stimulus
    - Sequence equivalent: test scenarios
    - Driver equivalent: cocotb signal driving
    - Monitor equivalent: output sampling and checking
    - Scoreboard equivalent: reference model comparison
    """
    
    # Build input/output port descriptions
    inputs_desc = "\n".join([
        f"    {inp['name']}[{inp['width']-1}:0]: {inp['description']}" 
        if inp['width'] > 1 else f"    {inp['name']}: {inp['description']}"
        for inp in design.inputs
    ])
    
    outputs_desc = "\n".join([
        f"    {out['name']}[{out['width']-1}:0]: {out['description']}"
        if out['width'] > 1 else f"    {out['name']}: {out['description']}"
        for out in design.outputs
    ])
    
    # Additional context for specific designs
    additional_context = ""
    if design.name == "alu":
        opcodes_str = "\n".join([f"    {name} = 0b{code:06b}" for name, code in ALU_OPCODES.items()])
        additional_context = f"""
ALU Operation Codes:
{opcodes_str}

The testbench should test all ALU operations."""
    
    elif design.name == "fsm":
        additional_context = """
The FSM detects the sequence "10011". Test cases should include:
- Single pattern detection
- Overlapping pattern detection (e.g., 1001110011 should match twice)
- Various non-matching sequences
- Reset behavior during pattern matching"""

    elif design.name == "accu":
        additional_context = """
The accumulator collects 4 valid inputs before producing output.
Test cases should include:
- Normal operation with 4 consecutive valid inputs
- Behavior when valid_in is intermittently 0
- Reset during accumulation
- Multiple accumulation cycles"""

    # Clock/reset handling
    clock_reset_info = ""
    if design.has_clock:
        clk_name = "CLK" if design.name == "fsm" else "clk"
        clock_reset_info += f"\nClock signal: {clk_name} (use cocotb.clock.Clock)"
    
    if design.has_reset:
        if design.reset_active_low:
            rst_name = "rst_n"
            clock_reset_info += f"\nReset signal: {rst_name} (active-low, set to 0 to reset, 1 for normal operation)"
        else:
            rst_name = "RST"
            clock_reset_info += f"\nReset signal: {rst_name} (active-high, set to 1 to reset, 0 for normal operation)"

    prompt = f"""Please act as a professional verification engineer.

You need to write a cocotb testbench for the following Verilog design.

Design: {design.module_name}
Description: {design.description}

Input ports:
{inputs_desc}

Output ports:
{outputs_desc}
{clock_reset_info}
{additional_context}

Requirements for the cocotb testbench:

1. **Imports**: Include all necessary cocotb imports:
   - cocotb
   - cocotb.clock (Clock)
   - cocotb.triggers (Timer, RisingEdge, FallingEdge, ClockCycles)
   - cocotb.result (TestSuccess, TestFailure) if needed
   - random for randomization

2. **Reference Model**: Implement a Python reference model function that computes 
   the expected output for given inputs. This serves as the scoreboard.

3. **Test Functions**: Create multiple test functions decorated with @cocotb.test():
   - test_reset: Verify reset behavior (if applicable)
   - test_basic: Basic functionality test
   - test_random: Randomized testing with many iterations for coverage
   - test_corner_cases: Edge cases and boundary conditions

4. **Coverage**: Generate diverse stimulus to maximize:
   - Line coverage (exercise all code paths)
   - Toggle coverage (toggle all signals)
   - Branch coverage (exercise all conditional branches)
   {"- FSM coverage (visit all states and transitions)" if design.has_fsm else ""}

5. **Assertions**: Add assertions to compare DUT outputs against reference model.
   Log any mismatches clearly.

6. **Stimulus Generation**: 
   - Use constrained random values
   - Include boundary values (0, max, etc.)
   - For multi-bit signals, test various bit patterns

Give me the complete cocotb testbench code in a single Python file.
The testbench should be thorough and aim for high functional coverage.
Do NOT include any markdown formatting - just the raw Python code.
"""
    
    return prompt


def generate_syntax_fix_prompt(original_code: str, error_message: str, iteration: int) -> str:
    """
    Generate a prompt to fix syntax errors in generated testbench.
    
    Following the paper's iterative refinement approach.
    """
    
    prompt = f"""The following cocotb testbench has syntax/runtime errors.
Please fix the errors and return the corrected code.

This is iteration {iteration}/4 of the fix attempt.

Error message:
{error_message}

Original code:
```python
{original_code}
```

Please provide the corrected complete cocotb testbench code.
Do NOT include any markdown formatting - just the raw Python code.
Focus only on fixing the errors, don't change the test logic unless necessary.
"""
    
    return prompt


def generate_coverage_improvement_prompt(design: DesignConfig, 
                                         current_coverage: Dict[str, float],
                                         original_code: str) -> str:
    """
    Generate a prompt to improve coverage of generated testbench.
    """
    
    coverage_report = "\n".join([
        f"  {metric}: {value:.1f}%"
        for metric, value in current_coverage.items()
    ])
    
    prompt = f"""The following cocotb testbench for {design.module_name} has achieved the following coverage:

{coverage_report}

The coverage needs improvement. Please enhance the testbench to achieve higher coverage.

Current code:
```python
{original_code}
```

Suggestions for improvement:
1. Add more randomized test iterations
2. Target specific uncovered branches/conditions
3. Add directed tests for edge cases
4. Ensure all input combinations are exercised
{"5. Ensure all FSM states are visited" if design.has_fsm else ""}

Please provide the improved complete cocotb testbench code.
Do NOT include any markdown formatting - just the raw Python code.
"""
    
    return prompt


def save_prompt(design_name: str, prompt: str, prompt_type: str = "initial") -> Path:
    """Save a prompt to file for reference."""
    from .config import PROMPTS_DIR
    
    PROMPTS_DIR.mkdir(parents=True, exist_ok=True)
    
    prompt_file = PROMPTS_DIR / f"{design_name}_{prompt_type}_prompt.txt"
    prompt_file.write_text(prompt)
    
    return prompt_file

