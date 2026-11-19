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


def identifier(value, field):
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field} must be a nonempty string.")
    return value


def number(value, field):
    if type(value) is not int or value < 0:
        raise ValueError(f"{field} must be a nonnegative integer.")
    return value


def boolean(value, field):
    if type(value) is not bool:
        raise ValueError(f"{field} must be a boolean.")
    return value


def verify_realtime_session(spec: dict[str, Any]) -> dict[str, Any]:
    """Replay an ordered observation of logical subscriptions through disconnects and ACL changes."""
    errors, missing = [], []
    applied = duplicate = unauthorized = 0
    emitted = {}
    clients = {}
    coverage = {"resume": 0, "replayed_duplicate": 0, "post_revocation_block": 0,
                "snapshot": 0, "queue_observations": 0, "cross_node_delivery": 0}
    try:
        if not isinstance(spec, dict):
            raise ValueError("Session requires a JSON object.")
        if "trace_version" not in spec:
            # Flat v1 events do not record actual client application, reconnect and ACL transitions.
            missing.append("Legacy session has no ordered v2 transport observations.")
        elif type(spec["trace_version"]) is not int or spec["trace_version"] != 2:
            raise ValueError("Unsupported trace_version.")
        else:
            events = spec.get("events")
            if not isinstance(events, list) or not events:
                raise ValueError("Trace needs a nonempty events array.")
            topology = spec.get("topology")
            if topology not in ("single_node", "multi_node"):
                raise ValueError("Declare the deployment topology.")
            capacity = number(spec.get("queue_capacity"), "queue_capacity")
            if capacity == 0:
                raise ValueError("Queue capacity must be positive.")
            for index, event in enumerate(events):
                if not isinstance(event, dict):
                    raise ValueError(f"Event {index} requires an object.")
                kind = identifier(event.get("type"), "type")
                if kind == "emit":
                    key = (identifier(event.get("tenant"), "tenant"), identifier(event.get("stream"), "stream"),
                           number(event.get("seq"), "seq"))
                    source = identifier(event.get("node"), "node")
                    if key in emitted:
                        raise ValueError(f"Ambiguous repeated emission for {key}.")
                    emitted[key] = source
                    continue
                cid = identifier(event.get("connection"), "connection")
                if kind == "connect":
                    if cid in clients:
                        raise ValueError("Use resume for an existing logical subscription.")
                    clients[cid] = {"tenant": identifier(event.get("tenant"), "tenant"),
                                    "stream": identifier(event.get("stream"), "stream"),
                                    "node": identifier(event.get("node"), "node"),
                                    "cursor": number(event.get("cursor"), "cursor"),
                                    "online": True, "authorized": False, "revoked": False,
                                    "snapshot": False, "resumed": False, "seen": set(), "applied": False}
                    continue
                if cid not in clients:
                    raise ValueError(f"Unknown logical connection at event {index}.")
                state = clients[cid]
                if kind == "revoke":
                    if not state["authorized"]:
                        raise ValueError("Revocation needs an observed grant.")
                    state["authorized"], state["revoked"] = False, True
                    continue
                if kind == "resume":
                    if state["online"]:
                        raise ValueError("Resume requires an observed disconnect.")
                    cursor = number(event.get("cursor"), "cursor")
                    earliest = number(event.get("earliest_retained"), "earliest_retained")
                    if cursor != state["cursor"]:
                        raise ValueError("Resume cursor differs from last acknowledged state.")
                    state.update(online=True, authorized=False, resumed=True,
                                 node=identifier(event.get("node"), "node"), snapshot=earliest > cursor + 1,
                                 earliest=earliest)
                    coverage["resume"] += 1
                    continue
                if not state["online"]:
                    raise ValueError(f"{kind} on disconnected client.")
                if kind == "authorize":
                    if event.get("tenant") != state["tenant"] or event.get("stream") != state["stream"]:
                        raise ValueError("Grant scope differs from the logical subscription.")
                    state.update(authorized=True, revoked=False)
                elif kind == "disconnect":
                    state["online"] = False
                elif kind == "snapshot":
                    cursor = number(event.get("cursor"), "cursor")
                    if (not state["authorized"] or not state["snapshot"] or cursor < state["earliest"] - 1
                            or event.get("tenant") != state["tenant"] or event.get("stream") != state["stream"]):
                        raise ValueError("Unexpected, stale or unauthorized snapshot.")
                    state.update(snapshot=False, cursor=cursor)
                    coverage["snapshot"] += 1
                elif kind == "queue":
                    depth = number(event.get("depth"), "depth")
                    if depth > capacity:
                        errors.append("Queue depth exceeded the per-client limit.")
                    coverage["queue_observations"] += 1
                elif kind in ("blocked", "deliver"):
                    key = (identifier(event.get("tenant"), "tenant"), identifier(event.get("stream"), "stream"),
                           number(event.get("seq"), "seq"))
                    if key not in emitted:
                        raise ValueError("Delivery decision lacks an observed emission.")
                    same_scope = key[:2] == (state["tenant"], state["stream"])
                    if kind == "blocked":
                        if same_scope and state["revoked"] and state["applied"]:
                            coverage["post_revocation_block"] += 1
                        continue
                    if not state["authorized"] or not same_scope:
                        unauthorized += 1
                        errors.append("Observed delivery outside authorized subscription.")
                        continue
                    if state["snapshot"]:
                        errors.append("Stream needs a snapshot before delivery.")
                        continue
                    did_apply = boolean(event.get("applied"), "applied")
                    if key in state["seen"]:
                        duplicate += 1
                        if did_apply:
                            errors.append("Client applied a duplicate frame.")
                        elif state["resumed"]:
                            coverage["replayed_duplicate"] += 1
                        continue
                    if key[2] != state["cursor"] + 1 or not did_apply:
                        errors.append("Sequence gap, stale frame or unaccounted client drop.")
                        continue
                    applied += 1
                    state["applied"] = True
                    state["seen"].add(key)
                    state["cursor"] = key[2]
                    if emitted[key] != state["node"]:
                        coverage["cross_node_delivery"] += 1
                else:
                    raise ValueError(f"Unknown event type {kind}.")
            if any(state["snapshot"] for state in clients.values()):
                missing.append("An expired cursor has no observed resync.")
            for requirement in ("resume", "replayed_duplicate", "post_revocation_block", "queue_observations"):
                if not coverage[requirement]:
                    missing.append(f"No observation for {requirement}.")
            if topology == "multi_node" and not coverage["cross_node_delivery"]:
                missing.append("No cross-node fan-out observation.")
    except ValueError as exc:
        errors.append(str(exc))
    status = "FAIL" if errors else "INCOMPLETE" if missing else "PASS"
    return {"skill_id": "shadow-realtime", "record_id": spec.get("record_id") if isinstance(spec, dict) else None,
            "status": status, "valid": status == "PASS", "deduped_unique_events_delivered": applied,
            "unauthorized_events_leaked": unauthorized, "duplicates_observed": duplicate,
            "coverage": coverage, "errors": errors + missing}


