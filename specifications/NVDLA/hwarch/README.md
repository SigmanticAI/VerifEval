# NVDLA v1 Hardware Manual (vendored)

Full text of the NVDLA v1 hardware documentation, fetched from https://nvdla.org/hw/v1/ and
converted to markdown, chapter-by-chapter, 1:1 with the upstream Sphinx site's table of contents.

| # | File | Upstream page |
|---|------|---------------|
| 01 | `01_hwarch_hardware_architectural_specification.md` | [hwarch.html](https://nvdla.org/hw/v1/hwarch.html) — top-level hardware architectural specification |
| 02 | `02_format_in_memory_data_formats.md` | [format.html](https://nvdla.org/hw/v1/format.html) — in-memory data formats |
| 03 | `03_integration_guide_integrators_manual.md` | [integration_guide.html](https://nvdla.org/hw/v1/integration_guide.html) — integrator's manual |
| 04 | `04_ias_precision_preservation.md` | [ias/precision.html](https://nvdla.org/hw/v1/ias/precision.html) — Implementation and Applications (IAS) guide: precision preservation |
| 05 | `05_ias_lut_programming.md` | [ias/lut-programming.html](https://nvdla.org/hw/v1/ias/lut-programming.html) — IAS guide: LUT programming |
| 06 | `06_unit_description.md` | [ias/unit_description.html](https://nvdla.org/hw/v1/ias/unit_description.html) — IAS guide: per-unit description |
| 07 | `07_ias_programming_guide.md` | [ias/programming_guide.html](https://nvdla.org/hw/v1/ias/programming_guide.html) — IAS guide: register programming guide |

This is the complete set of chapters linked from the v1 documentation's hardware section
(architecture, data formats, integrator's manual, and the full "Implementation and Applications
Specification" register/precision/LUT/unit programming guide). Nothing was skipped; each file
above is a full, unabridged conversion of its corresponding upstream HTML page (tables, formulas,
and code samples preserved), not a summary or excerpt.

See also `golden_rtl/NVDLA/README_VERIFEVAL.md` for the vendored RTL/C-model/testbench that this
specification describes, and NVDLA's own `README.md` / `spec/` directory inside that vendor tree
for release notes and build-time feature-flag documentation.
