"""Stage-one shortlist contract: safety blocks hold, model choices are validated, coverage stays high."""

from __future__ import annotations

import json
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "shadow-monarch" / "scripts"))

import skill_router  # noqa: E402
from skill_lexicon_id import english_term  # noqa: E402

DEVELOPMENT_FIXTURES = (
    "wave2-trigger-holdout-a.json",
    "wave2-trigger-holdout-b.json",
    "wave2-trigger-development.json",
)


def decide(prompt: str, selected_owner: str | None = None) -> dict:
    return skill_router.route_prompt(prompt, selected_owner=selected_owner)["routing_decision"]


class OwnerShortlistTests(unittest.TestCase):
    def test_unknown_choice_is_rejected_and_deterministic_owner_kept(self):
        prompt = "rotate JWT signing keys"
        baseline = decide(prompt)
        rejected = decide(prompt, selected_owner="shadow-nonexistent")
        self.assertEqual(rejected["owner_selection"]["status"], "rejected_unknown")
        self.assertEqual(rejected["primary_skill"], baseline["primary_skill"])

    def test_choice_outside_shortlist_is_allowed_when_not_excluded(self):
        decision = decide("rotate JWT signing keys", selected_owner="shadow-video")
        self.assertNotIn("shadow-video", decision["owner_candidates"])
        self.assertEqual(decision["owner_selection"]["status"], "accepted_outside_shortlist")
        self.assertEqual((decision["primary_skill"], decision["primary_source"]), ("shadow-video", "model_selected"))

    def test_selected_owner_drops_topical_guesses_but_keeps_requested_and_risk_skills(self):
        prompt = "Split the approved PRD into epics, user stories, and a two-week sprint backlog."
        decision = decide(prompt, selected_owner="shadow-plan")
        self.assertEqual(decision["primary_skill"], "shadow-plan")
        self.assertNotIn("shadow-discovery", decision["supporting_skills"])

    def test_non_authoring_visual_owner_does_not_load_ui_bundle(self):
        route = skill_router.route_prompt(
            "Jalankan Playwright di viewport 375, 768, dan 1440 lalu ambil screenshot tiap halaman.",
            selected_owner="shadow-browser",
        )
        self.assertEqual(route["routing_decision"]["primary_skill"], "shadow-browser")
        self.assertNotIn("antislop-layoutmobile", route["always_on_ui_skills"])

    def test_accepted_choice_becomes_primary_with_model_source(self):
        prompt = "Kami masuk gerbang performa Pre-UAT. Susun workload k6 berbatas waktu dan syarat lulus p95."
        decision = decide(prompt, selected_owner="shadow-perf")
        self.assertIn("shadow-perf", decision["owner_candidates"])
        self.assertEqual(decision["owner_selection"]["status"], "accepted")
        self.assertEqual((decision["primary_skill"], decision["primary_source"]), ("shadow-perf", "model_selected"))

    def test_explicit_execution_denial_keeps_skill_off_the_shortlist(self):
        for prompt, denied in (
            ("jangan pakai k6, cukup review kode saja untuk endpoint search", "shadow-perf"),
            ("Review the checkout code only; do not open a browser or run Playwright.", "shadow-browser"),
        ):
            with self.subTest(prompt=prompt):
                decision = decide(prompt, selected_owner=denied)
                self.assertNotIn(denied, decision["owner_candidates"])
                self.assertEqual(decision["owner_selection"]["status"], "rejected_excluded")
                self.assertNotEqual(decision["primary_skill"], denied)

    def test_explicit_skill_mention_fixes_the_shortlist(self):
        decision = decide("Use /shadow-api to design the pagination contract for orders.", selected_owner="shadow-db")
        self.assertEqual(decision["owner_candidates"], ["shadow-api"])
        self.assertEqual(decision["primary_skill"], "shadow-api")
        self.assertEqual(decision["owner_selection"]["status"], "rejected_fixed_owner")

    def test_trivial_question_has_no_candidates_and_accepts_no_owner(self):
        decision = decide("what is a closure in javascript")
        self.assertEqual(decision["owner_candidates"], [])
        none = decide("what is a closure in javascript", selected_owner=skill_router.NO_OWNER)
        self.assertEqual(none["primary_source"], "fallback")

    def test_versioned_api_questions_are_not_trivial(self):
        for prompt in (
            "What is the exact shape of Prisma 6.2 interactive `$transaction` options (maxWait, timeout)?",
            "What is the signature of cookies() in Next.js v15 route handlers?",
            "What is the default of axios@1.7 timeout?",
        ):
            with self.subTest(prompt=prompt):
                self.assertTrue(decide(prompt, selected_owner="context7")["owner_selection"]["status"].startswith("accepted"))
        for prompt in ("what is a closure in javascript", "What is the difference between let and const"):
            with self.subTest(prompt=prompt):
                self.assertEqual(decide(prompt, selected_owner="context7")["owner_selection"]["status"], "rejected_fixed_owner")

    def test_no_owner_choice_clears_specialists(self):
        decision = decide("bikin ERD dari database postgres", selected_owner=skill_router.NO_OWNER)
        self.assertEqual(decision["owner_selection"]["status"], "accepted_no_owner")
        self.assertEqual(decision["primary_source"], "fallback")

    def test_orchestrator_is_always_an_option_for_non_trivial_work(self):
        decision = decide("Koordinasikan modul e-katalog dari requirement sampai deploy dengan arsitektur, keamanan dan UAT.")
        self.assertIn(skill_router.ORCHESTRATOR, decision["owner_candidates"])

    def test_development_shortlist_recall_stays_high(self):
        positives = covered = 0
        for name in DEVELOPMENT_FIXTURES:
            for case in json.loads((ROOT / "evals" / "fixtures" / name).read_text(encoding="utf-8")):
                if case.get("exclude") or case.get("expected_primary") is None:
                    continue
                positives += 1
                covered += case["expected_primary"] in decide(case["prompt"])["owner_candidates"]
        self.assertGreaterEqual(covered / positives, 0.98, f"{covered}/{positives}")


