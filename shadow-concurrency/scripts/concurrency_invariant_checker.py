#!/usr/bin/env python3
"""
Shadow Concurrency Invariant & Replay Checker (concurrency_invariant_checker.py)

Deterministic workflow invariant checker and crash/replay simulator verifying:
1. Durable persistence before broker acknowledgement
2. Idempotent deduplication under crash-after-commit/before-ack replay
3. Mutual exclusion under concurrent double-claim attempts
4. Bounded retries routing poison messages to DLQ
5. Rejection of impossible 'guaranteed_exactly_once_external' claims
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


def simulate_at_least_once_replay(spec: dict[str, Any]) -> dict[str, Any]:
    """Deterministically simulate crash-after-side-effect / concurrent claim / poison DLQ."""
    has_durable_dedup = bool(spec.get("uses_durable_idempotency_store", False))
    ack_before_commit = bool(spec.get("ack_before_durable_commit", False))
    atomic_claim = bool(spec.get("uses_atomic_claim_or_lock", False))
    max_attempts = int(spec.get("max_attempts", 0))
    has_dlq = bool(spec.get("has_dlq", False))
    claims_unassisted_exactly_once = bool(spec.get("claims_unassisted_exactly_once_external", False))

    errors: list[str] = []
    if claims_unassisted_exactly_once:
        errors.append("Forbidden claim: external side effects cannot guarantee unassisted exactly-once without receiver/outbox idempotency.")
    if ack_before_commit:
        errors.append("Data-loss invariant violation: broker ACK executed before durable state commit.")
    if not has_durable_dedup:
        errors.append("Duplicate-side-effect violation: replay after ack failure executes side effect multiple times without durable idempotency store.")
    if not atomic_claim:
        errors.append("Race violation: two concurrent workers can claim the same pending job without CAS or SKIP LOCKED.")
    if max_attempts <= 0 or not has_dlq:
        errors.append("Poison-message violation: workflow lacks bounded max_attempts (>0) + Dead-Letter Queue (DLQ) policy.")

    # Simulate 2 concurrent workers + 1 ack-failure replay
    seen_keys: set[str] = set()
    side_effects_executed = 0
    for delivery in ("worker_1_initial", "worker_2_concurrent_claim", "worker_1_replay_after_ack_fail"):
        key = "job-101"
        if delivery == "worker_2_concurrent_claim" and atomic_claim:
            continue
        if has_durable_dedup:
            if key in seen_keys:
                continue
            seen_keys.add(key)
        side_effects_executed += 1

    # Simulate poison job failing consecutively until max_attempts
    dlq_routed = False
    if max_attempts > 0 and has_dlq:
        attempts = 0
        for _ in range(max_attempts + 2):
            attempts += 1
            if attempts >= max_attempts:
                dlq_routed = True
                break

    if side_effects_executed != 1:
        errors.append(f"Invariant failure: expected 1 logical side effect across replay/race, simulated {side_effects_executed}.")
    if not dlq_routed:
        errors.append("Invariant failure: poison job did not route to DLQ.")

    return {
        "skill_id": "shadow-concurrency",
        "workflow_id": spec.get("workflow_id", "WF-UNASSIGNED"),
        "status": "PASS" if not errors else "FAIL",
        "valid": len(errors) == 0,
        "simulated_side_effects": side_effects_executed,
        "poison_dlq_routed": dlq_routed,
        "delivery_guarantee": "AT_LEAST_ONCE_WITH_IDEMPOTENT_DEDUP" if not errors else "UNSAFE",
        "errors": errors,
    }


def run_self_test() -> dict[str, Any]:
    results: list[dict[str, Any]] = []

    golden = {
        "workflow_id": "WF-NOTIF-OUTBOX",
        "uses_durable_idempotency_store": True,
        "ack_before_durable_commit": False,
        "uses_atomic_claim_or_lock": True,
        "max_attempts": 5,
        "has_dlq": True,
        "claims_unassisted_exactly_once_external": False,
    }
    res_ok = simulate_at_least_once_replay(golden)
    results.append({"probe": "PRECISION-1: Crash/replay + concurrent claim yields 1 logical side effect & DLQ route", "passed": res_ok["valid"] and res_ok["simulated_side_effects"] == 1 and res_ok["poison_dlq_routed"]})

    # §10.1 Must-fail 1: duplicates on replay
    dup_spec = {**golden, "uses_durable_idempotency_store": False}
    results.append({"probe": "MUST-FAIL-1 (§10.1): Rejects workflow that duplicates side effects on replay", "passed": not simulate_at_least_once_replay(dup_spec)["valid"]})

    # §10.1 Must-fail 2: loses work after ack before commit
    early_ack = {**golden, "ack_before_durable_commit": True}
    results.append({"probe": "MUST-FAIL-2 (§10.1): Rejects ACK before durable state commit", "passed": not simulate_at_least_once_replay(early_ack)["valid"]})

    # §10.1 Must-fail 3: claims impossible unassisted exactly-once external effect
    false_eo = {**golden, "claims_unassisted_exactly_once_external": True}
    results.append({"probe": "MUST-FAIL-3 (§10.1): Rejects false unassisted exactly-once external delivery claim", "passed": not simulate_at_least_once_replay(false_eo)["valid"]})

    # Missing DLQ / infinite retry
    no_dlq = {**golden, "has_dlq": False, "max_attempts": 0}
    results.append({"probe": "RECALL-1: Blocks unbounded poison retry without DLQ", "passed": not simulate_at_least_once_replay(no_dlq)["valid"]})

    results.append({"probe": "BOUNDARY-1: Handles empty dict without crash", "passed": not simulate_at_least_once_replay({})["valid"]})
    results.append({"probe": "PRECISION-2: Deterministic repeat output", "passed": simulate_at_least_once_replay(golden) == res_ok})

    passed = sum(1 for r in results if r["passed"])
    return {
        "tool": "concurrency_invariant_checker.py",
        "total_probes": len(results),
        "passed": passed,
        "failed": len(results) - passed,
        "all_passed": passed == len(results),
        "results": results,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Shadow Concurrency Invariant Checker")
    parser.add_argument("--verify-workflow", default=None, help="JSON workflow definition path")
    parser.add_argument("--out", default=None, help="Optional output file path")
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()

    if args.self_test:
        out_data = run_self_test()
        exit_code = 0 if out_data["all_passed"] else 1
    elif args.verify_workflow:
        spec = json.loads(Path(args.verify_workflow).read_text(encoding="utf-8"))
        out_data = simulate_at_least_once_replay(spec)
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
