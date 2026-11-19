import copy
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from compare_search_indexes import compare

FIXTURE = Path(__file__).parent / "fixtures" / "search-index-pilot.json"


class PairedPilotTests(unittest.TestCase):
    def setUp(self):
        self.fixture = json.loads(FIXTURE.read_text(encoding="utf-8"))
        self.row = self.fixture["candidate"]["results"]["refund-id"]

    def result(self):
        return compare(self.fixture, "acl-7")

    def test_paired_reference_scores(self):
        report = self.result()
        self.assertEqual(report["decision"], "ELIGIBLE_FOR_REVIEW")
        self.assertAlmostEqual(report["pairs"]["refund-id"]["ndcg_delta"], 0.36907, places=4)
        self.assertEqual(report["segments"]["id"]["paired_count"], 1)

    def test_authorization_leak_overrides_perfect_recall(self):
        self.row["ranking"].append("B-policy")
        self.row["context"].append("B-policy")
        report = self.result()
        self.assertEqual(report["decision"], "HOLD")
        self.assertEqual(report["candidate"]["violations"][0]["reason"], "unauthorized_context")

    def test_revocation_before_generation(self):
        self.row["ranking"].append("A-expired")
        self.row["context"].append("A-expired")
        self.assertEqual(self.result()["decision"], "HOLD")

    def test_context_not_in_retrieval(self):
        self.row["ranking"] = ["A-policy"]
        self.row["context"].append("A-other")
        self.assertTrue(self.result()["candidate"]["violations"])

    def test_judgments_cannot_be_asserted_by_candidate(self):
        self.row["claims"][0].update(claim="Unverified answer", supported=True)
        self.assertFalse(self.result()["candidate"]["answers"]["gate_passed"])

    def test_insufficient_segment(self):
        self.fixture["min_queries_per_segment"] = 2
        self.assertIn("insufficient_pairs:id", self.result()["reasons"])

    def test_missing_labels(self):
        self.fixture["queries"]["refund-id"]["relevance_grades"] = {}
        self.assertEqual(self.result()["decision"], "HOLD")

    def test_regression_in_small_segment_despite_global_improvement(self):
        # Two English queries improve, one Indonesian query regresses.
        for side in ("baseline", "candidate"):
            results = self.fixture[side]["results"]
            results["refund-en-2"] = copy.deepcopy(results["refund-en"])
        self.fixture["queries"]["refund-en-2"] = copy.deepcopy(self.fixture["queries"]["refund-en"])
        self.fixture["baseline"]["results"]["refund-id"]["ranking"].reverse()
        self.row["ranking"].reverse()
        report = self.result()
        self.assertGreater(report["candidate"]["search"]["ndcg_at_k"], report["baseline"]["search"]["ndcg_at_k"])
        self.assertIn("segment_regression:id", report["reasons"])

    def test_generation_recall_regression_inside_one_language(self):
        for i in range(4):
            query_id = f"extra-en-{i}"
            self.fixture["queries"][query_id] = copy.deepcopy(self.fixture["queries"]["refund-en"])
            for side in ("baseline", "candidate"):
                results = self.fixture[side]["results"]
                results[query_id] = copy.deepcopy(results["refund-en"])
        self.fixture["queries"]["refund-id"]["relevance_grades"]["A-other"] = 1
        self.fixture["baseline"]["results"]["refund-id"]["context"].append("A-other")
        report = self.result()
        self.assertTrue(report["candidate"]["answers"]["gate_passed"])
        self.assertIn("answer_regression:id:context_recall", report["reasons"])
        self.assertEqual(report["segments"]["id"]["answer_deltas"]["context_recall"], -0.5)

    def test_stale_policy(self):
        self.assertEqual(compare(self.fixture, "acl-8")["reasons"], ["stale_acl_snapshot"])

    def test_cli_rejects_trace_from_different_snapshot(self):
        self.fixture["candidate"]["corpus_revision"] = "other"
        with tempfile.TemporaryDirectory() as directory:
            file = Path(directory, "trace.json")
            file.write_text(json.dumps(self.fixture))
            result = subprocess.run([sys.executable, str(FIXTURE.parents[1] / "compare_search_indexes.py"),
                                     str(file), "--acl-revision", "acl-7"], capture_output=True, text=True)
        self.assertEqual(result.returncode, 1)
        self.assertEqual(json.loads(result.stdout)["reasons"], ["invalid_input"])


if __name__ == "__main__":
    unittest.main()
