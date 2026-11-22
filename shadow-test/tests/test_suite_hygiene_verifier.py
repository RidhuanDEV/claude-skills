import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import suite_hygiene_verifier as thv


class TestHygieneVerifierTests(unittest.TestCase):
    def test_self_test_probes(self) -> None:
        report = thv.run_self_test()
        self.assertTrue(report["all_passed"], report)
        self.assertEqual(report["total_probes"], 7)

    def test_public_endpoint_may_explicitly_exempt_auth_surfaces(self) -> None:
        violations = thv.check_test_hygiene({
            "http_endpoint_suites": [
                {
                    "endpoint": "GET /api/v1/public/catalog",
                    "covered_surfaces": [
                        "happy_path",
                        "validation_4xx",
                        "not_found_404",
                        "boundary_values",
                        "state_cleanup",
                    ],
                    "not_applicable": [
                        "unauthenticated_401",
                        "forbidden_idor_403",
                        "conflict_idempotency_409",
                    ],
                }
            ]
        })
        self.assertEqual(violations, [])

    def test_playwright_wait_for_timeout_rejected(self) -> None:
        violations = thv.check_test_hygiene({
            "test_snippets": [
                {
                    "file": "tests/modal.test.ts",
                    "language": "ts",
                    "code": "await page.waitForTimeout(2000); expect(modal).toBeVisible();",
                }
            ]
        })
        codes = {x["code"] for x in violations}
        self.assertIn("FLAKY_WALL_CLOCK_SLEEP", codes)


if __name__ == "__main__":
    unittest.main()
