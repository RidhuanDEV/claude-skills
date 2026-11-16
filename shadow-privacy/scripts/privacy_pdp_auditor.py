#!/usr/bin/env python3
"""
Shadow Privacy Auditor (privacy_pdp_auditor.py)

Deterministic static auditor and falsification probe runner grounded in
Indonesia UU No. 27 Tahun 2022 (UU PDP) and EU GDPR.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

SKIP_DIRS = {
    ".git", "node_modules", ".next", "dist", "build", "__pycache__",
    ".venv", "venv", "coverage", ".turbo",
}

SCAN_EXTENSIONS = {
    ".ts", ".tsx", ".js", ".jsx", ".py", ".go", ".java", ".kt",
    ".php", ".cs", ".rb", ".sql", ".yaml", ".yml", ".json", ".env",
}

# Valid 2-digit Kemendagri province prefixes for Indonesian 16-digit NIK
NIK_REGEX = re.compile(
    r"(?<![0-9a-fA-FxX-])(?:1[1-9]|21|3[1-6]|5[1-3]|6[1-5]|7[1-6]|8[1-2]|9[1-4])\d{14}(?![0-9a-fA-FxX-])"
)
NPWP_REGEX = re.compile(r"\b\d{2}\.\d{3}\.\d{3}\.\d-\d{3}\.\d{3}\b")

LOG_CALL_REGEX = re.compile(
    r"\b(?:console\.(?:log|info|warn|error|debug)|logger\.(?:info|warn|error|debug)|logging\.(?:info|warning|error|debug)|print|Log::(?:info|warning|error)|fmt\.Print(?:f|ln)?)\s*\(",
    re.IGNORECASE,
)

SENSITIVE_PII_FIELDS = re.compile(
    r"\b(?:nik|no_ktp|npwp|bpjs|rekam_medis|medical_record|diagnosis|biometric|fingerprint|face_embedding|genetic_data|nomor_rekening|bank_account|credit_card|card_number|mother_maiden_name)\b",
    re.IGNORECASE,
)

REDACTION_GUARDS = re.compile(
    r"\b(?:mask|redact|hash|sha256|hmac|encrypt|encrypted|anonymize|pseudonymize|token|last4|len\(|count\()\b|\*{3,}",
    re.IGNORECASE,
)

CREATE_TABLE_SPECIFIC_REGEX = re.compile(
    r"CREATE\s+TABLE\b[\s\S]{0,1200}?\b(?:rekam_medis|medical_record|diagnosis|biometric|fingerprint|genetic_data|criminal_record|nomor_rekening)\b",
    re.IGNORECASE,
)

ENCRYPTION_OR_HASH_COLUMN_HINT = re.compile(
    r"(?:_enc\b|_encrypted\b|_hash\b|ciphertext|kms_key_id|encrypted_|pgcrypto|pgp_sym_encrypt)",
    re.IGNORECASE,
)


def audit_text(content: str, source_name: str = "<snippet>") -> list[dict[str, Any]]:
    """Inspect source text or SQL DDL for UU PDP / GDPR technical violations."""
    findings: list[dict[str, Any]] = []
    lines = content.splitlines()

    for idx, line in enumerate(lines, start=1):
        stripped = line.strip()
        if not stripped:
            continue

        # 1. Unmasked 16-digit Indonesian NIK literal outside masked/encrypted tokens
        if NIK_REGEX.search(line) and not REDACTION_GUARDS.search(line):
            findings.append({
                "rule_id": "UU_PDP_PASAL_4_35_RAW_NIK",
                "severity": "HIGH",
                "law_ref": "UU PDP Pasal 4 Ayat (3) & Pasal 35 / GDPR Art. 32",
                "file": source_name,
                "line": idx,
                "message": "Potential unmasked 16-digit Indonesian NIK literal detected.",
                "remediation": "Mask (e.g. 3174********0001), tokenize, or encrypt NIK before storage/logging.",
            })

        # 2. Unmasked 15-digit Indonesian NPWP literal
        if NPWP_REGEX.search(line) and not REDACTION_GUARDS.search(line):
            findings.append({
                "rule_id": "UU_PDP_PASAL_4_35_RAW_NPWP",
                "severity": "HIGH",
                "law_ref": "UU PDP Pasal 4 Ayat (3) & Pasal 35",
                "file": source_name,
                "line": idx,
                "message": "Unmasked Indonesian NPWP literal detected.",
                "remediation": "Redact or encrypt NPWP values outside authorized tax payloads.",
            })

        # 3. Logging sensitive personal data without redaction/masking guard
        if LOG_CALL_REGEX.search(line) and SENSITIVE_PII_FIELDS.search(line) and not REDACTION_GUARDS.search(line):
            findings.append({
                "rule_id": "UU_PDP_PASAL_35_UNMASKED_PII_LOG",
                "severity": "HIGH",
                "law_ref": "UU PDP Pasal 35 & 39 / GDPR Art. 25 & 32",
                "file": source_name,
                "line": idx,
                "message": "Sensitive PII field referenced in log/print statement without masking or redaction.",
                "remediation": "Apply maskPii()/redact() or log only an opaque subject UUID.",
            })

    # 4. SQL DDL storing Specific Personal Data (Pasal 4 Ayat 2) without encryption/hash marker
    for match in CREATE_TABLE_SPECIFIC_REGEX.finditer(content):
        block = match.group(0)
        if not ENCRYPTION_OR_HASH_COLUMN_HINT.search(block):
            line_num = content[: match.start()].count("\n") + 1
            findings.append({
                "rule_id": "UU_PDP_PASAL_4_2_UNENCRYPTED_SPECIFIC_DATA",
                "severity": "MEDIUM",
                "law_ref": "UU PDP Pasal 4 Ayat (2), Pasal 34 & Pasal 35 / GDPR Art. 9 & 32",
                "file": source_name,
                "line": line_num,
                "message": "SQL schema defines Specific Personal Data column without explicit field-encryption/ciphertext suffix or KMS reference.",
                "remediation": "Store Specific Personal Data encrypted (e.g., *_enc BYTEA/TEXT + kms_key_id) and pair with DPIA + consent/retention columns.",
            })

    return findings


def scan_path(target: Path) -> dict[str, Any]:
    findings: list[dict[str, Any]] = []
    scanned_files = 0
    if target.is_file():
        files = [target]
    else:
        files = [
            p for p in target.rglob("*")
            if p.is_file()
            and p.suffix.lower() in SCAN_EXTENSIONS
            and not any(part in SKIP_DIRS for part in p.parts)
        ]

    for fpath in files:
        try:
            text = fpath.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        scanned_files += 1
        findings.extend(audit_text(text, str(fpath)))

    return {
        "target": str(target),
        "scanned_files": scanned_files,
        "finding_count": len(findings),
        "status": "PASS" if not findings else "FINDINGS_DETECTED",
        "findings": findings,
    }


def run_self_test() -> dict[str, Any]:
    """Execute >=5 precision probes and >=3 recall probes (Rule 22)."""
    precision_cases = [
        ("PRECISION-1: Masked NIK in log", 'logger.info("Verified user nik=%s", mask_nik("3174********0001"))'),
        ("PRECISION-2: Hex trace ID & UUID", 'logger.info("request_id=9f86d081884c7d659a2feaa0c55ad015 trace=1234abcd5678ef90")'),
        ("PRECISION-3: Encrypted specific data DDL", "CREATE TABLE patient_records (id UUID PRIMARY KEY, diagnosis_enc BYTEA NOT NULL, kms_key_id TEXT NOT NULL);"),
        ("PRECISION-4: Log only anonymized user_id & count", 'console.info("Exported kyc records", { userId: user.id, count: records.length });'),
        ("PRECISION-5: 13-digit epoch timestamp & valid non-NIK number", 'const eventTs = 1763265600123; const refCode = "9900112233445566";'),
    ]
    recall_cases = [
        ("RECALL-1: Raw 16-digit Indonesian NIK literal", 'const testNik = "3174051208950001";', "UU_PDP_PASAL_4_35_RAW_NIK"),
        ("RECALL-2: Unmasked medical/BPJS field in console.log", 'console.log("Patient data:", user.nik, user.rekam_medis);', "UU_PDP_PASAL_35_UNMASKED_PII_LOG"),
        ("RECALL-3: Unmasked NPWP literal", 'const taxpayer = "01.234.567.8-901.000";', "UU_PDP_PASAL_4_35_RAW_NPWP"),
        ("RECALL-4: SQL DDL with plaintext Specific Personal Data", "CREATE TABLE health_claims (id UUID PRIMARY KEY, diagnosis TEXT NOT NULL, biometric TEXT);", "UU_PDP_PASAL_4_2_UNENCRYPTED_SPECIFIC_DATA"),
    ]

    results: list[dict[str, Any]] = []
    for name, snippet in precision_cases:
        hits = audit_text(snippet, name)
        results.append({
            "probe": name,
            "passed": len(hits) == 0,
            "finding_count": len(hits),
        })
    for name, snippet, expected_rule in recall_cases:
        hits = audit_text(snippet, name)
        rule_ids = {h["rule_id"] for h in hits}
        results.append({
            "probe": name,
            "passed": expected_rule in rule_ids,
            "expected_rule": expected_rule,
            "matched_rules": sorted(rule_ids),
        })

    passed = sum(1 for r in results if r["passed"])
    return {
        "tool": "privacy_pdp_auditor.py",
        "total_probes": len(results),
        "passed": passed,
        "failed": len(results) - passed,
        "all_passed": passed == len(results),
        "results": results,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Shadow Privacy (UU PDP / GDPR) Static Auditor")
    parser.add_argument("--scan", default=None, help="File or directory path to scan")
    parser.add_argument("--self-test", action="store_true", help="Run precision & recall probes")
    args = parser.parse_args()

    if args.self_test:
        res = run_self_test()
        print(json.dumps(res, indent=2))
        return 0 if res["all_passed"] else 1

    if args.scan:
        res = scan_path(Path(args.scan))
        print(json.dumps(res, indent=2))
        return 0 if res["finding_count"] == 0 else 1

    parser.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
