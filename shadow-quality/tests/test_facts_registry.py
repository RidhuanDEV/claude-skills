from __future__ import annotations

from datetime import date
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "facts_registry_check.py"
_spec = importlib.util.spec_from_file_location("facts_registry_check", SCRIPT)
assert _spec is not None and _spec.loader is not None
checker = importlib.util.module_from_spec(_spec)
sys.modules["facts_registry_check"] = checker
_spec.loader.exec_module(checker)

FACTS, PROBLEMS = checker.load_registry(ROOT)
BY_ID = {fact.id: fact for fact in FACTS}

# fact id -> (lines that must be flagged as stale, lines that must not be flagged)
PROBES: dict[str, tuple[tuple[str, ...], tuple[str, ...]]] = {
    "OWASP-LLM-TOP10": (
        ("OWASP Top 10 for LLM Applications 2025 - LLM01", "red-teaming per OWASP LLM 2025", "OWASP Top 10 for LLM 2025 / NIST"),
        ("OWASP Top 10 for LLM Applications 2026: LLM03 Excessive Agency", "LLM06 (2025 numbering) maps to LLM03 in 2026",
         "OWASP LLM 2025 edition (superseded by 2026)", "NIST AI 600-1 (2024)", "OWASP Top 10:2025 A03"),
    ),
    "DMARC-RFC": (
        ("IETF RFC 7489 - DMARC", "v=DMARC1; p=quarantine; pct=100"),
        ("RFC 9989 obsoletes RFC 7489", "RFC 7489 (obsolete)", "v=DMARC1; p=reject; adkim=s", "percent=100 of traffic"),
    ),
    "OAUTH-2-1": (
        ("Enforce OAuth 2.1 + PKCE auth", "Recommended OAuth 2.1 / OIDC Architecture"),
        ("OAuth 2.1 (draft-ietf-oauth-v2-1, not an RFC) and RFC 9700", "OAuth 2.0 with RFC 9700 BCP", "OAuth 2.1 draft"),
    ),
    "PLAY-TARGET-API": (
        ("targetSdk = 35", "targetSdkVersion 35"),
        ("targetSdk = 36", "targetSdk 35 is the minimum for existing apps to stay visible", "compileSdk = 35"),
    ),
    "WCAG-LARGE-TEXT": (
        ("Large text (18px+): minimum contrast ratio of 3:1", "3:1 for large text (18px+)"),
        ("large text (24px, or 18.66px bold)", "font-size: 18px", "18px bold heading", "large text 18pt (24px)"),
    ),
    "MCP-SPEC": (
        ("pipe a valid JSON-RPC `initialize` request",),
        ("for 2025-11-25 servers, send an initialize request", "call server/discover", "initialize the database"),
    ),
    "GMAIL-POSTMASTER": (
        ("Verify Postmaster Domain & IP Reputation = Medium/High",),
        ("Postmaster v1 domain reputation dashboards were retired", "Postmaster Tools v2 Compliance Status"),
    ),
    "SBOM-PROVENANCE-VERSIONS": (
        ("CycloneDX 1.5 / SPDX SBOM provenance standards", "SLSA v1.0 provenance"),
        ("CycloneDX 1.5+ (1.7 current)", "SLSA v1.0/v1.2 provenance", "CycloneDX 1.7", "SLSA v1.2 Source Track"),
    ),
    "OWASP-ASVS": (
        ("Map findings to ASVS 4.0.3", "ASVS-5.0-V4.1.1 authorization"),
        ("ASVS 5.0.0 v5.0.0-8.2.2", "WRONG: mixing ASVS 4.0 and 5.0 chapters", "MASVS v2.1.0"),
    ),
    "WEBAUTHN": (("Implement WebAuthn Level 2 ceremonies",), ("WebAuthn Level 3 Recommendation", "WebAuthn Level 2 (superseded by Level 3)")),
    "NIST-SSDF": (("Comply with SSDF v1.2 practices",), ("SSDF v1.1 final; SSDF v1.2 draft", "SSDF v1.1 PO.1")),
    "SVGO-VERSION": (("Run SVGO v3 with preset-default",), ("SVGO v4 preset-default", "migrating from SVGO v3 -> v4")),
    "RFC-9457": (("errors follow RFC 7807",), ("RFC 9457 (obsoletes RFC 7807)", "RFC 9457 problem details")),
    "OWASP-WEB-TOP10": (("OWASP Top 10: 2021 A01",), ("OWASP Top 10:2025 A01", "OWASP Top 10 2021 -> 2025 mapping")),
}


def flagged(fact_id: str, line: str) -> bool:
    fact = BY_ID[fact_id]
    return any(pattern.search(line) for pattern in fact.patterns) and not (fact.allow and fact.allow.search(line))


class RegistrySchemaTests(unittest.TestCase):
    def test_registry_parses_without_problems(self) -> None:
        self.assertEqual(PROBLEMS, [])
        self.assertGreaterEqual(len(FACTS), 15)

    def test_every_fact_with_stale_patterns_has_probes(self) -> None:
        with_patterns = {fact.id for fact in FACTS if fact.patterns}
        self.assertEqual(with_patterns - set(PROBES), set())

    def test_overdue_review_fails(self) -> None:
        report = checker.check(ROOT, date(2099, 1, 1))
        self.assertIn("OVERDUE_REVIEW", {finding["kind"] for finding in report["findings"]})

    def test_malformed_registry_entries_are_rejected(self) -> None:
        base = {"id": "X", "statement": "s", "value": "v", "source_url": "https://example.org", "publisher": "p",
                "verified_on": "2026-11-26", "review_by": "2027-01-01", "stale_patterns": []}
        bad_entries = (
            {**base, "review_by": "2026-01-01"},
            {**base, "source_url": "http://example.org"},
            {**base, "stale_patterns": "RFC"},
            {**base, "stale_patterns": ["("]},
            {**base, "required_in": ["shadow-eval"]},
            {key: value for key, value in base.items() if key != "statement"},
        )
        for entry in bad_entries:
            with self.subTest(entry=entry):
                fact, problem = checker._parse_fact(entry, set())
                self.assertIsNone(fact)
                self.assertIsNotNone(problem)
        _, duplicate = checker._parse_fact(base, {"X"})
        self.assertEqual(duplicate.kind, "DUPLICATE_ID")


class StalePatternProbeTests(unittest.TestCase):
    def test_recall_probes_are_flagged(self) -> None:
        for fact_id, (must_flag, _) in PROBES.items():
            for line in must_flag:
                with self.subTest(fact=fact_id, line=line):
                    self.assertTrue(flagged(fact_id, line))

    def test_precision_probes_are_not_flagged(self) -> None:
        for fact_id, (_, must_not) in PROBES.items():
            for line in must_not:
                with self.subTest(fact=fact_id, line=line):
                    self.assertFalse(flagged(fact_id, line))


class ScanTests(unittest.TestCase):
    def test_scan_skips_vendored_upstream_text(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            (repo / "shadow-monarch" / "reference").mkdir(parents=True)
            (repo / checker.REGISTRY).write_text((ROOT / checker.REGISTRY).read_text(encoding="utf-8"), encoding="utf-8")
            (repo / "skill-a" / "references" / "vendor").mkdir(parents=True)
            (repo / "skill-a" / "SKILL.md").write_text("Errors follow RFC 7807.\n", encoding="utf-8")
            (repo / "skill-a" / "references" / "vendor" / "UPSTREAM.md").write_text("RFC 7807 upstream text\n", encoding="utf-8")
            report = checker.check(repo, date(2026, 11, 27))
            stale = [f for f in report["findings"] if f["kind"] == "STALE_FACT"]
            self.assertEqual([(f["fact"], f["path"]) for f in stale], [("RFC-9457", "skill-a/SKILL.md")])
            self.assertTrue(report["skipped_vendored"])


if __name__ == "__main__":
    unittest.main()
