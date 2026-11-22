#!/usr/bin/env python3
"""Deterministic Expand-Contract Migration, Backfill & Seed Safety Verifier (L0/L1 offline CLI).

Zero third-party dependencies (Python 3 stdlib only).
Validates:
  - Resumable chunked backfill plans: keyset pagination (no OFFSET), batch bounds,
    pause/replica-lag throttle, interrupt/resume checkpoint, concurrent-writer parity,
    and reconciliation (--check-backfill-plan)
  - Idempotent seed safety: UPSERT semantics & production demo-seed block (--check-seed-safety)
  - Expand-Contract phase safety & contract-phase telemetry gate (--check-migration-phases)
  - Built-in precision & recall self-test probes (--self-test)
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


def check_backfill_plan(plan: dict[str, Any]) -> dict[str, Any]:
    errors: list[str] = []
    warnings: list[str] = []

    pagination = str(plan.get("pagination_mode", "")).strip().lower()
    if pagination != "keyset":
        errors.append(
            f"Backfill must use stable 'keyset' cursor pagination (got '{pagination}'); OFFSET degrades to O(N^2) and skips rows."
        )

    batch_size = int(plan.get("batch_size", 0))
    if batch_size < 100 or batch_size > 10000:
        errors.append(f"Backfill batch_size={batch_size} out of safe bounded range [100, 10000].")

    if int(plan.get("pause_ms", 0)) <= 0 and plan.get("replica_lag_throttle_enabled") is not True:
        errors.append("Backfill must configure positive pause_ms or replica-lag adaptive throttling to avoid replication/lock stalls.")

    if plan.get("resumable_checkpoint_persisted") is not True:
        errors.append("Backfill must persist durable cursor checkpoints so interrupted runs resume idempotently.")

    if plan.get("handles_concurrent_legacy_writers") is not True:
        errors.append(
            "Backfill must account for concurrent mixed-version/legacy writers invalidating rows behind the completed cursor."
        )

    if plan.get("reconciliation_check_included") is not True:
        errors.append("Backfill must verify post-run row-count & checksum/value reconciliation before switching reads.")

    if plan.get("lock_timeout_set") is not True:
        warnings.append("Set explicit lock_timeout & statement_timeout on backfill worker sessions.")

    return {"check": "backfill_plan", "passed": len(errors) == 0, "errors": errors, "warnings": warnings}


def check_migration_phases(phases: dict[str, Any]) -> dict[str, Any]:
    errors: list[str] = []
    warnings: list[str] = []

    if phases.get("destructive_ddl_in_expand_phase") is True:
        errors.append("FORBIDDEN: Destructive DDL (DROP/RENAME/type rewrite) cannot run inside Expand phase while old writers run.")

    if phases.get("mixed_version_rollback_tested") is not True:
        errors.append("Expand phase must verify rollback safety while both old and new application versions write simultaneously.")

    if phases.get("contract_phase_requested") is True:
        if phases.get("zero_legacy_readers_writers_verified") is not True:
            errors.append("CONTRACT_HOLD: Cannot drop old columns/tables until telemetry confirms 0 active legacy readers/writers.")
        if phases.get("explicit_l4_destructive_approval") is not True:
            errors.append("CONTRACT_HOLD: Destructive Contract DDL requires separate explicit L4 Monarch approval.")

    if phases.get("ephemeral_docker_cleanup_enforced") is False:
        errors.append("Ephemeral migration verification containers MUST use --rm --label shadow.ephemeral=true + try/finally cleanup.")

    return {"check": "migration_phases", "passed": len(errors) == 0, "errors": errors, "warnings": warnings}


def check_seed_safety(seed: dict[str, Any]) -> dict[str, Any]:
    errors: list[str] = []

    if seed.get("uses_upsert_idempotency") is not True:
        errors.append("Seed script must use idempotent UPSERT (ON CONFLICT DO UPDATE / DO NOTHING) so reruns never duplicate or fail.")

    if seed.get("demo_seed_blocked_in_production") is not True:
        errors.append("Demo/dummy seed scripts MUST fail closed when NODE_ENV/APP_ENV == 'production'.")

    if seed.get("separates_system_vs_demo_seeds") is not True:
        errors.append("Separate mandatory system reference seeds (roles/regions) from optional demo/dummy fixtures.")

    return {"check": "seed_safety", "passed": len(errors) == 0, "errors": errors}


def run_self_test() -> dict[str, Any]:
    probes: list[tuple[str, bool]] = []

    # PRECISION-1: Safe keyset resumable throttled backfill with legacy-writer parity & reconciliation passes
    r1 = check_backfill_plan(
        {
            "pagination_mode": "keyset",
            "batch_size": 1000,
            "pause_ms": 75,
            "replica_lag_throttle_enabled": True,
            "resumable_checkpoint_persisted": True,
            "handles_concurrent_legacy_writers": True,
            "reconciliation_check_included": True,
            "lock_timeout_set": True,
        }
    )
    probes.append(("PRECISION-1: Safe keyset throttled resumable backfill plan passes", r1["passed"] is True))

    # RECALL-1: OFFSET backfill, 500k batch size, no throttle, no reconciliation rejected
    r2 = check_backfill_plan(
        {
            "pagination_mode": "offset",
            "batch_size": 500000,
            "pause_ms": 0,
            "resumable_checkpoint_persisted": False,
            "handles_concurrent_legacy_writers": False,
            "reconciliation_check_included": False,
        }
    )
    probes.append(("RECALL-1: OFFSET unthrottled giant-batch backfill rejected", r2["passed"] is False and len(r2["errors"]) >= 6))

    # PRECISION-2: Safe Expand phase with mixed-version rollback tested passes
    r3 = check_migration_phases(
        {
            "destructive_ddl_in_expand_phase": False,
            "mixed_version_rollback_tested": True,
            "contract_phase_requested": False,
            "ephemeral_docker_cleanup_enforced": True,
        }
    )
    probes.append(("PRECISION-2: Additive Expand phase with rollback proof passes", r3["passed"] is True))

    # RECALL-2: Contract phase without zero-consumer telemetry or L4 approval blocked
    r4 = check_migration_phases(
        {
            "destructive_ddl_in_expand_phase": False,
            "mixed_version_rollback_tested": True,
            "contract_phase_requested": True,
            "zero_legacy_readers_writers_verified": False,
            "explicit_l4_destructive_approval": False,
        }
    )
    probes.append(("RECALL-2: Premature Contract phase without telemetry & L4 approval held", r4["passed"] is False and len(r4["errors"]) == 2))

    # RECALL-3: Destructive DDL inside Expand phase rejected
    r5 = check_migration_phases(
        {
            "destructive_ddl_in_expand_phase": True,
            "mixed_version_rollback_tested": False,
            "ephemeral_docker_cleanup_enforced": False,
        }
    )
    probes.append(("RECALL-3: Destructive Expand DDL & missing Docker cleanup rejected", r5["passed"] is False and len(r5["errors"]) >= 3))

    # PRECISION-3: Idempotent separated seed blocked in prod passes
    r6 = check_seed_safety(
        {
            "uses_upsert_idempotency": True,
            "demo_seed_blocked_in_production": True,
            "separates_system_vs_demo_seeds": True,
        }
    )
    probes.append(("PRECISION-3: Idempotent system/demo separated seed passes", r6["passed"] is True))

    # RECALL-4: Non-idempotent prod-unsafe demo seed rejected
    r7 = check_seed_safety(
        {
            "uses_upsert_idempotency": False,
            "demo_seed_blocked_in_production": False,
            "separates_system_vs_demo_seeds": False,
        }
    )
    probes.append(("RECALL-4: Non-idempotent demo seed runnable in prod rejected", r7["passed"] is False and len(r7["errors"]) == 3))

    passed = sum(1 for _, ok in probes if ok)
    return {
        "tool": "data_migration_plan_verifier.py",
        "total_probes": len(probes),
        "passed": passed,
        "failed": len(probes) - passed,
        "all_passed": passed == len(probes),
        "results": [{"probe": n, "passed": ok} for n, ok in probes],
    }


def _load_json(path_str: str) -> dict[str, Any]:
    raw = json.loads(Path(path_str).read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise ValueError(f"Expected JSON object in {path_str}")
    return raw


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Offline Data Migration, Backfill & Seed Safety Verifier")
    parser.add_argument("--self-test", action="store_true", help="Run built-in precision & recall probes")
    parser.add_argument("--check-backfill-plan", metavar="PATH", help="Validate chunked backfill plan JSON")
    parser.add_argument("--check-migration-phases", metavar="PATH", help="Validate Expand-Contract phase safety JSON")
    parser.add_argument("--check-seed-safety", metavar="PATH", help="Validate deterministic seed safety JSON")
    args = parser.parse_args(argv)

    if args.self_test:
        res = run_self_test()
        print(json.dumps(res, indent=2))
        return 0 if res["all_passed"] else 1
    if args.check_backfill_plan:
        res = check_backfill_plan(_load_json(args.check_backfill_plan))
        print(json.dumps(res, indent=2))
        return 0 if res["passed"] else 1
    if args.check_migration_phases:
        res = check_migration_phases(_load_json(args.check_migration_phases))
        print(json.dumps(res, indent=2))
        return 0 if res["passed"] else 1
    if args.check_seed_safety:
        res = check_seed_safety(_load_json(args.check_seed_safety))
        print(json.dumps(res, indent=2))
        return 0 if res["passed"] else 1

    parser.print_help()
    return 2


if __name__ == "__main__":
    sys.exit(main())
