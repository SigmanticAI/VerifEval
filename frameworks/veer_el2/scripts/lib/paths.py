"""
Path/config helpers for the VeeR EL2 benchmark framework.

All other scripts in this framework go through this module so that there is
exactly one place that knows about absolute paths, the cloned repo location,
and the target.yaml schema.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict

import yaml


# Absolute path of `frameworks/veer_el2/`
FRAMEWORK_DIR = Path(__file__).resolve().parents[2]
# Absolute path of the VerifEval repository root
VERIFEVAL_ROOT = FRAMEWORK_DIR.parents[1]
# Default target config
DEFAULT_TARGET_CONFIG = FRAMEWORK_DIR / "configs" / "target.yaml"


@dataclass
class Target:
    """Resolved view of a target.yaml config."""

    name: str
    display_name: str
    upstream_repo: str
    upstream_commit: str

    # Resolved absolute paths
    golden_repo: Path
    spec_pack: Path
    runs_root: Path
    reports_root: Path
    baseline_drop: Path
    framework_dir: Path

    raw: Dict[str, Any]

    # ---- spec-pack manifest ----
    @property
    def spec_inputs(self) -> Dict[str, Any]:
        return self.raw.get("spec_inputs", {})

    @property
    def golden_top_module(self) -> str:
        return self.spec_inputs.get("golden_top_module", "")

    @property
    def golden_top_file(self) -> str:
        return self.spec_inputs.get("golden_top_file", "")

    # ---- generation contract ----
    @property
    def generation_contract(self) -> Dict[str, Any]:
        return self.raw.get("generation_contract", {})

    def required_files(self) -> list[str]:
        return list(self.generation_contract.get("required_files", []))

    def optional_files(self) -> list[str]:
        return list(self.generation_contract.get("optional_files", []))

    def candidate_subdir(self) -> str:
        return str(self.generation_contract.get("candidate_subdir", "design"))

    def allow_golden_fallback(self) -> bool:
        return bool(self.generation_contract.get("allow_golden_fallback", True))

    # ---- evaluation toggles ----
    @property
    def evaluation(self) -> Dict[str, Any]:
        return self.raw.get("evaluation", {})

    def eval_flag(self, name: str, default: bool = False) -> bool:
        return bool(self.evaluation.get(name, default))

    def smoke_tests(self) -> list[str]:
        return list(self.evaluation.get("smoke_tests", []))

    def scoring_weights(self) -> Dict[str, float]:
        return dict(self.raw.get("scoring_weights", {}))


def _resolve(p: str) -> Path:
    """Resolve a path that may be relative-to-VerifEval or absolute."""
    pth = Path(p)
    if pth.is_absolute():
        return pth
    return (VERIFEVAL_ROOT / pth).resolve()


def load_target(config_path: Path | None = None) -> Target:
    """Load and resolve a target config."""
    cfg_path = Path(config_path) if config_path else DEFAULT_TARGET_CONFIG
    if not cfg_path.exists():
        raise FileNotFoundError(f"target config not found: {cfg_path}")
    with open(cfg_path) as f:
        raw = yaml.safe_load(f)
    p = raw.get("paths", {})
    return Target(
        name=raw["target_name"],
        display_name=raw.get("display_name", raw["target_name"]),
        upstream_repo=raw.get("upstream_repo", ""),
        upstream_commit=raw.get("upstream_commit", ""),
        golden_repo=_resolve(p["golden_repo"]),
        spec_pack=_resolve(p["spec_pack"]),
        runs_root=_resolve(p["runs_root"]),
        reports_root=_resolve(p["reports_root"]),
        baseline_drop=_resolve(p["baseline_drop"]),
        framework_dir=FRAMEWORK_DIR,
        raw=raw,
    )


def env_or(default: str, *names: str) -> str:
    """Return the first non-empty env var value, else default."""
    for n in names:
        v = os.environ.get(n, "").strip()
        if v:
            return v
    return default
