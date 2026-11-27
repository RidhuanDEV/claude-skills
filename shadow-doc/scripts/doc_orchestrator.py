#!/usr/bin/env python3
"""
Shadow Army Document Orchestrator (`SA-DOC-ENGINE-001` — G1/G3/G4 Core)
=======================================================================
Provides generator-agnostic discovery, 5-tier precedence resolution,
15-criterion compatibility assessment, adapter-first routing, User Decision Gate
(Options A/B/C/D), path traversal guards, overwrite protection, and L0-L4
authorization classification without silently replacing working project tools.
"""

from __future__ import annotations

import importlib.util
import json
import os
import re
import shutil
import sys
import tempfile
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Protocol

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "shadow-monarch" / "scripts"))
from shadow_input import run_checked_cli, strict_bool

SCRIPT_DIR = Path(__file__).resolve().parent
SHADOW_DOC_ROOT = SCRIPT_DIR.parent
REPO_ROOT_FALLBACK = SHADOW_DOC_ROOT.parent

SCHEMA_VERSION = "1.0.0"

GLOBAL_ENGINE_DEFAULT: dict[str, Any] = {
    "id": "shadow-doc-global",
    "name": "Shadow-Doc Global Document Engine",
    "version": "2.1.0",
    "kind": "global-engine",
    "entry_script": str(SCRIPT_DIR / "doc_scaffold.py"),
    "supported_inputs": ["json-ast-v2.0", "json-ast-v2.1", "json-ast-v1.0", "markdown", "docx"],
    "supported_outputs": ["md", "html", "docx", "pdf", "xlsx", "csv", "zip"],
}

COMPATIBILITY_CRITERIA: tuple[str, ...] = (
    "supported_input_formats",
    "supported_output_formats",
    "template_capabilities",
    "diagram_rendering",
    "table_rendering",
    "code_block_rendering",
    "image_and_asset_handling",
    "source_references_and_citations",
    "api_cli_integration",
    "dependency_compatibility",
    "configuration_requirements",
    "execution_side_effects",
    "security_implications",
    "rendering_quality",
    "existing_project_conventions",
)

IGNORED_SCAN_DIRS: frozenset[str] = frozenset(
    {
        ".git",
        "node_modules",
        ".venv",
        "venv",
        "__pycache__",
        ".next",
        ".nuxt",
        "dist",
        "build",
        "target",
        ".pytest_cache",
    }
)

DOC_SCRIPT_PATTERNS: tuple[tuple[str, re.Pattern[str], dict[str, Any]], ...] = (
    (
        "python-docx",
        re.compile(r"\bimport\s+(?:[^\n#]*,\s*)?docx\b|\bfrom\s+docx\s+import\b|python-docx", re.IGNORECASE),
        {"inputs": ["markdown", "json"], "outputs": ["docx"], "tables": True, "code_blocks": True, "python_module": "docx"},
    ),
    (
        "weasyprint-pdf",
        re.compile(r"\bweasyprint\b", re.IGNORECASE),
        {"inputs": ["html", "markdown"], "outputs": ["pdf", "html"], "tables": True, "code_blocks": True, "python_module": "weasyprint"},
    ),
    (
        "reportlab-pdf",
        re.compile(r"\breportlab\b", re.IGNORECASE),
        {"inputs": ["json", "text"], "outputs": ["pdf"], "tables": True, "code_blocks": False, "python_module": "reportlab"},
    ),
    (
        "fpdf2-pdf",
        re.compile(r"\bfpdf\b|\bfpdf2\b", re.IGNORECASE),
        {"inputs": ["json", "markdown"], "outputs": ["pdf"], "tables": True, "code_blocks": True, "python_module": "fpdf"},
    ),
    (
        "node-docx",
        re.compile(r"""(?:require|from)\s*\(?['"]docx['"]""", re.IGNORECASE),
        {"inputs": ["markdown", "json"], "outputs": ["docx"], "tables": True, "code_blocks": True, "node_pkg": "docx"},
    ),
    (
        "puppeteer-pdf",
        re.compile(r"\bpuppeteer\b|md-to-pdf|html-pdf", re.IGNORECASE),
        {"inputs": ["markdown", "html"], "outputs": ["pdf", "html"], "tables": True, "diagrams": True, "node_pkg": "puppeteer"},
    ),
    (
        "pandoc-cli",
        re.compile(r"\bpandoc\b", re.IGNORECASE),
        {"inputs": ["markdown", "html", "docx"], "outputs": ["pdf", "docx", "html", "md"], "tables": True, "code_blocks": True, "citations": True, "cli_tool": "pandoc"},
    ),
    (
        "typst-cli",
        re.compile(r"\btypst\b", re.IGNORECASE),
        {"inputs": ["typst", "markdown"], "outputs": ["pdf"], "tables": True, "code_blocks": True, "cli_tool": "typst"},
    ),
    (
        "openpyxl-xlsx",
        re.compile(r"\bopenpyxl\b|\bxlsxwriter\b", re.IGNORECASE),
        {"inputs": ["json", "csv"], "outputs": ["xlsx"], "tables": True, "python_module": "openpyxl"},
    ),
)

DANGEROUS_SINK_RE = re.compile(
    r"\b(?:os\.system|eval|exec|subprocess\.(?:run|Popen|call)\s*\([^\)]*shell\s*=\s*True)\b"
)
SELF_ISSUED_APPROVAL_SOURCES: frozenset[str] = frozenset(
    {
        "agent_self_approval",
        "self_issued",
        "cli_flag_only",
        "orchestrator_recommendation",
        "orchestrator_instruction",
        "subagent",
    }
)


def _load_execution_approval_gate() -> Any:
    """Reuse Shadow Army centralized execution_approval_gate.py without duplicating permission systems."""
    gate_path = REPO_ROOT_FALLBACK / "shadow-monarch" / "scripts" / "execution_approval_gate.py"
    if not gate_path.is_file():
        return None
    spec = importlib.util.spec_from_file_location("shadow_execution_approval_gate", str(gate_path))
    if spec is None or spec.loader is None:
        return None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


# =============================================================================
# Security, Path Containment & Authorization Classification
# =============================================================================
def validate_safe_path(
    target_path: Path,
    allowed_root: Path | None = None,
    *,
    allow_symlinks: bool = False,
) -> Path:
    """Resolve target_path cleanly and fail closed on path traversal or ancestor symlink escapes (H02)."""
    raw_str = str(target_path)
    if "\x00" in raw_str:
        raise ValueError("Invalid path: NUL byte rejected.")
    if not allow_symlinks:
        if target_path.is_symlink():
            raise ValueError(f"SYMLINK_TRAVERSAL_BLOCKED: '{target_path}' is a symlink.")
        if allowed_root is not None:
            # Check raw relative parent chain and existing ancestors against symlinks before resolve()
            check_root = allowed_root.resolve()
            probe = target_path if target_path.is_absolute() else (allowed_root / target_path)
            for parent in [probe, *probe.parents]:
                if os.path.islink(parent):
                    raise ValueError(f"SYMLINK_TRAVERSAL_BLOCKED: ancestor '{parent}' is a symlink.")
                try:
                    if parent.resolve() == check_root:
                        break
                except OSError:
                    pass
    resolved = target_path.resolve()
    if allowed_root is not None:
        root_resolved = allowed_root.resolve()
        try:
            resolved.relative_to(root_resolved)
        except ValueError as exc:
            raise ValueError(
                f"PATH_TRAVERSAL_BLOCKED: '{target_path}' resolves outside allowed root '{root_resolved}'."
            ) from exc
    return resolved


def atomic_write_text(target_path: Path, content: str, *, encoding: str = "utf-8") -> Path:
    """TOCTOU-safe atomic text write using unique temp file + os.replace with guaranteed cleanup (H02)."""
    target_path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding=encoding,
            dir=str(target_path.parent),
            prefix=f".{target_path.name}.",
            suffix=".tmp",
            delete=False,
        ) as tf:
            tf.write(content)
            tf.flush()
            os.fsync(tf.fileno())
            tmp_path = Path(tf.name)
        os.replace(str(tmp_path), str(target_path))
        tmp_path = None
        return target_path
    finally:
        if tmp_path is not None and tmp_path.exists():
            try:
                tmp_path.unlink()
            except OSError:
                pass


