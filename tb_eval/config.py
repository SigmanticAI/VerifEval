"""
Configuration for TB-Eval benchmark framework.
"""

from pathlib import Path
from dataclasses import dataclass, field
from typing import Dict, List, Optional
import json

# Base paths
TB_EVAL_ROOT = Path(__file__).parent
PROJECT_ROOT = TB_EVAL_ROOT.parent

# Design paths
DUTS_DIR = TB_EVAL_ROOT / "duts"
GENERATED_DIR = TB_EVAL_ROOT / "generated"
RESULTS_DIR = TB_EVAL_ROOT / "results"
PROMPTS_DIR = TB_EVAL_ROOT / "prompts"


@dataclass
class DesignConfig:
    """Configuration for a single DUT."""
    name: str
    module_name: str
    description: str
    dut_file: str
    inputs: List[Dict]
    outputs: List[Dict]
    has_clock: bool = True
    has_reset: bool = True
    reset_active_low: bool = True
    has_fsm: bool = False
    
    @property
    def dut_path(self) -> Path:
        return DUTS_DIR / self.name / self.dut_file


@dataclass
class BenchmarkConfig:
    """Overall benchmark configuration."""
    max_iterations: int = 4  # Max iterations to fix syntax errors
    simulation_timeout_ms: int = 10000  # 10 seconds
    num_test_runs: int = 5  # Number of test runs per LLM per design
    
    # Coverage thresholds (for reporting)
    line_coverage_threshold: float = 80.0
    branch_coverage_threshold: float = 70.0
    toggle_coverage_threshold: float = 70.0
    
    # LLM settings
    default_llm: str = "anthropic"  # or "openai"
    temperature: float = 0.7
    max_tokens: int = 8000


# Design specifications matching the paper
DESIGNS: Dict[str, DesignConfig] = {
    "accu": DesignConfig(
        name="accu",
        module_name="accu",
        description="Accumulator that accumulates 8-bit data and outputs after 4 inputs. "
                   "When valid_in is 1, data_in is valid. After receiving 4 valid inputs, "
                   "data_out outputs the accumulated sum and valid_out is set to 1 for one cycle.",
        dut_file="accu.v",
        inputs=[
            {"name": "clk", "width": 1, "description": "Clock input"},
            {"name": "rst_n", "width": 1, "description": "Active-low reset"},
            {"name": "data_in", "width": 8, "description": "8-bit input data"},
            {"name": "valid_in", "width": 1, "description": "Input valid signal"},
        ],
        outputs=[
            {"name": "data_out", "width": 10, "description": "10-bit accumulated output"},
            {"name": "valid_out", "width": 1, "description": "Output valid signal"},
        ],
        has_clock=True,
        has_reset=True,
        reset_active_low=True,
    ),
    "adder_8bit": DesignConfig(
        name="adder_8bit",
        module_name="adder_8bit",
        description="8-bit adder using full adder chain. Adds two 8-bit operands with carry-in "
                   "and produces 8-bit sum with carry-out.",
        dut_file="adder_8bit.v",
        inputs=[
            {"name": "a", "width": 8, "description": "First 8-bit operand"},
            {"name": "b", "width": 8, "description": "Second 8-bit operand"},
            {"name": "cin", "width": 1, "description": "Carry-in input"},
        ],
        outputs=[
            {"name": "sum", "width": 8, "description": "8-bit sum output"},
            {"name": "cout", "width": 1, "description": "Carry-out output"},
        ],
        has_clock=False,
        has_reset=False,
    ),
    "adder_16bit": DesignConfig(
        name="adder_16bit",
        module_name="adder_16bit",
        description="16-bit adder using hierarchical adder structure. Adds two 16-bit operands "
                   "with carry-in and produces 16-bit sum with carry-out.",
        dut_file="adder_16bit.v",
        inputs=[
            {"name": "a", "width": 16, "description": "First 16-bit operand"},
            {"name": "b", "width": 16, "description": "Second 16-bit operand"},
            {"name": "Cin", "width": 1, "description": "Carry-in input"},
        ],
        outputs=[
            {"name": "y", "width": 16, "description": "16-bit sum output"},
            {"name": "Co", "width": 1, "description": "Carry-out output"},
        ],
        has_clock=False,
        has_reset=False,
    ),
    "fsm": DesignConfig(
        name="fsm",
        module_name="fsm",
        description="Mealy FSM sequence detector that detects the pattern 10011. "
                   "When the sequence is detected, MATCH output is 1, otherwise 0. "
                   "Supports continuous input and overlapping pattern detection.",
        dut_file="fsm.v",
        inputs=[
            {"name": "CLK", "width": 1, "description": "Clock signal"},
            {"name": "RST", "width": 1, "description": "Active-high reset"},
            {"name": "IN", "width": 1, "description": "Serial input bit"},
        ],
        outputs=[
            {"name": "MATCH", "width": 1, "description": "Pattern match indicator"},
        ],
        has_clock=True,
        has_reset=True,
        reset_active_low=False,  # Active high reset
        has_fsm=True,
    ),
    "alu": DesignConfig(
        name="alu",
        module_name="alu",
        description="32-bit MIPS ALU supporting ADD, ADDU, SUB, SUBU, AND, OR, XOR, NOR, "
                   "SLT, SLTU, SLL, SRL, SRA, SLLV, SRLV, SRAV, and LUI operations.",
        dut_file="alu.v",
        inputs=[
            {"name": "a", "width": 32, "description": "First 32-bit operand"},
            {"name": "b", "width": 32, "description": "Second 32-bit operand"},
            {"name": "aluc", "width": 6, "description": "6-bit ALU control signal"},
        ],
        outputs=[
            {"name": "r", "width": 32, "description": "32-bit result"},
            {"name": "zero", "width": 1, "description": "Zero flag"},
            {"name": "carry", "width": 1, "description": "Carry flag"},
            {"name": "negative", "width": 1, "description": "Negative flag"},
            {"name": "overflow", "width": 1, "description": "Overflow flag"},
            {"name": "flag", "width": 1, "description": "SLT/SLTU result flag"},
        ],
        has_clock=False,
        has_reset=False,
    ),
}


# ALU operation codes (for reference in testbench generation)
ALU_OPCODES = {
    "ADD": 0b100000,
    "ADDU": 0b100001,
    "SUB": 0b100010,
    "SUBU": 0b100011,
    "AND": 0b100100,
    "OR": 0b100101,
    "XOR": 0b100110,
    "NOR": 0b100111,
    "SLT": 0b101010,
    "SLTU": 0b101011,
    "SLL": 0b000000,
    "SRL": 0b000010,
    "SRA": 0b000011,
    "SLLV": 0b000100,
    "SRLV": 0b000110,
    "SRAV": 0b000111,
    "LUI": 0b001111,
}


def get_design_config(design_name: str) -> DesignConfig:
    """Get configuration for a specific design."""
    if design_name not in DESIGNS:
        raise ValueError(f"Unknown design: {design_name}. Available: {list(DESIGNS.keys())}")
    return DESIGNS[design_name]


def get_all_design_names() -> List[str]:
    """Get list of all available design names."""
    return list(DESIGNS.keys())

