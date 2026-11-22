import sys
import tempfile
import unittest
from pathlib import Path

EVALS_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(EVALS_DIR))

import validate_skill_evaluations as vse  # noqa: E402


class ValidateSkillEvaluationsTests(unittest.TestCase):
    def test_repo_upgraded_specialists_pass(self) -> None:
        report = vse.audit_repository()
        self.assertTrue(report["all_passed"], f"Unexpected failures: {report['failures']}")
        self.assertGreaterEqual(report["total_skills"], 59)
        self.assertGreaterEqual(report["skills_with_evaluations_md"], 5)

    def test_strict_skill_catches_orphan_ref_and_missing_evals(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            skill = root / "shadow-demo"
            (skill / "references").mkdir(parents=True)
            (skill / "SKILL.md").write_text(
                "---\nname: shadow-demo\ndescription: Demo\n---\n# Demo\n",
                encoding="utf-8",
            )
            (skill / "references" / "01-demo.md").write_text("# Demo ref\n", encoding="utf-8")
            res = vse.audit_skill(skill, strict_eval_required=True)
            self.assertEqual(res["status"], "FAIL")
            self.assertTrue(any("evaluations.md" in e for e in res["errors"]))
            self.assertTrue(any("Reference Guide" in e for e in res["errors"]))

    def test_strict_skill_passes_with_complete_index_and_eval_guards(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            skill = root / "shadow-demo"
            (skill / "references").mkdir(parents=True)
            (skill / "SKILL.md").write_text(
                "---\nname: shadow-demo\ndescription: Demo\n---\n\n## Reference Guide\n| T | R |\n|---|---|\n| A | [01](references/01-demo.md) |\n",
                encoding="utf-8",
            )
            (skill / "references" / "01-demo.md").write_text("# Demo ref\n", encoding="utf-8")
            (skill / "evaluations.md").write_text(
                "# Evals\n| ID | Scenario | Pass | Fail Red Flags |\n|---|---|---|---|\n"
                + "\n".join(f"| **DEMO-{i}** | S{i} | P{i} | F{i} |" for i in range(1, 6)),
                encoding="utf-8",
            )
            res = vse.audit_skill(skill, strict_eval_required=True)
            self.assertEqual(res["status"], "PASS")
            self.assertEqual(res["evaluation_scenarios"], 5)


if __name__ == "__main__":
    unittest.main()
