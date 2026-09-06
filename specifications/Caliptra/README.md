# Caliptra — Specifications (vendored)

Full, unabridged specification documents for the Caliptra Root-of-Trust project, sourced from the
three upstream repositories that together make up the Caliptra project (see
`golden_rtl/Caliptra/README_VERIFEVAL.md` for RTL provenance and lint verification). Nothing here
is a summary or excerpt of the upstream documents.

## `caliptra-rtl/` — from [chipsalliance/caliptra-rtl](https://github.com/chipsalliance/caliptra-rtl) `docs/`

| File | Description |
|------|--------------|
| `CaliptraHardwareSpecification.md` | Caliptra Core Hardware Specification (3200+ lines) |
| `CaliptraIntegrationSpecification.md` | Caliptra Core Hardware Integration Specification (1400+ lines) |
| `CaliptraPreReleaseTestPlan.md` | Pre-release test plan |
| `CaliptraReleaseChecklist.md` | Release checklist |
| `Caliptra_TestPlan.xlsx`, `Caliptra_Gen2_TestPlan.xlsx`, `Caliptra_Gen2p1_TestPlan.xlsx` | Full DV test plans (1.x / Gen2 / Gen2.1) |
| `Verification_report_fpv.pdf` | Formal property verification (FPV) report |
| `images/` | Figures referenced by the above documents |

## `adams-bridge/` — from [chipsalliance/adams-bridge](https://github.com/chipsalliance/adams-bridge) `docs/`

| File | Description |
|------|--------------|
| `AdamsBridgeHardwareSpecification.md` | Adams Bridge (post-quantum crypto accelerator) hardware specification |
| `AdamsBridge_MLDSA.md` | ML-DSA (Dilithium) algorithm/hardware notes |
| `AdamsBridge_MLKEM.md` | ML-KEM (Kyber) algorithm/hardware notes |
| `AdamsBridgeSCA.md` | Side-channel-analysis considerations |
| `AdamsBridgeReleaseChecklist.md` | Release checklist |
| `AdamsBridge_TestPlan.xlsx` | DV test plan |
| `images/` | Figures referenced by the above documents |

## `governance/` — from [chipsalliance/Caliptra](https://github.com/chipsalliance/Caliptra) `doc/`

The umbrella repository's full `doc/` tree, unmodified, including:

| Path | Description |
|------|--------------|
| `caliptra_1x/Caliptra.md` | **Main Caliptra 1.x specification** (OCP), complete, ~1360 lines |
| `caliptra_20/Caliptra.ocp` | **Main Caliptra 2.0 specification** (OCP), complete (pandoc/markdown-flavored `.ocp` source, as published -- OCP's `ocp-spec-tools` renders this exact file to HTML/PDF; live rendered version: <https://chipsalliance.github.io/Caliptra/2.0/specification/HEAD/>), plus `caliptra_20/Roadmap.md`, `bibliography.yaml` |
| `ocp_lock/` | OCP L.O.C.K. specification (all versions v0.8 - v1.1 RC4, PDFs) + diagrams |
| `HWReleaseProcess.md`, `CaliptraContributingProcess.md` | Process docs |
| `oid_registry/oid_registry.md` | Caliptra OID registry |
| `trademark/`, `branding_guide/` | Trademark policy/checklist and brand guidelines (PDF) |
| `NCC_Group_Microsoft_MSFT283_Report_2023-*.pdf` | Independent NCC Group security assessment reports |
| `images/` | Figures referenced by the above (boot flow, HW block diagrams, mailbox state machine, etc.) |

Source commits: `caliptra-rtl` @ `1f272de5be683cce9146614a1537bb0db45ec392`, `adams-bridge` @
`2f15ffb1a2e9bd99652fa04d434a48ffcdc23f42`, `Caliptra` (governance) @
`e33b5f1f2919ff48b276630bd730e5fa8d151558`.
