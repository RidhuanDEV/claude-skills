import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import compat_deprecation_verifier as cdv


class CompatDeprecationVerifierTests(unittest.TestCase):
    def test_self_test_probes(self) -> None:
        report = cdv.run_self_test()
        self.assertTrue(report["all_passed"], report)
        self.assertEqual(report["total_probes"], 7)

    def test_invalid_sunset_format_rejected(self) -> None:
        violations = cdv.check_compat_spec({
            "deprecation": {
                "Deprecation": "@1767225600",
                "Sunset": "2026-12-31",  # Not IMF-fixdate!
                "Link": '<https://docs.example.com>; rel="deprecation"',
            }
        })
        codes = {v["code"] for v in violations}
        self.assertIn("INVALID_RFC8594_SUNSET", codes)


if __name__ == "__main__":
    unittest.main()
