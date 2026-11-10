#!/usr/bin/env python3
"""Shadow Doc v2.0 Core Engine: Canonical AST, Importers, Validation, Traceability, Impact & Governance."""

from __future__ import annotations

import copy
import hashlib
import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

SKILL_ROOT = Path(__file__).resolve().parent.parent
TEMPLATES_DIR = SKILL_ROOT / "templates"
SCHEMA_PATH = SKILL_ROOT / "schemas" / "canonical-document.schema.json"

TEMPLATE_MAP: dict[str, tuple[str, str]] = {
    "SDLC_PLAN": ("01_SDLC_PLAN.md", "Software Development Lifecycle Plan"),
    "BRD_PRD": ("02_BRD_PRD.md", "Business and Product Requirements"),
    "PRD": ("02_BRD_PRD.md", "Business and Product Requirements"),
    "BRD": ("02_BRD_PRD.md", "Business and Product Requirements"),
    "SRS": ("03_SRS.md", "Software Requirements Specification"),
    "SDD": ("04_SDD.md", "Software Design Document"),
    "ADR": ("05_ADR.md", "Architecture Decision Record"),
    "JUKNIS": ("06_JUKNIS.md", "Technical Implementation and Operations Guide"),
    "CONFIG": ("07_CONFIG.md", "Configuration Register"),
    "RTM": ("08_RTM.md", "Requirements Traceability Matrix"),
    "TEST_PLAN": ("09_TEST_PLAN.md", "Software Test Plan and Execution Report"),
    "UAT": ("10_UAT.md", "User Acceptance Test Plan and Report"),
    "BUG_LOG": ("11_BUG_LOG.md", "Defect and Bug Register"),
    "CHANGE_REQUEST": ("12_CHANGE_REQUEST.md", "Change Request and Impact Assessment"),
    "CR": ("12_CHANGE_REQUEST.md", "Change Request and Impact Assessment"),
    "CHANGELOG": ("13_CHANGELOG.md", "Change Log and Release Notes"),
    "INCIDENT": ("14_INCIDENT.md", "Production Incident Report and RCA"),
    "CAPA": ("15_CAPA.md", "Corrective Action and Improvement Recommendations"),
    "MANUAL": ("16_MANUAL.md", "User, Administrator and Operator Manual"),
    "HANDOVER": ("17_HANDOVER.md", "Handover Package / BAST Annex"),
    "BAST": ("17_HANDOVER.md", "Handover Package / BAST Annex"),
    "SECURITY_RISK": ("18_SECURITY_RISK.md", "Security Assessment and Risk Register"),
    "MAINTENANCE": ("19_MAINTENANCE.md", "Maintenance and Service Level Report"),
    "DEPLOYMENT": ("20_DEPLOYMENT.md", "Deployment and Production Verification Record"),
}

# Normative Industry Standards per Document Type (Research Source Policy)
NORMATIVE_STANDARDS_MAP: dict[str, dict[str, Any]] = {
    "SDLC_PLAN": {
        "source_id": "STD-ISO-12207",
        "source_type": "STANDARD",
        "standard_or_venue": "ISO/IEC/IEEE 12207:2017",
        "version_or_year": "2017",
        "reference": "ISO/IEC/IEEE 12207:2017 Systems and software engineering — Software life cycle processes",
        "doi_or_url": "https://www.iso.org/standard/63712.html",
        "peer_reviewed": True,
    },
    "BRD_PRD": {
        "source_id": "STD-ISO-29148",
        "source_type": "STANDARD",
        "standard_or_venue": "ISO/IEC/IEEE 29148:2018",
        "version_or_year": "2018",
        "reference": "ISO/IEC/IEEE 29148:2018 Systems and software engineering — Life cycle processes — Requirements engineering",
        "doi_or_url": "https://www.iso.org/standard/72089.html",
        "peer_reviewed": True,
    },
    "SRS": {
        "source_id": "STD-ISO-29148",
        "source_type": "STANDARD",
        "standard_or_venue": "ISO/IEC/IEEE 29148:2018",
        "version_or_year": "2018",
        "reference": "ISO/IEC/IEEE 29148:2018 Systems and software engineering — Life cycle processes — Requirements engineering",
        "doi_or_url": "https://www.iso.org/standard/72089.html",
        "peer_reviewed": True,
    },
    "SDD": {
        "source_id": "STD-ISO-42010",
        "source_type": "STANDARD",
        "standard_or_venue": "ISO/IEC/IEEE 42010:2022",
        "version_or_year": "2022",
        "reference": "ISO/IEC/IEEE 42010:2022 Software, systems and enterprise — Architecture description",
        "doi_or_url": "https://www.iso.org/standard/74393.html",
        "peer_reviewed": True,
    },
    "ADR": {
        "source_id": "STD-ISO-42010",
        "source_type": "STANDARD",
        "standard_or_venue": "ISO/IEC/IEEE 42010:2022",
        "version_or_year": "2022",
        "reference": "ISO/IEC/IEEE 42010:2022 Software, systems and enterprise — Architecture description",
        "doi_or_url": "https://www.iso.org/standard/74393.html",
        "peer_reviewed": True,
    },
    "RTM": {
        "source_id": "STD-ISO-29119",
        "source_type": "STANDARD",
        "standard_or_venue": "ISO/IEC/IEEE 29119:2021",
        "version_or_year": "2021",
        "reference": "ISO/IEC/IEEE 29119 Software and systems engineering — Software testing",
        "doi_or_url": "https://www.iso.org/standard/81291.html",
        "peer_reviewed": True,
    },
    "TEST_PLAN": {
        "source_id": "STD-ISO-29119",
        "source_type": "STANDARD",
        "standard_or_venue": "ISO/IEC/IEEE 29119-3:2021",
        "version_or_year": "2021",
        "reference": "ISO/IEC/IEEE 29119-3:2021 Software testing — Part 3: Test documentation",
        "doi_or_url": "https://www.iso.org/standard/79429.html",
        "peer_reviewed": True,
    },
    "UAT": {
        "source_id": "STD-ISO-29119",
        "source_type": "STANDARD",
        "standard_or_venue": "ISO/IEC/IEEE 29119-3:2021",
        "version_or_year": "2021",
        "reference": "ISO/IEC/IEEE 29119-3:2021 Software testing — Part 3: Test documentation & UAT",
        "doi_or_url": "https://www.iso.org/standard/79429.html",
        "peer_reviewed": True,
    },
    "SECURITY_RISK": {
        "source_id": "STD-NIST-SSDF-OWASP-ASVS",
        "source_type": "STANDARD",
        "standard_or_venue": "NIST SP 800-218 (SSDF v1.1) & OWASP ASVS 5.0.0",
        "version_or_year": "2022 / 5.0.0",
        "reference": "NIST SP 800-218 Secure Software Development Framework & OWASP Application Security Verification Standard 5.0",
        "doi_or_url": "https://csrc.nist.gov/pubs/sp/800/218/final",
        "peer_reviewed": True,
    },
    "INCIDENT": {
        "source_id": "STD-NIST-800-61",
        "source_type": "STANDARD",
        "standard_or_venue": "NIST SP 800-61 Rev. 2",
        "version_or_year": "2012",
        "reference": "NIST SP 800-61 Computer Security Incident Handling Guide",
        "doi_or_url": "https://csrc.nist.gov/pubs/sp/800/61/r2/final",
        "peer_reviewed": True,
    },
    "MANUAL": {
        "source_id": "STD-ISO-26514",
        "source_type": "STANDARD",
        "standard_or_venue": "ISO/IEC/IEEE 26514:2022",
        "version_or_year": "2022",
        "reference": "ISO/IEC/IEEE 26514:2022 Systems and software engineering — Design and development of information for users",
        "doi_or_url": "https://www.iso.org/standard/77451.html",
        "peer_reviewed": True,
    },
    "MAINTENANCE": {
        "source_id": "STD-ISO-14764",
        "source_type": "STANDARD",
        "standard_or_venue": "ISO/IEC/IEEE 14764:2022",
        "version_or_year": "2022",
        "reference": "ISO/IEC/IEEE 14764:2022 Software Engineering — Software Life Cycle Processes — Maintenance",
        "doi_or_url": "https://www.iso.org/standard/80710.html",
        "peer_reviewed": True,
    },
}

