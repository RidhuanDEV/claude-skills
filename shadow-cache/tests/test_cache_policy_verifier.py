import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import cache_policy_verifier as cpv


class CachePolicyVerifierTests(unittest.TestCase):
    def test_self_test_probes(self) -> None:
        report = cpv.run_self_test()
        self.assertTrue(report["all_passed"], report)
        self.assertEqual(report["total_probes"], 7)

    def test_public_scope_redis_key_does_not_require_tenant_id(self) -> None:
        violations = cpv.check_cache_config({
            "redis_keys": [
                {
                    "pattern": "prod:public:countries:v1:all",
                    "scope": "public",
                    "ttl_sec": 3600,
                }
            ]
        })
        self.assertEqual(violations, [])

    def test_s_maxage_on_pii_route_rejected(self) -> None:
        violations = cpv.check_cache_config({
            "http_routes": [
                {
                    "path": "/api/v1/patients/me",
                    "contains_pii": True,
                    "cache_control": "max-age=60, s-maxage=300",
                }
            ]
        })
        codes = {item["code"] for item in violations}
        self.assertIn("PUBLIC_CACHE_ON_PRIVATE_ROUTE", codes)


if __name__ == "__main__":
    unittest.main()
