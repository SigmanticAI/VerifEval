"""
Spec-pack builder for the VeeR EL2 benchmark.

Reads the doc/config/RTL files listed in target.yaml and writes a
deterministic, versioned snapshot under `frameworks/veer_el2/spec/`.

The same spec-pack is fed (verbatim) to:
  * VerifAgent  - via a JSON manifest
  * Cursor / Claude Code (manual)  - via the prompt template + this dir

Spec-pack layout produced:
    spec/
    ├── INDEX.md                   # human-readable manifest
    ├── MANIFEST.json              # machine-readable manifest + SHA256 hashes
    ├── docs/<flat-renamed copies of selected docs>
    ├── configs/<config docs>
    ├── interfaces/<top-level RTL interface files, copied verbatim>
    ├── flists/<authoritative flists>
    ├── verification/INDEX.md      # pointer to golden testbench / tests
    └── normalized_spec.json       # extracted top module + ports + parameters
                                   # (used by VerifAgent --spec)

Why this design:
  * Reproducible: identical inputs => identical outputs (spec pack is
    versioned by the manifest hash).
  * Tool-agnostic: every generator only needs to know about this dir.
  * Inspectable: a human can `cat INDEX.md` and see the entire spec input
    surface.
"""

from __future__ import annotations

import hashlib
import json
import re
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from .paths import Target


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def _safe_copy(src: Path, dst: Path) -> None:
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dst)


def _flat_name(repo_rel: str) -> str:
    """Convert a repo-relative path to a flat filename for the docs/ subdir."""
    return repo_rel.replace("/", "__")


# ---------------------------------------------------------------------------
# Top-level RTL interface extraction
# ---------------------------------------------------------------------------


_PORT_RE = re.compile(
    r"\b(input|output|inout)\b\s*"               # direction
    r"(?:(reg|wire|logic|tri[01]?)\s+)?"        # net type
    r"(?:(signed|unsigned)\s+)?"
    r"(\[[^\]]+\]\s*)?"                          # packed range
    r"([A-Za-z_][A-Za-z0-9_]*)"                  # name
    r"(?:\s*\[[^\]]+\])?",                       # unpacked range
    re.MULTILINE,
)
_MODULE_RE = re.compile(r"\bmodule\s+([A-Za-z_][A-Za-z0-9_]*)\b")
_PARAM_RE = re.compile(
    r"\bparameter\s+(?:[A-Za-z_]\w*\s+)?([A-Za-z_]\w*)\s*=\s*([^,;\)]+)",
    re.MULTILINE,
)


def _strip_comments(text: str) -> str:
    # IMPORTANT: strip line-comments BEFORE block-comments.  Otherwise
    # the regex `/\*.*?\*/` will gobble across lines because typical SV
    # banner comments like `//********` contain the byte sequence `/*`.
    text = re.sub(r"//[^\n]*", "", text)
    text = re.sub(r"/\*.*?\*/", "", text, flags=re.DOTALL)
    return text


def extract_top_interface(rtl_path: Path, top_module: str) -> Dict[str, Any]:
    """Extract module name, parameters, ports of `top_module` from RTL.

    This is a tolerant best-effort extractor.  It is NOT a full SV parser.
    Used for: (a) generating normalized_spec.json (b) port-match metric.
    """
    if not rtl_path.exists():
        return {"module": top_module, "found": False, "ports": [], "parameters": []}

    text = _strip_comments(rtl_path.read_text(errors="ignore"))

    # Find the top module declaration; isolate its header up to first ');' that
    # closes the port list.  We rely on top-level structure: `module NAME ...
    # ( ports ); body endmodule`.
    mod_idx = None
    for m in _MODULE_RE.finditer(text):
        if m.group(1) == top_module:
            mod_idx = m.end()
            break
    if mod_idx is None:
        return {"module": top_module, "found": False, "ports": [], "parameters": []}

    def _skip_balanced_parens(start: int) -> int:
        """Return idx just past the next balanced (...) starting at/near `start`."""
        # Find the first '(' from start (skipping whitespace/`#`/comments)
        i = start
        while i < len(text) and text[i] != "(":
            i += 1
        if i >= len(text):
            return start
        depth = 0
        for j in range(i, len(text)):
            if text[j] == "(":
                depth += 1
            elif text[j] == ")":
                depth -= 1
                if depth == 0:
                    return j + 1
        return len(text)

    # Some modules use `module NAME #( params ) ( ports );` — detect optional
    # parameter block and skip it before extracting the port list.
    cursor = mod_idx
    # find next non-space/non-comment char
    while cursor < len(text) and text[cursor] in " \t\r\n":
        cursor += 1
    # also skip "import pkg::*;" blocks
    while True:
        m = re.match(r"\s*import\s+[^;]+;", text[cursor:])
        if not m:
            break
        cursor += m.end()
    # if next non-space char is '#', the next () is parameters — skip it
    j = cursor
    while j < len(text) and text[j] in " \t\r\n":
        j += 1
    parameters_block = ""
    if j < len(text) and text[j] == "#":
        # Skip whitespace after '#'
        k = j + 1
        while k < len(text) and text[k] in " \t\r\n":
            k += 1
        end_params = _skip_balanced_parens(k)
        parameters_block = text[k:end_params]
        cursor = end_params

    # Now find the port list ()
    end_ports = _skip_balanced_parens(cursor)
    header = text[cursor:end_ports]

    ports: List[Dict[str, Any]] = []
    seen = set()
    for pm in _PORT_RE.finditer(header):
        direction = pm.group(1)
        width = (pm.group(4) or "").strip()
        name = pm.group(5)
        if name in seen or name in {"input", "output", "inout", "reg", "wire", "logic"}:
            continue
        seen.add(name)
        ports.append({"name": name, "direction": direction, "width": width})

    parameters: List[Dict[str, Any]] = []
    pseen = set()
    # Parameter sources: explicit `parameter` keywords inside parameter block
    # plus any `parameter` keywords appearing in the header proper.  Note that
    # `include "el2_param.vh"` style parameter lists won't be discovered
    # without preprocessing — that's accepted; the port list is the primary
    # normative interface for our metric.
    param_text = (parameters_block or "") + "\n" + header
    for pm in _PARAM_RE.finditer(param_text):
        name = pm.group(1)
        if name in pseen:
            continue
        pseen.add(name)
        parameters.append({"name": name, "default": pm.group(2).strip()})

    return {
        "module": top_module,
        "found": True,
        "file": str(rtl_path),
        "ports": ports,
        "parameters": parameters,
    }


