import hashlib
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from check_receipt import assess


class ReceiptTests(unittest.TestCase):
    def test_progressive_release_acceptance(self):
        with tempfile.TemporaryDirectory() as directory:
            artifact = Path(directory) / "release"
            artifact.write_bytes(b"3.2")
            receipt = dict(release="3.2", contract_ref="C4", sender="delivery", recipient="ops",
                           criteria="restore exercise", warranty_owner="support",
                           contract_sha256=hashlib.sha256(b"3.2").hexdigest())
            self.assertEqual(len(assess(artifact, receipt)["pending"]), 3)
            receipt.update(signed_receipt_ref="R1", operator_demo_ref="D1", access_receipt_ref="A1")
            self.assertEqual(assess(artifact, receipt)["status"], "READY_FOR_RECEIPT_REVIEW")
            artifact.write_bytes(b"3.1")
            self.assertIn("digest_mismatch", assess(artifact, receipt)["pending"])
