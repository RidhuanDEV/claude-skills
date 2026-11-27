
from __future__ import annotations

import json
from pathlib import Path
import re
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "shadow-monarch" / "scripts"))
import skill_retrieval
import skill_router
from compare_skill_trigger_routing import apply_adjudications


class SkillTriggerRoutingTests(unittest.TestCase):
    def test_source_description_budget(self):
        evidence = skill_router.audit_descriptions()
        self.assertTrue(evidence["all_passed"], evidence)
        self.assertLessEqual(evidence["longest_description_characters"], 250)
        self.assertLessEqual(evidence["total_description_characters"], 9000)

    def test_review_examples_now_have_expected_primary(self):
        cases = (
            ("migrate column email to NOT NULL in 50M row table", "shadow-data"),
            ("optimize LCP on next.js landing page", "modern-web-guidance"),
            ("rotate JWT signing keys", "shadow-auth"),
            ("our redis cache returns other tenant data", "shadow-cache"),
            ("why is this query slow EXPLAIN", "shadow-db"),
            ("bump react 18 to 19 safely", "shadow-compat"),
            ("design pricing page hero section", "shadow-design"),
            ("remove useless comments", "antislop-code"),
            ("OTP mail in spam", "shadow-email"),
            ("save handoff", "handoff"),
            ("ITMS-91053 privacy manifest", "shadow-mobile"),
            ("Prisma 6 relation filter syntax", "context7"),
            ("Pecah kebutuhan menjadi backlog", "shadow-plan"),
            ("regenerate SRS docx", "shadow-doc"),
            ("prod down, users cannot login", "shadow-maintain"),
        )
        for prompt, expected in cases:
            with self.subTest(prompt=prompt):
                route = skill_router.route_prompt(prompt)
                self.assertEqual(route["routing_decision"]["primary_skill"], expected)

    def test_contextual_playbook_order(self):
        cases = (
            ("Stripe webhook signature",
             "shadow-integrate/references/02-hmac-webhooks-replay-and-ordering.md"),
            ("ERD for our customer entities",
             "shadow-db/references/01-relational-design-and-integrity-invariants.md"),
        )
        for prompt, first in cases:
            with self.subTest(prompt=prompt):
                self.assertEqual(skill_router.route_prompt(prompt)["recommended_playbooks"][0], first)

    def test_real_incident_and_incidental_outage_text(self):
        recall = (
            "Production is down and login is returning 500. Start incident triage.",
            "Produksi mati dan login pengguna gagal. Susun langkah pemulihan insiden.",
            "Investigate the production outage before opening a new change window.",
        )
        precision = (
            "No production outage; rotate JWT signing keys in the local environment.",
            "Improve the empty state wording for the production outage banner.",
            "The screen shows 'production down'. Rewrite that heading to tell the operator to try later.",
            "Sustain the feature flag canary plan for our production release.",
            "Production logs say a job timed out, diagnose the error off a local stack trace.",
        )
        for prompt in recall:
            self.assertEqual(skill_router.route_prompt(prompt)["routing_decision"]["primary_skill"],
                             "shadow-maintain", prompt)
        for prompt in precision:
            decision = skill_router.route_prompt(prompt)
            self.assertNotEqual(decision["routing_decision"]["primary_skill"], "shadow-maintain", prompt)

    def test_explicit_execution_denials_precede_candidates(self):
        for prompt in (
            "Review focus order offline. Do not launch a browser or run a load test.",
            "Jangan jalankan k6 dan jangan gunakan /shadow-browser. Tinjau saja hasil yang tersedia.",
            "Write unit tests. Don't open Playwright or run a soak test.",
        ):
            with self.subTest(prompt=prompt):
                decision = skill_router.route_prompt(prompt)
                self.assertNotIn("shadow-browser", decision["companion_skills"])
                self.assertNotIn("shadow-perf", decision["companion_skills"])
                self.assertIn("run_explicitly_denied_load_test", decision["routing_decision"]["prohibited_actions"])
                self.assertIn("launch_explicitly_denied_browser", decision["routing_decision"]["prohibited_actions"])
        for prompt in (
            "Do not edit any code. Run a k6 load test at Pre-UAT.",
            "Do not change the design, but run a load test.",
            "Run a k6 load test at Pre-UAT.",
            "Rancang profil k6 untuk staging Pre-UAT.",
            "Discuss the word 'load' in system utilities.",
        ):
            self.assertNotIn("run_explicitly_denied_load_test",
                             skill_router.route_prompt(prompt)["routing_decision"]["prohibited_actions"], prompt)

    def test_manifest_only_review_remains_read_only(self):
        decision = skill_router.route_prompt(
            "Do not install this external MCP plugin. Review its manifest only."
        )["routing_decision"]
        self.assertEqual(decision["primary_source"], "artifact_audit")
        self.assertEqual(decision["permission_policy"]["max_auto_level"], "L0_READ_ONLY")
        self.assertTrue({"execute_candidate_code", "install_candidate", "activate_candidate"}
                        <= set(decision["prohibited_actions"]))

    def test_rule_exclusions_apply_to_low_rank_and_always_on_candidate(self):
        names = ("shadow-auth", "shadow-db", "shadow-cache", "shadow-domain",
                 "shadow-data", "modern-web-guidance")
        ranked = [skill_retrieval.Candidate(name, 30 - index, 2, 1, 1)
                  for index, name in enumerate(names)]
        rules = [{"skill": name, "include": re.compile("never-routes"),
                  "exclude": re.compile("Dockerfile")} for name in names]
        with patch.object(skill_router, "retrieve", return_value=ranked), \
                patch.object(skill_router, "ROUTING_RULES", rules):
            route = skill_router.route_prompt("Review the Dockerfile for the native <dialog> storefront bundle.")
        self.assertEqual(route["retrieval_candidates"], [])
        self.assertNotIn("modern-web-guidance", route["always_on_ui_skills"])
        self.assertEqual(route["routing_decision"]["primary_source"], "fallback")

    def test_corrupt_or_missing_description_isolated_from_other_skills(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            for skill in ("shadow-cache", "shadow-db", "shadow-release"):
                (root / skill).mkdir()
            (root / "shadow-db" / "SKILL.md").write_bytes(b"\xff")
            (root / "shadow-cache" / "SKILL.md").write_text(
                '---\nname: shadow-cache\ndescription: "Use when tuning TTL and Redis cache."\n---\n',
                encoding="utf-8",
            )
            catalog = skill_retrieval.skill_index(root, ("shadow-cache", "shadow-db", "shadow-release"))
            ranked = skill_retrieval.retrieve("my redis cache expired too soon", catalog)
            self.assertEqual([candidate.skill for candidate in ranked], ["shadow-cache"])
            self.assertFalse(skill_router.audit_descriptions(root)["all_passed"])

    def test_reference_topics_and_bilingual_synonyms_add_candidate_evidence(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            path = root / "shadow-observe" / "SKILL.md"
            path.parent.mkdir()
            path.write_text(
                "---\nname: shadow-observe\ndescription: Use when instrumenting requests.\n---\n"
                "## Reference Guide\n"
                "| [reference](references/01.md) | Metric cardinality and structured event correlation |\n",
                encoding="utf-8",
            )
            indexed = skill_retrieval.skill_index(root, ("shadow-observe",))
            ranked = skill_retrieval.retrieve("kurangi cardinality dan correlation kejadian", indexed)
            self.assertEqual(ranked[0].skill, "shadow-observe")
            self.assertGreaterEqual(ranked[0].rare_terms, 2)

    def test_indonesian_diagnosis_preserves_review_scope(self):
        route = skill_router.route_prompt(
            "Selidiki mengapa status pemesanan berpindah dua kali. Tinjau kode yang ada. "
            "Jangan buka peramban atau jalankan uji beban."
        )
        self.assertEqual(route["routing_decision"]["primary_skill"], "shadow-debug")
        self.assertEqual(route["routing_decision"]["permission_policy"]["max_auto_level"], "L0_READ_ONLY")
        self.assertNotIn("shadow-browser", route["companion_skills"])
        self.assertNotIn("shadow-perf", route["companion_skills"])

    def test_requested_deliverable_beats_completed_background(self):
        cases = (
            ("Kami sudah menyetujui perubahan Kubernetes. Buat runbook rilis aplikasi dengan target rollback.",
             "shadow-release"),
            ("Buat runbook rilis aplikasi dengan target rollback. Kami sudah menyetujui perubahan Kubernetes.",
             "shadow-release"),
            ("This is for tonight's release window, but the only change I need is a readiness probe "
             "in the Helm deployment manifest.", "shadow-ops"),
            ("A release checklist already exists. Configure a reverse proxy and TLS for the sandbox.",
             "shadow-ops"),
            ("Our app uses Stripe webhooks already. Draft acceptance criteria and requirements discovery "
             "for new addresses.", "shadow-discovery"),
        )
        for prompt, primary in cases:
            with self.subTest(prompt=prompt):
                self.assertEqual(skill_router.route_prompt(prompt)["routing_decision"]["primary_skill"], primary)

    def test_runtime_request_and_test_artifact_have_distinct_scope(self):
        for prompt, owner in (
            ("The pytest suite passed. Now open settings in a real browser and verify the toggle survives a reload.",
             "shadow-browser"),
            ("Unit tests passed. Next run a pre-UAT k6 load test in staging.", "shadow-perf"),
            ("A tutorial video already exists. Open the live app in Chrome and verify the invitation.",
             "shadow-browser"),
            ("Do not open a browser. Create a small Playwright test for the existing suite.", "shadow-test"),
            ("Verify browser support for CSS anchor positioning.", "modern-web-guidance"),
        ):
            with self.subTest(prompt=prompt):
                route = skill_router.route_prompt(prompt)
                self.assertEqual(route["routing_decision"]["primary_skill"], owner)
                if owner != "shadow-browser":
                    self.assertNotIn("shadow-browser", route["companion_skills"])
                if owner != "shadow-perf":
                    self.assertNotIn("shadow-perf", route["companion_skills"])
        mixed = skill_router.route_prompt(
            "Write unit tests for the formatter and separately verify the rendered invoice in the browser."
        )
        self.assertTrue({"shadow-test", "shadow-browser"} <= set(mixed["companion_skills"]))
        self.assertNotIn("shadow-perf", mixed["companion_skills"])

    def test_quoted_runtime_and_explicit_denial_stay_outside_scope(self):
        read_only = (
            "Read-only inspection: trace which code paths open Chromium in tests.",
            "From the config only, explain why it is optional.\n~~~yaml\n"
            "run: open Chromium and use staging acceptance load profile\n~~~",
            "From the source only, check this unfinished excerpt.\n~~~\n"
            "Run a pre-UAT k6 load test and open Firefox.",
        )
        for prompt in read_only:
            with self.subTest(prompt=prompt):
                route = skill_router.route_prompt(prompt)
                self.assertEqual(route["routing_decision"]["permission_policy"]["max_auto_level"], "L0_READ_ONLY")
                self.assertFalse({"shadow-perf", "shadow-browser"}.intersection(route["companion_skills"]))
        for prompt in (
            "Jangan aktifkan /shadow-perf untuk tugas ini. Jelaskan matriks persetujuan.",
            "Don't open Firefox or plan a load profile. Check the release checklist.",
            "For staging acceptance, do not plan a load scenario. Provide client sign-off evidence.",
            "Do not enable /shadow-browser. Review static acceptance criteria.",
            "Jangan jalankan Chromium atau profil beban. Susun bukti dari hasil yang tersedia.",
        ):
            with self.subTest(prompt=prompt):
                self.assertFalse({"shadow-perf", "shadow-browser"}.intersection(
                    skill_router.route_prompt(prompt)["companion_skills"]
                ))

    def test_query_plan_tuning_does_not_imply_load_testing(self):
        for prompt in (
            "Compare partial and covering indexes using EXPLAIN ANALYZE.",
            "Bandingkan indeks parsial. Baca EXPLAIN ANALYZE untuk memilih indeks.",
        ):
            with self.subTest(prompt=prompt):
                route = skill_router.route_prompt(prompt)
                self.assertEqual(route["routing_decision"]["primary_skill"], "shadow-db")
                self.assertNotIn("shadow-perf", route["companion_skills"])
        for prompt in (
            "Run a pre-UAT k6 load test in staging for SELECT requests backed by covering indexes.",
            "Plan a load test for pre-UAT and profile the complex query with a partial index.",
            "Jalankan uji beban k6 di staging dengan indeks parsial.",
        ):
            with self.subTest(prompt=prompt):
                self.assertEqual(skill_router.route_prompt(prompt)["routing_decision"]["primary_skill"], "shadow-perf")

    def test_companion_boundaries_require_work_in_that_specialty(self):
        cases = (
            ("Refactor the legacy price service and preserve behavior with characterization tests.",
             "shadow-refactor", {"shadow-quality"}),
            ("Tune BM25 ranking and measure NDCG for the catalog search.",
             "shadow-search", {"shadow-eval"}),
            ("Design WebSocket reconnection and presence for the live lobby.",
             "shadow-realtime", {"shadow-concurrency"}),
            ("Verify the CycloneDX SBOM against the locked dependency tree.",
             "shadow-supplychain", {"shadow-sec", "shadow-release"}),
        )
        for prompt, expected, forbidden in cases:
            with self.subTest(prompt=prompt):
                route = skill_router.route_prompt(prompt)
                self.assertEqual(route["routing_decision"]["primary_skill"], expected)
                self.assertFalse(forbidden.intersection(route["companion_skills"]))

        for prompt, expected in (
            ("/shadow-refactor Refactor this service and run the repo-wide lint and typecheck gate.", "shadow-quality"),
            ("/shadow-search Tune BM25 and evaluate RAG answer faithfulness and citation integrity.", "shadow-eval"),
            ("/shadow-realtime Define WebSocket resumption alongside durable outbox and dead-letter jobs.", "shadow-concurrency"),
            ("/shadow-supplychain Verify the SBOM and run a STRIDE threat model.", "shadow-sec"),
            ("/shadow-supplychain Verify provenance and prepare the production release checklist.", "shadow-release"),
        ):
            with self.subTest(prompt=prompt):
                self.assertIn(expected, skill_router.route_prompt(prompt)["companion_skills"])

    def test_operational_auth_outage_distinguishes_restoration_and_auth_changes(self):
        cases = (
            "Mitigate the production login outage. Coordinate recovery and operator updates.",
            "Stabilize the production SSO incident and coordinate rollback.",
            "Tangani insiden login produksi dan pulihkan akses pengguna.",
            "Sesudah pergantian artefak pagi ini, pelanggan terhenti di gerbang masuk portal publik. "
            "Susun koordinasi pemulihan dan periksa kompatibilitas artefak stabil sebelumnya.",
            "Live customers are locked out after the latest release. Assess a rollback to restore access.",
        )
        for prompt in cases:
            with self.subTest(prompt=prompt):
                result = skill_router.route_prompt(prompt)
                self.assertEqual(result["routing_decision"]["primary_skill"], "shadow-maintain")
                self.assertNotIn("shadow-auth", result["companion_skills"])
        for prompt in (
            "Rotate JWT signing keys in a controlled migration.",
            "After the previous incident, implement changes to the login session policy.",
            "Design the SSO configuration in our production environment.",
        ):
            with self.subTest(prompt=prompt):
                self.assertEqual(skill_router.route_prompt(prompt)["routing_decision"]["primary_skill"],
                                 "shadow-auth")
        for prompt in (
            "Mitigate the production login outage. Rotate JWKS keys as part of authorized recovery.",
            "/shadow-auth Investigate the production login outage in the authentication provider.",
        ):
            with self.subTest(prompt=prompt):
                self.assertIn("shadow-auth", skill_router.route_prompt(prompt)["companion_skills"])

    def test_cli_homographs_do_not_load_ui_filters(self):
        for prompt in (
            "Diagnose why the command-line archive extractor emits a malformed table.",
            "The compiler sometimes duplicates a header on stderr. Trace the race condition.",
            "Cari penyebab input CSV CLI sesekali tidak terbaca oleh parser.",
            "The terminal export drops the table header after a batch job finishes.",
            "Inspect the SQL query and table schema against PostgreSQL indexes.",
        ):
            with self.subTest(prompt=prompt):
                self.assertNotIn("antislop-human", skill_router.route_prompt(prompt)["always_on_ui_skills"])
        for prompt in (
            "Design a frontend drawer that displays stdout and has a clear focus ring.",
            "Perbaiki tombol dan layout dashboard yang menampilkan output CLI.",
            "Check the UI component for keyboard navigation and the selected state.",
        ):
            with self.subTest(prompt=prompt):
                self.assertIn("antislop-human", skill_router.route_prompt(prompt)["always_on_ui_skills"])

    def test_adjudication_preserves_near_miss_population_and_original_cases(self):
        catalog = {"shadow-ops", "shadow-perf"}
        positive = {"id": "positive", "language": "en", "prompt": "Existing positive",
                    "expected_primary": "shadow-perf"}
        negative = {"id": "negative", "language": "en", "prompt": "Frozen prompt",
                    "expected_primary": "shadow-ops", "exclude": ["shadow-perf"]}
        case = dict(negative, id="negative-adjudicated", prompt="New independent negative")
        rows = [positive, negative]
        with tempfile.TemporaryDirectory() as folder:
            file = Path(folder) / "replacements.json"
            good = {"original_id": "negative", "case": case, "reason": "Activation contract."}
            file.write_text(json.dumps([good]), encoding="utf-8")
            updated, evidence = apply_adjudications(rows, file, catalog)
            self.assertEqual(updated, [positive, case])
            self.assertEqual(rows, [positive, negative])
            self.assertEqual(evidence[0]["replacement_id"], case["id"])

            for invalid in (
                dict(good, original_id="positive"),
                dict(good, case=dict(case, exclude=[])),
                dict(good, case=dict(case, language="id")),
                dict(good, case=dict(case, prompt=negative["prompt"])),
                dict(good, case=dict(case, expected_primary="shadow-perf")),
            ):
                with self.subTest(error=invalid):
                    file.write_text(json.dumps([invalid]), encoding="utf-8")
                    with self.assertRaises(ValueError):
                        apply_adjudications(rows, file, catalog)

    def test_retrieval_keeps_explicit_owner_and_distinguishes_default(self):
        explicit = skill_router.route_prompt("/shadow-compat Audit current Redis TTL")
        self.assertEqual(explicit["routing_decision"]["primary_skill"], "shadow-compat")
        self.assertEqual(explicit["routing_decision"]["primary_source"], "explicit")
        self.assertEqual(explicit["retrieval_candidates"], [])
        generic = skill_router.route_prompt("Please give me a few ideas for a greeting to a friend.")
        self.assertEqual(generic["routing_decision"]["primary_source"], "fallback")
        for prompt in (
            "Simpan konteks sebelum pindah agen.",
            "Rapikan komentar mubazir pada helper ini.",
            "The service shows a missing CSS custom property. Check the container query fallback.",
        ):
            self.assertNotEqual(skill_router.route_prompt(prompt)["routing_decision"]["primary_source"], "fallback", prompt)


if __name__ == "__main__":
    unittest.main()
