#!/usr/bin/env python3
"""
Shadow Refactor Characterization & Invariant Gate (refactor_characterization_gate.py)

Deterministic verifier enforcing:
1. Local repository precedent inspection before refactoring
2. Characterization test pass both before and after refactor
3. Strict behavioral equivalence (blocks silent validation/API/schema changes)
4. Minimal scope boundary (blocks collateral edits to unrelated files)
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


def verify_refactor_plan(plan: dict[str, Any]) -> dict[str, Any]:
    errors: list[str] = []
    if not isinstance(plan, dict) or not plan:
        return {"status": "FAIL", "valid": False, "errors": ["Refactor payload must be a non-empty JSON object."]}

    if not plan.get("precedents_inspected"):
        errors.append("Missing 'precedents_inspected' (must inspect 1-3 nearest comparable files before editing).")

    if not plan.get("invariants_locked"):
        errors.append("Missing 'invariants_locked' declaring preserved API, validation, and data semantics.")

    char = plan.get("characterization_suite", {})
    if not isinstance(char, dict) or int(char.get("cases_count", 0)) < 1:
        errors.append("Characterization test suite requires at least 1 recorded case.")
    else:
        if int(char.get("before_refactor_exit_code", -1)) != 0 or int(char.get("after_refactor_exit_code", -1)) != 0:
            errors.append("Characterization suite must exit 0 both before and after refactoring.")

    if plan.get("silent_contract_changes"):
        errors.append(f"Forbidden silent contract/validation changes detected: {plan['silent_contract_changes']}")

    if plan.get("introduces_new_architecture_pattern") and not plan.get("adr_approved_for_new_pattern"):
        errors.append("Introducing a new architecture pattern requires an explicit approved ADR.")

    changed = {str(f) for f in plan.get("changed_files", [])}
    allowed = {str(f) for f in plan.get("allowed_scope_files", [])}
    out_of_scope = sorted(changed - allowed)
    if not changed:
        errors.append("'changed_files' cannot be empty.")
    if out_of_scope:
        errors.append(f"Collateral modification of untouched/out-of-scope files: {out_of_scope}")

    if not str(plan.get("rollback", "")).strip():
        errors.append("Missing explicit 'rollback' instruction.")

    return {
        "skill_id": "shadow-refactor",
        "record_id": plan.get("record_id", "REF-UNASSIGNED"),
        "status": "PASS" if not errors else "FAIL",
        "valid": len(errors) == 0,
        "error_count": len(errors),
        "errors": errors,
    }


def run_self_test() -> dict[str, Any]:
    results: list[dict[str, Any]] = []

    golden = {
        "record_id": "REF-100",
        "precedents_inspected": ["src/orders/discount.ts:10-65"],
        "invariants_locked": ["Returns exact 422 envelope on negative qty", "Preserves legacy currency rounding"],
        "characterization_suite": {"cases_count": 8, "before_refactor_exit_code": 0, "after_refactor_exit_code": 0},
        "changed_files": ["src/orders/pricing.ts", "tests/orders/pricing.char.spec.ts"],
        "allowed_scope_files": ["src/orders/pricing.ts", "tests/orders/pricing.char.spec.ts"],
        "silent_contract_changes": [],
        "introduces_new_architecture_pattern": False,
        "rollback": "git checkout -- src/orders/pricing.ts",
    }
    results.append({"probe": "PRECISION-1: Characterization-backed scoped refactor passes", "passed": verify_refactor_plan(golden)["valid"]})

    # §10.1 Must-fail: silently alters domain validation or local architecture
    silent_val = json.loads(json.dumps(golden))
    silent_val["silent_contract_changes"] = ["Changed minimum order amount from 10000 to 15000 without spec"]
    results.append({"probe": "MUST-FAIL-1 (§10.1): Blocks refactor that silently alters domain validation", "passed": not verify_refactor_plan(silent_val)["valid"]})

    unapproved_arch = json.loads(json.dumps(golden))
    unapproved_arch["introduces_new_architecture_pattern"] = True
    unapproved_arch["adr_approved_for_new_pattern"] = False
    results.append({"probe": "MUST-FAIL-2 (§10.1): Blocks unsolicited architecture pattern without ADR", "passed": not verify_refactor_plan(unapproved_arch)["valid"]})

    # Collateral file modification
    collateral = json.loads(json.dumps(golden))
    collateral["changed_files"].append("src/unrelated/users.ts")
    results.append({"probe": "RECALL-1: Blocks out-of-scope edits to unrelated files", "passed": not verify_refactor_plan(collateral)["valid"]})

    missing_scope = dict(golden)
    del missing_scope['allowed_scope_files']
    results.append({'probe': 'Changed files require an explicit scope', 'passed': not verify_refactor_plan(missing_scope)['valid']})

    # Empty / failing characterization
    results.append({"probe": "BOUNDARY-1: Rejects empty payload gracefully", "passed": not verify_refactor_plan({})["valid"]})
    results.append({"probe": "PRECISION-2: Deterministic output on repeat runs", "passed": verify_refactor_plan(golden) == verify_refactor_plan(golden)})

    passed = sum(1 for r in results if r["passed"])
    return {
        "tool": "refactor_characterization_gate.py",
        "total_probes": len(results),
        "passed": passed,
        "failed": len(results) - passed,
        "all_passed": passed == len(results),
        "results": results,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Shadow Refactor Characterization Gate")
    parser.add_argument("--verify-plan", default=None, help="Path to JSON refactor plan/ledger")
    parser.add_argument("--out", default=None, help="Optional output file path")
    parser.add_argument("--self-test", action="store_true", help="Run deterministic test suite")
    args = parser.parse_args()

    if args.self_test:
        out_data = run_self_test()
        exit_code = 0 if out_data["all_passed"] else 1
    elif args.verify_plan:
        payload = json.loads(Path(args.verify_plan).read_text(encoding="utf-8"))
        out_data = verify_refactor_plan(payload)
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
