"""
Evaluation pipeline for the VeeR EL2 benchmark.

Given a `RunInfo` whose `candidate/design/` contains generated RTL, run a
battery of checks reusing the *golden* repo's verification infrastructure
(testbench/, design/flist*, tools/Makefile, etc.) and score the candidate.

Every check is fail-soft: a missing tool yields status=SKIPPED rather than
an exception, so the pipeline can run on lean machines as well as fully
provisioned ones (Vivado + Verilator + Questa + RISC-V GCC).
"""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from .paths import Target, env_or
from .runinfo import RunInfo
from .specpack import extract_top_interface, list_design_modules


# ---------------------------------------------------------------------------
# Tool detection
# ---------------------------------------------------------------------------


def _which(name: str) -> Optional[str]:
    return shutil.which(name)


def _find_vivado() -> Optional[str]:
    """Locate vivado (PATH or known locations / env)."""
    for cmd in ("vivado", "xelab"):
        p = _which(cmd)
        if p:
            return p
    for cand in (
        os.environ.get("VIVADO_BIN"),
        "/home/sulaiman/Vivado_ML/2025.2/Vivado/bin/vivado",
        "/opt/Xilinx/Vivado/2024.2/bin/vivado",
        "/opt/Xilinx/Vivado/2024.1/bin/vivado",
    ):
        if cand and Path(cand).exists() and os.access(cand, os.X_OK):
            return cand
    return None


def _find_questa() -> Optional[str]:
    for cmd in ("vsim", "vlog"):
        p = _which(cmd)
        if p:
            return p
    for cand in (
        os.environ.get("QUESTA_BIN"),
        "/home/rocky/questa/questasim/linux_x86_64/vsim",
        "/home/rocky/questa/questasim/linux/vsim",
    ):
        if cand and Path(cand).exists() and os.access(cand, os.X_OK):
            return cand
    return None


def _find_verible_lint() -> Optional[str]:
    for cmd in ("verible-verilog-lint",):
        p = _which(cmd)
        if p:
            return p
    return None


def _find_riscv_gcc() -> Optional[str]:
    for cmd in (
        "riscv64-unknown-elf-gcc",
        "riscv32-unknown-elf-gcc",
    ):
        p = _which(cmd)
        if p:
            return p
    return None


def _run(
    cmd: List[str],
    cwd: Optional[Path] = None,
    timeout: int = 600,
    env: Optional[Dict[str, str]] = None,
    log_path: Optional[Path] = None,
) -> Tuple[int, str, str, float]:
    """Run a subprocess; return (rc, stdout, stderr, elapsed_seconds).
    Always tee output to log_path if provided."""
    t0 = time.monotonic()
    try:
        proc = subprocess.run(
            cmd,
            cwd=str(cwd) if cwd else None,
            env=env,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        rc = proc.returncode
        stdout = proc.stdout or ""
        stderr = proc.stderr or ""
    except subprocess.TimeoutExpired as e:
        rc = -1
        stdout = (e.stdout or b"").decode(errors="replace") if isinstance(e.stdout, bytes) else (e.stdout or "")
        stderr = (
            (e.stderr or b"").decode(errors="replace")
            if isinstance(e.stderr, bytes)
            else (e.stderr or "")
        ) + f"\n[TIMEOUT after {timeout}s]\n"
    except FileNotFoundError as e:
        rc = -2
        stdout = ""
        stderr = f"{e}\n"
    elapsed = time.monotonic() - t0
    if log_path:
        log_path.parent.mkdir(parents=True, exist_ok=True)
        with open(log_path, "w") as f:
            f.write(f"$ {' '.join(cmd)}\n")
            f.write(f"# cwd: {cwd}\n")
            f.write(f"# rc: {rc}  elapsed: {elapsed:.1f}s\n\n")
            f.write("=== stdout ===\n")
            f.write(stdout)
            f.write("\n=== stderr ===\n")
            f.write(stderr)
    return rc, stdout, stderr, elapsed


# ---------------------------------------------------------------------------
# Result containers
# ---------------------------------------------------------------------------


@dataclass
class CheckResult:
    name: str
    status: str  # PASS | FAIL | SKIPPED | PARTIAL
    score: float = 0.0          # within [0,1]
    weight: float = 0.0
    elapsed_seconds: float = 0.0
    details: Dict[str, Any] = field(default_factory=dict)
    log_relpath: Optional[str] = None

    def weighted(self) -> float:
        return self.score * self.weight

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "status": self.status,
            "score": round(self.score, 4),
            "weight": round(self.weight, 4),
            "weighted": round(self.weighted(), 4),
            "elapsed_seconds": round(self.elapsed_seconds, 2),
            "details": self.details,
            "log": self.log_relpath,
        }


