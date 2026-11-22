import sys
import unittest
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))

import auth_policy_verifier as verifier  # noqa: E402


class AuthPolicyVerifierTests(unittest.TestCase):
    def test_self_test_probes(self) -> None:
        res = verifier.run_self_test()
        self.assertTrue(res["all_passed"], f"Self-test failures: {res}")
        self.assertEqual(res["total_probes"], 7)

    def test_rejects_public_route_bypass_on_protected_multi_tenant_route(self) -> None:
        res = verifier.check_policy_matrix(
            {
                "deny_by_default": True,
                "routes": [
                    {
                        "path": "DELETE /api/v1/tenants/:id/users/:uid",
                        "public": False,
                        "multi_tenant": True,
                        "privileged": True,
                        "server_auth_enforced": False,
                        "tenant_scoped_in_query": False,
                        "negative_tests": {"unauth_401": False, "cross_tenant_denied": False, "role_denied_403": False},
                    }
                ],
            }
        )
        self.assertFalse(res["passed"])
        self.assertGreaterEqual(len(res["errors"]), 4)

    def test_rejects_missing_refresh_family_revocation(self) -> None:
        res = verifier.check_session_config(
            {
                "password_hash_algo": "argon2id",
                "cookie": {"enabled": True, "http_only": True, "secure": True, "same_site": "Lax"},
                "jwt": {
                    "enabled": True,
                    "alg": "RS256",
                    "allowed_algs": ["RS256"],
                    "access_ttl_sec": 300,
                    "refresh_rotation_family_revocation": False,
                },
                "revoke_on_password_or_role_change": True,
            }
        )
        self.assertFalse(res["passed"])


if __name__ == "__main__":
    unittest.main()
