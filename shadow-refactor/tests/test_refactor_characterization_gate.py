import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import refactor_characterization_gate as rcg


class RefactorCharacterizationGateTests(unittest.TestCase):
    def test_self_test_probes(self) -> None:
        report = rcg.run_self_test()
        self.assertTrue(report["all_passed"], report)

    def test_rejects_missing_before_characterization_pass(self) -> None:
        res = rcg.verify_refactor_plan({
            "precedents_inspected": ["src/orders/discount.ts"],
            "invariants_locked": ["exact 422 envelope"],
            "characterization_suite": {
                "cases_count": 3,
                "before_refactor_exit_code": 1,
                "after_refactor_exit_code": 0,
            },
            "changed_files": ["src/orders/pricing.ts"],
            "allowed_scope_files": ["src/orders/pricing.ts"],
            "rollback": "git checkout -- src/orders/pricing.ts",
        })
        self.assertFalse(res["valid"])
        self.assertTrue(any("exit 0 both before and after" in e for e in res["errors"]))

    def test_rejects_missing_rollback_plan(self) -> None:
        res = rcg.verify_refactor_plan({
            "precedents_inspected": ["src/orders/discount.ts"],
            "invariants_locked": ["exact 422 envelope"],
            "characterization_suite": {
                "cases_count": 3,
                "before_refactor_exit_code": 0,
                "after_refactor_exit_code": 0,
            },
            "changed_files": ["src/orders/pricing.ts"],
            "allowed_scope_files": ["src/orders/pricing.ts"],
            "rollback": "",
        })
        self.assertFalse(res["valid"])
        self.assertTrue(any("rollback" in e.lower() for e in res["errors"]))


if __name__ == "__main__":
    unittest.main()
