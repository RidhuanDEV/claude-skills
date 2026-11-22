import sys
import unittest
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))

import domain_invariant_verifier as verifier  # noqa: E402


class DomainInvariantVerifierTests(unittest.TestCase):
    def test_self_test_probes(self) -> None:
        res = verifier.run_self_test()
        self.assertTrue(res["all_passed"], f"Self-test failures: {res}")

    def test_blocks_full_ddd_on_simple_crud(self) -> None:
        res = verifier.verify_domain_model(
            {
                "bounded_context": "Categories",
                "is_simple_crud": True,
                "use_full_ddd": True,
                "state_transitions": {"ACTIVE": ["INACTIVE"]},
                "invariants": [{"id": "INV-1", "rule": "name non-empty"}],
            }
        )
        self.assertFalse(res["valid"])
        self.assertTrue(any("Overengineering" in e for e in res["errors"]))

    def test_blocks_terminal_state_backdating_transition(self) -> None:
        res = verifier.verify_domain_model(
            {
                "bounded_context": "FleetDispatch",
                "is_simple_crud": False,
                "use_full_ddd": True,
                "state_transitions": {
                    "SCHEDULED": ["IN_PROGRESS", "CANCELLED"],
                    "IN_PROGRESS": ["COMPLETED", "CANCELLED"],
                    "COMPLETED": [],
                },
                "invariants": [{"id": "INV-1", "rule": "completed trips immutable"}],
                "simulated_commands": [
                    {"from_state": "COMPLETED", "to_state": "SCHEDULED", "expected_allowed": True}
                ],
            }
        )
        self.assertFalse(res["valid"])


if __name__ == "__main__":
    unittest.main()
