#!/usr/bin/env python3
"""
VeeR EL2 benchmark runner — top-level CLI for the framework.

Subcommands:

    prepare              Clone/refresh the golden VeeR EL2 repo & build the
                         spec-pack from documented sources.
    spec-pack            (Re)build the spec-pack only (assumes repo present).
    show-tools           Print which simulator/lint/synth tools are available
                         on this host (useful for triaging SKIPPED checks).
    generate-verifagent  Run VerifAgent v2 against the spec-pack to produce
                         a candidate RTL set in a fresh run dir.
    ingest-baseline      Ingest an externally-generated RTL tree (Cursor or
                         Claude Code output) into a fresh baseline run dir.
    ingest-golden        Special: copy the GOLDEN RTL into a candidate dir
                         for sanity-checking the evaluator (upper-bound run).
    evaluate             Run all enabled checks against an existing run dir.
    report               Aggregate all eval results and emit JSON/CSV/MD/term.
    run-all              prepare -> spec-pack -> generate -> evaluate -> report
                         (uses VerifAgent by default; pass --baseline=<dir>
                          to additionally evaluate a baseline drop in the
                          same invocation for direct comparison).

All paths are resolved relative to the VerifEval repository root unless
absolute.  Outputs land under `frameworks/veer_el2/{runs,reports}`.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path
from typing import List, Optional

# Allow running directly without installing as a package
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from lib.paths import DEFAULT_TARGET_CONFIG, load_target  # noqa: E402
from lib.runinfo import RunInfo, create_run, latest_run, load_run  # noqa: E402
from lib.specpack import build_spec_pack  # noqa: E402
from lib.generators import (  # noqa: E402
    GenerationResult,
    ingest_baseline,
    ingest_golden,
    render_prompt,
    run_verifagent,
)
from lib.evaluator import (  # noqa: E402
    _find_questa,
    _find_riscv_gcc,
    _find_verible_lint,
    _find_vivado,
    _which,
    evaluate,
    write_summary_md,
)
from lib.reporter import collect_runs, to_terminal, write_reports  # noqa: E402


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _print_header(title: str) -> None:
    print()
    print("=" * 78)
    print(title)
    print("=" * 78)


def _resolve_run(target, run_arg: Optional[str], mode: Optional[str] = None) -> RunInfo:
    if run_arg in (None, "", "latest"):
        info = latest_run(target.runs_root, mode=mode)
        if info is None:
            raise SystemExit(f"no runs found under {target.runs_root}"
                             + (f" (mode={mode})" if mode else ""))
        return info
    p = Path(run_arg)
    if not p.is_absolute():
        # Try as run_id under runs_root
        cand = target.runs_root / run_arg
        if cand.exists():
            p = cand
    return load_run(p)


# ---------------------------------------------------------------------------
# Commands
# ---------------------------------------------------------------------------


def cmd_prepare(args: argparse.Namespace) -> int:
    target = load_target(args.target_config)
    _print_header(f"prepare: {target.display_name}")
    repo = target.golden_repo
    if repo.exists() and not args.refresh:
        print(f"Golden repo already present at {repo} (use --refresh to re-clone)")
    else:
        if repo.exists() and args.refresh:
            print(f"Removing existing repo {repo}")
            shutil.rmtree(repo)
        repo.parent.mkdir(parents=True, exist_ok=True)
        cmd = ["git", "clone", "--depth", "1", target.upstream_repo, str(repo)]
        print("$ " + " ".join(cmd))
        rc = subprocess.call(cmd)
        if rc != 0:
            print(f"git clone failed (rc={rc})", file=sys.stderr)
            return rc
    # Stamp commit SHA into target.yaml? — We just print it; we don't rewrite
    # the user's config file automatically.  The MANIFEST.json captures it.
    try:
        sha = subprocess.check_output(
            ["git", "-C", str(repo), "rev-parse", "HEAD"], text=True
        ).strip()
        print(f"Golden HEAD: {sha}")
        # Write a small marker file
        (repo / "_VERIFEVAL_VEER_EL2_HEAD.txt").write_text(sha + "\n")
    except Exception as e:
        print(f"could not read git HEAD: {e}")

    print()
    print("Building spec-pack ...")
    res = build_spec_pack(target, force=True)
    print(f"  spec dir:       {res.spec_dir}")
    print(f"  pack hash:      {res.pack_hash}")
    print(f"  files included: {sum(1 for r in res.files if r['status']=='ok')}")
    print(f"  manifest:       {res.manifest_path.relative_to(target.framework_dir)}")
    print(f"  normalized:     {res.normalized_spec_path.relative_to(target.framework_dir)}")
    return 0


def cmd_spec_pack(args: argparse.Namespace) -> int:
    target = load_target(args.target_config)
    _print_header(f"spec-pack: {target.display_name}")
    res = build_spec_pack(target, force=args.force)
    print(f"  pack hash:      {res.pack_hash}")
    print(f"  files included: {sum(1 for r in res.files if r['status']=='ok')}")
    print(f"  written:        {res.spec_dir}")
    return 0


def cmd_show_tools(args: argparse.Namespace) -> int:
    _print_header("Tool detection")
    rows = [
        ("verilator",            _which("verilator")),
        ("verible-verilog-lint", _find_verible_lint()),
        ("vivado",               _find_vivado()),
        ("vsim (Questa)",        _find_questa()),
        ("riscv gcc",            _find_riscv_gcc()),
        ("make",                 _which("make")),
        ("git",                  _which("git")),
        ("python3.11",           _which("python3.11")),
    ]
    width = max(len(n) for n, _ in rows)
    for name, path in rows:
        marker = "✓" if path else "✗"
        print(f"  {marker} {name.ljust(width)}  {path or '(not found)'}")
    print()
    print("Tools that are missing simply cause the corresponding eval check to")
    print("be reported as SKIPPED — the rest of the pipeline still runs.")
    return 0


def cmd_generate_verifagent(args: argparse.Namespace) -> int:
    target = load_target(args.target_config)
    _print_header(f"generate-verifagent: {target.display_name}")
    # spec pack must exist
    if not (target.spec_pack / "MANIFEST.json").exists():
        print("Spec pack missing; building now.")
        build_spec_pack(target, force=True)
    run = create_run(
        target.runs_root, target.name, mode="verifagent",
        label=args.label, extras={"model": args.model or ""},
    )
    print(f"Run dir: {run.run_dir}")
    res = run_verifagent(
        target, run, target.spec_pack,
        api_key=args.api_key,
        model=args.model,
        extra_args=(args.extra or "").split() if args.extra else None,
        python_bin=args.python_bin,
    )
    print(f"  ok:            {res.ok}")
    print(f"  files written: {len(res.files_written)}")
    print(f"  notes:         {res.notes}")
    print(f"  log:           {res.log_path}")
    if not args.no_evaluate:
        print()
        result = evaluate(target, run)
        _print_eval_summary(result)
    print()
    print(f"Run ID: {run.run_id}")
    return 0


def cmd_ingest_baseline(args: argparse.Namespace) -> int:
    target = load_target(args.target_config)
    _print_header(f"ingest-baseline: {target.display_name}")
    run = create_run(
        target.runs_root, target.name, mode="baseline",
        label=args.label, extras={"source_dir": str(args.source)},
    )
    print(f"Run dir: {run.run_dir}")
    res = ingest_baseline(target, run, Path(args.source).resolve(),
                          label=args.label)
    print(f"  files copied: {len(res.files_written)}")
    print(f"  notes:        {res.notes}")
    if not args.no_evaluate:
        print()
        result = evaluate(target, run)
        _print_eval_summary(result)
    print()
    print(f"Run ID: {run.run_id}")
    return 0


def cmd_ingest_golden(args: argparse.Namespace) -> int:
    target = load_target(args.target_config)
    _print_header(f"ingest-golden (sanity): {target.display_name}")
    run = create_run(target.runs_root, target.name, mode="golden",
                     label=args.label or "upper_bound")
    print(f"Run dir: {run.run_dir}")
    res = ingest_golden(target, run)
    print(f"  files copied: {len(res.files_written)}")
    if not args.no_evaluate:
        print()
        result = evaluate(target, run)
        _print_eval_summary(result)
    print()
    print(f"Run ID: {run.run_id}")
    return 0


def cmd_evaluate(args: argparse.Namespace) -> int:
    target = load_target(args.target_config)
    _print_header(f"evaluate: {target.display_name}")
    run = _resolve_run(target, args.run)
    print(f"Run dir: {run.run_dir} (mode={run.mode})")
    result = evaluate(target, run, fill_from_golden=not args.no_fill)
    _print_eval_summary(result)
    return 0


def cmd_report(args: argparse.Namespace) -> int:
    target = load_target(args.target_config)
    _print_header(f"report: {target.display_name}")
    runs = collect_runs(target)
    print(f"Discovered {len(runs)} run(s) with eval results.")
    paths = write_reports(target, runs)
    for k, p in paths.items():
        print(f"  {k:>4}: {p}")
    print()
    print(to_terminal(runs))
    return 0


def cmd_run_all(args: argparse.Namespace) -> int:
    target = load_target(args.target_config)
    _print_header(f"run-all: {target.display_name}")
    # 1. prepare (only if missing)
    if not target.golden_repo.exists():
        rc = cmd_prepare(argparse.Namespace(
            target_config=args.target_config, refresh=False,
        ))
        if rc != 0:
            return rc
    else:
        print(f"Skipping prepare; golden repo present at {target.golden_repo}")
    # 2. spec pack (always rebuild for determinism stamp)
    build_spec_pack(target, force=True)
    # 3. VerifAgent run
    if not args.skip_verifagent:
        rc = cmd_generate_verifagent(argparse.Namespace(
            target_config=args.target_config,
            label=args.label, api_key=args.api_key,
            model=args.model, extra=args.extra,
            python_bin=args.python_bin,
            no_evaluate=False,
        ))
        if rc != 0:
            print("VerifAgent run failed (continuing).")
    # 4. baseline drop (optional)
    if args.baseline:
        rc = cmd_ingest_baseline(argparse.Namespace(
            target_config=args.target_config,
            source=args.baseline, label=args.label,
            no_evaluate=False,
        ))
        if rc != 0:
            print("Baseline ingest failed (continuing).")
    # 5. report
    return cmd_report(argparse.Namespace(target_config=args.target_config))


# ---------------------------------------------------------------------------
# Pretty-print helpers
# ---------------------------------------------------------------------------


def _print_eval_summary(result) -> None:
    print(f"\n--- Eval results: {result.run_id} ---")
    print(f"Mode:   {result.mode}")
    print(f"Score:  {result.total_score*100:.1f} / 100  (over weight {result.total_weight:.2f})")
    width = max((len(c.name) for c in result.checks), default=10)
    for c in result.checks:
        log = f"  log: {c.log_relpath}" if c.log_relpath else ""
        print(
            f"  {c.name.ljust(width)}  status={c.status:<7} "
            f"score={c.score:.2f}  weight={c.weight:.2f}  "
            f"weighted={c.weighted():.3f}{log}"
        )


# ---------------------------------------------------------------------------
# argparse setup
# ---------------------------------------------------------------------------


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="veer_bench",
        description="VeeR EL2 benchmark runner (VerifEval framework)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    p.add_argument(
        "--target-config", "-c", default=str(DEFAULT_TARGET_CONFIG),
        help="path to target.yaml (default: frameworks/veer_el2/configs/target.yaml)",
    )
    sub = p.add_subparsers(dest="cmd", required=True)

    sp = sub.add_parser("prepare", help="Clone/refresh golden repo and build spec pack")
    sp.add_argument("--refresh", action="store_true",
                    help="Re-clone even if the golden repo already exists")
    sp.set_defaults(func=cmd_prepare)

    sp = sub.add_parser("spec-pack", help="Rebuild the spec pack only")
    sp.add_argument("--force", action="store_true")
    sp.set_defaults(func=cmd_spec_pack)

    sp = sub.add_parser("show-tools", help="Print detected tools")
    sp.set_defaults(func=cmd_show_tools)

    sp = sub.add_parser("generate-verifagent",
                        help="Generate candidate RTL via VerifAgent v2")
    sp.add_argument("--label", help="Optional human label tag for the run dir")
    sp.add_argument("--api-key", help="Anthropic API key (or set ANTHROPIC_API_KEY)")
    sp.add_argument("--model", help="Override model name (sets VERIFAGENT_MODEL env)")
    sp.add_argument("--extra", help="Extra CLI args appended to verifagent invocation")
    sp.add_argument("--python-bin", help="Python interpreter for verifagent (default python3.11)")
    sp.add_argument("--no-evaluate", action="store_true",
                    help="Don't auto-run evaluate after generation")
    sp.set_defaults(func=cmd_generate_verifagent)

    sp = sub.add_parser("ingest-baseline",
                        help="Ingest externally-generated RTL (Cursor/Claude Code)")
    sp.add_argument("--source", required=True,
                    help="Directory containing the generated RTL files")
    sp.add_argument("--label", help="Optional human label")
    sp.add_argument("--no-evaluate", action="store_true")
    sp.set_defaults(func=cmd_ingest_baseline)

    sp = sub.add_parser("ingest-golden",
                        help="Sanity check: copy golden RTL as candidate")
    sp.add_argument("--label", help="Optional human label")
    sp.add_argument("--no-evaluate", action="store_true")
    sp.set_defaults(func=cmd_ingest_golden)

    sp = sub.add_parser("evaluate",
                        help="Run all enabled checks against a run dir")
    sp.add_argument("--run", default="latest",
                    help="run id, run dir path, or 'latest' (default)")
    sp.add_argument("--no-fill", action="store_true",
                    help="Don't fill missing required files from golden")
    sp.set_defaults(func=cmd_evaluate)

    sp = sub.add_parser("report",
                        help="Aggregate eval results into JSON/CSV/MD/term")
    sp.set_defaults(func=cmd_report)

    sp = sub.add_parser("run-all",
                        help="prepare -> spec-pack -> generate -> evaluate -> report")
    sp.add_argument("--label")
    sp.add_argument("--api-key")
    sp.add_argument("--model")
    sp.add_argument("--extra")
    sp.add_argument("--python-bin")
    sp.add_argument("--baseline",
                    help="Directory of externally-generated RTL to also evaluate")
    sp.add_argument("--skip-verifagent", action="store_true",
                    help="Only do baseline + report (skip the agent run)")
    sp.set_defaults(func=cmd_run_all)

    return p


def main(argv: Optional[List[str]] = None) -> int:
    p = build_parser()
    args = p.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
