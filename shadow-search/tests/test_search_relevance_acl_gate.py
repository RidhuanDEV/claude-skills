"""Run with python -m unittest discover -s shadow-search/tests."""

import copy
import json
import math
from pathlib import Path
import runpy
import subprocess
import sys
import tempfile
import unittest


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "search_relevance_acl_gate.py"
module = runpy.run_path(str(SCRIPT))
evaluate = module["evaluate_search_dataset"]
fuse = module["reciprocal_rank_fusion"]


def query(name="id-exact", segment="id"):
    return {
        "query_id": name, "segment": segment, "tenant_id": "A",
        "relevance_grades": {"doc": 3, "other": 1},
        "retrieved": [{"id": "doc", "tenant_id": "A"}, {"id": "other", "tenant_id": "A"}],
    }


class RetrievalTests(unittest.TestCase):
    def test_duplicates_keep_rank_and_do_not_inflate_gain(self):
        q = query()
        q["retrieved"].insert(1, q["retrieved"][0])
        r = evaluate({"queries": [q], "k": 3})
        self.assertTrue(r["valid"])
        self.assertEqual(r["recall_at_k"], 1)
        self.assertAlmostEqual(r["ndcg_at_k"], (7 + 0.5) / (7 + 1 / math.log2(3)), places=4)
        self.assertEqual(r["query_results"][0]["duplicate_hits_at_k"], 1)
        self.assertEqual(evaluate({"queries": [q], "k": 2})["recall_at_k"], 0.5)

    def test_duplicate_within_one_rrf_list_does_not_outvote_consensus(self):
        self.assertEqual(fuse([["b", "b", "b", "a"], ["a"]]), ["a", "b"])

    def test_unjudged_and_observed_zero_differ(self):
        empty = query("e")
        empty["retrieved"] = []
        r = evaluate({"min_ndcg": 0, "queries": [empty]})
        self.assertTrue(r["valid"])
        self.assertEqual(r["ndcg_at_k"], 0)
        for grades in [{}, {"doc": 0}]:
            with self.subTest(grades=grades):
                q = query()
                q["relevance_grades"] = grades
                r = evaluate({"queries": [q, empty], "min_ndcg": 0})
                self.assertFalse(r["valid"])
                self.assertEqual(r["evidence_status"], "INSUFFICIENT_EVIDENCE")
                self.assertEqual(r["measured_queries"], 1)
                self.assertIsNone(r["query_results"][0]["ndcg_at_k"])
                self.assertEqual(r["segments"]["id"]["total_queries"], 2)

    def test_unjudged_and_below_k_still_check_access(self):
        q = query()
        q["relevance_grades"] = {}
        q["retrieved"][1]["tenant_id"] = "B"
        q["revoked_document_ids"] = ["other"]
        r = evaluate({"k": 1, "queries": [q]})
        self.assertFalse(r["valid"])
        self.assertEqual((r["acl_leaks"], r["revoked_leaks"]), (1, 1))
        self.assertEqual(r["query_results"][0]["evidence_status"], "ACCESS_VIOLATION")
        self.assertIsNone(r["ndcg_at_k"])
        self.assertNotIn('"other"', json.dumps(r))

    def test_same_tenant_still_needs_permission(self):
        q = query()
        q["allowed_document_ids"] = []
        r = evaluate({"queries": [q]})
        self.assertEqual(r["acl_leaks"], 2)
        self.assertFalse(r["valid"])

    def test_shape_type_and_range_contracts(self):
        invalid = [
            {}, {"queries": [{}]}, {"queries": "x"}, {"queries": [None]},
            *[{"queries": [query()], "k": k} for k in [True, 0, -1, "5", 1.5]],
            *[{"queries": [query()], "min_ndcg": t} for t in [True, -1, 2, "0.7", float("nan")]],
            {"queries": [query()], "uses_uncalibrated_fixed_similarity_threshold": "false"},
        ]
        for patch in [
            {"tenant_id": ""}, {"query_id": 1}, {"segment": False}, {"retrieved": None},
            {"retrieved": [{"id": "d"}]}, {"retrieved": [{"id": "d", "tenant_id": ""}]},
            {"retrieved": [{"id": "d", "tenant_id": "A", "deleted_or_revoked": "false"}]},
            {"allowed_document_ids": "abc"}, {"revoked_document_ids": [True]},
            *[{"relevance_grades": {"doc": g}} for g in [True, 0.5, "1", -1, 4]],
        ]:
            invalid.append({"queries": [dict(query(), **patch)]})
        for spec in invalid:
            with self.subTest(spec=spec):
                self.assertEqual(evaluate(spec)["evidence_status"], "INVALID_INPUT")

    def test_paired_queries_and_segments(self):
        queries = [query(), query("en-code", "en")]
        base = evaluate({"queries": queries})
        candidate = copy.deepcopy(queries)
        candidate[1]["retrieved"] = []
        new = evaluate({"queries": list(reversed(candidate))})
        self.assertEqual(base["segments"]["id"], new["segments"]["id"])
        self.assertEqual(new["segments"]["en"]["ndcg_at_k"], 0)
        self.assertEqual(new["query_results"][0]["query_id"], "en-code")
        self.assertFalse(evaluate({"queries": [queries[0], queries[0]]})["valid"])

    def test_rounding_cannot_rescue_missed_threshold(self):
        q = query()
        q["retrieved"].insert(1, q["retrieved"][0])
        r = evaluate({"queries": [q], "min_ndcg": 0})
        score = r["query_results"][0]["ndcg_at_k"]
        self.assertFalse(evaluate({"queries": [q], "min_ndcg": score + 0.000001})["valid"])

    def test_cli_rejects_malformed_json_with_structured_error(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "broken.json"
            path.write_text("{", encoding="utf-8")
            p = subprocess.run([sys.executable, str(SCRIPT), "--evaluate", str(path)],
                               capture_output=True, text=True, check=False)
        self.assertEqual(p.returncode, 1)
        self.assertEqual(json.loads(p.stdout)["evidence_status"], "INVALID_INPUT")
        self.assertEqual(p.stderr, "")


if __name__ == "__main__":
    unittest.main()
