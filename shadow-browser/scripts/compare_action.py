"""Compare one captured browser action with its predeclared acceptance criteria."""
import argparse
import json
from pathlib import Path


def assess(expected, observed):
    """Return only failing or missing field names, never captured user data."""
    identity = {"route", "role", "action"}
    assertions = {"httpStatus", "visibleState", "focusedControl", "sessionPresent", "persistedState"}
    if not isinstance(expected, dict) or not isinstance(observed, dict):
        raise ValueError("Expected two JSON objects")
    if not identity <= expected.keys() or any(not isinstance(expected[k], str) or not expected[k].strip() for k in identity):
        raise ValueError("Expected a route, role and action")
    checks = expected.keys() - identity
    if not checks <= assertions or "visibleState" not in checks:
        raise ValueError("Expected a visibleState oracle and supported checks")
    for field in checks:
        value = expected[field]
        if field == "httpStatus":
            valid = type(value) is int and 100 <= value <= 599
        elif field == "sessionPresent":
            valid = isinstance(value, bool)
        else:
            valid = isinstance(value, str) and bool(value.strip())
        if not valid:
            raise ValueError(f"Invalid oracle for {field}")
    if any(observed.get(k) != expected[k] for k in identity):
        return {"status": "BLOCKED", "reason": "Scenario identity mismatch"}
    if observed.get("environment") != "reachable":
        return {"status": "BLOCKED", "reason": "Reachability evidence missing or blocked"}
    missing = sorted(checks - observed.keys())
    failed = sorted(k for k in checks & observed.keys()
                    if type(observed[k]) is not type(expected[k]) or observed[k] != expected[k])
    return {"status": "FAIL" if failed else "BLOCKED" if missing else "PASS",
            "failed": failed, "missing": missing}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("expected", type=Path)
    parser.add_argument("observed", type=Path)
    args = parser.parse_args()
    try:
        result = assess(*(json.loads(path.read_text(encoding="utf-8-sig"))
                          for path in (args.expected, args.observed)))
    except (ValueError, OSError) as error:
        parser.exit(2, f"{error}\n")
    print(json.dumps(result))
    raise SystemExit({"PASS": 0, "FAIL": 1, "BLOCKED": 2}[result["status"]])
