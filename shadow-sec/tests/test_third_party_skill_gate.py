import hashlib
import json
import os
import stat
import subprocess
import sys
import tempfile
import unittest
import zipfile
from datetime import datetime, timedelta, timezone
from pathlib import Path


CLI = Path(__file__).resolve().parents[1] / "scripts" / "third_party_skill_gate.py"
SKILL = "---\nname: fixture-skill\ndescription: A benign fixture skill\n---\n\n# Fixture skill\n"


class ThirdPartySkillGateTests(unittest.TestCase):
    def setUp(self):
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        self.root = Path(folder.name).resolve()
        self.snapshot = self.root / "snapshot.zip"
        self.skills = self.root / "skills"
        self.skills.mkdir()
        self.receipt = self.root / "reviewed.json"
        self.make_snapshot()
        now = datetime.now(timezone.utc)
        self.evidence = {
            "schema_version": 1, "policy": "shadow-sec/third-party-skill-v1",
            "source_url": "https://fixtures.example/owner/skill", "source_commit": "a" * 40,
            "snapshot_sha256": hashlib.sha256(self.snapshot.read_bytes()).hexdigest(), "verdict": "APPROVED",
            "gates": {f"G{index}": {"status": "PASS", "evidence": "Benign fixture reviewed"} for index in range(7)},
            "target": {"host": "codex", "skill_name": "fixture-skill", "skills_root": str(self.skills), "action": "install-new"},
            "approval": {"approved_by": "Fixture operator", "approved_at": now.isoformat(),
                         "expires_at": (now + timedelta(minutes=10)).isoformat()},
        }

    def make_snapshot(self, entries=None, skill=SKILL):
        with zipfile.ZipFile(self.snapshot, "w", compression=zipfile.ZIP_DEFLATED) as archive:
            archive.writestr("SKILL.md", skill)
            archive.writestr("references/notes.txt", "ordinary example text")
            for name, data in entries or []:
                archive.writestr(name, data)

    def command(self, action, *extra, authorized=False):
        args = [sys.executable, "-B", str(CLI), action, "--snapshot", str(self.snapshot)]
        if authorized:
            raw = json.dumps(self.evidence).encode()
            self.receipt.write_bytes(raw)
            args.extend(["--receipt", str(self.receipt), "--receipt-sha256", hashlib.sha256(raw).hexdigest(),
                         "--skills-root", str(self.skills)])
        process = subprocess.run([*args, *extra], check=False, capture_output=True, text=True, encoding="utf-8")
        return process.returncode, json.loads(process.stdout)

    def test_read_only_inventory_and_preflight(self):
        code, result = self.command("inspect")
        self.assertEqual(code, 0, result)
        self.assertEqual(result["snapshot_sha256"], self.evidence["snapshot_sha256"])
        self.assertEqual([file["path"] for file in result["files"]], ["SKILL.md", "references/notes.txt"])
        self.evidence["gates"]["G6"]["status"] = "NOT_APPLICABLE"
        self.assertEqual(self.command("preflight", authorized=True)[1]["status"], "ELIGIBLE")
        self.assertEqual(list(self.skills.iterdir()), [])

    def test_blocks_missing_permission_digest_and_target_drift(self):
        checks = (
            self.command("install", "--approve"),
            self.command("install", authorized=True),
            self.command("install", "--approve", "--receipt-sha256", "0" * 64, authorized=True),
        )
        self.make_snapshot(entries=[("notes.txt", "different reviewed bytes")])
        self.assertIn("exact snapshot", self.command("install", "--approve", authorized=True)[1]["reason"])
        for code, result in checks:
            self.assertEqual((code, result["status"]), (1, "BLOCKED"), result)
        self.evidence["snapshot_sha256"] = hashlib.sha256(self.snapshot.read_bytes()).hexdigest()
        self.evidence["target"]["skills_root"] = str(self.root / "different-profile")
        self.assertIn("exact host", self.command("preflight", authorized=True)[1]["reason"])
        self.assertEqual(list(self.skills.iterdir()), [])

    def test_blocks_expired_approval_and_missing_gate_evidence(self):
        self.evidence["gates"]["G4"]["status"] = "NOT_RUN"
        self.assertIn("G4", self.command("preflight", authorized=True)[1]["reason"])
        self.evidence["gates"]["G4"]["status"] = "PASS"
        self.evidence["approval"]["expires_at"] = (datetime.now(timezone.utc) - timedelta(minutes=1)).isoformat()
        self.assertIn("currently valid", self.command("preflight", authorized=True)[1]["reason"])
        self.assertEqual(list(self.skills.iterdir()), [])

    def test_rejects_unsupported_archive_entries_and_bad_manifest(self):
        link = zipfile.ZipInfo("link.txt")
        link.create_system = 3
        link.external_attr = (stat.S_IFLNK | 0o777) << 16
        for entries in (
            [(link, "inert link entry")], [("../notes.txt", "inert text")],
            [("References/extra.txt", "case collision")], [("AGENTS.md", "host instruction file")],
            [("config.json", "{}")], [("nul.txt", "reserved file name")],
        ):
            with self.subTest(entries=entries):
                self.make_snapshot(entries)
                self.assertEqual(self.command("inspect")[1]["status"], "BLOCKED")
        for bad_header in (
            SKILL.replace("description:", "unknown:"), SKILL.replace("fixture-skill", "con"),
            SKILL.replace("fixture-skill", "2026-01-01"), SKILL.replace("\n", "\u0085"),
        ):
            self.make_snapshot(skill=bad_header)
            self.assertEqual(self.command("inspect")[1]["status"], "BLOCKED")

    @unittest.skipUnless(os.name == "nt", "Managed activation pilot uses Windows atomic rename")
    def test_windows_install_copies_same_bytes_refuses_replacement_and_rolls_back(self):
        code, result = self.command("install", "--approve", authorized=True)
        self.assertEqual((code, result["status"]), (0, "INSTALLED"), result)
        target = self.skills / "fixture-skill"
        skill_file = target / "SKILL.md"
        notes = target / "references" / "notes.txt"
        self.assertEqual(skill_file.read_bytes(), SKILL.encode())
        self.assertEqual(notes.read_bytes(), b"ordinary example text")
        self.assertEqual(self.command("install", "--approve", authorized=True)[1]["status"], "BLOCKED")
        self.assertEqual(skill_file.read_bytes(), SKILL.encode())
        notes.unlink()
        notes.parent.rmdir()
        skill_file.unlink()
        target.rmdir()
        self.assertEqual(list(self.skills.iterdir()), [])
        self.assertEqual(list(self.root.glob(".shadow-skill-*")), [])


if __name__ == "__main__":
    unittest.main()
