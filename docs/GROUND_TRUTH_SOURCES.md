# Ground Truth Sources - What to Obtain

## ⚠️ Current Status
The existing FIFO ground truth in `designs/fifo_sync/reference/` is **synthetic** (manually created by me, not from authoritative sources).

For a **robust, publishable benchmark**, we need ground truth from:
1. ✅ Industry standards
2. ✅ Academic benchmarks with validation
3. ✅ Real-world production IP with existing verification

---

## 🎯 Recommended Sources (In Priority Order)

### **Option 1: CVDP Benchmark** ⭐ BEST OPTION
**What:** Comprehensive Verilog Design Problems - 783 problems with verification tasks  
**Why:** Authored by experienced hardware engineers, includes verification-specific tasks  
**Status:** Paper published, dataset should be available

**📥 HOW TO OBTAIN:**
1. **Paper:** https://arxiv.org/abs/2506.14074
2. **Contact Authors:** 
   - Email authors listed in paper for dataset access
   - Or check paper for GitHub/Hugging Face link
3. **What to download:** 
   - FIFO verification problems (if included)
   - Verification requirements
   - Expected test coverage
   - Reference assertions

**🔍 SPECIFIC REQUEST:**
```
Please obtain from CVDP benchmark:
- Any FIFO-related problems
- Verification requirements for FIFO designs
- Expected assertions and coverage
- Test specifications

If CVDP has a FIFO example, it will include:
- Design specification
- RTL implementation  
- Verification requirements ← THIS IS WHAT WE NEED
- Expected testbench structure
```

---

### **Option 2: VerifLLMBench** ⭐ EXCELLENT FOR TESTBENCHES
**What:** Open-source benchmark for LLM-generated testbenches  
**Why:** Specifically for verification/testbench evaluation (exactly our use case!)  
**Status:** DVCon 2025 paper

**📥 HOW TO OBTAIN:**
1. **Paper:** https://people.ece.umn.edu/users/jsartori/papers/dvcon25.pdf
2. **Contact:** Authors at University of Minnesota ECE
3. **What to look for:**
   - GitHub repository (may be released with/after DVCon 2025)
   - Example designs with reference testbenches
   - Evaluation methodology

**🔍 SPECIFIC REQUEST:**
```
From VerifLLMBench (if available):
- Reference testbench examples
- Verification requirements format
- Coverage expectations
- Assertion specifications
```

---

### **Option 3: Industry FIFO IP with Documentation** ⭐ MOST AUTHORITATIVE

Several companies provide FIFO IP with comprehensive documentation:

#### A. **ARM AMBA Documentation**
**Source:** ARM AMBA specifications (publicly available)  
**URL:** https://developer.arm.com/architectures/system-architectures/amba

**📥 WHAT TO DOWNLOAD:**
- AMBA APB/AHB/AXI specifications
- Compliance requirements
- Verification IP (VIP) specifications if available
- These often include FIFO-like components

**🔍 USE FOR:**
- Interface protocol requirements
- What assertions are critical for bus protocols
- Coverage requirements for bus components

#### B. **OpenCores FIFO Projects**
**Source:** opencores.org  
**Best Projects:**
- `async_fifo` - https://opencores.org/projects/async_fifo
- `generic_fifos` - https://opencores.org/projects/generic_fifos

**📥 HOW TO OBTAIN:**
```bash
# Download from OpenCores SVN
svn checkout https://opencores.org/ocsvn/async_fifo/async_fifo/trunk async_fifo

# Or download as tarball from website
```

**🔍 WHAT TO EXTRACT:**
```
From OpenCores FIFO projects, we need:
- Design specification (doc/ folder)
- Existing testbench (bench/ or sim/ folder)
- Any verification plan documents
- Coverage reports if available

Then create ground truth from:
- What tests they have → our "expected tests"
- What assertions they use → our "required assertions"  
- What corner cases they test → our "expected coverage"
```

---

### **Option 4: Academic Papers with FIFO Verification**

**Search for:**
- "FIFO verification" + "SystemVerilog assertions"
- "FIFO testbench" + "UVM"
- "Synchronous FIFO" + "formal verification"

**Recommended Papers to Find:**
1. Any IEEE/ACM paper on FIFO verification methodology
2. Papers from DVCon, DAC, ICCAD with FIFO examples
3. University course materials (MIT, Stanford, Berkeley) with FIFO verification examples

**📥 HOW TO USE:**
```
If you find a paper titled:
"Formal Verification of Synchronous FIFO Designs" or similar

Download and extract:
- List of properties verified (→ required assertions)
- Test scenarios described (→ required tests)
- Coverage metrics used (→ coverage requirements)
```

---

### **Option 5: RealBench Dataset** ⭐ REAL-WORLD IP
**What:** Complex real-world open-source IP with verification  
**Paper:** https://huggingface.co/papers/2507.16200

**📥 HOW TO OBTAIN:**
1. Check Hugging Face for dataset
2. Look for GitHub release
3. Contact authors

