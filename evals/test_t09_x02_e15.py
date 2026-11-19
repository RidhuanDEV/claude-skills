from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "shadow-monarch" / "scripts"))
sys.path.insert(0, str(REPO_ROOT / "evals"))

import execution_approval_gate as gate
import run_evals
import skill_router


class OrchestrationAndEvalContractTests(unittest.TestCase):
    def test_t09_readme_only_api_docs_requires_decision_before_write(self) -> None:
        routed = skill_router.route_prompt(
            "Tolong buatkan dokumentasi API untuk service ini.",
            repo_context={"readme_summary_only": True, "has_active_generator": False},
        )
        policy = routed["routing_decision"]["user_input_policy"]
        self.assertTrue(policy["requires_user_decision"])
        self.assertEqual(policy["question_topic"], "api_docs_format")
        self.assertTrue(policy["stop_before_write"])

    def test_t09_explicit_format_and_active_generator_skip_question(self) -> None:
        explicit = skill_router.route_prompt(
            "Create OpenAPI 3.1 API documentation for this service.",
            repo_context={"readme_summary_only": True, "has_active_generator": False},
        )
        self.assertFalse(explicit["routing_decision"]["user_input_policy"]["requires_user_decision"])

        active_gen = skill_router.route_prompt(
            "Update API docs for the new order endpoint.",
            repo_context={"readme_summary_only": False, "has_active_generator": True},
        )
        self.assertFalse(active_gen["routing_decision"]["user_input_policy"]["requires_user_decision"])

    def test_t09_webhook_review_stays_l0_and_ignores_negated_or_quoted_tools(self) -> None:
        routed = skill_router.route_prompt(
            'Review this webhook handler, jangan load test, log: "k6 run failed and playwright timeout"'
        )
        decision = routed["routing_decision"]
        self.assertEqual(decision["permission_policy"]["intent_mode"], "code_review")
        self.assertEqual(decision["permission_policy"]["max_auto_level"], "L0_READ_ONLY")
        self.assertNotIn("shadow-perf", routed["companion_skills"])
        self.assertNotIn("shadow-browser", routed["companion_skills"])

    def test_x02_e15_multi_turn_approval_rejects_stale_repo_head_and_host_drift(self) -> None:
        req = {
            "task_id": "TASK-E15",
            "project_path": "/repo/app",
            "user_intent": "feature_implementation",
            "action_type": "broad_e2e",
            "command": "playwright test tests/checkout.spec.ts",
            "environment": "local",
            "host": "localhost:3000",
            "target_paths": ["tests/checkout.spec.ts"],
            "repo_head_sha": "sha-new-2222",
        }
        stale_approval = {
            "task_id": "TASK-E15",
            "project_path": "/repo/app",
            "execution_status": "APPROVED_PENDING",
            "permission_level": "L2_SCOPE_EXPANSION",
            "allowed_environments": ["local"],
            "host": "localhost:3000",
            "exact_targets": ["tests/checkout.spec.ts"],
            "repo_head_sha": "sha-old-1111",
        }
        blocked = gate.evaluate_execution_request(req, stale_approval)
        self.assertEqual(blocked["decision"], "BLOCKED")
        self.assertTrue(any("BLOCKED_STALE_APPROVAL" in r for r in blocked["reasons"]))

        fresh_approval = dict(stale_approval, repo_head_sha="sha-new-2222")
        allowed = gate.evaluate_execution_request(req, fresh_approval)
        self.assertEqual(allowed["decision"], "ALLOW")

        wrong_host = dict(fresh_approval, host="staging.internal")
        host_blocked = gate.evaluate_execution_request(req, wrong_host)
        self.assertEqual(host_blocked["decision"], "BLOCKED")

        for field, code in (("repo_head_sha", "BLOCKED_STALE_APPROVAL"),
                            ("host", "BLOCKED_APPROVAL_SCOPE_MISMATCH")):
            with self.subTest(missing_bound_field=field):
                incomplete = dict(req)
                del incomplete[field]
                blocked = gate.evaluate_execution_request(incomplete, fresh_approval)
                self.assertEqual(blocked["decision"], "BLOCKED")
                self.assertEqual(blocked["code"], code)

    def test_x04_progressive_disclosure_keeps_typo_near_zero_vs_multi_domain(self) -> None:
        typo = skill_router.route_prompt("Fix typo in README.md")
        multi = skill_router.route_prompt(
            "Buat REST API login RBAC multi-tenant dengan OpenAPI 3.1 dan migrasi DB Expand-Contract."
        )
        self.assertTrue(typo["disclosure_metrics"]["trivial_fast_path"])
        self.assertEqual(typo["disclosure_metrics"]["loaded_skill_count"], 0)
        self.assertEqual(typo["disclosure_metrics"]["loaded_ref_count"], 0)
        self.assertEqual(typo["disclosure_metrics"]["estimated_loaded_bytes"], 0)
        self.assertGreater(multi["disclosure_metrics"]["estimated_loaded_bytes"], 0)
        self.assertLessEqual(multi["disclosure_metrics"]["loaded_ref_count"], 4)

    def test_x01_x06_baseline_manifest_and_empty_evidence_cannot_pass(self) -> None:
        manifest_path = REPO_ROOT / "evals" / "fixtures" / "baseline-comparison-manifest.json"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        self.assertEqual(manifest["baseline_revision"], "bac8745")
        self.assertFalse(manifest["holdout_governance"]["external_holdout_present"])
        self.assertTrue(manifest["oracle_contract"]["rejects_empty_evidence_as_verified"])

        evals_data = run_evals.load_evals()
        eval18 = next(item for item in evals_data["evals"] if item["id"] == 18)
        empty_score = run_evals.score_response(eval18, "")
        self.assertFalse(empty_score["all_passed"])
        self.assertEqual(empty_score["passed_assertions"], 0)


if __name__ == "__main__":
    unittest.main()
