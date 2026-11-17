#!/usr/bin/env python3
"""
Shadow Army Cross-Skill Document Adapters (`SA-DOC-ENGINE-002` — R08 & H04 Hardened)
======================================================================================
Converts structured payloads from `shadow-handover`, `shadow-pmo`, `shadow-grc`,
`shadow-presales`, and `shadow-ea` into validated Canonical JSON AST v2.1 documents.

Non-negotiable rule (`R08`):
- NEVER fabricate business numbers, commercial metrics, audit findings, or verified
  source citations when inputs are missing.
- Explicitly classify missing vs user-provided vs computed inputs, emit `[MISSING_EVIDENCE]` /
  `[TBD]` / `UNVERIFIED` markers, and reject contradictory/invalid business values when strict.
"""

from __future__ import annotations

from typing import Any

from v2_core import (
    compute_full_hash,
    compute_semantic_hash,
    normalize_document_v2,
    utc_now_iso,
)

ADAPTER_CONTRACTS: dict[str, dict[str, Any]] = {
    "shadow-grc": {
        "target_document_type": "GRC_ASSESSMENT",
        "required_fields": ["sector", "findings", "sources"],
        "optional_fields": ["title", "summary", "findings[].criteria", "findings[].evidence_ref"],
        "output_guarantees": ["preserves 6-part findings cleanly", "never upgrades missing evidence to VERIFIED"],
        "unsupported_structures": ["binary workpaper attachments"],
    },
    "shadow-presales": {
        "target_document_type": "PRESALES_PROPOSAL",
        "required_fields": ["scenarios", "sources"],
        "optional_fields": ["title", "options", "selected_option"],
        "output_guarantees": ["preserves 3-scenario workload matrix", "blocks negative or inverted stress<conservative values"],
        "unsupported_structures": ["live vendor pricing API lookup"],
    },
    "shadow-handover": {
        "target_document_type": "HANDOVER",
        "required_fields": ["summary", "sources"],
        "optional_fields": ["title", "mermaid", "dbml", "code_refs", "git_commits"],
        "output_guarantees": ["preserves Mermaid/DBML source & code/git traceability", "never assumes UAT sign-off without evidence"],
        "unsupported_structures": ["plaintext production secrets"],
    },
    "shadow-pmo": {
        "target_document_type": "PROJECT_REPORT",
        "required_fields": ["metrics", "sources"],
        "optional_fields": ["title"],
        "output_guarantees": ["preserves deterministic schedule/EVM metrics", "flags negative/invalid EVM ratios"],
        "unsupported_structures": ["raw MS Project MPP XML"],
    },
    "shadow-ea": {
        "target_document_type": "ARCHITECTURE_REPORT",
        "required_fields": ["metrics", "sources"],
        "optional_fields": ["title", "mermaid"],
        "output_guarantees": ["preserves TIME/SPBE metrics & Mermaid blueprints"],
        "unsupported_structures": ["proprietary ArchiMate binary exchange"],
    },
}


def _resolve_sources(raw_sources: Any, *, missing_fields: list[str]) -> tuple[list[dict[str, Any]], list[str], bool]:
    if isinstance(raw_sources, list) and len(raw_sources) > 0:
        clean = [s for s in raw_sources if isinstance(s, dict) and s.get("source_id") and s.get("reference")]
        if clean:
            return clean, [str(s["source_id"]) for s in clean], False
    missing_fields.append("sources")
    placeholder = [
        {
            "source_id": "UNVERIFIED-SOURCE-MISSING",
            "reference": "[MISSING_EVIDENCE: supply verified source document]",
            "source_type": "UNVERIFIED",
            "peer_reviewed": False,
        }
    ]
    return placeholder, [], True