SECRET_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    ("AWS Access Key", re.compile(r"\bAKIA[0-9A-Z]{16}\b")),
    ("GitHub Token", re.compile(r"\bgh[pousr]_[A-Za-z0-9_]{20,}\b")),
    ("Private Key Block", re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----")),
    ("JWT Token", re.compile(r"\beyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\b")),
    (
        "Secret Assignment",
        re.compile(
            r"(?i)\b(password|passwd|secret|api_key|apikey|access_token|private_key|client_secret)\s*[:=]\s*['\"]?([A-Za-z0-9_!@#$%^&*()-+=]{6,})['\"]?"
        ),
    ),
    (
        "Database DSN Password",
        re.compile(r"(?i)\b(?:postgres|postgresql|mysql|mongodb|redis)://[^:\s]+:([^@\s]{4,})@"),
    ),
]

SYNC_TRIGGERS: dict[str, list[str]] = {
    "FR": ["SRS", "SDD", "RTM", "TEST_PLAN", "UAT"],
    "NFR": ["SRS", "SDD", "TEST_PLAN", "JUKNIS", "CONFIG"],
    "ADR": ["ADR", "SDD", "JUKNIS", "CONFIG"],
    "CR": ["CHANGE_REQUEST", "BRD_PRD", "SRS", "SDD", "RTM", "UAT"],
    "BUG": ["BUG_LOG", "TEST_PLAN", "UAT", "CHANGELOG", "CAPA"],
    "INC": ["INCIDENT", "CAPA", "MAINTENANCE", "JUKNIS"],
    "TC": ["TEST_PLAN", "RTM", "UAT"],
}


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def compute_semantic_hash(doc: dict[str, Any]) -> str:
    """Compute deterministic SHA-256 over semantic content, excluding volatile timestamps/hashes (AT-09)."""
    cleaned = copy.deepcopy(doc)
    for volatile_key in ("updated_at", "created_at", "hash", "semantic_hash"):
        cleaned.pop(volatile_key, None)
    if "history" in cleaned and isinstance(cleaned["history"], list):
        for h in cleaned["history"]:
            if isinstance(h, dict):
                h.pop("changed_at", None)
                h.pop("before_hash", None)
                h.pop("after_hash", None)
    canonical_bytes = json.dumps(cleaned, sort_keys=True, ensure_ascii=False).encode("utf-8")
    return hashlib.sha256(canonical_bytes).hexdigest()


def compute_full_hash(doc: dict[str, Any]) -> str:
    cleaned = copy.deepcopy(doc)
    cleaned.pop("hash", None)
    canonical_bytes = json.dumps(cleaned, sort_keys=True, ensure_ascii=False).encode("utf-8")
    return hashlib.sha256(canonical_bytes).hexdigest()


def compute_file_sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def atomic_write_json(target_path: Path, data: dict[str, Any], simulate_fail: bool = False) -> None:
    """Write JSON atomically via temp file + backup restoration on failure (DOC-NFR-007 / AT-14)."""
    target_path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = target_path.with_suffix(target_path.suffix + ".tmp")
    bak_path = target_path.with_suffix(target_path.suffix + ".bak")

    had_existing = target_path.exists()
    if had_existing:
        bak_path.write_bytes(target_path.read_bytes())

    try:
        payload = json.dumps(data, indent=2, ensure_ascii=False) + "\n"
        tmp_path.write_text(payload, encoding="utf-8")
        if simulate_fail:
            raise OSError("Simulated mid-write disk/renderer failure (AT-14)")
        os.replace(tmp_path, target_path)
    except Exception:
        if tmp_path.exists():
            tmp_path.unlink(missing_ok=True)
        if had_existing and bak_path.exists():
            os.replace(bak_path, target_path)
        raise
    finally:
        if bak_path.exists():
            bak_path.unlink(missing_ok=True)


def scan_and_redact_secrets(doc: dict[str, Any], redact_in_place: bool = False) -> list[dict[str, str]]:
    """Scan all text/table/code fields in AST for leaked secrets (DOC-FR-016 / AT-06)."""
    findings: list[dict[str, str]] = []

    def inspect_str(val: str, loc: str) -> str:
        out = val
        for label, pattern in SECRET_PATTERNS:
            for m in pattern.finditer(val):
                matched = m.group(0)
                if "[ISI" in matched or "REDACTED" in matched or "example" in matched.lower():
                    continue
                findings.append(
                    {
                        "severity": "CRITICAL",
                        "code": "SECRET_LEAK_DETECTED",
                        "location": loc,
                        "pattern": label,
                        "remediation": "Remove raw secret/credential from document and store in secret manager.",
                    }
                )
                if redact_in_place:
                    if label == "Secret Assignment" and m.lastindex and m.lastindex >= 2:
                        out = out.replace(m.group(2), "[REDACTED_SECRET]")
                    else:
                        out = pattern.sub("[REDACTED_SECRET]", out)
        return out

    for idx, b in enumerate(doc.get("blocks", [])):
        bid = b.get("id", f"BLK-{idx}")
        if isinstance(b.get("body"), str):
            b["body"] = inspect_str(b["body"], f"block:{bid}.body")
        if isinstance(b.get("title"), str):
            b["title"] = inspect_str(b["title"], f"block:{bid}.title")
        t_data = b.get("table_data")
        if isinstance(t_data, dict):
            new_rows = []
            for r_idx, row in enumerate(t_data.get("rows", [])):
                new_rows.append(
                    [inspect_str(str(cell), f"block:{bid}.table.row[{r_idx}]") for cell in row]
                )
            if redact_in_place:
                t_data["rows"] = new_rows

    return findings


