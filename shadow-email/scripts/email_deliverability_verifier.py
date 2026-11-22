#!/usr/bin/env python3
"""
Shadow Email Deterministic Deliverability & Safety Verifier (email_deliverability_verifier.py)

Offline L0/L1 validator for:
1. DNS Authentication records (SPF <= 10 DNS lookup limit, DMARC policy/alignment, DKIM key bit minimum)
2. RFC 8058 One-Click Unsubscribe applicability (mandatory + DKIM-signed on bulk marketing; warns/rejects forcing unsubscribe on security OTP/reset transactional mail)
3. Email template quality (Gmail <= 95KB clip safety cap, plain-text presence, no <svg>/data:image, no unresolved {{vars}}, no CRLF header injection)
4. Enhanced DSN bounce classification (5.x.x permanent suppress vs 5.7.x reputation alert vs 4.x.x bounded backoff)
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

SPF_LOOKUP_MECH_RE = re.compile(r"\b(?:include:|a(?::|/|\b)|mx(?::|/|\b)|ptr(?::|\b)|exists:|redirect=)", re.IGNORECASE)
CRLF_RE = re.compile(r"[\r\n]")
UNSUPPORTED_MEDIA_RE = re.compile(r"(?:data:image/|<svg[\s>])", re.IGNORECASE)
UNRESOLVED_VAR_RE = re.compile(r"\{\{[^}]+\}\}")


def validate_dns_auth(spec: dict[str, Any]) -> dict[str, Any]:
    errors: list[str] = []
    warnings: list[str] = []

    spf = str(spec.get("spf_record", "")).strip()
    if not spf.lower().startswith("v=spf1"):
        errors.append("SPF_MISSING: spf_record must start with 'v=spf1'")
    else:
        lookups = len(SPF_LOOKUP_MECH_RE.findall(spf))
        if lookups > 10:
            errors.append(f"SPF_DNS_LOOKUP_EXCEEDED: {lookups} DNS lookup mechanisms (RFC 7208 hard limit is 10)")
        if "+all" in spf.lower():
            errors.append("SPF_OPEN_PLUS_ALL: '+all' authorizes the entire internet to spoof your domain")

    dkim_bits = int(spec.get("dkim_key_bits", 0))
    if dkim_bits < 1024:
        errors.append(f"DKIM_KEY_TOO_WEAK: dkim_key_bits={dkim_bits} (minimum 1024, recommended 2048)")
    elif dkim_bits < 2048:
        warnings.append("DKIM_KEY_1024_LEGACY: upgrade DKIM key to 2048 bits")

    dmarc = str(spec.get("dmarc_record", "")).strip()
    if not dmarc.lower().startswith("v=dmarc1"):
        errors.append("DMARC_MISSING: dmarc_record must start with 'v=DMARC1'")
    else:
        if not re.search(r"\bp=(?:none|quarantine|reject)\b", dmarc, re.IGNORECASE):
            errors.append("DMARC_POLICY_MISSING: dmarc_record must declare p=none|quarantine|reject")
        if "rua=" not in dmarc.lower():
            warnings.append("DMARC_RUA_MISSING: configure rua=mailto:... to receive aggregate authentication reports")

    from_domain = str(spec.get("from_domain", "")).strip().lower()
    dkim_domain = str(spec.get("dkim_domain", "")).strip().lower()
    spf_domain = str(spec.get("return_path_domain", "")).strip().lower()
    if from_domain:
        dkim_aligned = bool(dkim_domain) and (dkim_domain == from_domain or dkim_domain.endswith("." + from_domain))
        spf_aligned = bool(spf_domain) and (spf_domain == from_domain or spf_domain.endswith("." + from_domain))
        if not (dkim_aligned or spf_aligned):
            errors.append(
                f"DMARC_ALIGNMENT_FAILED: neither DKIM ({dkim_domain}) nor SPF Return-Path ({spf_domain}) aligns with From ({from_domain})"
            )

    return {"errors": errors, "warnings": warnings, "passed": len(errors) == 0}


def validate_rfc8058_policy(message: dict[str, Any]) -> dict[str, Any]:
    """Enforce RFC 8058 contextually: mandatory on marketing/subscribed bulk mail, NOT on OTP/security transactional mail."""
    errors: list[str] = []
    warnings: list[str] = []
    category = str(message.get("category", "")).upper()  # MARKETING_BULK | SUBSCRIBED_DIGEST | TRANSACTIONAL_SECURITY | TRANSACTIONAL_RECEIPT
    headers = {str(k).lower(): str(v) for k, v in (message.get("headers") or {}).items()}
    dkim_signed = {str(h).lower() for h in (message.get("dkim_signed_headers") or [])}

    has_unsub = "list-unsubscribe" in headers
    has_unsub_post = headers.get("list-unsubscribe-post", "").strip() == "List-Unsubscribe=One-Click"

    if category in {"MARKETING_BULK", "SUBSCRIBED_DIGEST"}:
        if not has_unsub or not headers["list-unsubscribe"].startswith("<https://"):
            errors.append("RFC8058_MISSING_HTTPS_URL: bulk/subscribed mail requires List-Unsubscribe: <https://...>")
        if not has_unsub_post:
            errors.append("RFC8058_MISSING_POST_HEADER: bulk/subscribed mail requires List-Unsubscribe-Post: List-Unsubscribe=One-Click")
        if "list-unsubscribe" not in dkim_signed or "list-unsubscribe-post" not in dkim_signed:
            errors.append("RFC8058_UNSIGNED_HEADERS: both List-Unsubscribe and List-Unsubscribe-Post MUST be DKIM-signed")
        if bool(message.get("unsubscribe_requires_login", False)):
            errors.append("RFC8058_LOGIN_REQUIRED: one-click POST endpoint MUST work without cookies or login")
    elif category == "TRANSACTIONAL_SECURITY":
        if has_unsub or has_unsub_post:
            errors.append(
                "SECURITY_MAIL_UNSUBSCRIBE_ERROR: Do NOT attach one-click unsubscribe to OTP/password-reset/security alerts"
            )
    else:
        if has_unsub and not has_unsub_post:
            warnings.append("PARTIAL_UNSUBSCRIBE_HEADER: if adding List-Unsubscribe, pair with RFC 8058 List-Unsubscribe-Post")

    return {"category": category, "errors": errors, "warnings": warnings, "passed": len(errors) == 0}


def validate_email_artifact(artifact: dict[str, Any]) -> dict[str, Any]:
    errors: list[str] = []
    subject = str(artifact.get("subject", ""))
    from_hdr = str(artifact.get("from", ""))
    reply_to = str(artifact.get("reply_to", ""))
    html = str(artifact.get("html", ""))
    text = str(artifact.get("text", ""))

    for field_name, val in (("subject", subject), ("from", from_hdr), ("reply_to", reply_to)):
        if CRLF_RE.search(val):
            errors.append(f"HEADER_INJECTION_CRLF: forbidden CR/LF detected in '{field_name}'")

    html_bytes = len(html.encode("utf-8"))
    if html_bytes > 95_000:
        errors.append(f"GMAIL_CLIP_RISK: HTML is {html_bytes} bytes (> 95,000 byte safety ceiling below Gmail 102KB clip)")
    if len(text.strip()) < 20:
        errors.append("MISSING_PLAIN_TEXT: multipart/alternative requires a meaningful text/plain version")
    if UNSUPPORTED_MEDIA_RE.search(html):
        errors.append("UNSUPPORTED_EMAIL_MEDIA: replace <svg> or data:image base64 with hosted HTTPS PNG")
    if UNRESOLVED_VAR_RE.search(html) or UNRESOLVED_VAR_RE.search(text) or UNRESOLVED_VAR_RE.search(subject):
        errors.append("UNRESOLVED_TEMPLATE_VAR: raw {{placeholder}} leaked into compiled message")

    return {"html_bytes": html_bytes, "errors": errors, "passed": len(errors) == 0}


def classify_dsn_bounce(dsn_code: str, event_type: str = "BOUNCE") -> dict[str, Any]:
    etype = event_type.upper()
    code = dsn_code.strip()
    if etype == "COMPLAINT":
        return {"dsn_code": code, "disposition": "SUPPRESS_PERMANENT", "retry": False, "alert": True}
    if code.startswith("5.7."):
        return {"dsn_code": code, "disposition": "ALERT_REPUTATION_POLICY", "retry": False, "alert": True}
    if code.startswith("5."):
        return {"dsn_code": code, "disposition": "SUPPRESS_PERMANENT", "retry": False, "alert": False}
    if code.startswith("4."):
        return {"dsn_code": code, "disposition": "RETRY_BOUNDED_BACKOFF", "retry": True, "alert": False}
    return {"dsn_code": code, "disposition": "RETRY_BOUNDED_BACKOFF", "retry": True, "alert": False}


def run_self_test() -> dict[str, Any]:
    good_dns = validate_dns_auth(
        {
            "spf_record": "v=spf1 include:amazonses.com -all",
            "dkim_key_bits": 2048,
            "dmarc_record": "v=DMARC1; p=quarantine; pct=100; adkim=s; aspf=s; rua=mailto:dmarc@example.com",
            "from_domain": "tx.example.com",
            "dkim_domain": "tx.example.com",
            "return_path_domain": "bounces.tx.example.com",
        }
    )
    bad_spf = validate_dns_auth(
        {
            "spf_record": "v=spf1 " + " ".join(f"include:s{i}.example.net" for i in range(11)) + " ~all",
            "dkim_key_bits": 2048,
            "dmarc_record": "v=DMARC1; p=none; rua=mailto:d@example.com",
            "from_domain": "example.com",
            "dkim_domain": "unrelated-esp.net",
            "return_path_domain": "unrelated-esp.net",
        }
    )
    good_mkt = validate_rfc8058_policy(
        {
            "category": "MARKETING_BULK",
            "headers": {
                "List-Unsubscribe": "<https://example.com/unsub?t=abc>",
                "List-Unsubscribe-Post": "List-Unsubscribe=One-Click",
            },
            "dkim_signed_headers": ["from", "subject", "list-unsubscribe", "list-unsubscribe-post"],
            "unsubscribe_requires_login": False,
        }
    )
    bad_otp = validate_rfc8058_policy(
        {
            "category": "TRANSACTIONAL_SECURITY",
            "headers": {"List-Unsubscribe": "<https://example.com/unsub?t=abc>"},
            "dkim_signed_headers": ["list-unsubscribe"],
        }
    )
    good_otp = validate_rfc8058_policy({"category": "TRANSACTIONAL_SECURITY", "headers": {}, "dkim_signed_headers": ["from", "subject"]})
    bad_crlf = validate_email_artifact(
        {
            "subject": "Reset Password\r\nBcc: attacker@evil.test",
            "from": "no-reply@tx.example.com",
            "html": "<table><tr><td><svg></svg>{{OTP}}</td></tr></table>",
            "text": "short",
        }
    )
    b511 = classify_dsn_bounce("5.1.1", "BOUNCE")
    b571 = classify_dsn_bounce("5.7.1", "BOUNCE")
    b422 = classify_dsn_bounce("4.2.2", "BOUNCE")

    probes = [
        ("PRECISION-1: Aligned SPF/2048-DKIM/DMARC passes", good_dns["passed"]),
        ("RECALL-1: SPF >10 lookups & DMARC misalignment rejected", not bad_spf["passed"] and len(bad_spf["errors"]) >= 2),
        ("PRECISION-2: DKIM-signed RFC 8058 on MARKETING_BULK passes", good_mkt["passed"]),
        ("PRECISION-3: TRANSACTIONAL_SECURITY without unsubscribe passes", good_otp["passed"]),
        ("RECALL-2: Forcing List-Unsubscribe onto OTP security mail rejected", not bad_otp["passed"]),
        ("RECALL-3: CRLF header injection, <svg>, {{var}} & missing text caught", not bad_crlf["passed"] and len(bad_crlf["errors"]) == 4),
        ("RECALL-4: DSN 5.1.1 suppress, 5.7.1 reputation alert, 4.2.2 retry", b511["disposition"] == "SUPPRESS_PERMANENT" and b571["disposition"] == "ALERT_REPUTATION_POLICY" and b422["retry"] is True),
    ]
    results = [{"probe": name, "passed": ok} for name, ok in probes]
    passed = sum(1 for r in results if r["passed"])
    return {
        "tool": "email_deliverability_verifier.py",
        "total_probes": len(results),
        "passed": passed,
        "failed": len(results) - passed,
        "all_passed": passed == len(results),
        "results": results,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Shadow Email Offline Deliverability & Safety Verifier")
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument("--check-dns", default=None)
    parser.add_argument("--check-rfc8058", default=None)
    parser.add_argument("--check-artifact", default=None)
    parser.add_argument("--classify-dsn", default=None)
    args = parser.parse_args()

    if args.self_test:
        res = run_self_test()
        print(json.dumps(res, indent=2))
        return 0 if res["all_passed"] else 1
    if args.check_dns:
        res = validate_dns_auth(json.loads(Path(args.check_dns).read_text(encoding="utf-8-sig")))
        print(json.dumps(res, indent=2))
        return 0 if res["passed"] else 1
    if args.check_rfc8058:
        res = validate_rfc8058_policy(json.loads(Path(args.check_rfc8058).read_text(encoding="utf-8-sig")))
        print(json.dumps(res, indent=2))
        return 0 if res["passed"] else 1
    if args.check_artifact:
        res = validate_email_artifact(json.loads(Path(args.check_artifact).read_text(encoding="utf-8-sig")))
        print(json.dumps(res, indent=2))
        return 0 if res["passed"] else 1
    if args.classify_dsn:
        print(json.dumps(classify_dsn_bounce(args.classify_dsn), indent=2))
        return 0

    parser.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
