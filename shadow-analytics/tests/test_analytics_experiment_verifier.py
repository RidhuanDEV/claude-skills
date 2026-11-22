import sys
import unittest
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))

import analytics_experiment_verifier as verifier  # noqa: E402


class AnalyticsExperimentVerifierTests(unittest.TestCase):
    def test_self_test_probes(self) -> None:
        res = verifier.run_self_test()
        self.assertTrue(res["all_passed"], f"Self-test failures: {res}")
        self.assertEqual(res["total_probes"], 7)

    def test_monarch_benchmark_srm_blocks_significant_positive_lift(self) -> None:
        # +12% lift with p < 0.05, but SRM p ~ 0.00022 (< 0.001) MUST block shipping
        res = verifier.check_experiment(
            {
                "assignment_exposure_separated": True,
                "variants": [
                    {"name": "control", "expected_ratio": 0.5, "assigned_count": 10200, "conversions": 1020},
                    {"name": "treatment", "expected_ratio": 0.5, "assigned_count": 9680, "conversions": 1084},
                ],
            }
        )
        self.assertEqual(res["verdict"], "BLOCKED_SRM")
        self.assertTrue(res["metrics"]["srm_detected"])
        self.assertLess(res["metrics"]["srm_p_value"], 0.001)
        self.assertGreater(res["metrics"]["relative_lift"], 0.10)
        self.assertLess(res["metrics"]["p_value"], 0.05)

    def test_blocking_guardrail_overrides_positive_primary_lift(self) -> None:
        res = verifier.check_experiment(
            {
                "assignment_exposure_separated": True,
                "variants": [
                    {"name": "control", "expected_ratio": 0.5, "assigned_count": 20000, "conversions": 2000},
                    {"name": "treatment", "expected_ratio": 0.5, "assigned_count": 19980, "conversions": 2300},
                ],
                "guardrails": [{"name": "checkout_p95_latency", "regressed": True, "severity": "blocking"}],
            }
        )
        self.assertEqual(res["verdict"], "BLOCKED_GUARDRAIL")
        self.assertFalse(res["passed"])

    def test_complete_multi_vendor_dsar_passes(self) -> None:
        res = verifier.check_dsar_plan(
            {
                "warehouse_tables_covered": True,
                "warehouse_only": False,
                "configured_vendors": ["posthog", "ga4", "resend"],
                "vendor_deletion_apis_wired": ["posthog", "ga4", "resend"],
                "vendor_deletion_sla_days": {"posthog": 7, "ga4": 14, "resend": 1},
                "max_allowed_sla_days": 30,
                "suppression_tombstone_hashed": True,
            }
        )
        self.assertTrue(res["passed"])


if __name__ == "__main__":
    unittest.main()