@dataclass
class EvalResult:
    run_id: str
    target: str
    mode: str
    started_at: str
    finished_at: str = ""
    checks: List[CheckResult] = field(default_factory=list)
    total_score: float = 0.0
    total_weight: float = 0.0

    def add(self, c: CheckResult) -> None:
        self.checks.append(c)

    def finalize(self) -> None:
        self.total_weight = sum(c.weight for c in self.checks if c.status != "SKIPPED")
        if self.total_weight > 0:
            self.total_score = (
                sum(c.weighted() for c in self.checks if c.status != "SKIPPED")
                / self.total_weight
            )
        else:
            self.total_score = 0.0
        self.finished_at = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

    def to_dict(self) -> Dict[str, Any]:
        return {
            "run_id": self.run_id,
            "target": self.target,
            "mode": self.mode,
            "started_at": self.started_at,
            "finished_at": self.finished_at,
            "total_score": round(self.total_score, 4),
            "total_weight": round(self.total_weight, 4),
            "checks": [c.to_dict() for c in self.checks],
        }


# ---------------------------------------------------------------------------
# Staging - assemble candidate + golden into a buildable workspace
# ---------------------------------------------------------------------------


def stage_candidate(target: Target, run: RunInfo) -> Path:
    """Create a workspace under <run>/stage/repo that mirrors the golden repo
    but with the candidate's design files overlaid.

    Returns the path to the staged repo root (this becomes RV_ROOT).
    """
    stage = run.stage_dir / "repo"
    if stage.exists():
        shutil.rmtree(stage)
    # Copy the *entire* golden repo first (cheap; ~13 MiB).  We use a
    # filesystem copy not a symlink because the golden tree must be writable
    # for `make` to land snapshots/, work files, etc.
    shutil.copytree(target.golden_repo, stage, symlinks=False)

    # Overlay candidate design files (only those that exist in the candidate)
    cand_design = run.candidate_design_dir
    overlaid: List[str] = []
    if cand_design.exists():
        for src in cand_design.rglob("*"):
            if not src.is_file():
                continue
            if src.suffix.lower() not in (".sv", ".v", ".svh", ".vh"):
                continue
            rel = src.relative_to(cand_design)
            dst = stage / "design" / rel
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dst)
            overlaid.append(str(rel))

    (run.stage_dir / "overlay_manifest.json").write_text(
        json.dumps({"overlaid_files": overlaid}, indent=2)
    )
    return stage


# ---------------------------------------------------------------------------
# Individual checks
# ---------------------------------------------------------------------------


def check_inventory(target: Target, run: RunInfo, weight: float) -> CheckResult:
    """Compare module inventory of candidate vs golden."""
    cand = list_design_modules(run.candidate_design_dir)
    gold = list_design_modules(target.golden_repo / "design")
    cand_mods = {m["module"] for m in cand}
    gold_mods = {m["module"] for m in gold}
    missing = sorted(gold_mods - cand_mods)
    extra = sorted(cand_mods - gold_mods)
    intersection = sorted(gold_mods & cand_mods)
    score = (len(intersection) / len(gold_mods)) if gold_mods else 0.0
    status = (
        "PASS"
        if score >= 0.95
        else "PARTIAL"
        if score > 0.0
        else "FAIL"
    )
    return CheckResult(
        name="inventory",
        status=status,
        score=score,
        weight=weight,
        details={
            "candidate_module_count": len(cand_mods),
            "golden_module_count": len(gold_mods),
            "match_count": len(intersection),
            "missing_modules": missing[:50],
            "extra_modules": extra[:50],
        },
    )


