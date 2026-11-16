#!/usr/bin/env python3
"""
Shadow Realtime Transport & Revocation Verifier (realtime_transport_verifier.py)

Deterministic verifier for WebSocket/SSE guarantees:
1. Mid-stream token revocation / ACL downgrade MUST stop unauthorized event delivery
2. Resumption cursors & sequence deduplication prevent lost or duplicate frames
3. Bounded slow-consumer queues & shared broker fan-out prevent multi-node/OOM failures
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


def verify_realtime_session(spec: dict[str, Any]) -> dict[str, Any]:
    errors: list[str] = []
    if not isinstance(spec, dict) or not spec:
        return {"status": "FAIL", "valid": False, "errors": ["Realtime spec must be a non-empty JSON object."]}

    if not spec.get("supports_cursor_resume"):
        errors.append("Missing resumption cursor ('Last-Event-ID' or monotonic sequence) for disconnect recovery.")
    if not spec.get("enforces_token_revocation_mid_stream"):
        errors.append("Security violation: live connection does not revoke or halt delivery on token/ACL revocation.")
    if not spec.get("has_bounded_slow_consumer_queue"):
        errors.append("Backpressure violation: unbounded outbound queue risks OOM under slow consumers.")
    if not spec.get("uses_shared_pubsub_broker"):
        errors.append("Scaling violation: multi-instance fan-out requires shared broker (Redis Pub/Sub / NATS / Kafka), not local memory only.")
    if not spec.get("reconnect_backoff_has_jitter"):
        errors.append("Thundering-herd violation: client reconnect backoff lacks jitter.")

    # Simulate event stream delivery, duplicate frame suppression, and post-revocation halt
    seen_seq: set[tuple[str, int]] = set()
    delivered = 0
    unauthorized_leaked = 0
    for ev in spec.get("events", []):
        if ev.get("after_revocation"):
            if not spec.get("enforces_token_revocation_mid_stream") or ev.get("delivered_anyway"):
                unauthorized_leaked += 1
            continue
        key = (str(ev.get("stream", "")), int(ev.get("seq", 0)))
        if key in seen_seq:
            continue
        seen_seq.add(key)
        delivered += 1

    if unauthorized_leaked > 0:
        errors.append(f"Authorization failure: {unauthorized_leaked} event(s) leaked to revoked/expired connection.")

    return {
        "skill_id": "shadow-realtime",
        "record_id": spec.get("record_id", "RT-UNASSIGNED"),
        "status": "PASS" if not errors else "FAIL",
        "valid": len(errors) == 0,
        "deduped_unique_events_delivered": delivered,
        "unauthorized_events_leaked": unauthorized_leaked,
        "errors": errors,
    }


def run_self_test() -> dict[str, Any]:
    results: list[dict[str, Any]] = []

    golden = {
        "record_id": "RT-01",
        "protocol": "SSE",
        "supports_cursor_resume": True,
        "enforces_token_revocation_mid_stream": True,
        "has_bounded_slow_consumer_queue": True,
        "uses_shared_pubsub_broker": True,
        "reconnect_backoff_has_jitter": True,
        "events": [
            {"stream": "alerts:t1", "seq": 1},
            {"stream": "alerts:t1", "seq": 1},
            {"stream": "alerts:t1", "seq": 2},
            {"stream": "alerts:t1", "seq": 3, "after_revocation": True, "delivered_anyway": False},
        ],
    }
    res_ok = verify_realtime_session(golden)
    results.append({"probe": "PRECISION-1: Cursor resume + dedup (2 unique) + zero post-revocation leak passes", "passed": res_ok["valid"] and res_ok["deduped_unique_events_delivered"] == 2 and res_ok["unauthorized_events_leaked"] == 0})

    # §10.1 Must-fail: stale connection receives revoked/unauthorized event
    revoked_leak = json.loads(json.dumps(golden))
    revoked_leak["enforces_token_revocation_mid_stream"] = False
    revoked_leak["events"][3]["delivered_anyway"] = True
    results.append({"probe": "MUST-FAIL-1 (§10.1): Rejects stale socket delivering event after token/ACL revocation", "passed": not verify_realtime_session(revoked_leak)["valid"]})

    no_resume = {**golden, "supports_cursor_resume": False}
    results.append({"probe": "RECALL-1: Blocks missing reconnect cursor / Last-Event-ID", "passed": not verify_realtime_session(no_resume)["valid"]})

    unbounded = {**golden, "has_bounded_slow_consumer_queue": False}
    results.append({"probe": "RECALL-2: Blocks unbounded slow-consumer buffer", "passed": not verify_realtime_session(unbounded)["valid"]})

    results.append({"probe": "BOUNDARY-1: Handles empty dict gracefully", "passed": not verify_realtime_session({})["valid"]})
    results.append({"probe": "PRECISION-2: Deterministic repeat output", "passed": verify_realtime_session(golden) == res_ok})

    passed = sum(1 for r in results if r["passed"])
    return {
        "tool": "realtime_transport_verifier.py",
        "total_probes": len(results),
        "passed": passed,
        "failed": len(results) - passed,
        "all_passed": passed == len(results),
        "results": results,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Shadow Realtime Transport Verifier")
    parser.add_argument("--verify-session", default=None, help="JSON realtime session spec")
    parser.add_argument("--out", default=None, help="Optional output file path")
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()

    if args.self_test:
        out_data = run_self_test()
        exit_code = 0 if out_data["all_passed"] else 1
    elif args.verify_session:
        spec = json.loads(Path(args.verify_session).read_text(encoding="utf-8"))
        out_data = verify_realtime_session(spec)
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
