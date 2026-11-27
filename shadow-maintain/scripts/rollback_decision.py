"""Decide whether an incident rollback is safe, needs approval, or must become a forward fix.

Usage:
    python rollback_decision.py --assess decision.json
    python rollback_decision.py --self-test

The input names the current and target versions, whether a kill switch (feature flag) exists,
whether every migration between the versions is expand-only, and whether the incident commander
approved the rollback. Every flag must be a JSON boolean: a string such as "false" is rejected.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

FLAGS = ("feature_flag_available", "migration_is_expand_only", "incident_commander_approved")


def decide(record: object) -> dict[str, object]:
    """Return the rollback mode for one incident record; malformed input is never allowed."""
    if not isinstance(record, dict):
        return {"rollback_allowed": False, "mode": "INVALID_INPUT", "reason": "Expected a JSON object."}
    errors = [
        f"{name} must be a JSON boolean." for name in FLAGS if not isinstance(record.get(name), bool)
    ]
    for name in ("current_version", "target_version"):
        value = record.get(name)
        if not isinstance(value, str) or not value.strip():
            errors.append(f"{name} must be a non-empty string.")
    if errors:
        return {"rollback_allowed": False, "mode": "INVALID_INPUT", "reason": " ".join(errors)}
    current, target = record["current_version"], record["target_version"]
    if current == target:
        return {"rollback_allowed": False, "mode": "INVALID_INPUT", "reason": "Target equals the running version."}
    if record["migration_is_expand_only"] is not True:
        return {
            "rollback_allowed": False,
            "mode": "BLOCKED_INCOMPATIBLE_SCHEMA",
            "reason": f"Migrations between {target} and {current} are not expand-only; plan a forward fix or a tested restore.",
        }
    mode = "FLAG_OFF_AND_BINARY_ROLLBACK" if record["feature_flag_available"] else "EXPAND_COMPATIBLE_ROLLBACK"
    if record["incident_commander_approved"] is not True:
        return {
            "rollback_allowed": False,
            "mode": "AWAITING_APPROVAL",
            "compatible_mode": mode,
            "reason": "Rollback is compatible but needs incident commander approval.",
        }
    return {"rollback_allowed": True, "mode": mode}


def self_test() -> list[str]:
    base = {
        "current_version": "2.4.0", "target_version": "2.3.0", "feature_flag_available": True,
        "migration_is_expand_only": True, "incident_commander_approved": True,
    }
    cases = [
        (base, "FLAG_OFF_AND_BINARY_ROLLBACK"),
        ({**base, "feature_flag_available": False}, "EXPAND_COMPATIBLE_ROLLBACK"),
        ({**base, "migration_is_expand_only": False}, "BLOCKED_INCOMPATIBLE_SCHEMA"),
        ({**base, "incident_commander_approved": False}, "AWAITING_APPROVAL"),
        ({**base, "migration_is_expand_only": "true"}, "INVALID_INPUT"),
        ({**base, "target_version": "2.4.0"}, "INVALID_INPUT"),
        ([], "INVALID_INPUT"),
    ]
    return [f"{case!r} -> {decide(case)['mode']} (expected {want})" for case, want in cases if decide(case)["mode"] != want]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--assess", type=Path, help="JSON file describing the incident rollback.")
    group.add_argument("--self-test", action="store_true")
    args = parser.parse_args(argv)
    if args.self_test:
        failures = self_test()
        print(json.dumps({"self_test": "FAIL" if failures else "PASS", "failures": failures}, indent=2))
        return 1 if failures else 0
    try:
        record = json.loads(args.assess.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        print(json.dumps({"rollback_allowed": False, "mode": "INVALID_INPUT", "reason": str(error)}))
        return 1
    result = decide(record)
    print(json.dumps(result, indent=2))
    return 0 if result["rollback_allowed"] is True else 1


if __name__ == "__main__":
    sys.exit(main())
