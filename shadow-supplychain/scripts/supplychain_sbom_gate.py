#!/usr/bin/env python3
"""
Shadow Supply-Chain SBOM, Lockfile & Provenance Gate (supplychain_sbom_gate.py)

Deterministic verifier checking:
1. Exact 1:1 reconciliation between lockfile packages and CycloneDX/SPDX SBOM components
2. Lookalike/typosquatting heuristic check against common high-risk typos
3. Pinned CI action commit SHAs & pinned container SHA-256 digests
4. Signer provenance verification & waiver expiry enforcement
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

SHA_40_RE = re.compile(r"@[0-9a-f]{40}$", re.IGNORECASE)
IMAGE_DIGEST_RE = re.compile(r"@sha256:[0-9a-f]{64}$", re.IGNORECASE)
POPULAR_ECOSYSTEM_LIBS = {"express", "lodash", "react", "axios", "requests", "pydantic", "fastapi", "chalk"}


def _edit_distance_1(a: str, b: str) -> bool:
    if a == b or abs(len(a) - len(b)) > 1:
        return False
    if len(a) == len(b):
        return sum(1 for x, y in zip(a, b) if x != y) == 1
    shorter, longer = (a, b) if len(a) < len(b) else (b, a)
    i = j = diffs = 0
    while i < len(shorter) and j < len(longer):
        if shorter[i] != longer[j]:
            diffs += 1
            if diffs > 1:
                return False
            j += 1
        else:
            i += 1
            j += 1
    return True


def verify_supplychain_manifest(spec: dict[str, Any]) -> dict[str, Any]:
    errors: list[str] = []
    if not isinstance(spec, dict) or not spec:
        return {"status": "FAIL", "valid": False, "errors": ["Supply-chain manifest must be a non-empty JSON object."]}

    if not spec.get("lockfile_synced", False):
        errors.append("Stale/unsynced lockfile detected (`lockfile_synced: false`).")

    lock_set = {(str(p["name"]), str(p["version"])) for p in spec.get("lockfile_packages", []) if "name" in p and "version" in p}
    sbom_set = {(str(c["name"]), str(c["version"])) for c in spec.get("sbom_components", []) if "name" in c and "version" in c}
    if not lock_set or not sbom_set:
        errors.append("Both 'lockfile_packages' and 'sbom_components' must be non-empty.")
    elif lock_set != sbom_set:
        missing_in_sbom = sorted(lock_set - sbom_set)
        extra_in_sbom = sorted(sbom_set - lock_set)
        errors.append(f"SBOM/lockfile mismatch: missing_in_sbom={missing_in_sbom}, extra_in_sbom={extra_in_sbom}.")

    # Typosquatting lookalike check
    for name, _ in lock_set:
        base = name.split("/")[-1].lower()
        for pop in POPULAR_ECOSYSTEM_LIBS:
            if _edit_distance_1(base, pop):
                errors.append(f"Potential lookalike/typosquatted dependency detected: '{name}' is edit-distance 1 from '{pop}'.")

    # Pinned CI actions
    for act in spec.get("ci_actions", []):
        if not SHA_40_RE.search(str(act)):
            errors.append(f"Unpinned CI action reference '{act}'; require 40-char commit SHA.")

    base_img = str(spec.get("container_base", "")).strip()
    if base_img and not IMAGE_DIGEST_RE.search(base_img):
        errors.append(f"Unpinned container base '{base_img}'; require immutable @sha256:<64-hex> digest.")

    prov = spec.get("provenance", {})
    if not isinstance(prov, dict) or not prov.get("signer_verified", False):
        errors.append("Provenance gate failure: artifact signer is unverified (`signer_verified: false`).")

    as_of = str(spec.get("as_of_date", "2026-11-16"))
    for w in spec.get("waivers", []):
        exp = str(w.get("expires_at", ""))
        if not exp or exp < as_of:
            errors.append(f"Expired or undated vulnerability waiver '{w.get('cve_id', 'UNKNOWN')}' (expires_at={exp} < {as_of}).")

    return {
        "skill_id": "shadow-supplychain",
        "manifest_id": spec.get("manifest_id", "SC-UNASSIGNED"),
        "status": "PASS" if not errors else "FAIL",
        "valid": len(errors) == 0,
        "error_count": len(errors),
        "errors": errors,
    }


def run_self_test() -> dict[str, Any]:
    results: list[dict[str, Any]] = []

    golden = {
        "manifest_id": "SC-01",
        "as_of_date": "2026-11-16",
        "lockfile_synced": True,
        "lockfile_packages": [{"name": "express", "version": "4.21.2"}, {"name": "zod", "version": "3.24.0"}],
        "sbom_components": [{"name": "express", "version": "4.21.2"}, {"name": "zod", "version": "3.24.0"}],
        "ci_actions": ["actions/checkout@b4ffde65f46336ab88eb53be808477a3936bae11"],
        "container_base": "node:22-alpine@sha256:" + ("a" * 64),
        "provenance": {"signer_verified": True, "slsa_level": "SLSA_BUILD_L2"},
        "waivers": [{"cve_id": "CVE-2025-0001", "expires_at": "2026-12-31"}],
    }
    res_ok = verify_supplychain_manifest(golden)
    results.append({"probe": "PRECISION-1: Synced SBOM + pinned SHA + verified signer pass", "passed": res_ok["valid"]})

    # §10.1 Must-fail: trusts unverifiable signer or dependency source
    unverified_signer = json.loads(json.dumps(golden))
    unverified_signer["provenance"]["signer_verified"] = False
    results.append({"probe": "MUST-FAIL-1 (§10.1): Rejects unverifiable artifact signer", "passed": not verify_supplychain_manifest(unverified_signer)["valid"]})

    # Lookalike typosquatting package
    typo = json.loads(json.dumps(golden))
    typo["lockfile_packages"].append({"name": "1odash", "version": "1.0.0"})
    typo["sbom_components"].append({"name": "1odash", "version": "1.0.0"})
    results.append({"probe": "RECALL-1: Flags typosquatted lookalike package '1odash'", "passed": not verify_supplychain_manifest(typo)["valid"]})

    # SBOM mismatch with lockfile
    mismatch = json.loads(json.dumps(golden))
    mismatch["sbom_components"].pop()
    results.append({"probe": "RECALL-2: Rejects SBOM diverging from lockfile", "passed": not verify_supplychain_manifest(mismatch)["valid"]})

    # Unpinned CI action or expired waiver
    expired = json.loads(json.dumps(golden))
    expired["ci_actions"] = ["actions/checkout@v4"]
    expired["waivers"] = [{"cve_id": "CVE-2024-9999", "expires_at": "2025-01-01"}]
    res_exp = verify_supplychain_manifest(expired)
    results.append({"probe": "RECALL-3: Flags floating action tag & expired waiver", "passed": (not res_exp["valid"]) and len(res_exp["errors"]) >= 2})

    results.append({"probe": "BOUNDARY-1: Handles empty dict gracefully", "passed": not verify_supplychain_manifest({})["valid"]})
    results.append({"probe": "PRECISION-2: Deterministic repeat output", "passed": verify_supplychain_manifest(golden) == res_ok})

    passed = sum(1 for r in results if r["passed"])
    return {
        "tool": "supplychain_sbom_gate.py",
        "total_probes": len(results),
        "passed": passed,
        "failed": len(results) - passed,
        "all_passed": passed == len(results),
        "results": results,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Shadow Supply-Chain SBOM & Provenance Gate")
    parser.add_argument("--verify", default=None, help="JSON supply-chain manifest")
    parser.add_argument("--out", default=None, help="Optional output file path")
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()

    if args.self_test:
        out_data = run_self_test()
        exit_code = 0 if out_data["all_passed"] else 1
    elif args.verify:
        spec = json.loads(Path(args.verify).read_text(encoding="utf-8"))
        out_data = verify_supplychain_manifest(spec)
        exit_code = 0 if out_data["valid"] else 1
    else:
        parser.print_help()
        return 0

    rendered = json.dumps(out_data, indent=2)
    if args.out:
        Path(args.out).write_text(rendered + "\n", encoding="utf-8")
    print(rendered)
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
