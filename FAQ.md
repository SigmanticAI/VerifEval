# Benchmark FAQ

## Q1: "How are you scoring this - do you have ground truth?"

**Short Answer:** YES! The ground truth is manually created reference files.

**What is Ground Truth?**

The ground truth is **what a good verification environment SHOULD contain** for each design. It's like an answer key.

**Where is it?**
```
benchmark/designs/fifo_sync/reference/requirements.json
```

**What's in it?**
```json
{
  "functional_requirements": [
    {
      "id": "REQ-001",
      "description": "FIFO shall store/retrieve in FIFO order",
      "test_required": true,
      "assertion_required": true
    },
    // ... 11 more requirements
  ],
  "required_assertions": [
    {
      "name": "full_flag_correct",
      "description": "Full flag equals (count == DEPTH)"
    },
    // ... 7 more critical assertions
  ],
  "corner_cases": [ /* 10 corner cases to test */ ],
  "coverage_requirements": { /* what coverage is needed */ }
}
```

**How is it created?**

A human expert reads the FIFO specification and manually creates:
1. ✅ List of functional requirements
2. ✅ List of corner cases to test
3. ✅ List of critical assertions needed
4. ✅ Coverage targets

This becomes the "answer key" we compare against.

**Example Comparison:**

| Category | Ground Truth Says | VerifAgent Generated | Score |
|----------|-------------------|---------------------|-------|
| Critical Assertions | Need 8 assertions:<br>- full_flag_correct<br>- empty_flag_correct<br>- count_bounds<br>- no_write_when_full<br>- ... | Generated 15 assertions:<br>- assert_full_flag ✓<br>- assert_empty_flag ✓<br>- assert_count_bounds ✓<br>- assert_no_write_when_full ✓<br>- ... | 6/8 matched<br>= 75% coverage<br>= 6.56/7 pts |

---

## Q2: "VerifAgent generates multiple files - which do you use?"

**Short Answer:** We use ALL of them, but primarily the JSON files.

### File Usage Map

```
VerifAgent Output Directory:
output/build_verification_for_a_synch_205422/
│
├── design_spec.json        ← [PRIMARY] Specification extraction
│   │                          Contains: modules, ports, parameters, requirements
│   │                          Used for: Dimension 1 scoring
│   │
├── verification_plan.json  ← [PRIMARY] Verification strategy  
│   │                          Contains: tests, assertions, covergroups
│   │                          Used for: Dimensions 2 & 4 scoring
│   │
├── tb/                     ← [SECONDARY] Code quality
│   ├── tb_top.sv              Checked for: syntax, structure
│   ├── env/
│   │   └── env.sv             Checked for: UVM patterns
│   ├── agents/
│   │   ├── *_if.sv            Checked for: interface definitions
│   │   └── *_agent.sv         Checked for: UVM agent structure
│   └── tests/
│       └── tests.sv           Checked for: test structure
│
├── assertions/             ← [OPTIONAL] Deeper assertion check
│   └── *_assertions.sv        Could check: actual SVA syntax
│
├── coverage/               ← [OPTIONAL] Deeper coverage check
│   └── *_coverage.sv          Could check: actual covergroup syntax
│
├── Makefile                ← Not used for scoring
└── README.md               ← Not used for scoring
```

### Why Primarily JSON Files?

**The JSON files are structured and easy to compare:**

```python
# Easy to parse and compare
with open('design_spec.json') as f:
    spec = json.load(f)
    
ports_generated = [p['name'] for p in spec['modules'][0]['ports']]
ports_expected = ['clk', 'rst_n', 'wr_en', 'rd_en', ...]

score = len(set(ports_generated) & set(ports_expected)) / len(ports_expected)
```

**The .sv files are harder to parse automatically:**
- Need full Verilog parser
- Assertions can be in any format
- Tests can have various structures

So we:
- ✅ Check they exist
- ✅ Do basic syntax validation
- ✅ Look for UVM patterns with regex
- ❌ Don't deeply parse the HDL

### Detailed Breakdown

#### 1. `design_spec.json` → Dimension 1 (Spec Extraction)

**What we check:**
```json
{
  "modules": [
    {
      "name": "sync_fifo",           ← Does name match expected?
      "ports": [...],                 ← Are all required ports found?
      "parameters": [...],            ← Are parameters detected?
      "fsms": [...],                  ← Is FSM structure identified?
    }
  ],
  "requirements": [...]              ← Were requirements extracted?
}
```

**Scoring:**
- Module name: 5 pts
- Ports: 5 pts
- Parameters: 3 pts
- FSM: 5 pts
- Requirements: 7 pts

#### 2. `verification_plan.json` → Dimensions 2 & 4 (Planning + Completeness)

**What we check:**
```json
{
  "test_categories": [              ← Dimension 2: Test Planning
    {
      "name": "basic_functionality",
      "tests": [
        {"name": "test_reset", ...},
        {"name": "test_write", ...}
      ]
    }
  ],
  "assertions": [                   ← Dimension 2 & 4: Assertions
    {
      "name": "assert_full_flag",
      "description": "..."
    }
  ],
  "covergroups": [...]              ← Dimension 2 & 4: Coverage
}
```