def _base_doc(
    *,
    doc_type: str,
    project_id: str,
    doc_id: str,
    title: str,
    owner: str,
    sources: list[dict[str, Any]],
    blocks: list[dict[str, Any]],
    integrity_report: dict[str, Any],
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
        "extensions": {"x-shadow:data_integrity": integrity_report},
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
    strict: bool = False,
) -> dict[str, Any]:
    """Bridge `shadow-grc` findings/COBIT/SoA data into a Canonical v2.1 `GRC_ASSESSMENT` AST without fabricating evidence."""
    missing: list[str] = []
    invalid: list[str] = []
    sources, src_ids, src_missing = _resolve_sources(grc_payload.get("sources"), missing_fields=missing)

    sector = grc_payload.get("sector")
    if not sector:
        missing.append("sector")
        sector_display = "[UNVERIFIED: sector unspecified]"
    else:
        sector_display = str(sector)

    findings = grc_payload.get("findings")
    if not isinstance(findings, list) or len(findings) == 0:
        missing.append("findings")
        findings = []

    blocks: list[dict[str, Any]] = [
        {"id": "SEC-1", "kind": "heading", "level": 2, "title": "1. Governance & Regulatory Context", "body": None, "source_refs": src_ids, "trace_ids": []},
        {
            "id": "PAR-1",
            "kind": "paragraph",
            "title": "Sector & Framework Scope",
            "body": str(grc_payload.get("summary") or f"Regulatory assessment for sector: {sector_display}. Origin: {'missing_inputs' if missing else 'user_provided'}."),
            "source_refs": src_ids,
            "evidence_refs": src_ids,
            "trace_ids": [],
        },
        {"id": "SEC-2", "kind": "heading", "level": 2, "title": "2. Six-Part Defensible Findings", "body": None, "source_refs": src_ids, "trace_ids": []},
    ]

    if not findings:
        blocks.append(
            {
                "id": "PAR-NO-FINDINGS",
                "kind": "paragraph",
                "title": "Pending Fieldwork",
                "body": "[UNVERIFIED: No audit findings supplied in payload.]",
                "status": "UNVERIFIED",
                "source_refs": src_ids,
                "trace_ids": [],
            }
        )

    for idx, f in enumerate(findings, start=1):
        if not isinstance(f, dict):
            invalid.append(f"findings[{idx-1}] must be an object")
            continue
        fid = str(f.get("id") or f"FND-{idx:03d}")
        raw_ev = f.get("evidence_ref")
        if raw_ev:
            ev_ref = str(raw_ev)
            conf = str(f.get("confidence") or "USER_PROVIDED")
        else:
            missing.append(f"{fid}.evidence_ref")
            ev_ref = "[MISSING_EVIDENCE]"
            conf = "UNVERIFIED"
        blocks.append(
            {
                "id": fid,
                "kind": "finding",
                "title": str(f.get("title") or f.get("condition") or fid),
                "body": str(f.get("condition") or "[TBD]"),
                "status": "UNVERIFIED" if conf == "UNVERIFIED" else "DRAFT",
                "finding_data": {
                    "severity": str(f.get("severity", "UNSPECIFIED")),
                    "confidence": conf,
                    "criteria": str(f.get("criteria") or "[TBD: missing regulatory/standard criteria]"),
                    "condition": str(f.get("condition") or "[TBD: missing observed condition]"),
                    "cause": str(f.get("cause") or "[TBD]"),
                    "effect": str(f.get("effect") or "[TBD]"),
                    "recommendation": str(f.get("recommendation") or "[TBD]"),
                    "evidence_ref": ev_ref,
                },
                "source_refs": [ev_ref] if ev_ref in src_ids else src_ids,
                "evidence_refs": [ev_ref] if raw_ev else [],
                "trace_ids": [],
            }
        )

    if strict and (missing or invalid):
        raise ValueError(f"STRICT_ADAPTER_VALIDATION_FAILED (shadow-grc): missing={missing}, invalid={invalid}")

    return _base_doc(
        doc_type="GRC_ASSESSMENT",
        project_id=project_id,
        doc_id=doc_id,
        title=str(grc_payload.get("title") or "GRC & Regulatory Assurance Report"),
        owner=owner,
        sources=sources,
        blocks=blocks,
        integrity_report={
            "adapter": "shadow-grc",
            "source_status": "UNVERIFIED" if src_missing else "USER_PROVIDED",
            "missing_fields": missing,
            "invalid_or_contradictory": invalid,
        },
    )