def check_port_match(target: Target, run: RunInfo, weight: float) -> CheckResult:
    """Compare the candidate top module's port list against golden."""
    top = target.golden_top_module
    top_filename = Path(target.golden_top_file).name
    cand_top = run.candidate_design_dir / top_filename
    gold_top = target.golden_repo / target.golden_top_file
    gold_iface = extract_top_interface(gold_top, top)
    cand_iface = extract_top_interface(cand_top, top)
    gold_ports = {p["name"] for p in gold_iface.get("ports", [])}
    cand_ports = {p["name"] for p in cand_iface.get("ports", [])}
    if not gold_ports:
        return CheckResult("port_match", "SKIPPED", 0.0, weight, details={"reason": "no golden ports parsed"})
    if not cand_iface.get("found"):
        return CheckResult(
            "port_match",
            "FAIL",
            0.0,
            weight,
            details={
                "reason": f"top module {top} not found in candidate file {top_filename}",
                "golden_port_count": len(gold_ports),
                "candidate_port_count": 0,
            },
        )
    inter = gold_ports & cand_ports
    miss = sorted(gold_ports - cand_ports)
    extra = sorted(cand_ports - gold_ports)
    # Direction agreement bonus
    cand_dir = {p["name"]: p["direction"] for p in cand_iface.get("ports", [])}
    gold_dir = {p["name"]: p["direction"] for p in gold_iface.get("ports", [])}
    dir_ok = sum(1 for n in inter if cand_dir.get(n) == gold_dir.get(n))
    name_score = len(inter) / len(gold_ports)
    dir_score = (dir_ok / len(inter)) if inter else 0.0
    score = 0.7 * name_score + 0.3 * dir_score
    status = "PASS" if score >= 0.95 else "PARTIAL" if score > 0.0 else "FAIL"
    return CheckResult(
        name="port_match",
        status=status,
        score=score,
        weight=weight,
        details={
            "golden_port_count": len(gold_ports),
            "candidate_port_count": len(cand_ports),
            "intersection": len(inter),
            "missing_ports_sample": miss[:20],
            "extra_ports_sample": extra[:20],
            "direction_agreement_rate": round(dir_score, 3),
        },
    )


def check_diff_similarity(target: Target, run: RunInfo, weight: float) -> CheckResult:
    """Cheap textual similarity proxy.

    For each file the candidate provides, compute the line-set Jaccard against
    the golden file with the same basename.  Aggregate as the average across
    candidate files.  This is a rough proxy and never the primary metric.
    """
    cand_dir = run.candidate_design_dir
    gold_design = target.golden_repo / "design"
    cand_files = [p for p in cand_dir.rglob("*") if p.is_file() and p.suffix.lower() in (".sv", ".v")]
    if not cand_files:
        return CheckResult("diff_similarity", "FAIL", 0.0, weight,
                           details={"reason": "no candidate RTL files"})
    # Build basename->path map for golden
    gold_by_name: Dict[str, Path] = {}
    for p in gold_design.rglob("*"):
        if p.is_file() and p.suffix.lower() in (".sv", ".v"):
            gold_by_name.setdefault(p.name, p)
    per_file: List[Dict[str, Any]] = []
    sims: List[float] = []
    for cf in cand_files:
        gf = gold_by_name.get(cf.name)
        if gf is None:
            per_file.append({"file": cf.name, "matched_golden": None, "jaccard": 0.0})
            sims.append(0.0)
            continue
        try:
            cand_lines = {l.strip() for l in cf.read_text(errors="ignore").splitlines() if l.strip()}
            gold_lines = {l.strip() for l in gf.read_text(errors="ignore").splitlines() if l.strip()}
        except Exception:
            sims.append(0.0)
            continue
        if not cand_lines and not gold_lines:
            sim = 1.0
        elif not cand_lines or not gold_lines:
            sim = 0.0
        else:
            sim = len(cand_lines & gold_lines) / len(cand_lines | gold_lines)
        sims.append(sim)
        per_file.append({"file": cf.name, "matched_golden": str(gf.relative_to(gold_design)), "jaccard": round(sim, 3)})
    score = sum(sims) / len(sims) if sims else 0.0
    status = "PARTIAL" if 0 < score < 0.95 else ("PASS" if score >= 0.95 else "FAIL")
    return CheckResult(
        name="diff_similarity",
        status=status,
        score=score,
        weight=weight,
        details={"average_jaccard": round(score, 3), "per_file": per_file[:50]},
    )


