# Step 2: Classify and Route Submission

## Overview

This module classifies RTL testbench submissions and routes them to the 
appropriate execution track based on detected testbench type.

## Architecture
## Quick Start

```python
from step2_classify_route import ClassifierRouter
from pathlib import Path

# Classify a submission
router = ClassifierRouter(Path("./my_project"))
routing = router.classify_and_route()

# Check results
if routing.is_valid():
    print(f"TB Type: {routing.tb_type}")
    print(f"Track: {routing.track}")  # A (Python) or B (HDL)
    print(f"Simulator: {routing.chosen_simulator}")
else:
    print("Errors:", routing.errors)

# Save outputs
router.save_routing(routing)
