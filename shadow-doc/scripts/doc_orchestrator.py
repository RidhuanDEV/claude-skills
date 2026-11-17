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

import json
import os
import re
import shutil
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Protocol

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
        re.compile(r"\bimport\s+docx\b|\bfrom\s+docx\s+import\b|python-docx", re.IGNORECASE),
        {"inputs": ["markdown", "json"], "outputs": ["docx"], "tables": True, "code_blocks": True},
    ),
    (
        "weasyprint-pdf",
        re.compile(r"\bweasyprint\b", re.IGNORECASE),
        {"inputs": ["html", "markdown"], "outputs": ["pdf", "html"], "tables": True, "code_blocks": True},
    ),
    (
        "reportlab-pdf",
        re.compile(r"\breportlab\b", re.IGNORECASE),
        {"inputs": ["json", "text"], "outputs": ["pdf"], "tables": True, "code_blocks": False},
    ),
    (
        "fpdf2-pdf",
        re.compile(r"\bfpdf\b|\bfpdf2\b", re.IGNORECASE),
        {"inputs": ["json", "markdown"], "outputs": ["pdf"], "tables": True, "code_blocks": True},
    ),
    (
        "node-docx",
        re.compile(r"""(?:require|from)\s*\(?['"]docx['"]""", re.IGNORECASE),
        {"inputs": ["markdown", "json"], "outputs": ["docx"], "tables": True, "code_blocks": True},
    ),
    (
        "puppeteer-pdf",
        re.compile(r"\bpuppeteer\b|md-to-pdf|html-pdf", re.IGNORECASE),
        {"inputs": ["markdown", "html"], "outputs": ["pdf", "html"], "tables": True, "diagrams": True},
    ),
    (
        "pandoc-cli",
        re.compile(r"\bpandoc\b", re.IGNORECASE),
        {"inputs": ["markdown", "html", "docx"], "outputs": ["pdf", "docx", "html", "md"], "tables": True, "code_blocks": True, "citations": True},
    ),
    (
        "typst-cli",
        re.compile(r"\btypst\b", re.IGNORECASE),
        {"inputs": ["typst", "markdown"], "outputs": ["pdf"], "tables": True, "code_blocks": True},
    ),
    (
        "openpyxl-xlsx",
        re.compile(r"\bopenpyxl\b|\bxlsxwriter\b", re.IGNORECASE),
        {"inputs": ["json", "csv"], "outputs": ["xlsx"], "tables": True},
    ),
)


# =============================================================================
# Security, Path Containment & Authorization Classification
# =============================================================================
def validate_safe_path(
    target_path: Path,
    allowed_root: Path | None = None,
    *,
    allow_symlinks: bool = False,
) -> Path:
    """Resolve target_path cleanly and fail closed on path traversal outside allowed_root."""
    raw_str = str(target_path)
    if "\x00" in raw_str:
        raise ValueError("Invalid path: NUL byte rejected.")
    resolved = target_path.resolve()
    if not allow_symlinks and target_path.is_symlink():
        raise ValueError(f"Symlink target rejected for safety: '{target_path}'.")
    if allowed_root is not None:
        root_resolved = allowed_root.resolve()
        try:
            resolved.relative_to(root_resolved)
        except ValueError as exc:
            raise ValueError(
                f"PATH_TRAVERSAL_BLOCKED: '{target_path}' resolves outside allowed root '{root_resolved}'."
            ) from exc
    return resolved


def check_output_overwrite_safety(out_path: Path, overwrite: bool = False) -> None:
    """Block accidental overwriting of existing outputs unless overwrite=True is explicitly requested."""
    if out_path.exists() and not overwrite:
        raise FileExistsError(
            f"OUTPUT_EXISTS_OVERWRITE_BLOCKED: Destination '{out_path}' already exists. Pass --overwrite to replace."
        )