def check_verible_lint(target: Target, run: RunInfo, weight: float) -> CheckResult:
    tool = _find_verible_lint()
    if not tool:
        return CheckResult("verible_lint", "SKIPPED", 0.0, weight,
                           details={"reason": "verible-verilog-lint not found in PATH"})
    cand_files = sorted(p for p in run.candidate_design_dir.rglob("*")
                        if p.is_file() and p.suffix.lower() in (".sv", ".v"))
    if not cand_files:
        return CheckResult("verible_lint", "FAIL", 0.0, weight, details={"reason": "no candidate RTL"})
    log = run.eval_dir / "verible_lint.log"
    cmd = [tool] + [str(p) for p in cand_files]
    rc, out, err, dt = _run(cmd, timeout=120, log_path=log)
    # Verible reports one violation per line; count non-empty lines in stdout
    violations = sum(1 for ln in (out + "\n" + err).splitlines() if ln.strip())
    # Convert to a score: 0 violations -> 1.0; 100+ -> 0.0
    score = max(0.0, 1.0 - violations / 100.0)
    status = "PASS" if violations == 0 else "PARTIAL"
    return CheckResult(
        name="verible_lint",
        status=status,
        score=score,
        weight=weight,
        elapsed_seconds=dt,
        details={"violations": violations, "files": len(cand_files), "rc": rc},
        log_relpath=str(log.relative_to(run.run_dir)),
    )


def _generate_default_snapshot(stage_repo: Path, log: Path) -> Tuple[bool, str]:
    """Run veer.config to generate snapshots/default/* (defines, etc).

    Without these the design cannot be elaborated/compiled.
    """
    cfg = stage_repo / "configs" / "veer.config"
    if not cfg.exists():
        return False, "configs/veer.config missing"
    snap_dir = stage_repo / "snapshots" / "default"
    snap_dir.mkdir(parents=True, exist_ok=True)
    env = os.environ.copy()
    env["RV_ROOT"] = str(stage_repo)
    env["BUILD_PATH"] = str(snap_dir)
    rc, out, err, dt = _run(
        [str(cfg), "-target=default"],
        cwd=stage_repo,
        env=env,
        timeout=300,
        log_path=log,
    )
    if rc != 0:
        return False, f"veer.config rc={rc}; see {log.name}"
    if not (snap_dir / "common_defines.vh").exists():
        return False, "common_defines.vh not produced"
    return True, "ok"


def check_verilator_lint(target: Target, run: RunInfo, weight: float) -> CheckResult:
    tool = _which("verilator")
    if not tool:
        return CheckResult("verilator_lint", "SKIPPED", 0.0, weight,
                           details={"reason": "verilator not in PATH"})
    stage_repo = run.stage_dir / "repo"
    if not stage_repo.exists():
        stage_repo = stage_candidate(target, run)
    log = run.eval_dir / "verilator_lint.log"
    ok, msg = _generate_default_snapshot(stage_repo, run.eval_dir / "veer_config.log")
    if not ok:
        return CheckResult("verilator_lint", "FAIL", 0.0, weight,
                           details={"reason": f"snapshot setup: {msg}"})
    flist = stage_repo / "design" / "flist.lint"
    if not flist.exists():
        return CheckResult("verilator_lint", "FAIL", 0.0, weight,
                           details={"reason": "design/flist.lint missing"})
    env = os.environ.copy()
    env["RV_ROOT"] = str(stage_repo)
    cmd = [
        tool, "--lint-only", "-sv",
        "-Wno-fatal",
        "+define+RV_OPENSOURCE",
        "-f", str(flist),
        "--top-module", "el2_veer_wrapper",
    ]
    rc, out, err, dt = _run(cmd, cwd=stage_repo, env=env, timeout=600, log_path=log)
    text = out + err
    errs = len(re.findall(r"%Error", text))
    warns = len(re.findall(r"%Warning", text))
    if rc == 0 and errs == 0:
        score = 1.0
        status = "PASS"
    elif errs == 0:
        score = 0.5
        status = "PARTIAL"
    else:
        score = max(0.0, 1.0 - errs / 50.0)
        status = "FAIL"
    return CheckResult(
        name="verilator_lint",
        status=status,
        score=score,
        weight=weight,
        elapsed_seconds=dt,
        details={"rc": rc, "errors": errs, "warnings": warns},
        log_relpath=str(log.relative_to(run.run_dir)),
    )