# ---------------------------------------------------------------------------
# Module inventory across the design tree
# ---------------------------------------------------------------------------


def list_design_modules(design_root: Path) -> List[Dict[str, str]]:
    """Return [{file, module}] for every SV/V file under design_root."""
    out: List[Dict[str, str]] = []
    if not design_root.exists():
        return out
    for path in sorted(design_root.rglob("*")):
        if not path.is_file():
            continue
        if path.suffix.lower() not in (".sv", ".v"):
            continue
        try:
            text = _strip_comments(path.read_text(errors="ignore"))
        except Exception:
            continue
        for m in _MODULE_RE.finditer(text):
            out.append({"file": str(path.relative_to(design_root)), "module": m.group(1)})
    return out


# ---------------------------------------------------------------------------
# Spec-pack assembly
# ---------------------------------------------------------------------------


@dataclass
class SpecPackResult:
    spec_dir: Path
    manifest_path: Path
    normalized_spec_path: Path
    pack_hash: str
    files: List[Dict[str, Any]]


def build_spec_pack(target: Target, force: bool = False) -> SpecPackResult:
    """Build the spec-pack from the cloned golden repo."""
    repo = target.golden_repo
    if not repo.exists():
        raise FileNotFoundError(
            f"Golden repo not found at {repo}. Run `prepare` first."
        )
    out = target.spec_pack
    if out.exists() and force:
        # Wipe everything except the .keep markers placed by `mkdir -p` in tests
        for child in out.iterdir():
            if child.is_dir():
                shutil.rmtree(child)
            else:
                child.unlink()
    out.mkdir(parents=True, exist_ok=True)

    files_record: List[Dict[str, Any]] = []

    def _bring(repo_rel: str, dst_rel: str, kind: str) -> None:
        src = repo / repo_rel
        if not src.exists():
            files_record.append(
                {"src": repo_rel, "dst": None, "kind": kind, "status": "missing"}
            )
            return
        dst = out / dst_rel
        _safe_copy(src, dst)
        files_record.append(
            {
                "src": repo_rel,
                "dst": str(dst.relative_to(out)),
                "kind": kind,
                "status": "ok",
                "sha256": _sha256(src),
                "bytes": src.stat().st_size,
            }
        )

    spec_inputs = target.spec_inputs

    # Docs
    for d in spec_inputs.get("docs", []):
        _bring(d, f"docs/{_flat_name(d)}", kind="doc")

    # Configs
    for d in spec_inputs.get("configs", []):
        _bring(d, f"configs/{_flat_name(d)}", kind="config")

    # Flists
    for d in spec_inputs.get("flists", []):
        _bring(d, f"flists/{_flat_name(d)}", kind="flist")

    # Interface files (kept under preserved paths so the generator can copy them)
    for d in spec_inputs.get("interface_files", []):
        _bring(d, f"interfaces/{Path(d).name}", kind="interface")

    # Verification index (just point at golden testbench/verification dirs;
    # we don't bulk-copy them, generators don't need them — only evaluator does)
    verif_index = out / "verification" / "INDEX.md"
    verif_index.parent.mkdir(parents=True, exist_ok=True)
    verif_index.write_text(
        "# Verification infrastructure (reference)\n\n"
        "The golden VeeR EL2 verification flow lives in the cloned repo at:\n\n"
        f"- `{repo / 'testbench'}` - testbench top, asm/C tests, hex programs\n"
        f"- `{repo / 'verification' / 'block'}` - block-level verification\n"
        f"- `{repo / 'verification' / 'top'}` - top-level (pyuvm) verification\n"
        f"- `{repo / 'verification' / 'top' / 'README.md'}` - pyuvm tests README\n\n"
        "Generators do NOT need to produce a testbench.  The benchmark\n"
        "evaluator reuses this golden testbench against the candidate RTL.\n",
        encoding="utf-8",
    )

    # Top interface extraction -> normalized_spec.json
    top_module = target.golden_top_module
    top_file_rel = target.golden_top_file
    top_path = repo / top_file_rel
    top_iface = extract_top_interface(top_path, top_module)

    inventory = list_design_modules(repo / "design")

    normalized = {
        "design_name": target.name,
        "description": target.display_name,
        "upstream_repo": target.upstream_repo,
        "modules": [
            {
                "name": top_iface["module"],
                "description": "VeeR EL2 top-level core wrapper",
                "ports": top_iface.get("ports", []),
                "parameters": top_iface.get("parameters", []),
                "fsms": [],
                "key_signals": [],
            }
        ],
        "interfaces": [
            {
                "name": "top",
                "type": "custom",
                "signals": [p["name"] for p in top_iface.get("ports", [])],
            }
        ],
        "requirements": [
            {
                "id": "REQ-001",
                "description": "Implement the VeeR EL2 RISC-V core matching the docs/source/ specifications and the el2_veer_wrapper port list.",
                "priority": "high",
                "category": "functional",
            },
            {
                "id": "REQ-002",
                "description": "Pass the existing testbench/asm hello_world test running under the golden Verilator testbench (testbench/tb_top.sv + testbench/test_tb_top.cpp).",
                "priority": "high",
                "category": "functional",
            },
            {
                "id": "REQ-003",
                "description": "Synthesize / elaborate cleanly under Verible lint and Verilator --lint-only against design/flist.lint.",
                "priority": "medium",
                "category": "quality",
            },
        ],
        "corner_cases": [
            {
                "id": "CC-001",
                "description": "Reset behavior must match the golden core exactly.",
                "how_to_test": "Apply rst_l low for >= 4 cycles; check pc/regfile match.",
            }
        ],
        "module_inventory": inventory,
    }
    normalized_path = out / "normalized_spec.json"
    with open(normalized_path, "w") as f:
        json.dump(normalized, f, indent=2)

    # Manifest with hash for reproducibility
    pack_hash_input = json.dumps(
        sorted(
            (r.get("dst", ""), r.get("sha256", "")) for r in files_record if r["status"] == "ok"
        ),
        sort_keys=True,
    ).encode()
    pack_hash = hashlib.sha256(pack_hash_input).hexdigest()

    manifest = {
        "target": target.name,
        "upstream_repo": target.upstream_repo,
        "upstream_commit": target.upstream_commit,
        "top_module": top_module,
        "top_file": top_file_rel,
        "pack_hash": pack_hash,
        "files": files_record,
        "module_inventory_count": len(inventory),
        "ports_count": len(top_iface.get("ports", [])),
        "parameters_count": len(top_iface.get("parameters", [])),
    }
    manifest_path = out / "MANIFEST.json"
    with open(manifest_path, "w") as f:
        json.dump(manifest, f, indent=2)

    # Write a human-readable INDEX
    lines = [
        f"# VeeR EL2 spec pack",
        "",
        f"- Target: **{target.display_name}**",
        f"- Upstream: {target.upstream_repo}",
        f"- Upstream commit: `{target.upstream_commit or '(unknown)'}`",
        f"- Top module: `{top_module}`",
        f"- Top file:   `{top_file_rel}`",
        f"- Pack hash:  `{pack_hash}`",
        f"- Files included: {sum(1 for r in files_record if r['status']=='ok')}",
        f"- Module inventory entries: {len(inventory)}",
        "",
        "## Files",
        "",
        "| kind | source (in golden repo) | included as | sha256 (head) |",
        "|------|--------------------------|--------------|---------------|",
    ]
    for r in files_record:
        if r["status"] == "ok":
            lines.append(
                f"| {r['kind']} | `{r['src']}` | `{r['dst']}` | `{r['sha256'][:12]}` |"
            )
        else:
            lines.append(f"| {r['kind']} | `{r['src']}` | _missing_ | _-_ |")
    lines += [
        "",
        "## Generation contract",
        "",
        "Any generator (VerifAgent or prompt-only baseline) is expected to write",
        f"its candidate RTL into `<run>/candidate/{target.candidate_subdir()}/`.",
        "",
        f"Required: {target.required_files()}",
        f"Optional: {target.optional_files()}",
        "",
        "See the framework README and `prompts/veer_el2_generation_prompt.txt`.",
    ]
    (out / "INDEX.md").write_text("\n".join(lines) + "\n", encoding="utf-8")

    return SpecPackResult(
        spec_dir=out,
        manifest_path=manifest_path,
        normalized_spec_path=normalized_path,
        pack_hash=pack_hash,
        files=files_record,
    )
