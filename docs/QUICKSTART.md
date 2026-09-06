# VerifAgent Benchmark - Quick Start Guide

## Installation

No additional dependencies needed! The benchmark uses the same environment as VerifAgent.

```bash
cd /path/to/VerifAgent
# Ensure VerifAgent is installed
pip install -e .
```

## Running Your First Benchmark

### Option 1: Evaluate Existing Output

If you've already generated verification with VerifAgent:

```bash
# Evaluate the FIFO design using existing output
python3 benchmark/evaluator/runner.py --design fifo_sync
```

The runner will automatically find the most recent output in the `output/` directory.

### Option 2: Generate and Evaluate

```bash
# Regenerate verification and evaluate
python3 benchmark/evaluator/runner.py --design fifo_sync --regenerate
```

### Option 3: Run All Benchmarks

```bash
# Evaluate all designs in the benchmark
python3 benchmark/evaluator/runner.py --all
```

## Understanding the Output

The runner will output:

```
======================================================================
Evaluating design: fifo_sync
======================================================================

Using existing output: build_verification_for_a_synch_205422

[1/4] Evaluating specification extraction...
      Score: 21.50 / 25.00

[2/4] Evaluating verification planning...
      Score: 23.00 / 25.00

[3/4] Evaluating code generation...
      Score: 19.50 / 25.00

[4/4] Evaluating verification completeness...
      Score: 20.00 / 25.00

[Bonus] Testing bug detection...
        Bonus: +7.50 points

======================================================================
TOTAL SCORE: 91.50 / 100
======================================================================
```

## Viewing Results

### Generate Full Report

```bash
python3 benchmark/evaluator/scorer.py --report
```

### View Leaderboard

```bash
python3 benchmark/evaluator/scorer.py --leaderboard
```

### Compare Multiple Runs

```bash
python3 benchmark/evaluator/scorer.py --compare fifo_sync
```

### Save Report to File

```bash
python3 benchmark/evaluator/scorer.py --report --output benchmark_report.txt
```

## Understanding Scores

### Scoring Breakdown (100 points total)

1. **Specification Extraction (25 points)**
   - Module detection: 5 pts
   - Port identification: 5 pts
   - Parameter detection: 3 pts
   - FSM identification: 5 pts
   - Requirements extraction: 7 pts

2. **Verification Planning (25 points)**
   - Test coverage: 10 pts
   - Assertion planning: 8 pts
   - Coverage strategy: 7 pts

3. **Code Generation (25 points)**
   - Compilability: 10 pts
   - UVM compliance: 5 pts
   - Code quality: 5 pts
   - Interface correctness: 5 pts

4. **Verification Completeness (25 points)**
   - Requirement coverage: 10 pts
   - Assertion coverage: 7 pts
   - Functional coverage: 5 pts
   - Corner case coverage: 3 pts

5. **Bonus: Bug Detection (up to 10 points)**
   - Points for catching seeded bugs

### Grade Scale

- **A (90-100)**: Excellent - Production ready
- **B (80-89)**: Good - Minor improvements needed
- **C (70-79)**: Acceptable - Some gaps remain
- **D (60-69)**: Needs work - Significant issues
- **F (<60)**: Failing - Major problems

## Benchmark Structure

```
benchmark/
├── designs/              # Reference designs
│   └── fifo_sync/       # Each design has:
│       ├── spec.md          # Human-readable spec
│       ├── design.sv        # RTL implementation
│       ├── reference/       # Ground truth
│       │   └── requirements.json
│       ├── bugs/            # Seeded bugs for testing
│       └── eval_config.json # Evaluation settings
├── evaluator/           # Evaluation framework
│   ├── metrics.py          # Scoring logic
│   ├── runner.py           # Main runner
│   └── scorer.py           # Reporting
└── results/             # Evaluation results (JSON)
```

## Adding Your Own Test Cases

You can test VerifAgent on custom designs by creating a new design directory:

```bash
# Copy the template
cp -r benchmark/designs/fifo_sync benchmark/designs/my_design

# Edit the files:
# - spec.md: Your design specification
# - design.sv: Your RTL (optional)
# - reference/requirements.json: Expected verification items
# - eval_config.json: Adjust scoring criteria

# Run benchmark
python3 benchmark/evaluator/runner.py --design my_design
```

## Troubleshooting

### "No verification output found"

The runner looks for existing output in `output/` directory. Either:
- Generate verification first: `python3 -m verifagent.interactive`
- Use `--regenerate` flag

### "File not found" errors

Check that:
- You're running from the VerifAgent root directory
- The benchmark directory structure is intact
- Required JSON files exist in the design's reference directory

### Evaluation seems wrong

You can examine the detailed metrics in the results JSON files:
```bash
cat benchmark/results/fifo_sync_*.json | python3 -m json.tool
```

## Next Steps

1. **Run the benchmark** on your existing FIFO output
2. **Review the report** to see how well VerifAgent performed
3. **Add more designs** to create a comprehensive test suite
4. **Track improvements** over time as you enhance VerifAgent

## Example Session

```bash
# Step 1: Generate verification for FIFO
python3 -m verifagent.interactive "Build verification for a synchronous FIFO with depth 16"

# Step 2: Run benchmark
python3 benchmark/evaluator/runner.py --design fifo_sync

# Step 3: View results
python3 benchmark/evaluator/scorer.py --leaderboard

# Step 4: Generate detailed report
python3 benchmark/evaluator/scorer.py --report --output results.txt
cat results.txt
```

## Resources

- **VerilogEval**: https://github.com/NVlabs/verilog-eval
- **VerifLLMBench**: DVCon 2025 paper on testbench evaluation
- **OpenCores**: Source for reference designs
- **UVM Best Practices**: Accellera UVM documentation

---

**Ready to test your verification tool? Let's go!** 🚀

