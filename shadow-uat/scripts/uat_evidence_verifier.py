"""Check UAT evidence: batch sign-off against the requirement list, and filter-parameter drift.

Usage:
    python uat_evidence_verifier.py --batch evidence.json
    python uat_evidence_verifier.py --param-drift evidence.json
    python uat_evidence_verifier.py --self-test

Batch evidence: {"expected_ids": ["FR-01", ...], "results": {"FR-01": "PASS", ...}}.
Param-drift evidence: {"param": "status", "expected_value": "PAID",
                       "unfiltered_rows": [...], "filtered_rows": [...]}.
Sign-off is never granted on an empty requirement list or on unexpected result values.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

PASSING = "PASS"


def reconcile_batch(expected_ids: object, results: object) -> dict[str, object]:
    """Sign off only when every expected requirement has exactly the result PASS."""
    if not isinstance(expected_ids, list) or not expected_ids or not all(
        isinstance(item, str) and item.strip() for item in expected_ids
    ):
        return {"signoff_ready": False, "status": "INVALID_INPUT", "reason": "expected_ids must be a non-empty list of IDs."}
    if not isinstance(results, dict) or not all(isinstance(key, str) and isinstance(value, str) for key, value in results.items()):
        return {"signoff_ready": False, "status": "INVALID_INPUT", "reason": "results must map IDs to result strings."}
    expected = set(expected_ids)
    missing = sorted(expected - set(results))
    failed = sorted(key for key, value in results.items() if key in expected and value != PASSING)
    unexpected = sorted(set(results) - expected)
    ready = not missing and not failed
    return {
        "signoff_ready": ready,
        "status": "SIGNOFF_READY" if ready else "INCOMPLETE",
        "missing": missing,
        "failed": failed,
        "unexpected": unexpected,
    }


def check_param_effect(evidence: object) -> dict[str, object]:
    """Detect a filter parameter that the endpoint silently ignores, or a vacuous empty result."""
    if not isinstance(evidence, dict):
        return {"status": "INVALID_INPUT", "reason": "Expected a JSON object."}
    param, value = evidence.get("param"), evidence.get("expected_value")
    unfiltered, filtered = evidence.get("unfiltered_rows"), evidence.get("filtered_rows")
    if not isinstance(param, str) or not param or not isinstance(value, str):
        return {"status": "INVALID_INPUT", "reason": "param and expected_value must be strings."}
    if not isinstance(unfiltered, list) or not isinstance(filtered, list) or not all(
        isinstance(row, dict) for row in (*unfiltered, *filtered)
    ):
        return {"status": "INVALID_INPUT", "reason": "Row lists must contain objects."}
    leaking = [row for row in filtered if row.get(param) != value]
    if leaking:
        return {"status": "DRIFT_IGNORED_QUERY_PARAM", "param": param, "unexpected_rows": len(leaking)}
    matching = [row for row in unfiltered if row.get(param) == value]
    if not filtered and matching:
        return {"status": "DRIFT_EMPTY_RESULT", "param": param, "expected_rows": len(matching)}
    if not filtered:
        return {"status": "INSUFFICIENT_EVIDENCE", "param": param, "reason": "No rows match, so the filter is untested."}
    if len(filtered) != len(matching):
        return {"status": "DRIFT_ROW_COUNT", "param": param, "expected_rows": len(matching), "returned_rows": len(filtered)}
    return {"status": "VERIFIED", "param": param, "reduced_from": len(unfiltered), "reduced_to": len(filtered)}


def self_test() -> list[str]:
    rows = [{"id": "1", "status": "PAID"}, {"id": "2", "status": "PENDING"}]
    checks = [
        (reconcile_batch(["FR-01", "FR-02"], {"FR-01": "PASS", "FR-02": "PASS"})["status"], "SIGNOFF_READY"),
        (reconcile_batch(["FR-01", "FR-02"], {"FR-01": "PASS"})["status"], "INCOMPLETE"),
        (reconcile_batch([], {})["status"], "INVALID_INPUT"),
        (reconcile_batch(["FR-01"], {"FR-01": "pass"})["status"], "INCOMPLETE"),
        (check_param_effect({"param": "status", "expected_value": "PAID", "unfiltered_rows": rows, "filtered_rows": rows})["status"], "DRIFT_IGNORED_QUERY_PARAM"),
        (check_param_effect({"param": "status", "expected_value": "PAID", "unfiltered_rows": rows, "filtered_rows": [rows[0]]})["status"], "VERIFIED"),
        (check_param_effect({"param": "status", "expected_value": "PAID", "unfiltered_rows": rows, "filtered_rows": []})["status"], "DRIFT_EMPTY_RESULT"),
    ]
    return [f"got {got}, expected {want}" for got, want in checks if got != want]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--batch", type=Path)
    group.add_argument("--param-drift", type=Path)
    group.add_argument("--self-test", action="store_true")
    args = parser.parse_args(argv)
    if args.self_test:
        failures = self_test()
        print(json.dumps({"self_test": "FAIL" if failures else "PASS", "failures": failures}, indent=2))
        return 1 if failures else 0
    path = args.batch or args.param_drift
    try:
        evidence = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        print(json.dumps({"status": "INVALID_INPUT", "reason": str(error)}))
        return 1
    if args.batch:
        result = reconcile_batch(evidence.get("expected_ids") if isinstance(evidence, dict) else None,
                                 evidence.get("results") if isinstance(evidence, dict) else None)
        print(json.dumps(result, indent=2))
        return 0 if result["signoff_ready"] is True else 1
    result = check_param_effect(evidence)
    print(json.dumps(result, indent=2))
    return 0 if result["status"] == "VERIFIED" else 1


if __name__ == "__main__":
    sys.exit(main())
