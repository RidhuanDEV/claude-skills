from __future__ import annotations

import importlib.util
from pathlib import Path
import subprocess
import sys
import unittest

SCRIPT = Path(__file__).resolve().parents[1] / "contrast-check.py"
_spec = importlib.util.spec_from_file_location("contrast_check", SCRIPT)
assert _spec is not None and _spec.loader is not None
contrast_check = importlib.util.module_from_spec(_spec)
sys.modules["contrast_check"] = contrast_check
_spec.loader.exec_module(contrast_check)


def ratio(foreground: str, background: str) -> float:
    return contrast_check.contrast_ratio(contrast_check.parse_hex(foreground), contrast_check.parse_hex(background))


class ContrastCheckTests(unittest.TestCase):
    def test_known_wcag_pairs(self) -> None:
        self.assertAlmostEqual(ratio("#000000", "#ffffff"), 21.0, places=2)
        self.assertAlmostEqual(ratio("#767676", "#ffffff"), 4.54, places=2)
        self.assertLess(ratio("#777777", "#ffffff"), 4.5)
        self.assertAlmostEqual(ratio("#ffffff", "#ffffff"), 1.0, places=2)

    def test_ratio_is_symmetric(self) -> None:
        self.assertAlmostEqual(ratio("#336699", "#f0f0f0"), ratio("#f0f0f0", "#336699"), places=6)

    def test_cli_verdicts_follow_the_aa_thresholds(self) -> None:
        passing = subprocess.run([sys.executable, "-B", str(SCRIPT), "#767676", "#ffffff"],
                                 capture_output=True, text=True, timeout=60, check=False)
        self.assertIn("normal text (4.5:1): PASS", passing.stdout)
        failing = subprocess.run([sys.executable, "-B", str(SCRIPT), "#777777", "#ffffff"],
                                 capture_output=True, text=True, timeout=60, check=False)
        self.assertIn("normal text (4.5:1): FAIL", failing.stdout)

    def test_invalid_colors_are_rejected(self) -> None:
        for value in ("#12345", "red", "#gggggg", ""):
            with self.subTest(value=value):
                with self.assertRaises((ValueError, TypeError)):
                    contrast_check.parse_hex(value)

    def test_selftest_against_reference_table(self) -> None:
        result = subprocess.run([sys.executable, "-B", str(SCRIPT), "--selftest"],
                                capture_output=True, text=True, timeout=60, check=False)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