def validate_schema_v2(doc: dict[str, Any]) -> list[dict[str, str]]:
    """Deterministic schema validator against canonical-document.schema.json (DOC-FR-004)."""
    issues: list[dict[str, str]] = []
    required_top = [
        "schema_version",
        "document_id",
        "project_id",
        "document_type",
        "title",
        "revision",
        "status",
        "language",
        "blocks",
        "sources",
        "history",
    ]
    for req in required_top:
        if req not in doc:
            issues.append(
                {
                    "severity": "CRITICAL",
                    "code": "SCHEMA_MISSING_REQUIRED",
                    "location": f"root.{req}",
                    "message": f"Required field '{req}' is missing.",
                }
            )
    if doc.get("schema_version") != "2.0":
        issues.append(
            {
                "severity": "CRITICAL",
                "code": "SCHEMA_VERSION_MISMATCH",
                "location": "root.schema_version",
                "message": f"Expected schema_version '2.0', got '{doc.get('schema_version')}'.",
            }
        )
    valid_statuses = {
        "DRAFT",
        "IN_REVIEW",
        "CHANGES_REQUESTED",
        "APPROVED",
        "RELEASED",
        "SUPERSEDED",
        "ARCHIVED",
    }
    if doc.get("status") not in valid_statuses:
        issues.append(
            {
                "severity": "CRITICAL",
                "code": "SCHEMA_INVALID_STATUS",
                "location": "root.status",
                "message": f"Invalid status '{doc.get('status')}'.",
            }
        )
    if doc.get("language") not in {"id-ID", "en-US"}:
        issues.append(
            {
                "severity": "CRITICAL",
                "code": "SCHEMA_INVALID_LANGUAGE",
                "location": "root.language",
                "message": f"Invalid language '{doc.get('language')}'. Expected 'id-ID' or 'en-US'.",
            }
        )
    valid_kinds = {"heading", "paragraph", "table", "figure", "list", "code", "opaque"}
    for idx, b in enumerate(doc.get("blocks", [])):
        if not isinstance(b, dict) or not b.get("id") or b.get("kind") not in valid_kinds:
            issues.append(
                {
                    "severity": "CRITICAL",
                    "code": "SCHEMA_INVALID_BLOCK",
                    "location": f"blocks[{idx}]",
                    "message": "Block must be an object with non-empty 'id' and valid 'kind'.",
                }
            )
    return issues