def adapt_presales_payload(
    presales_payload: dict[str, Any],
    *,
    project_id: str = "PRJ-PRESALES",
    doc_id: str = "DOC-PRESALES-001",
    owner: str = "Solutions Architect",
    strict: bool = False,
) -> dict[str, Any]:
    """Bridge `shadow-presales` sizing & TCO output cleanly without fabricating synthetic sizing rows."""
    missing: list[str] = []
    invalid: list[str] = []
    sources, src_ids, src_missing = _resolve_sources(presales_payload.get("sources"), missing_fields=missing)

    scenarios = presales_payload.get("scenarios")
    rows: list[list[str]] = []
    parsed_rps_by_name: dict[str, float] = {}

    if isinstance(scenarios, list) and len(scenarios) > 0:
        for idx, s in enumerate(scenarios):
            if not isinstance(s, dict):
                invalid.append(f"scenarios[{idx}] must be an object")
                continue
            s_name = str(s.get("name") or f"scenario_{idx+1}")
            rps_val = s.get("rps", s.get("concurrency"))
            vcpu_val = s.get("vcpu")
            ram_val = s.get("ram_gb")
            for k_nm, v_raw in (("rps", rps_val), ("vcpu", vcpu_val), ("ram_gb", ram_val)):
                if v_raw is not None:
                    try:
                        num = float(v_raw)
                        if num < 0:
                            invalid.append(f"{s_name}.{k_nm} cannot be negative ({num})")
                        elif k_nm == "rps":
                            parsed_rps_by_name[s_name.lower()] = num
                    except (TypeError, ValueError):
                        invalid.append(f"{s_name}.{k_nm} must be numeric (got {v_raw!r})")
            rows.append(
                [
                    s_name,
                    str(rps_val if rps_val is not None else "[TBD]"),
                    str(vcpu_val if vcpu_val is not None else "[TBD]"),
                    str(ram_val if ram_val is not None else "[TBD]"),
                    str(s.get("notes") or "[USER_PROVIDED]"),
                ]
            )
        if "conservative" in parsed_rps_by_name and "stress" in parsed_rps_by_name:
            if parsed_rps_by_name["stress"] < parsed_rps_by_name["conservative"]:
                invalid.append(
                    f"Contradictory scenarios: stress RPS ({parsed_rps_by_name['stress']}) < conservative RPS ({parsed_rps_by_name['conservative']})."
                )
    else:
        missing.append("scenarios")
        rows = [["[MISSING]", "[TBD]", "[TBD]", "[TBD]", "[UNVERIFIED: supply workload capacity inputs]"]]

    raw_opts = presales_payload.get("options")
    if not isinstance(raw_opts, list) or not raw_opts:
        missing.append("options")
        raw_opts = [{"id": "TBD", "title": "[UNVERIFIED: solution options not supplied]", "status": "pending"}]

    if strict and (missing or invalid):
        raise ValueError(f"STRICT_ADAPTER_VALIDATION_FAILED (shadow-presales): missing={missing}, invalid={invalid}")

    blocks: list[dict[str, Any]] = [
        {"id": "SEC-1", "kind": "heading", "level": 2, "title": "1. Solution Sizing Scenarios", "body": None, "source_refs": src_ids, "trace_ids": []},
        {
            "id": "TBL-SIZING",
            "kind": "table",
            "title": "3-Scenario Capacity Sizing",
            "status": "UNVERIFIED" if (missing or invalid) else "DRAFT",
            "table_data": {
                "caption": "Conservative / Expected / Stress Workload Capacity",
                "columns": ["Scenario", "Load (RPS)", "vCPU", "RAM (GB)", "Notes"],
                "rows": rows,
            },
            "source_refs": src_ids,
            "trace_ids": [],
        },
        {
            "id": "DEC-PRESALES",
            "kind": "decision-matrix",
            "title": "Commercial & Architecture Recommendation",
            "decision_data": {
                "options": raw_opts,
                "selectedOption": presales_payload.get("selected_option"),
                "approvedBy": presales_payload.get("approved_by"),
                "approvedAt": presales_payload.get("approved_at"),
            },
            "source_refs": src_ids,
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
        integrity_report={
            "adapter": "shadow-presales",
            "source_status": "UNVERIFIED" if src_missing else "USER_PROVIDED",
            "missing_fields": missing,
            "invalid_or_contradictory": invalid,
        },
    )


def adapt_handover_payload(
    handover_payload: dict[str, Any],
    *,
    project_id: str = "PRJ-HANDOVER",
    doc_id: str = "DOC-HANDOVER-001",
    owner: str = "Tech Lead",
    strict: bool = False,
) -> dict[str, Any]:
    """Bridge `shadow-handover` BAST & diagram metadata cleanly without assuming unverified UAT acceptance."""
    missing: list[str] = []
    sources, src_ids, src_missing = _resolve_sources(handover_payload.get("sources"), missing_fields=missing)

    summary = handover_payload.get("summary")
    if not summary:
        missing.append("summary")
        summary_text = "[ISI DARI SUMBER PROYEK: Handover scope & system summary not yet provided.]"
    else:
        summary_text = str(summary)

    if strict and missing:
        raise ValueError(f"STRICT_ADAPTER_VALIDATION_FAILED (shadow-handover): missing={missing}")

    blocks: list[dict[str, Any]] = [
        {"id": "SEC-1", "kind": "heading", "level": 2, "title": "1. System Handover Summary", "body": None, "source_refs": src_ids, "trace_ids": []},
        {
            "id": "PAR-1",
            "kind": "paragraph",
            "title": "System Overview",
            "status": "UNVERIFIED" if missing else "DRAFT",
            "body": summary_text,
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
        integrity_report={
            "adapter": "shadow-handover",
            "source_status": "UNVERIFIED" if src_missing else "USER_PROVIDED",
            "missing_fields": missing,
            "invalid_or_contradictory": [],
        },
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
    strict: bool = False,
) -> dict[str, Any]:
    """Bridge `shadow-pmo` or `shadow-ea` structured output without inventing computed metrics."""
    missing: list[str] = []
    invalid: list[str] = []
    is_ea = skill_name == "shadow-ea"
    dtype = "ARCHITECTURE_REPORT" if is_ea else "PROJECT_REPORT"
    resolved_id = doc_id or ("DOC-EA-001" if is_ea else "DOC-PMO-001")
    sources, src_ids, src_missing = _resolve_sources(payload.get("sources"), missing_fields=missing)

    raw_metrics = payload.get("metrics")
    rows: list[list[str]] = []
    if isinstance(raw_metrics, dict) and len(raw_metrics) > 0:
        for k, v in raw_metrics.items():
            if str(k).upper() in ("CPI", "SPI", "EAC", "PV", "EV", "AC"):
                try:
                    num = float(v)
                    if num < 0:
                        invalid.append(f"Metric {k} cannot be negative ({num})")
                except (TypeError, ValueError):
                    invalid.append(f"Metric {k} must be numeric (got {v!r})")
            rows.append([str(k), str(v)])
    else:
        missing.append("metrics")
        rows = [["[MISSING_METRICS]", "[UNVERIFIED: supply computed engine outputs]"]]

    if strict and (missing or invalid):
        raise ValueError(f"STRICT_ADAPTER_VALIDATION_FAILED ({skill_name}): missing={missing}, invalid={invalid}")

    blocks: list[dict[str, Any]] = [
        {"id": "SEC-1", "kind": "heading", "level": 2, "title": "1. Executive Metrics & Baseline", "body": None, "source_refs": src_ids, "trace_ids": []},
        {
            "id": "TBL-METRICS",
            "kind": "table",
            "title": "Calculated Governance Metrics",
            "status": "UNVERIFIED" if (missing or invalid) else "DRAFT",
            "table_data": {
                "caption": "Engine Outputs Register",
                "columns": ["Metric", "Value"],
                "rows": rows,
            },
            "source_refs": src_ids,
            "trace_ids": [],
        },
    ]
    if is_ea and payload.get("mermaid"):
        blocks.append(
            {
                "id": "FIG-EA",
                "kind": "figure",
                "title": "Enterprise Architecture Topology",
                "body": str(payload["mermaid"]),
                "figure_data": {"diagram_type": "mermaid", "caption": "EA Blueprint", "mermaid": str(payload["mermaid"])},
                "source_refs": src_ids,
                "trace_ids": [],
            }
        )
    return _base_doc(
        doc_type=dtype,
        project_id=project_id,
        doc_id=resolved_id,
        title=str(payload.get("title") or ("Enterprise Architecture Blueprint Report" if is_ea else "PMO Governance & Progress Report")),
        owner=owner,
        sources=sources,
        blocks=blocks,
        integrity_report={
            "adapter": skill_name,
            "source_status": "UNVERIFIED" if src_missing else "COMPUTED_OR_PROVIDED",
            "missing_fields": missing,
            "invalid_or_contradictory": invalid,
        },
    )
