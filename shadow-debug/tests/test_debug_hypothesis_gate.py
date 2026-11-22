import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import debug_hypothesis_gate as dhg


class DebugHypothesisGateTests(unittest.TestCase):
    def test_self_test_probes(self) -> None:
        report = dhg.run_self_test()
        self.assertTrue(report["all_passed"], report)

    def test_rejects_symptom_copied_as_root_cause(self) -> None:
        res = dhg.validate_debug_report({
            "symptom": "API returns HTTP 500",
            "root_cause": "API returns HTTP 500",
            "hypotheses_tested": [
                {"id": "H1", "status": "CONFIRMED", "disconfirming_observation": "saw error line"},
                {"id": "H2", "status": "REFUTED", "disconfirming_observation": "none"},
            ],
            "evidence": [
                {"phase": "before_fix", "command": "pytest", "exit_code": 1},
                {"phase": "after_fix", "command": "pytest", "exit_code": 0},
            ],
        })
        self.assertFalse(res["valid"])
        self.assertTrue(any("merely repeats" in e for e in res["errors"]))

    def test_rejects_unredacted_postgres_dsn(self) -> None:
        res = dhg.validate_debug_report({
            "symptom": "Connection pool exhausted",
            "root_cause": "Unclosed transaction on postgres://admin:supersecret@db.internal:5432/prod",
            "hypotheses_tested": [
                {"id": "H1", "status": "REFUTED", "disconfirming_observation": "CPU low"},
                {"id": "H2", "status": "CONFIRMED", "disconfirming_observation": "idle in transaction"},
            ],
            "evidence": [
                {"phase": "before_fix", "command": "pytest tests/test_pool.py", "exit_code": 1},
                {"phase": "after_fix", "command": "pytest tests/test_pool.py", "exit_code": 0},
            ],
        })
        self.assertFalse(res["valid"])
        self.assertTrue(any("Unredacted secret" in e for e in res["errors"]))


if __name__ == "__main__":
    unittest.main()
