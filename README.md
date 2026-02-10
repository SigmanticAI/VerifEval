# VerifEval

[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![CocoTB](https://img.shields.io/badge/CocoTB-1.9+-green.svg)](https://www.cocotb.org/)
[![Verilator](https://img.shields.io/badge/Verilator-5.020+-orange.svg)](https://www.veripool.org/verilator/)

**A comprehensive benchmark framework for evaluating AI-generated hardware verification environments.**

VerifEval is the first standardized methodology for assessing the quality of automatically generated verification testbenches, providing objective metrics for UVM testbenches, SystemVerilog assertions, functional coverage, and more.

---

## 🎯 Overview

### What is VerifEval?

VerifEval evaluates **verification code quality**, not RTL quality. While frameworks like VerilogEval assess HDL generation, VerifEval focuses on:

- ✅ **Testbench Quality**: UVM structure, CocoTB tests, VUnit projects
- ✅ **Test Coverage**: Line, branch, toggle, and functional coverage
- ✅ **Assertion Coverage**: SVA (SystemVerilog Assertions) validation
- ✅ **Code Quality**: Lint compliance, coding standards
- ✅ **Test Effectiveness**: Pass rates, bug detection, efficiency

### Key Innovation

**Concept-Based Semantic Matching**: Unlike exact ID matching, VerifEval uses fuzzy semantic similarity to fairly evaluate tools that don't have access to original specifications.

### Use Cases

- **Benchmark AI Tools**: Compare GPT-4, Claude, Gemini for verification generation
- **Evaluate Agents**: Assess VerifAgent, AutoVerif, and other specialized tools
- **Research**: Quantify verification code quality in academic studies
- **CI/CD Integration**: Automated verification quality gates

---

## 🏗️ Architecture

VerifEval uses a **modular 6-step pipeline** where each step consumes JSON from the previous step and produces structured output for the next:

```
┌─────────────────────────────────────────────────────────────────┐
│                    VERIFEVAL PIPELINE                            │
└─────────────────────────────────────────────────────────────────┘

   Submission Directory
   (DUT + Testbench)
          ↓
┌─────────────────────┐
│  Step 2: Classify   │  Detect testbench type and route
│  & Route            │
└─────────────────────┘
          ↓ route.json + quality_report.json
┌─────────────────────┐
│  Step 3: Build &    │  Setup VUnit, configure simulator,
│  Orchestrate        │  compile sources, discover tests
└─────────────────────┘
          ↓ build_manifest.json
┌─────────────────────┐
│  Step 4: Execute    │  Run tests, collect coverage,
│  Tests              │  generate results
└─────────────────────┘
          ↓ test_report.json + coverage files
┌─────────────────────┐
│  Step 5: Coverage   │  Parse coverage formats,
│  Analysis           │  calculate metrics, merge data
└─────────────────────┘
          ↓ coverage_report.json
┌─────────────────────┐
│  Step 6: Score &    │  Multi-dimensional scoring,
│  Export             │  generate reports (HTML/JUnit/CSV)
└─────────────────────┘
          ↓ final_report.json + exports
    Final Evaluation Report
    (Score, Grade, Recommendations)
```

### Pipeline Steps Explained

#### Step 2: Classification & Route
**Purpose**: Intelligently detect testbench type and select appropriate tools

**Process**:
1. Scan submission for testbench files
2. Detect testbench type using pattern matching:
   - **CocoTB**: Python with `import cocotb`
   - **PyUVM**: Python with `import pyuvm`
   - **UVM-SV**: SystemVerilog with `uvm_component`, `uvm_test`
   - **VUnit**: Python with `from vunit import VUnit`
   - **Generic HDL**: Plain Verilog/VHDL/SystemVerilog
3. Run quality gate (Verible linter, GHDL checker)
4. Route to execution track:
   - **Track A**: Python-based (CocoTB, PyUVM, VUnit)
   - **Track B**: HDL-based (Generic SystemVerilog/VHDL)
   - **Track C**: Commercial-required (UVM-SV)
5. Select simulator: Verilator, Icarus, GHDL, or Questa

**Output**: `route.json`, `quality_report.json`

**Example**:
```json
{
  "tb_type": "cocotb",
  "track": "A",
  "simulator": "verilator",
  "confidence": 0.855,
  "dut_files": ["adder.v"],
  "tb_files": ["test_adder.py"]
}
```

#### Step 3: Build & Orchestrate
**Purpose**: Set up build environment and compile sources

**Process**:
1. Load routing decision from Step 2
2. Detect or generate VUnit project
3. Configure selected simulator with coverage flags
4. Compile all sources (DUT + testbench)
5. Discover test cases
6. Setup coverage collection

**Output**: `build_manifest.json`

**Example**:
```json
{
  "build_status": "success",
  "simulator": "verilator",
  "tests_discovered": 5,
  "test_cases": [
    {"name": "test_adder.test_basic_addition", "timeout": 10.0},
    {"name": "test_adder.test_overflow", "timeout": 10.0}
  ],
  "coverage_config": {
    "enabled": true,
    "line": true,
    "toggle": true
  }
}
```

#### Step 4: Execute Tests
**Purpose**: Run tests and collect results with coverage

**Process**:
1. Load build manifest
2. Initialize runner (VUnit or CocoTB)
3. Execute each test with timeout management
4. Collect per-test coverage files
5. Generate test results report

**Output**: `test_report.json` + coverage files

**Example**:
```json
{
  "status": "completed",
  "summary": {
    "total_tests": 5,
    "passed": 5,
    "failed": 0,
    "execution_time_ms": 1245.6
  },
  "results": [
    {
      "name": "test_adder.test_basic_addition",
      "outcome": "passed",
      "duration_ms": 156.2,
      "coverage_file": "coverage_basic.dat"
    }
  ]
}
```

#### Step 5: Coverage Analysis
**Purpose**: Parse and analyze coverage data

**Process**:
1. Load test report and coverage files
2. Auto-detect coverage format (Verilator, LCOV, Covered)
3. Parse coverage data into structured format
4. Calculate metrics: line, branch, toggle, FSM coverage
5. Merge per-test coverage with contribution tracking
6. Prepare mutation testing targets

**Output**: `coverage_report.json`

**Example**:
```json
{
  "structural_coverage": {
    "line_coverage": {
      "lines_hit": 3,
      "lines_total": 3,
      "percentage": 100.0
    },
    "toggle_coverage": {
      "signals_toggled": 12,
      "signals_total": 12,
      "percentage": 100.0
    }
  },
  "overall_score": 1.0
}
```

#### Step 6: Scoring & Export
**Purpose**: Generate final score and comprehensive reports

**Process**:
1. Load all reports (quality, test, coverage)
2. Detect scoring tier:
   - **Tier 1 (Open Source)**: Verilator-based structural coverage
   - **Tier 2 (Professional)**: Questa-based functional coverage + assertions + UVM
3. Calculate multi-dimensional scores
4. Generate final grade (A-F)
5. Export to multiple formats (HTML, JUnit, CSV, PDF)

**Output**: `final_report.json` + exports

**Example**:
```json
{
  "score": {
    "total": 93.5,
    "percentage": 93.5,
    "grade": "A"
  },
  "component_scores": {
    "structural_coverage": {"score": 35.0, "max": 35.0},
    "test_pass_rate": {"score": 15.0, "max": 15.0},
    "code_quality": {"score": 13.5, "max": 15.0},
    "test_efficiency": {"score": 19.0, "max": 20.0},
    "behavioral_accuracy": {"score": 11.0, "max": 15.0}
  }
}
```

---

## 🎭 Two Execution Paths

VerifEval intelligently routes testbenches to appropriate simulators based on their requirements:

### Path 1: Open Source (Tier 1)

**Testbench Types**: CocoTB, PyUVM, VUnit, Generic HDL

**Simulators**: Verilator, Icarus Verilog, GHDL

**Scoring (100 points)**:
- Structural Coverage (35 pts): Line + toggle coverage
- Code Quality (15 pts): Lint results, style compliance
- Test Efficiency (20 pts): Execution time, test design
- Test Pass Rate (15 pts): Success ratio
- Behavioral Accuracy (15 pts): Correctness validation

**Advantages**:
- ✅ Free and open source
- ✅ Fast simulation (10-100x faster)
- ✅ Easy CI/CD integration
- ✅ No license management

**Use Cases**: Academic research, open-source projects, CI/CD pipelines

### Path 2: Commercial (Tier 2)

**Testbench Types**: UVM SystemVerilog

**Simulators**: Questa, VCS, Xcelium

**Scoring (100 points)**:
- Functional Coverage (25 pts): Covergroups, bins, crosses
- Assertion Coverage (20 pts): SVA properties validated
- Structural Coverage (20 pts): Line + branch + toggle
- UVM Compliance (15 pts): Proper UVM architecture
- Code Quality (10 pts): Lint and style
- Test Stability (10 pts): Simulation reliability

**Advantages**:
- ✅ Full UVM support
- ✅ Advanced functional coverage
- ✅ SVA assertion checking
- ✅ Industry-standard workflows

**Use Cases**: Enterprise verification, UVM-based projects, commercial tools

---

## 🚀 Quick Start

### Installation

```bash
# Clone repository
git clone https://github.com/SigmanticAI/VerifEval.git
cd VerifEval

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install 'cocotb<2.0' vunit_hdl  # For Verilator 5.020
# OR
pip install 'cocotb>=2.0' vunit_hdl  # For Verilator 5.036+

# Install simulators (choose based on your needs)
sudo apt-get install verilator  # Open source
sudo apt-get install iverilog   # Alternative open source
# Questa/VCS require commercial licenses
```

### Basic Usage

#### Option 1: Run Complete Pipeline

```bash
# Evaluate a CocoTB/VUnit testbench (Open Source Path)
python run_eval.py --eval tb_eval --project /path/to/testbench

# Evaluate with verbose output
python run_eval.py --eval tb_eval --project /path/to/testbench --verbose

# Run multiple iterations
python run_eval.py --eval tb_eval --project /path/to/testbench --runs 3
```

#### Option 2: Run Individual Steps

```bash
# Step 2: Classify testbench
python -m tb_classif /path/to/testbench

# Step 3: Build (if you have build_orchestrate working)
python -m build_orchestrate /path/to/testbench

# Step 4: Execute tests
python -m step4_execute /path/to/testbench

# Step 5: Analyze coverage
python -m step5_coverage /path/to/testbench

# Step 6: Generate final score
python -m step6_score /path/to/testbench
```

#### Option 3: Python API

```python
from pathlib import Path
from tb_classif import ClassifierRouter

# Step 2: Classification
submission_dir = Path("./my_testbench")
router = ClassifierRouter(submission_dir)
routing = router.classify_and_route()

print(f"TB Type: {routing.tb_type}")
print(f"Simulator: {routing.chosen_simulator}")
print(f"Track: {routing.track}")

# Save routing decision
router.save_routing(routing)
```

---

## 📊 Example Results

### Simple Adder (CocoTB + Verilator)

**Testbench**: 8-bit adder with 5 test cases

**Results**:
```
Tests:     5/5 passed (100%)
Coverage:  100% line, 100% toggle
Score:     93.5/100 (Grade A)
Time:      0.01s real time, 61ns sim time
```

**Component Breakdown**:
| Component | Score | Max | Percentage |
|-----------|-------|-----|------------|
| Structural Coverage | 35.0 | 35 | 100% |
| Test Pass Rate | 15.0 | 15 | 100% |
| Test Efficiency | 19.0 | 20 | 95% |
| Code Quality | 13.5 | 15 | 90% |
| Behavioral Accuracy | 11.0 | 15 | 73% |
| **TOTAL** | **93.5** | **100** | **93.5%** |

**Grade**: **A**

### Synchronous FIFO (UVM-SV + Questa)

**Testbench**: Professional UVM environment with assertions

**Results**:
```
Tests:     12/12 passed (100%)
Coverage:  95% functional, 100% structural
Assertions: 25/25 properties validated
Score:     88.9/100 (Grade B+)
```

---

## 📁 Directory Structure

```
VerifEval/
├── README.md                       # This file
├── run_eval.py                     # Main pipeline runner
├── requirements.txt                # Python dependencies
│
├── tb_classif/                     # Step 2: Classification & Routing
│   ├── __init__.py
│   ├── orchestrator.py             # Main ClassifierRouter
│   ├── models.py                   # Data structures
│   ├── config.py                   # Configuration
│   ├── detectors/                  # Testbench type detectors
│   │   ├── base_detect.py
│   │   ├── cocotb_detect.py
│   │   ├── pyuvm_detect.py
│   │   ├── uvm_sv_detect.py
│   │   ├── vunit_detect.py
│   │   └── hdl_detect.py
│   ├── quality_gate/               # Static analysis
│   │   ├── verible_linter.py
│   │   └── ghdl_checker.py
│   ├── routing/                    # Routing logic
│   │   ├── engine.py
│   │   └── simulator_selector.py
│   └── discovery/                  # File discovery
│       ├── file_finder.py
│       └── manifest_parser.py
│
├── build_orchestrate/              # Step 3: Build & Orchestrate
│   ├── __init__.py
│   ├── orchestrator.py             # VUnitOrchestrator
│   ├── models.py
│   ├── config.py
│   ├── project/                    # VUnit project handling
│   ├── simulators/                 # Simulator configurations
│   └── tracks/                     # Track-specific builds
│
├── step4_execute/                  # Step 4: Test Execution
│   ├── __init__.py
│   ├── executor.py                 # TestExecutor
│   ├── models.py
│   ├── config.py
│   ├── runners/                    # VUnit/CocoTB runners
│   ├── reporters/                  # Report generation
│   └── handlers/                   # Output/timeout handling
│
├── step5_coverage/                 # Step 5: Coverage Analysis
│   ├── __init__.py
│   ├── analyzer.py                 # CoverageAnalyzer
│   ├── models.py
│   ├── config.py
│   ├── parsers/                    # Format parsers
│   │   ├── verilator_parser.py
│   │   ├── lcov_parser.py
│   │   └── covered_parser.py
│   └── metrics/                    # Metric calculation
│       ├── calculator.py
│       └── merger.py
│
├── step6_score/                    # Step 6: Scoring & Export
│   ├── __init__.py
│   ├── analyzer.py                 # TestbenchAnalyzer
│   ├── models.py
│   ├── config.py
│   ├── scorers/                    # Tier1/Tier2 scorers
│   │   ├── tier1_scorer.py
│   │   └── tier2_scorer.py
│   ├── questa/                     # Questa integration
│   │   ├── functional_coverage.py
│   │   ├── assertion_coverage.py
│   │   └── uvm_analyzer.py
│   └── exporters/                  # Report exporters
│       ├── html_exporter.py
│       ├── junit_exporter.py
│       ├── csv_exporter.py
│       └── pdf_exporter.py
│
├── designs/                        # Benchmark designs
│   └── fifo_sync/                  # Synchronous FIFO
│       ├── design.sv               # RTL
│       ├── spec.md                 # Specification
│       ├── reference/              # Ground truth
│       │   └── requirements.json
│       ├── bugs/                   # Seeded bugs
│       └── eval_config.json
│
├── sample_outputs/                 # Example outputs
│   └── verifagent_fifo/           # VerifAgent example
│
├── tb_eval/                        # TB-Eval (VerifLLMBench)
│   ├── runner.py
│   ├── simulator.py
│   └── examples/                   # Example testbenches
│       ├── adder_single/
│       ├── fifo_single/
│       └── fifo_multi/
│
├── formal_eval/                    # Formal verification eval
│   └── examples/
│
├── tests/                          # Unit and integration tests
│   ├── integration/
│   └── fixtures/
│
├── docs/                           # Documentation
│   ├── INTEGRATION.md              # CI/CD integration
│   ├── CLI_USAGE.md                # CLI reference
│   ├── CLI_QUICK_REFERENCE.md
│   ├── EXAMPLES.md                 # Usage examples
│   └── step5_architecture.md       # Architecture details
│
└── Documentation/                  # Generated reports
    ├── PIPELINE_RUN_SUMMARY.md
    ├── VERILATOR_PIPELINE_DEMO.md
    ├── PIPELINE_STATUS.md
    ├── COMPLETE_PIPELINE_RUN.md
    ├── FINAL_SUMMARY.md
    └── SUCCESS_REPORT.md           # Complete test results
```

---

## 🔧 Configuration

### Simulator Version Requirements

| Simulator | Minimum Version | CocoTB Compatibility |
|-----------|----------------|---------------------|
| Verilator | 5.020 | CocoTB 1.9.x |
| Verilator | 5.036+ | CocoTB 2.0+ |
| Icarus Verilog | 11.0 | All versions |
| GHDL | 2.0 | VUnit |
| Questa | 2021.1 | N/A (UVM-SV) |

### Environment Setup

Create `.tbeval.yaml` in your project:

```yaml
execution:
  timeouts:
    per_test_seconds: 600
    global_seconds: 3600
  retry:
    enabled: true
    max_attempts: 3

simulators:
  preferred_simulator: verilator
  questa:
    license_server: "1234@license-server"
    installation_path: "/opt/questa"

coverage:
  enabled: true
  types:
    - line
    - toggle
    - branch
  thresholds:
    line: 90.0
    branch: 80.0

quality_gate:
  enabled: true
  fail_on_error: false
  linters:
    - verible
    - ghdl
```

---

## 📈 Scoring Methodology

### Tier 1: Open Source (Verilator/Icarus/GHDL)

**Total: 100 points**

| Component | Points | Description |
|-----------|--------|-------------|
| **Structural Coverage** | 35 | Line coverage (35%) + Toggle coverage (20%) + Branch (10%) + FSM (10%) |
| **Code Quality** | 15 | Lint compliance, coding standards, style issues |
| **Test Efficiency** | 20 | Coverage per second, redundancy analysis, test design |
| **Test Pass Rate** | 15 | Percentage of passing tests, stability |
| **Behavioral Accuracy** | 15 | Correctness validation, expected behavior matching |

**Grade Scale**:
- **A (90-100)**: Excellent - Production ready
- **B (80-89)**: Good - Minor improvements needed
- **C (70-79)**: Acceptable - Some gaps remain
- **D (60-69)**: Needs work - Significant issues
- **F (<60)**: Failing - Major problems

### Tier 2: Professional (Questa/VCS/Xcelium)

**Total: 100 points**

| Component | Points | Description |
|-----------|--------|-------------|
| **Functional Coverage** | 25 | Covergroups, bins, crosses, transitions |
| **Assertion Coverage** | 20 | SVA properties, pass/fail ratios, vacuity |
| **Structural Coverage** | 20 | Line + branch + toggle |
| **UVM Compliance** | 15 | Proper UVM architecture, phases, TLM |
| **Code Quality** | 10 | Lint compliance, UVM best practices |
| **Test Stability** | 10 | Simulation reliability, no X/Z propagation |

---

## 🎯 Benchmark Designs

### Current Benchmarks

1. **Synchronous FIFO** (`designs/fifo_sync/`)
   - Parameterizable depth and data width
   - Status flags (full, empty, almost_full, almost_empty)
   - Count tracking and error detection
   - Ground truth from SystemVerilog Assertions Handbook

2. **Simple Adder** (`tb_eval/examples/adder_single/`)
   - 8-bit adder with carry
   - 5 comprehensive tests
   - 100% achievable coverage

3. **Multi-file FIFO** (`tb_eval/examples/fifo_multi/`)
   - More complex project structure
   - Multiple file testbench

### Adding Custom Benchmarks

```bash
# 1. Create design directory
mkdir -p designs/my_design

# 2. Add RTL
cp my_dut.sv designs/my_design/design.sv

# 3. Create specification
cat > designs/my_design/spec.md << EOF
# My Design Specification
...
EOF

# 4. Define ground truth
cat > designs/my_design/reference/requirements.json << EOF
{
  "requirements": [
    {"id": "REQ_001", "description": "...", "type": "functional"}
  ]
}
EOF

# 5. Configure evaluation
cat > designs/my_design/eval_config.json << EOF
{
  "thresholds": {"line_coverage": 95.0, "functional_coverage": 90.0}
}
EOF
```

---

## 🧪 Testing

### Run Unit Tests

```bash
# Install test dependencies
pip install pytest pytest-cov

# Run all tests
pytest tests/ -v

# Run with coverage
pytest tests/ --cov=tb_classif --cov=step4_execute --cov=step5_coverage

# Run specific test category
pytest tests/integration/ -v
```

### Run Integration Tests

```bash
# Test complete pipeline on examples
python run_eval.py --eval tb_eval --examples

# Test specific project
python run_eval.py --eval tb_eval --project tb_eval/examples/adder_single --verbose
```

---

## 📚 Documentation

- **[QUICKSTART.md](QUICKSTART.md)**: Getting started guide
- **[docs/CLI_USAGE.md](docs/CLI_USAGE.md)**: Complete CLI reference
- **[docs/INTEGRATION.md](docs/INTEGRATION.md)**: CI/CD integration guide
- **[docs/EXAMPLES.md](docs/EXAMPLES.md)**: Usage examples and recipes
- **[SUCCESS_REPORT.md](SUCCESS_REPORT.md)**: Complete test results and validation

---

## 🤝 Contributing

We welcome contributions! Areas for improvement:

1. **Add More Parsers**: Support additional coverage formats
2. **New Benchmarks**: Contribute reference designs
3. **Simulator Support**: Add support for new simulators
4. **Scoring Algorithms**: Enhance scoring methodology
5. **Documentation**: Improve guides and examples

### Development Setup

```bash
# Fork and clone
git clone https://github.com/yourusername/VerifEval.git
cd VerifEval

# Create branch
git checkout -b feature/my-feature

# Install dev dependencies
pip install -e '.[dev]'

# Run tests
pytest tests/ -v

# Submit PR
git push origin feature/my-feature
```

---

## 📊 Results & Benchmarks

### Verified Test Results

**Adder Example** (CocoTB + Verilator):
- ✅ 5/5 tests passed (100%)
- ✅ 100% line coverage
- ✅ 100% toggle coverage
- ✅ Score: 93.5/100 (Grade A)
- ✅ Execution time: 0.01s

See [SUCCESS_REPORT.md](SUCCESS_REPORT.md) for complete results.

### AI Tool Comparisons

*Coming soon: Comprehensive benchmarks comparing GPT-4, Claude, Gemini, and specialized verification agents.*

---

## 🔗 Related Projects

- **[VerilogEval](https://github.com/NVlabs/verilog-eval)**: RTL code generation benchmark
- **[CocoTB](https://www.cocotb.org/)**: Python-based verification framework
- **[VUnit](https://vunit.github.io/)**: HDL unit testing framework
- **[Verilator](https://www.veripool.org/verilator/)**: Fast open-source simulator

---

## 📄 License

MIT License - see [LICENSE](LICENSE) for details

---

## 📞 Contact & Support

- **Issues**: [GitHub Issues](https://github.com/SigmanticAI/VerifEval/issues)
- **Discussions**: [GitHub Discussions](https://github.com/SigmanticAI/VerifEval/discussions)
- **Email**: contact@sigmanticai.com

---

## 📖 Citation

If you use VerifEval in your research, please cite:

```bibtex
@software{verifeval2026,
  title = {VerifEval: A Comprehensive Benchmark Framework for AI-Generated Hardware Verification},
  author = {SigmanticAI},
  year = {2026},
  url = {https://github.com/SigmanticAI/VerifEval},
  note = {First standardized methodology for evaluating verification testbench quality}
}
```

---

## 🎉 Acknowledgments

- SystemVerilog Assertions Handbook for ground truth references
- CocoTB and VUnit communities for excellent testing frameworks
- Verilator team for fast, open-source simulation
- All contributors and early adopters

---

**Built with ❤️ for the hardware verification community**
