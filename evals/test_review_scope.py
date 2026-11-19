"""Exercise the scope handoff without executing a child action."""
from pathlib import Path
import runpy
import unittest

ROOT = Path(__file__).resolve().parents[1] / "shadow-monarch" / "scripts"
route = runpy.run_path(str(ROOT / "skill_router.py"))["route_prompt"]
authorize = runpy.run_path(str(ROOT / "execution_approval_gate.py"))["check_subagent_authorization"]


class ReviewScopeTests(unittest.TestCase):
    def test_read_only_scope_survives_handoff(self):
        for text in ("Only review this API endpoint; do not run a load test",
                     "Only review the endpoint before staging",
                     "Hanya tinjau endpoint API ini, jangan jalankan load test",
                     "Hanya inspect server.ts secara read-only dan usulkan rencana load test k6 lokal. JANGAN jalankan k6.",
                     "Ada dua tugas desain read-only (jangan ubah file apa pun). Susun interview-script untuk task-usability."):
            with self.subTest(text=text):
                out = route(text)
                policy = out["routing_decision"]
                self.assertEqual(policy["permission_policy"]["intent_mode"], "code_review")
                self.assertNotIn("shadow-perf", out["companion_skills"])
                scope = dict(policy["subagent_policy"], allowed_environments=["local"])
                self.assertEqual(authorize(scope, {"environment": "local", "action_type": "load_test"})["decision"], "BLOCKED")
                self.assertEqual(authorize(scope, {"environment": "local", "action_type": "inspect"})["decision"], "ALLOW")

    def test_explicit_denial_excludes_execution_skill_after_review(self):
        result = route("Saya TIDAK menyetujui load test k6 sekarang. Simpan session handoff.")
        self.assertEqual(result["routing_decision"]["primary_skill"], "handoff")
        self.assertNotIn("shadow-perf", result["companion_skills"])
        self.assertIn("load_test", result["routing_decision"]["subagent_policy"]["denied_actions"])

    def test_neighboring_tasks_keep_their_phase(self):
        for text in ("Implement this API endpoint", "Hanya buat dokumentasi API",
                     "Plan a Pre-UAT k6 load test", "Review the quarterly budget",
                     "Optimize the endpoint query"):
            with self.subTest(text=text):
                self.assertNotEqual(route(text)["routing_decision"]["permission_policy"]["intent_mode"], "code_review")


if __name__ == "__main__":
    unittest.main()
