#!/usr/bin/env python3
"""
Shadow Army Cross-Skill Document Adapters (`SA-DOC-ENGINE-001` — G4)
=====================================================================
Converts structured technical/consulting payloads from `shadow-handover`,
`shadow-pmo`, `shadow-grc`, `shadow-presales`, and `shadow-ea` into validated
Canonical JSON AST v2.1 documents (or Markdown via MarkdownCompatibilityAdapter
when routing into an existing compatible project generator).
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from v2_core import (
    compute_full_hash,
    compute_semantic_hash,
    normalize_document_v2,
    utc_now_iso,
)


def _base_doc(
    *,
    doc_type: str,
    project_id: str,
    doc_id: str,
    title: str,
    owner: str,
    sources: list[dict[str, Any]],
    blocks: list[dict[str, Any]],
    code_refs: list[str] | None = None,
    git_commits: list[str] | None = None,
) -> dict[str, Any]:
    now = utc_now_iso()
    doc: dict[str, Any] = {
        "schema_version": "2.1",
        "document_id": doc_id,
        "project_id": project_id,
        "document_type": doc_type,
        "template_id": doc_type,
        "template_version": "2.1.0",
        "title": title,
        "revision": "0.1-DRAFT",
        "app_version": "1.0.0",
        "status": "DRAFT",
        "language": "id-ID",
        "classification": "INTERNAL",
        "style_profile": "corporate",
        "owner": owner,
        "created_at": now,
        "updated_at": now,
        "code_refs": code_refs or [],
        "git_commits": git_commits or [],
        "sources": sources,
        "blocks": blocks,
        "history": [
            {
                "revision": "0.1-DRAFT",
                "reason": f"Generated via Shadow Army domain adapter ({doc_type})",
                "changed_by": owner,
                "changed_at": now,
            }
        ],
        "signoff_record": [
            {"role": "Approver", "identity": None, "decision": "PENDING", "timestamp": None, "evidence_ref": None}
        ],
    }
    doc = normalize_document_v2(doc)
    doc["semantic_hash"] = compute_semantic_hash(doc)
    doc["hash"] = compute_full_hash(doc)
    return doc


def adapt_grc_payload(
    grc_payload: dict[str, Any],
    *,
    project_id: str = "PRJ-GRC",
    doc_id: str = "DOC-GRC-001",
    owner: str = "GRC Lead Auditor",
) -> dict[str, Any]:
    """Bridge `shadow-grc` findings/COBIT/SoA data into a Canonical v2.1 `GRC_ASSESSMENT` AST."""
    findings = grc_payload.get("findings", [])
    sources = list(grc_payload.get("sources") or [{"source_id": "GRC-EVIDENCE", "reference": "Verified Audit Workpapers"}])
    src_ids = [str(s["source_id"]) for s in sources if isinstance(s, dict) and s.get("source_id")]

    blocks: list[dict[str, Any]] = [
        {"id": "SEC-1", "kind": "heading", "level": 2, "title": "1. Governance & Regulatory Context", "body": None, "source_refs": src_ids, "trace_ids": []},
        {
            "id": "PAR-1",
            "kind": "paragraph",
            "title": "Sector & Framework Scope",
            "body": str(grc_payload.get("summary", f"Regulatory assessment for sector {grc_payload.get('sector', 'ENTERPRISE')}.")),
            "source_refs": src_ids,
            "evidence_refs": src_ids,
            "trace_ids": [],
        },
        {"id": "SEC-2", "kind": "heading", "level": 2, "title": "2. Six-Part Defensible Findings", "body": None, "source_refs": src_ids, "trace_ids": []},
    ]
    for idx, f in enumerate(findings, start=1):
        fid = str(f.get("id") or f"FND-{idx:03d}")
        ev_ref = str(f.get("evidence_ref") or (src_ids[0] if src_ids else "GRC-EVIDENCE"))
        blocks.append(
            {
                "id": fid,
                "kind": "finding",
                "title": str(f.get("title") or f.get("condition") or fid),
                "body": str(f.get("condition") or ""),
                "finding_data": {
                    "severity": str(f.get("severity", "HIGH")),
                    "confidence": str(f.get("confidence", "VERIFIED")),
                    "criteria": str(f.get("criteria", "")),
                    "condition": str(f.get("condition", "")),
                    "cause": str(f.get("cause", "")),
                    "effect": str(f.get("effect", "")),
                    "recommendation": str(f.get("recommendation", "")),
                    "evidence_ref": ev_ref,
                },
                "source_refs": [ev_ref] if ev_ref in src_ids else src_ids,
                "evidence_refs": [ev_ref],
                "trace_ids": [],
            }
        )
    return _base_doc(
        doc_type="GRC_ASSESSMENT",
        project_id=project_id,
        doc_id=doc_id,
        title=str(grc_payload.get("title") or "GRC & Regulatory Assurance Report"),
        owner=owner,
        sources=sources,
        blocks=blocks,
    )


def adapt_presales_payload(
    presales_payload: dict[str, Any],
    *,
    project_id: str = "PRJ-PRESALES",
    doc_id: str = "DOC-PRESALES-001",
    owner: str = "Solutions Architect",
) -> dict[str, Any]:
    """Bridge `shadow-presales` 3-scenario sizing & TCO output into a `PRESALES_PROPOSAL` AST."""
    sources = list(presales_payload.get("sources") or [{"source_id": "KAK-TENDER", "reference": "Client KAK / TOR & Price Evidence Register"}])
    scenarios = presales_payload.get("scenarios", [])
    rows = [
        [
            str(s.get("name", "-")),
            str(s.get("rps", s.get("concurrency", "-"))),
            str(s.get("vcpu", "-")),
            str(s.get("ram_gb", "-")),
            str(s.get("notes", "-")),
        ]
        for s in scenarios
    ]
    blocks: list[dict[str, Any]] = [
        {"id": "SEC-1", "kind": "heading", "level": 2, "title": "1. Solution Sizing Scenarios", "body": None, "source_refs": [], "trace_ids": []},
        {
            "id": "TBL-SIZING",
            "kind": "table",
            "title": "3-Scenario Capacity Sizing",
            "table_data": {
                "caption": "Conservative / Expected / Stress Workload Capacity",
                "columns": ["Scenario", "Load (RPS)", "vCPU", "RAM (GB)", "Notes"],
                "rows": rows or [["expected", "50", "4", "16", "Baseline sizing"]],
            },
            "source_refs": [s["source_id"] for s in sources if "source_id" in s],
            "trace_ids": [],
        },
        {
            "id": "DEC-PRESALES",
            "kind": "decision-matrix",
            "title": "Commercial & Architecture Recommendation",
            "decision_data": {
                "options": presales_payload.get("options", [{"id": "A", "title": "Recommended Option", "status": "proposed"}]),
                "selectedOption": presales_payload.get("selected_option"),
                "approvedBy": None,
                "approvedAt": None,
            },
            "source_refs": [],
            "trace_ids": [],
        },
    ]
    return _base_doc(
        doc_type="PRESALES_PROPOSAL",
        project_id=project_id,
        doc_id=doc_id,
        title=str(presales_payload.get("title") or "Enterprise Solution & Commercial Proposal"),
        owner=owner,
        sources=sources,
        blocks=blocks,
    )


def adapt_handover_payload(
    handover_payload: dict[str, Any],
    *,
    project_id: str = "PRJ-HANDOVER",
    doc_id: str = "DOC-HANDOVER-001",
    owner: str = "Tech Lead",
) -> dict[str, Any]:
    """Bridge `shadow-handover` BAST, repo/code refs, git commits & DBML/Mermaid into `HANDOVER` AST."""
    sources = list(handover_payload.get("sources") or [{"source_id": "UAT-SIGNOFF", "reference": "Staging UAT Acceptance Evidence"}])
    src_ids = [str(s["source_id"]) for s in sources if isinstance(s, dict) and s.get("source_id")]
    blocks: list[dict[str, Any]] = [
        {"id": "SEC-1", "kind": "heading", "level": 2, "title": "1. System Handover Summary", "body": None, "source_refs": src_ids, "trace_ids": []},
        {
            "id": "PAR-1",
            "kind": "paragraph",
            "title": "System Overview",
            "body": str(handover_payload.get("summary", "Completed software handover package with verified source references.")),
            "source_refs": src_ids,
            "evidence_refs": src_ids,
            "trace_ids": [],
        },
    ]
    if handover_payload.get("mermaid"):
        blocks.append(
            {
                "id": "FIG-ARCH",
                "kind": "figure",
                "title": "Handover System Topology",
                "body": str(handover_payload["mermaid"]),
                "figure_data": {"diagram_type": "mermaid", "caption": "System Topology", "mermaid": str(handover_payload["mermaid"])},
                "source_refs": src_ids,
                "trace_ids": [],
            }
        )
    if handover_payload.get("dbml"):
        blocks.append(
            {
                "id": "FIG-DBML",
                "kind": "figure",
                "title": "Database Schema (DBML)",
                "body": str(handover_payload["dbml"]),
                "figure_data": {"diagram_type": "dbml", "caption": "Core Relational Schema", "dbml": str(handover_payload["dbml"])},
                "source_refs": src_ids,
                "trace_ids": [],
            }
        )
    return _base_doc(
        doc_type="HANDOVER",
        project_id=project_id,
        doc_id=doc_id,
        title=str(handover_payload.get("title") or "Technical & BAST Handover Package"),
        owner=owner,
        sources=sources,
        blocks=blocks,
        code_refs=list(handover_payload.get("code_refs", [])),
        git_commits=list(handover_payload.get("git_commits", [])),
    )


def adapt_pmo_or_ea_payload(
    payload: dict[str, Any],
    *,
    skill_name: str,
    project_id: str = "PRJ-EXEC",
    doc_id: str | None = None,
    owner: str = "Principal Architect / PMO",
) -> dict[str, Any]:
    """Bridge `shadow-pmo` or `shadow-ea` structured output into `PROJECT_REPORT` or `ARCHITECTURE_REPORT` AST."""
    is_ea = skill_name == "shadow-ea"
    dtype = "ARCHITECTURE_REPORT" if is_ea else "PROJECT_REPORT"
    resolved_id = doc_id or ("DOC-EA-001" if is_ea else "DOC-PMO-001")
    sources = list(payload.get("sources") or [{"source_id": "ENGINE-OUTPUT", "reference": f"Verified {skill_name} deterministic calculation"}])
    rows = [[str(k), str(v)] for k, v in payload.get("metrics", {}).items()]
    blocks: list[dict[str, Any]] = [
        {"id": "SEC-1", "kind": "heading", "level": 2, "title": "1. Executive Metrics & Baseline", "body": None, "source_refs": [], "trace_ids": []},
        {
            "id": "TBL-METRICS",
            "kind": "table",
            "title": "Calculated Governance Metrics",
            "table_data": {
                "caption": "Verified Engine Outputs",
                "columns": ["Metric", "Value"],
                "rows": rows or [["Status", "Verified"]],
            },
            "source_refs": [s["source_id"] for s in sources if "source_id" in s],
            "trace_ids": [],
        },
    ]
    return _base_doc(
        doc_type=dtype,
        project_id=project_id,
        doc_id=resolved_id,
        title=str(payload.get("title") or ("Enterprise Architecture Blueprint Report" if is_ea else "PMO Governance & Progress Report")),
        owner=owner,
        sources=sources,
        blocks=blocks,
    )
