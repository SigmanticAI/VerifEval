# Formal-Eval: Formal Verification Evaluation Framework

Implements the **FVEval** paper methodology for evaluating SVA-based formal verification.

## What This Does

Formal-Eval evaluates **existing** formal verification projects (no LLM generation). It measures:

1. **Syntax Success** - Do the SVA assertions parse and synthesize?
2. **Proof Rate** - What percentage of assertions are proven?
3. **Cover Rate** - What percentage of cover points are reached?

## Requirements

### System Dependencies
```bash
# macOS
brew install yosys

# Linux
apt install yosys
```

### Python Dependencies
```bash
pip install z3-solver
```

## Usage

### Evaluate a Project
```bash
# Single project
python run_eval.py --eval formal_eval --project path/to/verification

# Multiple projects
python run_eval.py --eval formal_eval --projects path/to/proj1 path/to/proj2

# With custom BMC depth
python run_eval.py --eval formal_eval --project my_verif/ --depth 30
```

### Run Built-in Examples
```bash
python run_eval.py --eval formal_eval --examples
```

## Project Structure

A formal verification project folder should contain:

```
my_project/
├── design.sv          # DUT Verilog/SystemVerilog
├── assertions.sv      # SVA assertions (or embedded in design)
└── constraints.sv     # Optional assumptions/constraints
```

### Single-File Example (`examples/counter_single/`)
```
counter_single/
└── counter_with_asserts.sv   # DUT + embedded assertions
```

### Multi-File Example (`examples/fifo_multi/`)
```
fifo_multi/
├── fifo.sv              # FIFO DUT
├── fifo_assertions.sv   # Separate assertion file
└── fifo_top.sv          # Top-level binding
```

## Metrics (from FVEval Paper)

| Metric | Description |
|--------|-------------|
| Syntax Success | % of projects that parse and synthesize |
| Proof Rate | % of assertions formally proven |
| Cover Rate | % of cover points reached |
| Overall Score | Weighted: 30% syntax + 50% proof + 20% cover |

## Supported SVA Constructs

```systemverilog
// Named assertions
my_assert: assert property (@(posedge clk) a |-> b);

// With disable condition
assert property (@(posedge clk) disable iff (!rst_n) ...);

// Temporal operators
assert property (@(posedge clk) a |=> b);      // Next cycle
assert property (@(posedge clk) a |-> ##2 b);  // After 2 cycles
assert property (@(posedge clk) a |-> ##[1:5] b); // Within 1-5 cycles

// Cover points
cover property (@(posedge clk) state == DONE);

// Assumptions
assume property (@(posedge clk) !reset);
```

## Example Output

```
==================================================
Evaluating: counter_single
==================================================
  Design files: ['counter_with_asserts.sv']
  Assertion files: []
  Type: Single-file
  ✓ Parse successful
  ✓ Synthesis successful
  Assertions: 7 found
    ✓ 7 proven
  Proof Rate: 100.0%
  Score: 100.0/100

======================================================================
FORMAL-EVAL RESULTS (FVEval Methodology)
======================================================================

Project              Syntax     Proof%       Score     
------------------------------------------------------------
counter_single       100%       100.0%       100.0     
fifo_multi           100%       100.0%       100.0     
------------------------------------------------------------
OVERALL                         100.0%       100.0
======================================================================
```

## How It Works

1. **Parse** - Extract assertions from SystemVerilog files
2. **Synthesize** - Use Yosys to compile the design
3. **Formal Check** - Run bounded model checking (SAT-based)
4. **Score** - Calculate metrics based on results

## Tools Used

- **Yosys** - Open-source synthesis and formal verification
- **Z3** - SMT solver (backend)
- No commercial tools required!

## Limitations vs Commercial FV Tools

| Feature | Formal-Eval | Cadence Jasper |
|---------|-------------|----------------|
| SVA parsing | Basic subset | Full SVA |
| Bounded model checking | ✓ | ✓ |
| Unbounded proofs | Limited | ✓ |
| Assertion equivalence | Via SAT | Native |
| Counterexamples | Basic | Detailed |
| Performance | Moderate | Optimized |


