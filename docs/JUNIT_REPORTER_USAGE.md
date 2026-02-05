# JUnit XML Reporter Usage

## Overview

JUnit XML is the standard format for test result reporting in CI/CD systems. This reporter generates compliant JUnit XML from test execution reports.

## Basic Usage

### Generate from Report
```python
from step4_execute.reporters import generate_junit
from pathlib import Path

# Load report
report = TestReport.load(Path("test_report.json"))

# Generate JUnit XML
generate_junit(report, Path("results.xml"))