**🔍 WHAT TO LOOK FOR:**
- Any queue/buffer/FIFO designs
- Their verification environments (100% line coverage testbenches)
- Formal checkers used

---

## 📂 What Files Do We Need?

For **each** authoritative source you find, we need:

### Minimum Requirements:
```
✅ Design Specification Document
   - Functional requirements list
   - Interface definition
   - Behavioral description
   
✅ Verification Requirements
   - What must be tested
   - Critical assertions
   - Corner cases
   - Coverage targets
```

### Ideal (if available):
```
✅ Existing testbench code
   - UVM/SystemVerilog testbench
   - Test list with descriptions
   
✅ Assertion library
   - SVA assertions used
   - Properties verified
   
✅ Coverage model
   - Covergroups defined
   - Coverage goals
```

---

## 🔧 How to Convert to Our Format

Once you obtain authoritative data, here's how to convert it:

### Step 1: Extract Requirements
```python
# From specification document or existing testbench
# Create: reference/requirements.json

{
  "functional_requirements": [
    {
      "id": "REQ-XXX",  # From spec section number or create
      "description": "...",  # From spec SHALL statements
      "priority": "critical",  # Based on spec language
      "test_required": true,  # If spec says "shall be tested"
      "assertion_required": true  # If spec mentions verification
    }
  ]
}
```

### Step 2: Extract Assertions
```python
# From existing testbench assertions or spec properties
# Create: reference/requirements.json → required_assertions

{
  "required_assertions": [
    {
      "name": "...",  # From existing assertion name
      "description": "...",  # From assertion property
      "property_type": "safety|liveness|invariant"
    }
  ]
}
```

### Step 3: Extract Test Coverage
```python
# From existing tests or spec test requirements
# Create: reference/requirements.json → corner_cases

{
  "corner_cases": [
    {
      "id": "CC-XXX",
      "description": "...",  # From test description
      "test_required": true
    }
  ]
}
```

---

## 📋 Action Items for You

Please obtain **at least ONE** of the following:

### Priority 1: Contact CVDP Authors
- [ ] Email authors of https://arxiv.org/abs/2506.14074
- [ ] Request: FIFO verification problems from dataset
- [ ] Ask: Are verification requirements included?

### Priority 2: Get OpenCores FIFO
- [ ] Download: `async_fifo` or `generic_fifos` from opencores.org
- [ ] Extract: specification, testbench, assertions
- [ ] Upload here: The specification and any test documentation

### Priority 3: Industry Documentation
- [ ] Download: ARM AMBA spec (free registration)
- [ ] Find: FIFO/queue requirements in AXI or APB specs
- [ ] Upload: Relevant sections with requirements

### Priority 4: Academic Papers
- [ ] Search: IEEE Xplore, ACM Digital Library for "FIFO verification"
- [ ] Download: Any paper with verification methodology
- [ ] Upload: PDF with verification requirements section

---

## 🎯 What to Upload Here

**Upload ANY of the following:**

1. **PDF Documents:**
   - FIFO specification datasheets
   - Academic papers on FIFO verification
   - ARM AMBA spec sections
   - Verification methodology documents

2. **Code Files:**
   - Existing FIFO testbenches (from OpenCores, GitHub)
   - Assertion files (SVA)
   - Coverage models

3. **Text Files:**
   - Verification plans
   - Test specifications
   - Requirements lists

**I will then:**
✅ Extract the requirements  
✅ Convert to our JSON format  
✅ Create authoritative ground truth  
✅ Replace current synthetic data  

---

## 📧 Contact Information for Datasets

### CVDP Benchmark
- **Authors:** Check paper for email
- **Paper:** arxiv.org/abs/2506.14074
- **Request:** "FIFO verification problems and requirements"

### VerifLLMBench  
- **Authors:** University of Minnesota, ECE
- **Paper:** people.ece.umn.edu/users/jsartori/papers/dvcon25.pdf
- **Request:** "Benchmark dataset access, specifically FIFO examples"

### RealBench
- **Check:** Hugging Face datasets
- **Search:** "RealBench verification"

---

## 🚀 Alternative: Create from Multiple Sources

If no single source has everything, we can **synthesize ground truth** from:

1. **OpenCores FIFO** → Functional requirements, corner cases
2. **Industry spec** → Interface requirements, protocols  
3. **Academic paper** → Assertion list, formal properties
4. **Existing testbench** → Test structure, coverage

This creates a **validated composite ground truth** that's:
- ✅ Based on real designs
- ✅ Includes industry practices
- ✅ Validated by academic research
- ✅ Proven by existing verification

---

## 📊 Summary

**Current Status:** Synthetic ground truth (not publishable)  
**Target:** Authoritative ground truth from validated sources  
**Best Options:** CVDP, VerifLLMBench, OpenCores, Industry specs  
**Your Action:** Obtain and upload any of the recommended documents  
**My Action:** Convert to proper ground truth format  

**This will make the benchmark:**
- 📈 Publishable in academic venues
- 🎯 Trustworthy for industry use
- ✅ Comparable to VerilogEval standards
- 🔬 Scientifically valid

