# TB-Eval: Testbench Generation Benchmark

This module implements the methodology from the **VerifLLMBench** paper for benchmarking LLM-generated testbenches using open-source tools.

## Overview

TB-Eval supports three evaluation modes:

1. **tb_eval** - Generate testbenches using LLMs and measure coverage
2. **folder_eval** - Evaluate existing verification folders
3. **spec_eval** - Original specification-based evaluation

## Requirements

### System Dependencies
```bash
# macOS
brew install verilator

# Linux (Ubuntu)
apt install verilator
```

### Python Dependencies
```bash
pip install cocotb cocotb-test anthropic openai
```

## Usage

### Evaluate a Verification Folder
```bash
# Single folder with DUT + testbench
python run_eval.py --eval folder_eval --folder path/to/verif

# Example with included FIFO test
python run_eval.py --eval folder_eval --folder tb_eval/test_verif/fifo_sc
```

### LLM-Based Testbench Generation
```bash
# Set API key
export ANTHROPIC_API_KEY="your-key"

# Run on all designs
python run_eval.py --eval tb_eval --all

# Run on specific design
python run_eval.py --eval tb_eval --design accu --runs 2
```

### Quick Framework Test
```bash
python tb_eval/test_framework.py
```

## Verification Folder Structure

A verification folder should contain:
```
my_verif/
├── dut.v              # DUT Verilog file(s)
├── test_dut.py        # Main cocotb test file
├── dut_if.py          # Interface (optional)
├── dut_driver.py      # Driver (optional)
├── dut_monitor.py     # Monitor (optional)
├── dut_scoreboard.py  # Scoreboard (optional)
├── dut_env.py         # Environment (optional)
└── Makefile           # Build configuration (optional, auto-generated)
```

## Included Test Designs

| Design | Description |
|--------|-------------|
| accu | 8-bit accumulator |
| adder_8bit | 8-bit ripple carry adder |
| adder_16bit | 16-bit hierarchical adder |
| fsm | Mealy FSM sequence detector |
| alu | 32-bit MIPS ALU |
| fifo_sc | Synchronous FIFO (multi-file example) |

## Coverage Metrics

- **Line coverage**: % of RTL lines executed
- **Toggle coverage**: % of signals toggled
- **Branch coverage**: % of branches taken

## Directory Structure

```
tb_eval/
├── __init__.py
├── config.py              # Configuration
├── prompt_generator.py    # LLM prompt generation
├── llm_generator.py       # LLM client
├── simulator.py           # Verilator + cocotb
├── coverage_analyzer.py   # Coverage metrics
├── folder_evaluator.py    # Folder evaluation
├── runner.py              # Main runner
├── test_framework.py      # Validation tests
├── duts/                  # Built-in DUTs
└── test_verif/            # Example verification folders
    └── fifo_sc/           # Multi-file FIFO example
```
