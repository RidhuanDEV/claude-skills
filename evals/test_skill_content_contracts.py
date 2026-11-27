"""Content contract for every skill, including the ones that ship no scripts.

A skill without code is still shipped content: its frontmatter, links, named helper scripts and
graded scenarios must stay valid. These checks fail when that content breaks.
"""

from __future__ import annotations

import json
from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parents[1]
SKILLS = sorted(path.parent for path in ROOT.glob("*/SKILL.md"))
FRONTMATTER_RE = re.compile(r"\A---\n(.*?)\n---\n", re.DOTALL)
NAME_RE = re.compile(r"^name:\s*(\S+)\s*$", re.MULTILINE)
DESCRIPTION_RE = re.compile(r"^description:\s*(.+)$", re.MULTILINE)
LINK_RE = re.compile(r"\]\((?!https?://|mailto:|#)([^)\s#]+)(?:#[^)]*)?\)")
CODE_FENCE_RE = re.compile(r"```.*?```", re.DOTALL)
OWN_SCRIPT_RE = re.compile(r"[\"`](?P<skill>[a-z0-9-]+)/scripts/(?P<file>[\w.-]+\.(?:py|mjs|js|ps1|sh))[\"`]")
SCENARIO_ROW_RE = re.compile(r"^\|(?P<first>[^|\n]+)\|(?P<cells>.+)\|\s*$", re.MULTILINE)
HEADER_CELLS = ("id", "probe", "scenario", "case", "check")
DESCRIPTION_LIMIT = 250


def frontmatter(skill: Path) -> str:
    match = FRONTMATTER_RE.match((skill / "SKILL.md").read_text(encoding="utf-8-sig").replace("\r\n", "\n"))
    return match[1] if match else ""


def graded_table_rows(text: str) -> list[str]:
    """Rows of a markdown table whose header names a prompt column and a pass/expected column."""
    rows: list[str] = []
    header: list[str] | None = None
    for line in text.splitlines():
        if not line.startswith("|"):
            header = None
            continue
        cells = [cell.strip().strip("*` ").lower() for cell in line.strip().strip("|").split("|")]
        if header is None:
            if any("prompt" in cell for cell in cells) and any("pass" in cell or "expected" in cell for cell in cells):
                header = cells
            continue
        if set("".join(cells)) <= set("-: "):
            continue
        rows.append(line)
    return rows


class SkillContentContractTests(unittest.TestCase):
    def test_catalog_is_complete(self) -> None:
        self.assertEqual(len(SKILLS), 59)

    def test_frontmatter_name_matches_folder_and_description_is_bounded(self) -> None:
        for skill in SKILLS:
            with self.subTest(skill=skill.name):
                block = frontmatter(skill)
                name = NAME_RE.search(block)
                description = DESCRIPTION_RE.search(block)
                self.assertIsNotNone(name, "missing name")
                self.assertEqual(name[1].strip("\"'"), skill.name)
                self.assertIsNotNone(description, "missing description")
                raw = description[1].strip()
                text = json.loads(raw) if raw.startswith('"') else raw
                self.assertLessEqual(len(text), DESCRIPTION_LIMIT)
                self.assertRegex(text, r"(?i)\buse\s+(?:only\s+)?when\b")

    def test_every_relative_link_in_skill_md_resolves(self) -> None:
        for skill in SKILLS:
            text = CODE_FENCE_RE.sub("", (skill / "SKILL.md").read_text(encoding="utf-8-sig"))
            for target in LINK_RE.findall(text):
                with self.subTest(skill=skill.name, link=target):
                    self.assertTrue((skill / target).resolve().exists(), f"{target} does not exist")

    def test_helper_scripts_named_for_this_skill_exist(self) -> None:
        for skill in SKILLS:
            text = (skill / "SKILL.md").read_text(encoding="utf-8-sig")
            for match in OWN_SCRIPT_RE.finditer(text):
                with self.subTest(skill=skill.name, script=match[0]):
                    self.assertTrue((ROOT / match["skill"] / "scripts" / match["file"]).exists())

    def test_every_skill_has_graded_scenarios_with_failure_signals(self) -> None:
        for skill in SKILLS:
            with self.subTest(skill=skill.name):
                path = skill / "evaluations.md"
                if skill.name == "shadow-monarch":
                    # The orchestrator's graded prompts live in the repo-level suite.
                    suite = json.loads((ROOT / "evals" / "evals.json").read_text(encoding="utf-8"))
                    self.assertGreaterEqual(len(suite["evals"]), 3)
                    continue
                self.assertTrue(path.exists(), "evaluations.md missing")
                text = path.read_text(encoding="utf-8")
                rows = [
                    match for match in SCENARIO_ROW_RE.finditer(text)
                    if not set(match["first"].strip()) <= set("-: ")
                    and match["first"].strip(" *`").lower() not in HEADER_CELLS
                ]
                headings = re.findall(r"^###\s+\S[^\n]*\n(?:[^\n]*\n){0,3}?[^\n]*\*\*Prompt", text, re.MULTILINE)
                graded_rows = graded_table_rows(text)
                self.assertGreaterEqual(len(graded_rows) + len(headings), 3,
                                        "fewer than 3 graded scenarios with a prompt and pass criteria")
                self.assertRegex(text, r"(?i)fail|red flag|must_not|must not", "no failure signal column")


if __name__ == "__main__":
    unittest.main()
