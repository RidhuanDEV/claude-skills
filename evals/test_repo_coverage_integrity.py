from __future__ import annotations

import re
import sys
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "shadow-monarch" / "scripts"))

import skill_router


class RepoCoverageAndIntegrityTests(unittest.TestCase):
    def test_every_skill_directory_is_routed_documented_and_portable(self) -> None:
        skill_dirs = sorted(
            p.name for p in REPO_ROOT.iterdir() if p.is_dir() and (p / "SKILL.md").is_file()
        )
        self.assertGreaterEqual(len(skill_dirs), 56)

        routed_by_rules = {rule["skill"] for rule in skill_router.ROUTING_RULES}
        routed_always_on_ui = {
            "antislop",
            "antislop-ui",
            "antislop-layoutmobile",
            "antislop-human",
            "antislop-copywriting",
            "antislop-code",
            "modern-web-guidance",
        }
        covered = routed_by_rules | routed_always_on_ui | {"shadow-monarch"}
        unrouted = sorted(set(skill_dirs) - covered)
        self.assertEqual(unrouted, [], f"Orphan skills missing from skill_router.py: {unrouted}")

        monarch_doc = (REPO_ROOT / "shadow-monarch" / "SKILL.md").read_text(encoding="utf-8")
        missing_from_monarch = [s for s in skill_dirs if s not in monarch_doc]
        self.assertEqual(missing_from_monarch, [], f"Skills missing from shadow-monarch/SKILL.md: {missing_from_monarch}")

        # Verify zero broken relative links, zero hardcoded machine paths, and <= 500 lines per root SKILL.md
        for s in skill_dirs:
            skill_md = REPO_ROOT / s / "SKILL.md"
            text = skill_md.read_text(encoding="utf-8")
            self.assertLessEqual(len(text.splitlines()), 500, f"{s}/SKILL.md exceeds 500 lines")
            self.assertNotRegex(
                text,
                r"(?:C:\\Users\\[A-Za-z0-9._-]+|C:/Users/[A-Za-z0-9._-]+|d:\\Ridhuan|D:\\Ridhuan|/Users/[A-Za-z0-9._-]+)",
                f"Hardcoded machine path in {s}/SKILL.md",
            )
            for match in re.finditer(r"\]\(([^)]+)\)", text):
                target = match.group(1).split("#")[0].strip()
                if not target or "://" in target or target.startswith(("mailto:", "/")):
                    continue
                exists = (skill_md.parent / target).exists() or (REPO_ROOT / target).exists()
                self.assertTrue(exists, f"Broken relative link `{target}` in {s}/SKILL.md")

    def test_router_references_all_exist_on_disk(self) -> None:
        refs_dir = REPO_ROOT / "shadow-monarch" / "reference"
        existing = {p.name for p in refs_dir.glob("*.md")}
        for rule in skill_router.ROUTING_RULES:
            for ref in rule.get("references", []):
                self.assertIn(ref, existing, f"Router references missing file `{ref}`")
        for _, lang_ref in skill_router.LANGUAGE_REF_RULES:
            self.assertIn(lang_ref, existing, f"Language router references missing file `{lang_ref}`")

    def test_ui_component_and_intent_mode_regressions(self) -> None:
        ui_route = skill_router.route_prompt("Tolong buatkan component card dan button primary sesuai theme aplikasi.")
        self.assertIn("antislop-human", ui_route["always_on_ui_skills"])
        self.assertIn("modern-web-guidance", ui_route["always_on_ui_skills"])
        self.assertIn("FRONTEND.md", ui_route["reference_modules"])

        multi = skill_router.route_prompt(
            "Buat REST API login RBAC multi-tenant dengan database migration, Redis cache, webhook Midtrans, dan OpenAPI 3.1"
        )
        self.assertEqual(multi["routing_decision"]["primary_skill"], "shadow-api")
        self.assertEqual(multi["routing_decision"]["permission_policy"]["intent_mode"], "feature_implementation")

        typo_doc = skill_router.route_prompt("Fix small typo in docs/guide.md")
        self.assertTrue(typo_doc["disclosure_metrics"]["trivial_fast_path"])
        self.assertEqual(typo_doc["disclosure_metrics"]["loaded_skill_count"], 0)


if __name__ == "__main__":
    unittest.main()
