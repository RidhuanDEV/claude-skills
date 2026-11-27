"""Every vendored third-party file must carry a license notice and match its provenance lock."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
VENDOR_DIRS = sorted(path for path in ROOT.glob("*/references/vendor") if path.is_dir())
ALLOWED_LICENSES = {"MIT", "CC-BY-SA-4.0", "CC0-1.0", "Apache-2.0"}
NOTICE_MARKER = "Vendored third-party content"
BOOKKEEPING = {"VENDOR.json", "LICENSES.md"}


class VendorProvenanceTests(unittest.TestCase):
    def test_vendor_folders_exist(self) -> None:
        self.assertGreaterEqual(len(VENDOR_DIRS), 2)

    def test_every_vendored_file_is_locked_licensed_and_unchanged(self) -> None:
        for folder in VENDOR_DIRS:
            lock_path = folder / "VENDOR.json"
            with self.subTest(folder=folder.relative_to(ROOT).as_posix()):
                self.assertTrue(lock_path.exists(), "VENDOR.json missing")
                self.assertTrue((folder / "LICENSES.md").exists(), "LICENSES.md missing")
                entries = {entry["file"]: entry for entry in json.loads(lock_path.read_text(encoding="utf-8"))["files"]}
                present = {path.name for path in folder.iterdir() if path.is_file() and path.name not in BOOKKEEPING}
                self.assertEqual(present, set(entries), "files and lock entries differ")
                for name, entry in entries.items():
                    # Hash with LF line endings so the lock holds on autocrlf checkouts too.
                    data = (folder / name).read_bytes().replace(b"\r\n", b"\n")
                    self.assertIn(entry["license"], ALLOWED_LICENSES, name)
                    self.assertTrue(entry["source_url"].startswith("https://"), name)
                    self.assertEqual(hashlib.sha256(data).hexdigest(), entry["sha256"], f"{name} changed without updating VENDOR.json")
                    self.assertIn(NOTICE_MARKER, data[:600].decode("utf-8", errors="replace"), f"{name} lacks its license notice")

    def test_share_alike_files_say_so_and_are_excluded_from_mit(self) -> None:
        notices = (ROOT / "THIRD_PARTY_NOTICES.md").read_text(encoding="utf-8")
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        self.assertIn("THIRD_PARTY_NOTICES.md", readme)
        for folder in VENDOR_DIRS:
            self.assertIn(folder.relative_to(ROOT).as_posix(), notices)
            for entry in json.loads((folder / "VENDOR.json").read_text(encoding="utf-8"))["files"]:
                if entry["license"] == "CC-BY-SA-4.0":
                    head = (folder / entry["file"]).read_text(encoding="utf-8")[:600]
                    with self.subTest(file=entry["file"]):
                        self.assertIn("CC BY-SA 4.0", head)
                        self.assertIn("Modified:", head)
                        self.assertIn(entry["source_url"], head)


if __name__ == "__main__":
    unittest.main()