def parse_markdown_into_blocks(md_text: str, doc_type: str = "SRS") -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Parse Markdown text into v2 canonical blocks + unmapped_blocks (DOC-FR-005)."""
    lines = md_text.splitlines()
    blocks: list[dict[str, Any]] = []
    unmapped: list[dict[str, Any]] = []

    sec_counter = 0
    blk_counter = 0
    i = 0
    n = len(lines)

    skip_h2 = {"riwayat revisi", "daftar distribusi dan persetujuan", "revision history"}
    in_skipped_meta_section = False

    while i < n:
        raw_line = lines[i]
        stripped = raw_line.strip()

        if not stripped or stripped.startswith("# ") or stripped.startswith("> "):
            i += 1
            continue

        # Detect unrecognized custom HTML / XML tags -> preserve in unmapped_blocks
        if stripped.startswith("<") and not stripped.startswith("<!--"):
            blk_counter += 1
            unmapped.append(
                {
                    "id": f"UNMAPPED-{blk_counter:03d}",
                    "line": i + 1,
                    "raw": raw_line,
                    "reason": "Raw HTML/custom tag preserved in unmapped_blocks for human review",
                }
            )
            blocks.append(
                {
                    "id": f"OPQ-{blk_counter:03d}",
                    "kind": "opaque",
                    "title": "Unmapped Construct",
                    "body": raw_line,
                    "source_refs": [],
                    "trace_ids": [],
                }
            )
            i += 1
            continue

        h_match = re.match(r"^(#{2,4})\s+(.*)$", stripped)
        if h_match:
            hashes, h_title = h_match.group(1), h_match.group(2).strip()
            if h_title.lower() in skip_h2:
                in_skipped_meta_section = True
                i += 1
                continue
            in_skipped_meta_section = False
            sec_counter += 1
            num_match = re.match(r"^(\d+(?:\.\d+)*)\.?\s+(.*)$", h_title)
            if num_match:
                sec_id = f"SEC-{num_match.group(1).replace('.', '-')}"
            else:
                slug = re.sub(r"[^A-Za-z0-9]+", "_", h_title).strip("_").upper()[:20]
                sec_id = f"SEC-{sec_counter}-{slug}"
            blocks.append(
                {
                    "id": sec_id,
                    "kind": "heading",
                    "level": len(hashes),
                    "title": h_title,
                    "body": None,
                    "source_refs": [],
                    "trace_ids": [],
                }
            )
            i += 1
            continue

        if in_skipped_meta_section:
            i += 1
            continue

        # Skip top metadata table before first ## heading
        if sec_counter == 0 and stripped.startswith("|"):
            i += 1
            continue

        # Code or Mermaid block
        if stripped.startswith("```"):
            lang = stripped[3:].strip()
            code_lines: list[str] = []
            i += 1
            while i < n and not lines[i].strip().startswith("```"):
                code_lines.append(lines[i])
                i += 1
            i += 1
            blk_counter += 1
            if lang.lower() == "mermaid":
                blocks.append(
                    {
                        "id": f"FIG-{blk_counter:03d}",
                        "kind": "figure",
                        "title": f"Diagram {blk_counter}",
                        "body": "\n".join(code_lines),
                        "figure_data": {
                            "path": None,
                            "caption": f"Mermaid Diagram {blk_counter}",
                            "alt_text": f"Architecture/Flow Diagram {blk_counter}",
                            "mermaid": "\n".join(code_lines),
                        },
                        "source_refs": [],
                        "trace_ids": [],
                    }
                )
            else:
                blocks.append(
                    {
                        "id": f"CODE-{blk_counter:03d}",
                        "kind": "code",
                        "title": f"Code Block ({lang or 'text'})",
                        "body": "\n".join(code_lines),
                        "code_language": lang or "text",
                        "source_refs": [],
                        "trace_ids": [],
                    }
                )
            continue

        # Markdown table
        if stripped.startswith("|"):
            t_rows: list[list[str]] = []
            while i < n and lines[i].strip().startswith("|"):
                cells = [c.strip() for c in lines[i].strip().strip("|").split("|")]
                t_rows.append(cells)
                i += 1
            if len(t_rows) >= 2:
                headers = t_rows[0]
                data_rows = [
                    r
                    for idx, r in enumerate(t_rows[1:], start=1)
                    if idx != 1 or not all(re.match(r"^:?-{2,}:?$", c) for c in r)
                ]
                blk_counter += 1
                extracted_traces: list[str] = []
                for r in data_rows:
                    for cell in r:
                        for tid in re.findall(
                            r"\b(?:FR|NFR|TC|UAT|BUG|INC|CR|ADR|SDD|RISK)-\d{3}\b", cell
                        ):
                            if tid not in extracted_traces:
                                extracted_traces.append(tid)
                blocks.append(
                    {
                        "id": f"TBL-{blk_counter:03d}",
                        "kind": "table",
                        "title": f"Register Table {blk_counter}",
                        "body": None,
                        "table_data": {
                            "caption": f"Tabel {blk_counter} — {doc_type}",
                            "columns": headers,
                            "rows": data_rows,
                        },
                        "source_refs": [],
                        "trace_ids": extracted_traces,
                    }
                )
            continue

        # Bullet / numbered list
        if re.match(r"^([-*]|\d+\.)\s+", stripped):
            items: list[str] = []
            while i < n and re.match(r"^([-*]|\d+\.)\s+", lines[i].strip()):
                item_text = re.sub(r"^([-*]|\d+\.)\s+", "", lines[i].strip())
                items.append(item_text)
                i += 1
            blk_counter += 1
            blocks.append(
                {
                    "id": f"LST-{blk_counter:03d}",
                    "kind": "list",
                    "title": None,
                    "body": "\n".join(items),
                    "list_items": items,
                    "source_refs": [],
                    "trace_ids": [],
                }
            )
            continue

        # Standard paragraph
        para_lines: list[str] = []
        while (
            i < n
            and lines[i].strip()
            and not lines[i].strip().startswith(("#", "|", "```", "<", "- ", "* "))
        ):
            para_lines.append(lines[i].strip())
            i += 1
        para_text = " ".join(para_lines).strip()
        if para_text:
            blk_counter += 1
            id_match = re.match(r"^\[?((?:FR|NFR|TC|UAT|BUG|INC|CR|ADR)-\d{3})\]?:\s*(.*)$", para_text)
            if id_match:
                bid = id_match.group(1)
                para_body = id_match.group(2)
            else:
                bid = f"PAR-{blk_counter:03d}"
                para_body = para_text
            traces = re.findall(r"\b(?:FR|NFR|TC|UAT|BUG|INC|CR|ADR|SDD)-\d{3}\b", para_body)
            blocks.append(
                {
                    "id": bid,
                    "kind": "paragraph",
                    "title": None,
                    "body": para_body,
                    "source_refs": [],
                    "trace_ids": list(dict.fromkeys(traces)),
                }
            )

    return blocks, unmapped


def create_document_from_template(
    doc_type: str,
    project_id: str,
    doc_id: str | None = None,
    language: str = "id-ID",
    classification: str = "INTERNAL",
    style_profile: str = "corporate",
    owner: str | None = None,
    audience: str | None = None,
) -> dict[str, Any]:
    """Create a canonical v2.0 document AST from any of the 20 baseline templates (DOC-FR-002/003)."""
    norm_type = doc_type.upper().strip()
    if norm_type not in TEMPLATE_MAP:
        raise ValueError(
            f"Unsupported document type '{doc_type}'. Valid types: {', '.join(sorted(TEMPLATE_MAP.keys()))}"
        )
    tpl_filename, default_title = TEMPLATE_MAP[norm_type]
    tpl_path = TEMPLATES_DIR / tpl_filename
    md_text = tpl_path.read_text(encoding="utf-8")
    blocks, unmapped = parse_markdown_into_blocks(md_text, norm_type)

    resolved_doc_id = doc_id or f"{project_id.upper()}-{norm_type}-001"
    doc: dict[str, Any] = {
        "schema_version": "2.0",
        "document_id": resolved_doc_id,
        "project_id": project_id.upper(),
        "document_type": norm_type,
        "title": default_title,
        "revision": "0.1-DRAFT",
        "app_version": None,
        "status": "DRAFT",
        "language": language if language in ("id-ID", "en-US") else "id-ID",
        "classification": classification,
        "style_profile": style_profile if style_profile in ("corporate", "institutional") else "corporate",
        "audience": audience,
        "owner": owner,
        "reviewers": [],
        "approvers": [],
        "created_at": utc_now_iso(),
        "updated_at": utc_now_iso(),
        "effective_date": None,
        "template_version": "2.0.0",
        "change_reason": "Initial template creation",
        "supersedes": None,
        "forbidden_terms": [],
        "sources": [
            {
                "source_id": "TPL-BASELINE",
                "source_type": "PROJECT_ARTIFACT",
                "reference": f"templates/{tpl_filename}",
                "verified_at": None,
                "checksum": compute_file_sha256(tpl_path),
                "peer_reviewed": True,
            },
            *(
                [copy.deepcopy(NORMATIVE_STANDARDS_MAP[norm_type])]
                if norm_type in NORMATIVE_STANDARDS_MAP
                else []
            ),
        ],
        "blocks": blocks,
        "history": [
            {
                "revision": "0.1-DRAFT",
                "reason": "Template initialization (placeholders require verified project sources)",
                "changed_by": owner,
                "changed_at": utc_now_iso(),
                "approval_ref": None,
            }
        ],
        "signoff_record": [
            {
                "role": "Reviewer",
                "identity": None,
                "decision": "PENDING",
                "timestamp": None,
                "evidence_ref": None,
            },
            {
                "role": "Approver",
                "identity": None,
                "decision": "PENDING",
                "timestamp": None,
                "evidence_ref": None,
            },
        ],
        "review_comments": [],
        "unmapped_blocks": unmapped,
    }
    doc["semantic_hash"] = compute_semantic_hash(doc)
    doc["hash"] = compute_full_hash(doc)
    return doc


def import_existing_file_to_v2(
    input_path: Path,
    project_id: str = "PROJ",
    doc_type: str = "SRS",
    doc_id: str | None = None,
) -> dict[str, Any]:
    """Import .md, .docx, .pdf (reference), or legacy v1 .json into Canonical v2.0 AST (DOC-FR-005/006/028)."""
    suffix = input_path.suffix.lower()
    resolved_id = doc_id or f"{project_id.upper()}-{doc_type.upper()}-001"

    if suffix == ".md":
        md_text = input_path.read_text(encoding="utf-8")
        h1_match = re.search(r"^#\s+(.+)$", md_text, flags=re.MULTILINE)
        title = h1_match.group(1).strip() if h1_match else input_path.stem
        blocks, unmapped = parse_markdown_into_blocks(md_text, doc_type)
        doc = create_document_from_template("SRS" if doc_type not in TEMPLATE_MAP else doc_type, project_id, resolved_id)
        doc["title"] = title
        doc["blocks"] = blocks
        doc["unmapped_blocks"] = unmapped
        doc["sources"] = [
            {
                "source_id": "IMPORTED-MD",
                "reference": str(input_path.name),
                "verified_at": utc_now_iso(),
                "checksum": compute_file_sha256(input_path),
            }
        ]
        doc["semantic_hash"] = compute_semantic_hash(doc)
        doc["hash"] = compute_full_hash(doc)
        return doc

    if suffix == ".docx":
        import docx as pydocx

        d = pydocx.Document(str(input_path))
        blocks = []
        unmapped = []
        idx = 0
        for p in d.paragraphs:
            txt = p.text.strip()
            if not txt:
                continue
            idx += 1
            style_name = (p.style.name if p.style else "").lower()
            if "heading" in style_name:
                lvl = 2
                for n_char in ("1", "2", "3", "4"):
                    if n_char in style_name:
                        lvl = int(n_char)
                        break
                blocks.append(
                    {
                        "id": f"SEC-{idx:03d}",
                        "kind": "heading",
                        "level": lvl,
                        "title": txt,
                        "body": None,
                        "source_refs": ["IMPORTED-DOCX"],
                        "trace_ids": [],
                    }
                )
            else:
                blocks.append(
                    {
                        "id": f"PAR-{idx:03d}",
                        "kind": "paragraph",
                        "title": None,
                        "body": txt,
                        "source_refs": ["IMPORTED-DOCX"],
                        "trace_ids": [],
                    }
                )
        for t_idx, tbl in enumerate(d.tables, start=1):
            rows_data = [[cell.text.strip() for cell in row.cells] for row in tbl.rows]
            if rows_data:
                blocks.append(
                    {
                        "id": f"TBL-{t_idx:03d}",
                        "kind": "table",
                        "title": f"Imported Table {t_idx}",
                        "body": None,
                        "table_data": {
                            "caption": f"Imported DOCX Table {t_idx}",
                            "columns": rows_data[0],
                            "rows": rows_data[1:],
                        },
                        "source_refs": ["IMPORTED-DOCX"],
                        "trace_ids": [],
                    }
                )
        doc = create_document_from_template("SRS" if doc_type not in TEMPLATE_MAP else doc_type, project_id, resolved_id)
        doc["title"] = input_path.stem
        doc["blocks"] = blocks
        doc["unmapped_blocks"] = unmapped
        doc["sources"] = [
            {
                "source_id": "IMPORTED-DOCX",
                "reference": input_path.name,
                "verified_at": utc_now_iso(),
                "checksum": compute_file_sha256(input_path),
            }
        ]
        doc["semantic_hash"] = compute_semantic_hash(doc)
        doc["hash"] = compute_full_hash(doc)
        return doc

    if suffix == ".pdf":
        # DOC-FR-006: Ingest PDF as reference; never assume lossless parsing
        doc = create_document_from_template("SRS" if doc_type not in TEMPLATE_MAP else doc_type, project_id, resolved_id)
        doc["title"] = f"Reference Ingestion: {input_path.name}"
        doc["blocks"] = [
            {
                "id": "SEC-PDF-REF",
                "kind": "heading",
                "level": 2,
                "title": "Ingested PDF Reference (Non-Lossless Source)",
                "body": None,
                "source_refs": ["IMPORTED-PDF"],
                "trace_ids": [],
            },
            {
                "id": "OPQ-PDF-001",
                "kind": "opaque",
                "title": input_path.name,
                "body": f"PDF ingested as immutable reference ({input_path.stat().st_size} bytes). Edit via canonical AST revisions; lossless PDF layout parsing is not assumed (DOC-FR-006).",
                "source_refs": ["IMPORTED-PDF"],
                "trace_ids": [],
            },
        ]
        doc["unmapped_blocks"] = [
            {
                "id": "UNMAPPED-PDF-BINARY",
                "reason": "PDF binary layout retained as external reference artifact per DOC-FR-006.",
                "file": input_path.name,
            }
        ]
        doc["sources"] = [
            {
                "source_id": "IMPORTED-PDF",
                "reference": input_path.name,
                "verified_at": utc_now_iso(),
                "checksum": compute_file_sha256(input_path),
            }
        ]
        doc["semantic_hash"] = compute_semantic_hash(doc)
        doc["hash"] = compute_full_hash(doc)
        return doc

    if suffix == ".json":
        raw_json = json.loads(input_path.read_text(encoding="utf-8"))
        if raw_json.get("schema_version") == "2.0":
            return raw_json
        bak_path = input_path.with_suffix(".v1.bak.json")
        if not bak_path.exists():
            bak_path.write_bytes(input_path.read_bytes())
        return migrate_v1_dict_to_v2(raw_json, project_id=project_id, source_name=input_path.name)

    raise ValueError(f"Unsupported import format: {suffix}")


def migrate_v1_dict_to_v2(
    v1_doc: dict[str, Any], project_id: str = "LEGACY", source_name: str = "legacy_v1.json"
) -> dict[str, Any]:
    """Migrate a v1.0 Shadow-Doc JSON ('jenis', 'judul', 'bagian') into v2.0 Canonical AST (DOC-FR-028 / AT-12)."""
    jenis = str(v1_doc.get("jenis", "SRS")).upper()
    judul = str(v1_doc.get("judul", "Migrated Document"))
    mapped_type = jenis if jenis in TEMPLATE_MAP else "SRS"
    blocks: list[dict[str, Any]] = []
    sec_idx = 0
    blk_idx = 0

    def convert_v1_blok_list(blok_list: list[dict[str, Any]]) -> None:
        nonlocal blk_idx
        for b in blok_list:
            blk_idx += 1
            s_refs = [str(b["sumber"])] if b.get("sumber") else ["LEGACY-V1"]
            if "paragraf" in b:
                blocks.append(
                    {
                        "id": f"PAR-{blk_idx:03d}",
                        "kind": "paragraph",
                        "title": None,
                        "body": str(b["paragraf"]),
                        "source_refs": s_refs,
                        "trace_ids": [],
                    }
                )
            elif "tabel" in b:
                t = b["tabel"]
                cols = [
                    c.get("judul", "-") if isinstance(c, dict) else str(c)
                    for c in t.get("kolom", [])
                ]
                blocks.append(
                    {
                        "id": f"TBL-{blk_idx:03d}",
                        "kind": "table",
                        "title": t.get("keterangan", f"Tabel {blk_idx}"),
                        "body": None,
                        "table_data": {
                            "caption": t.get("keterangan", f"Tabel {blk_idx}"),
                            "columns": cols,
                            "rows": t.get("baris", []),
                        },
                        "source_refs": s_refs,
                        "trace_ids": [],
                    }
                )
            elif "daftar" in b:
                items = [
                    f"{it.get('judul')}: {it.get('uraian')}" if isinstance(it, dict) else str(it)
                    for it in b["daftar"]
                ]
                blocks.append(
                    {
                        "id": f"LST-{blk_idx:03d}",
                        "kind": "list",
                        "title": None,
                        "body": "\n".join(items),
                        "list_items": items,
                        "source_refs": s_refs,
                        "trace_ids": [],
                    }
                )
            elif "diagram" in b:
                diag = b["diagram"]
                blocks.append(
                    {
                        "id": f"FIG-{blk_idx:03d}",
                        "kind": "figure",
                        "title": diag.get("keterangan", f"Diagram {blk_idx}"),
                        "body": diag.get("mermaid", ""),
                        "figure_data": {
                            "path": None,
                            "caption": diag.get("keterangan", f"Diagram {blk_idx}"),
                            "alt_text": diag.get("keterangan", f"Diagram {blk_idx}"),
                            "mermaid": diag.get("mermaid", ""),
                        },
                        "source_refs": s_refs,
                        "trace_ids": [],
                    }
                )
            elif "kode" in b:
                kd = b["kode"]
                blocks.append(
                    {
                        "id": f"CODE-{blk_idx:03d}",
                        "kind": "code",
                        "title": None,
                        "body": kd.get("isi", ""),
                        "code_language": kd.get("bahasa", "text"),
                        "source_refs": s_refs,
                        "trace_ids": [],
                    }
                )

    for bg in v1_doc.get("bagian", []):
        sec_idx += 1
        blocks.append(
            {
                "id": f"SEC-{sec_idx}",
                "kind": "heading",
                "level": 2,
                "title": bg.get("judul", f"Bagian {sec_idx}"),
                "body": None,
                "source_refs": ["LEGACY-V1"],
                "trace_ids": [],
            }
        )
        convert_v1_blok_list(bg.get("blok", []))
        for sub_i, sub in enumerate(bg.get("subbagian", []), start=1):
            blocks.append(
                {
                    "id": f"SEC-{sec_idx}-{sub_i}",
                    "kind": "heading",
                    "level": 3,
                    "title": sub.get("judul", f"Subbagian {sec_idx}.{sub_i}"),
                    "body": None,
                    "source_refs": ["LEGACY-V1"],
                    "trace_ids": [],
                }
            )
            convert_v1_blok_list(sub.get("blok", []))

    forbidden = v1_doc.get("metadata", {}).get("istilah_terlarang", [])
    doc: dict[str, Any] = {
        "schema_version": "2.0",
        "document_id": f"{project_id.upper()}-{mapped_type}-001",
        "project_id": project_id.upper(),
        "document_type": mapped_type,
        "title": judul,
        "revision": "1.0-MIGRATED",
        "app_version": None,
        "status": "DRAFT",
        "language": "id-ID",
        "classification": "INTERNAL",
        "style_profile": "institutional",
        "owner": None,
        "reviewers": [],
        "approvers": [],
        "created_at": utc_now_iso(),
        "updated_at": utc_now_iso(),
        "effective_date": None,
        "template_version": "2.0.0",
        "change_reason": f"Migrated from legacy v1 document '{source_name}'",
        "supersedes": "v1.0-legacy",
        "forbidden_terms": forbidden if isinstance(forbidden, list) else [],
        "sources": [
            {
                "source_id": "LEGACY-V1",
                "reference": source_name,
                "verified_at": utc_now_iso(),
                "checksum": None,
            }
        ],
        "blocks": blocks,
        "history": [
            {
                "revision": "1.0-MIGRATED",
                "reason": f"Automated migration from v1 AST ({source_name})",
                "changed_by": "shadow-doc-migrator",
                "changed_at": utc_now_iso(),
                "approval_ref": None,
            }
        ],
        "signoff_record": [],
        "review_comments": [],
        "unmapped_blocks": [],
        "legacy_v1_bagian": copy.deepcopy(v1_doc.get("bagian", [])),
    }
    doc["semantic_hash"] = compute_semantic_hash(doc)
    doc["hash"] = compute_full_hash(doc)
    return doc


def selective_update_v2(
    doc: dict[str, Any],
    scope_id: str,
    new_body: str | None = None,
    new_title: str | None = None,
    new_trace_ids: list[str] | None = None,
    new_source_refs: list[str] | None = None,
    change_ref: str = "CR-MANUAL",
    changed_by: str | None = None,
    expected_hash: str | None = None,
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Update ONLY the targeted block ID, preserving all other blocks and protecting APPROVED docs (AT-03, AT-04, AT-07)."""
    current_hash = doc.get("hash") or compute_full_hash(doc)
    if expected_hash and expected_hash != current_hash:
        raise RuntimeError(
            f"CONCURRENCY_CONFLICT (AT-07): Expected base hash '{expected_hash}', but document has hash '{current_hash}'. Resolve concurrent edits before saving."
        )

    working = copy.deepcopy(doc)
    was_approved = working.get("status") in ("APPROVED", "RELEASED")
    prev_rev = str(working.get("revision", "0.1"))

    # AT-04: Approved document cannot be mutated in-place; fork new DRAFT revision
    if was_approved:
        base_num_match = re.match(r"^(\d+)\.(\d+)", prev_rev)
        if base_num_match:
            major, minor = int(base_num_match.group(1)), int(base_num_match.group(2)) + 1
            next_rev = f"{major}.{minor}-DRAFT"
        else:
            next_rev = f"{prev_rev}-NEXT-DRAFT"
        working["supersedes"] = prev_rev
        working["revision"] = next_rev
        working["status"] = "DRAFT"
        # Reset signoff decisions for the new draft revision
        for s in working.get("signoff_record", []):
            s["decision"] = "PENDING"
            s["timestamp"] = None
    else:
        working["revision"] = prev_rev

    target_block = None
    for b in working.get("blocks", []):
        if b.get("id") == scope_id:
            target_block = b
            break

    before_snapshot = copy.deepcopy(target_block) if target_block else None
    if target_block is None:
        target_block = {
            "id": scope_id,
            "kind": "paragraph",
            "title": new_title,
            "body": new_body or "[ISI DARI SUMBER PROYEK]",
            "source_refs": new_source_refs or [change_ref],
            "trace_ids": new_trace_ids or [],
            "last_reviewed_at": utc_now_iso(),
        }
        working.setdefault("blocks", []).append(target_block)
    else:
        if new_body is not None:
            target_block["body"] = new_body
        if new_title is not None:
            target_block["title"] = new_title
        if new_trace_ids is not None:
            target_block["trace_ids"] = new_trace_ids
        if new_source_refs is not None:
            target_block["source_refs"] = new_source_refs
        target_block["last_reviewed_at"] = utc_now_iso()

    working["updated_at"] = utc_now_iso()
    working["change_reason"] = f"Selective update on {scope_id} via {change_ref}"
    after_semantic = compute_semantic_hash(working)
    working["semantic_hash"] = after_semantic
    after_full = compute_full_hash(working)
    working["hash"] = after_full

    working.setdefault("history", []).append(
        {
            "revision": working["revision"],
            "reason": f"Updated block '{scope_id}' ({change_ref})"
            + (f" — forked from approved revision {prev_rev}" if was_approved else ""),
            "changed_by": changed_by,
            "changed_at": utc_now_iso(),
            "approval_ref": change_ref,
            "before_hash": current_hash,
            "after_hash": after_full,
        }
    )

    diff_report = {
        "document_id": working["document_id"],
        "previous_revision": prev_rev,
        "new_revision": working["revision"],
        "forked_from_approved": was_approved,
        "updated_block_id": scope_id,
        "before_block": before_snapshot,
        "after_block": copy.deepcopy(target_block),
        "untouched_block_count": len(working["blocks"]) - 1,
        "before_hash": current_hash,
        "after_hash": after_full,
    }
    return working, diff_report


