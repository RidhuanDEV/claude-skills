import hashlib
import json
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from resolve_method import CHAPTERS, FLOWS, resolve_method


class DesignResolverTests(unittest.TestCase):
    def test_all_selected_modules_are_pinned_and_have_qualification_criteria(self):
        methods = json.loads((ROOT / "references/methods.json").read_text(encoding="utf8"))
        self.assertEqual(len({row["path"] for row in methods}), 17)
        for row in methods:
            with self.subTest(path=row["path"]):
                flows = ("checkout",) if row["method"] == "userflow" else ()
                result = resolve_method(row["method"], decision=row["decision"], flows=flows)
                self.assertIn(result["status"], {"READY", "HANDOFF"})
                self.assertEqual(result["provenance"][0]["path"], row["path"])
                self.assertTrue(all(result[k] for k in ("owner", "evidence", "procedure", "acceptance")))
                self.assertEqual(result["provenance"][0]["sha256"],
                                 hashlib.sha256((ROOT / row["path"]).read_bytes()).hexdigest())

    def test_three_collisions_follow_decision_or_remain_undecided(self):
        for method, decision in (("survey-design", "market-segment"), ("interview-script", "purchase-decision"),
                                 ("summarize-interview", "purchase-decision")):
            with self.subTest(method=method):
                ambiguous = resolve_method(method)
                self.assertEqual(ambiguous["status"], "NEEDS_DECISION")
                self.assertCountEqual(ambiguous["choices"], ("task-usability", decision))
                ux = resolve_method(method, decision="task-usability")
                pm = resolve_method(method, decision=decision)
                self.assertIn("/designer-skills/", ux["read"][0])
                self.assertIn("/pm-skills/", pm["read"][0])
                self.assertNotEqual(ux["acceptance"], pm["acceptance"])

    def test_moved_stubs_hand_off_only_to_actual_local_owner(self):
        for name, owner in (("code-review", "shadow-quality"), ("intended-vs-implemented", "shadow-discovery"),
                            ("shipping-artifacts", "shadow-release")):
            result = resolve_method(name)
            self.assertEqual(result["status"], "HANDOFF")
            self.assertEqual(result["read"], [f"../{owner}/SKILL.md"])

    def test_each_curated_chapter_resolves_relative_to_package(self):
        for i, chapter in enumerate(CHAPTERS, 1):
            result = resolve_method("ai-product-designer", chapter=chapter)
            self.assertEqual(result["status"], "READY")
            self.assertTrue(result["read"][0].endswith(f"/{i:02d}-{chapter}.md"))

    def test_each_flow_and_multi_flow_review_reads_only_selected_references(self):
        for flow in FLOWS:
            self.assertEqual(resolve_method("userflow", flows=[flow])["status"], "READY")
        result = resolve_method("userflow", flows=["checkout", "errors", "checkout"])
        self.assertEqual([Path(p).parent.name for p in result["read"]], ["flow-checkout", "flow-errors"])
        self.assertEqual(resolve_method("userflow", flows=["errors"], output="html")["status"], "NEEDS_DECISION")
        self.assertEqual(resolve_method("live-polls", output="html")["status"], "UNSUPPORTED")

    def test_selection_never_interprets_arbitrary_input_as_a_path(self):
        for name in ("review-the-user", "code review screen", "draft an email", "publish", "../SKILL.md"):
            self.assertEqual(resolve_method(name)["status"], "UNSUPPORTED")
        self.assertEqual(resolve_method("survey-design", decision="../scripts")["status"], "UNSUPPORTED")

    def test_relocated_install_missing_tampered_and_unavailable_sibling(self):
        with tempfile.TemporaryDirectory() as work:
            home = Path(work)
            moved = home / "installed skills" / "shadow-design"
            shutil.copytree(ROOT, moved)
            project = home / "customer repo"
            project.mkdir()
            before = list(project.iterdir())
            proc = subprocess.run([sys.executable, str(moved / "scripts/resolve_method.py"), "userflow",
                                   "--flow", "checkout"], cwd=project, capture_output=True, check=True)
            result = json.loads(proc.stdout)
            self.assertEqual(result["status"], "READY")
            src = moved / result["read"][0]
            src.write_text("unverified replacement", encoding="utf8")
            self.assertEqual(resolve_method("userflow", flows=["checkout"], package=moved)["status"], "UNAVAILABLE")
            src.unlink()
            self.assertEqual(resolve_method("userflow", flows=["checkout"], package=moved)["status"], "UNAVAILABLE")
            self.assertEqual(resolve_method("code-review", package=moved)["status"], "UNAVAILABLE")
            self.assertEqual(list(project.iterdir()), before)

    def test_all_design_entrypoint_links_resolve_from_the_package(self):
        entry = (ROOT / "SKILL.md").read_text(encoding="utf8")
        self.assertNotIn("file:///", entry)
        for link in re.findall(r"\]\(([^)]+)\)", entry):
            if "://" not in link:
                self.assertTrue((ROOT / link.split("#")[0]).is_file(), link)


if __name__ == "__main__":
    unittest.main()
