import sys
import unittest
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))

import appsec_control_verifier as verifier  # noqa: E402


class AppsecControlVerifierTests(unittest.TestCase):
    def test_self_test_probes(self) -> None:
        res = verifier.run_self_test()
        self.assertTrue(res["all_passed"], f"Self-test failures: {res}")
        self.assertEqual(res["total_probes"], 7)

    def test_ssrf_blocks_hex_and_cgnat_and_userinfo(self) -> None:
        for bad_url in [
            "https://0x7f000001/admin",
            "https://100.64.0.1/internal",
            "https://admin:pass@partner.example/hook",
            "https://metadata.google.internal/computeMetadata/v1/",
        ]:
            res = verifier.check_ssrf_url(bad_url)
            self.assertFalse(res["passed"], f"Expected SSRF block for {bad_url}")

    def test_cors_exact_origin_without_vary_emits_warning_not_error(self) -> None:
        res = verifier.check_security_headers(
            {
                "Strict-Transport-Security": "max-age=31536000",
                "Content-Security-Policy": "default-src 'self'; object-src 'none'; frame-ancestors 'none'",
                "X-Content-Type-Options": "nosniff",
                "Referrer-Policy": "no-referrer",
                "Access-Control-Allow-Origin": "https://portal.example.com",
            }
        )
        self.assertTrue(res["passed"])
        self.assertTrue(any("Vary: Origin" in w for w in res["warnings"]))


if __name__ == "__main__":
    unittest.main()
