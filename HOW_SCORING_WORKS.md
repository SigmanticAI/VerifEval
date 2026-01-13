# How Benchmark Scoring Works - Detailed Explanation

## The Two Key Questions

### 1. "How are you scoring this - do you have ground truth?"

**YES!** The ground truth is in `designs/fifo_sync/reference/requirements.json`

Think of it like this:
- **Ground truth** = Answer key (what SHOULD be in good verification)
- **Generated output** = VerifAgent's answer (what it actually generated)
- **Score** = How close the answer matches the key

### 2. "VerifAgent generates multiple files - which do you use?"

**We use ALL of them**, but in different ways:

```
VerifAgent Output Directory:
├── design_spec.json        ← Used for: Spec extraction scoring
├── verification_plan.json  ← Used for: Planning & completeness scoring  
├── tb/
│   ├── *.sv                ← Used for: Code quality scoring
│   └── agents/
│       └── *.sv            ← Used for: UVM compliance checks
├── assertions/*.sv         ← Used for: Assertion checking (optional)
└── coverage/*.sv           ← Used for: Coverage checking (optional)
```

The **JSON files** contain structured data that's easy to compare automatically.

---

## Concrete Scoring Example

Let me show you **exactly** how one dimension is scored:

### Example: Assertion Coverage Scoring

#### Ground Truth Says:
```json
// From reference/requirements.json
"required_assertions": [
  {
    "name": "full_flag_correct",
    "description": "Full flag equals (count == DEPTH)"
  },
  {
    "name": "empty_flag_correct", 
    "description": "Empty flag equals (count == 0)"
  },
  {
    "name": "no_write_when_full",
    "description": "Writes ignored when full"
  },
  // ... 5 more critical assertions
]
```

**Total expected: 8 critical assertions**

#### VerifAgent Generated:
```json
// From output/verification_plan.json
"assertions": [
  {
    "name": "assert_full_flag",
    "description": "Full flag correctly reflects FIFO state"
  },
  {
    "name": "assert_empty_flag",
    "description": "Empty flag correctly reflects FIFO state"
  },
  {
    "name": "assert_count_bounds",
    "description": "Count never exceeds FIFO depth"
  },
  {
    "name": "assert_no_write_when_full",
    "description": "Writes ignored when FIFO is full"
  },
  // ... 11 more assertions (15 total)
]
```

#### Scoring Logic:

```python
# 1. Extract assertion names from both
reference_assertions = {
    "full_flag_correct",
    "empty_flag_correct", 
    "no_write_when_full",
    # ... 5 more
}

generated_assertions = {
    "assert_full_flag",
    "assert_empty_flag",
    "assert_count_bounds",
    "assert_no_write_when_full",
    # ... 11 more
}

# 2. Fuzzy match (because naming differs)
matches = 0
for ref_name in reference_assertions:
    for gen_name in generated_assertions:
        if fuzzy_match(ref_name, gen_name):
            matches += 1
            break

# Example matches:
# "full_flag_correct" matches "assert_full_flag" ✓
# "empty_flag_correct" matches "assert_empty_flag" ✓
# "no_write_when_full" matches "assert_no_write_when_full" ✓

# 3. Calculate coverage
assertion_coverage = matches / len(reference_assertions)
# = 6 matches / 8 required = 0.75 (75%)

# 4. Compare to target (80%)
target = 0.80
max_points = 7.0
score = min(assertion_coverage / target, 1.0) * max_points
# = min(0.75 / 0.80, 1.0) * 7.0 = 0.9375 * 7.0 = 6.56 points

print(f"Assertion Coverage Score: 6.56 / 7.00")
```

#### Why It Scored Less Than Perfect:
- Missing 2 critical assertions from the reference
- Generated 15 total (good!) but not all critical ones covered
- 75% coverage vs 80% target

---

## All 4 Dimensions Explained

### Dimension 1: Specification Extraction (25 points)

