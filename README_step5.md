# TB Eval - Step 5: Coverage Analysis

[![Python 3.7+](https://img.shields.io/badge/python-3.7+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)

**Comprehensive coverage analysis for hardware verification testbenches**

Step 5 of the TB Eval framework processes coverage data from hardware verification tests, calculates detailed metrics, identifies test suite quality issues, and generates reports for downstream analysis and scoring.

## 🌟 Features

### Core Capabilities
- ✅ **Multi-format Support**: Verilator, LCOV, Covered (extensible)
- ✅ **Automatic Detection**: Smart coverage format detection
- ✅ **Comprehensive Metrics**: Line, branch, toggle, FSM coverage
- ✅ **Per-test Tracking**: Unique contribution analysis (Q13)
- ✅ **Hierarchical Analysis**: Merged + per-test + differential (Q4.1)
- ✅ **Test Optimization**: Identify essential and redundant tests
- ✅ **Mutation Targets**: Generate targets for mutation testing (Step 6)
- ✅ **CI/CD Ready**: Exit codes, thresholds, quiet mode

### Analysis Features
- Line coverage calculation with uncovered hotspot identification
- Branch coverage (full/partial/uncovered tracking)
- Toggle coverage (signal transition analysis)
- FSM state/transition coverage (Phase 2)
- Weighted scoring for Step 7 integration
- Test efficiency and redundancy scoring
- Optimal test execution order calculation
- Coverage convergence analysis

## 📦 Installation

### From Source
```bash
git clone https://github.com/tbeval/step5_coverage.git
cd step5_coverage
pip install -e .
Dependencies
bashCopypip install -r requirements.txt
Optional External Tools (for enhanced functionality):

verilator_coverage - Verilator coverage processing
lcov / genhtml - LCOV coverage reports
covered - Covered tool support

🚀 Quick Start
Command Line
bashCopy# Basic usage
python -m step5_coverage --test-report test_report.json

# With configuration
python -m step5_coverage --config .tbeval.yaml

# Custom thresholds
python -m step5_coverage \
    --test-report test_report.json \
    --line-threshold 85 \
    --branch-threshold 95 \
    --output ./coverage_reports
Python API
pythonCopyfrom step5_coverage import CoverageAnalyzer

# Create analyzer
analyzer = CoverageAnalyzer.from_test_report("test_report.json")

# Run analysis
result = analyzer.analyze()

if result.success:
    report = result.report
    print(f"Coverage: {report.structural_coverage.weighted_score:.2%}")
    analyzer.save_report(report)
📊 Input/Output
Inputs

test_report.json: Test execution results from Step 4
build_manifest.json: Build metadata from Step 3
Coverage files: .dat, .info, .lcov, .cdd

Outputs

coverage_report.json: Structured coverage analysis (Step 7 input)
coverage_summary.txt: Human-readable summary
enriched_test_report.json: Test report with coverage data

📖 Documentation

User Guide: Complete usage instructions
API Reference: Python API documentation
Architecture: System design (team members)
Development Guide: Contributing guidelines
Examples: Code examples and recipes

🔧 Configuration
Create .tbeval.yaml:
yamlCopycoverage:
  analysis:
    thresholds:
      line: 80.0
      branch: 90.0
      toggle: 70.0
      overall: 80.0
    
    weights:
      line: 0.35
      branch: 0.35
      toggle: 0.20
      fsm: 0.10
    
    reporting:
      output_dir: ".tbeval/coverage"
      json_detail_level: "full"
      export_mutation_targets: true
🧪 Testing
bashCopy# Run all tests
pytest

# With coverage
pytest --cov=step5_coverage --cov-report=html

# Specific test file
pytest tests/test_analyzer.py -v
📈 Example Output
CopyCoverage Summary:
  Line:    86.67% (13/15)
  Branch:  50.00% (2/4)
  Toggle:  50.00% (1/2)
  FSM:     100.00%
  Overall: 67.84% (weighted)

Per-Test Analysis:
  Essential Tests (2):
    • test_basic
    • test_overflow
  
  Redundant Tests (1):
    • test_duplicate

Mutation Testing Targets:
  Uncovered lines:     2
  Weak branches:       1
  Untoggled signals:   1
🤝 Integration
CI/CD Pipeline
bashCopy# Run with threshold enforcement
python -m step5_coverage \
    --test-report test_report.json \
    --fail-on-threshold \
    --quiet
Step 7 Integration
pythonCopy# Step 5 generates coverage_report.json
# Step 7 reads it for scoring
import json

with open("coverage_report.json") as f:
    coverage = json.load(f)

score = coverage["structural_coverage"]["weighted_score"]
print(f"Coverage score for Step 7: {score}")
🏗️ Architecture
CopyStep 4 (Execute Tests)
    ↓
    test_report.json + coverage files
    ↓
Step 5: Coverage Analysis
    ├─→ Format Detection (Verilator/LCOV/Covered)
    ├─→ Parsing (External tools + Python fallback)
    ├─→ Metrics Calculation (Line/Branch/Toggle/FSM)
    ├─→ Per-test Tracking (Unique contributions)
    └─→ Report Generation (coverage_report.json)
    ↓
Step 6: Mutation Testing (uses mutation targets)
Step 7: Scoring (uses weighted_score)
📋 Requirements Mapping

Q1.3: Loads test_report.json and build_manifest.json
Q4.1: Generates hierarchical coverage (merged + per-test)
Q4.2: Calculates mandatory metrics for Step 7
Q5.1: Generates mutation targets for Step 6
Q5.2: Provides agent-friendly JSON output
Q6.1/Q6.2: Coverage merging (tool + Python fallback)
Q7.1: Threshold validation (warning-only by default)
Q11: Parser priority (Verilator → LCOV → Covered)
Q12: External tool + Python fallback strategy
Q13: Advanced per-test contribution tracking

🐛 Troubleshooting
Coverage files not found
bashCopy# Check test_report.json contains coverage_file paths
python -m step5_coverage --dry-run --test-report test_report.json
Parser issues
bashCopy# List available parsers
python -m step5_coverage --list-parsers

# Enable debug mode
python -m step5_coverage --test-report test_report.json --debug
Configuration issues
bashCopy# Validate configuration
python -m step5_coverage --config .tbeval.yaml --check-config
📝 License
MIT License - see LICENSE file
👥 Authors
TB Eval Team
🔗 Related Projects

Step 4: Test Execution
Step 6: Mutation Testing
Step 7: Scoring

📞 Support

Issues: https://github.com/tbeval/step5_coverage/issues
Discussions: https://github.com/tbeval/step5_coverage/discussions
Email: support@tbeval.org

Copy
