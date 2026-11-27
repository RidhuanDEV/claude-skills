from __future__ import annotations

import copy
import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from types import ModuleType
from typing import Any

SCRIPT_PATH = Path(__file__).resolve().parents[1] / "scripts" / "auth_policy_verifier.py"


def _load_module() -> ModuleType:
    spec = importlib.util.spec_from_file_location("auth_policy_verifier_matrix", SCRIPT_PATH)
    if spec is None or spec.loader is None:
        raise ImportError(f"Cannot load {SCRIPT_PATH}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


verifier = _load_module()
InvalidInput: type[Exception] = verifier.InvalidInput

GOOD_MATRIX: dict[str, Any] = {
    "deny_by_default": True,
    "routes": [
        {
            "path": "GET /tenants/:tenant/records",
            "multi_tenant": True,
            "privileged": False,
            "server_auth_enforced": True,
            "tenant_scoped_in_query": True,
            "derives_tenant_from_request_body": False,
            "negative_tests": {"unauth_401": True, "cross_tenant_denied": True},
        },
        {
            "path": "GET /tenants/:tenant/admin-export",
            "multi_tenant": True,
            "privileged": True,
            "server_auth_enforced": True,
            "tenant_scoped_in_query": True,
            "negative_tests": {"unauth_401": True, "cross_tenant_denied": True, "role_denied_403": True},
        },
        {"path": "GET /healthz", "public": True},
    ],
}

GOOD_SESSION: dict[str, Any] = {
    "password_hash_algo": "argon2id",
    "cookie": {"enabled": True, "http_only": True, "secure": True, "same_site": "Lax"},
    "jwt": {
        "enabled": True,
        "alg": "RS256",
        "allowed_algs": ["RS256"],
        "access_ttl_sec": 300,
        "refresh_rotation_family_revocation": True,
        "jwks_kid_rollover_supported": True,
    },
    "trust_frontend_username_claim": False,
    "revoke_on_password_or_role_change": True,
}

GOOD_SSO: dict[str, Any] = {
    "oidc_pkce_s256": True,
    "state_and_nonce_verified": True,
    "tenant_bound_from_email_domain_only": False,
    "local_sdk_replaced_with_unverified_npm": False,
    "coexisting_cookie_and_jwks_unified_principal": True,
    "audit_log_enabled": True,
}


def _route(**overrides: object) -> dict[str, Any]:
    matrix = copy.deepcopy(GOOD_MATRIX)
    matrix["routes"][0].update(overrides)
    return matrix


def _session(**overrides: object) -> dict[str, Any]:
    cfg = copy.deepcopy(GOOD_SESSION)
    cfg.update(overrides)
    return cfg


def _jwt(**overrides: object) -> dict[str, Any]:
    cfg = copy.deepcopy(GOOD_SESSION)
    cfg["jwt"].update(overrides)
    return cfg


def _run_cli(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-B", str(SCRIPT_PATH), *args],
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )


class PolicyMatrixTests(unittest.TestCase):
    """Server-side RBAC + tenant isolation policy (was a local HTTP mock; now the shipped gate)."""

    def test_c06_tenant_scoped_deny_by_default_matrix_passes(self) -> None:
        res = verifier.check_policy_matrix(copy.deepcopy(GOOD_MATRIX))
        self.assertTrue(res["passed"], res)
        self.assertEqual(res["errors"], [])

    def test_c06_ui_guard_only_route_fails(self) -> None:
        res = verifier.check_policy_matrix(_route(server_auth_enforced=False))
        self.assertFalse(res["passed"])
        self.assertTrue(any("server-side authentication" in e for e in res["errors"]))

    def test_c06_unscoped_tenant_query_fails(self) -> None:
        res = verifier.check_policy_matrix(_route(tenant_scoped_in_query=False))
        self.assertFalse(res["passed"])
        self.assertTrue(any("anti-IDOR" in e for e in res["errors"]))

    def test_c06_tenant_from_request_body_fails(self) -> None:
        res = verifier.check_policy_matrix(_route(derives_tenant_from_request_body=True))
        self.assertFalse(res["passed"])
        self.assertTrue(any("confused deputy" in e for e in res["errors"]))

    def test_c06_missing_negative_tests_fail(self) -> None:
        for tests in ({}, {"unauth_401": True}, {"cross_tenant_denied": True}, "all", None):
            with self.subTest(tests=tests):
                self.assertFalse(verifier.check_policy_matrix(_route(negative_tests=tests))["passed"])

    def test_c06_privileged_route_without_role_denial_test_fails(self) -> None:
        matrix = copy.deepcopy(GOOD_MATRIX)
        matrix["routes"][1]["negative_tests"] = {"unauth_401": True, "cross_tenant_denied": True}
        res = verifier.check_policy_matrix(matrix)
        self.assertFalse(res["passed"])
        self.assertTrue(any("role-denial" in e for e in res["errors"]))

    def test_public_privileged_route_fails(self) -> None:
        matrix = copy.deepcopy(GOOD_MATRIX)
        matrix["routes"][2]["privileged"] = True
        self.assertFalse(verifier.check_policy_matrix(matrix)["passed"])

    def test_string_true_flags_do_not_count_as_enforced(self) -> None:
        for field in ("server_auth_enforced", "tenant_scoped_in_query"):
            with self.subTest(field=field):
                self.assertFalse(verifier.check_policy_matrix(_route(**{field: "true"}))["passed"])
        self.assertFalse(verifier.check_policy_matrix(_route(negative_tests={"unauth_401": "true", "cross_tenant_denied": 1}))["passed"])
        matrix = copy.deepcopy(GOOD_MATRIX)
        matrix["deny_by_default"] = "true"
        self.assertFalse(verifier.check_policy_matrix(matrix)["passed"])

    def test_string_false_on_bool_flags_is_invalid_input(self) -> None:
        for field in ("public", "privileged", "multi_tenant", "derives_tenant_from_request_body"):
            with self.subTest(field=field):
                with self.assertRaises(InvalidInput):
                    verifier.check_policy_matrix(_route(**{field: "false"}))

    def test_empty_missing_and_wrong_type_routes_fail(self) -> None:
        self.assertFalse(verifier.check_policy_matrix({})["passed"])
        self.assertFalse(verifier.check_policy_matrix({"deny_by_default": True, "routes": []})["passed"])
        self.assertFalse(verifier.check_policy_matrix({"deny_by_default": True, "routes": "GET /x"})["passed"])
        with self.assertRaises(InvalidInput):
            verifier.check_policy_matrix({"deny_by_default": True, "routes": ["GET /x"]})


class SessionConfigTests(unittest.TestCase):
    def test_hardened_session_passes(self) -> None:
        res = verifier.check_session_config(copy.deepcopy(GOOD_SESSION))
        self.assertTrue(res["passed"], res)

    def test_c06_trusting_frontend_username_fails(self) -> None:
        res = verifier.check_session_config(_session(trust_frontend_username_claim=True))
        self.assertFalse(res["passed"])
        self.assertTrue(any("NEVER trust frontend" in e for e in res["errors"]))

    def test_string_flags_on_trust_claim_are_invalid_input(self) -> None:
        for bad in ("false", "true", 0):
            with self.subTest(bad=bad):
                with self.assertRaises(InvalidInput):
                    verifier.check_session_config(_session(trust_frontend_username_claim=bad))

    def test_weak_unknown_or_flag_like_password_hash_fails(self) -> None:
        for bad in ("sha256", "md5", "", "true", "false", "rot13", True, None):
            with self.subTest(bad=bad):
                self.assertFalse(verifier.check_session_config(_session(password_hash_algo=bad))["passed"])

    def test_bcrypt_cost_threshold(self) -> None:
        self.assertTrue(verifier.check_session_config(_session(password_hash_algo="bcrypt", bcrypt_cost=12))["passed"])
        self.assertFalse(verifier.check_session_config(_session(password_hash_algo="bcrypt", bcrypt_cost=11))["passed"])
        self.assertFalse(verifier.check_session_config(_session(password_hash_algo="bcrypt"))["passed"])

    def test_cookie_flags_must_be_real_true(self) -> None:
        for field, bad in (("http_only", "true"), ("secure", "true"), ("http_only", False), ("same_site", "")):
            with self.subTest(field=field, bad=bad):
                cfg = copy.deepcopy(GOOD_SESSION)
                cfg["cookie"][field] = bad
                self.assertFalse(verifier.check_session_config(cfg)["passed"])
        with self.assertRaises(InvalidInput):
            verifier.check_session_config(_session(cookie="secure"))

    def test_jwt_alg_none_or_flag_like_fails(self) -> None:
        for bad in ("none", "", "true", "false", True):
            with self.subTest(bad=bad):
                self.assertFalse(verifier.check_session_config(_jwt(alg=bad))["passed"])
        self.assertFalse(verifier.check_session_config(_jwt(allowed_algs=[]))["passed"])
        self.assertFalse(verifier.check_session_config(_jwt(allowed_algs=["RS256", "none"]))["passed"])
        self.assertFalse(verifier.check_session_config(_jwt(allowed_algs=["true"]))["passed"])

    def test_jwt_access_ttl_ceiling(self) -> None:
        self.assertTrue(verifier.check_session_config(_jwt(access_ttl_sec=900))["passed"])
        self.assertFalse(verifier.check_session_config(_jwt(access_ttl_sec=901))["passed"])
        cfg = copy.deepcopy(GOOD_SESSION)
        del cfg["jwt"]["access_ttl_sec"]
        self.assertFalse(verifier.check_session_config(cfg)["passed"])

    def test_jwt_access_ttl_wrong_type_is_invalid_input(self) -> None:
        for bad in (True, "300", None):
            with self.subTest(bad=bad):
                with self.assertRaises(InvalidInput):
                    verifier.check_session_config(_jwt(access_ttl_sec=bad))

    def test_revocation_requires_real_true(self) -> None:
        for bad in ("true", 1, None):
            with self.subTest(bad=bad):
                self.assertFalse(verifier.check_session_config(_session(revoke_on_password_or_role_change=bad))["passed"])
        self.assertFalse(verifier.check_session_config(_jwt(refresh_rotation_family_revocation="true"))["passed"])

    def test_empty_session_config_fails(self) -> None:
        self.assertFalse(verifier.check_session_config({})["passed"])


class SsoCoexistenceTests(unittest.TestCase):
    def test_preserved_sdk_with_pkce_passes(self) -> None:
        self.assertTrue(verifier.check_sso_coexistence(copy.deepcopy(GOOD_SSO))["passed"])

    def test_required_true_fields_reject_strings_and_missing(self) -> None:
        for field in ("oidc_pkce_s256", "state_and_nonce_verified", "coexisting_cookie_and_jwks_unified_principal"):
            for bad in ("true", None, False):
                with self.subTest(field=field, bad=bad):
                    cfg = copy.deepcopy(GOOD_SSO)
                    cfg[field] = bad
                    self.assertFalse(verifier.check_sso_coexistence(cfg)["passed"])

    def test_sdk_swap_and_email_domain_binding_fail(self) -> None:
        for field in ("local_sdk_replaced_with_unverified_npm", "tenant_bound_from_email_domain_only"):
            with self.subTest(field=field):
                cfg = copy.deepcopy(GOOD_SSO)
                cfg[field] = True
                self.assertFalse(verifier.check_sso_coexistence(cfg)["passed"])
                cfg[field] = "false"
                with self.assertRaises(InvalidInput):
                    verifier.check_sso_coexistence(cfg)

    def test_empty_sso_config_fails(self) -> None:
        self.assertFalse(verifier.check_sso_coexistence({})["passed"])


class CliTests(unittest.TestCase):
    def _write(self, tmp: str, name: str, payload: object) -> str:
        path = Path(tmp) / name
        path.write_text(json.dumps(payload), encoding="utf-8")
        return str(path)

    def test_cli_exit_codes(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            good = self._write(tmp, "good.json", GOOD_MATRIX)
            bad = self._write(tmp, "bad.json", _route(server_auth_enforced="true"))
            invalid = self._write(tmp, "invalid.json", _route(public="false"))
            self.assertEqual(_run_cli("--check-policy-matrix", good).returncode, 0)
            self.assertEqual(_run_cli("--check-policy-matrix", bad).returncode, 1)
            invalid_run = _run_cli("--check-policy-matrix", invalid)
            self.assertEqual(invalid_run.returncode, 2)
            self.assertIn("INVALID_INPUT", invalid_run.stdout)
            self.assertEqual(_run_cli("--check-session-config", self._write(tmp, "s.json", GOOD_SESSION)).returncode, 0)
            self.assertEqual(_run_cli("--check-sso-coexistence", self._write(tmp, "e.json", {})).returncode, 1)

    def test_self_test_cli_passes(self) -> None:
        self.assertEqual(_run_cli("--self-test").returncode, 0)


if __name__ == "__main__":
    unittest.main()
