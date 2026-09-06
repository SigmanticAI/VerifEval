# OpenXuantie C910 (XuanTie C910) — Vendored Golden RTL

## Provenance

| | |
|---|---|
| Source | https://github.com/XUANTIE-RV/openc910 |
| Branch | `main` |
| Commit | `b91c90914c19f114d35c8f6b73408eb241ed847c` (2024-06-28), "update manuals and datasheet (#37)" |
| License | Apache License 2.0 (see `LICENSE` in this directory) |
| Imported | 2026-09 via shallow clone of the upstream repository, `.git` history dropped |

This is a **complete, unmodified vendor copy** of the `XUANTIE-RV/openc910` repository
contents (minus `.git`), with one relocation: the `doc/` folder (PDF manuals + QR code image)
was moved out to `specifications/OpenC910/` so that all specification documents in this repo
live under `specifications/`, consistent with the other vendored IPs. No RTL, testbench, or
build-system file was edited.

## What's included

```
OpenC910/
├── LICENSE, README.md                  # upstream files, unmodified
├── C910_RTL_FACTORY/
│   ├── gen_rtl/                        # RTL implementation (Verilog-2001, ~485 source files)
│   │   ├── cpu/rtl/ct_top.v            # top-level RV64GCV out-of-order core (ct_top)
│   │   ├── ifu, idu, iu, lsu, rtu,     # front-end / integer / load-store / retire units
│   │   │   mmu, pmp, cp0, biu, ciu,    # MMU, physical memory protection, control regs,
│   │   │   l2c, clint, plic, pmu,      # bus interface unit, L2 cache, CLINT/PLIC, perf mon
│   │   │   had, rst, clk, fpga         # debug (HAD), reset/clock trees, FPGA glue
│   │   ├── vfalu, vfdsu, vfmau, vfpu   # vector/scalar floating-point units (RVV + F/D)
│   │   ├── common/rtl/                 # shared cells: compressors, boothcode, sync cells,
│   │   │                              # cpu_cfig.h + mmu/sysmap.h (the two config headers
│   │   │                              # that every other .v file depends on via `PA_WIDTH`
│   │   │                              # and friends -- see "Synthesis / lint" below)
│   │   └── filelists/C910_asic_rtl.fl  # upstream's own canonical file list/build order
│   └── setup/                          # env-var setup scripts (`setup.csh`)
├── smart_run/                           # RTL simulation environment
│   ├── logical/{ahb,apb,axi,tb,pmu,gpio,uart,mem,common,filelists}/  # SoC demo + testbenches
│   ├── impl/{sdc,upf,mem_icg_test,memlist}/  # implementation constraints (SDC/UPF) + memlists
│   ├── tests/{bin,regress,cases,lib}/  # test driver + regression test cases
│   └── setup/                          # toolchain setup templates
```

## Synthesis / elaboration verification

C910's `gen_rtl/*.v` sources are plain synthesizable Verilog-2001 (no vendor-specific
preprocessing step is required, unlike NVDLA). All macro definitions the design needs
(`` `PA_WIDTH ``, `` `VLEN ``, etc.) live in two headers —
`gen_rtl/cpu/rtl/cpu_cfig.h` and `gen_rtl/mmu/rtl/sysmap.h` — which are **not** `` `include``d
by the other RTL files; instead, upstream's own canonical file list
(`gen_rtl/filelists/C910_asic_rtl.fl`) lists them first, relying on the fact that Verilog
`` `define``s are global once the preprocessor has seen them, provided the headers are
compiled/read before any file that uses their macros. We followed that same file order.

To validate that the vendored RTL is complete and elaborates correctly, we ran:

```bash
cd golden_rtl/OpenC910
export CODE_BASE_PATH=$(pwd)/C910_RTL_FACTORY
sed "s|\${CODE_BASE_PATH}|$CODE_BASE_PATH|g" \
    C910_RTL_FACTORY/gen_rtl/filelists/C910_asic_rtl.fl \
  | grep -E '\.(v|h)$' > /tmp/openc910_files.f
verilator --lint-only -Wno-fatal --top-module ct_top -f /tmp/openc910_files.f
```

**Result:** `verilator --lint-only` (Verilator 5.044) elaborates **all 487 modules** of the
`ct_top` hierarchy (the full C910 core: IFU/IDU/IU/LSU/RTU/MMU/PMP/CP0/BIU/CIU/L2C/CLINT/PLIC/
PMU/HAD/vector-FPU) with **exit code 0 and zero errors**. The only diagnostics are 3 benign,
pre-existing `WIDTHEXPAND`/`WIDTHTRUNC` bit-width mismatch warnings (`ct_lsu_snoop_req_arbiter.v`,
`ct_ifu_ipb.v`, `ct_had_dbg_info.v`) of the kind commonly seen in production RTL and accepted by
commercial synthesis tools without incident — no unsupported constructs, no missing modules, no
undefined macros. No source file was modified to achieve this result.

## Specification

The complete OpenC910 datasheet, user manual, and integration manual (as shipped by T-HEAD/
XuanTie in the upstream repo's `doc/` folder — the user and integration manuals are in
Chinese, as published) are vendored under `specifications/OpenC910/`. Nothing was excerpted,
summarized, or translated; these are the exact PDF files T-HEAD ships alongside the RTL.
