"""
Per-run directory layout and metadata.

A "run" is one attempt at producing a candidate VeeR EL2 RTL set and
evaluating it.  Each run lives in its own directory under
`frameworks/veer_el2/runs/<run_id>/` and is fully self-contained:

    runs/<run_id>/
    ├── run.json              # metadata: mode, model, timestamps, prompt path
    ├── prompt.txt            # the exact prompt text fed to the generator
    ├── spec_pack/            # snapshot of spec inputs used (or symlink)
    ├── candidate/
    │   └── design/           # generated/dropped RTL (mirrors golden tree)
    ├── stage/                # area where evaluation builds + simulates
    │   ├── snapshots/...
    │   ├── work/...
    │   └── *.log
    ├── eval/
    │   ├── results.json      # machine-readable per-check results
    │   ├── summary.md        # human-readable summary
    │   └── *.log             # per-tool raw output
    └── verifagent/           # VerifAgent-only: raw agent output dir & logs
"""

from __future__ import annotations

import json
import os
import shutil
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional


@dataclass
class RunInfo:
    run_id: str
    run_dir: Path
    mode: str  # "verifagent" | "baseline" | "golden"
    created_at: str  # ISO-8601
    target_name: str
    extras: Dict[str, Any] = field(default_factory=dict)

    # Convenience subpaths
    @property
    def candidate_dir(self) -> Path:
        return self.run_dir / "candidate"

    @property
    def candidate_design_dir(self) -> Path:
        return self.candidate_dir / "design"

    @property
    def stage_dir(self) -> Path:
        return self.run_dir / "stage"

    @property
    def eval_dir(self) -> Path:
        return self.run_dir / "eval"

    @property
    def verifagent_dir(self) -> Path:
        return self.run_dir / "verifagent"

    @property
    def metadata_path(self) -> Path:
        return self.run_dir / "run.json"

    def write_metadata(self) -> None:
        meta = {
            "run_id": self.run_id,
            "mode": self.mode,
            "created_at": self.created_at,
            "target_name": self.target_name,
            "extras": self.extras,
        }
        with open(self.metadata_path, "w") as f:
            json.dump(meta, f, indent=2)


def make_run_id(mode: str, label: Optional[str] = None) -> str:
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    parts = [ts, mode]
    if label:
        # sanitize
        safe = "".join(c if c.isalnum() or c in "-_" else "_" for c in label)
        parts.append(safe[:32])
    return "_".join(parts)


def create_run(
    runs_root: Path,
    target_name: str,
    mode: str,
    label: Optional[str] = None,
    extras: Optional[Dict[str, Any]] = None,
) -> RunInfo:
    runs_root.mkdir(parents=True, exist_ok=True)
    run_id = make_run_id(mode, label)
    run_dir = runs_root / run_id
    run_dir.mkdir(parents=True, exist_ok=False)
    info = RunInfo(
        run_id=run_id,
        run_dir=run_dir,
        mode=mode,
        created_at=datetime.now(timezone.utc).isoformat(),
        target_name=target_name,
        extras=extras or {},
    )
    info.write_metadata()
    # pre-create canonical subdirs
    info.candidate_design_dir.mkdir(parents=True, exist_ok=True)
    (info.candidate_design_dir / "include").mkdir(parents=True, exist_ok=True)
    info.stage_dir.mkdir(parents=True, exist_ok=True)
    info.eval_dir.mkdir(parents=True, exist_ok=True)
    return info


def load_run(run_dir: Path) -> RunInfo:
    meta_path = run_dir / "run.json"
    if not meta_path.exists():
        raise FileNotFoundError(f"not a valid run dir (missing run.json): {run_dir}")
    with open(meta_path) as f:
        meta = json.load(f)
    return RunInfo(
        run_id=meta["run_id"],
        run_dir=run_dir,
        mode=meta["mode"],
        created_at=meta.get("created_at", ""),
        target_name=meta.get("target_name", ""),
        extras=meta.get("extras", {}),
    )


def latest_run(runs_root: Path, mode: Optional[str] = None) -> Optional[RunInfo]:
    if not runs_root.exists():
        return None
    candidates = []
    for d in runs_root.iterdir():
        if not d.is_dir():
            continue
        meta = d / "run.json"
        if not meta.exists():
            continue
        try:
            with open(meta) as f:
                m = json.load(f)
        except Exception:
            continue
        if mode and m.get("mode") != mode:
            continue
        candidates.append((d.stat().st_mtime, d))
    if not candidates:
        return None
    _, d = max(candidates)
    return load_run(d)