def check_verilator_build(target: Target, run: RunInfo, weight: float) -> CheckResult:
    """Build the candidate via `make verilator-build` against the golden TB."""
    tool = _which("verilator")
    make = _which("make")
    if not tool or not make:
        return CheckResult("verilator_build", "SKIPPED", 0.0, weight,
                           details={"reason": "verilator/make missing"})
    stage_repo = run.stage_dir / "repo"
    if not stage_repo.exists():
        stage_repo = stage_candidate(target, run)
    work = run.stage_dir / "work_verilator"
    work.mkdir(parents=True, exist_ok=True)
    log = run.eval_dir / "verilator_build.log"
    env = os.environ.copy()
    env["RV_ROOT"] = str(stage_repo)
    timeout = int(target.evaluation.get("verilator_build_timeout", 1800))
    cmd = [make, "-f", f"{stage_repo}/tools/Makefile", "verilator-build"]
    rc, out, err, dt = _run(cmd, cwd=work, env=env, timeout=timeout, log_path=log)
    text = out + err
    errs = len(re.findall(r"%Error", text))
    binary = work / "obj_dir" / "Vtb_top"
    built = binary.exists() and os.access(binary, os.X_OK)
    if built and rc == 0:
        score = 1.0
        status = "PASS"
    elif rc == 0:
        score = 0.7
        status = "PARTIAL"
    else:
        score = 0.0
        status = "FAIL"
    return CheckResult(
        name="verilator_build",
        status=status,
        score=score,
        weight=weight,
        elapsed_seconds=dt,
        details={"rc": rc, "errors": errs, "binary_built": built},
        log_relpath=str(log.relative_to(run.run_dir)),
    )


def _have_hex_for(stage_repo: Path, test: str) -> Optional[Path]:
    hexd = stage_repo / "testbench" / "hex"
    cand = hexd / f"{test}.hex"
    if cand.exists():
        return cand
    # Some hex variants live under hex/user_mode0
    cand2 = hexd / "user_mode0" / f"{test}.hex"
    if cand2.exists():
        return cand2
    return None


def check_verilator_smoke(target: Target, run: RunInfo, weight: float) -> CheckResult:
    """Run a smoke test (default: hello_world) under the golden testbench.

    Uses the precompiled testbench/hex/<test>.hex if available so we don't
    require a RISC-V toolchain.  Reports per-test pass/fail and aggregates.
    """
    tool = _which("verilator")
    make = _which("make")
    if not tool or not make:
        return CheckResult("verilator_smoke", "SKIPPED", 0.0, weight,
                           details={"reason": "verilator/make missing"})
    stage_repo = run.stage_dir / "repo"
    if not stage_repo.exists():
        return CheckResult("verilator_smoke", "FAIL", 0.0, weight,
                           details={"reason": "stage repo not built; run verilator_build first"})
    binary = run.stage_dir / "work_verilator" / "obj_dir" / "Vtb_top"
    if not binary.exists():
        return CheckResult("verilator_smoke", "FAIL", 0.0, weight,
                           details={"reason": "Vtb_top binary missing; build failed"})
    work = run.stage_dir / "work_verilator"
    timeout = int(target.evaluation.get("verilator_run_timeout", 600))
    per_test: List[Dict[str, Any]] = []
    passed = 0
    for tname in target.smoke_tests():
        thex = _have_hex_for(stage_repo, tname)
        if thex is None:
            per_test.append({"test": tname, "status": "SKIPPED", "reason": "no precompiled hex"})
            continue
        # Place program.hex in the work dir
        shutil.copy2(thex, work / "program.hex")
        log = run.eval_dir / f"sim_{tname}.log"
        env = os.environ.copy()
        env["RV_ROOT"] = str(stage_repo)
        rc, out, err, dt = _run([str(binary), "--test-halt"], cwd=work, env=env,
                                timeout=timeout, log_path=log)
        text = out + err
        # Heuristic outcome: "TEST_PASSED" present and no fatal errors
        ok = "TEST_PASSED" in text or "Hello World from VeeR EL2" in text
        per_test.append({
            "test": tname,
            "status": "PASS" if ok else "FAIL",
            "rc": rc,
            "elapsed": round(dt, 2),
            "log": str(log.relative_to(run.run_dir)),
        })
        if ok:
            passed += 1
    runnable = sum(1 for t in per_test if t.get("status") in ("PASS", "FAIL"))
    if runnable == 0:
        return CheckResult("verilator_smoke", "SKIPPED", 0.0, weight,
                           details={"per_test": per_test, "reason": "no runnable tests"})
    score = passed / runnable
    status = "PASS" if score == 1.0 else "PARTIAL" if score > 0 else "FAIL"
    return CheckResult(
        name="verilator_smoke",
        status=status,
        score=score,
        weight=weight,
        details={
            "per_test": per_test,
            "passed": passed,
            "total_runnable": runnable,
        },
    )


