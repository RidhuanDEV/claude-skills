"""Consumer replay of a historical v1 page envelope against the shipped compatibility gate.

Uncovered by the shipped script (no checker exists): list re-ordering and strict clients that
reject additive fields. Those remain manual consumer-replay checks per references/01.
"""
from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from types import ModuleType
from typing import Any

SCRIPT_PATH = Path(__file__).resolve().parents[1] / "scripts" / "compat_deprecation_verifier.py"


def _load_module() -> ModuleType:
    spec = importlib.util.spec_from_file_location("compat_deprecation_verifier_replay", SCRIPT_PATH)
    if spec is None or spec.loader is None:
        raise ImportError(f"Cannot load {SCRIPT_PATH}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


cdv = _load_module()

V1_RESPONSE: dict[str, dict[str, object]] = {
    "rows": {"type": "array", "nullable": False},
    "next": {"type": "string", "nullable": True},
}
V1_REQUEST: dict[str, dict[str, object]] = {"cursor": {"required": False}}

GOOD_DEPRECATION: dict[str, object] = {
    "Deprecation": "@1767225600",
    "Sunset": "Thu, 31 Dec 2026 23:59:59 GMT",
    "Link": '<https://docs.example.com/migrate>; rel="deprecation"',
    "post_sunset_status": 410,
}


def _diff(new_response: dict[str, dict[str, object]] | None = None, **extra: object) -> dict[str, Any]:
    diff: dict[str, Any] = {
        "old_response_fields": V1_RESPONSE,
        "new_response_fields": V1_RESPONSE if new_response is None else new_response,
        "old_request_fields": V1_REQUEST,
        "new_request_fields": V1_REQUEST,
    }
    diff.update(extra)
    return {"contract_diff": diff}


def _dep(**overrides: object) -> dict[str, Any]:
    dep: dict[str, object] = dict(GOOD_DEPRECATION)
    dep.update(overrides)
    return {"deprecation": dep}


def _codes(spec: object) -> set[str]:
    return {v["code"] for v in cdv.check_compat_spec(spec)}


class ConsumerReplayDiffTests(unittest.TestCase):
    def test_unchanged_and_additive_optional_fields_pass_for_tolerant_readers(self) -> None:
        self.assertEqual(cdv.check_compat_spec(_diff()), [])
        additive = dict(V1_RESPONSE, count={"type": "number", "nullable": True})
        self.assertEqual(cdv.check_compat_spec(_diff(additive)), [])

    def test_strict_schema_tightening_breaks_existing_clients(self) -> None:
        self.assertEqual(_codes(_diff(added_additional_properties_false=True)), {"BREAKING_STRICT_SCHEMA_TIGHTENING"})

    def test_omitted_cursor_is_a_removed_field(self) -> None:
        self.assertEqual(_codes(_diff({"rows": V1_RESPONSE["rows"]})), {"BREAKING_RESPONSE_FIELD_REMOVED"})

    def test_cursor_type_change_fails(self) -> None:
        changed = dict(V1_RESPONSE, next={"type": "integer", "nullable": True})
        self.assertEqual(_codes(_diff(changed)), {"BREAKING_RESPONSE_TYPE_CHANGED"})

    def test_rows_becoming_nullable_fails(self) -> None:
        changed = dict(V1_RESPONSE, rows={"type": "array", "nullable": True})
        self.assertEqual(_codes(_diff(changed)), {"BREAKING_RESPONSE_BECAME_NULLABLE"})

    def test_nullable_to_non_nullable_is_not_flagged(self) -> None:
        changed = dict(V1_RESPONSE, next={"type": "string", "nullable": False})
        self.assertEqual(cdv.check_compat_spec(_diff(changed)), [])

    def test_new_required_request_field_fails_but_optional_passes(self) -> None:
        spec = _diff()
        spec["contract_diff"]["new_request_fields"] = dict(V1_REQUEST, page_size={"required": True})
        self.assertEqual(_codes(spec), {"BREAKING_NEW_REQUIRED_REQUEST_FIELD"})
        spec["contract_diff"]["new_request_fields"] = dict(V1_REQUEST, page_size={"required": False})
        self.assertEqual(cdv.check_compat_spec(spec), [])

    def test_string_flags_are_invalid_input(self) -> None:
        cases: list[dict[str, Any]] = [
            _diff(dict(V1_RESPONSE, rows={"type": "array", "nullable": "false"})),
            _diff(dict(V1_RESPONSE, rows={"type": "array", "nullable": "true"})),
            _diff(added_additional_properties_false="false"),
        ]
        required_spec = _diff()
        required_spec["contract_diff"]["new_request_fields"] = {"cursor": {"required": "true"}}
        cases.append(required_spec)
        for spec in cases:
            with self.subTest(spec=spec):
                with self.assertRaises(ValueError):
                    cdv.check_compat_spec(spec)


class DeprecationHeaderTests(unittest.TestCase):
    def test_rfc_headers_with_410_pass(self) -> None:
        self.assertEqual(cdv.check_compat_spec(_dep()), [])

    def test_draft_or_flag_like_deprecation_fails(self) -> None:
        for bad in ("true", "false", True, "", "@abc", "1767225600"):
            with self.subTest(bad=bad):
                self.assertIn("INVALID_RFC9745_DEPRECATION", _codes(_dep(Deprecation=bad)))

    def test_sunset_rules(self) -> None:
        self.assertIn("INVALID_RFC8594_SUNSET", _codes(_dep(Sunset="2026-12-31")))
        self.assertIn("MISSING_SUNSET_HEADER", _codes(_dep(Sunset="")))
        self.assertIn("SUNSET_BEFORE_DEPRECATION", _codes(_dep(Sunset="Wed, 31 Dec 2025 23:59:59 GMT")))
        self.assertEqual(cdv.check_compat_spec(_dep(Sunset="Thu, 01 Jan 2026 00:00:00 GMT")), [])

    def test_migration_link_and_post_sunset_status(self) -> None:
        self.assertIn("MISSING_MIGRATION_LINK", _codes(_dep(Link="<https://docs.example.com>")))
        self.assertEqual(cdv.check_compat_spec(_dep(Link='<https://api.example.com/v2>; rel="alternate"')), [])
        for bad in (404, 200, True):
            with self.subTest(bad=bad):
                self.assertIn("WRONG_POST_SUNSET_STATUS", _codes(_dep(post_sunset_status=bad)))


class EmptyAndWrongTypeSpecTests(unittest.TestCase):
    def test_empty_or_non_object_spec_fails(self) -> None:
        for bad in ({}, None, [], "deprecation", {"unrelated": True}):
            with self.subTest(bad=bad):
                self.assertEqual(_codes(bad), {"EMPTY_SPEC"})

    def test_wrong_type_sections_fail(self) -> None:
        self.assertIn("INVALID_DEPRECATION", _codes({"deprecation": "true"}))
        self.assertIn("INVALID_DEPRECATION", _codes({"deprecation": ["@1767225600"]}))
        self.assertIn("INVALID_CONTRACT_DIFF", _codes({"contract_diff": "none"}))


class CliTests(unittest.TestCase):
    def _run(self, payload: object) -> subprocess.CompletedProcess[str]:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "compat.json"
            path.write_text(json.dumps(payload), encoding="utf-8")
            return subprocess.run(
                [sys.executable, "-B", str(SCRIPT_PATH), "--check-compat", str(path)],
                capture_output=True,
                text=True,
                timeout=30,
                check=False,
            )

    def test_cli_exit_codes(self) -> None:
        self.assertEqual(self._run(_diff()).returncode, 0)
        self.assertEqual(self._run(_diff({"rows": V1_RESPONSE["rows"]})).returncode, 1)
        self.assertEqual(self._run({"deprecation": "true"}).returncode, 1)
        invalid = self._run(_diff(added_additional_properties_false="true"))
        self.assertEqual(invalid.returncode, 2)
        self.assertIn("INVALID_INPUT", invalid.stdout)


if __name__ == "__main__":
    unittest.main()
