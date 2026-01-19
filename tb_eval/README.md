# TB-Eval: Testbench Evaluation Framework

Implements the **VerifLLMBench** paper methodology for evaluating verification testbenches.

## What This Does

TB-Eval evaluates **existing** verification projects (no LLM generation). It measures:

1. **Build Success Rate** - Does the testbench compile with Verilator?
2. **Coverage Metrics** - Line, toggle, and branch coverage
3. **Lint Errors/Warnings** - Code quality issues

## Requirements

### System Dependencies
```bash
# macOS
brew install verilator

# Linux
apt install verilator
```

### Python Dependencies
```bash
pip install cocotb
```

## Usage

### Evaluate a Project
```bash
# Single project
python -m tb_eval.runner --project path/to/verification

# Multiple projects
python -m tb_eval.runner --projects path/to/proj1 path/to/proj2

# Multiple runs for consistency checking
python -m tb_eval.runner --project path/to/verif --runs 3
```

### Run Built-in Examples
```bash
python -m tb_eval.runner --examples
```

### From run_eval.py
```bash
python run_eval.py --eval tb_eval --project tb_eval/examples/adder_single
python run_eval.py --eval tb_eval --project tb_eval/examples/fifo_multi
```

## Project Structure

A verification project folder should contain:

```
my_project/
├── dut.v              # DUT Verilog/SystemVerilog file(s)
├── test_dut.py        # cocotb test file (must start with test_)
├── support.py         # Optional support files (drivers, monitors, etc.)
└── Makefile           # Optional (auto-generated if missing)
```

### Single-File Example (`examples/adder_single/`)
```
adder_single/
├── adder.v           # Simple 8-bit adder DUT
└── test_adder.py     # Self-contained cocotb testbench
```

### Multi-File Example (`examples/fifo_multi/`)
```
fifo_multi/
├── fifo.v              # Synchronous FIFO DUT
├── fifo_interface.py   # Signal interface wrapper
├── fifo_driver.py      # Stimulus driver
├── fifo_monitor.py     # Transaction monitor
├── fifo_scoreboard.py  # Reference model checker
├── fifo_env.py         # Environment (connects components)
└── test_fifo.py        # Top-level tests
```

## Metrics (from VerifLLMBench Paper)

| Metric | Description |
|--------|-------------|
| Build Success | % of runs where Verilator compilation succeeds |
| Line Coverage | % of RTL code lines executed |
| Toggle Coverage | % of signals that toggled both 0→1 and 1→0 |
| Branch Coverage | % of if/case branches taken |
| Lint Errors | Syntax and code quality issues |

## Example Output

```
==================================================
Evaluating: fifo_multi
==================================================
  DUT files: ['fifo.v']
  TB files: ['test_fifo.py']
  Support files: ['fifo_interface.py', 'fifo_driver.py', ...]
  Type: Multi-file

  ✓ Build successful
  ✓ Simulation successful
    Tests: 7/7 passed
    Coverage: 85.2%

==================================================
Project: fifo_multi
==================================================

Build Success Rate: 100.0%
Simulation Success Rate: 100.0%

Coverage (avg of successful runs):
  Line:   85.2%
  Toggle: 85.2%
  Branch: 0.0%
  Overall Average: 85.2%

Lint: 0.0 errors, 2.0 warnings (avg)
```

## Directory Layout

```
tb_eval/
├── __init__.py           # Package exports
├── config.py             # Configuration classes
├── runner.py             # Main evaluation runner
├── simulator.py          # Verilator + cocotb simulation
├── coverage_analyzer.py  # Metrics collection
├── README.md             # This file
└── examples/             # Built-in test examples
    ├── adder_single/     # Single-file example
    └── fifo_multi/       # Multi-file example
```

## Key Differences from Paper

| Paper | This Implementation |
|-------|---------------------|
| UVM + VCS | cocotb + Verilator |
| Commercial tools | Open-source only |
| FSM/Group coverage | Not available in Verilator |
| LLM generation | Evaluation only (no generation) |
