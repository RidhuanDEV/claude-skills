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
import hashlib
from datetime import date
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


def text_field(value: object, field: str) -> str:
    if not isinstance(value, str) or not value or value != value.strip():
        raise ValueError(f"{field} must be a nonempty canonical string.")
    return value


def string_list(value: object, field: str) -> list[str]:
    if not isinstance(value, list):
        raise ValueError(f"{field} must be a list.")
    return [text_field(item, field) for item in value]


def calendar_date(value: object, field: str) -> date:
    parsed = date.fromisoformat(text_field(value, field))
    if parsed.isoformat() != value:
        raise ValueError(f"{field} requires YYYY-MM-DD.")
    return parsed


def inventory(records: object, platform: str | None) -> tuple[set[tuple], list[tuple]]:
    if not isinstance(records, list) or not records:
        raise ValueError("Package inventory must be a nonempty list.")
    included, excluded = set(), []
    for component in records:
        if not isinstance(component, dict):
            raise ValueError("Package entries must be objects.")
        name = text_field(component.get("name"), "name")
        version = text_field(component.get("version"), "version")
        ecosystem = text_field(component.get("ecosystem", "unspecified"), "ecosystem")
        scope = component.get("scope", "runtime")
        if scope not in ("runtime", "dev", "optional"):
            raise ValueError("Unknown package scope.")
        key = (ecosystem, name, version, scope)
        platforms = string_list(component.get("platforms", []), "platforms")
        if scope == "optional" and platform and platforms and platform not in platforms:
            excluded.append(key)
        else:
            included.add(key)
    return included, excluded