class CompanionAfterSelectionTests(unittest.TestCase):
    def test_bundle_supporting_skill_needs_prompt_evidence_after_selection(self):
        decision = decide("Design the C4 container view for our municipal billing platform.", selected_owner="shadow-architect")
        self.assertEqual(decision["primary_skill"], "shadow-architect")
        self.assertNotIn("shadow-domain", decision["supporting_skills"])
        self.assertIn("shadow-architect", decision["owner_candidates"])

    def test_antislop_sub_skill_does_not_pull_in_its_siblings(self):
        route = skill_router.route_prompt(
            "Polish the card spacing and typographic scale on the pricing page.", selected_owner="antislop-ui",
        )
        self.assertEqual(route["routing_decision"]["primary_skill"], "antislop-ui")
        self.assertIn("antislop", route["always_on_ui_skills"])
        self.assertFalse({"antislop-human", "antislop-layoutmobile"} & set(route["always_on_ui_skills"]))

    def test_prompt_triggered_risk_reviews_survive_a_model_selection(self):
        risk_rules = [rule for rule in skill_router.ROUTING_RULES if rule.get("layer") == "risk"]
        checked = 0
        for name in DEVELOPMENT_FIXTURES:
            for case in json.loads((ROOT / "evals" / "fixtures" / name).read_text(encoding="utf-8")):
                deterministic = decide(case["prompt"])
                triggered = {
                    rule["skill"] for rule in risk_rules
                    if rule["include"].search(case["prompt"]) and rule["skill"] in deterministic["risk_review_skills"]
                }
                if not triggered:
                    continue
                owner = next((skill for skill in deterministic["owner_candidates"]
                              if skill not in triggered and skill != deterministic["primary_skill"]), None)
                if owner is None:
                    continue
                selected = decide(case["prompt"], selected_owner=owner)
                with self.subTest(case=case["id"], owner=owner):
                    self.assertTrue(triggered <= set(selected["risk_review_skills"]))
                checked += 1
        self.assertGreater(checked, 0, "No development case triggers a prompt-level risk review.")


