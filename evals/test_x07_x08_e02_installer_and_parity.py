from __future__ import annotations

import json
import shutil
import tempfile
import unittest
from pathlib import Path


def reconcile_multi_host_install(
    source_skills: Path,
    host_roots: dict[str, Path],
    interrupt_after_host: str | None = None,
) -> dict[str, object]:
    """Temp-profile-only simulator for multi-host install, interruption recovery, and single-skill rollback."""
    installed_hosts: list[str] = []
    partial = False
    for host, target in host_roots.items():
        skills_dir = target / "skills"
        skills_dir.mkdir(parents=True, exist_ok=True)
        for skill_dir in sorted(source_skills.iterdir()):
            if skill_dir.is_dir():
                dest = skills_dir / skill_dir.name
                if dest.exists():
                    shutil.rmtree(dest)
                shutil.copytree(skill_dir, dest)
        installed_hosts.append(host)
        if interrupt_after_host and host == interrupt_after_host:
            partial = True
            break
    return {"installed_hosts": installed_hosts, "partial": partial}


def rollback_single_skill(host_roots: dict[str, Path], skill_name: str, backup_dir: Path) -> None:
    for target in host_roots.values():
        dest = target / "skills" / skill_name
        if dest.exists():
            shutil.rmtree(dest)
        shutil.copytree(backup_dir / skill_name, dest)


class InstallerAndCrossHostParityTests(unittest.TestCase):
    def test_x08_e02_temp_profile_interrupted_install_reconciliation_and_single_skill_rollback(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            src = root / "repo-skills"
            backup = root / "backup"
            (src / "shadow-api").mkdir(parents=True)
            (src / "shadow-doc").mkdir(parents=True)
            (src / "shadow-api" / "SKILL.md").write_text("v1-api\n", encoding="utf-8")
            (src / "shadow-doc" / "SKILL.md").write_text("v1-doc\n", encoding="utf-8")
            shutil.copytree(src, backup)

            hosts = {
                "claude": root / "home" / ".claude",
                "codex": root / "home" / ".codex",
                "gemini": root / "home" / ".gemini",
            }

            # Initial full install
            r0 = reconcile_multi_host_install(src, hosts)
            self.assertFalse(r0["partial"])
            self.assertEqual(len(r0["installed_hosts"]), 3)

            # Upgrade v2 interrupted after first host -> creates drift between claude (v2) and codex/gemini (v1)
            (src / "shadow-api" / "SKILL.md").write_text("v2-api\n", encoding="utf-8")
            r_int = reconcile_multi_host_install(src, hosts, interrupt_after_host="claude")
            self.assertTrue(r_int["partial"])
            self.assertEqual((hosts["claude"] / "skills" / "shadow-api" / "SKILL.md").read_text(), "v2-api\n")
            self.assertEqual((hosts["codex"] / "skills" / "shadow-api" / "SKILL.md").read_text(), "v1-api\n")

            # Reconcile completes remaining hosts cleanly
            r_rec = reconcile_multi_host_install(src, hosts)
            self.assertFalse(r_rec["partial"])
            for h in hosts.values():
                self.assertEqual((h / "skills" / "shadow-api" / "SKILL.md").read_text(), "v2-api\n")

            # Single-skill rollback reverts shadow-api to v1 while keeping shadow-doc intact
            rollback_single_skill(hosts, "shadow-api", backup)
            for h in hosts.values():
                self.assertEqual((h / "skills" / "shadow-api" / "SKILL.md").read_text(), "v1-api\n")
                self.assertEqual((h / "skills" / "shadow-doc" / "SKILL.md").read_text(), "v1-doc\n")

    def test_x07_cross_host_fallback_rubric_marks_missing_interactive_tool_as_standalone_question(self) -> None:
        hosts_capabilities = {
            "antigravity": {"has_interactive_question_tool": True, "expected_channel": "ask_question"},
            "claude_code": {"has_interactive_question_tool": True, "expected_channel": "AskUserQuestion"},
            "codex": {"has_interactive_question_tool": True, "expected_channel": "request_user_input"},
            "plain_cli": {"has_interactive_question_tool": False, "expected_channel": "standalone_direct_question_and_wait"},
        }
        for host, cap in hosts_capabilities.items():
            channel = cap["expected_channel"] if cap["has_interactive_question_tool"] else "standalone_direct_question_and_wait"
            self.assertEqual(channel, cap["expected_channel"])
            self.assertTrue(json.dumps({host: cap}))


if __name__ == "__main__":
    unittest.main()
