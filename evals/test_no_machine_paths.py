r"""An open-source repo must not ship one operator's machine paths.

Fails when a tracked text file contains a personal home directory (Windows, macOS or Linux),
for example `C:\Users\alice\...`, `/Users/alice/...` or `/home/alice/...`. Generic service
accounts and documentation placeholders are allowed.
"""

from __future__ import annotations

from pathlib import Path
import re
import subprocess
import unittest

ROOT = Path(__file__).resolve().parents[1]
HOME_RE = re.compile(
    r"(?i)(?:\b[a-z]:(?:\\|\|/)+users(?:\\|\|/)+|(?<![\w.])/users/|(?<![\w.])/home/)"
    r"(?P<user>[a-z0-9._-]+)"
)
ALLOWED_USERS = {
    "<home>", "you", "user", "username", "your-user", "yourname", "name", "me", "example",
    "runner", "deploy", "node", "app", "ubuntu", "ec2-user", "admin", "root", "public", "default",
    "shared", "all", "appuser", "www-data", "git", "vscode", "codespace", "jenkins", "dev",
    "<user>", "%username%", "$user", "${user}", "{user}", "...", "…",
}
SELF = Path(__file__).resolve()
TEXT_SUFFIXES = {".md", ".json", ".py", ".txt", ".ps1", ".sh", ".mjs", ".js", ".ts", ".yml", ".yaml", ".toml"}


FILE_URI_RE = re.compile(r"(?i)file:///?[a-z]:/[^\s)\]\"'`]+")


def personal_paths(text: str) -> list[str]:
    hits = [m[0] for m in HOME_RE.finditer(text) if m["user"].lower() not in ALLOWED_USERS]
    # A file:// URI to a drive only resolves on the author's machine; links must be repo-relative.
    return hits + [m[0] for m in FILE_URI_RE.finditer(text)]


def tracked_text_files() -> list[Path]:
    names = subprocess.run(["git", "ls-files", "-co", "--exclude-standard"], cwd=ROOT,
                           capture_output=True, text=True, check=True).stdout.splitlines()
    return [ROOT / name for name in names if Path(name).suffix.lower() in TEXT_SUFFIXES and (ROOT / name).is_file()]


class NoMachinePathTests(unittest.TestCase):
    def test_detector_probes(self) -> None:
        recall = [r"C:\Users\alice\Downloads\pack", "C:/Users/bob/AppData", r"C:\Users\carol\x",
                  "/Users/dave/projects", "/home/erin/.config", "d:/users/frank/tmp",
                  "file:///D:/My%20Work/repo/skill/SKILL.md", "file:///c:/src/app/README.md"]
        precision = ["/home/deploy/app", "/home/runner/work", r"C:\Users\<home>\x", "/Users/you/project",
                     "~/.claude/settings.json", "$HOME/.codex", "https://example.com/users/alice",
                     "api/users/{id}", "/api/home/feed", "C:/Users/%USERNAME%/AppData",
                     "[guide](../shadow-design/SKILL.md)", "file://server/share is not a drive path"]
        for sample in recall:
            with self.subTest(recall=sample):
                self.assertTrue(personal_paths(sample), sample)
        for sample in precision:
            with self.subTest(precision=sample):
                self.assertEqual(personal_paths(sample), [], sample)

    def test_repo_contains_no_personal_home_paths(self) -> None:
        offenders: list[str] = []
        for path in tracked_text_files():
            if path.resolve() == SELF:
                continue  # the detector probes above are synthetic
            try:
                text = path.read_text(encoding="utf-8")
            except UnicodeDecodeError:
                continue
            for hit in personal_paths(text):
                offenders.append(f"{path.relative_to(ROOT).as_posix()}: {hit}")
        self.assertEqual(offenders, [], "\n".join(offenders[:20]))


if __name__ == "__main__":
    unittest.main()
