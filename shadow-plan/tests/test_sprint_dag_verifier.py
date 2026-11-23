from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from sprint_dag_verifier import audit_sprint_plan, run_self_test


class SprintDagVerifierTests(unittest.TestCase):
    def test_self_test_all_precision_and_recall_probes_pass(self) -> None:
        report = run_self_test()
        self.assertTrue(report["all_passed"], report)
        self.assertEqual(report["total_probes"], 7)
        self.assertEqual(report["failed"], 0)

    def test_computes_deterministic_execution_waves_for_diamond_dag(self) -> None:
        plan = {
            "tasks": [
                {
                    "task_id": "W0-CONTRACT",
                    "title": "Shared API & DB Contract",
                    "kind": "enabler",
                    "approval_tier": "L1",
                    "depends_on": [],
                    "definition_of_ready": ["FR locked"],
                    "definition_of_done": ["Contract green"],
                },
                {
                    "task_id": "W1-API",
                    "title": "Order Approve Endpoint",
                    "kind": "feature",
                    "fr_ref": "FR-ORD-012",
                    "story_id": "US-014",
                    "ac_refs": ["AC-ORD-012-01"],
                    "approval_tier": "L1",
                    "depends_on": ["W0-CONTRACT"],
                    "definition_of_ready": ["Schema ready"],
                    "definition_of_done": ["403/409 tests green"],
                },
                {
                    "task_id": "W1-UI",
                    "title": "Order Approve Modal",
                    "kind": "feature",
                    "fr_ref": "FR-ORD-012",
                    "story_id": "US-014",
                    "ac_refs": ["AC-ORD-012-02"],
                    "approval_tier": "L1",
                    "depends_on": ["W0-CONTRACT"],
                    "definition_of_ready": ["9-state design locked"],
                    "definition_of_done": ["375px overflow clean"],
                },
                {
                    "task_id": "W2-QA",
                    "title": "Integrated Order Verification",
                    "kind": "feature",
                    "fr_ref": "FR-ORD-012",
                    "story_id": "US-014",
                    "ac_refs": ["AC-ORD-012-01", "AC-ORD-012-02"],
                    "approval_tier": "L1",
                    "depends_on": ["W1-API", "W1-UI"],
                    "definition_of_ready": ["API & UI merged"],
                    "definition_of_done": ["All negative cases pass"],
                },
            ]
        }
        result = audit_sprint_plan(plan)
        self.assertEqual(result["status"], "PASS")
        self.assertTrue(result["is_acyclic"])
        self.assertEqual(
            result["waves"],
            [["W0-CONTRACT"], ["W1-API", "W1-UI"], ["W2-QA"]],
        )

    def test_rejects_unknown_dependency_and_missing_dor_dod(self) -> None:
        plan = {
            "tasks": [
                {
                    "task_id": "T-1",
                    "title": "Build Invoice Slice",
                    "kind": "feature",
                    "fr_ref": "FR-INV-001",
                    "story_id": "US-001",
                    "ac_refs": ["AC-INV-001-01"],
                    "approval_tier": "L1",
                    "depends_on": ["T-DOES-NOT-EXIST"],
                    "definition_of_ready": [],
                    "definition_of_done": [],
                }
            ]
        }
        result = audit_sprint_plan(plan)
        rules = {f["rule_id"] for f in result["findings"]}
        self.assertIn("PLAN_UNKNOWN_DEPENDENCY", rules)
        self.assertIn("PLAN_MISSING_DOR_DOD", rules)


if __name__ == "__main__":
    unittest.main()
