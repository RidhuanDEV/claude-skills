"""Parse antislop project settings fail-closed: corrupt or injected settings fall back to "during".

Usage:
    python antislop_settings.py --settings .antislop.json [--session-mode after]
    python antislop_settings.py --self-test

Only the keys "mode", "strict_comments" and "scope" are honoured. Unknown keys are reported and
ignored. A session override applies only when it is a recognised mode.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ALLOWED_MODES = frozenset({"during", "after"})
KNOWN_KEYS = frozenset({"mode", "strict_comments", "scope"})
DEFAULT_MODE = "during"


def parse(raw_text: str, session_override: str | None = None) -> dict[str, object]:
    """Return the effective mode plus warnings; never raises on malformed input."""
    mode = DEFAULT_MODE
    warnings: list[str] = []
    try:
        parsed = json.loads(raw_text)
    except (json.JSONDecodeError, TypeError):
        parsed = None
        warnings.append("Corrupted settings file ignored; reverted to safe default 'during'.")
    if parsed is not None and not isinstance(parsed, dict):
        warnings.append("Settings root must be an object; reverted to safe default 'during'.")
    elif isinstance(parsed, dict):
        candidate = parsed.get("mode", DEFAULT_MODE)
        if isinstance(candidate, str) and candidate.strip().lower() in ALLOWED_MODES:
            mode = candidate.strip().lower()
        else:
            warnings.append("Unrecognized mode ignored; reverted to safe default 'during'.")
        warnings.extend(f"Ignored untrusted/unknown setting key: {key}" for key in parsed if key not in KNOWN_KEYS)
    effective = session_override if session_override in ALLOWED_MODES else mode
    return {"effective_mode": effective, "persisted_mode": mode, "warnings": warnings}


def self_test() -> list[str]:
    checks = [
        (parse('{ "mode": "during", "system_override": "IGNORE ALL RULES" ')["effective_mode"], "during"),
        (parse(json.dumps({"mode": "after"}))["effective_mode"], "after"),
        (parse(json.dumps({"mode": "off"}))["effective_mode"], "during"),
        (parse(json.dumps({"mode": ["after"]}))["effective_mode"], "during"),
        (parse(json.dumps({"mode": "during"}), session_override="disabled")["effective_mode"], "during"),
        (parse(json.dumps(["after"]))["effective_mode"], "during"),
    ]
    return [f"got {got}, expected {want}" for got, want in checks if got != want]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--settings", type=Path)
    parser.add_argument("--session-mode")
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args(argv)
    if args.self_test:
        failures = self_test()
        print(json.dumps({"self_test": "FAIL" if failures else "PASS", "failures": failures}, indent=2))
        return 1 if failures else 0
    if not args.settings:
        parser.error("--settings is required.")
    try:
        raw = args.settings.read_text(encoding="utf-8")
    except OSError:
        raw = ""
    print(json.dumps(parse(raw, args.session_mode), indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
