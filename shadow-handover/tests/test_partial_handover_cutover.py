"""Partial-handover cutover gating against the shipped check_receipt.py."""
from __future__ import annotations

import hashlib
import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from types import ModuleType
from typing import Any

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "check_receipt.py"
ARTIFACT_BYTES = b'{"bomFormat":"CycloneDX","release":"3.2.0"}'


def _load() -> ModuleType:
    spec = importlib.util.spec_from_file_location("check_receipt_under_test", SCRIPT)
    if spec is None or spec.loader is None:
        raise ImportError(f"cannot load {SCRIPT}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


checker = _load()


def receipt(**overrides: Any) -> dict[str, Any]:
    doc: dict[str, Any] = {
        "release": "3.2.0",
        "contract_ref": "C4-ADD-2",
        "sender": "delivery",
        "recipient": "ops",
        "criteria": "restore exercise",
        "warranty_owner": "support",
        "contract_sha256": hashlib.sha256(ARTIFACT_BYTES).hexdigest(),
        "signed_receipt_ref": "BAST-3.2.0",
        "operator_demo_ref": "WALKTHROUGH-3.2.0",
        "access_receipt_ref": "SHIFT-CUTOVER-3.2.0",
    }
    doc.update(overrides)
    return doc


class PartialHandoverCutoverTests(unittest.TestCase):
    def setUp(self) -> None:
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.dir = Path(tmp.name)
        self.artifact = self.dir / "sbom.json"
        self.artifact.write_bytes(ARTIFACT_BYTES)

    def assess(self, doc: object) -> dict[str, Any]:
        return checker.assess(self.artifact, doc)

    def test_release_3_2_partial_handover_enforces_walkthrough_and_shift_cutover(self) -> None:
        for missing in ("operator_demo_ref", "access_receipt_ref"):
            with self.subTest(missing=missing):
                res = self.assess(receipt(**{missing: None}))
                self.assertEqual(res["status"], "PENDING")
                self.assertEqual(res["pending"], [missing])
        ready = self.assess(receipt())
        self.assertEqual(ready, {"status": "READY_FOR_RECEIPT_REVIEW", "pending": []})

    def test_uppercase_digest_accepted(self) -> None:
        upper = hashlib.sha256(ARTIFACT_BYTES).hexdigest().upper()
        self.assertEqual(self.assess(receipt(contract_sha256=upper))["status"], "READY_FOR_RECEIPT_REVIEW")

    def test_tampered_artifact_is_digest_mismatch(self) -> None:
        self.artifact.write_bytes(ARTIFACT_BYTES + b" ")
        self.assertEqual(self.assess(receipt())["pending"], ["digest_mismatch"])

    def test_malformed_digest_pending(self) -> None:
        good = hashlib.sha256(ARTIFACT_BYTES).hexdigest()
        for value in (None, "", good[:63], good + "\n", "z" * 64, 123):
            with self.subTest(value=value):
                self.assertIn("contract_sha256", self.assess(receipt(contract_sha256=value))["pending"])

    def test_wrong_type_or_blank_refs_pending(self) -> None:
        for key in ("signed_receipt_ref", "operator_demo_ref", "access_receipt_ref", "recipient", "warranty_owner"):
            for value in (True, False, 1, None, "   ", ""):
                with self.subTest(key=key, value=value):
                    res = self.assess(receipt(**{key: value}))
                    self.assertEqual(res["status"], "PENDING")
                    self.assertIn(key, res["pending"])

    def test_empty_receipt_lists_every_field(self) -> None:
        res = self.assess({})
        self.assertEqual(res["status"], "PENDING")
        self.assertEqual(len(res["pending"]), 10)

    def test_non_object_receipt_rejected(self) -> None:
        for bad in ([], "receipt", None):
            with self.subTest(bad=bad):
                with self.assertRaises(ValueError):
                    self.assess(bad)

    def test_missing_artifact_raises(self) -> None:
        with self.assertRaises(OSError):
            checker.assess(self.dir / "absent.bin", receipt())


class CheckReceiptCli(unittest.TestCase):
    def run_cli(self, doc: object, artifact_bytes: bytes | None = ARTIFACT_BYTES) -> subprocess.CompletedProcess[str]:
        with tempfile.TemporaryDirectory() as tmp:
            artifact = Path(tmp) / "release.bin"
            if artifact_bytes is not None:
                artifact.write_bytes(artifact_bytes)
            path = Path(tmp) / "receipt.json"
            path.write_text(json.dumps(doc), encoding="utf-8")
            return subprocess.run([sys.executable, "-B", str(SCRIPT), str(artifact), str(path)],
                                  capture_output=True, text=True, timeout=30)

    def test_cli_exit_codes(self) -> None:
        ok = self.run_cli(receipt())
        self.assertEqual(ok.returncode, 0)
        self.assertEqual(json.loads(ok.stdout)["status"], "READY_FOR_RECEIPT_REVIEW")
        self.assertEqual(self.run_cli(receipt(access_receipt_ref="")).returncode, 1)
        self.assertEqual(self.run_cli({}).returncode, 1)
        self.assertEqual(self.run_cli([]).returncode, 2)
        self.assertEqual(self.run_cli(receipt(), artifact_bytes=None).returncode, 2)


if __name__ == "__main__":
    unittest.main()
