#!/usr/bin/env python3
"""Deterministic AuthN, AuthZ, Session/JWT & Multi-Tenant Policy Verifier (L0/L1 offline CLI).

Zero third-party dependencies (Python 3 stdlib only).
Validates:
  - Password hashing, cookie flags, JWT/JWKS rotation & session revocation (--check-session-config)
  - Route/tenant/role authorization policy matrix & anti-IDOR coverage (--check-policy-matrix)
  - External SSO + local session + JWKS coexistence & local SDK safety (--check-sso-coexistence)
  - Built-in precision & recall self-test probes (--self-test)
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "shadow-monarch" / "scripts"))
from shadow_input import InvalidInput, run_checked_cli, strict_bool

ACCEPTED_HASH_ALGOS = {"argon2id", "bcrypt", "scrypt"}
ACCEPTED_JWT_ALGOS = {
    "hs256", "hs384", "hs512", "rs256", "rs384", "rs512", "ps256", "ps384", "ps512",
    "es256", "es384", "es512", "es256k", "eddsa",
}


def check_session_config(cfg: dict[str, Any]) -> dict[str, Any]:
    errors: list[str] = []
    warnings: list[str] = []

    pw_algo = str(cfg.get("password_hash_algo", "")).strip().lower()
    if pw_algo not in ACCEPTED_HASH_ALGOS:
        errors.append(
            f"Insecure or missing password_hash_algo '{pw_algo}'; require 'argon2id' (preferred), 'bcrypt' (cost >= 12), or 'scrypt'."
        )
    elif pw_algo == "bcrypt" and int(cfg.get("bcrypt_cost", 0)) < 12:
        errors.append(f"bcrypt_cost={cfg.get('bcrypt_cost')} is below minimum 12.")

    cookie = cfg.get("cookie", {})
    if not isinstance(cookie, dict):
        raise InvalidInput("cookie must be a JSON object.")
    if strict_bool(cookie.get("enabled", True), "cookie.enabled"):
        if cookie.get("http_only") is not True:
            errors.append("Session/refresh cookie MUST set HttpOnly=true.")
        if cookie.get("secure") is not True:
            errors.append("Session/refresh cookie MUST set Secure=true.")
        samesite = str(cookie.get("same_site", "")).strip().lower()
        if samesite not in {"strict", "lax", "none"}:
            errors.append(f"Cookie SameSite must be Strict, Lax, or None (got '{samesite}').")
        if samesite == "none" and cookie.get("secure") is not True:
            errors.append("SameSite=None requires Secure=true.")

    jwt_cfg = cfg.get("jwt", {})
    if not isinstance(jwt_cfg, dict):
        raise InvalidInput("jwt must be a JSON object.")
    if strict_bool(jwt_cfg.get("enabled", False), "jwt.enabled"):
        alg = str(jwt_cfg.get("alg", "")).strip().lower()
        if alg not in ACCEPTED_JWT_ALGOS:
            errors.append(f"Forbidden or missing JWT signing algorithm '{alg}'.")
        allowed_algs = [str(a).strip().lower() for a in jwt_cfg.get("allowed_algs", [])]
        if len(allowed_algs) == 0 or any(a not in ACCEPTED_JWT_ALGOS for a in allowed_algs):
            errors.append("JWT verifier MUST explicitly pin non-empty allowed_algs of registered JWS algorithms (never 'none').")
        access_ttl = jwt_cfg.get("access_ttl_sec", 999999)
        if isinstance(access_ttl, bool) or not isinstance(access_ttl, int):
            raise InvalidInput("jwt.access_ttl_sec must be a JSON integer.")
        if access_ttl > 900:
            errors.append(f"JWT access_ttl_sec={access_ttl} exceeds 900s (15 min) ceiling.")
        if jwt_cfg.get("refresh_rotation_family_revocation") is not True:
            errors.append("Refresh tokens MUST enforce rotation with token-family reuse revocation.")
        if jwt_cfg.get("jwks_kid_rollover_supported") is not True:
            warnings.append("Enable dual-key JWKS kid rollover so signing key rotation causes zero downtime.")

    if strict_bool(cfg.get("trust_frontend_username_claim", False), "trust_frontend_username_claim"):
        errors.append("CRITICAL: Backend MUST NEVER trust frontend-supplied username/role/tenant_id without server-verified token claims.")
    if cfg.get("revoke_on_password_or_role_change") is not True:
        errors.append("Password change, role downgrade, or deactivation MUST revoke active sessions/refresh tokens immediately.")

    return {"check": "session_config", "passed": len(errors) == 0, "errors": errors, "warnings": warnings}


def check_policy_matrix(matrix: dict[str, Any]) -> dict[str, Any]:
    errors: list[str] = []
    warnings: list[str] = []

    if matrix.get("deny_by_default") is not True:
        errors.append("Authorization policy MUST enforce deny_by_default=true.")

    routes = matrix.get("routes", [])
    if not isinstance(routes, list) or len(routes) == 0:
        errors.append("Policy matrix must enumerate >= 1 route.")
        return {"check": "policy_matrix", "passed": False, "errors": errors, "warnings": warnings}

    for r in routes:
        if not isinstance(r, dict):
            raise InvalidInput("Each routes entry must be a JSON object.")
        path = str(r.get("path", "<unknown>"))
        public = strict_bool(r.get("public", False), "public")
        privileged = strict_bool(r.get("privileged", False), "privileged")
        multi_tenant = strict_bool(r.get("multi_tenant", True), "multi_tenant")
        derives_tenant_from_body = strict_bool(r.get("derives_tenant_from_request_body", False), "derives_tenant_from_request_body")
        if derives_tenant_from_body:
            errors.append(f"Route '{path}' derives tenant_id or role from untrusted request body/params (confused deputy risk).")
        if public:
            if privileged:
                errors.append(f"Route '{path}' cannot be both public and privileged.")
            continue
        if r.get("server_auth_enforced") is not True:
            errors.append(f"Route '{path}' lacks server-side authentication enforcement (UI guard alone is insufficient).")
        if multi_tenant and r.get("tenant_scoped_in_query") is not True:
            errors.append(f"Multi-tenant route '{path}' must scope DB queries by authenticated tenant_id / RLS (anti-IDOR).")
        tests = r.get("negative_tests", {})
        if not isinstance(tests, dict) or tests.get("unauth_401") is not True:
            errors.append(f"Route '{path}' missing negative test asserting 401 for unauthenticated caller.")
        if multi_tenant and (not isinstance(tests, dict) or tests.get("cross_tenant_denied") is not True):
            errors.append(f"Route '{path}' missing cross-tenant IDOR denial test (403/404).")
        if privileged and (not isinstance(tests, dict) or tests.get("role_denied_403") is not True):
            errors.append(f"Privileged route '{path}' missing role-denial negative test (403).")

    return {"check": "policy_matrix", "passed": len(errors) == 0, "errors": errors, "warnings": warnings}


def check_sso_coexistence(cfg: dict[str, Any]) -> dict[str, Any]:
    errors: list[str] = []
    warnings: list[str] = []

    if cfg.get("oidc_pkce_s256") is not True:
        errors.append("OIDC Authorization Code flow MUST enforce PKCE S256.")
    if cfg.get("state_and_nonce_verified") is not True:
        errors.append("OIDC flow MUST verify single-use state (CSRF) and nonce (ID-token replay).")
    if strict_bool(cfg.get("tenant_bound_from_email_domain_only", False), "tenant_bound_from_email_domain_only"):
        errors.append("NEVER bind enterprise tenant solely from unverified email domain suffix; bind via verified IdP connection metadata.")
    if strict_bool(cfg.get("local_sdk_replaced_with_unverified_npm", False), "local_sdk_replaced_with_unverified_npm"):
        errors.append("CRITICAL: Do NOT replace an existing local SSO SDK (e.g., file:../sdk/sso-client) with an unverified npm package.")
    if cfg.get("coexisting_cookie_and_jwks_unified_principal") is not True:
        errors.append("Coexisting external SSO, local cookie session, and JWKS JWT must resolve into one canonical server principal + tenant context.")
    if cfg.get("audit_log_enabled") is not True:
        warnings.append("Enable immutable append-only audit_logs for SSO login, role changes, and revocations.")

    return {"check": "sso_coexistence", "passed": len(errors) == 0, "errors": errors, "warnings": warnings}


def run_self_test() -> dict[str, Any]:
    probes: list[tuple[str, bool]] = []

    # PRECISION-1: Hardened Argon2id + HttpOnly/Secure/Lax + EdDSA/RS256 short TTL JWT passes
    r1 = check_session_config(
        {
            "password_hash_algo": "argon2id",
            "cookie": {"enabled": True, "http_only": True, "secure": True, "same_site": "Lax"},
            "jwt": {
                "enabled": True,
                "alg": "EdDSA",
                "allowed_algs": ["EdDSA", "RS256"],
                "access_ttl_sec": 600,
                "refresh_rotation_family_revocation": True,
                "jwks_kid_rollover_supported": True,
            },
            "trust_frontend_username_claim": False,
            "revoke_on_password_or_role_change": True,
        }
    )
    probes.append(("PRECISION-1: Hardened Argon2id + cookie + rotating EdDSA/RS256 JWT passes", r1["passed"] is True))

    # RECALL-1: SHA256 password hash, alg=none, 24h TTL & frontend username trust rejected
    r2 = check_session_config(
        {
            "password_hash_algo": "sha256",
            "cookie": {"enabled": True, "http_only": False, "secure": False, "same_site": "None"},
            "jwt": {"enabled": True, "alg": "none", "allowed_algs": ["none"], "access_ttl_sec": 86400},
            "trust_frontend_username_claim": True,
            "revoke_on_password_or_role_change": False,
        }
    )
    probes.append(("RECALL-1: Weak password hash, alg=none, insecure cookie & frontend username trust rejected", r2["passed"] is False and len(r2["errors"]) >= 6))

    # PRECISION-2: Deny-by-default tenant-scoped policy matrix with full negative tests passes
    r3 = check_policy_matrix(
        {
            "deny_by_default": True,
            "routes": [
                {
                    "path": "GET /api/v1/invoices/:id",
                    "multi_tenant": True,
                    "privileged": False,
                    "server_auth_enforced": True,
                    "tenant_scoped_in_query": True,
                    "derives_tenant_from_request_body": False,
                    "negative_tests": {"unauth_401": True, "cross_tenant_denied": True},
                },
                {
                    "path": "POST /api/v1/admin/export",
                    "multi_tenant": True,
                    "privileged": True,
                    "server_auth_enforced": True,
                    "tenant_scoped_in_query": True,
                    "derives_tenant_from_request_body": False,
                    "negative_tests": {"unauth_401": True, "cross_tenant_denied": True, "role_denied_403": True},
                },
            ],
        }
    )
    probes.append(("PRECISION-2: Deny-by-default tenant-scoped policy matrix passes", r3["passed"] is True))

    # RECALL-2: Cross-tenant IDOR (unscoped query + tenant_id from body + missing tests) rejected
    r4 = check_policy_matrix(
        {
            "deny_by_default": False,
            "routes": [
                {
                    "path": "GET /api/v1/invoices/:id",
                    "multi_tenant": True,
                    "privileged": True,
                    "server_auth_enforced": True,
                    "tenant_scoped_in_query": False,
                    "derives_tenant_from_request_body": True,
                    "negative_tests": {},
                }
            ],
        }
    )
    probes.append(("RECALL-2: Unscoped IDOR route & body-derived tenant_id rejected", r4["passed"] is False and len(r4["errors"]) >= 4))

    # PRECISION-3: Coexisting external OIDC SSO + local cookie + JWKS with preserved SDK passes
    r5 = check_sso_coexistence(
        {
            "oidc_pkce_s256": True,
            "state_and_nonce_verified": True,
            "tenant_bound_from_email_domain_only": False,
            "local_sdk_replaced_with_unverified_npm": False,
            "coexisting_cookie_and_jwks_unified_principal": True,
            "audit_log_enabled": True,
        }
    )
    probes.append(("PRECISION-3: Coexisting OIDC PKCE + cookie + JWKS with preserved local SDK passes", r5["passed"] is True))

    # RECALL-3: Unverified npm SSO swap & email-domain-only tenant binding rejected
    r6 = check_sso_coexistence(
        {
            "oidc_pkce_s256": False,
            "state_and_nonce_verified": False,
            "tenant_bound_from_email_domain_only": True,
            "local_sdk_replaced_with_unverified_npm": True,
            "coexisting_cookie_and_jwks_unified_principal": False,
        }
    )
    probes.append(("RECALL-3: Unverified npm SSO swap, missing PKCE & email-domain tenant binding rejected", r6["passed"] is False and len(r6["errors"]) >= 5))

    # RECALL-4: bcrypt cost < 12 rejected
    r7 = check_session_config(
        {
            "password_hash_algo": "bcrypt",
            "bcrypt_cost": 8,
            "cookie": {"enabled": True, "http_only": True, "secure": True, "same_site": "Strict"},
            "revoke_on_password_or_role_change": True,
        }
    )
    probes.append(("RECALL-4: Low bcrypt cost (<12) rejected", r7["passed"] is False))

    passed = sum(1 for _, ok in probes if ok)
    return {
        "tool": "auth_policy_verifier.py",
        "total_probes": len(probes),
        "passed": passed,
        "failed": len(probes) - passed,
        "all_passed": passed == len(probes),
        "results": [{"probe": n, "passed": ok} for n, ok in probes],
    }


def _load_json(path_str: str) -> dict[str, Any]:
    raw = json.loads(Path(path_str).read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise ValueError(f"Expected JSON object in {path_str}")
    return raw


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Offline AuthN/AuthZ, Session/JWT & SSO Policy Verifier")
    parser.add_argument("--self-test", action="store_true", help="Run built-in precision & recall probes")
    parser.add_argument("--check-session-config", metavar="PATH", help="Validate password/cookie/JWT/revocation config JSON")
    parser.add_argument("--check-policy-matrix", metavar="PATH", help="Validate multi-tenant route policy matrix JSON")
    parser.add_argument("--check-sso-coexistence", metavar="PATH", help="Validate OIDC/SSO + cookie + JWKS coexistence JSON")
    args = parser.parse_args(argv)

    if args.self_test:
        res = run_self_test()
        print(json.dumps(res, indent=2))
        return 0 if res["all_passed"] else 1
    if args.check_session_config:
        res = check_session_config(_load_json(args.check_session_config))
        print(json.dumps(res, indent=2))
        return 0 if res["passed"] else 1
    if args.check_policy_matrix:
        res = check_policy_matrix(_load_json(args.check_policy_matrix))
        print(json.dumps(res, indent=2))
        return 0 if res["passed"] else 1
    if args.check_sso_coexistence:
        res = check_sso_coexistence(_load_json(args.check_sso_coexistence))
        print(json.dumps(res, indent=2))
        return 0 if res["passed"] else 1

    parser.print_help()
    return 2


if __name__ == "__main__":
    sys.exit(run_checked_cli(main))