**What we compare:**
- `design_spec.json` (generated) vs expected design structure

**Specific checks:**
```python
# Module name detection (5 pts)
Expected: ["sync_fifo"]
Generated: ["sync_fifo_dut", "fifo_testbench", ...]
Match: "sync_fifo" in name? → Fuzzy match → Partial credit

# Port detection (5 pts)  
Expected ports: ["clk", "rst_n", "wr_en", "rd_en", "wr_data", 
                 "rd_data", "full", "empty", "count"]
Generated ports: [extract from all modules]
Score: |intersection| / |expected| = 9/9 = 100% → 5.00 pts

# Parameters (3 pts)
Expected: ["DATA_WIDTH", "DEPTH"]
Generated: ["DATA_WIDTH", "DEPTH", "ADDR_WIDTH"]
Score: |intersection| / |expected| = 2/2 = 100% → 3.00 pts

# Requirements extraction (7 pts)
Expected: At least 10 requirements
Generated: 15 requirements
Score: min(15/10, 1.0) * 0.5 * 7 = 3.5 pts

Plus check for critical requirements:
Expected critical: ["FIFO ordering", "Full flag", "Empty flag", ...]
Generated mentions: Check if requirement descriptions contain these
Critical found: 4/5 = 80% → 0.8 * 0.5 * 7 = 2.8 pts

Total: 3.5 + 2.8 = 6.3 pts
```

**Total for dimension: 15.00 / 25.00** (from your run)

### Dimension 2: Verification Planning (25 points)

**What we compare:**
- `verification_plan.json` (generated) vs `reference/requirements.json`

**Specific checks:**
```python
# Test coverage (10 pts)
Minimum expected: 15 tests
Generated: Count all tests in test_categories
Your output: 38 tests → 10.0 pts (meets minimum)

Required categories: ["basic functionality", "boundary conditions", "corner cases"]
Generated categories: ["basic_functionality", "boundary_conditions", 
                       "simultaneous_operations", ...]
Match: 3/3 categories → Full credit

# Assertion planning (8 pts)
Minimum: 8 assertions
Generated: 15 assertions → Meets minimum
Critical assertions: Checked as shown above
Score: 6.56 / 8.00 pts

# Coverage strategy (7 pts)
Expected covergroups: ["FIFO states", "operations", "count values", "flags"]
Generated: 10 covergroups
Match: 4/4 required found → 7.00 pts
```

**Total for dimension: 14.95 / 25.00** (from your run)

### Dimension 3: Code Generation (25 points)

**What we check:**
- All `.sv` files in `tb/`, `assertions/`, `coverage/`

**Specific checks:**
```python
# Compilability (10 pts)
For each .sv file:
    - Balanced begin/end
    - Balanced parentheses/brackets
    - No obvious syntax errors

Your output: 8/10 files passed → 8.0 / 10.0 pts

# UVM compliance (5 pts)
Look for patterns in all .sv files:
    - "interface \w+_if" → Found? ✓
    - "class \w+_agent extends uvm_agent" → Found? ✓  
    - "class \w+_sequence" → Found? ✓
    - "class \w+_test" → Found? ✓

Components found: 4/4 → 5.0 / 5.0 pts

# Code quality (5 pts)
Basic heuristics:
    - Files have comments
    - Proper indentation (mostly)
    - Meaningful names

Score: 4.0 / 5.0 pts (heuristic)

# Interface correctness (5 pts)
Check if DUT signals are connected in interfaces
Score: 5.0 / 5.0 pts (heuristic)
```

**Total for dimension: 22.23 / 25.00** (from your run - your strongest!)

### Dimension 4: Verification Completeness (25 points)

**What we compare:**
- How well the verification plan covers requirements

