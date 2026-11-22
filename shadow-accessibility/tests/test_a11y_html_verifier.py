import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import a11y_html_verifier as ahv


class A11yHtmlVerifierTests(unittest.TestCase):
    def test_self_test_probes(self) -> None:
        report = ahv.run_self_test()
        self.assertTrue(report["all_passed"], report)
        self.assertEqual(report["total_probes"], 7)

    def test_outline_none_with_focus_visible_replacement_passes(self) -> None:
        html = (
            "<style>button:focus { outline: none; } "
            "button:focus-visible { outline: 2px solid #2563EB; outline-offset: 2px; }</style>"
            "<button>Submit</button>"
        )
        self.assertEqual(ahv.audit_html(html), [])

    def test_contrast_ratio_exact_black_on_white(self) -> None:
        self.assertEqual(ahv.contrast_ratio("#000000", "#FFFFFF"), 21.0)


if __name__ == "__main__":
    unittest.main()