def run_self_test() -> dict[str, Any]:
    events = [
        {"type": "connect", "tenant": "t", "stream": "alerts", "node": "A", "cursor": 9},
        {"type": "authorize", "tenant": "t", "stream": "alerts"},
        {"type": "emit", "tenant": "t", "stream": "alerts", "seq": 10, "node": "A"},
        {"type": "deliver", "tenant": "t", "stream": "alerts", "seq": 10, "applied": True},
        {"type": "disconnect"},
        {"type": "resume", "cursor": 10, "earliest_retained": 10, "node": "B"},
        {"type": "authorize", "tenant": "t", "stream": "alerts"},
        {"type": "deliver", "tenant": "t", "stream": "alerts", "seq": 10, "applied": False},
        {"type": "emit", "tenant": "t", "stream": "alerts", "seq": 11, "node": "A"},
        {"type": "deliver", "tenant": "t", "stream": "alerts", "seq": 11, "applied": True},
        {"type": "queue", "depth": 1},
        {"type": "revoke"},
        {"type": "emit", "tenant": "t", "stream": "alerts", "seq": 12, "node": "A"},
        {"type": "blocked", "tenant": "t", "stream": "alerts", "seq": 12},
    ]
    events = [dict(event, connection="user1") for event in events]
    golden = {"trace_version": 2, "topology": "multi_node", "queue_capacity": 1, "events": events}
    def altered(index, **fields):
        return {**golden, "events": [dict(event, **fields) if i == index else event for i, event in enumerate(events)]}
    probes = [
        ("resumed seq 10,10,11 across nodes", golden, "PASS"),
        ("single node needs no broker", {**golden, "topology": "single_node",
         "events": [dict(event, node="A") if "node" in event else event for event in events]}, "PASS"),
        ("no delivery to revoked client", altered(13, type="deliver", applied=True), "FAIL"),
        ("duplicate application", altered(7, applied=True), "FAIL"),
        ("overflow", altered(10, depth=2), "FAIL"),
        ("expired cursor while sending old frame", altered(5, earliest_retained=20), "FAIL"),
        ("stale evidence missing revocation check", {**golden, "events": events[:-1]}, "INCOMPLETE"),
        ("legacy declarations alone", {"supports_cursor_resume": "false"}, "INCOMPLETE"),
        ("bad boolean", altered(3, applied="false"), "FAIL"),
        ("tenant mismatch", altered(6, tenant="other"), "FAIL"),
    ]
    results = []
    for name, trace, expected in probes:
        result = verify_realtime_session(trace)
        ok = result["status"] == expected
        if expected == "PASS":
            ok = ok and result["deduped_unique_events_delivered"] == 2
        results.append({"probe": name, "expected": expected, "observed": result["status"], "passed": ok})
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
        try:
            spec = json.loads(Path(args.verify_session).read_text(encoding="utf-8-sig"))
            out_data = verify_realtime_session(spec)
        except (OSError, ValueError) as exc:
            out_data = {"status": "INCOMPLETE", "valid": False, "errors": [str(exc)]}
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
