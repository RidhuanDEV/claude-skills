#!/usr/bin/env python3
"""Deterministic production release readiness & rollback verifier for shadow-release.

Audits release manifests against the 8 Pre-Flight Release Gates:
  1. Quality/tests pass on exact release commit SHA
  2. Security audit clear (0 secrets / 0 reachable criticals)
  3. Staging UAT / Pre-UAT perf status recorded
  4. Recovery point / pre-deploy backup verified
  5. Expand-only migration-before-code ordering (no destructive DDL during rolling deploy)
  6. Environment parity confirmed
  7. Pinned immutable rollback tag/digest (`PREV_TAG`, forbids `:latest`)
  8. SBOM + SLSA provenance artifact present
Plus SemVer major-bump consistency for breaking changes and deterministic canary abort thresholds.
Zero external dependencies (Python stdlib only).
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "shadow-monarch" / "scripts"))
from shadow_input import InvalidInput, run_checked_cli, strict_bool

SEMVER_RE = re.compile(r"^v?(\d+)\.(\d+)\.(\d+)(?:-[0-9A-Za-z.-]+)?(?:\+[0-9A-Za-z.-]+)?$")
FLOATING_TAG_RE = re.compile(r"(?::latest\b|@main\b|@master\b|\blatest\b)", re.IGNORECASE)
DESTRUCTIVE_DDL_RE = re.compile(r"\b(?:DROP\s+(?:TABLE|COLUMN)|ALTER\s+TABLE\s+\S+\s+DROP|TRUNCATE)\b", re.IGNORECASE)


def _parse_semver(tag: str) -> tuple[int, int, int] | None:
    m = SEMVER_RE.match(tag.strip())
    if not m:
        return None
    return (int(m.group(1)), int(m.group(2)), int(m.group(3)))


def check_release_manifest(manifest: Any) -> list[dict[str, str]]:
    """Audit a release readiness manifest across all 8 gates, SemVer, and rollback safety."""
    violations: list[dict[str, str]] = []
    if not isinstance(manifest, dict) or not manifest:
        return [{"code": "EMPTY_MANIFEST", "detail": "Release manifest must be a non-empty JSON object."}]

    # SemVer check
    version = str(manifest.get("version", "")).strip()
    prev_version = str(manifest.get("previous_version", "")).strip()
    cur_sv = _parse_semver(version)
    prev_sv = _parse_semver(prev_version) if prev_version else None
    breaking_changes = strict_bool(manifest.get("has_breaking_changes", False), "has_breaking_changes")
    if cur_sv is None:
        violations.append({"code": "INVALID_SEMVER", "detail": f"Release `version` (`{version}`) is not valid SemVer 2.0.0."})
    elif prev_sv is not None:
        if cur_sv <= prev_sv:
            violations.append({"code": "NON_MONOTONIC_VERSION", "detail": f"`version` ({version}) must exceed `previous_version` ({prev_version})."})
        if breaking_changes and cur_sv[0] <= prev_sv[0]:
            violations.append({
                "code": "BREAKING_CHANGE_WITHOUT_MAJOR_BUMP",
                "detail": f"Release declares `has_breaking_changes: true` but did not bump SemVer MAJOR ({prev_version} -> {version}).",
            })

    # Image / artifact pinning (zero :latest)
    artifact_ref = str(manifest.get("artifact_ref", "")).strip()
    rollback_ref = str(manifest.get("rollback_ref", "")).strip()
    if not artifact_ref or FLOATING_TAG_RE.search(artifact_ref):
        violations.append({"code": "FLOATING_OR_MISSING_ARTIFACT", "detail": f"`artifact_ref` (`{artifact_ref}`) must be an immutable SHA/digest, never `:latest`."})
    if not rollback_ref or FLOATING_TAG_RE.search(rollback_ref):
        violations.append({"code": "FLOATING_OR_MISSING_ROLLBACK", "detail": f"`rollback_ref` (`{rollback_ref}`) must pin the previous immutable tag/digest."})

    # Gate checks
    gates = manifest.get("gates", {})
    if not isinstance(gates, dict):
        violations.append({"code": "MISSING_GATES_OBJECT", "detail": "`gates` must be a JSON object."})
        return violations

    required_bool_gates = [
        ("quality_and_tests_passed", "GATE_1_QUALITY_BLOCKED", "Gate 1 (Quality & Tests on release SHA) not verified."),
        ("security_audit_passed", "GATE_2_SECURITY_BLOCKED", "Gate 2 (Security audit: 0 secrets / 0 reachable criticals) not verified."),
        ("staging_uat_passed", "GATE_3_UAT_BLOCKED", "Gate 3 (Staging UAT / Pre-UAT readiness) not verified."),
        ("backup_or_recovery_point_verified", "GATE_4_BACKUP_BLOCKED", "Gate 4 (Pre-deploy backup / recovery point) not verified."),
        ("env_parity_verified", "GATE_6_ENV_PARITY_BLOCKED", "Gate 6 (Environment parity for new env vars) not verified."),
        ("rollback_command_tested", "GATE_7_ROLLBACK_BLOCKED", "Gate 7 (1-command rollback script) not verified."),
        ("sbom_and_provenance_verified", "GATE_8_SUPPLYCHAIN_BLOCKED", "Gate 8 (CycloneDX/SPDX SBOM & provenance attestation) not verified."),
    ]
    for field, code, msg in required_bool_gates:
        if not strict_bool(gates.get(field, False), f"gates.{field}"):
            violations.append({"code": code, "detail": msg})

    # Gate 5: Migration-before-code & expand-only during rolling deploy
    migration = manifest.get("migration", {})
    if not isinstance(migration, dict):
        raise InvalidInput("migration must be a JSON object.")
    destructive = strict_bool(migration.get("destructive", False), "migration.destructive")
    if strict_bool(migration.get("has_schema_change", False), "migration.has_schema_change"):
        if migration.get("order") != "before_code":
            violations.append({
                "code": "GATE_5_MIGRATION_ORDER_BLOCKED",
                "detail": "Gate 5 requires Expand-Only migrations to run `before_code` so N-1 rollback remains safe.",
            })
        ddl = str(migration.get("sql_preview", ""))
        if destructive or DESTRUCTIVE_DDL_RE.search(ddl):
            violations.append({
                "code": "GATE_5_DESTRUCTIVE_DDL_IN_DEPLOY",
                "detail": "Destructive DDL (`DROP COLUMN`/`DROP TABLE`) breaks N-1 binary rollback; defer to post-drain Contract release.",
            })

    # Canary policy validation (if canary enabled)
    canary = manifest.get("canary", {})
    if not isinstance(canary, dict):
        raise InvalidInput("canary must be a JSON object.")
    if strict_bool(canary.get("enabled", False), "canary.enabled"):
        if str(canary.get("bucketing", "")).lower() != "deterministic_hash":
            violations.append({
                "code": "NON_DETERMINISTIC_CANARY",
                "detail": "Canary rollout must use `deterministic_hash` bucketing (never per-request Math.random).",
            })
        if not canary.get("abort_thresholds"):
            violations.append({
                "code": "CANARY_MISSING_ABORT_THRESHOLDS",
                "detail": "Canary rollout must define objective `abort_thresholds` (5xx delta, latency SLO, min sample size).",
            })

    return violations


def run_self_test() -> dict[str, Any]:
    probes: list[tuple[str, bool]] = []

    golden = {
        "version": "1.4.0",
        "previous_version": "1.3.2",
        "has_breaking_changes": False,
        "artifact_ref": "ghcr.io/org/api@sha256:abc123def456",
        "rollback_ref": "ghcr.io/org/api@sha256:999888777666",
        "gates": {
            "quality_and_tests_passed": True,
            "security_audit_passed": True,
            "staging_uat_passed": True,
            "backup_or_recovery_point_verified": True,
            "env_parity_verified": True,
            "rollback_command_tested": True,
            "sbom_and_provenance_verified": True,
        },
        "migration": {"has_schema_change": True, "order": "before_code", "destructive": False, "sql_preview": "ALTER TABLE orders ADD COLUMN note text;"},
        "canary": {"enabled": True, "bucketing": "deterministic_hash", "abort_thresholds": {"max_5xx_delta_pct": 0.5, "min_samples": 500}},
    }
    probes.append(("PRECISION-1: Complete 8-gate Expand-Only release with pinned digests & deterministic canary passes", len(check_release_manifest(golden)) == 0))

    # RECALL-1: Breaking change without MAJOR SemVer bump rejected
    bad_sv = dict(golden, version="1.4.0", previous_version="1.3.2", has_breaking_changes=True)
    probes.append(("RECALL-1: Rejects breaking change without MAJOR version bump", any(v["code"] == "BREAKING_CHANGE_WITHOUT_MAJOR_BUMP" for v in check_release_manifest(bad_sv))))

    # RECALL-2: Floating :latest artifact/rollback tag rejected
    bad_tag = dict(golden, artifact_ref="ghcr.io/org/api:latest", rollback_ref="ghcr.io/org/api:latest")
    codes = {v["code"] for v in check_release_manifest(bad_tag)}
    probes.append(("RECALL-2: Rejects floating :latest artifact and rollback tags", {"FLOATING_OR_MISSING_ARTIFACT", "FLOATING_OR_MISSING_ROLLBACK"}.issubset(codes)))

    # RECALL-3: Destructive DROP COLUMN during rolling deploy & wrong migration order rejected
    bad_mig = dict(golden, migration={"has_schema_change": True, "order": "after_code", "sql_preview": "ALTER TABLE orders DROP COLUMN legacy_code;"})
    codes = {v["code"] for v in check_release_manifest(bad_mig)}
    probes.append(("RECALL-3: Blocks destructive DDL and after_code migration order", {"GATE_5_MIGRATION_ORDER_BLOCKED", "GATE_5_DESTRUCTIVE_DDL_IN_DEPLOY"}.issubset(codes)))

    # RECALL-4: Missing Gate 8 SBOM & Gate 4 backup blocks release
    bad_gates = dict(golden, gates=dict(golden["gates"], backup_or_recovery_point_verified=False, sbom_and_provenance_verified=False))
    codes = {v["code"] for v in check_release_manifest(bad_gates)}
    probes.append(("RECALL-4: Blocks release missing Gate 4 backup or Gate 8 SBOM/provenance", {"GATE_4_BACKUP_BLOCKED", "GATE_8_SUPPLYCHAIN_BLOCKED"}.issubset(codes)))

    # RECALL-5: Random canary bucketing & missing abort thresholds rejected
    bad_canary = dict(golden, canary={"enabled": True, "bucketing": "random", "abort_thresholds": {}})
    codes = {v["code"] for v in check_release_manifest(bad_canary)}
    probes.append(("RECALL-5: Rejects non-deterministic canary & missing abort thresholds", {"NON_DETERMINISTIC_CANARY", "CANARY_MISSING_ABORT_THRESHOLDS"}.issubset(codes)))

    # BOUNDARY-1: Empty manifest rejected gracefully
    v_empty = check_release_manifest({})
    probes.append(("BOUNDARY-1: Rejects empty release manifest gracefully", len(v_empty) == 1 and v_empty[0]["code"] == "EMPTY_MANIFEST"))

    passed = sum(1 for _, ok in probes if ok)
    return {
        "tool": "release_readiness_verifier.py",
        "total_probes": len(probes),
        "passed": passed,
        "failed": len(probes) - passed,
        "all_passed": passed == len(probes),
        "results": [{"probe": name, "passed": ok} for name, ok in probes],
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Verify production release readiness gates, SemVer, migration order, and rollback safety.")
    parser.add_argument("--self-test", action="store_true", help="Run built-in precision/recall falsification probes.")
    parser.add_argument("--check-release", type=Path, help="Path to JSON release readiness manifest.")
    args = parser.parse_args(argv)

    if args.self_test:
        report = run_self_test()
        print(json.dumps(report, indent=2))
        return 0 if report["all_passed"] else 1

    if not args.check_release:
        parser.print_help()
        return 2

    data = json.loads(args.check_release.read_text(encoding="utf-8"))
    violations = check_release_manifest(data)
    output = {"status": "PASS" if not violations else "BLOCKED", "violation_count": len(violations), "violations": violations}
    print(json.dumps(output, indent=2))
    return 0 if not violations else 1


if __name__ == "__main__":
    sys.exit(run_checked_cli(main))
