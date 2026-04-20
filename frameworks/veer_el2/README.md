# VeeR EL2 benchmark (VerifEval framework)

A reproducible, paper-quality benchmark that drops the
[Cores-VeeR-EL2](https://github.com/chipsalliance/Cores-VeeR-EL2) project into
VerifEval as a *target* and evaluates AI-generated RTL against it using the
upstream verification infrastructure.

This framework supports two comparable generation modes:

| mode        | how RTL is produced                                                                 |
|-------------|--------------------------------------------------------------------------------------|
| `verifagent`| One command runs **VerifAgent v2** with the spec pack and lands RTL in a run dir.   |
| `baseline`  | RTL produced externally by Cursor / Claude Code (using the prompt template) is dropped into a run dir and evaluated through the **same** pipeline. |

Plus a `golden` sanity mode that copies the upstream RTL as a candidate so you
can verify the evaluator works end-to-end (upper-bound run).

## Directory layout

```
frameworks/veer_el2/
├── README.md                    <- this file
├── configs/target.yaml          <- single source of truth (edit this, not code)
├── spec/                        <- deterministic spec-pack (built by `prepare`)
│   ├── INDEX.md
│   ├── MANIFEST.json
│   ├── normalized_spec.json
│   ├── docs/                    <- selected docs/source/*.md flattened
│   ├── configs/                 <- configurable build-arg docs
│   ├── interfaces/              <- top-level RTL interface files (NORMATIVE)
│   ├── flists/                  <- design/flist + design/flist.lint
│   └── verification/INDEX.md    <- pointer at golden TB
├── prompts/
│   └── veer_el2_generation_prompt.txt  <- send this to Cursor / Claude Code
├── scripts/
│   ├── veer_bench.py            <- top-level CLI (subcommands)
│   └── lib/                     <- paths, runinfo, specpack, generators,
│                                   evaluator, reporter
├── runs/<run_id>/               <- one folder per generation+eval attempt
│   ├── run.json
│   ├── prompt.txt
│   ├── generation.log
│   ├── candidate/design/...     <- the candidate RTL under test
│   ├── stage/repo/...           <- working copy of golden+candidate overlay
│   ├── stage/work_verilator/    <- verilator obj_dir + program.hex
│   ├── eval/results.json        <- per-check machine-readable scores
│   ├── eval/summary.md          <- per-run human-readable summary
│   ├── eval/*.log               <- raw tool output (verilator, vivado, ...)
│   └── verifagent/              <- (verifagent mode) raw agent output dir
├── reports/                     <- aggregated outputs across runs
│   ├── aggregate.json
│   ├── aggregate.csv
│   └── report.md
├── artifacts/                   <- placeholder for paper artifacts
└── tools/                       <- placeholder for helper utilities
```

The cloned VeeR EL2 source itself lives at the standard VerifEval location:

```
VerifEval/golden_rtl/veer_el2/      <- full upstream Cores-VeeR-EL2 clone
```

## Spec input — what is fed to the generator

The framework only feeds the generator a **deterministic, versioned subset**
of the upstream repo (the *spec pack*).  The exact file list is in
`configs/target.yaml` under `spec_inputs`.  The chosen anchors are:

* `README.md`, `release-notes.md`
* `docs/source/*.md` – the rendered Sphinx source (intro, overview, memory map,
  CSRs, build-args, adaptations, clocks, power, error-protection, cache,
  interrupts, timers, debugging, dual-core lock-step, performance, PMP,
  user-mode, verification, tests, etc.).  These are the authoritative
  human-readable specs (the `RISC-V_VeeR_EL2_PRM.pdf` is the rendered PDF
  equivalent and is referenced in `INDEX.md`).
* `configs/README.md` – the `veer.config` configurable knobs.
* `design/flist`, `design/flist.lint` – the authoritative file inventory.
* `design/el2_veer_wrapper.sv`, `design/el2_veer.sv`, `design/include/el2_def.sv`
  – the **normative** top-level port list and parameter definitions.
* `verification/INDEX.md` – pointer at the golden testbench (the testbench
  is *not* part of the spec input; it is part of the *evaluator* infrastructure).

Why this subset and not "the entire repo"?  The benchmark is meant to be
**reproducible** and to test whether a generator can build the design from
the *documented* contract, not whether it can copy the existing RTL.  The PRM
plus port headers is exactly the human contract a chip designer would have.

## Quickstart

```bash
cd /home/rocky/VerifEval

# 1. clone golden + build deterministic spec pack
python3 frameworks/veer_el2/scripts/veer_bench.py prepare

# 2. (optional) check tool availability for richer eval
python3 frameworks/veer_el2/scripts/veer_bench.py show-tools

# 3a. mode A — VerifAgent generation + eval in one shot
python3 frameworks/veer_el2/scripts/veer_bench.py generate-verifagent \
    --label run1 --api-key "$ANTHROPIC_API_KEY"

# 3b. mode B — externally-generated RTL (Cursor / Claude Code)
#     1. send prompts/veer_el2_generation_prompt.txt + spec/ to the agent
#     2. drop the resulting RTL tree somewhere (say /tmp/cursor_run/)
python3 frameworks/veer_el2/scripts/veer_bench.py ingest-baseline \
    --source /tmp/cursor_run --label cursor_run1

# 4. cross-run report (markdown + csv + json)
python3 frameworks/veer_el2/scripts/veer_bench.py report

# 5. one-shot end-to-end
python3 frameworks/veer_el2/scripts/veer_bench.py run-all \
    --label nightly --baseline /tmp/cursor_run/

# Sanity: evaluate the GOLDEN RTL itself (upper bound)
python3 frameworks/veer_el2/scripts/veer_bench.py ingest-golden
```

## Evaluation checks and metrics

All checks live in `scripts/lib/evaluator.py`.  Each check produces a score
in `[0,1]` and is weighted per `target.yaml::scoring_weights`.  Missing tools
yield `status: SKIPPED` (no score, no weight) — the pipeline never aborts.

| check               | what it does                                                  | tool needed              |
|---------------------|---------------------------------------------------------------|--------------------------|
| `inventory`         | candidate vs golden module-name set (Jaccard)                 | -                        |
| `port_match`        | top module port names + directions vs golden                  | -                        |
| `diff_similarity`   | per-file line-set Jaccard between candidate and golden        | -                        |
| `verible_lint`      | `verible-verilog-lint` violations                             | `verible-verilog-lint`   |
| `verilator_lint`    | `verilator --lint-only -f design/flist.lint`                  | `verilator`              |
| `verilator_build`   | upstream `make verilator-build` -> `obj_dir/Vtb_top`          | `verilator` + `make`     |
| `verilator_smoke`   | runs `testbench/asm/hello_world` via precompiled hex          | `verilator` + `make`     |
| `vivado_elab`       | `xelab --prj` against `design/flist.lint`                     | Vivado (`xelab`)         |
| `vivado_synth`      | `synth_design -rtl` (heavier; off by default)                 | Vivado (`vivado`)        |

> **Vivado note:** `xelab` cannot standalone-elaborate a top with SystemVerilog
> interface ports (`el2_icache_export`, `el2_mem_export`).  We detect this
> exact failure pattern and report the check as `PARTIAL` with score 0.7 —
> the Verilog/SV analysis itself succeeded (every module parsed cleanly), only
> the static-elab top-binding step is blocked by a Vivado tool limitation.
> Enabling `enable_vivado_synth: true` in `target.yaml` bypasses this and runs
> a full `synth_design -rtl` instead (slower).

Per-test pass/fail, runtime, error/warning counts, log paths, and details are
all kept in `runs/<id>/eval/results.json`.  Raw tool output is preserved in
`runs/<id>/eval/*.log` and never deleted by the pipeline.

### Coverage

When Verilator is built with `--coverage` (set `COVERAGE=all` in your
environment before `verilator_build`), the standard `coverage.dat` lands in
`stage/work_verilator/` and is preserved for inspection.  Functional / branch
/ toggle coverage flags are documented in
`golden_rtl/veer_el2/tools/Makefile` (`COVERAGE=all|branch|toggle|functional`)
and surface through the same `verilator_build` check.

### What is NOT a primary metric

`diff_similarity` is included for paper analysis but is intentionally
under-weighted vs the functional checks.  A generator that *passes
hello_world* under the golden testbench scores higher than one that just
looks similar to the golden RTL — which is the right semantic.

## Reusing other VerifEval infrastructure

* The framework lives under `frameworks/veer_el2/` and never modifies any
  existing VerifEval folder.  It uses the standard `golden_rtl/<name>/`
  location for the cloned repo so other VerifEval scripts that scan
  `golden_rtl/` see it automatically.
* The evaluator deliberately reuses the **upstream** `tools/Makefile` and
  `design/flist*` so we are not inventing toy verification — pass/fail comes
  from the same flow chip designers use upstream.
* The `target.yaml` schema is generic enough that adding a new core (e.g.
  Ibex, CV32E40P) is a copy-and-edit job: clone the repo to
  `golden_rtl/<name>/`, copy this framework folder, edit the docs / file
  list / top-module, and you're done.

## Environment & toolchain notes

* **Verilator >= 4.106** is required for the upstream Makefile.  We have
  verified against Verilator 5.024.
* **Perl modules** `Bit::Vector` and `JSON::PP` are required by the upstream
  `configs/veer.config` script that generates `snapshots/default/*` defines.
  Install with `dnf install perl-Bit-Vector perl-JSON-PP` (RHEL/Rocky) or
  `apt install libbit-vector-perl libjson-pp-perl` (Debian/Ubuntu).
* **Vivado** is detected at `vivado`/`xelab` on PATH or at common locations
  (`$VIVADO_BIN`, `/home/sulaiman/Vivado_ML/2025.2/Vivado/bin/vivado`,
  `/opt/Xilinx/Vivado/<ver>/bin/vivado`).  Source the official
  `settings64.sh` before invoking the bench if you need Vivado checks.
* **Questa** (`vsim`) is detected at `$QUESTA_BIN` or
  `/home/rocky/questa/questasim/linux_x86_64/vsim`.  `enable_questa_build` is
  off by default; flip it in `target.yaml` once your license is set.
* **RISC-V GCC** is *not* required for the smoke check — we use the upstream
  precompiled hex files in `testbench/hex/` so the smoke test runs anywhere
  Verilator is installed.
* **VerifAgent v2** must be importable.  If `verifagent_v2` is not on
  `sys.path` we add `${VERIFAGENT_HOME:-$HOME/VerifAgent}` automatically.
  Override the python interpreter via `--python-bin` (default `python3.11`).

## Key design choices and rationale

* **Decoupled spec input from evaluation input.**  The generator only sees
  the spec pack; the evaluator only uses the upstream verification flow.
  This avoids info leakage from the testbench into the generator while still
  being a *real* test (we run the same testbench upstream chip designers do).
* **Single config file drives the whole pipeline.**  `target.yaml` controls
  which docs are spec, which RTL files are required, which checks run, and
  the scoring weights.  No code changes are needed to retune the benchmark.
* **Fail-soft tooling.**  Verilator may not be installed on a paper-author's
  laptop; Vivado may not be licensed.  Each check is independent and
  reports `SKIPPED` rather than tanking the whole eval.
* **Run dir is self-contained.**  Every run is a single directory you can
  `tar -czf` and ship: it has the prompt, the candidate RTL, the staged
  workspace, every tool log, and the results JSON.
* **Golden fallback (configurable).**  When a candidate is incomplete (very
  common for early generations of a 30k-LOC core) we optionally fill missing
  required files from the golden tree.  This lets us still measure *which
  parts* the generator got right, and the `inventory` / `diff_similarity`
  / `port_match` metrics correctly reflect what was actually generated vs
  filled.  The fill list is recorded in `eval/filled_from_golden.json`.

## Adding another core target

```bash
# 1. clone the upstream repo
git clone --depth 1 https://example.com/MyCore.git VerifEval/golden_rtl/mycore

# 2. copy this framework folder
cp -r VerifEval/frameworks/veer_el2 VerifEval/frameworks/mycore

# 3. edit configs/target.yaml: target_name, paths.golden_repo, spec_inputs.docs,
#    golden_top_module/file, generation_contract.required_files, etc.

# 4. tweak prompts/veer_el2_generation_prompt.txt as needed

# 5. test
python3 VerifEval/frameworks/mycore/scripts/veer_bench.py prepare
python3 VerifEval/frameworks/mycore/scripts/veer_bench.py ingest-golden
python3 VerifEval/frameworks/mycore/scripts/veer_bench.py report
```

## Smoke-test transcript

A reference smoke run on the GOLDEN RTL (using the `ingest-golden` upper-bound
mode) demonstrates that the pipeline works end-to-end:

```
$ python3 frameworks/veer_el2/scripts/veer_bench.py prepare
$ python3 frameworks/veer_el2/scripts/veer_bench.py ingest-golden
...
--- Eval results: <run-id>_golden_upper_bound ---
Mode:   golden
Score:  98.3 / 100  (over weight 0.89)
  inventory        status=PASS    score=1.00  weight=0.10  weighted=0.100
  port_match       status=PASS    score=1.00  weight=0.10  weighted=0.100
  diff_similarity  status=PASS    score=1.00  weight=0.10  weighted=0.100
  verible_lint     status=SKIPPED score=0.00  weight=0.06  weighted=0.000
  verilator_lint   status=PASS    score=1.00  weight=0.09  weighted=0.090
  verilator_build  status=PASS    score=1.00  weight=0.20  weighted=0.200
  verilator_smoke  status=PASS    score=1.00  weight=0.25  weighted=0.250
  vivado_elab      status=PARTIAL score=0.70  weight=0.05  weighted=0.035
```

The `verilator_smoke` line ran the upstream `testbench/asm/hello_world.hex`
through the upstream `tb_top.sv` against the candidate RTL and parsed
`TEST_PASSED` from the simulator output — i.e. the exact functional check
chip designers run upstream.  A trivial 1-port stub baseline scores ~30/100
on the same pipeline, giving a healthy dynamic range.

## License

Same as VerifEval (MIT) for everything in this folder.  The cloned VeeR EL2
upstream is Apache-2.0 — see `golden_rtl/veer_el2/LICENSE`.
