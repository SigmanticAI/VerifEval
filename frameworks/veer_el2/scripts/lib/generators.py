"""
Two generator backends for the VeeR EL2 benchmark:

  1. VerifAgentGenerator   - drives `verifagent_v2.cli` (or fallback inline
                              python) to produce a candidate RTL set.
  2. BaselineDropGenerator - copies an externally-generated RTL tree (e.g.
                              from Cursor/Claude Code) into the candidate
                              area.  This is the "prompt-only" mode.

Both produce the same candidate dir structure so the evaluator does not need
to know how the candidate was made.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional

from .paths import Target
from .runinfo import RunInfo


# ---------------------------------------------------------------------------
# Prompt assembly
# ---------------------------------------------------------------------------


PROMPT_TEMPLATE_PATH_REL = "prompts/veer_el2_generation_prompt.txt"


def render_prompt(target: Target, spec_pack_dir: Path) -> str:
    """Build the full text prompt sent to a generator.

    Combines the on-disk template with the resolved spec-pack manifest
    so the generator knows exactly which files to consult.
    """
    tmpl_path = target.framework_dir / PROMPT_TEMPLATE_PATH_REL
    if not tmpl_path.exists():
        raise FileNotFoundError(f"prompt template missing: {tmpl_path}")
    template = tmpl_path.read_text()

    manifest_path = spec_pack_dir / "MANIFEST.json"
    manifest_blob = manifest_path.read_text() if manifest_path.exists() else "{}"

    return template.format(
        target_name=target.name,
        display_name=target.display_name,
        upstream_repo=target.upstream_repo,
        spec_pack_dir=str(spec_pack_dir),
        candidate_subdir=target.candidate_subdir(),
        required_files=", ".join(target.required_files()),
        optional_files=", ".join(target.optional_files()),
        top_module=target.golden_top_module,
        top_file=target.golden_top_file,
        manifest_blob=manifest_blob[:8000],
    )


# ---------------------------------------------------------------------------
# VerifAgent backend
# ---------------------------------------------------------------------------


@dataclass
class GenerationResult:
    ok: bool
    files_written: List[str]
    log_path: Optional[Path]
    elapsed_seconds: float
    notes: str = ""


def run_verifagent(
    target: Target,
    run: RunInfo,
    spec_pack_dir: Path,
    *,
    api_key: Optional[str] = None,
    model: Optional[str] = None,
    extra_args: Optional[List[str]] = None,
    python_bin: Optional[str] = None,
) -> GenerationResult:
    """Invoke VerifAgent v2 to generate VeeR EL2 candidate RTL.

    The agent is given:
      * --spec <spec_pack>/normalized_spec.json   (so it skips its own analysis)
      * --output-dir <run>/verifagent
      * a freeform prompt rendered from the framework template

    After the agent finishes we sweep the agent's output dir for any .sv/.v
    files and copy them into <run>/candidate/design/.
    """
    log_path = run.run_dir / "generation.log"
    prompt = render_prompt(target, spec_pack_dir)
    (run.run_dir / "prompt.txt").write_text(prompt)

    agent_out = run.verifagent_dir
    agent_out.mkdir(parents=True, exist_ok=True)

    py = python_bin or os.environ.get("VERIFAGENT_PYTHON") or "python3.11"
    if shutil.which(py) is None:
        # Fallback to current python if explicit interpreter not on PATH
        py = sys.executable

    cmd: List[str] = [
        py, "-m", "verifagent_v2.cli", "generate",
        "--spec", str(spec_pack_dir / "normalized_spec.json"),
        "--output-dir", str(agent_out),
        "--prompt", prompt[:4000],  # CLI takes prompt as a single arg
        "--max-iterations", "1",
    ]
    if model:
        os.environ["VERIFAGENT_MODEL"] = model
    if api_key:
        cmd += ["--api-key", api_key]
    if extra_args:
        cmd += list(extra_args)

    env = os.environ.copy()
    # Make sure verifagent_v2 is importable: VerifAgent repo lives at
    # ${VERIFAGENT_HOME} (defaults to /home/<user>/VerifAgent).
    va_home = env.get("VERIFAGENT_HOME") or str(Path.home() / "VerifAgent")
    if Path(va_home).exists():
        env["PYTHONPATH"] = va_home + os.pathsep + env.get("PYTHONPATH", "")

    t0 = time.monotonic()
    try:
        proc = subprocess.run(
            cmd, env=env, capture_output=True, text=True, timeout=24 * 3600
        )
        rc = proc.returncode
        out = proc.stdout
        err = proc.stderr
    except FileNotFoundError as e:
        return GenerationResult(False, [], None, 0.0, notes=f"verifagent invocation failed: {e}")
    elapsed = time.monotonic() - t0

    log_path.write_text(
        f"$ {' '.join(cmd)}\nrc={rc}  elapsed={elapsed:.1f}s\n\n=== stdout ===\n{out}\n=== stderr ===\n{err}\n"
    )

    # Sweep agent output for RTL files; copy into candidate/design/
    written: List[str] = []
    if agent_out.exists():
        for src in agent_out.rglob("*"):
            if not src.is_file():
                continue
            if src.suffix.lower() not in (".sv", ".v", ".svh", ".vh"):
                continue
            rel = src.relative_to(agent_out)
            # If the agent organized things under a subdir like rtl/, design/ etc,
            # strip that and place under candidate/design/.
            parts = rel.parts
            if parts and parts[0].lower() in ("rtl", "design", "src"):
                parts = parts[1:]
            dst_rel = Path(*parts) if parts else rel.name
            dst = run.candidate_design_dir / dst_rel
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dst)
            written.append(str(dst_rel))

    return GenerationResult(
        ok=(rc == 0),
        files_written=written,
        log_path=log_path,
        elapsed_seconds=elapsed,
        notes=f"verifagent rc={rc}; {len(written)} RTL files copied",
    )


# ---------------------------------------------------------------------------
# Baseline drop backend
# ---------------------------------------------------------------------------


def ingest_baseline(
    target: Target,
    run: RunInfo,
    source_dir: Path,
    *,
    label: Optional[str] = None,
) -> GenerationResult:
    """Copy a Cursor/Claude-generated RTL tree from source_dir into the
    candidate area.

    The source dir is expected to contain SV/V files (recursively).  We
    preserve the directory structure under candidate/design/.
    """
    if not source_dir.exists() or not source_dir.is_dir():
        return GenerationResult(False, [], None, 0.0,
                                notes=f"source dir not found: {source_dir}")
    written: List[str] = []
    t0 = time.monotonic()
    for src in source_dir.rglob("*"):
        if not src.is_file():
            continue
        if src.suffix.lower() not in (".sv", ".v", ".svh", ".vh"):
            continue
        rel = src.relative_to(source_dir)
        parts = rel.parts
        if parts and parts[0].lower() in ("rtl", "design", "src"):
            parts = parts[1:]
        dst_rel = Path(*parts) if parts else Path(src.name)
        dst = run.candidate_design_dir / dst_rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)
        written.append(str(dst_rel))
    log_path = run.run_dir / "generation.log"
    log_path.write_text(
        f"baseline drop from {source_dir}\nlabel: {label or '(none)'}\n"
        f"copied {len(written)} files\n"
    )
    # Save the prompt template too, so the run is self-describing
    prompt_text = render_prompt(target, target.spec_pack)
    (run.run_dir / "prompt.txt").write_text(prompt_text)
    return GenerationResult(
        ok=bool(written),
        files_written=written,
        log_path=log_path,
        elapsed_seconds=time.monotonic() - t0,
        notes=f"baseline drop: {len(written)} files from {source_dir}",
    )


def ingest_golden(target: Target, run: RunInfo) -> GenerationResult:
    """Special mode: copy the GOLDEN RTL into candidate area.  Used as a
    sanity check / upper bound for the evaluator."""
    src = target.golden_repo / "design"
    return ingest_baseline(target, run, src, label="GOLDEN")
