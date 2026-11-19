import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from drill_evidence import assess


class RecoveryTest(unittest.TestCase):
    def setUp(self):
        self.record = dict(disruption_at="2026-08-10T06:00:00Z",
                           business_verified_at="2026-08-10T13:15:00+07:00",
                           recovered_checkpoint_at="2026-08-10T05:59:30Z",
                           required_dependencies_verified=True,
                           consumer_workflow_passed=True,
                           checkpoint_verified_in_source_timeline=True)

    def test_business_workflow_and_watermark(self):
        self.assertEqual(assess(self.record), dict(rto_seconds=900, rpo_upper_bound_seconds=30, issues=[]))

    def test_idle_table(self):
        del self.record["recovered_checkpoint_at"]
        self.record["max_created_at"] = "2026-08-09T00:00:00Z"
        self.assertIsNone(assess(self.record)["rpo_upper_bound_seconds"])

    def test_missing_key_or_validation(self):
        for key in ("required_dependencies_verified", "consumer_workflow_passed"):
            with self.subTest(key=key):
                self.assertIsNone(assess({**self.record, key: False})["rto_seconds"])

    def test_reject_impossible_times(self):
        self.record["business_verified_at"] = "2026-08-10T05:59:59Z"
        self.record["recovered_checkpoint_at"] = "2026-08-10T06:00:01Z"
        self.assertEqual(len(assess(self.record)["issues"]), 2)