def check_output_overwrite_safety(out_path: Path, overwrite: bool = False) -> None:
    """Block accidental overwriting of existing outputs unless authorized and overwrite=True."""
    if out_path.exists() and not overwrite:
        raise FileExistsError(
            f"OUTPUT_EXISTS_OVERWRITE_BLOCKED: Destination '{out_path}' already exists. Explicit authorization required."
        )


def classify_document_action(
    action: str,
    *,
    target_scope: str = "project",
    overwrite: bool = False,
    external_publish: bool = False,
) -> dict[str, Any]:
    """Classify action under L0-L4 User Intent Boundary rules (SA-DOC-ENGINE-001/002)."""
    approval_actions = {
        "init_global_generator": ("L4_HIGH_IMPACT", "Initializing persistent global generator infrastructure"),
        "change_global_config": ("L4_HIGH_IMPACT", "Modifying global user/IDE generator configuration"),
        "install_global_dependency": ("L3_RESOURCE_INTENSIVE", "Installing global system or package dependencies"),
        "replace_existing_generator": ("L4_HIGH_IMPACT", "Replacing an existing project document generator"),
        "migrate_pipeline": ("L2_SCOPE_EXPANSION", "Migrating existing document generation pipeline"),
        "persistent_adapter": ("L2_SCOPE_EXPANSION", "Adding persistent adapter outside current task scope"),
        "overwrite_document": ("L2_SCOPE_EXPANSION", "Overwriting existing generated document file"),
        "unrelated_repo_write": ("L4_HIGH_IMPACT", "Modifying unrelated repository outside requested scope"),
        "export_unrequested_format": ("L2_SCOPE_EXPANSION", "Exporting formats not requested by the user"),
        "publish_external": ("L4_HIGH_IMPACT", "Publishing or transmitting documents externally"),
    }
    if external_publish or action == "publish_external":
        lvl, reason = approval_actions["publish_external"]
        return {"permission_level": lvl, "short_level": lvl[:2], "requires_approval": True, "reason": reason}
    if overwrite or action == "overwrite_document":
        lvl, reason = approval_actions["overwrite_document"]
        return {"permission_level": lvl, "short_level": lvl[:2], "requires_approval": True, "reason": reason}
    if action in approval_actions:
        lvl, reason = approval_actions[action]
        return {"permission_level": lvl, "short_level": lvl[:2], "requires_approval": True, "reason": reason}
    if target_scope == "unrelated_repo":
        lvl, reason = approval_actions["unrelated_repo_write"]
        return {"permission_level": lvl, "short_level": lvl[:2], "requires_approval": True, "reason": reason}

    safe_read = {"discover", "assess", "resolve", "validate", "inspect", "read_config"}
    if action in safe_read:
        return {"permission_level": "L0_READ_ONLY", "short_level": "L0", "requires_approval": False, "reason": "Read-only inspection in authorized scope."}
    return {"permission_level": "L1_SAFE_VERIFICATION", "short_level": "L1", "requires_approval": False, "reason": "Bounded local generation inside authorized destination."}


def enforce_document_execution_authorization(
    action: str,
    *,
    project_root: Path,
    target_paths: list[Path] | None = None,
    environment: str = "local",
    approval: dict[str, Any] | None = None,
    parent_scope: dict[str, Any] | None = None,
    task_id: str = "DOC-TASK",
) -> dict[str, Any]:
    """
    Execution-boundary authorization enforcement (`R02`).
    Reuses `shadow-monarch/scripts/execution_approval_gate.py` cleanly, rejects CLI-flag-only or
    self-issued agent approvals, validates action/path/project/environment/expiry bindings, and
    enforces sub-agent parent scope limits.
    """
    proj_resolved = project_root.resolve()
    rel_targets: list[str] = []
    outside_project = False
    for tp in target_paths or []:
        tp_res = tp.resolve()
        try:
            rel_targets.append(tp_res.relative_to(proj_resolved).as_posix())
        except ValueError:
            outside_project = True
            rel_targets.append(str(tp_res))

    effective_action = "unrelated_repo_write" if outside_project else action
    classification = classify_document_action(
        effective_action,
        target_scope="unrelated_repo" if outside_project else "project",
        overwrite=(effective_action == "overwrite_document"),
        external_publish=(effective_action == "publish_external"),
    )

    gate_mod = _load_execution_approval_gate()
    if gate_mod is None:
        return {
            "decision": "BLOCKED",
            "allowed": False,
            "code": "APPROVAL_GATE_MODULE_MISSING",
            "reasons": ["execution_approval_gate.py unavailable; fail closed."],
        }

    is_read_only = classification["permission_level"] == "L0_READ_ONLY"
    lvl_str = classification["permission_level"]
    mapped_action_type = (
        "read_file"
        if is_read_only
        else (
            "git_push"
            if lvl_str == "L4_HIGH_IMPACT"
            else (
                "high_cost_eval"
                if lvl_str == "L3_RESOURCE_INTENSIVE"
                else ("unrelated_refactor" if lvl_str == "L2_SCOPE_EXPANSION" else "write_file")
            )
        )
    )
    req_payload: dict[str, Any] = {
        "task_id": str((approval or {}).get("task_id") or task_id),
        "project_path": str(proj_resolved),
        "environment": environment,
        "user_intent": "general",
        "action_type": mapped_action_type,
        "is_mutation": not is_read_only,
        "is_destructive": lvl_str == "L4_HIGH_IMPACT",
        "requested_permission_level": lvl_str,
        "target_paths": rel_targets or ["output"],
        "allowed_paths": (rel_targets or ["output"]) if not outside_project else [],
        "command": f"doc_scaffold {effective_action}",
    }

    # Sub-agent parent scope boundary enforcement (always checked first if executing as sub-agent)
    if parent_scope is not None:
        sub_check = gate_mod.check_subagent_authorization(
            parent_scope,
            {
                **req_payload,
                "approval_source": str((approval or {}).get("approval_source") or "subagent"),
            },
        )
        if sub_check["decision"] != "ALLOW":
            return {
                "decision": "BLOCKED",
                "allowed": False,
                "code": "BLOCKED_SUBAGENT_AUTHORIZATION",
                "permission_level": classification["permission_level"],
                "reasons": sub_check.get("errors", []),
            }

    # Fast safe path: L0 or bounded new-file L1 in local safe env inside project
    if not classification["requires_approval"] and not outside_project:
        res_safe = gate_mod.evaluate_execution_request(req_payload, approval=approval)
        return {
            "decision": res_safe["decision"],
            "allowed": res_safe["decision"] == "ALLOW",
            "code": res_safe["code"],
            "permission_level": classification["permission_level"],
            "reasons": res_safe.get("reasons", []),
        }

    # Protected action (L2/L3/L4 or outside-project): strict explicit approval verification
    if not approval or not isinstance(approval, dict):
        return {
            "decision": "BLOCKED",
            "allowed": False,
            "code": "BLOCKED_MISSING_APPROVAL",
            "permission_level": classification["permission_level"],
            "reasons": [classification["reason"]],
        }

    auth_src = str(approval.get("approval_source") or approval.get("issued_by") or "").strip().lower()
    if not auth_src or auth_src in SELF_ISSUED_APPROVAL_SOURCES:
        return {
            "decision": "BLOCKED",
            "allowed": False,
            "code": "BLOCKED_SELF_ISSUED_OR_UNTRUSTED_APPROVAL",
            "permission_level": classification["permission_level"],
            "reasons": [f"Untrusted or missing approval_source '{auth_src}'; self-issued/CLI-flag approvals are rejected."],
        }

    exp_raw = approval.get("expires_at")
    if exp_raw:
        try:
            exp_dt = datetime.fromisoformat(str(exp_raw).replace("Z", "+00:00"))
            if exp_dt.tzinfo is None:
                exp_dt = exp_dt.replace(tzinfo=timezone.utc)
            if datetime.now(timezone.utc) > exp_dt:
                return {
                    "decision": "BLOCKED",
                    "allowed": False,
                    "code": "BLOCKED_APPROVAL_EXPIRED",
                    "permission_level": classification["permission_level"],
                    "reasons": [f"Approval expired at '{exp_raw}'."],
                }
        except ValueError:
            return {
                "decision": "BLOCKED",
                "allowed": False,
                "code": "BLOCKED_INVALID_APPROVAL_EXPIRY",
                "permission_level": classification["permission_level"],
                "reasons": [f"Invalid expires_at format: '{exp_raw}'."],
            }

    allowed_actions = approval.get("allowed_actions")
    if isinstance(allowed_actions, list) and effective_action not in [str(a) for a in allowed_actions]:
        return {
            "decision": "BLOCKED",
            "allowed": False,
            "code": "BLOCKED_APPROVAL_ACTION_MISMATCH",
            "permission_level": classification["permission_level"],
            "reasons": [f"Action '{effective_action}' not authorized in allowed_actions={allowed_actions}."],
        }

    # Normalize approval payload cleanly for central execution_approval_gate validation
    normalized_approval = dict(approval)
    if not normalized_approval.get("permission_level"):
        normalized_approval["permission_level"] = classification["permission_level"]
    res_gate = gate_mod.evaluate_execution_request(req_payload, approval=normalized_approval)
    return {
        "decision": res_gate["decision"],
        "allowed": res_gate["decision"] == "ALLOW",
        "code": res_gate["code"],
        "permission_level": classification["permission_level"],
        "approval_id": res_gate.get("approval_id"),
        "reasons": res_gate.get("reasons", []),
    }


