#!/usr/bin/env python3
"""
Shadow GRC Assurance Engine (grc_assurance_engine.py)

Deterministic evaluator for:
1. COBIT 2019 (strict separation of Process Capability 0-5 vs Focus Area Maturity 0-5)
2. ISO/IEC 27001:2022 (Clauses 4-10 + 93 Annex A distribution + SoA justification & DE/OE evidence)
3. 6-part Defensible Audit Findings + Active Regulation Validation (PADK OJK 1/2026 vs revoked SEOJK 21/2017)
"""

from __future__ import annotations

from datetime import date
import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "shadow-monarch" / "scripts"))
from shadow_input import InvalidInput, run_checked_cli, strict_bool

REPO_ROOT = Path(__file__).resolve().parents[2]
CORE_SCRIPTS = REPO_ROOT / "shadow-monarch" / "consulting-core" / "scripts"
if str(CORE_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(CORE_SCRIPTS))

from consulting_core import check_regulations  # noqa: E402

REQUIRED_ISO_CLAUSES = {"4", "5", "6", "7", "8", "9", "10"}
EXPECTED_ANNEX_A_COUNTS = {
    "ORGANIZATIONAL": 37,
    "PEOPLE": 8,
    "PHYSICAL": 14,
    "TECHNOLOGICAL": 34,
}
UNAUTHORIZED_CERT_CLAIM = re.compile(
    r"\b(?:officially\s+certified\s+ISO\s*27001|tersedia\s+sertifikasi\s+resmi|100%\s+compliant\s+without\s+audit)\b",
    re.IGNORECASE,
)


def assess_cobit_2019(payload: dict[str, Any]) -> dict[str, Any]:
    """Assess COBIT 2019 Process Capability separately from Focus Area Maturity."""
    objectives = payload.get("objectives", [])
    if not objectives:
        raise ValueError("objectives list cannot be empty.")

    capability_results: list[dict[str, Any]] = []
    domain_buckets: dict[str, list[int]] = {}
    low_confidence_count = 0

    for obj in objectives:
        oid = str(obj["objective_id"]).upper()
        domain = re.sub(r"\d+", "", oid)
        level = obj["capability_level"]
        if isinstance(level, bool) or not isinstance(level, int):
            raise InvalidInput(f"{oid}: capability_level must be a JSON integer.")
        if not (0 <= level <= 5):
            raise ValueError(f"Capability level for {oid} must be 0..5, got {level}.")
        ev_refs = obj.get("evidence_refs", [])
        if not isinstance(ev_refs, list) or not all(isinstance(ref, str) and ref.strip() for ref in ev_refs):
            raise InvalidInput(f"{oid}: evidence_refs must be an array of nonblank strings.")
        confidence = "HIGH" if len(ev_refs) >= 2 else ("MEDIUM" if len(ev_refs) == 1 else "INSUFFICIENT")
        if confidence == "INSUFFICIENT":
            low_confidence_count += 1
        capability_results.append({
            "objective_id": oid,
            "domain": domain,
            "process_capability_level": level,
            "evidence_confidence": confidence,
        })
        domain_buckets.setdefault(domain, []).append(level)

    # Focus Area Maturity uses minimum systemic threshold per focus area (cannot exceed weakest core objective)
    focus_areas = payload.get("focus_areas", [])
    focus_maturity: list[dict[str, Any]] = []
    for fa in focus_areas:
        fa_objs = [o for o in capability_results if o["objective_id"] in fa.get("objective_ids", [])]
        if not fa_objs:
            focus_maturity.append({"focus_area": fa["name"], "maturity_level": None, "status": "INSUFFICIENT_SCOPE"})
            continue
        min_cap = min(o["process_capability_level"] for o in fa_objs)
        avg_cap = round(sum(o["process_capability_level"] for o in fa_objs) / len(fa_objs), 2)
        focus_maturity.append({
            "focus_area": fa["name"],
            "focus_area_maturity_level": min_cap,
            "mean_objective_capability_reference": avg_cap,
            "note": "Focus Area Maturity is governed by weakest critical process capability, not raw average.",
        })

    return {
        "framework": "COBIT 2019",
        "capability_vs_maturity_separated": True,
        "objective_capabilities": capability_results,
        "focus_area_maturity": focus_maturity,
        "insufficient_evidence_objectives": low_confidence_count,
        "assurance_ready": low_confidence_count == 0,
    }


