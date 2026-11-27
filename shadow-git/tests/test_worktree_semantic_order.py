"""Exercise the shipped git_orchestrator against real temporary repositories (no network, no pushes)."""

from __future__ import annotations

import importlib.util
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "git_orchestrator.py"
_spec = importlib.util.spec_from_file_location("git_orchestrator", SCRIPT)
assert _spec is not None and _spec.loader is not None
git_orchestrator = importlib.util.module_from_spec(_spec)
sys.modules["git_orchestrator"] = git_orchestrator
_spec.loader.exec_module(git_orchestrator)

GIT_AVAILABLE = shutil.which("git") is not None


def git(cwd: Path, *args: str) -> str:
    completed = subprocess.run(["git", *args], cwd=cwd, capture_output=True, text=True, check=True, timeout=60)
    return completed.stdout.strip()


def init_repo(root: Path) -> Path:
    repo = root / "repo"
    repo.mkdir()
    git(repo, "init", "-q", "-b", "main")
    git(repo, "config", "user.email", "test@example.invalid")
    git(repo, "config", "user.name", "Shadow Test")
    git(repo, "config", "commit.gpgsign", "false")
    (repo / "app.py").write_text("VALUE = 1\n", encoding="utf-8")
    git(repo, "add", "app.py")
    git(repo, "commit", "-q", "-m", "initial")
    return repo


def commit_on(repo: Path, branch: str, filename: str, content: str, base: str = "main") -> None:
    git(repo, "checkout", "-q", "-B", branch, base)
    (repo / filename).parent.mkdir(parents=True, exist_ok=True)
    (repo / filename).write_text(content, encoding="utf-8")
    git(repo, "add", filename)
    git(repo, "commit", "-q", "-m", f"change {filename} on {branch}")
    git(repo, "checkout", "-q", "main")


class RedactionTests(unittest.TestCase):
    def test_credentials_are_redacted(self) -> None:
        cases = (
            "remote https://user:s3cr3tpass@github.com/acme/app.git",
            "token ghp_" + "A" * 30,
            "key AKIA" + "B" * 16,
        )
        for text in cases:
            with self.subTest(text=text):
                out = git_orchestrator.redact_secrets(text)
                self.assertIn("[REDACTED", out)
                self.assertNotIn("s3cr3tpass", out)

    def test_ordinary_text_is_untouched(self) -> None:
        for text in ("https://github.com/acme/app.git", "branch feature/ghp-docs", "AKIA is a prefix"):
            with self.subTest(text=text):
                self.assertEqual(git_orchestrator.redact_secrets(text), text)


@unittest.skipUnless(GIT_AVAILABLE, "git is not installed")
class WorktreeGateTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.repo = init_repo(Path(self._tmp.name))

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def test_status_distinguishes_clean_untracked_staged_and_missing(self) -> None:
        self.assertTrue(git_orchestrator.inspect_worktree_status(self.repo)["clean"])
        (self.repo / "notes.txt").write_text("wip\n", encoding="utf-8")
        untracked = git_orchestrator.inspect_worktree_status(self.repo)
        self.assertEqual((untracked["dirty"], untracked["untracked_count"]), (True, 1))
        git(self.repo, "add", "notes.txt")
        self.assertEqual(git_orchestrator.inspect_worktree_status(self.repo)["staged_count"], 1)
        self.assertFalse(git_orchestrator.inspect_worktree_status(self.repo / "missing")["exists"])

    def test_ongoing_merge_is_detected(self) -> None:
        self.assertEqual(git_orchestrator.detect_ongoing_operations(self.repo), [])
        head = git(self.repo, "rev-parse", "HEAD")
        (self.repo / ".git" / "MERGE_HEAD").write_text(head + "\n", encoding="utf-8")
        self.assertIn("MERGE_IN_PROGRESS", git_orchestrator.detect_ongoing_operations(self.repo))

    def test_conflict_prediction_separates_real_conflicts_from_clean_merges(self) -> None:
        commit_on(self.repo, "feature-a", "app.py", "VALUE = 2\n")
        commit_on(self.repo, "feature-b", "app.py", "VALUE = 3\n")
        commit_on(self.repo, "feature-c", "other.py", "OTHER = 1\n")
        conflict = git_orchestrator.predict_conflicts_and_risks(self.repo, "feature-a", "feature-b")
        self.assertTrue(conflict["has_git_conflicts"])
        self.assertFalse(conflict["safe_to_merge_automatically"])
        self.assertIn("app.py", conflict["both_modified_files"])
        clean = git_orchestrator.predict_conflicts_and_risks(self.repo, "feature-c", "main")
        self.assertFalse(clean["has_git_conflicts"])
        self.assertTrue(clean["safe_to_merge_automatically"])

    def test_parallel_migrations_are_a_semantic_risk_even_without_conflicts(self) -> None:
        commit_on(self.repo, "feature-a", "migrations/0002_a.sql", "ALTER TABLE t ADD a int;\n")
        commit_on(self.repo, "feature-b", "migrations/0002_b.sql", "ALTER TABLE t ADD b int;\n")
        result = git_orchestrator.predict_conflicts_and_risks(self.repo, "feature-a", "feature-b")
        self.assertFalse(result["has_git_conflicts"])
        self.assertIn("PARALLEL_SCHEMA_MIGRATIONS", {risk["type"] for risk in result["semantic_risks"]})
        self.assertFalse(result["safe_to_merge_automatically"])

    def test_unknown_ref_is_rejected(self) -> None:
        with self.assertRaises(ValueError):
            git_orchestrator.predict_conflicts_and_risks(self.repo, "does-not-exist", "main")

    def test_cleanup_previews_without_approval_and_blocks_unmerged_dirty_work(self) -> None:
        commit_on(self.repo, "feature-x", "x.py", "X = 1\n")
        worktree = Path(self._tmp.name) / "wt-x"
        git(self.repo, "worktree", "add", "-q", str(worktree), "feature-x")
        (worktree / "scratch.txt").write_text("unsaved\n", encoding="utf-8")
        preview = git_orchestrator.safe_cleanup(self.repo, "feature-x", target_branch="main")
        self.assertEqual(preview["mode"], "READ_ONLY_PREVIEW")
        self.assertFalse(preview["safe_to_clean"])
        self.assertTrue(preview["blockers"])
        with self.assertRaises(RuntimeError):
            git_orchestrator.safe_cleanup(self.repo, "feature-x", target_branch="main", approve=True, delete_branch=True)
        self.assertTrue((worktree / "scratch.txt").exists())


@unittest.skipUnless(GIT_AVAILABLE, "git is not installed")
class AcceptanceSuiteTests(unittest.TestCase):
    def test_shipped_acceptance_suite_passes(self) -> None:
        report = git_orchestrator.run_acceptance_suite()
        failed = [result["test_id"] for result in report["results"] if result["status"] != "PASS"]
        self.assertTrue(report["all_passed"], failed)
        self.assertGreaterEqual(report["total_tests"], 13)


if __name__ == "__main__":
    unittest.main()