def verify_supplychain_manifest(spec: dict[str, Any], *, policy=None, receipt=None,
                               artifact_digest=None, as_of=None) -> dict[str, Any]:
    """Reconcile a normalized inventory with evidence supplied by the consumer's trusted CI."""
    errors, missing, exclusions = [], [], []
    provenance = "UNVERIFIED"
    try:
        if not isinstance(spec, dict):
            raise ValueError("Manifest must be an object.")
        if spec.get("lockfile_synced") is not True:
            errors.append("A synchronized lockfile requires a true boolean.")
        if policy is not None and not isinstance(policy, dict):
            raise ValueError("Consumer policy must be an object.")
        platform = text_field(policy["platform"], "platform") if policy and "platform" in policy else None
        packages, skip_lock = inventory(spec.get("lockfile_packages"), platform)
        components, skip_sbom = inventory(spec.get("sbom_components"), platform)
        exclusions = sorted(set(skip_lock + skip_sbom))
        if not packages or packages != components:
            errors.append(f"Inventory differs: missing={sorted(packages-components)}, extra={sorted(components-packages)}.")
        for _, name, _, _ in sorted(packages):
            for pop in sorted(POPULAR_ECOSYSTEM_LIBS):
                if _edit_distance_1(name.split("/")[-1].lower(), pop):
                    errors.append(f"Review dependency origin: '{name}' resembles '{pop}'.")
        for action in string_list(spec.get("ci_actions", []), "ci_actions"):
            if not SHA_40_RE.search(action):
                errors.append(f"Unpinned CI action: {action}")
        if "container_base" in spec and not IMAGE_DIGEST_RE.search(text_field(spec["container_base"], "container_base")):
            errors.append("Container must be pinned by digest.")
        waivers = spec.get("waivers", [])
        if not isinstance(waivers, list):
            raise ValueError("waivers must be a list.")
        for waiver in waivers:
            if not isinstance(waiver, dict):
                raise ValueError("waiver requires an object.")
            cve = text_field(waiver.get("cve_id"), "cve_id")
            expiry = calendar_date(waiver.get("expires_at"), "expires_at")
            if as_of is None:
                missing.append("Waiver evaluation requires an independent assessment date.")
            elif expiry < calendar_date(as_of, "as_of"):
                errors.append(f"Waiver expired for {cve}.")
        declared = spec.get("provenance", {})
        if not isinstance(declared, dict):
            raise ValueError("provenance must be an object.")
        if "signer_verified" in declared and declared["signer_verified"] is not True:
            errors.append("Manifest signer declaration is false or malformed.")
        if policy is None or receipt is None or artifact_digest is None:
            missing.append("Provide a consumer policy, trusted verifier receipt and exact release artifact.")
        elif not isinstance(receipt, dict):
            raise ValueError("Verifier receipt must be an object.")
        elif receipt.get("status") in ("OFFLINE", "NOT_RUN"):
            missing.append("CI signature verification was not observed.")
        else:
            if receipt.get("status") != "VERIFIED":
                errors.append("Verifier has no successful result.")
            elif (not isinstance(artifact_digest, str) or len(artifact_digest) != 64
                  or any(c not in "0123456789abcdef" for c in artifact_digest)
                  or receipt.get("subject_sha256") != artifact_digest):
                errors.append("Verified subject differs from release artifact digest.")
            else:
                # Keep issuer and builder paired; independent allowlists would authorize new combinations.
                trusted = policy.get("trusted_builds")
                if not isinstance(trusted, list) or not trusted or not all(isinstance(rule, dict) for rule in trusted):
                    raise ValueError("Supply one or more consumer trust rules.")
                fields = ("issuer", "builder_id", "build_type", "verifier")
                observed = tuple(text_field(receipt.get(key), key) for key in fields)
                rules = {tuple(text_field(rule.get(key), key) for key in fields) for rule in trusted}
                if observed in rules:
                    provenance = "VERIFIED_RECEIPT"
                else:
                    errors.append("Verifier, issuer, builder or build type differs from consumer policy.")
    except (TypeError, ValueError) as exc:
        errors.append(str(exc))
    status = "FAIL" if errors else "INCOMPLETE" if missing else "PASS"
    return {"skill_id": "shadow-supplychain",
            "manifest_id": spec.get("manifest_id", "SC-UNASSIGNED") if isinstance(spec, dict) else "SC-UNASSIGNED",
            "status": status, "valid": status == "PASS", "provenance_status": provenance,
            "platform_exclusions": exclusions, "error_count": len(errors) + len(missing), "errors": errors + missing}


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
    rule = {"issuer": "test-issuer", "builder_id": "test-builder", "build_type": "test-build", "verifier": "fixture"}
    def check(manifest):
        return verify_supplychain_manifest(manifest, policy={"trusted_builds": [rule]},
                    receipt={**rule, "status": "VERIFIED", "subject_sha256": "a" * 64},
                    artifact_digest="a" * 64, as_of="2026-11-16")
    res_ok = check(golden)
    results.append({"probe": "PRECISION-1: Synced SBOM + pinned SHA + verified signer pass", "passed": res_ok["valid"]})

    # §10.1 Must-fail: trusts unverifiable signer or dependency source
    unverified_signer = json.loads(json.dumps(golden))
    unverified_signer["provenance"]["signer_verified"] = False
    results.append({"probe": "MUST-FAIL-1 (§10.1): Rejects unverifiable artifact signer", "passed": not check(unverified_signer)["valid"]})

    # Lookalike typosquatting package
    typo = json.loads(json.dumps(golden))
    typo["lockfile_packages"].append({"name": "1odash", "version": "1.0.0"})
    typo["sbom_components"].append({"name": "1odash", "version": "1.0.0"})
    results.append({"probe": "RECALL-1: Flags typosquatted lookalike package '1odash'", "passed": not check(typo)["valid"]})

    # SBOM mismatch with lockfile
    mismatch = json.loads(json.dumps(golden))
    mismatch["sbom_components"].pop()
    results.append({"probe": "RECALL-2: Rejects SBOM diverging from lockfile", "passed": not check(mismatch)["valid"]})

    # Unpinned CI action or expired waiver
    expired = json.loads(json.dumps(golden))
    expired["ci_actions"] = ["actions/checkout@v4"]
    expired["waivers"] = [{"cve_id": "CVE-2024-9999", "expires_at": "2025-01-01"}]
    res_exp = check(expired)
    results.append({"probe": "RECALL-3: Flags floating action tag & expired waiver", "passed": (not res_exp["valid"]) and len(res_exp["errors"]) >= 2})

    results.append({"probe": "BOUNDARY-1: Handles empty dict gracefully", "passed": not check({})["valid"]})
    results.append({"probe": "PRECISION-2: Deterministic repeat output", "passed": check(golden) == res_ok})

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
    parser.add_argument("--policy", help="Trusted consumer policy JSON")
    parser.add_argument("--receipt", help="Trusted CI verifier result JSON, supplied independently of the manifest")
    parser.add_argument("--artifact", help="Release artifact to hash locally")
    parser.add_argument("--as-of-date", help="Independent waiver assessment date, YYYY-MM-DD")
    parser.add_argument("--out", default=None, help="Optional output file path")
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()

    if args.self_test:
        out_data = run_self_test()
        exit_code = 0 if out_data["all_passed"] else 1
    elif args.verify:
        def read_json(file):
            return json.loads(Path(file).read_text(encoding="utf-8-sig"))
        try:
            digest = None
            if args.artifact:
                with Path(args.artifact).open("rb") as stream:
                    checksum = hashlib.sha256()
                    for block in iter(lambda: stream.read(1024 * 1024), b""):
                        checksum.update(block)
                    digest = checksum.hexdigest()
            out_data = verify_supplychain_manifest(read_json(args.verify),
                policy=read_json(args.policy) if args.policy else None,
                receipt=read_json(args.receipt) if args.receipt else None,
                artifact_digest=digest, as_of=args.as_of_date)
        except (OSError, ValueError) as exc:
            out_data = {"skill_id": "shadow-supplychain", "status": "INCOMPLETE", "valid": False,
                        "provenance_status": "UNVERIFIED", "errors": [str(exc)]}
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
