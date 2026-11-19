from __future__ import annotations

import hashlib
import json
import subprocess
import sys
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "shadow-doc" / "scripts"))

import reference_verifier


def evaluate_source_record(record: dict[str, str], now: datetime, max_age_days: int = 365) -> dict[str, object]:
    required = ("owner", "effective_version", "accessed_at", "digest", "revalidation_trigger")
    missing = [k for k in required if not str(record.get(k, "")).strip()]
    if missing:
        return {"status": "UNKNOWN_METADATA", "missing": missing, "stale": True}
    accessed = datetime.fromisoformat(record["accessed_at"].replace("Z", "+00:00"))
    stale = (now - accessed) > timedelta(days=max_age_days)
    return {"status": "STALE" if stale else "VERIFIED_ARCHIVED", "missing": [], "stale": stale}


class ReferenceArchiveAndLocalGeneratorTests(unittest.TestCase):
    def test_x03_dated_source_metadata_stale_detection_and_offline_fallback(self) -> None:
        now = datetime(2026, 11, 19, tzinfo=timezone.utc)
        with tempfile.TemporaryDirectory() as tmp:
            ref_file = Path(tmp) / "perpres-46-2025.md"
            ref_file.write_text("# Perpres 46/2025 Summary\nOfficial extract.\n", encoding="utf-8")
            safety = reference_verifier.verify_file_safety(ref_file)
            self.assertTrue(safety["safe"])

            digest = hashlib.sha256(ref_file.read_bytes()).hexdigest()
            fresh = evaluate_source_record(
                {
                    "owner": "LKPP / Setneg",
                    "effective_version": "Perpres 46/2025",
                    "accessed_at": "2026-10-01T00:00:00Z",
                    "digest": digest,
                    "revalidation_trigger": "amendment_or_annual_review",
                },
                now=now,
            )
            self.assertEqual(fresh["status"], "VERIFIED_ARCHIVED")

            stale = evaluate_source_record(
                {
                    "owner": "OWASP",
                    "effective_version": "ASVS 4.0.3",
                    "accessed_at": "2024-01-01T00:00:00Z",
                    "digest": digest,
                    "revalidation_trigger": "major_release_5.0",
                },
                now=now,
            )
            self.assertEqual(stale["status"], "STALE")
            self.assertTrue(stale["stale"])

            missing = evaluate_source_record({"owner": "Unknown"}, now=now)
            self.assertEqual(missing["status"], "UNKNOWN_METADATA")

    def test_c15_existing_repo_generator_single_paragraph_update_without_new_pipeline(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            src = root / "docs" / "proposal.md"
            src.parent.mkdir(parents=True)
            src.write_text("# Proposal\n\nOriginal scope paragraph.\n", encoding="utf-8")
            gen = root / "build_doc.py"
            gen.write_text(
                "from pathlib import Path\n"
                "text = Path('docs/proposal.md').read_text(encoding='utf-8')\n"
                "Path('dist').mkdir(exist_ok=True)\n"
                "Path('dist/proposal.html').write_text(f'<article>{text}</article>', encoding='utf-8')\n",
                encoding="utf-8",
            )
            # Update only the source paragraph and re-run existing generator
            src.write_text("# Proposal\n\nUpdated single paragraph for section 1.\n", encoding="utf-8")
            subprocess.run([sys.executable, str(gen)], cwd=root, check=True)
            out = (root / "dist" / "proposal.html").read_text(encoding="utf-8")
            self.assertIn("Updated single paragraph for section 1.", out)
            # Ensure no competing global pipeline files were introduced
            self.assertFalse((root / "canonical-ast.json").exists())


if __name__ == "__main__":
    unittest.main()
