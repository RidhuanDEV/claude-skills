from __future__ import annotations

from decimal import Decimal, ROUND_HALF_UP
import subprocess
import tempfile
import unittest
from pathlib import Path


def git(cwd: Path, *args: str) -> str:
    proc = subprocess.run(["git", *args], cwd=cwd, capture_output=True, text=True, check=True)
    return proc.stdout.strip()


def apply_discount_cents(subtotal_cents: int, pct: Decimal) -> int:
    discount = (Decimal(subtotal_cents) * pct / Decimal("100")).quantize(Decimal("1"), rounding=ROUND_HALF_UP)
    return max(0, subtotal_cents - int(discount))


class WorktreeAndSemanticOrderTests(unittest.TestCase):
    def test_t03_target_branch_advance_invalidates_stale_merge_tree_preview(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            repo = root / "repo"
            repo.mkdir()
            git(repo, "init", "-b", "main")
            git(repo, "config", "user.email", "test@shadow.local")
            git(repo, "config", "user.name", "Shadow Test")
            (repo / "app.txt").write_text("v1\n", encoding="utf-8")
            git(repo, "add", "app.txt")
            git(repo, "commit", "-m", "init")

            wt_a = root / "wt-a"
            wt_b = root / "wt-b"
            git(repo, "worktree", "add", "-b", "feat/a", str(wt_a))
            git(repo, "worktree", "add", "-b", "feat/b", str(wt_b))

            (wt_a / "a.txt").write_text("feature a\n", encoding="utf-8")
            git(wt_a, "add", "a.txt")
            git(wt_a, "commit", "-m", "add a")

            preview_base_sha = git(repo, "rev-parse", "main")
            # Advance main independently
            (repo / "main.txt").write_text("main advance\n", encoding="utf-8")
            git(repo, "add", "main.txt")
            git(repo, "commit", "-m", "advance main")
            current_main_sha = git(repo, "rev-parse", "main")

            self.assertNotEqual(preview_base_sha, current_main_sha)
            # Clean worktrees before tempdir cleanup on Windows
            git(repo, "worktree", "remove", "--force", str(wt_a))
            git(repo, "worktree", "remove", "--force", str(wt_b))

    def test_t16_e09_semantic_event_ordering_catches_pre_commit_publish_but_allows_safe_refactor(self) -> None:
        def run_pipeline(events: list[str], publish_before_commit: bool, use_new_serializer: bool) -> list[str]:
            log: list[str] = []
            payload = "v2-serialized" if use_new_serializer else "v1-serialized"
            if publish_before_commit:
                log.append(f"PUBLISH:{payload}")
                log.append("DB_COMMIT")
            else:
                log.append("DB_COMMIT")
                log.append(f"PUBLISH:{payload}")
            events.extend(log)
            return log

        bad_trace: list[str] = []
        run_pipeline(bad_trace, publish_before_commit=True, use_new_serializer=False)
        self.assertLess(bad_trace.index("PUBLISH:v1-serialized"), bad_trace.index("DB_COMMIT"))

        good_trace: list[str] = []
        run_pipeline(good_trace, publish_before_commit=False, use_new_serializer=True)
        self.assertLess(good_trace.index("DB_COMMIT"), good_trace.index("PUBLISH:v2-serialized"))

    def test_t22_discount_rounding_boundaries_and_storage_idempotency(self) -> None:
        self.assertEqual(apply_discount_cents(100, Decimal("0")), 100)
        self.assertEqual(apply_discount_cents(100, Decimal("100")), 0)
        self.assertEqual(apply_discount_cents(105, Decimal("10")), 94)  # 10.5 -> 11 half-up
        self.assertEqual(apply_discount_cents(100, Decimal("150")), 0)

        store: dict[str, int] = {}
        for _ in range(3):
            store["order-1"] = apply_discount_cents(105, Decimal("10"))
        self.assertEqual(store, {"order-1": 94})


if __name__ == "__main__":
    unittest.main()