class UiBundleHomographTests(unittest.TestCase):
    def test_frontend_tooling_runs_do_not_load_ui_filters(self):
        for prompt in (
            "Run eslint and tsc --noEmit on the frontend package and tell me whether the CI gate passes",
            "The frontend build fails inside Docker with exit code 137",
            "Bump frontend dependencies and refresh the lockfile",
            "Frontend CI pipeline red after merge, check the lint step",
            "Deploy the frontend container image to staging",
        ):
            with self.subTest(prompt=prompt):
                self.assertEqual(skill_router.route_prompt(prompt)["always_on_ui_skills"], [])

    def test_real_frontend_work_still_loads_ui_filters(self):
        for prompt in (
            "Fix the frontend button hover state on the pricing card",
            "Build the frontend dashboard page with a React component layout",
            "Rapikan tampilan halaman checkout di frontend, tombolnya terlalu mepet",
            "Make the navbar responsive on mobile",
            "The frontend modal closes when I press Tab, fix the focus trap",
        ):
            with self.subTest(prompt=prompt):
                self.assertTrue(skill_router.route_prompt(prompt)["always_on_ui_skills"])


class CopywritingHomographTests(unittest.TestCase):
    def test_deliverability_work_does_not_load_the_copy_filter(self):
        for prompt in (
            "Headline newsletter kita masuk folder spam Gmail, cek DKIM sama DMARC",
            "Our marketing headline emails bounce at Outlook, check SPF alignment",
            "Email OTP masuk spam, reputasi pengirim turun, padahal headline sudah diganti",
        ):
            with self.subTest(prompt=prompt):
                self.assertNotIn("antislop-copywriting", skill_router.route_prompt(prompt)["always_on_ui_skills"])

    def test_ui_copy_still_loads_the_copy_filter(self):
        for prompt in (
            "Rewrite the hero headline and CTA on the pricing page",
            "Perbaiki microcopy tombol daftar dan pesan error form login",
            "Tolong ganti headline landing page biar gak generik",
        ):
            with self.subTest(prompt=prompt):
                self.assertIn("antislop-copywriting", skill_router.route_prompt(prompt)["always_on_ui_skills"])


