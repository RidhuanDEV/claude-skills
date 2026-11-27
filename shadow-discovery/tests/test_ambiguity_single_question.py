from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "sla_ambiguity.py"
_spec = importlib.util.spec_from_file_location("sla_ambiguity", SCRIPT)
assert _spec is not None and _spec.loader is not None
sla_ambiguity = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(sla_ambiguity)


def run_cli(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-B", str(SCRIPT), *args], capture_output=True, text=True, timeout=60, check=False,
    )

class DiscoveryAmbiguityTests(unittest.TestCase):
    def test_c14_single_clarifying_question_for_calendar_vs_business_days(self) -> None:
        ambiguous = sla_ambiguity.detect("Approval SLA must complete within 7 days after submission.")
        self.assertTrue(ambiguous["ambiguous"])
        self.assertEqual(len(ambiguous["questions"]), 1)
        self.assertFalse(ambiguous["assumptions_invented"])
        explicit = sla_ambiguity.detect("Approval SLA must complete within 7 business days after submission.")
        self.assertEqual((explicit["ambiguous"], explicit["questions"]), (False, []))

    def test_question_names_the_duration_actually_stated(self) -> None:
        question = sla_ambiguity.detect("Refund must be processed within 14 days.")["questions"][0]
        self.assertIn("14-day", question)
        self.assertNotIn("7-day", question)

    def test_indonesian_basis_and_durations(self) -> None:
        self.assertEqual(sla_ambiguity.detect("Persetujuan maksimal 14 hari kerja.")["status"], "CLEAR")
        self.assertEqual(sla_ambiguity.detect("Laporan dikirim dalam 3 hari.")["status"], "AMBIGUOUS")

    def test_non_requirements_are_not_flagged(self) -> None:
        for text in ("No deadline stated.", "Kirim laporan secepatnya."):
            with self.subTest(text=text):
                self.assertFalse(sla_ambiguity.detect(text)["ambiguous"])
        self.assertEqual(sla_ambiguity.detect("")["status"], "INVALID_INPUT")

    def test_cli_self_test(self) -> None:
        self.assertEqual(run_cli("--self-test").returncode, 0)


if __name__ == "__main__":
    unittest.main()