def diff_documents_v2(doc_a: dict[str, Any], doc_b: dict[str, Any]) -> dict[str, Any]:
    """Compute block-by-block diff between two revisions of a document (DOC-FR-007 / DOC-FR-029)."""
    map_a = {b["id"]: b for b in doc_a.get("blocks", [])}
    map_b = {b["id"]: b for b in doc_b.get("blocks", [])}

    added = [bid for bid in map_b if bid not in map_a]
    removed = [bid for bid in map_a if bid not in map_b]
    modified = []
    unchanged = []

    for bid in map_a:
        if bid in map_b:
            ba = {k: v for k, v in map_a[bid].items() if k != "last_reviewed_at"}
            bb = {k: v for k, v in map_b[bid].items() if k != "last_reviewed_at"}
            if ba != bb:
                modified.append({"id": bid, "before": map_a[bid], "after": map_b[bid]})
            else:
                unchanged.append(bid)

    return {
        "document_id": doc_b.get("document_id"),
        "from_revision": doc_a.get("revision"),
        "to_revision": doc_b.get("revision"),
        "added_blocks": added,
        "removed_blocks": removed,
        "modified_blocks": modified,
        "unchanged_block_count": len(unchanged),
    }


def transition_approval_status(
    doc: dict[str, Any],
    target_status: str,
    actor: str,
    role: str = "Approver",
    evidence_ref: str | None = None,
) -> dict[str, Any]:
    """Controlled lifecycle transition with Separation of Duties & BAST evidence enforcement (DOC-FR-011 / AT-11)."""
    working = copy.deepcopy(doc)
    owner = working.get("owner")
    if target_status in ("APPROVED", "RELEASED"):
        if not actor or not actor.strip():
            raise ValueError("APPROVAL_BLOCKED: Approver identity is required (cannot auto-signoff).")
        if owner and owner.strip().lower() == actor.strip().lower():
            raise ValueError(
                f"SEPARATION_OF_DUTIES_VIOLATION (DOC-FR-011): Document owner '{owner}' cannot approve their own controlled artifact."
            )
        if not evidence_ref or not evidence_ref.strip():
            raise ValueError(
                "EVIDENCE_REQUIRED (AT-11): Status APPROVED/RELEASED requires an explicit evidence_ref."
            )
        if working.get("document_type") in ("HANDOVER", "BAST") and not evidence_ref:
            raise ValueError("BAST_UNSIGNED_GUARD (AT-11): BAST/Handover cannot be approved without signed evidence.")

    working["status"] = target_status
    if target_status == "APPROVED" and working["revision"].endswith("-DRAFT"):
        working["revision"] = working["revision"].replace("-DRAFT", "")
        working["effective_date"] = utc_now_iso()

    working.setdefault("signoff_record", []).append(
        {
            "role": role,
            "identity": actor,
            "decision": "APPROVED" if target_status in ("APPROVED", "RELEASED") else target_status,
            "timestamp": utc_now_iso(),
            "evidence_ref": evidence_ref,
        }
    )
    working.setdefault("history", []).append(
        {
            "revision": working["revision"],
            "reason": f"Lifecycle transition to {target_status}",
            "changed_by": actor,
            "changed_at": utc_now_iso(),
            "approval_ref": evidence_ref,
        }
    )
    working["semantic_hash"] = compute_semantic_hash(working)
    working["hash"] = compute_full_hash(working)
    return working