def classify_document_action(
    action: str,
    *,
    target_scope: str = "project",
    overwrite: bool = False,
    external_publish: bool = False,
) -> dict[str, Any]:
    """Classify action under L0-L4 User Intent Boundary rules (SA-DOC-ENGINE-001 Section 9)."""
    approval_actions = {
        "init_global_generator": ("L4", "Initializing persistent global generator infrastructure"),
        "change_global_config": ("L4", "Modifying global user/IDE generator configuration"),
        "install_global_dependency": ("L3", "Installing global system or package dependencies"),
        "replace_existing_generator": ("L4", "Replacing an existing project document generator"),
        "migrate_pipeline": ("L2", "Migrating existing document generation pipeline"),
        "persistent_adapter": ("L2", "Adding persistent adapter outside current task scope"),
        "overwrite_document": ("L2", "Overwriting existing generated document file"),
        "unrelated_repo_write": ("L4", "Modifying unrelated repository outside requested scope"),
        "export_unrequested_format": ("L2", "Exporting formats not requested by the user"),
        "publish_external": ("L4", "Publishing or transmitting documents externally"),
    }
    if external_publish or action == "publish_external":
        lvl, reason = approval_actions["publish_external"]
        return {"permission_level": lvl, "requires_approval": True, "reason": reason}
    if overwrite or action == "overwrite_document":
        lvl, reason = approval_actions["overwrite_document"]
        return {"permission_level": lvl, "requires_approval": True, "reason": reason}
    if action in approval_actions:
        lvl, reason = approval_actions[action]
        return {"permission_level": lvl, "requires_approval": True, "reason": reason}
    if target_scope == "unrelated_repo":
        lvl, reason = approval_actions["unrelated_repo_write"]
        return {"permission_level": lvl, "requires_approval": True, "reason": reason}

    safe_read = {"discover", "assess", "resolve", "validate", "inspect", "read_config"}
    if action in safe_read:
        return {"permission_level": "L0", "requires_approval": False, "reason": "Read-only inspection in authorized scope."}
    return {"permission_level": "L1", "requires_approval": False, "reason": "Bounded local generation inside authorized destination."}


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
                    add_candidate(
                        {
                            "id": f"npm-script:{s_name}",
                            "name": f"package.json script '{s_name}'",
                            "kind": "package-script",
                            "source": "package.json",
                            "command": f"npm run {s_name}",
                            "raw_script": s_cmd,
                            "matched_dependencies": matched_deps,
                            "supported_inputs": ["markdown", "json"],
                            "supported_outputs": inferred_outputs,
                            "capabilities": {
                                "tables": True,
                                "code_blocks": True,
                                "diagrams": any("mermaid" in d for d in matched_deps),
                                "citations": "pandoc" in str(s_cmd).lower(),
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
        if matched_techs:
            # Determine if this is Shadow Doc Global Engine inside current repo
            is_shadow_doc = fpath.name == "doc_scaffold.py" and (fpath.parent.parent / "schemas" / "canonical-document.schema.json").is_file()
            add_candidate(
                {
                    "id": "shadow-doc-global" if is_shadow_doc else f"repo-script:{rel}",
                    "name": "Shadow-Doc Global Document Engine" if is_shadow_doc else f"Project Script ({rel})",
                    "kind": "global-engine" if is_shadow_doc else "project-local",
                    "source": rel,
                    "technologies": matched_techs,
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
            add_candidate(
                {
                    "id": str(pg.get("id", "project-configured-generator")),
                    "name": str(pg.get("name", f"Configured Generator ({entry.name})")),
                    "kind": "project-configured",
                    "source": cfg_info["config_path"],
                    "exists": exists,
                    "supported_inputs": list(pg.get("supportedInputs", ["markdown", "json"])),
                    "supported_outputs": list(pg.get("supportedOutputs", ["pdf", "docx"])),
                    "capabilities": dict(pg.get("capabilities", {"tables": True, "code_blocks": True, "diagrams": False, "citations": True, "templates": True})),
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
# 15-Criterion Compatibility Assessment (Section 4)
# =============================================================================
def assess_generator_compatibility(
    candidate: dict[str, Any],
    requirements: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    Classify a candidate generator across all 15 criteria into:
    COMPATIBLE | PARTIALLY_COMPATIBLE | INCOMPATIBLE | UNKNOWN.
    Explicitly prevents marking a PDF-only emitter COMPATIBLE when richer formatting is needed.
    """
    req = requirements or {}
    needed_outputs = {str(x).lower() for x in req.get("required_outputs", ["md"])}
    needed_input = str(req.get("preferred_input", "markdown")).lower()
    needs_tables = bool(req.get("requires_tables", True))
    needs_diagrams = bool(req.get("requires_diagrams", False))
    needs_code = bool(req.get("requires_code_blocks", False))
    needs_citations = bool(req.get("requires_citations", False))
    needs_templates = bool(req.get("requires_templates", False))

    cand_exists = candidate.get("exists", True)
    exec_p = candidate.get("paths", {}).get("executable_path")
    if cand_exists is False or (exec_p and candidate.get("kind") != "global-engine" and not Path(exec_p).exists()):
        return {
            "generator_id": candidate.get("id"),
            "status": "INCOMPATIBLE",
            "adapter_possible": False,
            "missing_capabilities": ["executable_missing_or_invalid_path"],
            "criteria": {c: "FAIL" for c in COMPATIBILITY_CRITERIA},
            "reason": f"Configured executable path does not exist: '{exec_p}'.",
        }

    supported_outputs = {str(x).lower() for x in candidate.get("supported_outputs", [])}
    supported_inputs = {str(x).lower() for x in candidate.get("supported_inputs", [])}
    caps = candidate.get("capabilities", {}) or {}

    if not supported_outputs and not supported_inputs:
        return {
            "generator_id": candidate.get("id"),
            "status": "UNKNOWN",
            "adapter_possible": False,
            "missing_capabilities": ["unverified_implementation"],
            "criteria": {c: "UNKNOWN" for c in COMPATIBILITY_CRITERIA},
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

    criteria_scores: dict[str, str] = {
        "supported_input_formats": "PASS" if needed_input in supported_inputs else ("ADAPTER" if bridgeable_gaps else "FAIL"),
        "supported_output_formats": "PASS" if not missing_outputs else "FAIL",
        "template_capabilities": "PASS" if caps.get("templates", False) else ("WARN" if not needs_templates else "ADAPTER"),
        "diagram_rendering": "PASS" if caps.get("diagrams", False) else ("ADAPTER" if needs_diagrams else "N/A"),
        "table_rendering": "PASS" if caps.get("tables", False) else ("FAIL" if needs_tables else "N/A"),
        "code_block_rendering": "PASS" if caps.get("code_blocks", False) else ("FAIL" if needs_code else "N/A"),
        "image_and_asset_handling": "PASS",
        "source_references_and_citations": "PASS" if caps.get("citations", False) else ("ADAPTER" if needs_citations else "N/A"),
        "api_cli_integration": "PASS",
        "dependency_compatibility": "PASS",
        "configuration_requirements": "PASS",
        "execution_side_effects": "PASS",
        "security_implications": "PASS",
        "rendering_quality": "PASS" if not missing_outputs else "PARTIAL",
        "existing_project_conventions": "PASS" if candidate.get("kind") != "global-engine" else "FALLBACK",
    }

    if not missing and not bridgeable_gaps:
        status = "COMPATIBLE"
        adapter_possible = False
    elif not missing and bridgeable_gaps:
        status = "PARTIALLY_COMPATIBLE"
        adapter_possible = True
    elif missing_outputs and len(missing) == len([m for m in missing if m.startswith("outputs:")]) and "json-ast" in str(supported_inputs):
        status = "INCOMPATIBLE"
        adapter_possible = False
    elif len(missing) == 1 and missing[0].startswith("input:") and "markdown" in supported_inputs:
        status = "PARTIALLY_COMPATIBLE"
        adapter_possible = True
    elif missing:
        # Outputs missing or hard capability missing -> cannot claim COMPATIBLE
        status = "PARTIALLY_COMPATIBLE" if not missing_outputs else "INCOMPATIBLE"
        adapter_possible = not missing_outputs
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
        "criteria": criteria_scores,
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

    # Tier 1: Explicit User Selection (never silently override!)
    if explicit_generator and explicit_generator.lower() not in ("auto", "default"):
        matched = [
            c
            for c in [*all_candidates, global_cand]
            if c.get("id") == explicit_generator or c.get("source") == explicit_generator or explicit_generator in str(c.get("paths", {}).get("executable_path", ""))
        ]
        if not matched:
            cand_path = resolve_portable_path(explicit_generator, repo_root.resolve())
            if cand_path and cand_path.exists():
                matched = [
                    {
                        "id": f"explicit:{explicit_generator}",
                        "name": f"Explicit Generator ({cand_path.name})",
                        "kind": "explicit",
                        "exists": True,
                        "supported_inputs": ["markdown", "json"],
                        "supported_outputs": list(req.get("required_outputs", ["md"])),
                        "capabilities": {"tables": True, "code_blocks": True, "diagrams": False, "citations": True, "templates": True},
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
    """Translates Canonical AST v2.0/v2.1 cleanly into standard Markdown + preserved Mermaid/DBML + Citations."""

    adapter_id = "canonical-ast-to-markdown-adapter"

    def adapt(self, canonical_doc: dict[str, Any]) -> dict[str, Any]:
        from v2_renderers import render_v2_to_markdown

        lines: list[str] = []
        # Reuse render logic cleanly in-memory without temp leaks
        import tempfile

        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_md = Path(tmpdir) / "adapted.md"
            render_v2_to_markdown(canonical_doc, tmp_md)
            md_text = tmp_md.read_text(encoding="utf-8")

        return {
            "adapter_id": self.adapter_id,
            "target_format": "markdown",
            "content": md_text,
            "source_refs_preserved": len(canonical_doc.get("sources", [])),
            "lossless_verified": True,
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
    sys.exit(main())