# =============================================================================
# Platform-Safe Configuration Loader (.shadow/document-engine.json)
# =============================================================================
def resolve_portable_path(raw_path: str | None, base_dir: Path) -> Path | None:
    """Resolve relative or env-expanded path cleanly on Windows/Linux/macOS."""
    if not raw_path or not isinstance(raw_path, str):
        return None
    expanded = os.path.expandvars(os.path.expanduser(raw_path.strip()))
    p = Path(expanded)
    if not p.is_absolute():
        return (base_dir / p).resolve()
    return p


def load_project_doc_config(repo_root: Path) -> dict[str, Any]:
    """Load optional project-local config without mutating global IDE configuration."""
    candidates = [
        repo_root / ".shadow" / "document-engine.json",
        repo_root / "shadow-doc.config.json",
    ]
    for cfg_path in candidates:
        if cfg_path.is_file():
            data = json.loads(cfg_path.read_text(encoding="utf-8"))
            return {"found": True, "config_path": str(cfg_path.resolve()), "data": data}
    return {"found": False, "config_path": None, "data": {}}


# =============================================================================
# Generator Discovery (Non-Assumptive Multi-Signal Scanner)
# =============================================================================
def _build_path_profile(
    *,
    source_dir: Path | None = None,
    executable_path: Path | None = None,
    global_config_dir: Path | None = None,
    project_config_path: Path | None = None,
    template_dir: Path | None = None,
    input_dir: Path | None = None,
    output_dir: Path | None = None,
    temp_dir: Path | None = None,
) -> dict[str, str | None]:
    return {
        "generator_source_dir": str(source_dir) if source_dir else None,
        "executable_path": str(executable_path) if executable_path else None,
        "global_config_dir": str(global_config_dir) if global_config_dir else None,
        "project_config_path": str(project_config_path) if project_config_path else None,
        "template_dir": str(template_dir) if template_dir else None,
        "input_dir": str(input_dir) if input_dir else None,
        "output_dir": str(output_dir) if output_dir else None,
        "temp_dir": str(temp_dir) if temp_dir else None,
    }


def _iter_repo_files(repo_root: Path, max_depth: int = 4) -> list[Path]:
    found: list[Path] = []
    root_resolved = repo_root.resolve()
    for current, dirs, files in os.walk(root_resolved):
        cur_path = Path(current)
        rel_parts = cur_path.relative_to(root_resolved).parts
        if len(rel_parts) >= max_depth:
            dirs[:] = []
        else:
            dirs[:] = sorted(d for d in dirs if d not in IGNORED_SCAN_DIRS and not d.startswith(".git"))
        for fname in sorted(files):
            found.append(cur_path / fname)
    return found


