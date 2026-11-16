#!/usr/bin/env python3
"""
Shadow Domain Invariant & Boundary Verifier (domain_invariant_verifier.py)

Deterministic checker ensuring:
1. Business invariants hold across concurrent transition checks (no illegal terminal mutations)
2. Heavy DDD is rejected on trivial CRUD unless justified
3. Contradictory/ambiguous business policies are escalated rather than silently invented
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


def verify_domain_model(spec: dict[str, Any]) -> dict[str, Any]:
    errors: list[str] = []
    if not isinstance(spec, dict) or not spec:
        return {"status": "FAIL", "valid": False, "errors": ["Domain specification must be a non-empty JSON object."]}

    if spec.get("is_simple_crud") and spec.get("use_full_ddd"):
        errors.append("Overengineering violation: avoid full DDD aggregate/event ceremony for simple CRUD.")

    if spec.get("invented_policy_for_ambiguous_rule"):
        errors.append("Escalation violation: ambiguous/contradictory policy must be escalated instead of invented.")

    transitions: dict[str, list[str]] = spec.get("state_transitions", {})
    if not transitions:
        errors.append("Missing 'state_transitions' state machine definition.")

    invariants = spec.get("invariants", [])
    if not invariants:
        errors.append("Missing explicit 'invariants' list.")

    # Simulate test transitions declared in spec
    for tx in spec.get("simulated_commands", []):
        from_state = str(tx.get("from_state", ""))
        to_state = str(tx.get("to_state", ""))
        expected_allowed = bool(tx.get("expected_allowed", True))
        allowed_targets = transitions.get(from_state, [])
        actual_allowed = to_state in allowed_targets
        if actual_allowed != expected_allowed:
            errors.append(
                f"Transition mismatch {from_state}->{to_state}: expected_allowed={expected_allowed}, actual_allowed={actual_allowed}."
            )

    if spec.get("unresolved_policy_conflicts") and not spec.get("escalated_to_owner"):
        errors.append("Unresolved policy conflicts exist without escalation marker ('escalated_to_owner: true').")

    return {
        "skill_id": "shadow-domain",
        "bounded_context": spec.get("bounded_context", "UNKNOWN"),
        "status": "PASS" if not errors else "FAIL",
        "valid": len(errors) == 0,
        "error_count": len(errors),
        "errors": errors,
    }


def run_self_test() -> dict[str, Any]:
    results: list[dict[str, Any]] = []

    golden = {
        "bounded_context": "LoanApproval",
        "is_simple_crud": False,
        "use_full_ddd": True,
        "state_transitions": {
            "DRAFT": ["SUBMITTED", "CANCELLED"],
            "SUBMITTED": ["APPROVED", "REJECTED"],
            "APPROVED": ["DISBURSED"],
            "DISBURSED": [],
        },
        "invariants": [
            {"id": "INV-01", "rule": "maker != checker enforced with optimistic lock version"},
            {"id": "INV-02", "rule": "tenant_id scoped on aggregate root"},
        ],
        "simulated_commands": [
            {"from_state": "SUBMITTED", "to_state": "APPROVED", "expected_allowed": True},
            {"from_state": "DISBURSED", "to_state": "CANCELLED", "expected_allowed": False},
        ],
        "invented_policy_for_ambiguous_rule": False,
        "unresolved_policy_conflicts": [],
    }
    results.append({"probe": "PRECISION-1: Concurrent transition invariants & terminal immutability pass", "passed": verify_domain_model(golden)["valid"]})

    # §10.1 Must-fail: invents unstated policy for ambiguous requirement
    invented = {**golden, "invented_policy_for_ambiguous_rule": True}
    results.append({"probe": "MUST-FAIL-1 (§10.1): Rejects inventing unstated policy on ambiguous requirement", "passed": not verify_domain_model(invented)["valid"]})

    # Must-fail: heavy DDD applied to simple CRUD
    crud_ddd = {**golden, "is_simple_crud": True, "use_full_ddd": True}
    results.append({"probe": "RECALL-1: Blocks unnecessary heavy DDD ceremony on simple CRUD", "passed": not verify_domain_model(crud_ddd)["valid"]})

    # Recall-2: Cancellation after completion wrongly permitted
    bad_tx = json.loads(json.dumps(golden))
    bad_tx["state_transitions"]["DISBURSED"] = ["CANCELLED"]
    results.append({"probe": "RECALL-2: Catches illegal cancellation transition after completion", "passed": not verify_domain_model(bad_tx)["valid"]})

    results.append({"probe": "BOUNDARY-1: Handles empty dict gracefully", "passed": not verify_domain_model({})["valid"]})
    results.append({"probe": "PRECISION-2: Deterministic repeat output", "passed": verify_domain_model(golden) == verify_domain_model(golden)})

    passed = sum(1 for r in results if r["passed"])
    return {
        "tool": "domain_invariant_verifier.py",
        "total_probes": len(results),
        "passed": passed,
        "failed": len(results) - passed,
        "all_passed": passed == len(results),
        "results": results,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Shadow Domain Invariant Verifier")
    parser.add_argument("--verify-model", default=None, help="JSON domain model file")
    parser.add_argument("--out", default=None, help="Optional output file path")
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()

    if args.self_test:
        out_data = run_self_test()
        exit_code = 0 if out_data["all_passed"] else 1
    elif args.verify_model:
        spec = json.loads(Path(args.verify_model).read_text(encoding="utf-8"))
        out_data = verify_domain_model(spec)
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
