#!/usr/bin/env python3
"""
Shadow Debug Hypothesis & Red-Green Evidence Gate (debug_hypothesis_gate.py)

Deterministic verifier ensuring debug reports distinguish symptom from root cause,
evaluate competing hypotheses with falsification, prove red-before/green-after tests,
and redact secrets/DSN credentials before reporting PASS.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

SECRET_LEAK_RE = re.compile(
    r"(?:postgres(?:ql)?://[^:\s]+:[^@\s]+@|Bearer\s+[A-Za-z0-9._-]{16,}|-----BEGIN\s+(?:RSA\s+)?PRIVATE\s+KEY-----|\bAKIA[0-9A-Z]{16}\b)",
    re.IGNORECASE,
)


def validate_debug_report(report: dict[str, Any]) -> dict[str, Any]:
    errors: list[str] = []
    if not isinstance(report, dict) or not report:
        return {"status": "FAIL", "valid": False, "errors": ["Report must be a non-empty JSON object."]}

    symptom = str(report.get("symptom", "")).strip()
    root_cause = str(report.get("root_cause", "")).strip()
    if not symptom or not root_cause:
        errors.append("Both 'symptom' and 'root_cause' must be explicitly non-empty.")
    elif symptom.lower() == root_cause.lower():
        errors.append("'root_cause' merely repeats 'symptom'; causal mechanism required.")

    hypotheses = report.get("hypotheses_tested", [])
    if not isinstance(hypotheses, list) or len(hypotheses) < 2:
        errors.append("Requires at least 2 competing 'hypotheses_tested' to prevent premature single-log bias.")
    else:
        has_falsification = any(str(h.get("disconfirming_observation", "")).strip() for h in hypotheses if isinstance(h, dict))
        has_confirmed = any(str(h.get("status", "")).upper() == "CONFIRMED" for h in hypotheses if isinstance(h, dict))
        if not has_falsification:
            errors.append("At least one hypothesis must record a disconfirming observation / falsification probe.")
        if not has_confirmed:
            errors.append("At least one hypothesis must be marked CONFIRMED with probe evidence.")

    evidence = report.get("evidence", [])
    before_fail = any(
        isinstance(e, dict) and e.get("phase") == "before_fix" and int(e.get("exit_code", 0)) != 0 and str(e.get("command", "")).strip()
        for e in evidence
    )
    after_pass = any(
        isinstance(e, dict) and e.get("phase") == "after_fix" and int(e.get("exit_code", -1)) == 0 and str(e.get("command", "")).strip()
        for e in evidence
    )
    if not before_fail:
        if not str(report.get("reproduction_infeasible_reason", "")).strip():
            errors.append("Missing failing-before-fix regression test evidence (`phase: before_fix`, `exit_code != 0`).")
    if not after_pass:
        errors.append("Missing passing-after-fix verification evidence (`phase: after_fix`, `exit_code == 0`).")

    if SECRET_LEAK_RE.search(json.dumps(report)):
        errors.append("Unredacted secret/DSN/token detected in debug report; redact sensitive material.")

    return {
        "skill_id": "shadow-debug",
        "record_id": report.get("record_id", "DBG-UNASSIGNED"),
        "status": "PASS" if not errors else "FAIL",
        "valid": len(errors) == 0,
        "error_count": len(errors),
        "errors": errors,
    }


def run_self_test() -> dict[str, Any]:
    """Run unit, boundary, precision, and §10.1 must-fail tests."""
    results: list[dict[str, Any]] = []

    golden = {
        "record_id": "DBG-001",
        "symptom": "Duplicate email sent when queue worker retries after Redis ack timeout",
        "root_cause": "SMTP side effect ran before durable idempotency key commit in DB",
        "hypotheses_tested": [
            {"id": "H1", "status": "REFUTED", "disconfirming_observation": "SMTP provider logs show 2 distinct client message IDs -> not provider retry"},
            {"id": "H2", "status": "CONFIRMED", "disconfirming_observation": "Injected ack failure triggered worker replay with no idempotency record"},
        ],
        "evidence": [
            {"phase": "before_fix", "command": "pytest tests/test_retry.py", "exit_code": 1},
            {"phase": "after_fix", "command": "pytest tests/test_retry.py", "exit_code": 0},
        ],
    }
    results.append({"probe": "PRECISION-1: Valid red-before/green-after falsified report passes", "passed": validate_debug_report(golden)["valid"]})

    # §10.1 Must-fail: asserts root cause from a single coincidental error log with no falsification or red-green test
    single_log_guess = {
        "record_id": "DBG-BAD-1",
        "symptom": "500 error in checkout",
        "root_cause": "Saw one timeout line in app.log so database is broken",
        "hypotheses_tested": [{"id": "H1", "status": "CONFIRMED"}],
        "evidence": [{"phase": "after_fix", "command": "pytest", "exit_code": 0}],
    }
    res_bad = validate_debug_report(single_log_guess)
    results.append({"probe": "MUST-FAIL-1 (§10.1): Rejects single-hypothesis log guess without disconfirmation or failing-before test", "passed": not res_bad["valid"]})

    # Secret redaction guard
    leaked = json.loads(json.dumps(golden))
    leaked["notes"] = "Connected to postgres://admin:supersecret@prod-db:5432/app"
    results.append({"probe": "RECALL-1: Blocks unredacted DSN password in debug artifact", "passed": not validate_debug_report(leaked)["valid"]})

    # Symptom == root_cause guard
    same = json.loads(json.dumps(golden))
    same["root_cause"] = same["symptom"]
    results.append({"probe": "RECALL-2: Rejects tautology where root_cause duplicates symptom", "passed": not validate_debug_report(same)["valid"]})

    # Empty / malformed input boundary
    results.append({"probe": "BOUNDARY-1: Handles empty dict gracefully without crash", "passed": not validate_debug_report({})["valid"]})

    # Deterministic repeat check
    results.append({"probe": "PRECISION-2: Deterministic identical result on repeated validation", "passed": validate_debug_report(golden) == validate_debug_report(golden)})

    passed = sum(1 for r in results if r["passed"])
    return {
        "tool": "debug_hypothesis_gate.py",
        "total_probes": len(results),
        "passed": passed,
        "failed": len(results) - passed,
        "all_passed": passed == len(results),
        "results": results,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Shadow Debug Hypothesis & Red-Green Gate")
    parser.add_argument("--validate-report", default=None, help="Path to JSON debug report")
    parser.add_argument("--out", default=None, help="Optional output file path")
    parser.add_argument("--self-test", action="store_true", help="Run deterministic test suite")
    args = parser.parse_args()

    out_data: dict[str, Any]
    exit_code = 0
    if args.self_test:
        out_data = run_self_test()
        exit_code = 0 if out_data["all_passed"] else 1
    elif args.validate_report:
        report = json.loads(Path(args.validate_report).read_text(encoding="utf-8"))
        out_data = validate_debug_report(report)
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
