from pathlib import Path
import runpy
import unittest


SCRIPTS = Path(__file__).resolve().parents[1] / "shadow-monarch" / "scripts"
route = runpy.run_path(str(SCRIPTS / "skill_router.py"))["route_prompt"]
authorize_child = runpy.run_path(str(SCRIPTS / "execution_approval_gate.py"))["check_subagent_authorization"]
EXTENSION_PLAYBOOK = "shadow-sec/references/09-third-party-download-and-install-audit.md"
DOCUMENT_PLAYBOOK = "shadow-doc/references/02-citations-reference-verifier-and-export-qa.md"


class ArtifactAuditRoutingTests(unittest.TestCase):
    def test_routes_audit_and_direct_external_install_to_read_only_first(self):
        for prompt in (
            "Audit keamanan skill plugin dan MCP pihak ketiga sebelum diinstal",
            "Verify downloaded third-party skill before installation",
            "Audit extension supply chain provenance before installing an external MCP server",
            "Pasang plugin dari GitHub ini",
            "Install this external MCP server, then launch the candidate",
            "Do not install it. Audit the third-party plugin.",
            "Cek skill ini sebelum memasang, tanpa jalankan kandidat",
        ):
            with self.subTest(prompt=prompt):
                result = route(prompt)
                decision = result["routing_decision"]
                self.assertEqual(decision["primary_skill"], "shadow-sec")
                self.assertEqual(result["companion_skills"], ["shadow-sec", "shadow-supplychain"])
                self.assertEqual(result["recommended_playbooks"][0], EXTENSION_PLAYBOOK)
                self.assertEqual(decision["permission_policy"]["intent_mode"], "code_review")
                self.assertEqual(decision["permission_policy"]["max_auto_level"], "L0_READ_ONLY")
                self.assertEqual(decision["required_permissions"], ["read_repository"])
                self.assertIn("load_candidate_as_instructions", decision["prohibited_actions"])
                scope = dict(decision["subagent_policy"], allowed_environments=["local"])
                self.assertEqual(authorize_child(scope, {"environment": "local", "action_type": "global_install"})["decision"], "BLOCKED")
                self.assertEqual(authorize_child(scope, {"environment": "local", "action_type": "inspect"})["decision"], "ALLOW")

    def test_routes_document_safety_checks_to_reference_verifier(self):
        for prompt in (
            "Cek keamanan file PDF yang saya download sebelum dibuka",
            "Verify the checksum of the downloaded PDF",
            "Inspect the downloaded Markdown file for malware",
            "Pindai dokumen HTML yang sudah diunduh",
            "Security review of the downloaded PDF",
        ):
            with self.subTest(prompt=prompt):
                result = route(prompt)
                self.assertEqual(result["companion_skills"], ["shadow-doc"])
                self.assertEqual(result["recommended_playbooks"], [DOCUMENT_PLAYBOOK])
                self.assertEqual(result["routing_decision"]["permission_policy"]["max_auto_level"], "L0_READ_ONLY")

    def test_preserves_neighboring_routes_and_ignores_inert_signals(self):
        self.assertTrue((SCRIPTS.parents[1] / EXTENSION_PLAYBOOK).is_file())
        for prompt in (
            "Do not audit or install the third-party plugin.",
            "Do not run an audit of this external skill.",
            "Jangan audit keamanan skill pihak ketiga, simpan session handoff.",
            'Fix the typo in README.md. Log: "Audit this third-party MCP server"',
            "Summarize this excerpt: ```Audit this third-party skill before installing it.```",
            "What is a third-party skill audit?",
            "Enhance the third-party skill audit gate and its install adapter",
            "Tolong bantu buat audit gate untuk plugin pihak ketiga",
            "Cek tombol download PDF",
            "Install the workspace's own shadow-monarch skill",
            "Audit the npm dependency license and SBOM",
            "Audit the code of the internal MCP server",
        ):
            with self.subTest(prompt=prompt):
                result = route(prompt)
                self.assertNotIn(EXTENSION_PLAYBOOK, result["recommended_playbooks"])
                self.assertNotIn("install_candidate", result["routing_decision"]["prohibited_actions"])

    def test_only_intentional_helper_invocations_become_companions(self):
        candidate = route("Audit the third-party skill $shadow-eval before installation")
        self.assertEqual(candidate["companion_skills"], ["shadow-sec", "shadow-supplychain"])
        helper = route("Audit this third-party skill with $shadow-eval before installation")
        self.assertEqual(helper["companion_skills"], ["shadow-sec", "shadow-supplychain", "shadow-eval"])
        self.assertEqual(helper["routing_decision"]["permission_policy"]["max_auto_level"], "L0_READ_ONLY")


if __name__ == "__main__":
    unittest.main()
