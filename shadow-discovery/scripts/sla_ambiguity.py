"""Flag SLA durations whose day basis is unstated, and produce one clarifying question per duration.

Usage:
    python sla_ambiguity.py --text "Approval must complete within 7 days."
    python sla_ambiguity.py --self-test

A duration such as "7 days" or "14 hari" is ambiguous unless the same requirement states the
basis: calendar or business/working days. The tool never assumes a basis.
"""

from __future__ import annotations

import argparse
import json
import re
import sys

DURATION_RE = re.compile(r"\b(\d+)\s*(days?|hari)\b", re.IGNORECASE)
BASIS_RE = re.compile(r"\b(?:calendar|kalender|business|working|kerja)\s*(?:days?|hari)\b|\bhari\s+(?:kerja|kalender)\b", re.IGNORECASE)


def detect(requirement: object) -> dict[str, object]:
    """Return one clarifying question per duration whose day basis is not stated."""
    if not isinstance(requirement, str) or not requirement.strip():
        return {"status": "INVALID_INPUT", "ambiguous": False, "questions": [], "assumptions_invented": False}
    if BASIS_RE.search(requirement):
        return {"status": "CLEAR", "ambiguous": False, "questions": [], "assumptions_invented": False}
    durations = list(dict.fromkeys(match[1] for match in DURATION_RE.finditer(requirement)))
    if not durations:
        return {"status": "NO_DURATION", "ambiguous": False, "questions": [], "assumptions_invented": False}
    questions = [
        f"Should the {count}-day deadline be counted in calendar days or business/working days "
        "(excluding weekends and public holidays)?"
        for count in durations
    ]
    return {"status": "AMBIGUOUS", "ambiguous": True, "questions": questions, "assumptions_invented": False}


def self_test() -> list[str]:
    checks = [
        (detect("Approval SLA must complete within 7 days after submission.")["status"], "AMBIGUOUS"),
        (detect("Approval SLA must complete within 7 business days.")["status"], "CLEAR"),
        (detect("Persetujuan selesai maksimal 14 hari kerja.")["status"], "CLEAR"),
        (detect("Laporan dikirim dalam 3 hari.")["questions"][0].startswith("Should the 3-day"), True),
        (detect("No deadline stated.")["status"], "NO_DURATION"),
        (detect("")["status"], "INVALID_INPUT"),
    ]
    return [f"got {got!r}, expected {want!r}" for got, want in checks if got != want]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--text")
    group.add_argument("--self-test", action="store_true")
    args = parser.parse_args(argv)
    if args.self_test:
        failures = self_test()
        print(json.dumps({"self_test": "FAIL" if failures else "PASS", "failures": failures}, indent=2))
        return 1 if failures else 0
    result = detect(args.text)
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0 if result["status"] in {"CLEAR", "NO_DURATION"} else 1


if __name__ == "__main__":
    sys.exit(main())
