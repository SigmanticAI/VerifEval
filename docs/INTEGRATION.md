# CI/CD Integration Guide

Complete guide for integrating TB Eval Step 4 into your CI/CD pipelines.

## Table of Contents

1. [Overview](#overview)
2. [GitHub Actions](#github-actions)
3. [GitLab CI](#gitlab-ci)
4. [Jenkins](#jenkins)
5. [Azure DevOps](#azure-devops)
6. [CircleCI](#circleci)
7. [Docker Integration](#docker-integration)
8. [Artifact Management](#artifact-management)
9. [Notifications](#notifications)
10. [Best Practices](#best-practices)

## Overview

### Integration Workflow

### Prerequisites

All CI/CD integrations require:
- Python 3.8+
- Build manifest from Step 3
- Simulator installed (Verilator, GHDL, etc.)
- Test execution framework

## GitHub Actions

### Basic Workflow

**.github/workflows/test.yml**

```yaml
name: Hardware Tests

on:
  push:
    branches: [ main, develop ]
  pull_request:
    branches: [ main ]
  workflow_dispatch:

jobs:
  test:
    runs-on: ubuntu-latest
    timeout-minutes: 60
    
    steps:
    - name: Checkout repository
      uses: actions/checkout@v3
      with:
        submodules: recursive
    
    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: '3.9'
        cache: 'pip'
    
    - name: Install TB Eval framework
      run: |
        python -m pip install --upgrade pip
        pip install tbeval-step4-execute
    
    - name: Install Verilator
      run: |
        sudo apt-get update
        sudo apt-get install -y verilator
    
    - name: Run tests
      run: |
        tbeval-run \
          --junit results.xml \
          --html report.html \
          --no-color \
          --timeout 600 \
          submission/
    
    - name: Publish test results
      uses: EnricoMi/publish-unit-test-result-action@v2
      if: always()
      with:
        files: results.xml
        check_name: Test Results
    
    - name: Upload HTML report
      uses: actions/upload-artifact@v3
      if: always()
      with:
        name: test-report
        path: report.html
    
    - name: Upload coverage
      uses: actions/upload-artifact@v3
      if: always()
      with:
        name: coverage
        path: .tbeval/test_runs/*/coverage/



