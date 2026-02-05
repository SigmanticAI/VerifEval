# tbeval-run Quick Reference

## Common Commands

```bash
# Basic execution
tbeval-run <submission_dir>

# Dry run
tbeval-run --dry-run <submission_dir>

# Filter tests
tbeval-run -f "test_pattern" <submission_dir>

# Verbose output
tbeval-run -v <submission_dir>

# Set timeout
tbeval-run -t 600 <submission_dir>

# Parallel execution
tbeval-run -p 8 <submission_dir>

# Export JUnit
tbeval-run --junit results.xml <submission_dir>