class PostAwardAndHomographTests(unittest.TestCase):
    def test_post_award_requirement_work_may_select_discovery(self):
        for prompt in (
            "We won the tender; set up the requirement workshops with the client.",
            "Kami menang tender e-Perizinan. Susun daftar pertanyaan elisitasi kebutuhan.",
            "Setelah kontrak ditandatangani, buat SRS dari KAK yang ada.",
            "We just won the university SIAKAD tender. Plan the requirement workshops and map stakeholders.",
            "Tender SIAKAD sudah dimenangkan, susun SRS dan pemetaan pemangku kepentingan.",
        ):
            with self.subTest(prompt=prompt):
                self.assertEqual(decide(prompt, selected_owner="shadow-discovery")["primary_skill"], "shadow-discovery")

    def test_pre_award_tender_work_still_excludes_discovery(self):
        for prompt in (
            "Analisis KAK tender ini dan buat RAB penawaran",
            "Kami ikut tender SIMRS, susun estimasi biaya dan HPS",
            "Kalau kita menang tender ini, apa saja kebutuhan yang perlu di-PRD-kan? Hitung RAB dulu",
            "Help us win the tender: score bid/no-bid and draft the PRD outline for the proposal",
        ):
            with self.subTest(prompt=prompt):
                status = decide(prompt, selected_owner="shadow-discovery")["owner_selection"]["status"]
                self.assertEqual(status, "rejected_excluded")

    def test_http_header_names_are_not_ui_components(self):
        self.assertEqual(skill_router.route_prompt(
            "Set header Cache-Control dan Surrogate-Key untuk aset statis di CDN")["always_on_ui_skills"], [])
        self.assertTrue(skill_router.route_prompt(
            "Make the sticky header component collapse on scroll")["always_on_ui_skills"])

    def test_search_indexing_pages_are_not_ui_work(self):
        for prompt in (
            "Sitemap.xml dan canonical URL portal berita salah sehingga ribuan halaman tidak terindeks Google.",
            "Halaman kategori belum terindeks sejak robots.txt diubah",
        ):
            with self.subTest(prompt=prompt):
                self.assertEqual(skill_router.route_prompt(prompt)["always_on_ui_skills"], [])
        self.assertTrue(skill_router.route_prompt(
            "Perbaiki tampilan halaman profil, card dan tombolnya tidak rapi")["always_on_ui_skills"])

    def test_delivery_owners_do_not_load_ui_filters_for_framework_names(self):
        for prompt, owner in (
            ("Siapkan pipeline CI untuk build image Docker aplikasi Next.js 15 dan push ke registry Harbor", "shadow-ops"),
            ("Cut the v3.2.0 release of the React dashboard with a canary rollout", "shadow-release"),
            ("Resolve the merge conflict in the Next.js layout branch before rebasing", "shadow-git"),
        ):
            with self.subTest(prompt=prompt):
                self.assertEqual(skill_router.route_prompt(prompt, selected_owner=owner)["always_on_ui_skills"], [])

    def test_weak_ui_words_follow_the_selected_owner(self):
        for prompt, owner in (
            ("Our Go settlement worker panics with nil pointer dereference only when the freight rate table is empty.", "shadow-debug"),
            ("Add a partial index on the invoices table for unpaid rows", "shadow-db"),
        ):
            with self.subTest(prompt=prompt):
                self.assertEqual(skill_router.route_prompt(prompt, selected_owner=owner)["always_on_ui_skills"], [])
        self.assertTrue(skill_router.route_prompt(
            "Rapikan tabel transaksi di dashboard supaya kolomnya sejajar", selected_owner="antislop-ui",
        )["always_on_ui_skills"])

    def test_typo_and_audit_paths_accept_selection_without_error(self):
        self.assertEqual(decide("fix typo in README", selected_owner="shadow-doc")["owner_selection"]["status"],
                         "rejected_fixed_owner")
        self.assertTrue(decide("Audit this third-party MCP server before install",
                               selected_owner="shadow-sec")["owner_selection"]["status"].startswith("accepted"))

    def test_document_styling_does_not_load_ui_filters(self):
        route = skill_router.route_prompt(
            "The headings and table spacing in our generated SRS .docx look inconsistent; fix the style definitions",
            selected_owner="shadow-doc",
        )
        self.assertEqual(route["always_on_ui_skills"], [])


class SelectOwnerCliTests(unittest.TestCase):
    def test_cli_validates_the_stage_two_choice(self):
        import subprocess
        script = ROOT / "shadow-monarch" / "scripts" / "skill_router.py"
        result = subprocess.run(
            [sys.executable, "-B", str(script), "--route", "rotate JWT signing keys", "--select-owner", "shadow-auth"],
            capture_output=True, text=True, encoding="utf-8", timeout=60, check=True,
        )
        decision = json.loads(result.stdout)["routing_decision"]
        self.assertEqual(decision["owner_selection"], {"requested": "shadow-auth", "status": "accepted"})
        self.assertEqual(decision["primary_source"], "model_selected")


class IndonesianLexiconTests(unittest.TestCase):
    def test_precision_probes_stay_unmapped(self):
        for word in ("menteri", "pending", "merge", "session", "terraform", "dimension", "persistent",
                     "penting", "selesai", "terus", "menu", "mesin", "masuk", "sedang", "server", "deploy"):
            with self.subTest(word=word):
                self.assertIsNone(english_term(word))

    def test_recall_probes_resolve_inflected_forms(self):
        for word, expected in (("pembayaran", "payment"), ("dipulihkan", "restore"), ("memulihkan", "restore"),
                               ("pengujian", "test"), ("menggabungkan", "merge"), ("sinkronisasinya", "sync"),
                               ("pemisahan", "split"), ("kodenya", "code")):
            with self.subTest(word=word):
                self.assertEqual(english_term(word), expected)


if __name__ == "__main__":
    unittest.main()
