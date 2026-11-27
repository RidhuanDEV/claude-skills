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

SCRIPT_PATH = Path(__file__).resolve().parents[1] / "scripts" / "compare_action.py"


def _load_module() -> ModuleType:
    spec = importlib.util.spec_from_file_location("compare_action_boundaries", SCRIPT_PATH)
    if spec is None or spec.loader is None:
        raise ImportError(f"Cannot load {SCRIPT_PATH}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


compare_action = _load_module()

EXPECTED_LOGIN: dict[str, Any] = {
    "route": "/dashboard",
    "role": "viewer",
    "action": "open dashboard with stored session",
    "httpStatus": 200,
    "visibleState": "dashboard heading",
    "sessionPresent": True,
}


def _observed(**overrides: object) -> dict[str, Any]:
    observed: dict[str, Any] = dict(EXPECTED_LOGIN, environment="reachable")
    observed.update(overrides)
    return observed


def _run_cli(expected: object, observed: object) -> subprocess.CompletedProcess[str]:
    with tempfile.TemporaryDirectory() as tmp:
        exp_path = Path(tmp) / "expected.json"
        obs_path = Path(tmp) / "observed.json"
        exp_path.write_text(json.dumps(expected), encoding="utf-8")
        obs_path.write_text(json.dumps(observed), encoding="utf-8")
        return subprocess.run(
            [sys.executable, "-B", str(SCRIPT_PATH), str(exp_path), str(obs_path)],
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )


class HostBoundaryTests(unittest.TestCase):
    """Host/target boundary has no shipped policy function; the shipped oracle blocks off-target captures."""

    def test_c08_matching_local_capture_passes(self) -> None:
        res = compare_action.assess(dict(EXPECTED_LOGIN), _observed())
        self.assertEqual(res, {"status": "PASS", "failed": [], "missing": []})

    def test_c08_capture_from_other_route_or_host_is_blocked(self) -> None:
        for route in ("https://prod.example.com/admin", "/admin", "", None):
            with self.subTest(route=route):
                res = compare_action.assess(dict(EXPECTED_LOGIN), _observed(route=route))
                self.assertEqual(res["status"], "BLOCKED")

    def test_c08_capture_for_other_role_or_action_is_blocked(self) -> None:
        self.assertEqual(compare_action.assess(dict(EXPECTED_LOGIN), _observed(role="admin"))["status"], "BLOCKED")
        self.assertEqual(compare_action.assess(dict(EXPECTED_LOGIN), _observed(action="delete"))["status"], "BLOCKED")

    def test_c08_unreachable_or_flag_like_environment_is_blocked(self) -> None:
        for env in ("unreachable", "true", True, None, ""):
            with self.subTest(env=env):
                res = compare_action.assess(dict(EXPECTED_LOGIN), _observed(environment=env))
                self.assertEqual(res["status"], "BLOCKED")
        observed = _observed()
        del observed["environment"]
        self.assertEqual(compare_action.assess(dict(EXPECTED_LOGIN), observed)["status"], "BLOCKED")


class SessionResponseTests(unittest.TestCase):
    def test_c08_expired_session_401_fails_200_oracle(self) -> None:
        res = compare_action.assess(dict(EXPECTED_LOGIN), _observed(httpStatus=401, sessionPresent=False))
        self.assertEqual(res["status"], "FAIL")
        self.assertEqual(res["failed"], ["httpStatus", "sessionPresent"])

    def test_c08_expected_401_rejection_passes(self) -> None:
        expected = dict(EXPECTED_LOGIN, httpStatus=401, sessionPresent=False, visibleState="session expired alert")
        observed = dict(expected, environment="reachable")
        self.assertEqual(compare_action.assess(expected, observed)["status"], "PASS")

    def test_string_and_int_lookalikes_fail(self) -> None:
        for field, value in (("httpStatus", "200"), ("httpStatus", 200.0), ("sessionPresent", "true"), ("sessionPresent", 1)):
            with self.subTest(field=field, value=value):
                res = compare_action.assess(dict(EXPECTED_LOGIN), _observed(**{field: value}))
                self.assertEqual(res["status"], "FAIL")
                self.assertEqual(res["failed"], [field])

    def test_missing_assertion_is_blocked(self) -> None:
        observed = _observed()
        del observed["sessionPresent"]
        res = compare_action.assess(dict(EXPECTED_LOGIN), observed)
        self.assertEqual(res["status"], "BLOCKED")
        self.assertEqual(res["missing"], ["sessionPresent"])

    def test_result_never_echoes_captured_values(self) -> None:
        res = compare_action.assess(dict(EXPECTED_LOGIN), _observed(visibleState="token=secret-abc123"))
        self.assertEqual(res["status"], "FAIL")
        self.assertNotIn("secret-abc123", json.dumps(res))


class InvalidOracleTests(unittest.TestCase):
    def test_invalid_oracles_raise(self) -> None:
        bad_oracles: list[object] = [
            {},
            [],
            None,
            dict(EXPECTED_LOGIN, sessionPresent="false"),
            dict(EXPECTED_LOGIN, httpStatus="200"),
            dict(EXPECTED_LOGIN, httpStatus=True),
            dict(EXPECTED_LOGIN, httpStatus=99),
            dict(EXPECTED_LOGIN, role="  "),
            dict(EXPECTED_LOGIN, unknownCheck="x"),
            {k: v for k, v in EXPECTED_LOGIN.items() if k != "visibleState"},
        ]
        for oracle in bad_oracles:
            with self.subTest(oracle=oracle):
                with self.assertRaises(ValueError):
                    compare_action.assess(oracle, _observed())

    def test_non_object_observation_raises(self) -> None:
        for observed in (None, [], "reachable"):
            with self.subTest(observed=observed):
                with self.assertRaises(ValueError):
                    compare_action.assess(dict(EXPECTED_LOGIN), observed)

    def test_empty_observation_is_blocked(self) -> None:
        self.assertEqual(compare_action.assess(dict(EXPECTED_LOGIN), {})["status"], "BLOCKED")


class CliExitCodeTests(unittest.TestCase):
    def test_cli_exit_codes(self) -> None:
        self.assertEqual(_run_cli(EXPECTED_LOGIN, _observed()).returncode, 0)
        self.assertEqual(_run_cli(EXPECTED_LOGIN, _observed(httpStatus=401)).returncode, 1)
        self.assertEqual(_run_cli(EXPECTED_LOGIN, _observed(environment="unreachable")).returncode, 2)
        self.assertEqual(_run_cli(dict(EXPECTED_LOGIN, sessionPresent="true"), _observed()).returncode, 2)


if __name__ == "__main__":
    unittest.main()