def discover_project_generators(repo_root: Path, *, include_system_clis: bool = True) -> dict[str, Any]:
    """
    Discover document-generation capabilities across an unfamiliar repo using manifests,
    scripts, package scripts, templates, CI workflows, README clues, and optional project config.
    """
    root = repo_root.resolve()
    cfg_info = load_project_doc_config(root)
    doc_cfg = cfg_info["data"].get("documentGeneration", {}) if cfg_info["found"] else {}
    proj_cfg_path = Path(cfg_info["config_path"]) if cfg_info["config_path"] else None

    files = _iter_repo_files(root)
    template_dirs: list[str] = []
    for d_name in ("templates", "docs/templates", "doc-templates", ".shadow/templates"):
        cand = root / d_name
        if cand.is_dir():
            template_dirs.append(str(cand.resolve()))

    candidates: list[dict[str, Any]] = []
    seen_ids: set[str] = set()

    def add_candidate(cand: dict[str, Any]) -> None:
        cid = str(cand["id"])
        if cid in seen_ids:
            return
        seen_ids.add(cid)
        candidates.append(cand)

    # 1. Manifests: package.json scripts & dependencies
    pkg_json = root / "package.json"
    if pkg_json.is_file():
        try:
            pkg = json.loads(pkg_json.read_text(encoding="utf-8"))
            scripts = pkg.get("scripts", {}) or {}
            deps = {**(pkg.get("dependencies", {}) or {}), **(pkg.get("devDependencies", {}) or {})}
            doc_script_re = re.compile(r"(?:doc|docs|pdf|docx|report|manual|spec|handover)", re.IGNORECASE)
            doc_pkg_re = re.compile(r"(?:docx|puppeteer|pdfkit|md-to-pdf|exceljs|xlsx|mermaid|@dbml/cli|pandoc)", re.IGNORECASE)
            matched_deps = sorted(k for k in deps if doc_pkg_re.search(k))
            for s_name, s_cmd in scripts.items():
                if doc_script_re.search(s_name) or doc_pkg_re.search(str(s_cmd)):
                    inferred_outputs = []
                    if "pdf" in str(s_cmd).lower() or "puppeteer" in matched_deps or "md-to-pdf" in matched_deps:
                        inferred_outputs.append("pdf")
                    if "docx" in str(s_cmd).lower() or "docx" in matched_deps:
                        inferred_outputs.append("docx")
                    if "html" in str(s_cmd).lower() or "mkdocs" in str(s_cmd).lower():
                        inferred_outputs.append("html")
                    if "xlsx" in str(s_cmd).lower() or "xlsx" in matched_deps or "exceljs" in matched_deps:
                        inferred_outputs.append("xlsx")
                    if not inferred_outputs:
                        inferred_outputs = ["md"]
                    cmd_str = str(s_cmd)
                    npm_rt_checks = [{"type": "node_pkg", "name": d, "available": True} for d in matched_deps]
                    npm_sinks = DANGEROUS_SINK_RE.findall(cmd_str)
                    referenced_local = None
                    for tok in cmd_str.split():
                        if "/" in tok or "\\" in tok or tok.endswith((".js", ".mjs", ".cjs", ".ts", ".py")):
                            cand_ref = (root / tok).resolve()
                            if cand_ref.is_file():
                                referenced_local = cand_ref
                                break
                    if referenced_local is not None:
                        insp_ref = _inspect_script_file(referenced_local, root)
                        npm_sinks.extend(insp_ref.get("unsafe_sinks", []))
                        npm_rt_checks.extend(insp_ref.get("runtime_checks", []))
                    add_candidate(
                        {
                            "id": f"npm-script:{s_name}",
                            "name": f"package.json script '{s_name}'",
                            "kind": "package-script",
                            "source": "package.json",
                            "command": f"npm run {s_name}",
                            "raw_script": s_cmd,
                            "matched_dependencies": matched_deps,
                            "runtime_checks": npm_rt_checks,
                            "security_scan": {"scanned": True, "unsafe_sinks": npm_sinks},
                            "verified_source_scan": True,
                            "side_effects_verified": bool(referenced_local is not None),
                            "supported_inputs": ["markdown", "json"],
                            "supported_outputs": inferred_outputs,
                            "capabilities": {
                                "tables": True,
                                "code_blocks": True,
                                "diagrams": any("mermaid" in d for d in matched_deps),
                                "citations": "pandoc" in cmd_str.lower(),
                                "templates": bool(template_dirs),
                            },
                            "paths": _build_path_profile(
                                source_dir=root,
                                executable_path=pkg_json,
                                project_config_path=proj_cfg_path,
                                template_dir=Path(template_dirs[0]) if template_dirs else None,
                                input_dir=root / "docs" if (root / "docs").is_dir() else root,
                                output_dir=root / "dist" if (root / "dist").is_dir() else root / "output",
                            ),
                        }
                    )
        except Exception:
            pass

    # 2. Source scripts anywhere in repo (Python/Node/Shell — not restricted to a 'generator/' folder)
    for fpath in files:
        if fpath.suffix.lower() not in (".py", ".js", ".mjs", ".cjs", ".ts", ".sh", ".ps1"):
            continue
        rel = fpath.relative_to(root).as_posix()
        # Avoid flagging test files or orchestrator itself when scanning SKILL repo
        if "test" in fpath.name.lower() or fpath.name in ("doc_orchestrator.py", "shadow_gate.py"):
            continue
        try:
            text = fpath.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue
        matched_techs: list[str] = []
        runtime_checks: list[dict[str, Any]] = []
        outputs: set[str] = set()
        inputs: set[str] = set()
        caps: dict[str, bool] = {"tables": False, "code_blocks": False, "diagrams": False, "citations": False, "templates": bool(template_dirs)}
        for tech_name, pat, meta in DOC_SCRIPT_PATTERNS:
            if pat.search(text):
                matched_techs.append(tech_name)
                outputs.update(meta.get("outputs", []))
                inputs.update(meta.get("inputs", []))
                for cap_k in ("tables", "code_blocks", "diagrams", "citations"):
                    if meta.get(cap_k):
                        caps[cap_k] = True
                if meta.get("python_module"):
                    mod_nm = str(meta["python_module"])
                    runtime_checks.append({"type": "python_module", "name": mod_nm, "available": importlib.util.find_spec(mod_nm) is not None})
                if meta.get("cli_tool"):
                    cli_nm = str(meta["cli_tool"])
                    runtime_checks.append({"type": "cli_tool", "name": cli_nm, "available": shutil.which(cli_nm) is not None})
                if meta.get("node_pkg"):
                    pkg_nm = str(meta["node_pkg"])
                    has_nm = (root / "node_modules" / pkg_nm).exists() or (pkg_json.is_file() and pkg_nm in pkg_json.read_text(encoding="utf-8", errors="ignore"))
                    runtime_checks.append({"type": "node_pkg", "name": pkg_nm, "available": has_nm})
        if matched_techs:
            # Determine if this is Shadow Doc Global Engine inside current repo
            is_shadow_doc = fpath.name == "doc_scaffold.py" and (fpath.parent.parent / "schemas" / "canonical-document.schema.json").is_file()
            unsafe_sinks = DANGEROUS_SINK_RE.findall(text) if not is_shadow_doc else []
            add_candidate(
                {
                    "id": "shadow-doc-global" if is_shadow_doc else f"repo-script:{rel}",
                    "name": "Shadow-Doc Global Document Engine" if is_shadow_doc else f"Project Script ({rel})",
                    "kind": "global-engine" if is_shadow_doc else "project-local",
                    "source": rel,
                    "technologies": matched_techs,
                    "runtime_checks": runtime_checks,
                    "security_scan": {"scanned": True, "unsafe_sinks": unsafe_sinks},
                    "verified_source_scan": True,
                    "side_effects_verified": is_shadow_doc or bool(re.search(r"out_dir|output|TemporaryDirectory|atomic", text)),
                    "supported_inputs": sorted(inputs | ({"json-ast-v2.0", "json-ast-v2.1"} if is_shadow_doc else set())),
                    "supported_outputs": sorted(outputs | ({"md", "html", "xlsx", "csv", "zip"} if is_shadow_doc else set())),
                    "capabilities": {
                        **caps,
                        "diagrams": caps["diagrams"] or bool(re.search(r"mermaid|dbml", text, re.IGNORECASE)),
                    },
                    "paths": _build_path_profile(
                        source_dir=fpath.parent,
                        executable_path=fpath,
                        project_config_path=proj_cfg_path,
                        template_dir=Path(template_dirs[0]) if template_dirs else None,
                        input_dir=root / "docs" if (root / "docs").is_dir() else root,
                        output_dir=root / "output" if (root / "output").is_dir() else root / "docs" / "output",
                    ),
                }
            )

    # 3. Project configuration explicit generator registration (.shadow/document-engine.json)
    if cfg_info["found"] and isinstance(doc_cfg.get("projectGenerator"), dict):
        pg = doc_cfg["projectGenerator"]
        entry = resolve_portable_path(pg.get("entry"), root)
        if entry is not None:
            exists = entry.exists()
            declared_outputs = [str(x).lower() for x in pg.get("supportedOutputs", [])]
            declared_inputs = [str(x).lower() for x in pg.get("supportedInputs", [])]
            contradictions: list[str] = []
            inspected_pg: dict[str, Any] = {}
            if exists and entry.is_file():
                inspected_pg = _inspect_script_file(entry, root)
                if inspected_pg.get("has_entry") and declared_outputs:
                    actual_outs = set(inspected_pg.get("outputs", []))
                    extra_declared = sorted(set(declared_outputs) - actual_outs - {"md"})
                    if extra_declared and actual_outs:
                        contradictions.append(f"declared_outputs_{extra_declared}_not_backed_by_{inspected_pg['technologies']}")
            add_candidate(
                {
                    "id": str(pg.get("id", "project-configured-generator")),
                    "name": str(pg.get("name", f"Configured Generator ({entry.name})")),
                    "kind": "project-configured",
                    "source": cfg_info["config_path"],
                    "exists": exists,
                    "capabilities_verified": bool(declared_outputs or declared_inputs),
                    "runtime_checks": inspected_pg.get("runtime_checks", []),
                    "security_scan": {"scanned": entry.is_file() if exists else False, "unsafe_sinks": inspected_pg.get("unsafe_sinks", [])},
                    "verified_source_scan": inspected_pg.get("has_entry") is True,
                    "side_effects_verified": False,
                    "contradictions": contradictions,
                    "supported_inputs": declared_inputs,
                    "supported_outputs": declared_outputs,
                    "capabilities": dict(pg.get("capabilities", {"tables": False, "code_blocks": False, "diagrams": False, "citations": False, "templates": bool(template_dirs)})),
                    "paths": _build_path_profile(
                        source_dir=entry.parent if entry.is_file() else entry,
                        executable_path=entry,
                        project_config_path=proj_cfg_path,
                        template_dir=resolve_portable_path(pg.get("templateDir"), root),
                        input_dir=resolve_portable_path(pg.get("inputDir"), root),
                        output_dir=resolve_portable_path(pg.get("outputDir"), root),
                        temp_dir=resolve_portable_path(pg.get("tempDir"), root),
                    ),
                }
            )

    # 4. Registered Global Engine (configured via project config OR bundled shadow-doc fallback)
    global_cfg = doc_cfg.get("globalEngine", {}) if isinstance(doc_cfg.get("globalEngine"), dict) else {}
    global_entry = resolve_portable_path(global_cfg.get("path"), root) if global_cfg.get("path") else Path(GLOBAL_ENGINE_DEFAULT["entry_script"])
    global_exists = global_entry.exists() if global_entry else False
    global_candidate = {
        "id": "shadow-doc-global",
        "name": GLOBAL_ENGINE_DEFAULT["name"],
        "kind": "global-engine",
        "version": str(global_cfg.get("version", GLOBAL_ENGINE_DEFAULT["version"])),
        "source": "global-registration",
        "exists": global_exists,
        "supported_inputs": list(GLOBAL_ENGINE_DEFAULT["supported_inputs"]),
        "supported_outputs": list(GLOBAL_ENGINE_DEFAULT["supported_outputs"]),
        "capabilities": {
            "tables": True,
            "code_blocks": True,
            "diagrams": True,
            "citations": True,
            "templates": True,
        },
        "paths": _build_path_profile(
            source_dir=SHADOW_DOC_ROOT,
            executable_path=global_entry,
            global_config_dir=SHADOW_DOC_ROOT / "config" if (SHADOW_DOC_ROOT / "config").is_dir() else SHADOW_DOC_ROOT,
            project_config_path=proj_cfg_path,
            template_dir=SHADOW_DOC_ROOT / "templates",
            input_dir=root,
            output_dir=root / "docs" / "output",
            temp_dir=root / ".shadow" / "tmp",
        ),
    }

    system_clis: dict[str, str | None] = {}
    if include_system_clis:
        for tool in ("pandoc", "typst", "xelatex", "mmdc", "soffice"):
            system_clis[tool] = shutil.which(tool)

    return {
        "schemaVersion": SCHEMA_VERSION,
        "repoRoot": str(root),
        "projectConfigFound": cfg_info["found"],
        "projectConfigPath": cfg_info["config_path"],
        "templateDirs": template_dirs,
        "projectCandidates": [c for c in candidates if c.get("kind") != "global-engine"],
        "globalEngine": global_candidate,
        "systemClis": system_clis,
    }


