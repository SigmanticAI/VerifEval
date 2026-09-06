# `specifications/` — Vendored Full Specification Documents

Full, unabridged specification/manual documents, grouped by IP. Nothing in this tree is a summary
or excerpt — every document here is the complete file as published upstream. See each subdirectory
for a per-document index, and see the corresponding IP's `README_VERIFEVAL.md` under
[`golden_rtl/`](../golden_rtl/README.md) for RTL provenance and verification details.

| Directory / file | IP |
|---|---|
| `AMBA AXI Protocol Specification.pdf` | Arm AMBA AXI protocol |
| `DMA Axi Specs.pdf`, `I2C Master Core Specifications.pdf`, `UART_spec.pdf`, `spi.pdf`, `synch_fifo_verif_spec.pdf` | Small peripheral IP specs (paired with `golden_rtl/axi`, `i2c`, `uart`, `spi`, `fifo`) |
| [`NVDLA/`](NVDLA/README.md) | NVDLA Hardware Architecture Specification + Integrator's Manual (converted to markdown) |
| [`OpenC910/`](OpenC910/README.md) | OpenC910 datasheet, user manual, integration manual |
| [`Caliptra/`](Caliptra/README.md) | Caliptra + Adams Bridge hardware/integration specs, plus the umbrella OCP/CHIPS-Alliance Caliptra governance specs |
| [`OpenPiton/`](OpenPiton/README.md) | OpenPiton microarchitecture, simulation, FPGA, and synthesis/back-end manuals |