def validate_iso27001_soa(soa: dict[str, Any]) -> dict[str, Any]:
    """Validate ISO/IEC 27001:2022 Clauses 4-10 coverage and Annex A SoA rules."""
    errors: list[str] = []
    clauses_covered = {str(c) for c in soa.get("management_clauses_covered", [])}
    missing_clauses = sorted(REQUIRED_ISO_CLAUSES - clauses_covered)
    if missing_clauses:
        errors.append(f"Missing mandatory ISMS Clauses 4-10 coverage: {missing_clauses}")

    if UNAUTHORIZED_CERT_CLAIM.search(json.dumps(soa)):
        errors.append("HG3: Self-assessment SoA cannot declare official ISO 27001 certification.")

    controls = soa.get("annex_a_controls", [])
    if not isinstance(controls, list):
        raise InvalidInput("annex_a_controls must be a JSON array.")
    if not controls:
        errors.append("Annex A scope requires at least one control with an applicability determination.")
    theme_counts: dict[str, int] = {k: 0 for k in EXPECTED_ANNEX_A_COUNTS}
    for ctrl in controls:
        if not isinstance(ctrl, dict):
            raise InvalidInput("Each annex_a_controls entry must be a JSON object.")
        cid = ctrl.get("control_id")
        if not isinstance(cid, str) or not cid.strip():
            raise InvalidInput("Each Annex A control requires a nonblank control_id.")
        theme = str(ctrl.get("theme", "")).upper()
        if theme not in theme_counts:
            raise InvalidInput(f"{cid}: theme must match an Annex A control theme.")
        theme_counts[theme] += 1
        applicable = strict_bool(ctrl.get("applicable", True), "applicable")
        justification = ctrl.get("justification")
        if not isinstance(justification, str) or not justification.strip():
            errors.append(f"{cid}: missing applicability justification.")
        if applicable and str(ctrl.get("status", "")).upper() == "IMPLEMENTED":
            refs = (ctrl.get("design_evidence_ref"), ctrl.get("operating_evidence_ref"))
            if not all(isinstance(ref, str) and ref.strip() for ref in refs):
                errors.append(f"{cid}: IMPLEMENTED control requires both design_evidence_ref and operating_evidence_ref.")

    if strict_bool(soa.get("require_full_93_controls", False), "require_full_93_controls"):
        if theme_counts != EXPECTED_ANNEX_A_COUNTS:
            errors.append(f"Annex A control distribution mismatch: got {theme_counts}, expected {EXPECTED_ANNEX_A_COUNTS}.")

    return {
        "standard": "ISO/IEC 27001:2022",
        "clauses_4_10_complete": len(missing_clauses) == 0,
        "theme_counts": theme_counts,
        "total_controls_evaluated": len(controls),
        "valid": len(errors) == 0,
        "errors": errors,
    }


def validate_audit_findings(findings: list[dict[str, Any]], sector: str = "GENERAL_ENTERPRISE", as_of_date: str | None = None) -> dict[str, Any]:
    """Validate 6-part defensible findings and regulatory applicability."""
    required_parts = ("criteria", "condition", "cause", "effect", "recommendation", "evidence_ref")
    errors: list[dict[str, Any]] = []
    cited_regs: list[str] = []

    if not isinstance(findings, list):
        raise InvalidInput("findings must be a JSON array.")
    for f in findings:
        if not isinstance(f, dict):
            raise InvalidInput("Each findings entry must be a JSON object.")
        fid = f.get("finding_id", "<unknown>")
        for part in required_parts:
            value = f.get(part)
            if not isinstance(value, str) or not value.strip():
                errors.append({"finding_id": fid, "error": f"Missing mandatory audit element '{part}'."})
        for reg_id in f.get("regulation_ids", []):
            cited_regs.append(str(reg_id))

    try:
        if not as_of_date or date.fromisoformat(as_of_date).isoformat() != as_of_date:
            raise ValueError
    except (ValueError, TypeError):
        errors.append({"finding_id": "REGULATORY_GATE", "error": "Supply assessment date as YYYY-MM-DD."})
        return {"sector": sector, "as_of_date": as_of_date, "finding_count": len(findings), "valid": False, "errors": errors}

    if not findings:
        errors.append({"finding_id": "FINDINGS_GATE", "error": "At least one audit finding is required."})

    reg_check = check_regulations(sector, cited_regs, as_of_date=as_of_date)
    for rerr in reg_check["errors"]:
        errors.append({"finding_id": "REGULATORY_GATE", "error": rerr["reason"], "gate": rerr["gate"]})

    return {
        "sector": sector,
        "as_of_date": as_of_date,
        "finding_count": len(findings),
        "applicability_warnings": reg_check["warnings"],
        "valid": len(errors) == 0,
        "errors": errors,
    }


