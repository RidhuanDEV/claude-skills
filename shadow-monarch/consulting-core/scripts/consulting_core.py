#!/usr/bin/env python3
"""
Shadow Army Consulting Intelligence Core (consulting_core.py)

Shared foundation across /shadow-presales, /shadow-grc, /shadow-modernize,
/shadow-pmo, and /shadow-ea providing:
1. Context-aware methodology & industry pack routing
2. Versioned regulatory applicability & superseded-citation checks
3. Evidence & provenance bundle validation + cross-skill traceability checks
4. Non-compensable Hard Gates & Consulting Competency Scorecard evaluation
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))
from shadow_input import run_checked_cli, strict_bool

CORE_DIR = Path(__file__).resolve().parent.parent
REGISTRY_PATH = CORE_DIR / "regulations_registry.json"
PACKS_PATH = CORE_DIR / "industry_packs.json"

PROHIBITED_OVERCLAIMS: list[tuple[str, re.Pattern[str]]] = [
    (
        "HG3_UNAUTHORIZED_CERTIFICATION_CLAIM",
        re.compile(r"\b(?:officially\s+certified\s+ISO\s*27001|tersedia\s+sertifikasi\s+resmi|100%\s+compliant\s+without\s+audit)\b", re.IGNORECASE),
    ),
    (
        "HG3_UNAUTHORIZED_PPK_HPS_DETERMINATION",
        re.compile(r"\b(?:menetapkan\s+HPS\s+resmi\s+atas\s+nama\s+PPK|official\s+PPK\s+HPS\s+approved\s+by\s+AI)\b", re.IGNORECASE),
    ),
    (
        "HG3_UNAUTHORIZED_LEGAL_CR_VERDICT",
        re.compile(r"\b(?:legally\s+binding\s+paid\s+CR\s+verdict|final\s+legal\s+determination\s+without\s+contract\s+counsel)\b", re.IGNORECASE),
    ),
]


def load_registry() -> dict[str, Any]:
    return json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))


def load_industry_packs() -> dict[str, Any]:
    return json.loads(PACKS_PATH.read_text(encoding="utf-8"))


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def select_methodology(org_type: str, engagement_type: str) -> dict[str, Any]:
    packs = load_industry_packs()["industry_packs"]
    org_key = org_type.upper()
    if org_key not in packs:
        raise ValueError(f"Unknown org_type '{org_type}'. Valid: {sorted(packs.keys())}")
    pack = packs[org_key]
    return {
        "org_type": org_key,
        "engagement_type": engagement_type.upper(),
        "label": pack["label"],
        "mandatory_regulations": pack["mandatory_regulations"],
        "methodologies": pack["primary_methodologies"],
        "escalation_authorities": pack["escalation_authorities"],
        "prohibited_claims": pack["prohibited_claims"],
    }


def check_regulations(sector: str, cited_ids: list[str] | None = None, as_of_date: str = "2026-11-16") -> dict[str, Any]:
    reg_data = load_registry()["regulations"]
    by_id = {r["regulation_id"]: r for r in reg_data}
    sector_key = sector.upper()
    applicable = [r for r in reg_data if sector_key in r.get("applicability", []) and r.get("verification_status") == "VERIFIED"]

    errors: list[dict[str, Any]] = []
    warnings: list[dict[str, Any]] = []
    verified_citations: list[str] = []

    for cid in cited_ids or []:
        if cid not in by_id:
            errors.append({
                "gate": "HG1_NO_FABRICATED_OR_SUPERSEDED_REGULATION",
                "citation": cid,
                "reason": f"Regulation ID '{cid}' does not exist in verified primary registry.",
            })
            continue
        entry = by_id[cid]
        if entry.get("verification_status") == "SUPERSEDED":
            sup_date = entry.get("superseded_effective_date", "")
            if not sup_date or as_of_date >= sup_date:
                errors.append({
                    "gate": "HG1_NO_FABRICATED_OR_SUPERSEDED_REGULATION",
                    "citation": cid,
                    "reason": f"'{cid}' was superseded by '{entry.get('superseded_by')}' effective {sup_date}.",
                })
                continue
        if sector_key not in entry.get("applicability", []):
            warnings.append({
                "citation": cid,
                "reason": f"'{cid}' is not mapped to sector '{sector_key}' by default; verify applicability.",
            })
        verified_citations.append(cid)

    return {
        "sector": sector_key,
        "as_of_date": as_of_date,
        "applicable_verified_ids": [r["regulation_id"] for r in applicable],
        "verified_citations": verified_citations,
        "errors": errors,
        "warnings": warnings,
        "passed": len(errors) == 0,
    }


def validate_bundle(bundle: dict[str, Any]) -> dict[str, Any]:
    """Validate engagement schema, evidence provenance, assumptions, traceability, and hard gates."""
    errors: list[dict[str, Any]] = []
    required_top = [
        "engagement_id", "context", "evidence_registry", "assumption_register",
        "findings", "decisions", "traceability_links", "review_gate",
    ]
    for key in required_top:
        if key not in bundle:
            errors.append({"gate": "SCHEMA_REQUIRED_FIELD", "field": key, "reason": f"Missing top-level field '{key}'."})
    if errors:
        return {"valid": False, "errors": errors, "hard_gates_passed": False}

    ev_ids = {e["evidence_id"] for e in bundle.get("evidence_registry", []) if "evidence_id" in e}
    for e in bundle.get("evidence_registry", []):
        if len(str(e.get("integrity_hash", ""))) < 8:
            errors.append({
                "gate": "HG4_EVIDENCE_PROVENANCE_COMPLETE",
                "id": e.get("evidence_id"),
                "reason": "Evidence item lacks integrity_hash (SHA-256 or digest >= 8 chars).",
            })

    assump_ids = {a["assumption_id"] for a in bundle.get("assumption_register", []) if "assumption_id" in a}
    finding_ids = set()
    for f in bundle.get("findings", []):
        fid = f.get("finding_id", "<unknown>")
        finding_ids.add(fid)
        refs = f.get("evidence_refs", [])
        if not refs:
            errors.append({
                "gate": "HG4_EVIDENCE_PROVENANCE_COMPLETE",
                "id": fid,
                "reason": "Finding has zero evidence_refs.",
            })
        for ref in refs:
            if ref not in ev_ids:
                errors.append({
                    "gate": "HG4_EVIDENCE_PROVENANCE_COMPLETE",
                    "id": fid,
                    "reason": f"Finding references missing evidence_id '{ref}'.",
                })

    decision_ids = set()
    for d in bundle.get("decisions", []):
        did = d.get("decision_id", "<unknown>")
        decision_ids.add(did)
        if not d.get("alternatives_compared"):
            errors.append({
                "gate": "DECISION_ALTERNATIVES_REQUIRED",
                "id": did,
                "reason": "Decision must compare at least 1 explicit alternative.",
            })
        for aref in d.get("assumption_refs", []):
            if aref not in assump_ids:
                errors.append({
                    "gate": "HG2_NO_UNDECLARED_ASSUMPTIONS",
                    "id": did,
                    "reason": f"Decision references undeclared assumption_id '{aref}'.",
                })
        if not strict_bool(d.get("requires_human_approval"), "requires_human_approval"):
            rec_text = str(d.get("recommendation", ""))
            for gate_id, pat in PROHIBITED_OVERCLAIMS:
                if pat.search(rec_text):
                    errors.append({
                        "gate": gate_id,
                        "id": did,
                        "reason": "High-authority legal/certification/HPS conclusion requires human approval.",
                    })

    # Check raw text of bundle for prohibited overclaims
    serialized = json.dumps(bundle, ensure_ascii=False)
    for gate_id, pat in PROHIBITED_OVERCLAIMS:
        if pat.search(serialized):
            errors.append({
                "gate": gate_id,
                "id": bundle.get("engagement_id"),
                "reason": f"Prohibited overclaim pattern detected ({gate_id}).",
            })

    # Check regulations cited in context
    ctx = bundle.get("context", {})
    reg_res = check_regulations(
        str(ctx.get("org_type", "GENERAL_ENTERPRISE")),
        list(ctx.get("sector_regulations", [])),
        str(ctx.get("assessment_date", "2026-11-16")),
    )
    for rerr in reg_res["errors"]:
        errors.append(rerr)

    # Check cross-skill traceability links point to declared IDs
    system_ids = {s.get("system_id") for s in bundle.get("systems", []) if s.get("system_id")}
    known_ids = ev_ids | assump_ids | finding_ids | decision_ids | system_ids
    for link in bundle.get("traceability_links", []):
        for end_key in ("from_id", "to_id"):
            node = link.get(end_key)
            if node not in known_ids:
                errors.append({
                    "gate": "TRACEABILITY_BROKEN_LINK",
                    "id": node,
                    "reason": f"Traceability link endpoint '{node}' not found in systems/evidence/assumptions/findings/decisions.",
                })

    return {
        "engagement_id": bundle.get("engagement_id"),
        "valid": len(errors) == 0,
        "hard_gates_passed": len(errors) == 0,
        "evidence_count": len(ev_ids),
        "assumption_count": len(assump_ids),
        "finding_count": len(finding_ids),
        "decision_count": len(decision_ids),
        "traceability_link_count": len(bundle.get("traceability_links", [])),
        "error_count": len(errors),
        "errors": errors,
    }


def score_competency(scores: dict[str, float], bundle: dict[str, Any] | None = None, numerical_reconciled: bool = False) -> dict[str, Any]:
    """
    Compute 6-dimension weighted Consulting Competency Scorecard (0-100)
    with 5 Non-Compensable Hard Gates.
    """
    weights = {
        "methodology_selection": 15.0,
        "technical_depth": 20.0,
        "evidence_traceability": 20.0,
        "quantitative_reliability": 15.0,
        "regulatory_accuracy": 15.0,
        "decision_quality": 15.0,
    }
    weighted_sum = 0.0
    for dim, weight in weights.items():
        val = float(scores.get(dim, 0.0))
        val = max(0.0, min(5.0, val))
        weighted_sum += (val / 5.0) * weight

    hard_gate_failures: list[str] = []
    if not strict_bool(numerical_reconciled, "numerical_reconciled"):
        hard_gate_failures.append("HG5_NUMERICAL_RECONCILIATION_VALID")
    if bundle is not None:
        val_res = validate_bundle(bundle)
        for err in val_res["errors"]:
            hard_gate_failures.append(str(err["gate"]))

    unique_failures = sorted(set(hard_gate_failures))
    enterprise_ready = (round(weighted_sum, 2) >= 90.0) and (len(unique_failures) == 0)

    return {
        "score_0_100": round(weighted_sum, 2),
        "threshold": 90.0,
        "hard_gates_passed": len(unique_failures) == 0,
        "hard_gate_failures": unique_failures,
        "enterprise_ready": enterprise_ready,
    }


def run_self_test() -> dict[str, Any]:
    """Run Golden, Adversarial, Traceability & Precision/Recall probes."""
    results: list[dict[str, Any]] = []

    # 1. Precision: Valid Banking context citing POJK-11-2022 & PADK-OJK-1-2026
    r_ok = check_regulations("BANKING", ["POJK-11-2022", "PADK-OJK-1-2026", "UU-27-2022"], as_of_date="2026-11-16")
    results.append({"probe": "PRECISION-1: Active banking regulations after 2026-03-01", "passed": r_ok["passed"]})

    # 2. Adversarial Recall: Superseded SEOJK-21-2017 after 2026-03-01 must FAIL HG1
    r_old = check_regulations("BANKING", ["SEOJK-21-2017"], as_of_date="2026-11-16")
    results.append({
        "probe": "RECALL-1: Superseded SEOJK-21-2017 blocked after 2026-03-01",
        "passed": (not r_old["passed"]) and any(e["gate"] == "HG1_NO_FABRICATED_OR_SUPERSEDED_REGULATION" for e in r_old["errors"]),
    })

    # 3. Adversarial Recall: Fabricated Regulation ID must FAIL HG1
    r_fake = check_regulations("GOVERNMENT_SPBE", ["PERPRES-999-2099"])
    results.append({"probe": "RECALL-2: Fabricated regulation ID blocked", "passed": not r_fake["passed"]})

    # 4. End-to-End Cross-Skill Bundle (EA -> Modernize -> GRC -> Presales -> PMO)
    golden_bundle: dict[str, Any] = {
        "engagement_id": "ENG-BUMN-2026-001",
        "context": {
            "org_type": "BUMN",
            "engagement_type": "ADVISORY",
            "sector_regulations": ["PERPRES-46-2025", "UU-27-2022", "ISO-IEC-27001-2022", "ISACA-COBIT-2019"],
            "assessment_date": "2026-11-16",
            "access_limitations": ["Read-only code & config; no prod DB dump access"],
        },
        "evidence_registry": [
            {
                "evidence_id": "EVD-EA-001",
                "source_type": "application_catalog",
                "source_path": "docs/ea/portfolio.csv",
                "collected_at": "2026-11-16",
                "method": "stakeholder_inventory_reconciliation",
                "integrity_hash": sha256_text("EVD-EA-001"),
            },
            {
                "evidence_id": "EVD-MOD-001",
                "source_type": "dependency_manifest",
                "source_path": "legacy-billing/package-lock.json",
                "collected_at": "2026-11-16",
                "method": "read_only_static_scan",
                "integrity_hash": sha256_text("EVD-MOD-001"),
            },
        ],
        "assumption_register": [
            {
                "assumption_id": "ASM-001",
                "statement": "Peak concurrency reaches 3x expected baseline during month-end closing",
                "owner": "Client IT Infra Lead",
                "sensitivity": "HIGH",
                "validation_status": "CLIENT_CONFIRMED",
            }
        ],
        "systems": [
            {"system_id": "SYS-BILL-01", "name": "Legacy Billing A", "capability": "Invoicing", "time_quadrant": "MIGRATE"},
            {"system_id": "SYS-BILL-02", "name": "Subsidiary Billing B", "capability": "Invoicing", "time_quadrant": "ELIMINATE"},
        ],
        "findings": [
            {
                "finding_id": "EA-DUP-001",
                "claim": "2 overlapping invoicing applications identified in Finance capability",
                "severity": "HIGH",
                "confidence": "HIGH",
                "evidence_refs": ["EVD-EA-001"],
                "review_status": "REVIEWED_APPROVED",
            },
            {
                "finding_id": "MOD-EOL-001",
                "claim": "Legacy Billing A runs on EOL runtime lacking automated integration tests",
                "severity": "HIGH",
                "confidence": "HIGH",
                "evidence_refs": ["EVD-MOD-001"],
                "review_status": "REVIEWED_APPROVED",
            },
        ],
        "decisions": [
            {
                "decision_id": "DEC-CONSOL-001",
                "skill": "shadow-modernize",
                "recommendation": "Execute phased Strangler Fig consolidation onto Billing A core with characterization tests",
                "alternatives_compared": ["FULL_REWRITE", "STRANGLER_FIG_REFACTOR", "STATUS_QUO"],
                "assumption_refs": ["ASM-001"],
                "requires_human_approval": True,
                "approval_authority": "Enterprise Architecture Board & CFO",
            }
        ],
        "traceability_links": [
            {"from_id": "EA-DUP-001", "to_id": "SYS-BILL-01", "relation": "identifies_consolidation_target"},
            {"from_id": "MOD-EOL-001", "to_id": "DEC-CONSOL-001", "relation": "drives_modernization_option"},
        ],
        "review_gate": {
            "independent_review_status": "PASSED",
            "reviewer_role": "Principal Enterprise Architect",
            "hard_gates_checked": True,
        },
    }
    b_val = validate_bundle(golden_bundle)
    score_ok = score_competency(
        {
            "methodology_selection": 5, "technical_depth": 5, "evidence_traceability": 5,
            "quantitative_reliability": 5, "regulatory_accuracy": 5, "decision_quality": 5,
        },
        bundle=golden_bundle,
        numerical_reconciled=True,
    )
    results.append({
        "probe": "PRECISION-2: Cross-skill traced golden bundle passes all Hard Gates (100/100)",
        "passed": b_val["valid"] and score_ok["enterprise_ready"] and score_ok["score_0_100"] == 100.0,
    })

    # 5. Adversarial Recall: Missing evidence + unauthorized certification claim must fail even with 5/5 subjective scores
    bad_bundle = json.loads(json.dumps(golden_bundle))
    bad_bundle["findings"][0]["evidence_refs"] = []
    bad_bundle["decisions"][0]["recommendation"] = "Organization is officially certified ISO 27001 by self-assessment."
    bad_bundle["decisions"][0]["requires_human_approval"] = False
    score_bad = score_competency(
        {
            "methodology_selection": 5, "technical_depth": 5, "evidence_traceability": 5,
            "quantitative_reliability": 5, "regulatory_accuracy": 5, "decision_quality": 5,
        },
        bundle=bad_bundle,
        numerical_reconciled=False,
    )
    results.append({
        "probe": "RECALL-3: Non-compensable Hard Gates block 5/5 score when evidence/claims/math fail",
        "passed": (not score_bad["enterprise_ready"]) and (not score_bad["hard_gates_passed"]) and len(score_bad["hard_gate_failures"]) >= 3,
        "failures_caught": score_bad["hard_gate_failures"],
    })

    # 6. Precision: Methodology router returns Government 6-domain SPBE + Perpres 46/2025
    meth = select_methodology("GOVERNMENT_SPBE", "PRESALES")
    results.append({
        "probe": "PRECISION-3: Context-aware router injects Perpres 46/2025 & SPBE for Government",
        "passed": "PERPRES-46-2025" in meth["mandatory_regulations"] and "PERPRES-132-2022" in meth["mandatory_regulations"],
    })

    passed = sum(1 for r in results if r["passed"])
    return {
        "tool": "consulting_core.py",
        "total_probes": len(results),
        "passed": passed,
        "failed": len(results) - passed,
        "all_passed": passed == len(results),
        "results": results,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Shadow Army Consulting Intelligence Core")
    parser.add_argument("--select-methodology", action="store_true")
    parser.add_argument("--org-type", default="GENERAL_ENTERPRISE")
    parser.add_argument("--engagement-type", default="ADVISORY")
    parser.add_argument("--check-regulations", action="store_true")
    parser.add_argument("--sector", default="GENERAL_ENTERPRISE")
    parser.add_argument("--cite", action="append", default=[])
    parser.add_argument("--validate-bundle", default=None)
    parser.add_argument("--score-competency", default=None)
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()

    if args.self_test:
        res = run_self_test()
        print(json.dumps(res, indent=2, ensure_ascii=False))
        return 0 if res["all_passed"] else 1

    if args.select_methodology:
        print(json.dumps(select_methodology(args.org_type, args.engagement_type), indent=2, ensure_ascii=False))
        return 0

    if args.check_regulations:
        res = check_regulations(args.sector, args.cite)
        print(json.dumps(res, indent=2, ensure_ascii=False))
        return 0 if res["passed"] else 1

    if args.validate_bundle:
        bundle = json.loads(Path(args.validate_bundle).read_text(encoding="utf-8"))
        res = validate_bundle(bundle)
        print(json.dumps(res, indent=2, ensure_ascii=False))
        return 0 if res["valid"] else 1

    if args.score_competency:
        payload = json.loads(Path(args.score_competency).read_text(encoding="utf-8"))
        res = score_competency(
            payload.get("scores", {}),
            bundle=payload.get("bundle"),
            numerical_reconciled=strict_bool(payload.get("numerical_reconciled"), "numerical_reconciled"),
        )
        print(json.dumps(res, indent=2, ensure_ascii=False))
        return 0 if res["enterprise_ready"] else 1

    parser.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(run_checked_cli(main))
