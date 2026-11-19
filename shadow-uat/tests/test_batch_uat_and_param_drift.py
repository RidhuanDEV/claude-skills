from __future__ import annotations

import unittest


def check_query_param_effect(
    unfiltered_rows: list[dict[str, str]],
    filtered_rows: list[dict[str, str]],
    param_name: str,
    expected_value: str,
) -> dict[str, object]:
    """Detect silently ignored query parameters (E03 API/UAT contract drift)."""
    leaking = [r for r in filtered_rows if r.get(param_name) != expected_value]
    if leaking:
        return {
            "status": "DRIFT_IGNORED_QUERY_PARAM",
            "param": param_name,
            "unexpected_rows": len(leaking),
        }
    return {
        "status": "VERIFIED",
        "param": param_name,
        "reduced_from": len(unfiltered_rows),
        "reduced_to": len(filtered_rows),
    }


def reconcile_headless_batch_uat(expected_ids: set[str], executed_results: dict[str, str]) -> dict[str, object]:
    missing = sorted(expected_ids - set(executed_results.keys()))
    failed = sorted(k for k, v in executed_results.items() if v != "PASS")
    return {
        "signoff_ready": not missing and not failed,
        "missing": missing,
        "failed": failed,
    }


class BatchUatAndParamDriftTests(unittest.TestCase):
    def test_t23_e03_detects_silently_ignored_query_param_and_incomplete_batch_uat(self) -> None:
        all_rows = [
            {"id": "1", "status": "PAID"},
            {"id": "2", "status": "PENDING"},
        ]
        # Buggy endpoint ignores ?status=PAID and returns all rows
        drift = check_query_param_effect(all_rows, all_rows, "status", "PAID")
        self.assertEqual(drift["status"], "DRIFT_IGNORED_QUERY_PARAM")

        # Fixed endpoint honors ?status=PAID
        fixed = check_query_param_effect(all_rows, [all_rows[0]], "status", "PAID")
        self.assertEqual(fixed["status"], "VERIFIED")

        uat_incomplete = reconcile_headless_batch_uat({"FR-01", "FR-02"}, {"FR-01": "PASS"})
        self.assertFalse(uat_incomplete["signoff_ready"])
        self.assertEqual(uat_incomplete["missing"], ["FR-02"])

        uat_ready = reconcile_headless_batch_uat({"FR-01", "FR-02"}, {"FR-01": "PASS", "FR-02": "PASS"})
        self.assertTrue(uat_ready["signoff_ready"])


if __name__ == "__main__":
    unittest.main()
