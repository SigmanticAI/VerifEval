# VerifEval

A benchmark framework for evaluating AI-generated hardware verification environments.

## Overview

VerifEval provides a standardized methodology for assessing the quality of automatically generated UVM testbenches, SystemVerilog assertions, and functional coverage. It uses industry-standard specifications (e.g., SystemVerilog Assertions Handbook) as ground truth for fair, concept-based evaluation.

## Key Features

- **Concept-Based Matching**: Evaluates semantic coverage of requirements rather than exact ID matching
- **Multi-Dimensional Scoring**: Assesses specification extraction, verification planning, code generation, and completeness
- **Industry-Standard Ground Truth**: Uses authoritative sources like the SystemVerilog Assertions Handbook
- **Fuzzy Matching**: Intelligent comparison of generated descriptions with reference requirements
- **Extensible Design Framework**: Easy to add new benchmark designs

## Directory Structure

```
VerifEval/
├── designs/                    # Benchmark designs with ground truth
│   └── fifo_sync/             # Synchronous FIFO benchmark
│       ├── design.sv          # Original RTL
│       ├── design_final.sv    # Corrected RTL (spec-compliant)
│       ├── spec.md            # Human-readable specification
│       ├── reference/         # Ground truth data
│       │   └── requirements.json
│       ├── bugs/              # Seeded bugs for mutation testing
│       └── eval_config.json   # Evaluation configuration
├── evaluator/                  # Scoring algorithms
│   ├── metrics.py             # Metric calculations
│   ├── scorer.py              # Main scoring logic
│   └── runner.py              # Benchmark runner
├── baseline_comparison/        # Comparison data
│   ├── claude_verification/   # Claude (Cursor) generated output
│   └── results/               # Comparison results
├── sample_outputs/            # Example tool outputs
│   └── verifagent_fifo/       # VerifAgent generated output
├── results/                   # Benchmark results
│   ├── BENCHMARK_RESULTS.md
│   └── BENCHMARK_RESULTS.pdf
├── tools/                     # Utility scripts
├── test_benchmark.py          # Quick test script
├── HOW_SCORING_WORKS.md       # Detailed scoring methodology
├── QUICKSTART.md              # Getting started guide
└── FAQ.md                     # Frequently asked questions
```

## Scoring Methodology

### Dimensions (100 points total)

| Dimension | Points | Description |
|-----------|--------|-------------|
| Spec Extraction | 15 | Correctly identifying design features |
| Requirements Coverage | 20 | Matching functional requirements |
| Corner Cases | 10 | Identifying edge conditions |
| Assertions | 15 | SVA property coverage |
| Code Generation | 25 | UVM structure and quality |
| Coverage Strategy | 15 | Functional coverage completeness |

### Concept-Based Matching

Unlike exact ID matching, VerifEval uses semantic similarity to compare:
- Generated test descriptions vs. reference requirements
- Generated assertions vs. expected SVA properties
- Corner case coverage vs. specification edge cases

This approach fairly evaluates tools that don't have access to the original specification document.

## Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Run benchmark on a design
python test_benchmark.py

# Or use the evaluator directly
python -m evaluator.runner --design fifo_sync --output path/to/generated/
```

## Adding New Benchmarks

1. Create a new directory under `designs/`
2. Add the RTL design (`design.sv`)
3. Create the specification (`spec.md`)
4. Define ground truth (`reference/requirements.json`)
5. Configure evaluation (`eval_config.json`)

## Ground Truth Sources

The ground truth for the FIFO benchmark is derived from:
- **SystemVerilog Assertions Handbook** (fifo_req_001, fifo_ver_plan_001)
- Industry-standard verification practices

See `GROUND_TRUTH_SOURCES.md` for detailed attribution.

## Results

Current benchmark results comparing VerifAgent vs Claude (Cursor):

| Category | VerifAgent | Claude |
|----------|------------|--------|
| Spec Extraction | 15.00 | 15.00 |
| Requirements | 18.33 | 13.33 |
| Corner Cases | 10.00 | 10.00 |
| Assertions | 13.33 | 8.33 |
| Code Generation | 22.23 | 22.23 |
| Coverage Strategy | 10.00 | 10.00 |
| **Total** | **88.90** | **78.90** |

## License

MIT License

## Contributing

Contributions welcome! Please see our contribution guidelines.

## Citation

If you use VerifEval in your research, please cite:

```bibtex
@software{verifeval2026,
  title = {VerifEval: A Benchmark for AI-Generated Hardware Verification},
  author = {SigmanticAI},
  year = {2026},
  url = {https://github.com/SigmanticAI/VerifEval}
}
```