def check_vivado_elab(target: Target, run: RunInfo, weight: float) -> CheckResult:
    """Optionally run Vivado xelab against the candidate via design/flist.lint."""
    vivado = _find_vivado()
    if not vivado:
        return CheckResult("vivado_elab", "SKIPPED", 0.0, weight,
                           details={"reason": "Vivado not found (vivado/xelab not in PATH)"})
    # Prefer xelab next to vivado
    xelab = Path(vivado).parent / "xelab"
    if not xelab.exists():
        return CheckResult("vivado_elab", "SKIPPED", 0.0, weight,
                           details={"reason": "xelab not found alongside vivado"})
    stage_repo = run.stage_dir / "repo"
    if not stage_repo.exists():
        stage_repo = stage_candidate(target, run)
    ok, msg = _generate_default_snapshot(stage_repo, run.eval_dir / "veer_config.log")
    if not ok:
        return CheckResult("vivado_elab", "FAIL", 0.0, weight,
                           details={"reason": f"snapshot setup: {msg}"})
    # Prefer flist.lint (it pre-includes the snapshot defines + el2_def.sv).
    flist = stage_repo / "design" / "flist.lint"
    if not flist.exists():
        flist = stage_repo / "design" / "flist"
    if not flist.exists():
        return CheckResult("vivado_elab", "FAIL", 0.0, weight,
                           details={"reason": "design/flist[.lint] missing"})
    # Build a Vivado .prj file from the flist - this is xelab's native input
    # format and avoids confusion between Verilator/Vivado flag syntaxes
    # (e.g. `-v <file>` means "library file" to Verilator but "--verbose" to
    # xelab).
    log = run.eval_dir / "vivado_elab.log"
    work = run.stage_dir / "work_vivado"
    work.mkdir(parents=True, exist_ok=True)
    rv_root = str(stage_repo)
    import shlex
    tokens: List[str] = []
    for line in flist.read_text().splitlines():
        s = line.strip()
        if not s or s.startswith("#"):
            continue
        s = s.replace("$RV_ROOT", rv_root)
        try:
            tokens.extend(shlex.split(s))
        except ValueError:
            tokens.extend(s.split())
    incdirs: List[str] = [
        str(stage_repo / "design" / "include"),
        str(stage_repo / "design" / "lib"),
        str(stage_repo / "snapshots" / "default"),
    ]
    # Force-pass tech-specific macros that Verilator picks up via the
    # snapshot include order but xelab's .prj loader doesn't propagate.
    defines: List[str] = [
        "RV_OPENSOURCE",
        "TEC_RV_ICG=clockhdr",
        "RV_BUILD_AXI4",
    ]
    sv_files: List[str] = []
    lib_files: List[str] = []
    i = 0
    while i < len(tokens):
        tok = tokens[i]
        if tok.startswith("+incdir+"):
            incdirs.append(tok[len("+incdir+"):])
        elif tok.startswith("+define+"):
            defines.append(tok[len("+define+"):])
        elif tok.startswith("+libext+") or tok == "+libext":
            pass
        elif tok == "-v" and i + 1 < len(tokens):
            lib_files.append(tokens[i + 1])
            i += 1
        elif tok == "-y" and i + 1 < len(tokens):
            i += 1  # ignore lib search dirs for now
        elif tok.startswith("+") or tok.startswith("-"):
            pass
        else:
            sv_files.append(tok)
        i += 1
    # Deduplicate while preserving order
    seen_inc = set()
    incdirs = [x for x in incdirs if not (x in seen_inc or seen_inc.add(x))]
    seen_files = set()
    sv_files = [x for x in sv_files if not (x in seen_files or seen_files.add(x))]
    lib_files = [x for x in lib_files if x not in seen_files]
    # Write a .prj file
    prj = work / "elab.prj"
    with open(prj, "w") as f:
        for sf in sv_files + lib_files:
            f.write(f'sv work "{sf}"\n')
    args: List[str] = ["-sv", "--relax", "--prj", str(prj),
                       "--top", "el2_veer_wrapper"]
    for d in defines:
        args += ["--define", d]
    for inc in incdirs:
        args += ["-i", inc]
    timeout = int(target.evaluation.get("vivado_elab_timeout", 1200))
    rc, out, err, dt = _run([str(xelab)] + args, cwd=work, timeout=timeout, log_path=log)
    text = out + err
    errs = len(re.findall(r"^ERROR:", text, re.MULTILINE))
    warns = len(re.findall(r"^WARNING:", text, re.MULTILINE))
    # Known xelab limitation: cannot standalone-elaborate a top with SV
    # interface ports.  When that's the *only* error, treat the parse as
    # successful (modules analyzed cleanly) but flag PARTIAL instead of FAIL.
    iface_only = (
        errs <= 2
        and "having interface port(s)" in text
        and "cannot be elaborated by itself" in text
    )
    if rc == 0 and errs == 0:
        score, status = 1.0, "PASS"
    elif iface_only:
        score, status = 0.7, "PARTIAL"
    elif errs == 0:
        score, status = 0.5, "PARTIAL"
    else:
        score, status = 0.0, "FAIL"
    return CheckResult(
        name="vivado_elab",
        status=status,
        score=score,
        weight=weight,
        elapsed_seconds=dt,
        details={
            "rc": rc, "errors": errs, "warnings": warns, "tool": str(xelab),
            "iface_port_limitation": iface_only,
        },
        log_relpath=str(log.relative_to(run.run_dir)),
    )


