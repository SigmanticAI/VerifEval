### `step2_classify_route/quality_gate/README.md`

```markdown
# Quality Gate Module

## Purpose

Performs static analysis on HDL files using open-source linting tools.

## Supported Tools

### Verible (SystemVerilog/Verilog)
- **Syntax checking**: `verible-verilog-syntax`
- **Linting**: `verible-verilog-lint`
- Installation: https://github.com/chipsalliance/verible

### GHDL (VHDL)
- **Syntax checking**: `ghdl -s`
- Installation: http://ghdl.free.fr/

## Quality Gate Modes

| Mode | Behavior |
|------|----------|
| `blocking` | Fails pipeline if critical errors found |
| `advisory` | Reports issues but continues |
| `disabled` | Skips quality checks entirely |

## Customizing Verible Rules

Create a `.verible.rules` file:
