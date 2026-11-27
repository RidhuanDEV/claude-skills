from __future__ import annotations

import hashlib
import importlib.util
import json
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import ModuleType

SCRIPTS_DIR = Path(__file__).resolve().parents[1] / "scripts"


def _load(name: str) -> ModuleType:
    path = SCRIPTS_DIR / f"{name}.py"
    spec = importlib.util.spec_from_file_location(f"{name}_tenant_tests", path)
    if spec is None or spec.loader is None:
        raise ImportError(f"Cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


appsec = _load("appsec_control_verifier")
skill_gate = _load("third_party_skill_gate")

# OWASP ASVS 5.0.0: V8 is Authorization (8.2.2 = data-specific access / IDOR-BOLA); V4.1.1 is Content-Type.
TENANT_EXPORT_CONTROL = "ASVS-5.0 v5.0.0-8.2.2"


def _tenant_export_finding() -> dict[str, object]:
    return {
        "severity": "CRITICAL",
        "control_id": TENANT_EXPORT_CONTROL,
        "location": "src/routes/export.ts:42",
        "impact": "Caller from tenant t-alpha can export rows of tenant t-beta (cross-tenant IDOR).",
        "remediation": "Derive tenant_id from the server session and scope the export query by it.",
    }


def _report(**overrides: object) -> dict[str, object]:
    return {"unapproved_live_probing_executed": False, "findings": [_tenant_export_finding()], **overrides}


class TenantExportFindingReportTests(unittest.TestCase):
    def test_authorization_finding_with_asvs_v8_and_nist_ssdf_locators_passes(self) -> None:
        for control in (TENANT_EXPORT_CONTROL, "NIST-SSDF SP800-218 PW.7", "CWE-639"):
            with self.subTest(control=control):
                finding = {**_tenant_export_finding(), "control_id": control}
                self.assertEqual(appsec.check_finding_report(_report(findings=[finding])), {"check": "finding_report", "passed": True, "errors": []})

    def test_unversioned_or_missing_control_locator_fails(self) -> None:
        for control in ("V8.2.2", "ASVS 4.0.3 4.1.1", "", None, 822):
            with self.subTest(control=control):
                finding = {**_tenant_export_finding(), "control_id": control}
                self.assertFalse(appsec.check_finding_report(_report(findings=[finding]))["passed"])

    def test_live_probing_flag_must_be_a_real_false(self) -> None:
        self.assertTrue(appsec.check_finding_report(_report())["passed"])
        report = _report()
        del report["unapproved_live_probing_executed"]
        self.assertTrue(appsec.check_finding_report(report)["passed"])
        violation = appsec.check_finding_report(_report(unapproved_live_probing_executed=True))
        self.assertFalse(violation["passed"])
        self.assertTrue(any("SAFETY_VIOLATION" in e for e in violation["errors"]))
        for value in ("true", "false", "yes", 1, 0):
            with self.subTest(value=value):
                self.assertFalse(appsec.check_finding_report(_report(unapproved_live_probing_executed=value))["passed"])

    def test_empty_missing_or_wrong_type_findings_fail(self) -> None:
        for findings in ([], None, "finding", {"severity": "HIGH"}, ["not-an-object"]):
            with self.subTest(findings=findings):
                self.assertFalse(appsec.check_finding_report(_report(findings=findings))["passed"])
        self.assertFalse(appsec.check_finding_report({})["passed"])

    def test_invalid_severity_and_thin_fields_fail(self) -> None:
        for key, value in (("severity", "URGENT"), ("severity", None), ("location", "x"), ("impact", 12345), ("remediation", "")):
            with self.subTest(key=key, value=value):
                finding = {**_tenant_export_finding(), key: value}
                self.assertFalse(appsec.check_finding_report(_report(findings=[finding]))["passed"])


class SecurityHeaderAndSsrfGateTests(unittest.TestCase):
    HARDENED: dict[str, str] = {
        "Strict-Transport-Security": "max-age=31536000",
        "Content-Security-Policy": "default-src 'self'; object-src 'none'; frame-ancestors 'none'",
        "X-Content-Type-Options": "nosniff",
        "Referrer-Policy": "no-referrer",
    }

    def test_hardened_headers_pass(self) -> None:
        self.assertTrue(appsec.check_security_headers(self.HARDENED)["passed"])

    def test_weak_or_wrong_type_headers_fail(self) -> None:
        for key, value in (
            ("Strict-Transport-Security", "max-age=31535999"),
            ("Strict-Transport-Security", 31536000),
            ("X-Content-Type-Options", "true"),
            ("Content-Security-Policy", "default-src 'self'; object-src 'none'; frame-ancestors 'none'; script-src 'unsafe-eval'"),
        ):
            with self.subTest(key=key, value=value):
                self.assertFalse(appsec.check_security_headers({**self.HARDENED, key: value})["passed"])
        self.assertFalse(appsec.check_security_headers({})["passed"])
        wildcard = {**self.HARDENED, "Access-Control-Allow-Origin": "*", "Access-Control-Allow-Credentials": "true"}
        self.assertFalse(appsec.check_security_headers(wildcard)["passed"])

    def test_public_allowlisted_export_webhook_passes_and_internal_targets_fail(self) -> None:
        ok = appsec.check_ssrf_url("https://exports.partner.example/t-alpha", {"exports.partner.example"}, ["93.184.216.34"])
        self.assertTrue(ok["passed"], ok)
        for url, allowed, resolved in (
            ("http://exports.partner.example/t-alpha", {"exports.partner.example"}, []),
            ("https://exports.partner.example/t-alpha", {"other.example"}, []),
            ("https://exports.partner.example/t-alpha", None, ["10.0.0.5"]),
            ("https://", None, []),
            ("https://0177.0.0.1/", None, []),
        ):
            with self.subTest(url=url, allowed=allowed, resolved=resolved):
                self.assertFalse(appsec.check_ssrf_url(url, allowed, resolved)["passed"])


class ThirdPartyReceiptTests(unittest.TestCase):
    SNAPSHOT_SHA = "b" * 64

    def setUp(self) -> None:
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        self.root = Path(folder.name)
        now = datetime.now(timezone.utc)
        self.receipt: dict[str, object] = {
            "schema_version": 1,
            "policy": skill_gate.POLICY,
            "source_url": "https://fixtures.example/owner/skill",
            "source_commit": "a" * 40,
            "snapshot_sha256": self.SNAPSHOT_SHA,
            "verdict": "APPROVED",
            "gates": {f"G{i}": {"status": "PASS", "evidence": "Reviewed"} for i in range(7)},
            "target": {"host": "codex", "skills_root": str(self.root), "skill_name": "fixture-skill", "action": "install-new"},
            "approval": {
                "approved_by": "Fixture operator",
                "approved_at": now.isoformat(),
                "expires_at": (now + timedelta(minutes=10)).isoformat(),
            },
        }

    def _check(self, receipt: dict[str, object]) -> dict[str, object]:
        raw = json.dumps(receipt).encode("utf-8")
        return skill_gate.checked_receipt(raw, hashlib.sha256(raw).hexdigest(), self.SNAPSHOT_SHA, "fixture-skill", self.root)

    def test_exact_approved_receipt_passes(self) -> None:
        self.assertEqual(self._check(self.receipt)["source_commit"], "a" * 40)

    def test_string_flags_and_type_drift_are_blocked(self) -> None:
        gates = dict(self.receipt["gates"]) if isinstance(self.receipt["gates"], dict) else {}
        for key, value in (
            ("schema_version", "1"),
            ("schema_version", True),
            ("verdict", "approved"),
            ("verdict", "true"),
            ("snapshot_sha256", "c" * 64),
            ("source_url", "http://fixtures.example/owner/skill"),
            ("source_commit", "a" * 39),
            ("gates", {**gates, "G3": {"status": "true", "evidence": "Reviewed"}}),
            ("gates", {**gates, "G2": {"status": "NOT_APPLICABLE", "evidence": "   "}}),
        ):
            with self.subTest(key=key, value=value):
                with self.assertRaises(ValueError):
                    self._check({**self.receipt, key: value})

    def test_missing_keys_and_digest_mismatch_are_blocked(self) -> None:
        for key in ("gates", "target", "approval"):
            with self.subTest(key=key):
                receipt = dict(self.receipt)
                del receipt[key]
                with self.assertRaises(KeyError):
                    self._check(receipt)
        raw = json.dumps(self.receipt).encode("utf-8")
        with self.assertRaises(ValueError):
            skill_gate.checked_receipt(raw, "0" * 64, self.SNAPSHOT_SHA, "fixture-skill", self.root)
        with self.assertRaises(ValueError):
            skill_gate.checked_receipt(b"", hashlib.sha256(b"").hexdigest(), self.SNAPSHOT_SHA, "fixture-skill", self.root)

    def test_source_url_validation(self) -> None:
        self.assertTrue(skill_gate.valid_source_url("https://fixtures.example/owner/skill"))
        for value in ("", None, "https://fixtures.example/", "https://u:p@fixtures.example/x", "https://fixtures.example/x?y=1", 42):
            with self.subTest(value=value):
                self.assertFalse(skill_gate.valid_source_url(value))


if __name__ == "__main__":
    unittest.main()
