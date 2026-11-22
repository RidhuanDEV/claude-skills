import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import telemetry_hygiene_verifier as thv


class TelemetryHygieneVerifierTests(unittest.TestCase):
    def test_self_test_probes(self) -> None:
        report = thv.run_self_test()
        self.assertTrue(report["all_passed"], report)
        self.assertEqual(report["total_probes"], 7)

    def test_head_sampling_without_tail_retention_rejected(self) -> None:
        violations = thv.check_metrics_config({
            "metrics": [{"name": "http_reqs", "labels": ["method", "status_class"]}],
            "alerts": [],
            "otel_sampling": {"head_sample_rate": 0.05},
        })
        codes = {item["code"] for item in violations}
        self.assertIn("HEAD_SAMPLING_DROPS_ERRORS", codes)

    def test_jwt_leak_inside_nested_field_rejected(self) -> None:
        fake_jwt = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIn0.abc123def456"
        violations = thv.check_log_sample({
            "ts": "2026-11-22T10:15:30Z",
            "level": "info",
            "event": "auth.checked",
            "traceId": "4bf92f3577b34da6a3ce929d0e0e4736",
            "meta": {"raw": fake_jwt},
        })
        codes = {item["code"] for item in violations}
        self.assertIn("SECRET_TOKEN_LEAK", codes)

    def test_non_paging_info_alert_does_not_require_burn_rate_window(self) -> None:
        violations = thv.check_metrics_config({
            "metrics": [],
            "alerts": [
                {
                    "name": "WorkerCpuAdvisory",
                    "severity": "info",
                    "paging": False,
                    "expr": "avg(node_cpu_seconds_total) > 0.75",
                }
            ],
        })
        self.assertEqual(violations, [])


if __name__ == "__main__":
    unittest.main()
