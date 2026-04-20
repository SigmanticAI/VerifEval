"""
Aggregation, comparison, and reporting across runs.

Reads each `runs/<id>/eval/results.json` and emits:
  * JSON aggregate
  * CSV (one row per run, one column per check)
  * Markdown summary with per-check breakdown
  * Compact terminal table
  * Comparison: VerifAgent vs prompt-only baseline
"""

from __future__ import annotations

import csv
import io
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

from .paths import Target
from .runinfo import RunInfo, load_run


@dataclass
class RunSummary:
    run_id: str
    mode: str
    target: str
    total_score: float
    checks: Dict[str, Dict[str, Any]]   # name -> {status, score, weight, ...}
    created_at: str = ""


def collect_runs(target: Target) -> List[RunSummary]:
    out: List[RunSummary] = []
    if not target.runs_root.exists():
        return out
    for d in sorted(target.runs_root.iterdir()):
        if not d.is_dir():
            continue
        results = d / "eval" / "results.json"
        if not results.exists():
            continue
        try:
            data = json.loads(results.read_text())
        except Exception:
            continue
        try:
            info = load_run(d)
        except Exception:
            info = None
        out.append(
            RunSummary(
                run_id=data.get("run_id", d.name),
                mode=data.get("mode", "unknown"),
                target=data.get("target", target.name),
                total_score=float(data.get("total_score", 0.0)),
                checks={c["name"]: c for c in data.get("checks", [])},
                created_at=info.created_at if info else "",
            )
        )
    return out


def to_csv(runs: List[RunSummary]) -> str:
    """Wide CSV: row=run, columns=check scores + statuses + total."""
    if not runs:
        return ""
    check_names: List[str] = []
    seen = set()
    for r in runs:
        for n in r.checks:
            if n not in seen:
                check_names.append(n)
                seen.add(n)
    buf = io.StringIO()
    fieldnames = ["run_id", "mode", "target", "created_at", "total_score"]
    for n in check_names:
        fieldnames += [f"{n}.status", f"{n}.score", f"{n}.weighted"]
    w = csv.DictWriter(buf, fieldnames=fieldnames)
    w.writeheader()
    for r in runs:
        row: Dict[str, Any] = {
            "run_id": r.run_id,
            "mode": r.mode,
            "target": r.target,
            "created_at": r.created_at,
            "total_score": round(r.total_score, 4),
        }
        for n in check_names:
            c = r.checks.get(n)
            if c is None:
                row[f"{n}.status"] = ""
                row[f"{n}.score"] = ""
                row[f"{n}.weighted"] = ""
            else:
                row[f"{n}.status"] = c.get("status", "")
                row[f"{n}.score"] = c.get("score", "")
                row[f"{n}.weighted"] = c.get("weighted", "")
        w.writerow(row)
    return buf.getvalue()


def to_markdown(runs: List[RunSummary]) -> str:
    if not runs:
        return "_no runs_\n"
    check_names: List[str] = []
    seen = set()
    for r in runs:
        for n in r.checks:
            if n not in seen:
                check_names.append(n)
                seen.add(n)
    lines = ["# VeeR EL2 benchmark report", "",
             f"- Total runs: **{len(runs)}**", ""]
    # Leaderboard
    lines += [
        "## Leaderboard",
        "",
        "| run_id | mode | total | " + " | ".join(check_names) + " |",
        "|--------|------|-------|" + "|".join(["---"] * len(check_names)) + "|",
    ]
    for r in sorted(runs, key=lambda x: -x.total_score):
        cells = []
        for n in check_names:
            c = r.checks.get(n)
            if c is None:
                cells.append("-")
            else:
                cells.append(f"{c.get('status','?')[:4]} {c.get('score',0):.2f}")
        lines.append(
            f"| `{r.run_id}` | `{r.mode}` | **{r.total_score*100:.1f}** | "
            + " | ".join(cells) + " |"
        )
    # Comparison: best per mode
    lines += ["", "## Best per mode", "", "| mode | best run | score |", "|------|----------|-------|"]
    by_mode: Dict[str, RunSummary] = {}
    for r in runs:
        cur = by_mode.get(r.mode)
        if cur is None or r.total_score > cur.total_score:
            by_mode[r.mode] = r
    for m, r in by_mode.items():
        lines.append(f"| `{m}` | `{r.run_id}` | {r.total_score*100:.1f} |")
    # VerifAgent vs Baseline
    va_runs = [r for r in runs if r.mode == "verifagent"]
    bl_runs = [r for r in runs if r.mode == "baseline"]
    if va_runs and bl_runs:
        va_best = max(va_runs, key=lambda x: x.total_score)
        bl_best = max(bl_runs, key=lambda x: x.total_score)
        lines += [
            "",
            "## VerifAgent vs Prompt-only Baseline",
            "",
            "| check | VerifAgent (best) | Baseline (best) | Δ |",
            "|-------|-------------------|------------------|---|",
        ]
        for n in check_names:
            a = va_best.checks.get(n, {})
            b = bl_best.checks.get(n, {})
            asc = a.get("score", 0.0)
            bsc = b.get("score", 0.0)
            lines.append(
                f"| `{n}` | {a.get('status','-')} {asc:.2f} | "
                f"{b.get('status','-')} {bsc:.2f} | {asc - bsc:+.2f} |"
            )
        lines.append(
            f"| **TOTAL** | **{va_best.total_score*100:.1f}** | "
            f"**{bl_best.total_score*100:.1f}** | "
            f"**{(va_best.total_score - bl_best.total_score)*100:+.1f}** |"
        )
    return "\n".join(lines) + "\n"


def to_terminal(runs: List[RunSummary]) -> str:
    if not runs:
        return "(no runs)\n"
    lines = []
    width = max(len(r.run_id) for r in runs)
    lines.append(f"{'run_id'.ljust(width)}  {'mode':<10} {'score':>6}")
    lines.append("-" * (width + 22))
    for r in sorted(runs, key=lambda x: -x.total_score):
        lines.append(
            f"{r.run_id.ljust(width)}  {r.mode:<10} {r.total_score*100:>6.1f}"
        )
    return "\n".join(lines) + "\n"


def write_reports(target: Target, runs: List[RunSummary]) -> Dict[str, Path]:
    target.reports_root.mkdir(parents=True, exist_ok=True)
    outputs: Dict[str, Path] = {}

    aggregate = {
        "target": target.name,
        "runs": [
            {
                "run_id": r.run_id,
                "mode": r.mode,
                "total_score": r.total_score,
                "created_at": r.created_at,
                "checks": r.checks,
            }
            for r in runs
        ],
    }
    p_json = target.reports_root / "aggregate.json"
    p_json.write_text(json.dumps(aggregate, indent=2))
    outputs["json"] = p_json

    p_csv = target.reports_root / "aggregate.csv"
    p_csv.write_text(to_csv(runs))
    outputs["csv"] = p_csv

    p_md = target.reports_root / "report.md"
    p_md.write_text(to_markdown(runs))
    outputs["md"] = p_md

    return outputs
