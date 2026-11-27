"""Strict evidence types and structured CLI input errors for Shadow Army verifiers."""

from __future__ import annotations

import json
from collections.abc import Callable


class InvalidInput(ValueError):
    """Evidence is missing or has the wrong type."""


def strict_bool(value: object, field: str) -> bool:
    if not isinstance(value, bool):
        raise InvalidInput(f"{field} must be a JSON boolean (true or false).")
    return value


def run_checked_cli(main: Callable[[], int]) -> int:
    try:
        return main()
    except InvalidInput as exc:
        print(json.dumps({"status": "INVALID_INPUT", "passed": False, "errors": [str(exc)]}))
        return 2
