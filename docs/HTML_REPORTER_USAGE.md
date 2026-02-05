# HTML Reporter Usage

## Overview

The HTML reporter generates interactive, self-contained HTML reports with charts, filtering, and detailed test information.

## Features

- 📊 Interactive charts (pie charts for outcomes, bar charts for duration)
- 🔍 Filterable test results (all, passed, failed, errors, skipped)
- 📝 Expandable test details with tracebacks
- 📱 Mobile-responsive design
- 🎨 Professional styling with gradient header
- 💾 Self-contained (no external dependencies)

## Basic Usage

### Generate from Report
```python
from step4_execute.reporters import generate_html
from pathlib import Path

# Load report
report = TestReport.load(Path("test_report.json"))

# Generate HTML
generate_html(report, Path("report.html"))
