# OpenPiton (Princeton University) — Vendored Golden RTL

## Provenance

| | |
|---|---|
| Source | https://github.com/PrincetonUniversity/openpiton |
| Branch | `master` |
| Commit | `1c6bfd2d2ea53ddd7b6f933fa2d439d1a540e207` (2026-02-25), "Merge pull request #176 from Vaibhavee89/fix-issue-175-pm-atomic-tests" |
| License | BSD 3-Clause (Princeton University) — see `LICENSE`/license headers in this directory |
| Imported | 2026-09 via shallow clone of the upstream repository, `.git` history dropped |

This is a **complete, unmodified vendor copy** of the `PrincetonUniversity/openpiton` repository
contents (minus `.git`), with one relocation: the two branding logo PNGs under the upstream `docs/`
folder were moved to `specifications/OpenPiton/images/` so that all specification/documentation
assets in this repository are consistently grouped under `specifications/`. No RTL, testbench, or
build-system file was edited — see "Synthesis / elaboration verification" below for the FuseSoC
schema-compatibility patches that were required *only in a scratch working copy* to run the checks,
and were never applied to the vendored copy itself.

Three git submodules declared in upstream's `.gitmodules` (`piton/design/chip/tile/ariane` →
[pulp-platform/ariane](https://github.com/pulp-platform/ariane), `piton/design/aws` →
[PrincetonUniversity/openpiton-aws](https://github.com/PrincetonUniversity/openpiton-aws), and
`piton/design/chipset/rv64_platform/bootrom/u-boot/uboot` → upstream U-Boot) are **not** initialized
here (they ship as empty directories, exactly as a plain `git clone` without `--recurse-submodules`
would leave them). These are optional, independently-versioned external projects — the Ariane
RV64GC core is an alternative drop-in replacement for the default OpenSPARC-T1-derived core used by
the design verified below, and AWS/u-boot are FPGA-cloud and bootloader integrations, not part of
the core manycore RTL. Run `git submodule update --init` after cloning any of those upstream repos
directly if you need them.

## What's included

```
OpenPiton/
├── README.md, CHANGELOG.md, .gitlab-ci.yml, .gitmodules, .release, .gitignore   # upstream, unmodified
├── fusesoc.conf                     # FuseSoC library registration (points at piton/)
├── build/                           # empty placeholder (upstream build-output directory, .keep only)
└── piton/
    ├── design/                      # RTL (~24 MB source)
    │   ├── chip/tile/               # per-tile RTL: sparc/ (OpenSPARC-T1-derived core: ifu, exu, lsu,
    │   │                            # tlu, ffu/FPU, mul, srams), l15 (L1.5 cache), l2 (L2 cache),
    │   │                            # dynamic_node (NoC router + crossbar), jtag, chip_bridge, pll,
    │   │                            # exu_bw_r_irf (register file), tile/config_regs, and the (empty,
    │   │                            # git-submodule) ariane/ alternative RV64GC core integration
    │   ├── chipset/                 # chip-level integration: NoC crossbars (io_xbar/mem_xbar),
    │   │                            # memory controller glue, I/O controller (UART/Ethernet/SD),
    │   │                            # RV64 platform bootrom, chipset_impl top
    │   └── aws/                     # empty placeholder (git submodule, FPGA-cloud shell integration)
    ├── verif/
    │   ├── env/manycore/            # chip-level testbench (manycore_tb, cmp_top, monitor/pc_cmp,
    │   │                            # SAS self-checking task infra, devices.xml network configs)
    │   └── diag/                    # ~2,200 SPARC/RISC-V assembly + C regression diagnostics
    │                                # (architectural, TSO, MMU, random, bug-repro test programs —
    │                                # ~434 MB of upstream test-suite source, kept complete/unfiltered)
    └── tools/                       # `sims` Perl build/regression wrapper, `pyhp`/`pyhplib`
                                     # Python-embedded-in-Verilog preprocessor, FuseSoC `.core` files
```

## Synthesis / elaboration verification

OpenPiton's RTL is authored as **Python-templated Verilog** (`.v.pyv` files, using an embedded
Python preprocessor called `pyhp` — Python code between `<% ... %>` markers is executed and its
`print()` output is spliced into the surrounding Verilog, e.g. to replicate per-tile-count logic or
per-port `case` arms from an XML network-topology description). Upstream's own build system,
`piton/tools/bin/sims` (a Perl wrapper) plus **FuseSoC** (`piton/**/*.core` CAPI2 files), invokes
`pyhp` automatically before handing the result to a Verilog tool. We used FuseSoC directly
(version 2.4.6) rather than reimplementing `sims`, since FuseSoC is itself the officially-supported,
documented build path (see `piton/tools/bin/fusesoc*`, `*.core` files throughout `piton/design` and
`piton/verif`).

**Environment variables** `pyhp`/`pyhplib` and the `.core` generators require (none upstream-documented
in one place; recovered by reading `piton/tools/bin/pyhplib.py` and comparing against
`piton/piton_settings.bash`):