**Scoring:**
- Test count & categories: 10 pts
- Assertion planning: 8 pts
- Coverage strategy: 7 pts
- Requirement tracing: 10 pts
- Corner case coverage: 3 pts

#### 3. `tb/**/*.sv` → Dimension 3 (Code Generation)

**What we check:**
```python
# For each .sv file:

1. Syntax Check (10 pts):
   - Count 'begin' vs 'end' → balanced?
   - Count '(' vs ')' → balanced?
   - Count '[' vs ']' → balanced?
   - Count '{' vs '}' → balanced?
   
2. UVM Pattern Check (5 pts):
   Search for regex patterns:
   - r"interface\s+\w+_if"              → Found interface?
   - r"class\s+\w+_agent extends"       → Found agent?
   - r"class\s+\w+_sequence"            → Found sequence?
   - r"class\s+\w+_test"                → Found test?

3. Quality Heuristics (5 pts):
   - Has comments?
   - Reasonable indentation?
   - Meaningful names?

4. Interface Check (5 pts):
   - DUT signals connected?
   - Proper clocking blocks?
```

### Summary: Which Files for What?

| Scoring Dimension | Primary Files | What We Extract | Score |
|-------------------|--------------|-----------------|-------|
| **1. Spec Extraction** | `design_spec.json` | Modules, ports, parameters, FSMs, requirements | 15/25 |
| **2. Planning** | `verification_plan.json` | Tests, assertions, covergroups | 14.95/25 |
| **3. Code Generation** | `tb/**/*.sv` | Syntax, UVM patterns, quality | 22.23/25 |
| **4. Completeness** | `verification_plan.json` + `reference/*.json` | Requirement/corner case tracing | 8.28/25 |

---

## Q3: "How do you know which output directory to use?"

**Answer:** The runner finds the most recent output matching the design name.

```python
# In runner.py:

def find_output(design_name):
    output_root = Path('output/')
    
    # Find all directories with design name
    matching = [
        d for d in output_root.iterdir()
        if d.is_dir() and design_name in d.name.lower()
    ]
    
    # Use most recent
    if matching:
        return max(matching, key=lambda d: d.stat().st_mtime)
```

**Example:**
```bash
# You have:
output/
  ├── build_verification_for_a_synch_205422/  ← Created Jan 5
  ├── build_verification_for_a_synch_205442/  ← Created Jan 6  ← NEWEST!
  └── built_formal_verification_for__203357/

# When you run:
python benchmark/evaluator/runner.py --design fifo_sync

# It finds: "synch" matches "fifo_sync"
# Uses: build_verification_for_a_synch_205442 (newest)
```

**To use a specific directory:**
Currently automatic, but you could modify the runner or manually specify.

---

## Q4: "What if VerifAgent generated good code but bad JSON?"

**Good question!** Currently we rely heavily on the JSON files because:

1. They're easier to parse automatically
2. They represent the "plan" which is critical
3. The code follows from the plan

**But you're right** - we could add deeper .sv parsing in the future:
- Parse actual assertions from .sv files
- Extract test structure from SystemVerilog
- Check coverage definitions in detail

**For now:** The JSON files are the primary "interface" for evaluation.

---

## Q5: "Can I see the actual scoring code?"

**Yes!** It's in `benchmark/evaluator/metrics.py`

**Example - Assertion Coverage:**
```python
# From metrics.py, line ~380

def evaluate_assertion_coverage(generated_plan, reference, config):
    # Get generated assertions
    gen_assertions = {a['name'] for a in generated_plan.get('assertions', [])}
    
    # Get required assertions from reference
    ref_assertions = {a['name'] for a in reference.get('required_assertions', [])}
    
    # Fuzzy match (names might differ)
    matches = 0
    for ref_name in ref_assertions:
        for gen_name in gen_assertions:
            if fuzzy_match(ref_name, gen_name):
                matches += 1
                break
    
    # Calculate score
    coverage = matches / len(ref_assertions) if ref_assertions else 0
    target = config['assertion_coverage']['target']  # 0.80
    max_points = config['assertion_coverage']['points']  # 7.0
    
    score = min(coverage / target, 1.0) * max_points
    
    return score, {
        'coverage': coverage,
        'matches': matches,
        'required': len(ref_assertions),
        'generated': len(gen_assertions)
    }
```

---

## Summary

### Ground Truth
✅ Manually created reference files  
✅ Defines what GOOD verification should have  
✅ Located in `benchmark/designs/*/reference/`  

### Files Used
✅ **Primary**: `design_spec.json`, `verification_plan.json`  
✅ **Secondary**: All `.sv` files for syntax/quality  
✅ **Optional**: Could parse `.sv` files deeper in future  

### How to Find Output
✅ Automatically finds newest matching directory  
✅ Based on design name pattern matching  
✅ From `output/` directory  

### Scoring Process
1. Load generated JSON files
2. Load reference ground truth
3. Compare using fuzzy matching
4. Calculate scores per dimension
5. Weight and sum to total

**It's all automated and objective!** 🎯

