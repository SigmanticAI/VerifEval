# FIFO Synchronous - Benchmark Reference Design

## Source

**AUTHORITATIVE SOURCE**: This ground truth is extracted from:
- **Book**: "SystemVerilog Assertions Handbook" (Industry-standard reference)
- **Documents**: 
  - fifo_req_001: Requirements Specification for Synchronous FIFO
  - fifo_ver_plan_001: Verification Plan for Synchronous FIFO
- **Location**: `/specifications/synch_fifo_req_verif_plan.pdf`

This is **NOT synthetic data** - it represents industry best practices and professional verification standards.

## What This Contains

### Requirements (15 functional requirements)
Extracted from Section 5 of the requirements specification:
- Push/Pop operation requirements
- Data sequencing (FIFO ordering)
- Status flags (Full, Empty, Almost Full, Almost Empty)
- Reset behavior
- Error handling
- Performance specifications

### Assertions (9 critical assertions)
With actual SVA property code from the specification:
- `ap_push_error` - No push when full
- `ap_pop_error` - No pop when empty
- `ap_pop_data` - Data integrity
- `ap_fifo_full` - Full flag correctness
- `ap_fifo_empty` - Empty flag correctness
- `ap_fifo_almost_full` - Almost full threshold
- `ap_fifo_almost_empty` - Almost empty threshold
- `ap_fifo_ptrs_flags_at_reset` - Reset behavior
- `ap_error_flag` - Error detection

### Test Strategies (3 categories)
From Table 4.1 of the verification plan:
1. **Fixed Parameterization** - Configuration testing
2. **Reset Testing** - Reset at different fill levels
3. **Coverage** - Sequences and state coverage

### Corner Cases (11 scenarios)
- Push to full FIFO
- Pop from empty FIFO
- Simultaneous read/write at boundaries
- Reset at various fill levels
- Pointer wraparound
- Back-to-back operations
- Data pattern integrity

### Coverage Requirements
- **Code Coverage**: 100%
- **FSM Coverage**: 100% states and transitions
- **Toggle Coverage**: 95%
- **Functional Coverage**: All sequences must have count ≥ 1

## Design Parameters

```systemverilog
BIT_DEPTH = 4           // 2**4 = 16 entry FIFO
WIDTH = 32              // 32-bit data width
ALMOST_FULL = 12        // ¾ of 16 = 12
ALMOST_EMPTY = 4        // ¼ of 16 = 4
```

## Verification Approach

From the verification plan (Section 4):
- **Language**: SystemVerilog with SVA
- **Strategy**: Directed tests + pseudo-random transactions
- **Architecture**: Transactor block with server tasks
- **Properties**: Interface verification with formal properties

## Why This Is Robust Ground Truth

✅ **Industry Standard**: From professional reference book  
✅ **Complete Specification**: All requirements documented  
✅ **SVA Properties**: Formal properties defined  
✅ **Verification Plan**: Test strategies specified  
✅ **Used Worldwide**: Standard reference in verification training  

## Benchmark Usage

This ground truth will be used to evaluate VerifAgent by comparing:
1. **Requirements Coverage**: Does VerifAgent identify all 15 requirements?
2. **Assertion Generation**: Does it create the 9 critical assertions?
3. **Test Planning**: Does it cover the 3 test strategy categories?
4. **Corner Cases**: Does it address the 11 corner cases?
5. **Coverage Goals**: Does it define proper coverage requirements?

## Citation

When publishing benchmark results, cite:
```
Ground Truth Source: SystemVerilog Assertions Handbook
FIFO Requirements Specification (Document #: fifo_req_001)
FIFO Verification Plan (Document #: fifo_ver_plan_001)
```

---

**This benchmark now has authoritative, publishable ground truth!** 🎯

