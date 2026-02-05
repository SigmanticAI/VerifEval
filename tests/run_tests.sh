#!/bin/bash

# Run all tests
echo "Running all tests..."
pytest tests/ -v

# Run only integration tests
echo -e "\n\nRunning integration tests..."
pytest tests/integration/ -v -m integration

# Run with coverage
echo -e "\n\nRunning with coverage..."
pytest tests/ --cov=step4_execute --cov-report=html --cov-report=term

echo -e "\n\nTests complete!"
echo "Coverage report: htmlcov/index.html"
