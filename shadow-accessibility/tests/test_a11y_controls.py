from __future__ import annotations

import importlib.util
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from types import ModuleType

SCRIPT_PATH = Path(__file__).resolve().parents[1] / "scripts" / "a11y_html_verifier.py"


def _load_module() -> ModuleType:
    spec = importlib.util.spec_from_file_location("a11y_html_verifier_controls", SCRIPT_PATH)
    if spec is None or spec.loader is None:
        raise ImportError(f"Cannot load {SCRIPT_PATH}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


ahv = _load_module()


def _codes(html: object) -> list[str]:
    return [v["code"] for v in ahv.audit_html(html)]


def _run_cli(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-B", str(SCRIPT_PATH), *args],
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )


class AccessibleInputLabelTests(unittest.TestCase):
    def test_c04_accepts_wrapped_explicit_and_aria_labels(self) -> None:
        good_html = (
            '<label for="email">Email</label><input id="email" type="email" />'
            '<label>Phone <input type="tel" /></label>'
            '<input type="search" aria-label="Search orders" />'
            '<input type="hidden" name="csrf" value="abc" />'
        )
        self.assertEqual(ahv.audit_html(good_html), [])

    def test_c04_rejects_placeholder_only_input(self) -> None:
        violations = ahv.audit_html('<input type="text" placeholder="Enter your email" />')
        self.assertEqual([v["code"] for v in violations], ["UNLABELED_INPUT"])
        self.assertIn("placeholder alone is insufficient", violations[0]["detail"])

    def test_c04_rejects_label_for_pointing_at_different_id(self) -> None:
        html = '<label for="email">Email</label><input id="phone" type="tel" />'
        self.assertEqual(_codes(html), ["UNLABELED_INPUT"])

    def test_c04_rejects_empty_aria_label(self) -> None:
        self.assertEqual(_codes('<input type="text" aria-label="" />'), ["UNLABELED_INPUT"])

    def test_c04_text_input_is_not_exempt_like_hidden(self) -> None:
        self.assertEqual(_codes('<input type="text" />'), ["UNLABELED_INPUT"])
        self.assertEqual(_codes('<input type="submit" value="Send" />'), [])


class FocusAndKeyboardTests(unittest.TestCase):
    """Dialog focus restoration has no shipped checker; these cover the shipped focus rules instead."""

    def test_c04_dialog_with_focus_visible_ring_passes(self) -> None:
        html = (
            "<style>dialog button:focus { outline: none; }"
            " dialog button:focus-visible { outline: 2px solid #2563EB; }</style>"
            '<button type="button">Open</button><dialog><button type="button">Close</button></dialog>'
        )
        self.assertEqual(ahv.audit_html(html), [])

    def test_c04_dialog_close_button_with_suppressed_outline_fails(self) -> None:
        html = '<style>dialog button:focus { outline: 0; }</style><dialog><button>Close</button></dialog>'
        self.assertEqual(_codes(html), ["FOCUS_OUTLINE_REMOVED"])

    def test_positive_tabindex_and_div_onclick_fail(self) -> None:
        codes = _codes('<div onclick="openModal()" tabindex="3">Open</div>')
        self.assertIn("NON_SEMANTIC_CLICKABLE", codes)
        self.assertIn("POSITIVE_TABINDEX", codes)

    def test_zero_and_negative_tabindex_pass(self) -> None:
        self.assertEqual(ahv.audit_html('<button tabindex="0">A</button><button tabindex="-1">B</button>'), [])


class DocumentStructureTests(unittest.TestCase):
    def test_sequential_headings_lang_and_decorative_alt_pass(self) -> None:
        html = '<html lang="id"><body><h1>A</h1><h2>B</h2><h2>C</h2><h3>D</h3><img src="x.svg" alt="" /></body></html>'
        self.assertEqual(ahv.audit_html(html), [])

    def test_skipped_heading_missing_lang_and_missing_alt_fail(self) -> None:
        codes = set(_codes('<html><body><h1>A</h1><h3>B</h3><img src="x.png" /></body></html>'))
        self.assertEqual(codes, {"MISSING_HTML_LANG", "SKIPPED_HEADING_LEVEL", "IMG_MISSING_ALT"})


class EmptyAndWrongTypeInputTests(unittest.TestCase):
    def test_empty_and_whitespace_html_blocked(self) -> None:
        self.assertEqual(_codes(""), ["EMPTY_HTML"])
        self.assertEqual(_codes("   \n"), ["EMPTY_HTML"])

    def test_wrong_type_html_blocked(self) -> None:
        for bad in (None, 123, b"<input>", ["<input>"], False):
            with self.subTest(bad=bad):
                self.assertEqual(_codes(bad), ["EMPTY_HTML"])


class ContrastRatioTests(unittest.TestCase):
    def test_extremes_and_symmetry(self) -> None:
        self.assertEqual(ahv.contrast_ratio("#000000", "#FFFFFF"), 21.0)
        self.assertEqual(ahv.contrast_ratio("#FFFFFF", "#000000"), 21.0)
        self.assertEqual(ahv.contrast_ratio("#777777", "#777777"), 1.0)
        self.assertEqual(ahv.contrast_ratio("fff", "#FFFFFF"), 1.0)

    def test_aa_threshold_sides(self) -> None:
        self.assertGreaterEqual(ahv.contrast_ratio("#111827", "#FFFFFF"), 4.5)
        self.assertLess(ahv.contrast_ratio("#9CA3AF", "#FFFFFF"), 4.5)

    def test_invalid_colors_raise_value_error(self) -> None:
        for bad in ("", "#12345", "#GGGGGG", "false", "true", "#1234567"):
            with self.subTest(bad=bad):
                with self.assertRaises(ValueError):
                    ahv.contrast_ratio(bad, "#FFFFFF")

    def test_wrong_type_colors_raise_value_error(self) -> None:
        for bad in (None, 0, 0x000000, ["#000000"]):
            with self.subTest(bad=bad):
                with self.assertRaises(ValueError):
                    ahv.contrast_ratio(bad, "#FFFFFF")


class CliGateTests(unittest.TestCase):
    def test_check_contrast_exit_codes(self) -> None:
        self.assertEqual(_run_cli("--check-contrast", "#111827", "#FFFFFF").returncode, 0)
        self.assertEqual(_run_cli("--check-contrast", "#CCCCCC", "#FFFFFF").returncode, 1)
        self.assertNotEqual(_run_cli("--check-contrast", "false", "#FFFFFF").returncode, 0)

    def test_check_html_exit_codes(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            good = Path(tmp) / "good.html"
            good.write_text('<html lang="en"><body><h1>Ok</h1></body></html>', encoding="utf-8")
            bad = Path(tmp) / "bad.html"
            bad.write_text('<input type="text" placeholder="Name" />', encoding="utf-8")
            empty = Path(tmp) / "empty.html"
            empty.write_text("", encoding="utf-8")
            good_run = _run_cli("--check-html", str(good))
            self.assertEqual(good_run.returncode, 0, good_run.stdout)
            self.assertIn('"status": "PASS"', good_run.stdout)
            self.assertEqual(_run_cli("--check-html", str(bad)).returncode, 1)
            self.assertEqual(_run_cli("--check-html", str(empty)).returncode, 1)

    def test_self_test_cli_passes(self) -> None:
        self.assertEqual(_run_cli("--self-test").returncode, 0)


if __name__ == "__main__":
    unittest.main()
