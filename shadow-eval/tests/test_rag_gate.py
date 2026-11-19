import copy
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "ai_eval_gate.py"


def run_cli(option, *payloads):
    with tempfile.TemporaryDirectory() as tmp:
        paths = []
        for index, payload in enumerate(payloads):
            path = Path(tmp) / f"{index}.json"
            path.write_text(json.dumps(payload), encoding="utf-8")
            paths.append(str(path))
        process = subprocess.run([sys.executable, str(SCRIPT), option, *paths], capture_output=True, text=True)
    return process.returncode, json.loads(process.stdout)


def fixture():
    return {"sample_id": "policy", "sample_type": "answerable", "language": "id",
            "query": "kapan", "split": "holdout", "tenant_id": "A",
            "retrieved_chunks": [{"id": "doc", "tenant_id": "A"}],
            "expected_chunk_ids": ["doc"], "answer_citations": ["doc"], "abstained": False,
            "claims": [{"claim": "14 hari", "citations": ["doc"], "supported": True}]}


def runs():
    baseline = {"revision": "a", "corpus_snapshot": "frozen", "acl_revision": "acl-7",
                "judgment_revision": "labels-4", "development_sample_ids": [], "samples": [fixture()]}
    candidate = copy.deepcopy(baseline)
    candidate["revision"] = "b"
    return baseline, candidate


class RagGateTests(unittest.TestCase):
    def test_standalone_revoked_chunk_blocks_even_if_reviewer_supports_it(self):
        row = fixture()
        row["retrieved_chunks"][0]["deleted_or_revoked"] = True
        code, result = run_cli("--score-rag", [row])
        self.assertEqual((code, result["status"], result["revoked_hits"]), (1, "FAIL", 1))
        self.assertEqual(result["claim_support"], 0)
        self.assertEqual(result["context_recall"], 0)
        self.assertEqual(result["citation_integrity"], 0)

    def test_invalid_revocation_marker_is_unmeasured(self):
        row = fixture()
        row["retrieved_chunks"][0]["deleted_or_revoked"] = "false"
        code, result = run_cli("--score-rag", [row])
        self.assertEqual((code, result["status"]), (1, "INCOMPLETE"))

    def test_answerable_and_abstain_have_distinct_denominators(self):
        row = fixture()
        abstain = {"sample_id": "none", "sample_type": "abstain", "language": "id",
                   "tenant_id": "A", "retrieved_chunks": [], "abstained": True}
        code, result = run_cli("--score-rag", [row, abstain])
        self.assertEqual((code, result["status"]), (0, "PASS"))
        coverage = result["coverage"]
        for key in ("answer_decisions", "abstain_decisions", "recall_samples", "judged_claims"):
            self.assertEqual(coverage[key], 1)
        abstain["abstained"] = False
        code, result = run_cli("--score-rag", [row, abstain])
        self.assertEqual((code, result["false_accepts"], result["gate_passed"]), (1, 1, False))

    def test_legacy_clean_and_empty_evidence(self):
        legacy = {"tenant_id": "A", "expected_chunk_ids": ["doc"], "answer_citations": ["doc"],
                  "retrieved_chunks": [{"id": "doc", "tenant_id": "A"}]}
        code, result = run_cli("--score-rag", {"samples": [legacy]})
        self.assertEqual((code, result["claim_support"]), (0, None))
        code, result = run_cli("--score-rag", [{}])
        self.assertEqual((code, result["gate_passed"], result["context_recall"]), (1, False, None))

    def test_comparison_valid_alignment_and_revocation(self):
        base, candidate = runs()
        code, result = run_cli("--compare-rag", base, candidate)
        self.assertEqual((code, result["status"], result["sample_ids"]), (0, "PASS", ["policy"]))
        candidate["samples"][0]["retrieved_chunks"][0]["deleted_or_revoked"] = True
        code, result = run_cli("--compare-rag", base, candidate)
        self.assertEqual((code, result["status"]), (1, "FAIL"))
        self.assertEqual(result["by_language"]["id"]["revoked_hits"]["delta"], 1)

    def test_cli_detects_noncomparable_runs(self):
        for key, value in (("revision", "a"), ("acl_revision", "stale"), ("judgment_revision", "unknown"),
                           ("corpus_snapshot", "other"), ("development_sample_ids", ["policy"])):
            with self.subTest(key=key):
                base, candidate = runs()
                candidate[key] = value
                code, result = run_cli("--compare-rag", base, candidate)
                self.assertEqual((code, result["status"], result["comparable"]), (1, "INCOMPLETE", False))
        base, candidate = runs()
        candidate["samples"][0]["expected_chunk_ids"] = ["other"]
        self.assertFalse(run_cli("--compare-rag", base, candidate)[1]["comparable"])


if __name__ == "__main__":
    unittest.main()