def analyze_traceability_and_impact(
    docs: list[dict[str, Any]], changed_id: str | None = None
) -> dict[str, Any]:
    """Build bidirectional traceability graph, coverage metrics, orphan detection, and impact analysis (DOC-FR-008/009, DOC-NFR-012)."""
    defined_items: dict[str, dict[str, str]] = {}
    forward_links: dict[str, set[str]] = {}
    reverse_links: dict[str, set[str]] = {}

    def register_link(src: str, dst: str) -> None:
        if src == dst:
            return
        forward_links.setdefault(src, set()).add(dst)
        reverse_links.setdefault(dst, set()).add(src)

    for d in docs:
        doc_id = d.get("document_id", "UNKNOWN")
        doc_type = d.get("document_type", "UNKNOWN")
        for b in d.get("blocks", []):
            bid = b.get("id", "")
            if re.match(r"^(?:FR|NFR|TC|UAT|BUG|INC|CR|ADR|SDD|RISK)-\d{3,}$", bid):
                defined_items[bid] = {
                    "document_id": doc_id,
                    "document_type": doc_type,
                    "status": str(b.get("status") or "UNSPECIFIED"),
                }
            for tid in b.get("trace_ids", []):
                register_link(bid, tid)
            t_data = b.get("table_data")
            if isinstance(t_data, dict):
                for row in t_data.get("rows", []):
                    row_ids = []
                    for cell in row:
                        for found in re.findall(
                            r"\b(?:FR|NFR|TC|UAT|BUG|INC|CR|ADR|SDD|RISK)-\d{3,}\b", str(cell)
                        ):
                            row_ids.append(found)
                            if found not in defined_items:
                                defined_items[found] = {
                                    "document_id": doc_id,
                                    "document_type": doc_type,
                                    "status": row[-1] if row else "UNSPECIFIED",
                                }
                    for idx_a in range(len(row_ids)):
                        for idx_b in range(idx_a + 1, len(row_ids)):
                            register_link(row_ids[idx_a], row_ids[idx_b])

    reqs = [k for k in defined_items if k.startswith(("FR-", "NFR-"))]
    reqs_with_design = 0
    reqs_with_test = 0
    reqs_with_uat = 0
    orphan_reqs: list[str] = []

    for r in reqs:
        neighbors = forward_links.get(r, set()) | reverse_links.get(r, set())
        has_design = any(n.startswith(("SDD-", "ADR-", "SEC-")) for n in neighbors)
        has_test = any(n.startswith("TC-") for n in neighbors)
        has_uat = any(n.startswith("UAT-") for n in neighbors)
        if has_design:
            reqs_with_design += 1
        if has_test:
            reqs_with_test += 1
        if has_uat:
            reqs_with_uat += 1
        if not neighbors:
            orphan_reqs.append(r)

    total_reqs = len(reqs)
    coverage = {
        "total_requirements": total_reqs,
        "requirement_to_design_ratio": round(reqs_with_design / total_reqs, 4) if total_reqs else 1.0,
        "requirement_to_test_ratio": round(reqs_with_test / total_reqs, 4) if total_reqs else 1.0,
        "requirement_to_uat_ratio": round(reqs_with_uat / total_reqs, 4) if total_reqs else 1.0,
        "orphan_requirements": orphan_reqs,
    }

    impact_report: dict[str, Any] = {}
    if changed_id:
        direct = sorted(forward_links.get(changed_id, set()) | reverse_links.get(changed_id, set()))
        transitive: set[str] = set(direct)
        for d_id in direct:
            transitive |= forward_links.get(d_id, set()) | reverse_links.get(d_id, set())
        transitive.discard(changed_id)

        prefix = changed_id.split("-")[0].upper()
        recommended_doc_types = SYNC_TRIGGERS.get(prefix, ["SRS", "SDD", "RTM", "TEST_PLAN", "UAT"])
        affected_documents = sorted(
            {
                defined_items[item_id]["document_id"]
                for item_id in transitive
                if item_id in defined_items
            }
        )
        impact_report = {
            "changed_id": changed_id,
            "direct_linked_ids": direct,
            "all_impacted_ids": sorted(transitive),
            "affected_documents_in_workspace": affected_documents,
            "recommended_doc_types_to_review": recommended_doc_types,
        }

    return {
        "total_tracked_ids": len(defined_items),
        "total_trace_links": sum(len(v) for v in forward_links.values()),
        "coverage": coverage,
        "impact": impact_report,
    }