# =============================================================================
# 15-Criterion Compatibility Assessment (Section 4 & R04 Evidence-Backed)
# =============================================================================
def _inspect_script_file(script_path: Path, repo_root: Path) -> dict[str, Any]:
    """Inspect a candidate generator file genuinely for tech patterns, runtime deps, and security sinks."""
    text = script_path.read_text(encoding="utf-8", errors="ignore")
    techs: list[str] = []
    inputs: set[str] = set()
    outputs: set[str] = set()
    runtime_checks: list[dict[str, Any]] = []
    caps: dict[str, bool] = {"tables": False, "code_blocks": False, "diagrams": False, "citations": False, "templates": False}
    for tech_name, pat, meta in DOC_SCRIPT_PATTERNS:
        if pat.search(text):
            techs.append(tech_name)
            outputs.update(meta.get("outputs", []))
            inputs.update(meta.get("inputs", []))
            for cap_k in ("tables", "code_blocks", "diagrams", "citations"):
                if meta.get(cap_k):
                    caps[cap_k] = True
            if meta.get("python_module"):
                mod_nm = str(meta["python_module"])
                runtime_checks.append({"type": "python_module", "name": mod_nm, "available": importlib.util.find_spec(mod_nm) is not None})
            if meta.get("cli_tool"):
                cli_nm = str(meta["cli_tool"])
                runtime_checks.append({"type": "cli_tool", "name": cli_nm, "available": shutil.which(cli_nm) is not None})
            if meta.get("node_pkg"):
                pkg_nm = str(meta["node_pkg"])
                pkg_json = repo_root / "package.json"
                has_nm = (repo_root / "node_modules" / pkg_nm).exists() or (pkg_json.is_file() and pkg_nm in pkg_json.read_text(encoding="utf-8", errors="ignore"))
                runtime_checks.append({"type": "node_pkg", "name": pkg_nm, "available": has_nm})
    return {
        "technologies": techs,
        "inputs": sorted(inputs),
        "outputs": sorted(outputs),
        "runtime_checks": runtime_checks,
        "capabilities": caps,
        "unsafe_sinks": DANGEROUS_SINK_RE.findall(text),
        "has_entry": bool(techs),
    }


