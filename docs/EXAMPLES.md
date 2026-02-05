# Examples and Recipes

Practical examples for common use cases with TB Eval Step 4.

## Table of Contents

1. [Basic Examples](#basic-examples)
2. [Configuration Examples](#configuration-examples)
3. [Python API Examples](#python-api-examples)
4. [CI/CD Integration](#cicd-integration)
5. [Advanced Scenarios](#advanced-scenarios)
6. [Custom Workflows](#custom-workflows)

## Basic Examples

### Example 1: Simple Test Execution

```bash
# Navigate to submission directory
cd /path/to/submission

# Run all tests with default settings
tbeval-run .

# Output:
# ══════════════════════════════════════════════════════════════════
# TEST EXECUTION SUMMARY
# ══════════════════════════════════════════════════════════════════
# Tests: 10
# Running 10 tests...
# ✓ test_adder.test_basic (0.52s)
# ...
