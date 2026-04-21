# frameworks/ot_uart — OpenTitan UART verification-track benchmark

Mirror of `frameworks/veer_el2/` layout, verification direction.

## Paradigm

| | `frameworks/veer_el2` | `frameworks/ot_uart` |
|---|---|---|
| Direction | spec → RTL | RTL + spec → TB |
| What's scored | RTL matches golden | TB coverage + test pass |
| Ground truth | Golden RTL | Golden dv/ (NOT exposed to generator) |
| Gate policy | Soft (PARTIAL) | Hard zero on G1/G2 fail |

Both tracks live in the same paper and share the `frameworks/<target>/` convention.

## Layout

```
frameworks/ot_uart/
    configs/target.yaml     — single source of truth (paths, spec pack, scoring)
    prompts/                — generation prompt (TBD)
    spec/                   — materialized deterministic spec pack (TBD)
    runs/                   — per-run artifacts (generated TB + logs + results.json)
    reports/                — aggregated reports
```

## Spec-pack info-leak protection

`golden_repo/dv/` is EXPLICITLY excluded from `spec_inputs` (see `excluded_paths`
in target.yaml). The generator sees only RTL interface files + natural-language
docs + register hjson + testplan hjson. The golden TB is never shown.

## Scoring — VerifScore v1

Provisional weights locked 2026-04-20, reviewable after ot_uart pilot run:

| Metric | Weight | Source |
|---|---|---|
| functional_coverage | 0.30 | xcrg / vcover / UCDB |
| structural_coverage | 0.25 | line + branch + toggle avg |
| test_pass_rate      | 0.20 | tests_pass / tests_total |
| assertion_density   | 0.15 | SVA count / RTL signal count |
| uvm_conformance     | 0.10 | VerifAgent graph validator |

**Side metrics** (reported separately, not in composite):
`multi_seed_stability`, `cost_per_verifscore`, `iteration_count`.

## Sibling targets

- `frameworks/ot_rv_timer/` — planned (blocked on pilot clean)
- `frameworks/ot_hmac/`     — planned (blocked on pilot clean)
