from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "uat_evidence_verifier.py"
_spec = importlib.util.spec_from_file_location("uat_evidence_verifier", SCRIPT)
assert _spec is not None and _spec.loader is not None
uat_evidence_verifier = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(uat_evidence_verifier)


def run_cli(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-B", str(SCRIPT), *args], capture_output=True, text=True, timeout=60, check=False,
    )

ROWS = [{"id": "1", "status": "PAID"}, {"id": "2", "status": "PENDING"}]


def drift(filtered: list[dict[str, str]], unfiltered: list[dict[str, str]] = ROWS) -> str:
    evidence = {"param": "status", "expected_value": "PAID", "unfiltered_rows": unfiltered, "filtered_rows": filtered}
    return str(uat_evidence_verifier.check_param_effect(evidence)["status"])


class BatchUatAndParamDriftTests(unittest.TestCase):
    def test_t23_e03_ignored_query_param_and_incomplete_batch(self) -> None:
        self.assertEqual(drift(ROWS), "DRIFT_IGNORED_QUERY_PARAM")
        self.assertEqual(drift([ROWS[0]]), "VERIFIED")
        incomplete = uat_evidence_verifier.reconcile_batch(["FR-01", "FR-02"], {"FR-01": "PASS"})
        self.assertEqual((incomplete["signoff_ready"], incomplete["missing"]), (False, ["FR-02"]))
        ready = uat_evidence_verifier.reconcile_batch(["FR-01", "FR-02"], {"FR-01": "PASS", "FR-02": "PASS"})
        self.assertTrue(ready["signoff_ready"])

    def test_vacuous_or_malformed_evidence_never_signs_off(self) -> None:
        for expected, results in (([], {}), ([], {"FR-01": "PASS"}), ("FR-01", {"FR-01": "PASS"}),
                                  (["FR-01"], {"FR-01": True}), (["FR-01"], {"FR-01": "pass"})):
            with self.subTest(expected=expected, results=results):
                self.assertFalse(uat_evidence_verifier.reconcile_batch(expected, results)["signoff_ready"])

    def test_empty_or_short_filtered_result_is_drift_not_verified(self) -> None:
        self.assertEqual(drift([]), "DRIFT_EMPTY_RESULT")
        self.assertEqual(drift([], [{"id": "2", "status": "PENDING"}]), "INSUFFICIENT_EVIDENCE")
        two_paid = [{"id": "1", "status": "PAID"}, {"id": "3", "status": "PAID"}]
        self.assertEqual(drift([two_paid[0]], two_paid), "DRIFT_ROW_COUNT")

    def test_unexpected_results_are_reported(self) -> None:
        result = uat_evidence_verifier.reconcile_batch(["FR-01"], {"FR-01": "PASS", "FR-99": "PASS"})
        self.assertEqual(result["unexpected"], ["FR-99"])

    def test_cli_self_test(self) -> None:
        self.assertEqual(run_cli("--self-test").returncode, 0)


if __name__ == "__main__":
    unittest.main()
