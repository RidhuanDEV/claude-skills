from __future__ import annotations

import importlib.util
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "privacy_pdp_auditor.py"
_spec = importlib.util.spec_from_file_location("privacy_pdp_auditor", SCRIPT)
assert _spec is not None and _spec.loader is not None
auditor = importlib.util.module_from_spec(_spec)
sys.modules["privacy_pdp_auditor"] = auditor
_spec.loader.exec_module(auditor)


def rules(text: str) -> set[str]:
    return {finding["rule_id"] for finding in auditor.audit_text(text)}


class AuditTextTests(unittest.TestCase):
    def test_raw_nik_and_npwp_are_flagged(self) -> None:
        self.assertIn("UU_PDP_PASAL_4_35_RAW_NIK", rules('user = {"nik": "3174012345670001"}'))
        self.assertIn("UU_PDP_PASAL_4_35_RAW_NPWP", rules('npwp = "01.234.567.8-901.000"'))

    def test_masked_or_non_nik_numbers_are_not_flagged(self) -> None:
        for text in (
            'masked = mask("3174012345670001")',
            'display = "3174********0001"',
            "order_id = 9912345678901234",
            "trace = 0x3174012345670001",
            "amount = 1234567890123",
        ):
            with self.subTest(text=text):
                self.assertNotIn("UU_PDP_PASAL_4_35_RAW_NIK", rules(text))

    def test_logging_sensitive_fields_without_redaction(self) -> None:
        self.assertIn("UU_PDP_PASAL_35_UNMASKED_PII_LOG", rules("logger.info(f'user nik={user.nik}')"))
        self.assertIn("UU_PDP_PASAL_35_UNMASKED_PII_LOG", rules("console.log('diagnosis', patient.diagnosis)"))
        self.assertNotIn("UU_PDP_PASAL_35_UNMASKED_PII_LOG", rules("logger.info(f'nik={mask(user.nik)}')"))
        self.assertNotIn("UU_PDP_PASAL_35_UNMASKED_PII_LOG", rules("logger.info('order created')"))

    def test_specific_data_tables_need_an_encryption_marker(self) -> None:
        plain = "CREATE TABLE patients (id bigint, diagnosis text);"
        protected = "CREATE TABLE patients (id bigint, diagnosis_encrypted bytea, kms_key_id text);"
        self.assertIn("UU_PDP_PASAL_4_2_UNENCRYPTED_SPECIFIC_DATA", rules(plain))
        self.assertNotIn("UU_PDP_PASAL_4_2_UNENCRYPTED_SPECIFIC_DATA", rules(protected))
        self.assertEqual(rules("CREATE TABLE orders (id bigint, total numeric);"), set())


class ScanPathTests(unittest.TestCase):
    def test_scan_reports_findings_and_skips_vendor_folders(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "app.py").write_text('nik = "3174012345670001"\n', encoding="utf-8")
            (root / "node_modules").mkdir()
            (root / "node_modules" / "lib.js").write_text('const nik = "3174012345670002";\n', encoding="utf-8")
            report = auditor.scan_path(root)
            self.assertEqual((report["status"], report["scanned_files"], report["finding_count"]), ("FINDINGS_DETECTED", 1, 1))

    def test_clean_scan_passes_and_empty_scan_is_blocked(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.assertEqual(auditor.scan_path(root)["status"], "BLOCKED_NO_FILES_SCANNED")
            self.assertEqual(auditor.scan_path(root / "missing")["status"], "BLOCKED_NO_FILES_SCANNED")
            (root / "app.py").write_text("total = 1\n", encoding="utf-8")
            self.assertEqual(auditor.scan_path(root)["status"], "PASS")

    def test_cli_exit_follows_status(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            result = subprocess.run([sys.executable, "-B", str(SCRIPT), "--scan", tmp],
                                    capture_output=True, text=True, timeout=60, check=False)
        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)

    def test_self_test_passes(self) -> None:
        self.assertTrue(auditor.run_self_test()["all_passed"])


class ErasureGateTests(unittest.TestCase):
    def plan(self, receipts: dict[str, object]) -> dict[str, object]:
        return {"synthetic": True, "expected_stores": ["postgres", "search", "backup"], "receipts": receipts}

    def test_each_store_needs_its_own_evidence(self) -> None:
        result = auditor.assess_erasure(self.plan({
            "postgres": {"owner_decision_ref": "DPO-1", "action": "deleted", "verification_ref": "Q-1"},
            "search": {"owner_decision_ref": "DPO-1", "action": "invalidated"},
            "backup": {"owner_decision_ref": "DPO-1", "action": "retained", "retention_ref": "R-1", "review_date": "2027-01-01"},
        }))
        self.assertEqual(result["stores"], {
            "postgres": "RECEIPT_RECORDED", "search": "AWAITING_RECEIPT", "backup": "RETAINED_PENDING_REVIEW",
        })
        self.assertFalse(result["all_removal_receipts_present"])

    def test_missing_owner_decision_blocks_the_store(self) -> None:
        result = auditor.assess_erasure(self.plan({"postgres": {"action": "deleted", "verification_ref": "Q-1"}}))
        self.assertEqual(result["stores"]["postgres"], "NEEDS_RETENTION_DECISION")

    def test_complete_receipts_pass(self) -> None:
        done = {"owner_decision_ref": "DPO-1", "action": "deleted", "verification_ref": "Q"}
        result = auditor.assess_erasure(self.plan({"postgres": done, "search": done, "backup": done}))
        self.assertTrue(result["all_removal_receipts_present"])

    def test_malformed_plans_are_rejected(self) -> None:
        for plan in (
            {"synthetic": "true", "expected_stores": ["db"], "receipts": {}},
            {"synthetic": True, "expected_stores": [], "receipts": {}},
            {"synthetic": True, "expected_stores": ["db", "db"], "receipts": {}},
            {"synthetic": True, "expected_stores": ["db"], "receipts": {"other": {}}},
            {"synthetic": True, "expected_stores": ["db"], "receipts": {"db": "deleted"}},
        ):
            with self.subTest(plan=plan):
                with self.assertRaises(ValueError):
                    auditor.assess_erasure(plan)


if __name__ == "__main__":
    unittest.main()