def run_self_test() -> dict[str, Any]:
    """Run precision, recall, and adversarial GRC probes."""
    results: list[dict[str, Any]] = []

    # Precision-1: Valid COBIT assessment separating capability vs maturity
    cobit_ok = assess_cobit_2019({
        "objectives": [
            {"objective_id": "APO12", "capability_level": 3, "evidence_refs": ["EVD-1", "EVD-2"]},
            {"objective_id": "DSS05", "capability_level": 2, "evidence_refs": ["EVD-3", "EVD-4"]},
        ],
        "focus_areas": [{"name": "Cyber & Risk Resilience", "objective_ids": ["APO12", "DSS05"]}],
    })
    results.append({
        "probe": "PRECISION-1: COBIT separates objective capability (3, 2) from focus maturity (min=2)",
        "passed": cobit_ok["assurance_ready"] and cobit_ok["focus_area_maturity"][0]["focus_area_maturity_level"] == 2,
    })

    # Recall-1: COBIT with 0 evidence flagged as insufficient
    cobit_no_ev = assess_cobit_2019({
        "objectives": [{"objective_id": "APO13", "capability_level": 4, "evidence_refs": []}],
        "focus_areas": [{"name": "Security", "objective_ids": ["APO13"]}],
    })
    results.append({"probe": "RECALL-1: COBIT flags missing evidence despite high claimed score", "passed": not cobit_no_ev["assurance_ready"]})

    # Precision-2: Valid ISO 27001:2022 SoA (Clauses 4-10 + DE/OE evidence)
    soa_ok = validate_iso27001_soa({
        "management_clauses_covered": ["4", "5", "6", "7", "8", "9", "10"],
        "annex_a_controls": [
            {"control_id": "A.5.15", "theme": "ORGANIZATIONAL", "applicable": True, "status": "IMPLEMENTED", "justification": "RBAC required", "design_evidence_ref": "EVD-D1", "operating_evidence_ref": "EVD-O1"},
            {"control_id": "A.7.1", "theme": "PHYSICAL", "applicable": False, "status": "NOT_APPLICABLE", "justification": "Fully remote cloud-native org without physical server rooms"},
        ],
    })
    results.append({"probe": "PRECISION-2: ISO 27001 SoA with Clauses 4-10 & DE+OE evidence passes", "passed": soa_ok["valid"]})

    # Recall-2: ISO 27001 missing Clauses 4-10 and missing OE evidence must FAIL
    soa_bad = validate_iso27001_soa({
        "management_clauses_covered": ["4"],
        "annex_a_controls": [
            {"control_id": "A.8.24", "theme": "TECHNOLOGICAL", "applicable": True, "status": "IMPLEMENTED", "justification": "Crypto", "design_evidence_ref": "EVD-D2"},
        ],
    })
    results.append({"probe": "RECALL-2: Rejects ISO 27001 audit omitting Clauses 5-10 & operating evidence", "passed": (not soa_bad["valid"]) and len(soa_bad["errors"]) >= 2})

    # Precision-3: Banking findings citing POJK-11-2022 + PADK-OJK-1-2026 with all 6 fields
    f_ok = validate_audit_findings([
        {
            "finding_id": "GRC-BNK-01",
            "criteria": "PADK OJK No. 1/2026 & POJK 11/POJK.03/2022 PPJTI Review",
            "condition": "2 of 5 critical cloud vendors lack annual materiality reassessment",
            "cause": "Vendor lifecycle workflow omits risk trigger",
            "effect": "Regulatory & operational resilience exposure",
            "recommendation": "Institute annual PPJTI materiality review before renewal",
            "evidence_ref": "EVD-VEND-01",
            "regulation_ids": ["POJK-11-2022", "PADK-OJK-1-2026"],
        }
    ], sector="BANKING", as_of_date="2026-11-16")
    results.append({"probe": "PRECISION-3: Defensible banking finding citing PADK OJK 1/2026 passes", "passed": f_ok["valid"]})

    # Recall-3: Banking finding citing superseded SEOJK-21-2017 after 2026-03-01 fails
    f_old = validate_audit_findings([
        {
            "finding_id": "GRC-BNK-OLD",
            "criteria": "SEOJK 21/SEOJK.03/2017",
            "condition": "Missing log review",
            "cause": "No alert rule",
            "effect": "Undetected intrusion",
            "recommendation": "Enable SIEM alerts",
            "evidence_ref": "EVD-LOG-01",
            "regulation_ids": ["SEOJK-21-2017"],
        }
    ], sector="BANKING", as_of_date="2026-11-16")
    results.append({"probe": "RECALL-3: Blocks revoked SEOJK-21-2017 citation after 2026-03-01", "passed": not f_old["valid"]})

    # Recall-4: Rejects finding missing cause/evidence_ref
    f_incomplete = validate_audit_findings([
        {"finding_id": "GRC-BAD", "criteria": "ISO", "condition": "Weak auth", "recommendation": "Fix", "evidence_ref": ""}
    ])
    results.append({"probe": "RECALL-4: Rejects findings missing cause/effect/evidence_ref", "passed": not f_incomplete["valid"]})

    for missing in (None, "2026-02-30"):
        result = validate_audit_findings([], as_of_date=missing)
        results.append({"probe": f"Reject missing or invalid assessment date {missing}", "passed": not result["valid"]})

    # Precision-4: Unauthorized ISO certification overclaim in SoA blocked
    soa_overclaim = validate_iso27001_soa({
        "management_clauses_covered": ["4", "5", "6", "7", "8", "9", "10"],
        "summary": "Organization is officially certified ISO 27001 based on this self-assessment.",
        "annex_a_controls": [],
    })
    results.append({"probe": "RECALL-5: Blocks self-assessment claiming official ISO 27001 certification", "passed": not soa_overclaim["valid"]})

    passed = sum(1 for r in results if r["passed"])
    return {
        "tool": "grc_assurance_engine.py",
        "total_probes": len(results),
        "passed": passed,
        "failed": len(results) - passed,
        "all_passed": passed == len(results),
        "results": results,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Shadow GRC Evidence-Based Assurance Engine")
    parser.add_argument("--assess-cobit", default=None)
    parser.add_argument("--validate-soa", default=None)
    parser.add_argument("--validate-findings", default=None)
    parser.add_argument("--as-of-date", help="Assessment date (YYYY-MM-DD) for regulatory applicability")
    parser.add_argument("--sector", default="GENERAL_ENTERPRISE")
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()

    if args.self_test:
        res = run_self_test()
        print(json.dumps(res, indent=2))
        return 0 if res["all_passed"] else 1
    if args.assess_cobit:
        payload = json.loads(Path(args.assess_cobit).read_text(encoding="utf-8"))
        print(json.dumps(assess_cobit_2019(payload), indent=2))
        return 0
    if args.validate_soa:
        payload = json.loads(Path(args.validate_soa).read_text(encoding="utf-8"))
        res = validate_iso27001_soa(payload)
        print(json.dumps(res, indent=2))
        return 0 if res["valid"] else 1
    if args.validate_findings:
        payload = json.loads(Path(args.validate_findings).read_text(encoding="utf-8"))
        res = validate_audit_findings(payload if isinstance(payload, list) else payload.get("findings", []), sector=args.sector, as_of_date=args.as_of_date or (payload.get("as_of_date") if isinstance(payload, dict) else None))
        print(json.dumps(res, indent=2))
        return 0 if res["valid"] else 1

    parser.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(run_checked_cli(main))