```bash
export PITON_ROOT=/path/to/golden_rtl/OpenPiton
export DV_ROOT=$PITON_ROOT/piton
export PYTHONPATH=$PITON_ROOT/piton/tools/bin:$PYTHONPATH
export PROTOSYN_RUNTIME_DESIGN_PATH=$PITON_ROOT/piton/verif/env
export PROTOSYN_RUNTIME_BOARD=manycore        # selects piton/verif/env/manycore/devices.xml,
                                               # which fixes the I/O-crossbar port count
export PITON_X_TILES=1 PITON_Y_TILES=1 PITON_NUM_TILES=1   # single-tile manycore config
```

**FuseSoC 2.4.6 schema-compatibility note** (tooling-version issue, not an RTL defect, and **not**
applied to the vendored copy — only needed transiently in a scratch clone used to run the full
chip-level `manycore_tb` testbench build, see caveat below): two upstream `.core` files predate a
CAPI2 schema tightening in newer FuseSoC releases — `piton/verif/env/manycore/manycore.core` has an
empty `tools:` key under the `sim` target (schema now requires an object, e.g. `tools: {}`), and
`piton/design/chip/tile/sparc/exu/bw_r_irf/common/rtl/exu_bw_r_irf_common.core` has a null
`description:` (schema now requires a string). Both are one-line, self-evident fixes if you hit this
with a newer FuseSoC; we did not carry them into the vendored files.

To validate that the vendored RTL is complete and elaborates correctly, we ran FuseSoC's `verify`
target (pure elaboration + a bare simulation run, no external testbench/stimulus) against
`openpiton::chip` — **the full single-tile design**: the OpenSPARC-T1-derived core (IFU, EXU, LSU,
TLU, FPU, integer multiplier, register files), the L1.5 (`l15`) and L2 caches, the on-chip dynamic
NoC router/crossbar, JTAG debug access, `chip_bridge`, and PLL:

```bash
cd golden_rtl/OpenPiton
export PITON_ROOT=$(pwd) DV_ROOT=$PITON_ROOT/piton
export PYTHONPATH=$PITON_ROOT/piton/tools/bin:$PYTHONPATH
export PROTOSYN_RUNTIME_DESIGN_PATH=$PITON_ROOT/piton/verif/env PROTOSYN_RUNTIME_BOARD=manycore
export PITON_X_TILES=1 PITON_Y_TILES=1 PITON_NUM_TILES=1
fusesoc --cores-root . run --target=verify --tool=icarus openpiton::chip
```

**Result:** Icarus Verilog (`iverilog`/`vvp`, version 12+) elaborates and runs the full `chip` design
(317 source files after `pyhp` preprocessing) with **exit code 0 and zero errors**. As an independent
cross-check, we also ran `verilator --lint-only` (Verilator 5.044) over the same, already-preprocessed
sources:

```bash
verilator --lint-only -Wno-fatal --top-module chip +incdir+<piton_include dirs> -f <file list above>
```

**Result:** Verilator elaborates **681 modules** with **zero `%Error`s** — every SPARC execution
unit, the FPU, both cache levels, and the NoC router build cleanly. Remaining diagnostics are the
same benign categories seen across the other vendored IPs in this repository
(`CASEINCOMPLETE`, `LATCH` — mostly hand-instantiated SRAM behavioral wrappers and priority-decoder
`case` statements that intentionally omit unreachable/don't-care patterns), none of which are
unsupported constructs or missing/undefined references. No vendored source file was modified to
achieve either result.

### Known open-source-tool caveat: `manycore_tb` chip-level testbench under Icarus

We also attempted to build upstream's full chip-level *testbench* target, `openpiton::manycore_tb`
(`cmp_top`, which wraps `chip` together with the `chipset` I/O/memory controller and a monitor/
self-checking harness). Icarus Verilog fails to elaborate one specific legacy construct: when the
optional real I/O controller is not built in (`` `ifndef PITONSYS_IOCTRL ``, the default for a plain
simulation build), `piton/design/chipset/rtl/chipset_impl.v.pyv` instantiates a `ciop_fake_iob` module
and connects one of its **input ports directly to a hierarchical cross-module reference** into a
sibling instance's internals (`` `define PITON_CORE0_INST_DONE  `TOP_MOD.monitor.pc_cmp.spc0_inst_done ``,
used as a port-connection actual). This "reach into another instance's internal registers via a
dotted hierarchical path used as a wire" pattern is a legacy ASIC-testbench idiom that VCS/Xcelium
(upstream's supported simulators, per `piton/tools/bin/sims`) accept, but Icarus Verilog's elaborator
does not resolve when the reference is used as a port-connection expression in this configuration —
it reports `Unable to bind wire/reg/memory ... in ...chipset_impl`. This is testbench/monitor-only
plumbing (a debug instruction-completion tap for the self-checking `pc_cmp` task), not part of the
DUT itself, and is architecturally identical in spirit to the NVDLA multi-level `defparam` and
Caliptra SVA-subset caveats documented for the other vendored IPs in this repository: a real,
reproducible open-source-tool support gap on a construct upstream itself only validates against
commercial simulators, not an RTL defect. We did not patch the vendored RTL to work around it. The
actual synthesizable design (`openpiton::chip`, verified above) is unaffected.

## Specification

The four official OpenPiton manuals (linked from upstream's own `README.md`, hosted at
`parallel.princeton.edu`) are vendored in full, unabridged, under `specifications/OpenPiton/`:
the Microarchitecture Specification, Simulation Manual, FPGA Prototype Manual, and Synthesis &
Back-end Manual. Nothing was excerpted or summarized.
