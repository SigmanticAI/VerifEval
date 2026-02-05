# Summary Reporter Usage

## Basic Usage

### Print to Console
```python
from step4_execute.reporters import print_summary, SummaryVerbosity

# Normal verbosity (default)
print_summary(report)

# Detailed output
print_summary(report, verbosity=SummaryVerbosity.DETAILED)

# Minimal output
print_summary(report, verbosity=SummaryVerbosity.MINIMAL)
