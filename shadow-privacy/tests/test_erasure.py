import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from privacy_pdp_auditor import assess_erasure


class ErasureTests(unittest.TestCase):
    def test_partial_and_missing_receipts(self):
        decision = {"owner_decision_ref": "privacy-review-1"}
        stores = ["cache", "index", "backup", "processor", "legacy"]
        result = assess_erasure({"synthetic": True, "expected_stores": stores, "receipts": {
            "cache": dict(decision, action="invalidated", verification_ref="read-miss"),
            "index": dict(decision, action="deleted", verification_ref="lookup-miss"),
            "backup": dict(decision, action="retained", retention_ref="hold-1", review_date="2027-01-01"),
            "processor": decision,
        }})
        self.assertFalse(result["all_removal_receipts_present"])
        self.assertEqual(list(result["stores"].values()), ["RECEIPT_RECORDED", "RECEIPT_RECORDED",
            "RETAINED_PENDING_REVIEW", "AWAITING_RECEIPT", "NEEDS_RETENTION_DECISION"])

    def test_empty_or_live_request(self):
        for synthetic in (True, False):
            with self.assertRaises(ValueError):
                assess_erasure({"synthetic": synthetic, "expected_stores": [], "receipts": {}})