def check_vivado_synth(target: Target, run: RunInfo, weight: float) -> CheckResult:
    vivado = _find_vivado()
    if not vivado:
        return CheckResult("vivado_synth", "SKIPPED", 0.0, weight,
                           details={"reason": "Vivado not found"})
    if not target.eval_flag("enable_vivado_synth"):
        return CheckResult("vivado_synth", "SKIPPED", 0.0, weight,
                           details={"reason": "enable_vivado_synth=false in target.yaml"})
    # Stub: run a minimal `synth_design -rtl` via a tcl script.
    stage_repo = run.stage_dir / "repo"
    if not stage_repo.exists():
        stage_repo = stage_candidate(target, run)
    log = run.eval_dir / "vivado_synth.log"
    tcl = run.eval_dir / "synth.tcl"
    flist = stage_repo / "design" / "flist"
    rv_root = str(stage_repo)
    sv_files: List[str] = []
    incdirs: List[str] = []
    for line in flist.read_text().splitlines():
        s = line.strip().replace("$RV_ROOT", rv_root)
        if not s or s.startswith("#"):
            continue
        if s.startswith("+incdir+"):
            incdirs.append(s[len("+incdir+"):])
        elif s.startswith("+"):
            continue
        else:
            sv_files.append(s)
    tcl_lines = ["set_msg_config -severity INFO -suppress"]
    for inc in incdirs:
        tcl_lines.append(f"set_property include_dirs {{{inc}}} [current_fileset]")
    for f in sv_files:
        tcl_lines.append(f"read_verilog -sv {f}")
    tcl_lines += [
        "synth_design -top el2_veer_wrapper -part xc7a35tcsg324-1 -rtl",
        "exit",
    ]
    tcl.write_text("\n".join(tcl_lines) + "\n")
    timeout = int(target.evaluation.get("vivado_elab_timeout", 1800))
    rc, out, err, dt = _run([str(vivado), "-mode", "batch", "-source", str(tcl)],
                            cwd=run.eval_dir, timeout=timeout, log_path=log)
    text = out + err
    errs = len(re.findall(r"^ERROR:", text, re.MULTILINE))
    warns = len(re.findall(r"^WARNING:", text, re.MULTILINE))
    score = 1.0 if rc == 0 and errs == 0 else (0.5 if errs == 0 else 0.0)
    status = "PASS" if score == 1.0 else "PARTIAL" if score > 0 else "FAIL"
    return CheckResult(
        name="vivado_synth",
        status=status,
        score=score,
        weight=weight,
        elapsed_seconds=dt,
        details={"rc": rc, "errors": errs, "warnings": warns, "tool": vivado},
        log_relpath=str(log.relative_to(run.run_dir)),
    )


