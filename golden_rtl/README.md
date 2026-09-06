# `golden_rtl/` — Vendored Reference RTL

Golden/reference RTL implementations used as ground truth for verification tasks in this
repository. Two categories:

## Small, single-block IP (used by the core VerifEval auto-testing framework)

Small peripheral-style designs, each a handful of files, used directly by the scripts under the
repo root (`evaluator/`, `frameworks/`, `test_benchmark.py`, etc.):

| Directory | IP |
|---|---|
| `axi/` | AXI DMA controller |
| `fifo/` | Generic synchronous/asynchronous FIFO |
| `i2c/` | I2C master core |
| `spi/` | SPI master/slave core |
| `uart/` | UART core |
| `ibex/` | Ibex RISC-V core (lowRISC) |
| `veer_el2/` | VeeR-EL2 RISC-V core (CHIPS Alliance) |
| `OpenTitan/` | OpenTitan IP blocks |
| `RTLLM/`, `VeriLLMBench/` | RTL-generation benchmark suites (design collections used as scoring targets) |

## Large, full-chip/SoC-scale vendored IP (dataset-only — not wired into the auto-testing framework)

Full, complete, unmodified vendor copies of large open-source hardware projects, added as extra
datasets on this branch. Each has its own `README_VERIFEVAL.md` documenting exact upstream
provenance (source repo, branch/commit, license) and how the RTL was independently verified to
elaborate/synthesize using open-source tools (Verilator and/or Icarus Verilog), including any
open-source-tool compatibility caveats encountered (documented, never silently patched around):

| Directory | IP | README |
|---|---|---|
| `NVDLA/` | NVIDIA Deep Learning Accelerator | [`NVDLA/README_VERIFEVAL.md`](NVDLA/README_VERIFEVAL.md) |
| `OpenC910/` | T-Head/XuanTie C910 RV64GCV out-of-order core | [`OpenC910/README_VERIFEVAL.md`](OpenC910/README_VERIFEVAL.md) |
| `Caliptra/` | Caliptra RISC-V RoT (+ Adams Bridge PQC accelerator) | [`Caliptra/README_VERIFEVAL.md`](Caliptra/README_VERIFEVAL.md) |
| `OpenPiton/` | Princeton OpenPiton manycore research platform | [`OpenPiton/README_VERIFEVAL.md`](OpenPiton/README_VERIFEVAL.md) |

Corresponding full specification documents for every entry above live under
[`specifications/`](../specifications/README.md).
