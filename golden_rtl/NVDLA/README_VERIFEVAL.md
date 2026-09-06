# NVDLA (NVIDIA Deep Learning Accelerator) — Vendored Golden RTL

## Provenance

| | |
|---|---|
| Source | https://github.com/nvdla/hw |
| Branch | `nvdlav1` (stable "full-precision" release; RTL feature-frozen) |
| Commit | `8e06b1b9d85aab65b40d43d08eec5ea4681ff715` (2018-04-19) |
| License | NVDLA Open Hardware License (see `LICENSE` in this directory) |
| Imported | 2026-09 via shallow clone of the upstream repository, `.git` history dropped |

This is a **complete, unmodified vendor copy** of the `nvdla/hw` repository contents
(minus the `.git` directory). Nothing under this directory has been edited — see
"Synthesis / elaboration verification" below for tool-compatibility notes that were
found *without* modifying any source file.

## What's included

```
NVDLA/
├── LICENSE, README.md, VERSION, Makefile, .gitignore   # upstream files, unmodified
├── vmod/            # RTL implementation (Verilog-2001 style, ~266 source files)
│   ├── nvdla/       # Functional units: CDMA, CBUF, CSC, CMAC, CACC, SDP, PDP, CDP,
│   │                # RUBIK, BDMA, GLB, NOCIF, CSB master, top-level partitions
│   ├── vlibs        # Standard-cell / DesignWare library behavioral stubs
│   ├── rams/        # Synthesizable RAM wrappers (rams/synth) + behavioral models (rams/model)
│   └── include/     # Shared `.vh` headers
├── cmod/            # C/C++ functional (bit-accurate) reference model
├── verif/           # Trace-player testbench + sample traces (verif/traces) for
│                    # several sample networks, Verilator & Vivado sim wrappers
├── spec/            # Build "spec" definitions (feature-flag configs, register spec)
├── syn/             # Example Synopsys Design Compiler synthesis scripts/constraints
└── tools/           # NVIDIA's internal `tmake` build system (Perl), incl. the `vcp`
                      # Verilog/C preprocessor used to resolve the `#ifdef` feature
                      # flags in vmod/ (see below)
```

## Synthesis / elaboration verification

NVDLA's `vmod/*.v` sources use **C-preprocessor-style** `#ifdef` / `#endif` blocks
(not SystemVerilog `` `ifdef ``) to gate four optional IP blocks:
`NVDLA_BDMA_ENABLE`, `NVDLA_CDP_ENABLE`, `NVDLA_PDP_ENABLE`, `NVDLA_RUBIK_ENABLE`.
Upstream's own `tools/bin/vcp` script exists specifically to run these files through
a real C preprocessor before any Verilog tool ever sees them — the raw `vmod/`
sources are **not** directly synthesizable without this step, by design.

To validate that the vendored RTL is complete and elaborates correctly, we:

1. Ran the full `vmod/` source tree (406 files) through `tools/bin/vcp` using the
   **`nv_full`** configuration (`spec/defs/nv_full.spec` — the "everything enabled"
   config, which is also the default `tmake` project and what `verif/dut/dut.f`
   builds), i.e. all four optional blocks enabled.
   - Note: on this machine `cpp` (Apple clang's preprocessor front-end) rejects the
     `-o <file> <file>` argument form `vcp` uses by default; we pointed `vcp` at
     `clang -E -x c` instead (`vcp --cpp="clang -E -x c" ...`), which is functionally
     identical to a real `cpp`. No NVDLA file was modified to make this work.
2. Ran `verilator --lint-only --top-module NV_nvdla` over the preprocessed sources
   plus `vmod/rams/{synth,model}`, `vmod/vlibs`, `vmod/include`.

**Result:** The design elaborates almost completely cleanly. The only remaining
diagnostics are in 3 clock-domain-crossing utility modules
(`vmod/nvdla/car/NV_NVDLA_sync3d.v`, `NV_NVDLA_sync3d_c.v`, `NV_NVDLA_sync3d_s.v`),
which use a **multi-level hierarchical `defparam`** (e.g.
`defparam sync_0.first_stage_of_sync.mode = 0;`) to configure a sub-sub-instance.
This is legal Verilog-2001 (IEEE 1364-2001 §12.2.2 permits multi-level hierarchical
paths in `defparam`), and is accepted by commercial tools (Design Compiler, the
tool NVDLA's own `syn/` scripts target), but is an explicit
[unsupported construct in Verilator](https://verilator.org/warn/UNSUPPORTED)
(`defparam with more than one dot`). We did **not** patch the vendored RTL to work
around this, since doing so would mean this is no longer an unmodified vendor copy;
this is recorded here as a known open-source-tool-compatibility caveat, not an RTL
defect.

We cross-checked with `yosys read_verilog` as well; it gets through the same
preprocessing successfully but stops earlier on a different, unrelated
Verilog-2005-frontend limitation in a DesignWare library stub
(`vmod/vlibs/NV_DW_lsd.v`, non-constant procedural `for`-loop bound) — again a
library-stub/tool-support issue, not a defect in the NVDLA IP itself.

Reproduce locally:
```bash
cd golden_rtl/NVDLA
printf '#define NVDLA_BDMA_ENABLE\n#define NVDLA_CDP_ENABLE\n#define NVDLA_PDP_ENABLE\n#define NVDLA_RUBIK_ENABLE\n' > /tmp/nvdla_macros.h
mkdir -p /tmp/nvdla_pp
find vmod -name '*.v' | while read -r f; do
  rel="${f#vmod/}"; outdir="/tmp/nvdla_pp/$(dirname "$rel")"; mkdir -p "$outdir"
  perl tools/bin/vcp --cpp="clang -E -x c" -imacros /tmp/nvdla_macros.h \
       -o "$outdir/$(basename "$f")" -i "$f"
done
verilator --lint-only -Wno-fatal --top-module NV_nvdla \
  -y vmod/rams/synth -y vmod/rams/model -y vmod/vlibs -y vmod/include \
  $(find /tmp/nvdla_pp -name '*.v')
```

## Specification

The companion NVDLA Hardware Architecture Specification (full multi-chapter doc
from https://nvdla.org/hw/v1/hwarch.html) is vendored under
`specifications/NVDLA/hwarch/`.