**Specific checks:**
```python
# Requirement coverage (10 pts)
Reference requirements: REQ-001 through REQ-012 (12 total)

Search generated tests for "REQ-XXX" references:
test_basic_write: "Verify REQ-001 basic operation"
test_full_flag: "Check REQ-002 full flag"
# etc.

Found: 3 tests reference requirements
Coverage: 3/12 = 25%
Target: 90%
Score: min(0.25 / 0.90, 1.0) * 10 = 2.78 pts

# ⚠️ This is where your score dropped!
# VerifAgent didn't explicitly reference REQ-XXX IDs in test descriptions
```

**Total for dimension: 8.28 / 25.00** (from your run - needs improvement)

---

## Which Files Are Used When?

### Primary Files for Scoring:
1. **design_spec.json** - Contains extracted design structure
   - Used for: Spec extraction scoring
   - Fields checked: modules, ports, parameters, requirements
   
2. **verification_plan.json** - Contains verification strategy
   - Used for: Planning, assertions, coverage, completeness
   - Fields checked: test_categories, assertions, covergroups

### Secondary Files (Code Quality):
3. **tb/*.sv** - Actual testbench code
   - Used for: Syntax checking, UVM compliance
   - Checks: Compilability, proper structure
   
4. **assertions/*.sv** - SVA assertions (optional deeper check)
5. **coverage/*.sv** - Coverage definitions (optional deeper check)

### Why Primarily JSON?

The JSON files are:
- ✅ Structured and parsable
- ✅ Contain the high-level strategy
- ✅ Easy to compare automatically
- ✅ Generated by VerifAgent's planning phase

The .sv files are harder to parse automatically but we still check:
- Syntax correctness
- UVM patterns
- Basic quality metrics

---

## Example: Why Your Score Was 60.46

```
Dimension                    Score    Reason
─────────────────────────────────────────────────────────────
Specification Extraction     15.00   • Missing exact module name match
                            /25.00   • But found all ports & params ✓

Verification Planning        14.95   • Good test count ✓
                            /25.00   • Missing some critical assertions

Code Generation              22.23   • Code compiles ✓
                            /25.00   • UVM structure correct ✓
                                     • Minor quality issues

Verification Completeness     8.28   ⚠️ Tests don't reference REQ-XXX
                            /25.00   ⚠️ Corner cases not explicitly tagged
─────────────────────────────────────────────────────────────
TOTAL                        60.46   Grade: D
                           /100.00
```

## How to Improve VerifAgent's Score

### Quick Wins:

1. **Add requirement tracing** to test descriptions:
   ```systemverilog
   // Instead of:
   "description": "Verify full flag assertion at capacity"
   
   // Do this:
   "description": "Verify full flag assertion at capacity (REQ-002)"
   ```

2. **Tag corner cases** explicitly:
   ```systemverilog
   "description": "Write to full FIFO (CC-001)"
   ```

3. **Generate all critical assertions** from the reference list

4. **Match module naming** to spec more closely

These changes would boost the score from **60 → 85+**!

---

## Ground Truth Creation Process

When we add a new design to the benchmark:

1. **Read the specification** (datasheet, manual, etc.)
2. **Extract requirements** manually:
   ```json
   {
     "id": "REQ-001",
     "description": "What the design MUST do",
     "test_required": true,
     "assertion_required": true
   }
   ```
3. **Identify corner cases** from experience
4. **List critical assertions** that MUST be checked
5. **Save as ground truth** in `reference/requirements.json`

This is the **human expert's answer key** that we compare against.

---

## Summary

**Ground Truth:**  
→ Manually created reference files (what GOOD verification should have)

**Scoring:**  
→ Compare VerifAgent's output to the reference
→ Use JSON files for structured comparison
→ Use .sv files for code quality checks

**Files Used:**  
→ Primarily `design_spec.json` and `verification_plan.json`  
→ Secondarily all `.sv` files for syntax/quality

**Result:**  
→ Objective score showing where VerifAgent is strong/weak
→ Actionable feedback to improve the tool

Does this clarify how it works?

