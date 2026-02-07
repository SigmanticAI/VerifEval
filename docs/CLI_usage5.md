Copy# CLI Usage Guide

## Installation

```bash
pip install -e .
Basic Usage
bashCopypython -m step5_coverage --test-report <path_to_test_report.json>
Command-Line Options
Input Files

--test-report PATH: Path to test_report.json (required)
--build-manifest PATH: Path to build_manifest.json (auto-detected)
--config PATH: Path to .tbeval.yaml configuration file

Output Options

--output DIR: Output directory (default: .tbeval/coverage)
--report-name NAME: Output filename (default: coverage_report.json)
--summary: Generate human-readable summary
--json-detail LEVEL: Detail level: summary, normal, full

Analysis Options

--no-per-test: Disable per-test tracking
--no-hotspots: Skip hotspot identification
--no-mutation: Skip mutation data generation

Thresholds

--line-threshold PCT: Minimum line coverage %
--branch-threshold PCT: Minimum branch coverage %
--toggle-threshold PCT: Minimum toggle coverage %
--fail-on-threshold: Exit with error if thresholds not met

Display Options

--verbose, -v: Verbose output
--debug: Debug output
--quiet, -q: Minimal output
--no-color: Disable colored output

Diagnostic Commands

--list-parsers: Show available parsers
--check-config: Validate configuration
--dry-run: Validate inputs without analysis
--version: Show version
--help: Show help message

Examples
Basic Analysis
bashCopypython -m step5_coverage --test-report test_report.json
With Custom Thresholds
bashCopypython -m step5_coverage \
    --test-report test_report.json \
    --line-threshold 85 \
    --branch-threshold 95
Generate All Reports
bashCopypython -m step5_coverage \
    --test-report test_report.json \
    --summary \
    --output ./coverage_reports
CI/CD Integration
bashCopy# Fail build if thresholds not met
python -m step5_coverage \
    --test-report test_report.json \
    --fail-on-threshold \
    --quiet
Exit Codes

0: Success
1: Analysis failed or thresholds not met (with --fail-on-threshold)

Configuration File
Instead of CLI arguments, use .tbeval.yaml:
yamlCopycoverage:
  analysis:
    thresholds:
      line: 85.0
      branch: 95.0
      toggle: 75.0
    
    reporting:
      output_dir: "./coverage_reports"
      json_detail_level: "full"
Then run:
bashCopypython -m step5_coverage --config .tbeval.yaml