def validate_document_v2(
    doc: dict[str, Any],
    workspace_docs: list[dict[str, Any]] | None = None,
    strict: bool = False,
) -> dict[str, Any]:
    """Fail-closed quality gate & semantic validator (DOC-FR-015, DOC-FR-016, DOC-FR-020, AT-05, AT-06, AT-10, AT-11)."""
    issues: list[dict[str, str]] = []
    issues.extend(validate_schema_v2(doc))
    issues.extend(scan_and_redact_secrets(doc, redact_in_place=False))

    # Check unique block IDs
    seen_ids: set[str] = set()
    for b in doc.get("blocks", []):
        bid = b.get("id", "")
        if bid in seen_ids:
            issues.append(
                {
                    "severity": "CRITICAL",
                    "code": "DUPLICATE_BLOCK_ID",
                    "location": f"block:{bid}",
                    "message": f"Duplicate block ID '{bid}' found.",
                }
            )
        seen_ids.add(bid)

    # Check forbidden terms / cross-project bleed (AT-10)
    forbidden = [t.lower() for t in doc.get("forbidden_terms", []) if isinstance(t, str) and t.strip()]
    proj_id = str(doc.get("project_id", "")).upper()
    if workspace_docs:
        for other in workspace_docs:
            other_proj = str(other.get("project_id", "")).upper()
            if other_proj and other_proj != proj_id:
                forbidden.append(f"project:{other_proj.lower()}")

    raw_dump_lower = json.dumps(doc.get("blocks", []), ensure_ascii=False).lower()
    for term in forbidden:
        if term in raw_dump_lower:
            issues.append(
                {
                    "severity": "CRITICAL",
                    "code": "CROSS_PROJECT_OR_FORBIDDEN_TERM_BLEED",
                    "location": "blocks",
                    "message": f"Forbidden or cross-project identifier '{term}' detected in document belonging to '{proj_id}'.",
                }
            )

    # Check unverified status claims without sources (DOC-FR-012 / DOC-FR-020 / Section 12)
    doc_sources = {s.get("source_id") for s in doc.get("sources", []) if isinstance(s, dict)}

    # Research Source Policy Validation: verify preprints vs normative standards
    has_normative_or_project_source = False
    has_preprint_source = False
    for s_idx, src in enumerate(doc.get("sources", [])):
        if not isinstance(src, dict):
            continue
        s_type = str(src.get("source_type", "PROJECT_ARTIFACT")).upper()
        ref_str = str(src.get("reference", "")).lower()
        url_str = str(src.get("doi_or_url", "")).lower()
        is_arxiv = "arxiv" in ref_str or "arxiv.org" in url_str or s_type == "PREPRINT"
        if is_arxiv:
            has_preprint_source = True
            if src.get("peer_reviewed") is True and "10.48550/arxiv" in (url_str + ref_str):
                issues.append(
                    {
                        "severity": "CRITICAL",
                        "code": "PREPRINT_FALSE_PEER_REVIEW_CLAIM",
                        "location": f"root.sources[{s_idx}]",
                        "message": f"Source '{src.get('source_id')}' is an arXiv preprint and cannot be marked peer_reviewed=true without a verified journal/conference DOI.",
                    }
                )
        elif s_type in ("STANDARD", "OFFICIAL_DOCS", "PEER_REVIEWED", "REGULATION", "PROJECT_ARTIFACT"):
            has_normative_or_project_source = True

    if has_preprint_source and not has_normative_or_project_source:
        issues.append(
            {
                "severity": "CRITICAL" if strict else "WARNING",
                "code": "PREPRINT_WITHOUT_NORMATIVE_STANDARD",
                "location": "root.sources",
                "message": "Document cites a preprint (e.g., arXiv) without any normative industry standard (ISO/IEC/IEEE, NIST, OWASP) or official documentation source.",
            }
        )
    if doc.get("status") in ("APPROVED", "RELEASED") or strict:
        if "[isi" in raw_dump_lower or "[tbd]" in raw_dump_lower or "unverified" in raw_dump_lower:
            issues.append(
                {
                    "severity": "CRITICAL" if (doc.get("status") in ("APPROVED", "RELEASED") or strict) else "WARNING",
                    "code": "UNRESOLVED_PLACEHOLDER_OR_TBD",
                    "location": "blocks",
                    "message": "Document contains unresolved '[ISI ...]', '[TBD]', or 'UNVERIFIED' placeholders and cannot be marked APPROVED/RELEASED under strict gate (AT-09).",
                }
            )
    if doc.get("status") in ("APPROVED", "RELEASED"):
        approved_signoffs = [
            s
            for s in doc.get("signoff_record", [])
            if s.get("decision") == "APPROVED" and s.get("identity") and s.get("evidence_ref")
        ]
        if not approved_signoffs:
            issues.append(
                {
                    "severity": "CRITICAL",
                    "code": "UNVERIFIED_APPROVAL_STATE",
                    "location": "root.signoff_record",
                    "message": f"Document status is '{doc.get('status')}' but signoff_record lacks an APPROVED entry with identity and evidence_ref.",
                }
            )

    # AT-05: Mismatched BUG status vs test/UAT PASS
    open_bugs: set[str] = set()
    all_docs = workspace_docs if workspace_docs else [doc]
    for d in all_docs:
        for b in d.get("blocks", []):
            bid = b.get("id", "")
            b_status = str(b.get("status") or "").upper()
            if bid.startswith("BUG-") and b_status in ("OPEN", "IN_PROGRESS", "REOPENED"):
                open_bugs.add(bid)
            t_data = b.get("table_data")
            if isinstance(t_data, dict):
                for row in t_data.get("rows", []):
                    row_str = " ".join(str(c) for c in row)
                    for bug_id in re.findall(r"\bBUG-\d{3,}\b", row_str):
                        if any(st in row_str.upper() for st in ("OPEN", "FAIL", "BLOCKED")):
                            open_bugs.add(bug_id)

    for b in doc.get("blocks", []):
        bid = b.get("id", "")
        b_status = str(b.get("status") or "").upper()
        s_refs = b.get("source_refs", [])
        if b_status in ("PASS", "APPROVED", "DEPLOYED", "CLOSED") and not s_refs:
            issues.append(
                {
                    "severity": "CRITICAL",
                    "code": "CLAIM_WITHOUT_EVIDENCE",
                    "location": f"block:{bid}",
                    "message": f"Block '{bid}' claims status '{b_status}' without any source_refs/evidence.",
                }
            )
        for unknown_ref in s_refs:
            if doc_sources and unknown_ref not in doc_sources and not unknown_ref.startswith("CR-"):
                issues.append(
                    {
                        "severity": "WARNING" if not strict else "CRITICAL",
                        "code": "UNREGISTERED_SOURCE_REF",
                        "location": f"block:{bid}",
                        "message": f"Block '{bid}' cites source_ref '{unknown_ref}' not listed in root.sources.",
                    }
                )
        if b_status == "PASS":
            linked_open = [t for t in b.get("trace_ids", []) if t in open_bugs]
            if linked_open:
                issues.append(
                    {
                        "severity": "CRITICAL",
                        "code": "MISMATCHED_BUG_AND_TEST_STATUS",
                        "location": f"block:{bid}",
                        "message": f"Test/Requirement '{bid}' is marked PASS while linked defect(s) {linked_open} are still OPEN (AT-05).",
                    }
                )

    critical_count = sum(1 for i in issues if i["severity"] == "CRITICAL")
    warning_count = sum(1 for i in issues if i["severity"] != "CRITICAL")
    return {
        "document_id": doc.get("document_id"),
        "revision": doc.get("revision"),
        "valid": critical_count == 0 and (warning_count == 0 if strict else True),
        "critical_count": critical_count,
        "warning_count": warning_count,
        "issues": issues,
    }