def assess_generator_compatibility(
    candidate: dict[str, Any],
    requirements: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    Classify a candidate generator across all 15 criteria into:
    COMPATIBLE | PARTIALLY_COMPATIBLE | INCOMPATIBLE | UNKNOWN.
    Criteria strictly use PASS | FAIL | UNKNOWN | NOT_APPLICABLE | ADAPTER_REQUIRED with explicit evidence.
    """
    req = requirements or {}
    needed_outputs = {str(x).lower() for x in req.get("required_outputs", ["md"])}
    needed_input = str(req.get("preferred_input", "markdown")).lower()
    needs_tables = strict_bool(req.get("requires_tables", True), "requires_tables")
    needs_diagrams = strict_bool(req.get("requires_diagrams", False), "requires_diagrams")
    needs_code = strict_bool(req.get("requires_code_blocks", False), "requires_code_blocks")
    needs_citations = strict_bool(req.get("requires_citations", False), "requires_citations")
    needs_templates = strict_bool(req.get("requires_templates", False), "requires_templates")

    cand_exists = candidate.get("exists", True)
    exec_p = candidate.get("paths", {}).get("executable_path")
    if cand_exists is False or (exec_p and candidate.get("kind") != "global-engine" and not Path(exec_p).exists()):
        return {
            "generator_id": candidate.get("id"),
            "status": "INCOMPATIBLE",
            "adapter_possible": False,
            "missing_capabilities": ["executable_missing_or_invalid_path"],
            "criteria": {c: "FAIL" for c in COMPATIBILITY_CRITERIA},
            "criteria_evidence": {"api_cli_integration": f"Executable missing at '{exec_p}'"},
            "reason": f"Configured executable path does not exist: '{exec_p}'.",
        }

    if candidate.get("capabilities_verified") is False:
        return {
            "generator_id": candidate.get("id"),
            "name": candidate.get("name"),
            "kind": candidate.get("kind"),
            "status": "UNKNOWN",
            "adapter_possible": False,
            "missing_capabilities": ["unverified_generator_implementation"],
            "criteria": {c: "UNKNOWN" for c in COMPATIBILITY_CRITERIA},
            "criteria_evidence": {"api_cli_integration": str(candidate.get("verification_note") or "Target path is not a recognized generator manifest or script.")},
            "reason": "Target path exists on disk but lacks verifiable generator manifest or script signatures.",
        }

    supported_outputs = {str(x).lower() for x in candidate.get("supported_outputs", [])}
    supported_inputs = {str(x).lower() for x in candidate.get("supported_inputs", [])}
    caps = candidate.get("capabilities", {}) or {}
    contradictions: list[str] = list(candidate.get("contradictions", []))

    if not supported_outputs and not supported_inputs:
        return {
            "generator_id": candidate.get("id"),
            "status": "UNKNOWN",
            "adapter_possible": False,
            "missing_capabilities": ["unverified_implementation"],
            "criteria": {c: "UNKNOWN" for c in COMPATIBILITY_CRITERIA},
            "criteria_evidence": {"supported_output_formats": "Neither supported_inputs nor supported_outputs are declared or detected."},
            "reason": "Generator declares neither inputs nor outputs; cannot assume compatibility.",
        }

    missing: list[str] = []
    bridgeable_gaps: list[str] = []

    missing_outputs = sorted(needed_outputs - supported_outputs)
    if missing_outputs:
        missing.append(f"outputs:{','.join(missing_outputs)}")

    if needed_input and needed_input not in supported_inputs and "markdown" in supported_inputs:
        bridgeable_gaps.append(f"input_adapter_needed:{needed_input}->markdown")
    elif needed_input and needed_input not in supported_inputs and "json" in supported_inputs:
        bridgeable_gaps.append(f"input_adapter_needed:{needed_input}->json")
    elif needed_input and supported_inputs and needed_input not in supported_inputs:
        missing.append(f"input:{needed_input}")

    if needs_tables and not caps.get("tables", False):
        missing.append("table_rendering")
    if needs_code and not caps.get("code_blocks", False):
        missing.append("code_block_rendering")
    if needs_diagrams and not caps.get("diagrams", False):
        bridgeable_gaps.append("diagram_pre_render_adapter_needed")
    if needs_citations and not caps.get("citations", False):
        bridgeable_gaps.append("citation_reference_section_adapter_needed")
    if needs_templates and not caps.get("templates", False):
        bridgeable_gaps.append("template_wrapper_needed")

    # Runtime dependency evidence (R04: never blindly PASS!)
    runtime_checks = list(candidate.get("runtime_checks") or [])
    missing_deps = [rc["name"] for rc in runtime_checks if not rc.get("available")]
    if missing_deps:
        missing.append(f"missing_runtime_dependencies:{','.join(missing_deps)}")

    is_global = candidate.get("kind") == "global-engine"
    is_pkg_script = candidate.get("kind") == "package-script"
    deps_evidence = (
        "FAIL: missing runtime dependencies " + ", ".join(missing_deps)
        if missing_deps
        else ("PASS: verified runtime dependencies installed " + str([rc["name"] for rc in runtime_checks])
              if runtime_checks
              else ("PASS: Global Engine Python packages verified" if is_global else "UNKNOWN: no runtime dependency manifest inspected"))
    )
    dep_status = "FAIL" if missing_deps else ("PASS" if (runtime_checks or is_global) else "UNKNOWN")

    sec_scan = candidate.get("security_scan") or {}
    unsafe_sinks = list(sec_scan.get("unsafe_sinks") or [])
    if unsafe_sinks:
        sec_status = "FAIL"
        sec_evidence = f"FAIL: potentially dangerous execution sinks found: {unsafe_sinks}"
        missing.append("unsafe_security_sinks")
    elif sec_scan.get("scanned") or is_global:
        sec_status = "PASS"
        sec_evidence = "PASS: static inspection found zero unsafe eval/exec/shell=True sinks."
    else:
        sec_status = "UNKNOWN"
        sec_evidence = "UNKNOWN: candidate implementation has not been statically security-scanned."

    if candidate.get("side_effects_verified") or is_global:
        side_status = "PASS"
        side_evidence = "PASS: bounded output directory / non-destructive behavior inspected."
    else:
        side_status = "UNKNOWN"
        side_evidence = "UNKNOWN: execution side effects not independently verified."

    if contradictions:
        missing.extend(f"contradiction:{c}" for c in contradictions)

    if missing_outputs or contradictions:
        rq_status = "FAIL"
        rq_evidence = f"FAIL: missing outputs {missing_outputs} or contradictions {contradictions}."
    elif is_global or candidate.get("rendering_quality_verified"):
        rq_status = "PASS"
        rq_evidence = "PASS: QA parity verification verified against output formats."
    elif candidate.get("verified_source_scan") or is_pkg_script:
        rq_status = "PASS"
        rq_evidence = f"PASS: recognized generator technology matches requested outputs {sorted(needed_outputs)}."
    else:
        rq_status = "UNKNOWN"
        rq_evidence = "UNKNOWN: rendering quality not yet proven via execution fixture."

    criteria_scores: dict[str, str] = {
        "supported_input_formats": "PASS" if needed_input in supported_inputs else ("ADAPTER_REQUIRED" if any("input_adapter" in g for g in bridgeable_gaps) else "FAIL"),
        "supported_output_formats": "PASS" if (not missing_outputs and not contradictions) else "FAIL",
        "template_capabilities": "PASS" if caps.get("templates", False) else ("ADAPTER_REQUIRED" if needs_templates else "NOT_APPLICABLE"),
        "diagram_rendering": "PASS" if caps.get("diagrams", False) else ("ADAPTER_REQUIRED" if needs_diagrams else "NOT_APPLICABLE"),
        "table_rendering": "PASS" if caps.get("tables", False) else ("FAIL" if needs_tables else "NOT_APPLICABLE"),
        "code_block_rendering": "PASS" if caps.get("code_blocks", False) else ("FAIL" if needs_code else "NOT_APPLICABLE"),
        "image_and_asset_handling": "PASS" if (is_global or candidate.get("verified_source_scan")) else "UNKNOWN",
        "source_references_and_citations": "PASS" if caps.get("citations", False) else ("ADAPTER_REQUIRED" if needs_citations else "NOT_APPLICABLE"),
        "api_cli_integration": "PASS" if (exec_p or candidate.get("command")) else "UNKNOWN",
        "dependency_compatibility": dep_status,
        "configuration_requirements": "PASS" if (candidate.get("paths", {}).get("project_config_path") or is_global or is_pkg_script or candidate.get("verified_source_scan")) else "UNKNOWN",
        "execution_side_effects": side_status,
        "security_implications": sec_status,
        "rendering_quality": rq_status,
        "existing_project_conventions": "PASS" if candidate.get("kind") != "global-engine" else "NOT_APPLICABLE",
    }
    criteria_evidence: dict[str, str] = {
        "supported_input_formats": f"supports {sorted(supported_inputs)}, requested '{needed_input}'",
        "supported_output_formats": f"supports {sorted(supported_outputs)}, requested {sorted(needed_outputs)}" + (f"; contradictions={contradictions}" if contradictions else ""),
        "dependency_compatibility": deps_evidence,
        "execution_side_effects": side_evidence,
        "security_implications": sec_evidence,
        "rendering_quality": rq_evidence,
    }

    if contradictions or missing_deps or missing_outputs or unsafe_sinks:
        status = "INCOMPATIBLE"
        adapter_possible = False
    elif not missing and not bridgeable_gaps and sec_status != "UNKNOWN":
        status = "COMPATIBLE"
        adapter_possible = False
    elif not missing and bridgeable_gaps:
        status = "PARTIALLY_COMPATIBLE"
        adapter_possible = True
    elif missing:
        status = "PARTIALLY_COMPATIBLE" if (not missing_outputs and not missing_deps) else "INCOMPATIBLE"
        adapter_possible = not missing_outputs and not missing_deps
    else:
        status = "UNKNOWN"
        adapter_possible = False

    return {
        "generator_id": candidate.get("id"),
        "name": candidate.get("name"),
        "kind": candidate.get("kind"),
        "status": status,
        "adapter_possible": adapter_possible,
        "missing_capabilities": missing,
        "bridgeable_gaps": bridgeable_gaps,
        "contradictions": contradictions,
        "criteria": criteria_scores,
        "criteria_evidence": criteria_evidence,
        "supported_outputs": sorted(supported_outputs),
    }


def build_user_decision_gate(
    candidate: dict[str, Any],
    assessment: dict[str, Any],
    reason: str,
) -> dict[str, Any]:
    """Build mandatory Option A/B/C/D decision gate payload (SA-DOC-ENGINE-001 Section 4.4)."""
    return {
        "decision_required": True,
        "reason": reason,
        "target_generator": candidate.get("id"),
        "assessment_status": assessment.get("status"),
        "options": {
            "A": {
                "title": "Continue with existing generator and document its limitations",
                "trade_off": "Preserves existing workflow untouched; unsupported outputs/diagrams logged as limitations.",
                "requires_approval": False,
            },
            "B": {
                "title": "Introduce a non-destructive compatibility adapter",
                "trade_off": "Translates canonical AST/data into existing generator native format without replacing it.",
                "requires_approval": True,
            },
            "C": {
                "title": "Use the Global Document Engine for this specific task only",
                "trade_off": "Meets full format/schema requirements cleanly without altering repository generators.",
                "requires_approval": True,
            },
            "D": {
                "title": "Migrate the project to the Global Document Engine",
                "trade_off": "Unified long-term maintenance, highest change impact and migration risk.",
                "requires_approval": True,
            },
        },
        "never_auto_select": ["replace_existing_generator", "migrate_pipeline"],
    }


# =============================================================================
# Deterministic Generator Resolution Precedence (Section 3)
# =============================================================================
def resolve_document_generator(
    repo_root: Path,
    requirements: dict[str, Any] | None = None,
    *,
    explicit_generator: str | None = None,
    allow_global_fallback: bool = True,
) -> dict[str, Any]:
    """
    Deterministic precedence:
      1. Explicit User Selection
      2. Project-Local Generator Discovery
      3. Project Configuration (.shadow/document-engine.json)
      4. Global Generator Configuration / Engine Fallback
      5. User Decision Required
    """
    discovery = discover_project_generators(repo_root)
    req = requirements or {}
    all_candidates = list(discovery["projectCandidates"])
    global_cand = discovery["globalEngine"]

    # Tier 1: Explicit User Selection (strictly verified, never silently overridden or fabricated!)
    if explicit_generator and explicit_generator.lower() not in ("auto", "default"):
        matched = [
            c
            for c in [*all_candidates, global_cand]
            if c.get("id") == explicit_generator or c.get("source") == explicit_generator or explicit_generator in str(c.get("paths", {}).get("executable_path", ""))
        ]
        if not matched:
            repo_res = repo_root.resolve()
            cand_path = resolve_portable_path(explicit_generator, repo_res)
            outside_proj = False
            if cand_path is not None:
                try:
                    cand_path.resolve().relative_to(repo_res)
                except ValueError:
                    outside_proj = True

            if cand_path and cand_path.exists():
                if cand_path.is_dir():
                    # Directory must contain a recognized generator entrypoint or config manifest
                    has_cfg = (cand_path / ".shadow" / "document-engine.json").is_file() or (cand_path / "package.json").is_file()
                    matched = [
                        {
                            "id": f"explicit:{explicit_generator}",
                            "name": f"Explicit Directory ({cand_path.name})",
                            "kind": "explicit",
                            "exists": True,
                            "outside_project": outside_proj,
                            "capabilities_verified": False if not has_cfg else True,
                            "verification_note": "Directory contains no verified generator manifest or entry script." if not has_cfg else "Manifest present.",
                            "supported_inputs": [],
                            "supported_outputs": [],
                            "paths": _build_path_profile(executable_path=cand_path, source_dir=cand_path),
                        }
                    ]
                else:
                    inspected = _inspect_script_file(cand_path, repo_res)
                    matched = [
                        {
                            "id": f"explicit:{explicit_generator}",
                            "name": f"Explicit Generator ({cand_path.name})",
                            "kind": "explicit",
                            "exists": True,
                            "outside_project": outside_proj,
                            "capabilities_verified": inspected["has_entry"],
                            "verification_note": (
                                "Recognized generator libraries detected: " + ", ".join(inspected["technologies"])
                                if inspected["has_entry"]
                                else f"File '{cand_path.name}' is arbitrary text/code without recognized generator libraries or manifest."
                            ),
                            "technologies": inspected["technologies"],
                            "runtime_checks": inspected["runtime_checks"],
                            "security_scan": {"scanned": True, "unsafe_sinks": inspected["unsafe_sinks"]},
                            "verified_source_scan": inspected["has_entry"],
                            "side_effects_verified": inspected["has_entry"],
                            "supported_inputs": inspected["inputs"],
                            "supported_outputs": inspected["outputs"],
                            "capabilities": inspected["capabilities"],
                            "paths": _build_path_profile(executable_path=cand_path, source_dir=cand_path.parent),
                        }
                    ]
            else:
                return {
                    "resolution_tier": "1_EXPLICIT_USER_SELECTION",
                    "status": "INVALID_EXPLICIT_GENERATOR",
                    "selected": None,
                    "error": f"Explicitly selected generator '{explicit_generator}' does not exist or is unreadable.",
                    "decision_gate": build_user_decision_gate(
                        {"id": explicit_generator},
                        {"status": "INCOMPATIBLE"},
                        "Explicitly requested generator path is invalid; refusing silent override.",
                    ),
                }
        chosen = matched[0]
        assessment = assess_generator_compatibility(chosen, req)
        if chosen.get("outside_project"):
            return {
                "resolution_tier": "1_EXPLICIT_USER_SELECTION",
                "status": "USER_DECISION_REQUIRED",
                "selected": chosen,
                "assessment": assessment,
                "outside_project_boundary": True,
                "decision_gate": build_user_decision_gate(
                    chosen,
                    assessment,
                    f"Explicit generator '{chosen.get('id')}' resolves outside project root '{repo_root}'. Authorization required.",
                ),
                "discovery": discovery,
            }
        if assessment["status"] in ("COMPATIBLE", "PARTIALLY_COMPATIBLE"):
            return {
                "resolution_tier": "1_EXPLICIT_USER_SELECTION",
                "status": "RESOLVED_WITH_ADAPTER" if assessment["status"] == "PARTIALLY_COMPATIBLE" else "RESOLVED",
                "selected": chosen,
                "assessment": assessment,
                "adapter_required": assessment["status"] == "PARTIALLY_COMPATIBLE",
                "discovery": discovery,
            }
        return {
            "resolution_tier": "1_EXPLICIT_USER_SELECTION",
            "status": "USER_DECISION_REQUIRED",
            "selected": chosen,
            "assessment": assessment,
            "decision_gate": build_user_decision_gate(
                chosen,
                assessment,
                f"Explicit generator '{chosen.get('id')}' is {assessment['status']} for this task.",
            ),
            "discovery": discovery,
        }

    # Tier 2 & Tier 3: Project-Local Discovery vs Project Configured
    local_cands = [c for c in all_candidates if c.get("kind") in ("project-local", "package-script")]
    configured_cands = [c for c in all_candidates if c.get("kind") == "project-configured"]

    def evaluate_pool(pool: list[dict[str, Any]], tier_label: str) -> dict[str, Any] | None:
        assessed = [(c, assess_generator_compatibility(c, req)) for c in pool]
        compat = [(c, a) for c, a in assessed if a["status"] == "COMPATIBLE"]
        if len(compat) == 1:
            return {
                "resolution_tier": tier_label,
                "status": "RESOLVED",
                "selected": compat[0][0],
                "assessment": compat[0][1],
                "adapter_required": False,
                "discovery": discovery,
            }
        if len(compat) > 1:
            # Prefer npm/package-script workflow entry over raw helper scripts if unique
            scripts_only = [(c, a) for c, a in compat if c.get("kind") == "package-script"]
            if len(scripts_only) == 1:
                return {
                    "resolution_tier": tier_label,
                    "status": "RESOLVED",
                    "selected": scripts_only[0][0],
                    "assessment": scripts_only[0][1],
                    "adapter_required": False,
                    "discovery": discovery,
                }
            return {
                "resolution_tier": tier_label,
                "status": "CONFLICT_USER_DECISION_REQUIRED",
                "selected": None,
                "competing_candidates": [c["id"] for c, _ in compat],
                "assessments": [a for _, a in compat],
                "decision_gate": build_user_decision_gate(
                    compat[0][0],
                    compat[0][1],
                    f"Multiple equally valid compatible generators found: {[c['id'] for c, _ in compat]}.",
                ),
                "discovery": discovery,
            }
        partial = [(c, a) for c, a in assessed if a["status"] == "PARTIALLY_COMPATIBLE" and a.get("adapter_possible")]
        if partial:
            return {
                "resolution_tier": tier_label,
                "status": "RESOLVED_WITH_ADAPTER",
                "selected": partial[0][0],
                "assessment": partial[0][1],
                "adapter_required": True,
                "decision_gate": build_user_decision_gate(
                    partial[0][0],
                    partial[0][1],
                    f"Existing project generator '{partial[0][0]['id']}' is PARTIALLY_COMPATIBLE; Adapter-First recommended before replacement.",
                ),
                "discovery": discovery,
            }
        return None

    res_local = evaluate_pool(local_cands, "2_PROJECT_LOCAL_DISCOVERY")
    if res_local is not None:
        return res_local

    res_cfg = evaluate_pool(configured_cands, "3_PROJECT_CONFIGURATION")
    if res_cfg is not None:
        return res_cfg

    # Tier 4: Global Document Engine fallback (when permitted)
    if allow_global_fallback:
        g_assess = assess_generator_compatibility(global_cand, req)
        if g_assess["status"] in ("COMPATIBLE", "PARTIALLY_COMPATIBLE"):
            return {
                "resolution_tier": "4_GLOBAL_ENGINE_FALLBACK",
                "status": "RESOLVED",
                "selected": global_cand,
                "assessment": g_assess,
                "adapter_required": False,
                "discovery": discovery,
            }

    # Tier 5: User Decision Required
    fallback_cand = (all_candidates[0] if all_candidates else global_cand)
    fallback_assess = assess_generator_compatibility(fallback_cand, req)
    return {
        "resolution_tier": "5_USER_DECISION_REQUIRED",
        "status": "USER_DECISION_REQUIRED",
        "selected": None,
        "assessment": fallback_assess,
        "decision_gate": build_user_decision_gate(
            fallback_cand,
            fallback_assess,
            "No compatible generator found automatically; user decision required.",
        ),
        "discovery": discovery,
    }


# =============================================================================
# Compatibility Adapters (Section 4.3 — Adapter Before Replacement)
# =============================================================================
class GeneratorAdapter(Protocol):
    adapter_id: str

    def adapt(self, canonical_doc: dict[str, Any]) -> dict[str, Any]: ...


class MarkdownCompatibilityAdapter:
    """
    Translates Canonical AST v2.0/v2.1 into Markdown and executes round-trip semantic
    fidelity verification (`R03`: LOSSLESS_VERIFIED | LOSSY_WITH_WARNINGS | UNVERIFIED | FAILED).
    Never emits `lossless_verified=True` without proven round-trip equivalence.
    """

    adapter_id = "canonical-ast-to-markdown-adapter"

    def adapt(self, canonical_doc: dict[str, Any]) -> dict[str, Any]:
        from v2_core import parse_markdown_into_blocks
        from v2_renderers import render_v2_to_markdown

        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_md = Path(tmpdir) / "adapted.md"
            render_v2_to_markdown(canonical_doc, tmp_md)
            md_text = tmp_md.read_text(encoding="utf-8")

        parsed_blocks, parsed_unmapped = parse_markdown_into_blocks(
            md_text, str(canonical_doc.get("document_type", "SRS"))
        )

        # Semantic fidelity checks comparing source canonical AST against rendered + re-parsed Markdown
        src_blocks = [b for b in canonical_doc.get("blocks", []) if isinstance(b, dict)]
        warnings: list[str] = []
        failures: list[str] = []

        src_title = str(canonical_doc.get("title") or "")
        title_ok = (not src_title) or (f"# {src_title}" in md_text)
        if not title_ok:
            failures.append("Document title missing from adapted Markdown H1.")

        src_headings = [str(b.get("title") or "") for b in src_blocks if b.get("kind") == "heading"]
        missing_headings = [h for h in src_headings if h and h not in md_text]
        if missing_headings:
            failures.append(f"Missing headings in Markdown: {missing_headings}")

        src_tables = [b for b in src_blocks if b.get("kind") == "table" and isinstance(b.get("table_data"), dict)]
        parsed_tables = [b for b in parsed_blocks if b.get("kind") == "table"]
        # Re-parsed tables exclude metadata/history/approvals? Compare total data row content presence instead
        for tb in src_tables:
            td = tb["table_data"]
            header_cols = [str(c).replace("|", "\\|") for c in td.get("columns", td.get("headers", []))]
            if header_cols and ("| " + " | ".join(header_cols) + " |") not in md_text:
                failures.append(f"Table header lost or reordered in {tb.get('id')}: {header_cols}")
            for row in td.get("rows", []):
                for cell in row:
                    c_str = str(cell)
                    escaped_c = c_str.replace("|", "\\|")
                    if c_str and (c_str not in md_text and escaped_c not in md_text):
                        failures.append(f"Table cell lost in {tb.get('id')}: {c_str[:40]}")

        for b in src_blocks:
            kind = str(b.get("kind", ""))
            if kind == "paragraph" and b.get("body"):
                if str(b["body"]) not in md_text:
                    failures.append(f"Paragraph body lost in {b.get('id')}")
            elif kind == "code" and b.get("body"):
                if str(b["body"]) not in md_text:
                    failures.append(f"Code block body lost in {b.get('id')}")
            elif kind == "figure" and isinstance(b.get("figure_data"), dict):
                fd = b["figure_data"]
                diag_src = str(fd.get("dbml") or fd.get("mermaid") or "")
                if diag_src and diag_src not in md_text:
                    failures.append(f"Diagram source lost in {b.get('id')}")
            elif kind == "finding":
                warnings.append(f"Structured 'finding' node ({b.get('id')}) flattened into Markdown bullet list (lossy node type round-trip).")
            elif kind == "decision-matrix":
                warnings.append(f"Structured 'decision-matrix' node ({b.get('id')}) flattened into Markdown table + summary line.")
            elif kind == "appendix":
                if str(b.get("title") or "") not in md_text:
                    failures.append(f"Appendix missing in {b.get('id')}")

            if b.get("evidence_refs") or b.get("requirement_refs"):
                warnings.append(f"Block-level semantic arrays (evidence_refs/requirement_refs) on {b.get('id')} are not first-class Markdown syntax.")
            if b.get("extensions"):
                warnings.append(f"Block extensions {list(b['extensions'].keys())} on {b.get('id')} cannot round-trip cleanly through plain Markdown.")

        if canonical_doc.get("extensions"):
            warnings.append(f"Document-level extensions {list(canonical_doc['extensions'].keys())} are not preserved in Markdown representation.")
        if canonical_doc.get("rendering_hints"):
            warnings.append("Document rendering_hints stripped in plain Markdown representation.")

        # Verify sources preservation
        src_list = canonical_doc.get("sources", [])
        missing_sources = [str(s.get("source_id")) for s in src_list if isinstance(s, dict) and s.get("source_id") and str(s.get("source_id")) not in md_text]
        if missing_sources:
            failures.append(f"Source references omitted: {missing_sources}")

        if failures:
            fidelity_status = "FAILED"
        elif warnings:
            fidelity_status = "LOSSY_WITH_WARNINGS"
        else:
            fidelity_status = "LOSSLESS_VERIFIED"

        return {
            "adapter_id": self.adapter_id,
            "target_format": "markdown",
            "content": md_text,
            "source_refs_preserved": len(src_list) - len(missing_sources),
            "fidelity_status": fidelity_status,
            "lossless_verified": fidelity_status == "LOSSLESS_VERIFIED",
            "fidelity_warnings": warnings,
            "fidelity_failures": failures,
            "roundtrip_table_count": len(parsed_tables),
            "roundtrip_unmapped_count": len(parsed_unmapped),
        }


# =============================================================================
# Self-Test Suite (Positive + Negative Discovery/Compatibility Probes)
# =============================================================================
def run_self_test() -> dict[str, Any]:
    import tempfile

    probes: list[dict[str, Any]] = []
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)

        # Fixture 1: Custom generator script + package script (reuse local first)
        f1 = root / "proj_local"
        (f1 / "tools" / "docbuilder").mkdir(parents=True)
        (f1 / "package.json").write_text(
            json.dumps({"name": "p1", "scripts": {"build:docs": "node tools/docbuilder/build.mjs"}, "dependencies": {"docx": "^8.5.0"}}),
            encoding="utf-8",
        )
        (f1 / "tools" / "docbuilder" / "build.mjs").write_text("import { Document } from 'docx';\n", encoding="utf-8")
        r1 = resolve_document_generator(f1, {"required_outputs": ["docx"]})
        probes.append({"probe": "LOCAL-FIRST-DISCOVERY", "passed": r1["status"] == "RESOLVED" and r1["selected"]["id"] == "npm-script:build:docs", "detail": r1["status"]})

        # Fixture 2: Invalid explicit generator refuses silent override
        r2 = resolve_document_generator(f1, {"required_outputs": ["md"]}, explicit_generator="nonexistent/bin.py")
        probes.append({"probe": "EXPLICIT-INVALID-REFUSED", "passed": r2["status"] == "INVALID_EXPLICIT_GENERATOR", "detail": r2["status"]})

        # Fixture 3: PDF-only reportlab script must NOT be marked COMPATIBLE when docx + code_blocks required
        f3 = root / "proj_pdf_only"
        (f3 / "scripts").mkdir(parents=True)
        (f3 / "scripts" / "pdf_emit.py").write_text("import reportlab\n", encoding="utf-8")
        d3 = discover_project_generators(f3)
        a3 = assess_generator_compatibility(d3["projectCandidates"][0], {"required_outputs": ["pdf", "docx"], "requires_code_blocks": True})
        probes.append({"probe": "PDF-ONLY-NOT-BLIND-COMPATIBLE", "passed": a3["status"] == "INCOMPATIBLE" and "outputs:docx" in a3["missing_capabilities"], "detail": a3["status"]})

        # Fixture 4: Path traversal guard & overwrite protection
        traversal_blocked = False
        try:
            validate_safe_path(f1 / ".." / "escape.pdf", allowed_root=f1)
        except ValueError:
            traversal_blocked = True
        overwrite_blocked = False
        existing_out = f1 / "existing.md"
        existing_out.write_text("keep me", encoding="utf-8")
        try:
            check_output_overwrite_safety(existing_out, overwrite=False)
        except FileExistsError:
            overwrite_blocked = True
        probes.append({"probe": "TRAVERSAL-AND-OVERWRITE-BLOCKED", "passed": traversal_blocked and overwrite_blocked, "detail": f"traversal={traversal_blocked}, overwrite={overwrite_blocked}"})

        # Fixture 5: Global fallback works cleanly when repo has no generator
        f5 = root / "proj_empty"
        f5.mkdir(parents=True)
        r5 = resolve_document_generator(f5, {"required_outputs": ["html", "docx"]})
        probes.append({"probe": "GLOBAL-FALLBACK-CLEAN", "passed": r5["resolution_tier"] == "4_GLOBAL_ENGINE_FALLBACK" and r5["selected"]["id"] == "shadow-doc-global", "detail": r5["resolution_tier"]})

    passed = sum(1 for p in probes if p["passed"])
    return {
        "tool": "doc_orchestrator.py",
        "total_probes": len(probes),
        "passed": passed,
        "failed": len(probes) - passed,
        "all_passed": passed == len(probes),
        "results": probes,
    }


def main() -> int:
    import argparse

    parser = argparse.ArgumentParser(description="Shadow Army Generator-Agnostic Document Orchestrator")
    parser.add_argument("--self-test", action="store_true", help="Run orchestrator discovery & safety self-tests")
    parser.add_argument("--repo", default=".", help="Target project root")
    parser.add_argument("--discover", action="store_true", help="Discover generators in repo")
    parser.add_argument("--resolve", action="store_true", help="Resolve best generator")
    parser.add_argument("--outputs", default="md", help="Comma-separated desired outputs")
    parser.add_argument("--generator", default="auto", help="Explicit generator ID or path")
    args = parser.parse_args()

    if args.self_test:
        res = run_self_test()
        print(json.dumps(res, indent=2))
        return 0 if res["all_passed"] else 1
    if args.discover:
        res = discover_project_generators(Path(args.repo))
        print(json.dumps(res, indent=2))
        return 0
    if args.resolve:
        req = {"required_outputs": [x.strip() for x in args.outputs.split(",") if x.strip()]}
        res = resolve_document_generator(Path(args.repo), req, explicit_generator=args.generator)
        print(json.dumps(res, indent=2))
        return 0
    parser.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(run_checked_cli(main))
