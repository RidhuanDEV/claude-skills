"""Recommend a deployment topology for ONE application from stated, verified drivers.

Usage:
    python topology_decision.py --assess drivers.json
    python topology_decision.py --self-test

Input: {"team_count": 2, "independent_scaling_proven": false, "shared_acid_transactions": true,
        "regulatory_isolation_required": false}
The thresholds are heuristics (team size around 3, Fowler's "MonolithFirst", Team Topologies).
They support an ADR; they do not replace one. Flags must be JSON booleans.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

FLAGS = ("independent_scaling_proven", "shared_acid_transactions", "regulatory_isolation_required")
SMALL_TEAM_LIMIT = 3


def recommend(drivers: object) -> dict[str, object]:
    """Prefer a modular monolith unless proven scaling or isolation needs justify a split."""
    if not isinstance(drivers, dict):
        return {"topology": None, "status": "INVALID_INPUT", "reason": "Expected a JSON object."}
    errors = [f"{name} must be a JSON boolean." for name in FLAGS if not isinstance(drivers.get(name), bool)]
    team_count = drivers.get("team_count")
    if not isinstance(team_count, int) or isinstance(team_count, bool) or team_count < 1:
        errors.append("team_count must be a positive integer.")
    if errors:
        return {"topology": None, "status": "INVALID_INPUT", "reason": " ".join(errors)}
    regulated = drivers["regulatory_isolation_required"]
    if not drivers["independent_scaling_proven"] and not regulated and team_count <= SMALL_TEAM_LIMIT:
        return {
            "topology": "modular_monolith", "status": "RECOMMENDED", "rejected": ["microservices"],
            "reason": "One deployable unit with strict module boundaries avoids distributed-transaction overhead.",
        }
    if drivers["shared_acid_transactions"] and not regulated:
        return {
            "topology": "modular_monolith_with_worker", "status": "RECOMMENDED", "rejected": ["microservices"],
            "reason": "Keep ACID write invariants in one transactional store; isolate only asynchronous workers.",
        }
    return {
        "topology": "bounded_split_services", "status": "RECOMMENDED", "rejected": [],
        "reason": "Proven independent scaling or regulatory isolation justifies a split deployment; record it in an ADR.",
    }


def self_test() -> list[str]:
    base = {"team_count": 2, "independent_scaling_proven": False, "shared_acid_transactions": True,
            "regulatory_isolation_required": False}
    checks = [
        (recommend(base)["topology"], "modular_monolith"),
        (recommend({**base, "team_count": 6})["topology"], "modular_monolith_with_worker"),
        (recommend({**base, "team_count": 6, "regulatory_isolation_required": True})["topology"], "bounded_split_services"),
        (recommend({**base, "independent_scaling_proven": "false"})["status"], "INVALID_INPUT"),
        (recommend({**base, "team_count": 0})["status"], "INVALID_INPUT"),
    ]
    return [f"got {got}, expected {want}" for got, want in checks if got != want]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--assess", type=Path)
    group.add_argument("--self-test", action="store_true")
    args = parser.parse_args(argv)
    if args.self_test:
        failures = self_test()
        print(json.dumps({"self_test": "FAIL" if failures else "PASS", "failures": failures}, indent=2))
        return 1 if failures else 0
    try:
        drivers = json.loads(args.assess.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        print(json.dumps({"topology": None, "status": "INVALID_INPUT", "reason": str(error)}))
        return 1
    result = recommend(drivers)
    print(json.dumps(result, indent=2))
    return 0 if result["status"] == "RECOMMENDED" else 1


if __name__ == "__main__":
    sys.exit(main())
