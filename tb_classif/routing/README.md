### `step2_classify_route/routing/README.md`

```markdown
# Routing Module

## Purpose

Determines execution track and simulator selection based on detection results.

## Track Assignment

| TB Type | Track | Description |
|---------|-------|-------------|
| CocoTB | A | Python testbench with Verilator |
| PyUVM | A | Python UVM with Verilator |
| VUnit | B | VUnit orchestration with GHDL/Verilator |
| SystemVerilog | B | HDL TB with VUnit wrapper |
| VHDL | B | HDL TB with VUnit wrapper |
| UVM-SV | C | ❌ Requires commercial simulator |

## Confidence Scoring

Confidence is calculated based on:
1. **Detection confidence** (pattern match strength)
2. **Quality gate results** (errors reduce confidence)
3. **Manifest presence** (explicit declaration = 100%)

Formula:
