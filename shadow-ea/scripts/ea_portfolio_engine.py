#!/usr/bin/env python3
"""
Shadow EA Portfolio Intelligence & SPBE 6-Domain Engine (ea_portfolio_engine.py)

Provides:
1. Application Portfolio TIME rationalization & duplicate capability detection
2. Government SPBE 6-Domain completeness validation (Perpres 95/2018 & 132/2022)
3. ABB-to-SBB mapping validation and cross-skill traceable finding generation
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

REQUIRED_SPBE_6_DOMAINS = {
    "PROSES_BISNIS",
    "DATA_DAN_INFORMASI",
    "INFRASTRUKTUR_SPBE",
    "APLIKASI_SPBE",
    "KEAMANAN_SPBE",
    "LAYANAN_SPBE",
}


def classify_time(business_value: float, tech_health: float, is_duplicate_redundant: bool = False) -> str:
    if is_duplicate_redundant and business_value < 4.0:
        return "ELIMINATE"
    if business_value >= 3.5 and tech_health >= 3.0:
        return "INVEST"
    if business_value >= 3.5 and tech_health < 3.0:
        return "MIGRATE"
    if business_value < 3.5 and tech_health >= 3.0:
        return "TOLERATE"
    return "ELIMINATE"


def analyze_portfolio(spec: dict[str, Any]) -> dict[str, Any]:
    org_type = str(spec.get("org_type", "GENERAL_ENTERPRISE")).upper()
    apps = spec.get("applications", [])
    if not apps:
        raise ValueError("applications list cannot be empty.")

    by_capability: dict[str, list[dict[str, Any]]] = {}
    for app in apps:
        cap = str(app.get("business_capability", "UNMAPPED"))
        by_capability.setdefault(cap, []).append(app)

    duplicate_capabilities: list[dict[str, Any]] = []
    catalog_out: list[dict[str, Any]] = []
    ea_findings: list[dict[str, Any]] = []

    for cap, group in by_capability.items():
        is_dup = len(group) > 1
        if is_dup:
            duplicate_capabilities.append({
                "business_capability": cap,
                "system_count": len(group),
                "system_ids": [a["system_id"] for a in group],
            })
            ea_findings.append({
                "finding_id": f"EA-DUP-{cap.upper().replace(' ', '_')}",
                "claim": f"{len(group)} overlapping applications support '{cap}'.",
                "affected_systems": [a["system_id"] for a in group],
                "downstream_handoff": ["shadow-modernize", "shadow-presales", "shadow-pmo"],
            })

        # Keep highest (business_value + tech_health) system as anchor; lower duplicates marked redundant
        sorted_group = sorted(
            group,
            key=lambda a: (float(a.get("business_value", 0)), float(a.get("tech_health", 0))),
            reverse=True,
        )
        for idx, app in enumerate(sorted_group):
            bv = float(app.get("business_value", 3.0))
            th = float(app.get("tech_health", 3.0))
            quad = classify_time(bv, th, is_duplicate_redundant=(is_dup and idx > 0))
            catalog_out.append({
                "system_id": app["system_id"],
                "name": app["name"],
                "business_capability": cap,
                "business_value": bv,
                "tech_health": th,
                "time_quadrant": quad,
                "data_owner": app.get("data_owner", "UNASSIGNED"),
            })

    spbe_validation: dict[str, Any] = {"required": org_type == "GOVERNMENT_SPBE", "valid": True, "missing_domains": []}
    if org_type == "GOVERNMENT_SPBE":
        declared_domains = {str(d).upper() for d in spec.get("spbe_domains_covered", [])}
        missing = sorted(REQUIRED_SPBE_6_DOMAINS - declared_domains)
        spbe_validation = {
            "required": True,
            "expected_domains_count": 6,
            "missing_domains": missing,
            "valid": len(missing) == 0,
        }

    abb_gaps = []
    for gap in spec.get("abb_sbb_gaps", []):
        if not gap.get("abb_id") or not gap.get("candidate_sbb"):
            abb_gaps.append({"gap": gap, "error": "Gap entry must specify both vendor-neutral abb_id and concrete candidate_sbb."})

    return {
        "org_type": org_type,
        "total_systems": len(apps),
        "duplicate_capability_groups": duplicate_capabilities,
        "portfolio_time_catalog": catalog_out,
        "spbe_6_domain_validation": spbe_validation,
        "abb_sbb_errors": abb_gaps,
        "traceable_findings": ea_findings,
        "valid": spbe_validation["valid"] and len(abb_gaps) == 0,
    }


def run_self_test() -> dict[str, Any]:
    """Run precision, recall, and SPBE 6-domain adversarial probes."""
    results: list[dict[str, Any]] = []

    gov_ok = analyze_portfolio({
        "org_type": "GOVERNMENT_SPBE",
        "spbe_domains_covered": [
            "PROSES_BISNIS", "DATA_DAN_INFORMASI", "INFRASTRUKTUR_SPBE",
            "APLIKASI_SPBE", "KEAMANAN_SPBE", "LAYANAN_SPBE",
        ],
        "applications": [
            {"system_id": "SYS-SIMPEG-1", "name": "SIMPEG Pusat", "business_capability": "HR Management", "business_value": 4.5, "tech_health": 2.0, "data_owner": "BKD"},
            {"system_id": "SYS-SIMPEG-2", "name": "Absensi Silo", "business_capability": "HR Management", "business_value": 2.5, "tech_health": 1.5, "data_owner": "Unit B"},
            {"system_id": "SYS-PORTAL", "name": "Portal Layanan Publik", "business_capability": "Citizen Portal", "business_value": 4.8, "tech_health": 4.2, "data_owner": "Diskominfo"},
        ],
        "abb_sbb_gaps": [{"abb_id": "ABB-IAM-SSO", "candidate_sbb": "Keycloak OIDC HA"}],
    })
    results.append({
        "probe": "PRECISION-1: SPBE 6 domains complete + detects duplicate HR capability + classifies MIGRATE/ELIMINATE/INVEST",
        "passed": (
            gov_ok["valid"]
            and len(gov_ok["duplicate_capability_groups"]) == 1
            and any(c["system_id"] == "SYS-SIMPEG-1" and c["time_quadrant"] == "MIGRATE" for c in gov_ok["portfolio_time_catalog"])
            and any(c["system_id"] == "SYS-SIMPEG-2" and c["time_quadrant"] == "ELIMINATE" for c in gov_ok["portfolio_time_catalog"])
            and any(c["system_id"] == "SYS-PORTAL" and c["time_quadrant"] == "INVEST" for c in gov_ok["portfolio_time_catalog"])
        ),
    })

    # Recall-1: Government SPBE using only 4 TOGAF domains (missing KEAMANAN_SPBE & LAYANAN_SPBE) MUST FAIL
    gov_4_domains = analyze_portfolio({
        "org_type": "GOVERNMENT_SPBE",
        "spbe_domains_covered": ["PROSES_BISNIS", "DATA_DAN_INFORMASI", "INFRASTRUKTUR_SPBE", "APLIKASI_SPBE"],
        "applications": [{"system_id": "SYS-1", "name": "App 1", "business_capability": "Core", "business_value": 4.0, "tech_health": 4.0}],
    })
    results.append({
        "probe": "RECALL-1: Blocks Government SPBE blueprint covering only 4 TOGAF domains instead of 6 SPBE domains",
        "passed": (not gov_4_domains["valid"]) and set(gov_4_domains["spbe_6_domain_validation"]["missing_domains"]) == {"KEAMANAN_SPBE", "LAYANAN_SPBE"},
    })

    # Precision-2: General Enterprise does not require 6 SPBE domains
    ent_ok = analyze_portfolio({
        "org_type": "GENERAL_ENTERPRISE",
        "applications": [{"system_id": "SYS-ERP", "name": "ERP", "business_capability": "Finance", "business_value": 4.5, "tech_health": 4.0}],
    })
    results.append({"probe": "PRECISION-2: General Enterprise is not forced into SPBE 6-domain check", "passed": ent_ok["valid"]})

    # Recall-2: Missing candidate_sbb in ABB/SBB gap flagged
    bad_abb = analyze_portfolio({
        "org_type": "GENERAL_ENTERPRISE",
        "applications": [{"system_id": "SYS-1", "name": "App", "business_capability": "Ops", "business_value": 3.0, "tech_health": 3.5}],
        "abb_sbb_gaps": [{"abb_id": "ABB-01"}],
    })
    results.append({"probe": "RECALL-2: Rejects ABB gap entry missing concrete candidate_sbb", "passed": not bad_abb["valid"]})

    # Precision-3: TOLERATE classification for stable low-strategic utility app
    tol = analyze_portfolio({
        "org_type": "BUMN",
        "applications": [{"system_id": "SYS-ARCH", "name": "Archive Viewer", "business_capability": "Compliance Archive", "business_value": 2.5, "tech_health": 4.0}],
    })
    results.append({
        "probe": "PRECISION-3: Low business value + healthy app classifies as TOLERATE",
        "passed": tol["portfolio_time_catalog"][0]["time_quadrant"] == "TOLERATE",
    })

    # Recall-3: Empty applications raises ValueError
    empty_caught = False
    try:
        analyze_portfolio({"org_type": "BUMN", "applications": []})
    except ValueError:
        empty_caught = True
    results.append({"probe": "RECALL-3: Empty application portfolio raises explicit ValueError", "passed": empty_caught})

    # Precision-4: Generates downstream traceable findings for shadow-modernize/presales/pmo
    results.append({
        "probe": "PRECISION-4: Duplicate capabilities emit traceable EA-DUP-* findings linking downstream skills",
        "passed": gov_ok["traceable_findings"][0]["finding_id"] == "EA-DUP-HR_MANAGEMENT",
    })

    # Precision-5: Unique capabilities produce 0 duplicate capability groups
    results.append({
        "probe": "PRECISION-5: Distinct capabilities produce zero false-positive duplicate alerts",
        "passed": len(ent_ok["duplicate_capability_groups"]) == 0 and len(ent_ok["traceable_findings"]) == 0,
    })

    passed = sum(1 for r in results if r["passed"])
    return {
        "tool": "ea_portfolio_engine.py",
        "total_probes": len(results),
        "passed": passed,
        "failed": len(results) - passed,
        "all_passed": passed == len(results),
        "results": results,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Shadow EA Portfolio & SPBE 6-Domain Engine")
    parser.add_argument("--analyze-portfolio", default=None)
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()

    if args.self_test:
        res = run_self_test()
        print(json.dumps(res, indent=2))
        return 0 if res["all_passed"] else 1
    if args.analyze_portfolio:
        spec = json.loads(Path(args.analyze_portfolio).read_text(encoding="utf-8"))
        res = analyze_portfolio(spec)
        print(json.dumps(res, indent=2))
        return 0 if res["valid"] else 1

    parser.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
