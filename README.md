# VerifEval - Hardware Verification Benchmark Framework

A comprehensive benchmark framework for evaluating AI-generated hardware verification environments using **Siemens Questa**.

---

## Table of Contents

1. [Overview](#overview)
2. [Prerequisites](#prerequisites)
3. [License Configuration](#license-configuration)
4. [Installation](#installation)
5. [Quick Start](#quick-start)
6. [Evaluation Modes](#evaluation-modes)
   - [UVM Evaluation](#uvm-evaluation)
   - [Formal Evaluation](#formal-evaluation)
   - [Specification Evaluation](#specification-evaluation)
7. [Directory Structure](#directory-structure)
8. [Configuration](#configuration)
9. [Creating Test Projects](#creating-test-projects)
10. [Scoring Methodology](#scoring-methodology)
11. [Troubleshooting](#troubleshooting)
12. [API Reference](#api-reference)
13. [Examples](#examples)
14. [Contributing](#contributing)

---

## Overview

VerifEval provides a standardized methodology for assessing the quality of automatically generated:
- **UVM testbenches** - Universal Verification Methodology environments
- **SystemVerilog Assertions (SVA)** - Formal property specifications
- **Functional coverage** - Coverage metrics and goals

### Key Features

| Feature | Description |
|---------|-------------|
| **Multi-mode Evaluation** | UVM simulation, formal verification, and spec-based analysis |
| **Questa Integration** | Native support for Siemens Questa tools |
| **Coverage Collection** | Automatic UCDB coverage analysis |
| **Detailed Metrics** | Line, branch, toggle, FSM, and functional coverage |
| **Formal Verification** | Assertion proofs and cover point reachability |
| **Fuzzy Matching** | Semantic comparison of generated vs expected verification |
| **Extensible Design** | Easy to add new benchmark designs |

---

## Prerequisites

### Required Software

1. **Siemens Questa** (QuestaSim or Questa Prime)
   - Includes: `vlib`, `vlog`, `vopt`, `vsim`, `vcover`
   - Optional: `qformal` for formal verification

2. **Python 3.8+**

3. **Valid Questa License**
   - License server access configured

### Verifying Questa Installation

```bash
# Check if Questa tools are in PATH
which vsim
which vlog
which vcover

# Check Questa version
vsim -version
```

---

## License Configuration

Questa requires a valid license from a FlexLM license server. Configure the license using one of these methods:

### Method 1: Environment Variable (Recommended)

```bash
# Add to ~/.bashrc or ~/.zshrc for persistence
export QUESTA_LICENSE="port@server"

# Example:
export QUESTA_LICENSE="1717@license.company.com"
```

### Method 2: Standard FlexLM Variables

```bash
export LM_LICENSE_FILE="1717@license.company.com"
# or
export MGLS_LICENSE_FILE="1717@license.company.com"
```

### Method 3: Runtime Configuration (Python)

```python
from questa.config import set_license

# Configure license at runtime
set_license("1717@license.company.com")
```

### Verifying License Configuration

```bash
# Check if license is configured correctly
python run_eval.py --check-license
```

Expected output when configured correctly:
```
============================================================
QUESTA CONFIGURATION
============================================================

License: 1717@license.company.com
Install Path: /opt/questasim/2024.1
Edition: questa_prime
UVM Version: 1.2

Tool Paths:
  vlib:   /opt/questasim/2024.1/bin/vlib
  vlog:   /opt/questasim/2024.1/bin/vlog
  vsim:   /opt/questasim/2024.1/bin/vsim
  vcover: /opt/questasim/2024.1/bin/vcover

✓ Configuration valid
============================================================

✓ License check passed - Questa is accessible
```

---

## Installation

### Step 1: Clone the Repository

```bash
git clone https://github.com/SigmanticAI/VerifEval.git
cd VerifEval
git checkout questa_version
```

### Step 2: Install Python Dependencies

```bash
pip install -r requirements.txt
```

### Step 3: Configure License

```bash
export QUESTA_LICENSE="port@server"
```

### Step 4: Verify Installation

```bash
python run_eval.py --check-license
```

---

## Quick Start

### 1. Check License Configuration

```bash
python run_eval.py --check-license
```

### 2. Run UVM Evaluation

```bash
# Evaluate a verification project
python run_eval.py --eval uvm_eval --project sample_outputs/verifagent_fifo

# Run built-in examples
python run_eval.py --eval uvm_eval --examples
```

### 3. Run Formal Evaluation

```bash
# Evaluate SVA assertions
python run_eval.py --eval formal_eval --project path/to/assertions

# Run with custom BMC depth
python run_eval.py --eval formal_eval --project path/to/project --depth 30
```

### 4. Run Specification Evaluation

```bash
# Evaluate against design specification
python run_eval.py --eval spec_eval --design fifo_sync
```

---

## Evaluation Modes

### UVM Evaluation (`uvm_eval`)

Evaluates UVM testbenches using Questa simulation.

**What it measures:**
- Build/compile success rate
- Test pass rate
- Coverage metrics:
  - Line coverage
  - Branch coverage
  - Toggle coverage
  - FSM state coverage
  - Assertion coverage
  - Functional coverage (covergroups)

**Questa tools used:**
- `vlib` - Create work library
- `vlog` - Compile SystemVerilog with UVM
- `vsim` - Run simulation
- `vcover` - Extract coverage

**Usage:**

```bash
# Single project
python run_eval.py --eval uvm_eval --project path/to/verif

# Multiple projects
python run_eval.py --eval uvm_eval --projects proj1 proj2 proj3

# Multiple runs for consistency
python run_eval.py --eval uvm_eval --project path/to/verif --runs 3

# Keep work directory for debugging
python run_eval.py --eval uvm_eval --project path/to/verif --keep-work
```

**Expected project structure:**

```
my_verification_project/
├── design_spec.json         # Design specification (optional)
├── verification_plan.json   # Verification plan with test list
├── tb/
│   ├── tb_top.sv           # Testbench top module
│   ├── env/
│   │   └── env.sv          # UVM environment
│   ├── agents/
│   │   ├── my_agent.sv     # UVM agent
│   │   └── my_if.sv        # Interface
│   └── tests/
│       └── tests.sv        # UVM tests
├── assertions/
│   └── my_assertions.sv    # SVA assertions
└── coverage/
    └── my_coverage.sv      # Covergroups
```

**Example output:**

```
============================================================
Evaluating: verifagent_fifo
============================================================
  Source files: 8
  Top module: tb_top

  Running test: base_test
    ✓ Compile successful (2.3s)
    ✓ Simulation successful (15.7s)
      Test: PASSED
      UVM Errors: 0
      Coverage: 87.5%

============================================================
UVM EVAL RESULTS: verifagent_fifo
============================================================

Compile Success Rate: 1/1 (100%)
Simulation Success Rate: 1/1 (100%)
Test Pass Rate: 1/1 (100%)
Average Coverage: 87.5%
============================================================
```

---

### Formal Evaluation (`formal_eval`)

Evaluates SystemVerilog Assertions using Questa Formal.

**What it measures:**
- Assertion proof rate (proven/failed/unknown)
- Cover point reachability
- Syntax/parse success

**Questa tools used:**
- `vlog` - Compile with formal options
- `qformal` - Run formal verification (if available)
- `vsim -formal` - Fallback formal verification

**Usage:**

```bash
# Single project
python run_eval.py --eval formal_eval --project path/to/assertions

# With custom BMC depth
python run_eval.py --eval formal_eval --project path --depth 50

# Multiple runs
python run_eval.py --eval formal_eval --project path --runs 3
```

**Expected project structure:**

```
my_formal_project/
├── rtl/
│   └── dut.sv              # Design under test
└── sva/
    └── assertions.sv       # SVA assertions and covers
```

**Example assertions file:**

```systemverilog
// assertions.sv
module dut_assertions (
    input logic clk,
    input logic rst_n,
    input logic [7:0] data_in,
    output logic [7:0] data_out
);

    // Assertion: Output should never be X after reset
    no_x_after_reset: assert property (
        @(posedge clk) disable iff (!rst_n)
        !$isunknown(data_out)
    );

    // Assertion: Data integrity check
    data_integrity: assert property (
        @(posedge clk) disable iff (!rst_n)
        (valid_in |-> ##1 (data_out == $past(data_in)))
    );

    // Cover: Verify we can reach max value
    cover_max_value: cover property (
        @(posedge clk) data_out == 8'hFF
    );

endmodule
```

**Example output:**

```
============================================================
Formal Verification: counter_single
============================================================
  ✓ Parse successful
  Assertions: 5 found
    ✓ 4 proven
    ✗ 0 failed
    ? 1 unknown
  Proof Rate: 80.0%
  Score: 78.0/100
```

---

### Specification Evaluation (`spec_eval`)

Evaluates verification output against design specifications.

**What it measures:**

| Dimension | Points | Description |
|-----------|--------|-------------|
| Specification Extraction | 15 | Correctly identifying design features |
| Requirements Coverage | 20 | Matching functional requirements |
| Corner Cases | 10 | Identifying edge conditions |
| Assertions | 15 | SVA property coverage |
| Code Generation | 25 | UVM structure and quality |
| Coverage Strategy | 15 | Functional coverage completeness |

**Usage:**

```bash
# Evaluate specific design
python run_eval.py --eval spec_eval --design fifo_sync

# Evaluate all designs
python run_eval.py --eval spec_eval --all
```

**Example output:**

```
======================================================================
Evaluating design: fifo_sync
======================================================================

[1/4] Evaluating specification extraction...
      Score: 15.00 / 25.00

[2/4] Evaluating verification planning...
      Score: 18.33 / 25.00

[3/4] Evaluating code generation...
      Score: 22.23 / 25.00

[4/4] Evaluating verification completeness...
      Score: 15.00 / 25.00

======================================================================
TOTAL SCORE: 70.56 / 100
======================================================================
```

---

## Directory Structure

```
VerifEval/
├── README.md                   # This file - comprehensive documentation
├── requirements.txt            # Python dependencies
├── run_eval.py                 # Main evaluation runner
│
├── questa/                     # Questa integration module
│   ├── __init__.py
│   ├── config.py               # License and tool configuration
│   ├── simulator.py            # UVM simulation (vlog, vsim)
│   ├── coverage.py             # Coverage analysis (vcover)
│   └── formal.py               # Formal verification (qformal)
│
├── evaluator/                  # Specification evaluation
│   ├── __init__.py
│   ├── metrics.py              # Scoring algorithms
│   ├── runner.py               # Benchmark runner
│   └── scorer.py               # Reporting system
│
├── pipeline/                   # Evaluation pipeline utilities
│   ├── __init__.py
│   ├── evaluator.py
│   └── reporter.py
│
├── designs/                    # Benchmark designs with ground truth
│   └── fifo_sync/
│       ├── design.sv           # Original RTL
│       ├── design_final.sv     # Corrected RTL
│       ├── spec.md             # Design specification
│       ├── eval_config.json    # Evaluation configuration
│       ├── reference/
│       │   └── requirements.json  # Ground truth requirements
│       └── bugs/
│           └── manifest.json   # Seeded bugs for testing
│
├── sample_outputs/             # Example verification outputs
│   └── verifagent_fifo/        # Example UVM testbench
│       ├── design_spec.json
│       ├── verification_plan.json
│       ├── tb/                 # Testbench files
│       ├── assertions/         # SVA assertions
│       └── coverage/           # Covergroups
│
├── golden_rtl/                 # Reference RTL designs
│   ├── fifo/                   # FIFO implementations
│   ├── uart/                   # UART IP
│   ├── spi/                    # SPI IP
│   ├── i2c/                    # I2C IP
│   └── axi/                    # AXI components
│
├── specifications/             # Design specifications (PDFs)
│   ├── synch_fifo_verif_spec.pdf
│   ├── UART_spec.pdf
│   ├── spi.pdf
│   └── I2C Master Core Specifications.pdf
│
├── results/                    # Evaluation results
│   ├── BENCHMARK_RESULTS.md
│   └── BENCHMARK_RESULTS.pdf
│
├── baseline_comparison/        # Comparison data
│   ├── claude_verification/
│   └── results/
│
├── tests/                      # Python unit tests
│   ├── __init__.py
│   └── test_pipeline.py
│
└── tools/                      # Utility scripts
    └── convert_ground_truth.py
```

---

## Configuration

### Questa Configuration Options

The `questa/config.py` module provides comprehensive configuration:

```python
from questa.config import QuestaConfig, configure, get_config

# Get current configuration
config = get_config()

# Configure with custom options
config = configure(
    license_file="1717@license.company.com",
    install_path="/opt/questasim/2024.1",
    uvm_version="1.2",
    timeout_sec=600,
    verbose=True,
    generate_waves=True,
    wave_format="wlf",
    extra_vlog_args=["+define+DEBUG"],
    extra_vsim_args=["-suppress", "3829"]
)

# Print configuration for debugging
from questa.config import print_config
print_config()
```

### Configuration Options Reference

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `license_file` | str | None | License server (port@server) |
| `install_path` | Path | Auto-detect | Questa installation path |
| `uvm_version` | str | "1.2" | UVM version to use |
| `work_dir` | Path | "work" | Working directory |
| `coverage_db` | Path | "coverage.ucdb" | Coverage database file |
| `timeout_sec` | int | 300 | Simulation timeout (seconds) |
| `verbose` | bool | False | Enable verbose output |
| `generate_waves` | bool | True | Generate waveform files |
| `wave_format` | str | "wlf" | Waveform format (wlf, vcd) |
| `extra_vlog_args` | list | [] | Additional vlog arguments |
| `extra_vsim_args` | list | [] | Additional vsim arguments |

### Environment Variables

| Variable | Description |
|----------|-------------|
| `QUESTA_LICENSE` | Primary license server specification |
| `LM_LICENSE_FILE` | Standard FlexLM license variable |
| `MGLS_LICENSE_FILE` | Mentor Graphics license variable |
| `UVM_HOME` | Path to UVM library (optional) |

---

## Creating Test Projects

### UVM Testbench Project

To create a project for UVM evaluation:

#### 1. Create directory structure

```bash
mkdir -p my_project/{tb/{env,agents,tests},assertions,coverage}
```

#### 2. Create verification_plan.json

```json
{
  "project_name": "my_dut_verification",
  "top_module": "tb_top",
  "tests": [
    {"name": "base_test", "description": "Basic functionality test"},
    {"name": "reset_test", "description": "Reset behavior test"},
    {"name": "random_test", "description": "Random stimulus test"}
  ],
  "assertions": [
    {"name": "no_x_outputs", "description": "Outputs never X after reset"},
    {"name": "protocol_check", "description": "Protocol compliance"}
  ],
  "covergroups": [
    {"name": "operation_cg", "description": "Operation coverage"},
    {"name": "state_cg", "description": "State machine coverage"}
  ]
}
```

#### 3. Create tb_top.sv

```systemverilog
`timescale 1ns/1ps

module tb_top;
    import uvm_pkg::*;
    `include "uvm_macros.svh"
    
    // Clock and reset
    logic clk;
    logic rst_n;
    
    // Clock generation
    initial begin
        clk = 0;
        forever #5 clk = ~clk;
    end
    
    // Reset sequence
    initial begin
        rst_n = 0;
        #100;
        rst_n = 1;
    end
    
    // DUT instantiation
    my_dut dut (
        .clk(clk),
        .rst_n(rst_n),
        // ... other ports
    );
    
    // Interface
    my_if vif(clk, rst_n);
    
    // Connect interface to DUT
    assign vif.data_in = dut.data_in;
    // ...
    
    // UVM configuration
    initial begin
        uvm_config_db#(virtual my_if)::set(null, "*", "vif", vif);
        run_test();
    end
    
endmodule
```

#### 4. Run evaluation

```bash
python run_eval.py --eval uvm_eval --project my_project
```

### Formal Verification Project

To create a project for formal evaluation:

#### 1. Create directory structure

```bash
mkdir -p my_formal_project/{rtl,sva}
```

#### 2. Add design file (rtl/dut.sv)

```systemverilog
module my_dut (
    input  logic clk,
    input  logic rst_n,
    input  logic [7:0] data_in,
    input  logic valid_in,
    output logic [7:0] data_out,
    output logic valid_out
);
    // Implementation
endmodule
```

#### 3. Add assertions file (sva/assertions.sv)

```systemverilog
module my_dut_assertions (
    input logic clk,
    input logic rst_n,
    input logic [7:0] data_in,
    input logic valid_in,
    input logic [7:0] data_out,
    input logic valid_out
);

    // Properties
    property valid_follows_data;
        @(posedge clk) disable iff (!rst_n)
        valid_in |-> ##[1:3] valid_out;
    endproperty

    // Assertions
    valid_timing: assert property (valid_follows_data)
        else $error("Valid timing violation");

    // Covers
    all_ones_cover: cover property (
        @(posedge clk) data_out == 8'hFF
    );

endmodule
```

#### 4. Run evaluation

```bash
python run_eval.py --eval formal_eval --project my_formal_project --depth 20
```

---

## Scoring Methodology

### UVM Evaluation Scoring

| Metric | Weight | Description |
|--------|--------|-------------|
| Compile Success | 20% | Source files compile without errors |
| Test Pass Rate | 30% | UVM tests pass without UVM_FATAL/ERROR |
| Line Coverage | 15% | Percentage of RTL lines executed |
| Branch Coverage | 15% | Percentage of branches taken |
| Functional Coverage | 20% | Covergroup coverage |

**Overall Score** = Weighted average of all metrics

### Formal Evaluation Scoring

| Metric | Weight | Description |
|--------|--------|-------------|
| Syntax Success | 30% | Parse and synthesis successful |
| Proof Rate | 50% | Percentage of assertions proven |
| Cover Rate | 20% | Percentage of cover points reached |

**Overall Score** = 0.30 × Syntax + 0.50 × ProofRate + 0.20 × CoverRate

### Specification Evaluation Scoring

| Dimension | Points | Sub-metrics |
|-----------|--------|-------------|
| Spec Extraction | 15 | Module detection (5), Ports (5), Parameters (3), FSM (5), Requirements (7) |
| Verification Planning | 20 | Test coverage (10), Assertion planning (8), Coverage strategy (7) |
| Corner Cases | 10 | Edge condition identification |
| Assertions | 15 | Critical assertions coverage |
| Code Generation | 25 | Compilability (10), UVM compliance (5), Quality (5), Interface (5) |
| Coverage Strategy | 15 | Covergroup completeness |

**Total: 100 points**

---

## Troubleshooting

### License Issues

**Problem:** License check fails

```
✗ License check failed
```

**Solutions:**

1. Verify license server is running:
   ```bash
   lmstat -a -c $QUESTA_LICENSE
   ```

2. Check firewall allows connection to license server port

3. Verify license file format:
   ```bash
   echo $QUESTA_LICENSE
   # Should be: port@server (e.g., 1717@license.company.com)
   ```

4. Try alternative environment variable:
   ```bash
   export LM_LICENSE_FILE="1717@license.company.com"
   ```

### Compilation Errors

**Problem:** vlog compilation fails

```
** Error: (vlog-xxx) ...
```

**Solutions:**

1. Check SystemVerilog syntax:
   ```bash
   vlog -sv +acc my_file.sv
   ```

2. Verify UVM is available:
   ```bash
   vlog -sv +incdir+$UVM_HOME/src $UVM_HOME/src/uvm_pkg.sv
   ```

3. Add missing include directories:
   ```python
   from questa.config import configure
   configure(extra_vlog_args=["+incdir+./includes"])
   ```

### Simulation Timeouts

**Problem:** Simulation times out

**Solutions:**

1. Increase timeout:
   ```python
   from questa.config import configure
   configure(timeout_sec=600)  # 10 minutes
   ```

2. Check for infinite loops in testbench

3. Add simulation limits:
   ```systemverilog
   initial begin
       #1000000;  // Max simulation time
       $finish;
   end
   ```

### Coverage Not Collected

**Problem:** Coverage percentages are 0%

**Solutions:**

1. Enable coverage in compilation:
   ```python
   simulator.compile(source_files, enable_coverage=True)
   ```

2. Verify UCDB file is created:
   ```bash
   ls -la work/*.ucdb
   ```

3. Check coverage save command in simulation

---

## API Reference

### questa.config Module

```python
# Configure license
from questa.config import set_license, get_config, configure

set_license("1717@license.company.com")

config = get_config()
print(config.license_file)
print(config.vsim_path)

# Full configuration
config = configure(
    license_file="...",
    timeout_sec=600,
    verbose=True
)
```

### questa.simulator Module

```python
from questa.simulator import QuestaSimulator

sim = QuestaSimulator()

# Validate environment
valid, errors = sim.validate_environment()

# Create work library
sim.create_library(work_dir="./work")

# Compile sources
success, errors, warnings = sim.compile(
    source_files=[Path("tb_top.sv")],
    include_dirs=[Path("./includes")],
    defines={"DEBUG": "1"},
    enable_coverage=True
)

# Run simulation
result = sim.simulate(
    top_module="tb_top",
    uvm_test="base_test",
    seed=12345,
    coverage_db=Path("coverage.ucdb")
)

print(f"Pass: {result.passed}")
print(f"Coverage: {result.coverage_percent}%")

# Complete flow (compile + simulate)
result = sim.run_uvm_test(
    source_files=[...],
    top_module="tb_top",
    uvm_test="base_test"
)
```

### questa.coverage Module

```python
from questa.coverage import QuestaCoverageAnalyzer

analyzer = QuestaCoverageAnalyzer()

# Analyze coverage
result = analyzer.analyze("coverage.ucdb")
print(f"Line: {result.line_coverage}%")
print(f"Branch: {result.branch_coverage}%")
print(f"Total: {result.total_coverage}%")

# Merge multiple UCDBs
analyzer.merge(["test1.ucdb", "test2.ucdb"], "merged.ucdb")

# Generate HTML report
analyzer.generate_html_report("coverage.ucdb", "./html_report")
```

### questa.formal Module

```python
from questa.formal import QuestaFormalChecker

checker = QuestaFormalChecker()

# Verify assertions
result = checker.verify(
    source_files=[Path("dut.sv"), Path("assertions.sv")],
    top_module="dut",
    max_depth=30
)

print(f"Proof rate: {result.proof_rate}%")
print(f"Score: {result.overall_score}/100")

for assertion in result.assertions:
    print(f"  {assertion.name}: {assertion.status.value}")
```

---

## Examples

### Example 1: Basic UVM Evaluation

```python
#!/usr/bin/env python3
"""Evaluate a UVM testbench project."""

from pathlib import Path
from questa.config import set_license
from questa.simulator import QuestaSimulator

# Configure license
set_license("1717@license.company.com")

# Create simulator
sim = QuestaSimulator()

# Find source files
project = Path("my_uvm_project")
sources = list(project.rglob("*.sv"))

# Run test
result = sim.run_uvm_test(
    source_files=sources,
    top_module="tb_top",
    uvm_test="base_test"
)

# Print results
print(f"Compile: {'✓' if result.compile_success else '✗'}")
print(f"Simulation: {'✓' if result.simulation_success else '✗'}")
print(f"Test: {'PASSED' if result.test_passed else 'FAILED'}")
print(f"Coverage: {result.coverage_percent:.1f}%")
```

### Example 2: Formal Verification

```python
#!/usr/bin/env python3
"""Run formal verification on SVA assertions."""

from pathlib import Path
from questa.config import set_license
from questa.formal import QuestaFormalChecker

# Configure
set_license("1717@license.company.com")

# Create checker
checker = QuestaFormalChecker()

# Verify project
result = checker.verify_project(
    project_dir=Path("my_formal_project"),
    max_depth=20
)

# Print results
print(result.summary())
```

### Example 3: Coverage Analysis

```python
#!/usr/bin/env python3
"""Analyze coverage from multiple simulation runs."""

from pathlib import Path
from questa.config import set_license
from questa.coverage import QuestaCoverageAnalyzer

# Configure
set_license("1717@license.company.com")

# Create analyzer
analyzer = QuestaCoverageAnalyzer()

# Merge coverage from multiple tests
ucdb_files = [
    Path("test1_coverage.ucdb"),
    Path("test2_coverage.ucdb"),
    Path("test3_coverage.ucdb"),
]

merged = analyzer.merge(ucdb_files, Path("merged_coverage.ucdb"))

# Analyze merged coverage
result = analyzer.analyze(merged)
print(result.summary())

# Generate HTML report
analyzer.generate_html_report(merged, Path("./coverage_report"))
print("HTML report generated in ./coverage_report/")
```

### Example 4: Complete Evaluation Pipeline

```python
#!/usr/bin/env python3
"""Complete evaluation pipeline for AI-generated verification."""

import json
from pathlib import Path
from questa.config import set_license, configure
from questa.simulator import QuestaSimulator
from questa.coverage import QuestaCoverageAnalyzer
from questa.formal import QuestaFormalChecker

def evaluate_verification_project(project_path: Path):
    """Evaluate a complete verification project."""
    
    # Configure Questa
    set_license("1717@license.company.com")
    config = configure(verbose=True, timeout_sec=600)
    
    results = {
        "project": project_path.name,
        "uvm_results": [],
        "formal_results": None,
        "coverage_summary": None,
    }
    
    # Load verification plan
    plan_file = project_path / "verification_plan.json"
    if plan_file.exists():
        with open(plan_file) as f:
            plan = json.load(f)
    else:
        plan = {"tests": [{"name": "base_test"}]}
    
    # Find source files
    sv_files = list(project_path.rglob("*.sv"))
    
    # 1. Run UVM tests
    print("\n=== UVM Evaluation ===")
    sim = QuestaSimulator(config)
    
    for test in plan.get("tests", []):
        test_name = test.get("name", "base_test")
        print(f"\nRunning: {test_name}")
        
        result = sim.run_uvm_test(
            source_files=sv_files,
            top_module="tb_top",
            uvm_test=test_name
        )
        
        results["uvm_results"].append(result.to_dict())
        print(f"  Status: {'PASS' if result.passed else 'FAIL'}")
        print(f"  Coverage: {result.coverage_percent:.1f}%")
    
    # 2. Run formal verification (if assertions exist)
    assertions_dir = project_path / "assertions"
    if assertions_dir.exists():
        print("\n=== Formal Evaluation ===")
        checker = QuestaFormalChecker(config)
        
        formal_result = checker.verify_project(project_path)
        results["formal_results"] = formal_result.to_dict()
        
        print(f"  Assertions: {formal_result.total_assertions}")
        print(f"  Proven: {formal_result.proven_assertions}")
        print(f"  Proof Rate: {formal_result.proof_rate:.1f}%")
    
    # 3. Analyze overall coverage
    print("\n=== Coverage Summary ===")
    analyzer = QuestaCoverageAnalyzer(config)
    
    ucdb_files = list(project_path.glob("*.ucdb"))
    if ucdb_files:
        merged = analyzer.merge(ucdb_files, project_path / "merged.ucdb")
        if merged:
            cov_result = analyzer.analyze(merged)
            results["coverage_summary"] = cov_result.to_dict()
            print(cov_result.summary())
    
    return results


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python example.py <project_path>")
        sys.exit(1)
    
    project = Path(sys.argv[1])
    results = evaluate_verification_project(project)
    
    # Save results
    with open(project / "eval_results.json", "w") as f:
        json.dump(results, f, indent=2)
    
    print(f"\nResults saved to {project}/eval_results.json")
```

---

## Contributing

### Adding New Benchmark Designs

1. Create directory under `designs/`:
   ```
   designs/my_design/
   ├── design.sv           # RTL implementation
   ├── spec.md             # Human-readable specification
   ├── eval_config.json    # Evaluation configuration
   ├── reference/
   │   └── requirements.json  # Ground truth
   └── bugs/               # Optional: seeded bugs
       └── manifest.json
   ```

2. Define ground truth in `requirements.json`:
   ```json
   {
     "functional_requirements": [
       {"id": "REQ-001", "description": "..."}
     ],
     "required_assertions": [
       {"name": "...", "description": "..."}
     ],
     "corner_cases": [
       {"id": "CC-001", "description": "..."}
     ]
   }
   ```

3. Configure evaluation in `eval_config.json`

### Reporting Issues

Please include:
- Questa version (`vsim -version`)
- Operating system
- Complete error output
- Minimal reproducing example

---

## License

MIT License

## Citation

```bibtex
@software{verifeval2026,
  title = {VerifEval: A Benchmark for AI-Generated Hardware Verification},
  author = {SigmanticAI},
  year = {2026},
  url = {https://github.com/SigmanticAI/VerifEval}
}
```

---

*For questions or support, please open an issue on GitHub.*
