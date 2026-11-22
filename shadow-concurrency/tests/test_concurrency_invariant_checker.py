import sys
import unittest
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))

import concurrency_invariant_checker as checker  # noqa: E402


class ConcurrencyInvariantCheckerTests(unittest.TestCase):
    def test_self_test_probes(self) -> None:
        res = checker.run_self_test()
        self.assertTrue(res["all_passed"], f"Self-test failures: {res}")

    def test_rejects_ack_before_commit_and_unassisted_exactly_once_claim(self) -> None:
        res = checker.simulate_at_least_once_replay(
            {
                "workflow_id": "WF-BAD-SMTP",
                "uses_durable_idempotency_store": False,
                "ack_before_durable_commit": True,
                "uses_atomic_claim_or_lock": False,
                "max_attempts": 0,
                "has_dlq": False,
                "claims_unassisted_exactly_once_external": True,
            }
        )
        self.assertFalse(res["valid"])
        self.assertEqual(res["delivery_guarantee"], "UNSAFE")
        self.assertGreaterEqual(len(res["errors"]), 5)


if __name__ == "__main__":
    unittest.main()