# ---------------------------------------------------------------------------
# Top-level evaluator
# ---------------------------------------------------------------------------


def _maybe_fill_from_golden(target: Target, run: RunInfo) -> List[str]:
    """If allow_golden_fallback is on, copy any required files that the
    candidate is missing FROM the golden tree.  This keeps the pipeline
    runnable on partial generations.  Records what was filled in."""
    if not target.allow_golden_fallback():
        return []
    filled: List[str] = []
    for rel in target.required_files() + target.optional_files():
        cand_path = run.candidate_design_dir / rel
        if cand_path.exists():
            continue
        gold_path = target.golden_repo / "design" / rel
        if not gold_path.exists():
            continue
        cand_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(gold_path, cand_path)
        filled.append(rel)
    return filled


def evaluate(target: Target, run: RunInfo, fill_from_golden: bool = True) -> EvalResult:
    """Run all configured checks and write results to <run>/eval/."""
    result = EvalResult(
        run_id=run.run_id,
        target=target.name,
        mode=run.mode,
        started_at=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    )
    weights = target.scoring_weights()

    # Optional fallback fill before staging
    filled: List[str] = []
    if fill_from_golden:
        filled = _maybe_fill_from_golden(target, run)
    (run.eval_dir / "filled_from_golden.json").write_text(
        json.dumps({"filled": filled}, indent=2)
    )

    # Pure-static checks (no staging required)
    if target.eval_flag("enable_module_inventory"):
        result.add(check_inventory(target, run, weights.get("inventory", 0.0)))
    if target.eval_flag("enable_port_match"):
        result.add(check_port_match(target, run, weights.get("port_match", 0.0)))
    if target.eval_flag("enable_file_diff"):
        result.add(check_diff_similarity(target, run, weights.get("diff_similarity", 0.0)))
    if target.eval_flag("enable_verible_lint"):
        result.add(check_verible_lint(target, run, weights.get("lint", 0.0) * 0.4))

    # Staged checks (need an overlaid repo)
    needs_stage = any(
        target.eval_flag(f) for f in [
            "enable_verilator_lint", "enable_verilator_build", "enable_verilator_smoke",
            "enable_vivado_elab", "enable_vivado_synth",
        ]
    )
    if needs_stage:
        stage_candidate(target, run)

    if target.eval_flag("enable_verilator_lint"):
        result.add(check_verilator_lint(target, run, weights.get("lint", 0.0) * 0.6))
    if target.eval_flag("enable_verilator_build"):
        result.add(check_verilator_build(target, run, weights.get("build", 0.0)))
    if target.eval_flag("enable_verilator_smoke"):
        result.add(check_verilator_smoke(target, run, weights.get("smoke", 0.0)))
    if target.eval_flag("enable_vivado_elab"):
        result.add(check_vivado_elab(target, run, weights.get("synth_elab", 0.0) * 0.5))
    if target.eval_flag("enable_vivado_synth"):
        result.add(check_vivado_synth(target, run, weights.get("synth_elab", 0.0) * 0.5))

    result.finalize()

    # Persist
    (run.eval_dir / "results.json").write_text(json.dumps(result.to_dict(), indent=2))
    write_summary_md(result, run.eval_dir / "summary.md")
    return result


def write_summary_md(result: EvalResult, path: Path) -> None:
    lines = [
        f"# Eval summary — {result.run_id}",
        "",
        f"- Target: `{result.target}`",
        f"- Mode:   `{result.mode}`",
        f"- Score:  **{result.total_score * 100:.1f} / 100** "
        f"(over weight {result.total_weight:.2f})",
        f"- Started:  {result.started_at}",
        f"- Finished: {result.finished_at}",
        "",
        "## Checks",
        "",
        "| check | status | score | weight | weighted | seconds | log |",
        "|-------|--------|-------|--------|----------|---------|-----|",
    ]
    for c in result.checks:
        lines.append(
            f"| `{c.name}` | {c.status} | {c.score:.2f} | {c.weight:.2f} | "
            f"{c.weighted():.3f} | {c.elapsed_seconds:.1f} | "
            f"{('`' + c.log_relpath + '`') if c.log_relpath else '-'} |"
        )
    lines += ["", "## Details", ""]
    for c in result.checks:
        lines += [f"### {c.name}", "```json", json.dumps(c.details, indent=2), "```", ""]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
