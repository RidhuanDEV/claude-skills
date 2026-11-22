from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import email_deliverability_verifier as em


class EmailDeliverabilityVerifierTests(unittest.TestCase):
    def test_self_test_probes(self) -> None:
        res = em.run_self_test()
        self.assertTrue(res["all_passed"], json.dumps(res, indent=2))

    def test_gmail_clip_limit_blocks_oversized_html(self) -> None:
        res = em.validate_email_artifact(
            {
                "subject": "Monthly Account Statement",
                "from": "billing@tx.example.com",
                "html": "<table>" + ("x" * 96_000) + "</table>",
                "text": "Your monthly account statement is ready in your dashboard.",
            }
        )
        self.assertFalse(res["passed"])
        self.assertTrue(any("GMAIL_CLIP_RISK" in e for e in res["errors"]))

    def test_unsigned_rfc8058_on_bulk_mail_rejected(self) -> None:
        res = em.validate_rfc8058_policy(
            {
                "category": "MARKETING_BULK",
                "headers": {
                    "List-Unsubscribe": "<https://example.com/u?t=1>",
                    "List-Unsubscribe-Post": "List-Unsubscribe=One-Click",
                },
                "dkim_signed_headers": ["from", "subject"],
            }
        )
        self.assertFalse(res["passed"])
        self.assertTrue(any("RFC8058_UNSIGNED_HEADERS" in e for e in res["errors"]))


if __name__ == "__main__":
    unittest.main()
