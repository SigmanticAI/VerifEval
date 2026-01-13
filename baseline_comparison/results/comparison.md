# VerifAgent vs Claude Cursor Comparison

## Benchmark: Synchronous FIFO Verification

**Input**: Same RTL code (no spec hints)  
**Ground Truth**: SystemVerilog Assertions Handbook (fifo_req_001)

---

## Score Summary

| Category | VerifAgent | Claude Cursor | Winner |
|----------|------------|---------------|--------|
| Specification Extraction | 15.00 / 15.00 | 15.00 / 15.00 | Tie |
| Requirement Coverage | 18.33 / 25.00 | 13.33 / 25.00 | VerifAgent |
| Corner Case Coverage | 10.00 / 10.00 | 10.00 / 10.00 | Tie |
| Assertion Coverage | 13.33 / 15.00 | 8.33 / 15.00 | VerifAgent |
| Code Generation | 22.23 / 25.00 | 22.23 / 25.00 | Tie |
| Coverage Strategy | 10.00 / 10.00 | 10.00 / 10.00 | Tie |
| **TOTAL** | **88.90 / 100** | **78.90 / 100** | **VerifAgent (+10.00)** |

---

## Generation Statistics

| Metric | VerifAgent | Claude Cursor |
|--------|------------|---------------|
| Test Cases | 36 | 28 |
| Assertions | 12 | 9 |
| Covergroups | 7 | 5 (coverage goals) |

---

## Detailed Breakdown

### Requirements Matched

| Metric | VerifAgent | Claude Cursor |
|--------|------------|---------------|
| Matched | 11 / 15 | 8 / 15 |
| Score | 18.33 | 13.33 |

### Corner Cases Matched

| Metric | VerifAgent | Claude Cursor |
|--------|------------|---------------|
| Matched | 11 / 11 | 11 / 11 |
| Score | 10.00 | 10.00 |

### Assertions Matched

| Metric | VerifAgent | Claude Cursor |
|--------|------------|---------------|
| Matched | 8 / 9 | 5 / 9 |
| Score | 13.33 | 8.33 |

---

## Key Differences

| Aspect | VerifAgent | Claude Cursor |
|--------|------------|---------------|
| Test Depth | More tests per category | Fewer but detailed tests |
| Assertion Format | SVA templates with code | High-level descriptions |
| Coverage Model | Formal covergroups | Coverage goals list |
| Output Structure | Multiple SV files | JSON + SV files |

---

## Conclusion

**VerifAgent outperforms Claude Cursor by 10 points** on the same input.

Primary advantages:
- 29% more test cases generated (36 vs 28)
- 60% better assertion coverage (8/9 vs 5/9)
- 38% better requirement coverage (11/15 vs 8/15)

