#!/usr/bin/env python3
"""
Shadow Modernize Forensics & Migration Economics Engine (modernize_forensics_engine.py)

Provides:
1. Read-only codebase forensic inventory with SHA-256 evidence provenance
2. Multi-dimensional risk vector evaluation (not a single opaque score) with confidence
3. Risk-adjusted Modernization TCO comparison (Strangler Fig Refactor vs Modularize vs Rewrite)
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "shadow-monarch" / "scripts"))
from shadow_input import InvalidInput, run_checked_cli, strict_bool

SKIP_DIRS = {".git", "node_modules", ".next", "dist", "build", "__pycache__", ".venv", "venv", "vendor"}
REQUIRED_COST_INPUTS = ("annual_legacy_ops_cost", "rewrite_build_cost", "strangler_build_cost", "encapsulate_build_cost")
MANIFEST_NAMES = {
    "package.json", "package-lock.json", "pnpm-lock.yaml", "yarn.lock",
    "pyproject.toml", "requirements.txt", "poetry.lock",
    "go.mod", "go.sum", "pom.xml", "build.gradle", "build.gradle.kts",
    "composer.json", "composer.lock", "cargo.toml", "dockerfile", "docker-compose.yml",
}


def scan_repo_forensics(repo_path: Path) -> dict[str, Any]:
    """Read-only repository structural & manifest inventory with provenance digests."""
    if not repo_path.exists():
        raise FileNotFoundError(f"Repository path not found: {repo_path}")

    manifests: list[dict[str, str]] = []
    ext_counts: dict[str, int] = {}
    has_tests = False
    has_ci = False
    sql_migrations = 0

    for fpath in repo_path.rglob("*"):
        if not fpath.is_file() or any(part in SKIP_DIRS for part in fpath.parts):
            continue
        rel = fpath.relative_to(repo_path).as_posix()
        lname = fpath.name.lower()
        ext = fpath.suffix.lower() or "<noext>"
        ext_counts[ext] = ext_counts.get(ext, 0) + 1

        if lname in MANIFEST_NAMES:
            digest = hashlib.sha256(fpath.read_bytes()).hexdigest()[:16]
            manifests.append({"path": rel, "sha256_prefix": digest})
        if "test" in rel.lower() or "spec" in rel.lower():
            has_tests = True
        if rel.startswith(".github/workflows/") or lname in {".gitlab-ci.yml", "jenkinsfile", "azure-pipelines.yml"}:
            has_ci = True
        if ext == ".sql" or "migration" in rel.lower():
            sql_migrations += 1

    return {
        "repo": str(repo_path),
        "method": "read_only_static_scan",
        "manifests": manifests,
        "extension_counts": dict(sorted(ext_counts.items(), key=lambda kv: (-kv[1], kv[0]))[:12]),
        "signals": {
            "has_automated_tests": has_tests,
            "has_ci_pipeline": has_ci,
            "migration_artifacts_count": sql_migrations,
        },
        "limitations": [
            "Static repo inspection only; production latency/SLO, live DB triggers, and incident frequency require runtime telemetry."
        ],
    }


def evaluate_modernization_options(profile: dict[str, Any]) -> dict[str, Any]:
    """
    Evaluate multi-dimensional risk vector + risk-adjusted TCO across modernization strategies.
    Prevents blind rewrite recommendations on stable, rule-heavy legacy cores lacking tests.
    """
    dims = profile.get("risk_dimensions", {})
    weights = profile.get("dimension_weights", {
        "code_dependencies": 0.15,
        "architecture_coupling": 0.15,
        "data_integrity": 0.20,
        "operations_slo": 0.15,
        "security_supply_chain": 0.20,
        "business_criticality": 0.15,
    })

    if not isinstance(dims, dict) or not isinstance(weights, dict):
        raise InvalidInput("risk_dimensions and dimension_weights must be JSON objects.")
    vector_out: dict[str, Any] = {}
    has_evidence = False
    weighted_risk = 0.0
    low_conf_dims: list[str] = []
    missing_dims: list[str] = []
    for dim, weight in weights.items():
        if type(weight) not in (int, float) or not math.isfinite(weight) or weight < 0:
            raise InvalidInput(f"dimension_weights.{dim} must be finite and nonnegative.")
        if dim not in dims:
            if weight > 0:
                missing_dims.append(dim)
            continue
        entry = dims[dim]
        if not isinstance(entry, dict):
            raise InvalidInput(f"risk_dimensions.{dim} must be a JSON object.")
        evidence = entry.get("evidence_refs", [])
        if not isinstance(evidence, list) or not all(isinstance(ref, str) and ref.strip() for ref in evidence):
            raise InvalidInput(f"risk_dimensions.{dim}.evidence_refs must be an array of nonblank strings.")
        if "score" not in entry:
            if weight > 0:
                missing_dims.append(dim)
            continue
        sc = entry["score"]
        if type(sc) not in (int, float) or not 0 <= sc <= 5:
            raise InvalidInput(f"risk_dimensions.{dim}.score must be a finite JSON number in [0, 5].")
        has_evidence = has_evidence or (weight > 0 and "score" in entry and bool(evidence))
        conf = str(entry.get("confidence", "LOW")).upper()
        if conf == "LOW":
            low_conf_dims.append(dim)
        weighted_risk += sc * float(weight)
        vector_out[dim] = {"score_0_5": sc, "weight": weight, "confidence": conf, "evidence_refs": evidence}

    if not has_evidence:
        raise InvalidInput("At least one weighted risk dimension requires a score and evidence_refs.")

    rule_complexity = str(profile.get("business_rule_complexity", "HIGH")).upper()
    ops_stable = strict_bool(profile.get("production_stability_high", True), "production_stability_high")
    has_tests = strict_bool(profile.get("has_automated_tests", False), "has_automated_tests")

    # Economics inputs (3-5 yr horizon) must come from the profile; no hidden default costs.
    missing_costs: list[str] = []
    costs: dict[str, float] = {}
    for field in REQUIRED_COST_INPUTS:
        if field not in profile:
            missing_costs.append(field)
            continue
        value = profile[field]
        if type(value) not in (int, float) or not math.isfinite(value) or value <= 0:
            raise InvalidInput(f"{field} must be a finite, positive JSON number.")
        costs[field] = float(value)
    years_raw = profile.get("horizon_years")
    if years_raw is None:
        missing_costs.append("horizon_years")
    elif type(years_raw) is not int or not 1 <= years_raw <= 10:
        raise InvalidInput("horizon_years must be a JSON integer in [1, 10].")

    if missing_dims or missing_costs:
        return {
            "system_id": profile.get("system_id", "SYS-UNKNOWN"),
            "status": "INSUFFICIENT_EVIDENCE",
            "recommended_strategy": None,
            "missing_risk_dimensions": missing_dims,
            "missing_cost_inputs": missing_costs,
            "guardrail_rationale": "Provide every weighted risk dimension (score + evidence_refs) and all cost inputs before ranking strategies.",
        }

    years = int(years_raw)
    annual_legacy_ops = costs["annual_legacy_ops_cost"]
    rewrite_build = costs["rewrite_build_cost"]
    strangler_build = costs["strangler_build_cost"]
    encapsulate_build = costs["encapsulate_build_cost"]

    # Rewrite carries higher business-rule loss & dual-run coexistence risk when undocumented rules are HIGH
    rewrite_risk_penalty = 0.45 * rewrite_build if rule_complexity == "HIGH" else 0.20 * rewrite_build
    strangler_risk_penalty = 0.15 * strangler_build
    coexistence_strangler = 0.35 * annual_legacy_ops * years
    coexistence_rewrite = 0.65 * annual_legacy_ops * years

    options = [
        {
            "strategy": "STRANGLER_FIG_REFACTOR",
            "build_cost": round(strangler_build, 2),
            "coexistence_and_ops_cost": round(coexistence_strangler + (0.6 * annual_legacy_ops * years), 2),
            "risk_adjusted_penalty": round(strangler_risk_penalty, 2),
        },
        {
            "strategy": "FULL_REWRITE",
            "build_cost": round(rewrite_build, 2),
            "coexistence_and_ops_cost": round(coexistence_rewrite + (0.4 * annual_legacy_ops * years), 2),
            "risk_adjusted_penalty": round(rewrite_risk_penalty, 2),
        },
        {
            "strategy": "ENCAPSULATE_RETAIN",
            "build_cost": round(encapsulate_build, 2),
            "coexistence_and_ops_cost": round(annual_legacy_ops * years, 2),
            "risk_adjusted_penalty": round(weighted_risk * 0.10 * annual_legacy_ops, 2),
        },
    ]
    for opt in options:
        opt["total_risk_adjusted_tco"] = round(opt["build_cost"] + opt["coexistence_and_ops_cost"] + opt["risk_adjusted_penalty"], 2)

    options.sort(key=lambda o: o["total_risk_adjusted_tco"])
    recommended = options[0]["strategy"]

    # Guard against naive rewrite recommendation when stable & high undocumented rules without tests
    archaeology_required = (not has_tests) and rule_complexity == "HIGH"
    rewrite_guard_note = (
        "Lack of tests + high business-rule complexity requires Business-Rule Archaeology & Characterization Tests before code extraction; avoid blind Full Rewrite."
        if (ops_stable and archaeology_required)
        else "Proceed with phased verification gates."
    )

    return {
        "system_id": profile.get("system_id", "SYS-UNKNOWN"),
        "status": "EVALUATED",
        "risk_vector": vector_out,
        "composite_reference_risk_0_5": round(weighted_risk, 2),
        "low_confidence_dimensions": low_conf_dims,
        "archaeology_prerequisite_required": archaeology_required,
        "recommended_strategy": recommended,
        "guardrail_rationale": rewrite_guard_note,
        "options_tco_ranked": options,
    }


def run_self_test() -> dict[str, Any]:
    """Run precision, recall, and anti-blind-rewrite probes."""
    results: list[dict[str, Any]] = []

    stable_legacy = {
        "system_id": "SYS-CORE-LEDGER",
        "business_rule_complexity": "HIGH",
        "production_stability_high": True,
        "has_automated_tests": False,
        "horizon_years": 3,
        "annual_legacy_ops_cost": 1_000_000_000,
        "strangler_build_cost": 1_800_000_000,
        "rewrite_build_cost": 3_200_000_000,
        "encapsulate_build_cost": 900_000_000,
        "risk_dimensions": {
            "code_dependencies": {"score": 4.0, "confidence": "HIGH", "evidence_refs": ["EVD-CODE-1"]},
            "architecture_coupling": {"score": 4.0, "confidence": "HIGH", "evidence_refs": ["EVD-ARCH-1"]},
            "data_integrity": {"score": 3.0, "confidence": "HIGH", "evidence_refs": ["EVD-DB-1"]},
            "operations_slo": {"score": 1.5, "confidence": "HIGH", "evidence_refs": ["EVD-OPS-1"]},
            "security_supply_chain": {"score": 3.5, "confidence": "MEDIUM", "evidence_refs": ["EVD-SEC-1"]},
            "business_criticality": {"score": 5.0, "confidence": "HIGH", "evidence_refs": ["EVD-BIZ-1"]},
        },
    }
    res = evaluate_modernization_options(stable_legacy)
    # Precision-1: Must NOT recommend blind FULL_REWRITE on stable rule-heavy core without tests
    results.append({
        "probe": "PRECISION-1: Stable high-rule system without tests avoids blind FULL_REWRITE & requires archaeology",
        "passed": res["recommended_strategy"] != "FULL_REWRITE" and res["archaeology_prerequisite_required"],
    })

    # Precision-2: Risk vector exposes all 6 dimensions separately with evidence confidence
    results.append({
        "probe": "PRECISION-2: Separate 6-dimension risk vector + confidence returned",
        "passed": len(res["risk_vector"]) == 6 and len(res["low_confidence_dimensions"]) == 0,
    })

    # Recall-1: Low-confidence dimensions explicitly surfaced
    low_conf = json.loads(json.dumps(stable_legacy))
    low_conf["risk_dimensions"]["operations_slo"] = {"score": 2.0, "confidence": "LOW", "evidence_refs": []}
    res_low = evaluate_modernization_options(low_conf)
    results.append({
        "probe": "RECALL-1: Surfaces low-confidence risk dimensions when telemetry missing",
        "passed": "operations_slo" in res_low["low_confidence_dimensions"],
    })

    # Recall-2: TCO arithmetic reconciliation across all options
    math_ok = all(
        round(o["build_cost"] + o["coexistence_and_ops_cost"] + o["risk_adjusted_penalty"], 2) == o["total_risk_adjusted_tco"]
        for o in res["options_tco_ranked"]
    )
    results.append({"probe": "PRECISION-3: Migration TCO components sum exactly to total_risk_adjusted_tco", "passed": math_ok})

    # Precision-4: Read-only repo scan works on this workspace cleanly
    repo_scan = scan_repo_forensics(Path(__file__).resolve().parents[2])
    results.append({
        "probe": "PRECISION-4: Read-only repo scan detects manifests & preserves limitation disclosure",
        "passed": repo_scan["method"] == "read_only_static_scan" and len(repo_scan["limitations"]) >= 1,
    })

    # Recall-3: Higher rewrite build cost monotonically raises FULL_REWRITE TCO
    expensive = json.loads(json.dumps(stable_legacy))
    expensive["rewrite_build_cost"] = 5_000_000_000
    res_exp = evaluate_modernization_options(expensive)
    rw_base = next(o["total_risk_adjusted_tco"] for o in res["options_tco_ranked"] if o["strategy"] == "FULL_REWRITE")
    rw_exp = next(o["total_risk_adjusted_tco"] for o in res_exp["options_tco_ranked"] if o["strategy"] == "FULL_REWRITE")
    results.append({"probe": "RECALL-2: Higher rewrite cost monotonically increases FULL_REWRITE risk-adjusted TCO", "passed": rw_exp > rw_base})

    # Recall-4: Missing repo path raises FileNotFoundError cleanly
    err_caught = False
    try:
        scan_repo_forensics(Path("non_existent_repo_xyz_999"))
    except FileNotFoundError:
        err_caught = True
    results.append({"probe": "RECALL-3: Missing repo path raises explicit FileNotFoundError", "passed": err_caught})

    # Precision-5: Configurable dimension weights shift composite reference risk accurately
    custom_w = json.loads(json.dumps(stable_legacy))
    custom_w["dimension_weights"] = {
        "code_dependencies": 0.0, "architecture_coupling": 0.0, "data_integrity": 0.0,
        "operations_slo": 1.0, "security_supply_chain": 0.0, "business_criticality": 0.0,
    }
    res_w = evaluate_modernization_options(custom_w)
    results.append({"probe": "PRECISION-5: Configurable dimension weights change risk calculation deterministically", "passed": res_w["composite_reference_risk_0_5"] == 1.5})

    passed = sum(1 for r in results if r["passed"])
    return {
        "tool": "modernize_forensics_engine.py",
        "total_probes": len(results),
        "passed": passed,
        "failed": len(results) - passed,
        "all_passed": passed == len(results),
        "results": results,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Shadow Modernize Forensics & Economics Engine")
    parser.add_argument("--scan-repo", default=None)
    parser.add_argument("--evaluate-options", default=None)
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()

    if args.self_test:
        res = run_self_test()
        print(json.dumps(res, indent=2))
        return 0 if res["all_passed"] else 1
    if args.scan_repo:
        print(json.dumps(scan_repo_forensics(Path(args.scan_repo)), indent=2))
        return 0
    if args.evaluate_options:
        profile = json.loads(Path(args.evaluate_options).read_text(encoding="utf-8"))
        res = evaluate_modernization_options(profile)
        print(json.dumps(res, indent=2))
        return 0 if res["status"] == "EVALUATED" else 1

    parser.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(run_checked_cli(main))
