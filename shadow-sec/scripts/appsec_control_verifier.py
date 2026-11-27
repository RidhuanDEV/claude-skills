#!/usr/bin/env python3
"""Deterministic AppSec Headers, SSRF Egress Guard & Finding Schema Verifier (L0/L1 offline CLI).

Zero third-party dependencies (Python 3 stdlib only, zero outbound network calls).
Validates:
  - Browser security headers: HSTS, strict CSP, CORS credentials safety, nosniff (--check-security-headers)
  - Offline SSRF URL & IP/decimal/hex/IPv6 bypass guard checks (--check-ssrf-url)
  - Actionable security finding schema & versioned OWASP ASVS / NIST SSDF locators (--check-finding-report)
  - Built-in precision & recall self-test probes (--self-test)
"""

from __future__ import annotations

import argparse
import ipaddress
import json
import re
import sys
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

VALID_SEVERITIES = {"CRITICAL", "HIGH", "MEDIUM", "LOW", "INFO"}
CONTROL_ID_RE = re.compile(r"(?:ASVS[- ]?5\.0|v5\.0\.0-\d+\.\d+\.\d+|NIST[- ]?SSDF|SP\s*800-218|CWE-\d+|UNVERIFIED)", re.IGNORECASE)


def check_security_headers(headers: dict[str, Any]) -> dict[str, Any]:
    errors: list[str] = []
    warnings: list[str] = []
    lower = {str(k).strip().lower(): str(v).strip() for k, v in headers.items()}

    hsts = lower.get("strict-transport-security", "")
    m_age = re.search(r"max-age=(\d+)", hsts, re.IGNORECASE)
    if not m_age or int(m_age.group(1)) < 31536000:
        errors.append("Strict-Transport-Security missing or max-age < 31536000 (1 year).")

    if lower.get("x-content-type-options", "").lower() != "nosniff":
        errors.append("Missing 'X-Content-Type-Options: nosniff'.")

    csp = lower.get("content-security-policy", "")
    if not csp:
        errors.append("Missing 'Content-Security-Policy' header.")
    else:
        if "object-src 'none'" not in csp.lower():
            errors.append("CSP must include \"object-src 'none'\".")
        if "frame-ancestors" not in csp.lower():
            errors.append("CSP must include 'frame-ancestors' directive (clickjacking defense).")
        if "'unsafe-eval'" in csp.lower():
            errors.append("CSP must not permit 'unsafe-eval'.")
        if re.search(r"script-src[^;]*\s\*", csp, re.IGNORECASE):
            errors.append("CSP 'script-src' must not allow wildcard '*'.")

    acao = lower.get("access-control-allow-origin", "")
    acac = lower.get("access-control-allow-credentials", "").lower()
    if acao == "*" and acac == "true":
        errors.append("CRITICAL CORS misconfiguration: Access-Control-Allow-Origin '*' cannot be combined with Allow-Credentials: true.")
    if acao and acao != "*" and "origin" not in lower.get("vary", "").lower():
        warnings.append("Dynamic/specific Access-Control-Allow-Origin should emit 'Vary: Origin' to prevent cache poisoning.")

    if not lower.get("referrer-policy"):
        warnings.append("Set 'Referrer-Policy: strict-origin-when-cross-origin' (or stricter).")

    return {"check": "security_headers", "passed": len(errors) == 0, "errors": errors, "warnings": warnings}


def _parse_numeric_ipv4(host: str) -> ipaddress.IPv4Address | None:
    """Detect obfuscated integer/hex/octal IPv4 literals (e.g., 2130706433, 0x7f000001, 0177.0.0.1)."""
    clean = host.strip()
    if re.fullmatch(r"\d+", clean):
        val = int(clean, 10)
        if 0 <= val <= 0xFFFFFFFF:
            return ipaddress.IPv4Address(val)
    if re.fullmatch(r"0x[0-9a-fA-F]+", clean):
        val = int(clean, 16)
        if 0 <= val <= 0xFFFFFFFF:
            return ipaddress.IPv4Address(val)
    parts = clean.split(".")
    if len(parts) == 4 and all(re.fullmatch(r"(?:0x[0-9a-fA-F]+|0[0-7]+|\d+)", p) for p in parts):
        try:
            octets = [int(p, 16) if p.lower().startswith("0x") else int(p, 8) if len(p) > 1 and p.startswith("0") else int(p) for p in parts]
            if all(0 <= o <= 255 for o in octets):
                return ipaddress.IPv4Address(bytes(octets))
        except ValueError:
            return None
    return None


def _is_forbidden_ip_obj(ip_obj: ipaddress.IPv4Address | ipaddress.IPv6Address) -> bool:
    if isinstance(ip_obj, ipaddress.IPv6Address) and ip_obj.ipv4_mapped is not None:
        ip_obj = ip_obj.ipv4_mapped
    # Covers loopback, private (10/8, 172.16/12, 192.168/16, fc00::/7), link-local (169.254/16, fe80::/10),
    # unspecified, multicast, reserved, and CGNAT 100.64.0.0/10
    if isinstance(ip_obj, ipaddress.IPv4Address):
        cgnat = ipaddress.IPv4Network("100.64.0.0/10")
        if ip_obj in cgnat:
            return True
    return not ip_obj.is_global


def check_ssrf_url(
    raw_url: str,
    allowed_hosts: set[str] | None = None,
    resolved_ips: list[str] | None = None,
) -> dict[str, Any]:
    """Pure offline SSRF validator (inspects scheme, host obfuscation, allowlist, and supplied DNS IPs)."""
    errors: list[str] = []
    parsed = urlparse(raw_url.strip())

    if parsed.scheme.lower() != "https":
        errors.append(f"SSRF_BLOCKED_SCHEME: Only 'https' allowed (got '{parsed.scheme}').")

    if parsed.username or parsed.password:
        errors.append("SSRF_BLOCKED_USERINFO: Embedded credentials '@' in URL are forbidden.")

    host = (parsed.hostname or "").strip().lower()
    if not host:
        errors.append("SSRF_EMPTY_HOST: URL missing valid hostname.")
        return {"check": "ssrf_url", "url": raw_url, "passed": False, "errors": errors}

    if host in {"localhost", "localhost.localdomain", "metadata.google.internal"} or host.endswith(".internal") or host.endswith(".local"):
        errors.append(f"SSRF_FORBIDDEN_HOSTNAME: Internal/metadata host '{host}' blocked.")

    # Direct IP literal or obfuscated numeric IP check
    ip_obj: ipaddress.IPv4Address | ipaddress.IPv6Address | None = None
    try:
        ip_obj = ipaddress.ip_address(host)
    except ValueError:
        ip_obj = _parse_numeric_ipv4(host)

    if ip_obj is not None:
        if _is_forbidden_ip_obj(ip_obj):
            errors.append(f"SSRF_FORBIDDEN_IP_LITERAL: Non-public IP '{ip_obj}' blocked.")
        elif allowed_hosts is not None and host not in allowed_hosts:
            errors.append(f"SSRF_IP_NOT_ALLOWLISTED: Direct IP '{host}' not in explicit host allowlist.")
    elif allowed_hosts is not None and host not in allowed_hosts:
        errors.append(f"SSRF_HOST_NOT_ALLOWED: Host '{host}' not in configured allowlist.")

    # Check simulated/captured DNS A/AAAA resolution records
    for raw_ip in resolved_ips or []:
        try:
            rec_ip = ipaddress.ip_address(raw_ip.strip())
            if _is_forbidden_ip_obj(rec_ip):
                errors.append(f"SSRF_DNS_RESOLVED_FORBIDDEN_IP: Host resolved to non-public IP '{rec_ip}'.")
        except ValueError:
            errors.append(f"SSRF_INVALID_RESOLVED_IP: Unparseable resolved IP '{raw_ip}'.")

    return {"check": "ssrf_url", "url": raw_url, "passed": len(errors) == 0, "errors": errors}


def check_finding_report(report: dict[str, Any]) -> dict[str, Any]:
    errors: list[str] = []
    live_probing = report.get("unapproved_live_probing_executed")
    if live_probing is True:
        errors.append("SAFETY_VIOLATION: Active live security probing/fuzzing executed without explicit L3/L4 approval.")
    elif live_probing is not None and live_probing is not False:
        errors.append("'unapproved_live_probing_executed' must be a JSON boolean.")

    findings = report.get("findings", [])
    if not isinstance(findings, list) or len(findings) == 0:
        errors.append("Security report must include >= 1 structured finding.")
        return {"check": "finding_report", "passed": False, "errors": errors}

    for idx, f in enumerate(findings):
        if not isinstance(f, dict):
            errors.append(f"Finding #{idx} must be an object.")
            continue
        sev = str(f.get("severity", "")).upper()
        if sev not in VALID_SEVERITIES:
            errors.append(f"Finding #{idx}: invalid severity '{sev}'.")
        ctrl = str(f.get("control_id", ""))
        if not CONTROL_ID_RE.search(ctrl):
            errors.append(f"Finding #{idx}: missing versioned control locator (ASVS 5.0 / NIST SSDF / CWE / UNVERIFIED).")
        for req in ("location", "impact", "remediation"):
            if not isinstance(f.get(req), str) or len(str(f.get(req)).strip()) < 5:
                errors.append(f"Finding #{idx}: missing substantive '{req}'.")

    return {"check": "finding_report", "passed": len(errors) == 0, "errors": errors}


def run_self_test() -> dict[str, Any]:
    probes: list[tuple[str, bool]] = []

    # PRECISION-1: Hardened HSTS + nonce CSP + exact CORS + Vary passes
    r1 = check_security_headers(
        {
            "Strict-Transport-Security": "max-age=31536000; includeSubDomains",
            "Content-Security-Policy": "default-src 'self'; script-src 'self' 'nonce-abc123'; object-src 'none'; frame-ancestors 'none'",
            "X-Content-Type-Options": "nosniff",
            "Referrer-Policy": "strict-origin-when-cross-origin",
            "Access-Control-Allow-Origin": "https://app.example.com",
            "Vary": "Origin",
        }
    )
    probes.append(("PRECISION-1: Hardened HSTS, nonce CSP & allowlisted CORS pass", r1["passed"] is True))

    # RECALL-1: Wildcard CORS+credentials, unsafe-eval, weak HSTS rejected
    r2 = check_security_headers(
        {
            "Strict-Transport-Security": "max-age=300",
            "Content-Security-Policy": "script-src * 'unsafe-eval'",
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Credentials": "true",
        }
    )
    probes.append(("RECALL-1: Wildcard CORS+credentials, unsafe-eval & weak HSTS rejected", r2["passed"] is False and len(r2["errors"]) >= 5))

    # PRECISION-2: Allowlisted HTTPS host resolving to public IP passes
    r3 = check_ssrf_url(
        "https://webhooks.partner.example/hooks",
        allowed_hosts={"webhooks.partner.example"},
        resolved_ips=["93.184.216.34"],
    )
    probes.append(("PRECISION-2: Allowlisted HTTPS webhook resolving to public IP passes", r3["passed"] is True))

    # RECALL-2: AWS metadata 169.254.169.254 & decimal loopback 2130706433 blocked
    r4a = check_ssrf_url("http://169.254.169.254/latest/meta-data/")
    r4b = check_ssrf_url("https://2130706433/admin")
    probes.append(("RECALL-2: Cloud metadata 169.254.169.254 & decimal loopback 2130706433 blocked", not r4a["passed"] and not r4b["passed"]))

    # RECALL-3: IPv6 loopback [::1] & IPv4-mapped IPv6 DNS rebinding blocked
    r5a = check_ssrf_url("https://[::1]/internal")
    r5b = check_ssrf_url(
        "https://rebind.partner.example/hook",
        allowed_hosts={"rebind.partner.example"},
        resolved_ips=["::ffff:169.254.169.254"],
    )
    probes.append(("RECALL-3: IPv6 [::1] and IPv4-mapped metadata DNS resolution blocked", not r5a["passed"] and not r5b["passed"]))

    # PRECISION-3: Structured ASVS 5.0 finding report without live probing passes
    r6 = check_finding_report(
        {
            "unapproved_live_probing_executed": False,
            "findings": [
                {
                    "severity": "CRITICAL",
                    "control_id": "ASVS-5.0 v5.0.0-8.2.1",
                    "location": "src/routes/internal-export.ts:42",
                    "impact": "Unauthenticated internal endpoint exposed in frontend JS bundle leaks tenant rows.",
                    "remediation": "Require server-side AuthN/AuthZ middleware and remove internal URL from client bundle.",
                }
            ],
        }
    )
    probes.append(("PRECISION-3: Structured ASVS 5.0 finding report passes", r6["passed"] is True))

    # RECALL-4: Unapproved live probing flagged as SAFETY_VIOLATION
    r7 = check_finding_report({"unapproved_live_probing_executed": True, "findings": []})
    probes.append(("RECALL-4: Unapproved live probing triggers SAFETY_VIOLATION", r7["passed"] is False and any("SAFETY_VIOLATION" in e for e in r7["errors"])))

    passed = sum(1 for _, ok in probes if ok)
    return {
        "tool": "appsec_control_verifier.py",
        "total_probes": len(probes),
        "passed": passed,
        "failed": len(probes) - passed,
        "all_passed": passed == len(probes),
        "results": [{"probe": n, "passed": ok} for n, ok in probes],
    }


def _load_json(path_str: str) -> dict[str, Any]:
    raw = json.loads(Path(path_str).read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise ValueError(f"Expected JSON object in {path_str}")
    return raw


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Offline AppSec Headers, SSRF & Finding Schema Verifier")
    parser.add_argument("--self-test", action="store_true", help="Run built-in precision & recall probes")
    parser.add_argument("--check-security-headers", metavar="PATH", help="Validate HTTP security headers JSON")
    parser.add_argument("--check-ssrf-url", metavar="URL", help="Validate URL against offline SSRF rules")
    parser.add_argument("--allow-host", action="append", default=[], help="Optional allowlisted host(s) for --check-ssrf-url")
    parser.add_argument("--resolved-ip", action="append", default=[], help="Optional simulated DNS IP(s) for --check-ssrf-url")
    parser.add_argument("--check-finding-report", metavar="PATH", help="Validate structured AppSec finding JSON")
    args = parser.parse_args(argv)

    if args.self_test:
        res = run_self_test()
        print(json.dumps(res, indent=2))
        return 0 if res["all_passed"] else 1
    if args.check_security_headers:
        res = check_security_headers(_load_json(args.check_security_headers))
        print(json.dumps(res, indent=2))
        return 0 if res["passed"] else 1
    if args.check_ssrf_url:
        allowed = {h.lower() for h in args.allow_host} if args.allow_host else None
        res = check_ssrf_url(args.check_ssrf_url, allowed_hosts=allowed, resolved_ips=args.resolved_ip)
        print(json.dumps(res, indent=2))
        return 0 if res["passed"] else 1
    if args.check_finding_report:
        res = check_finding_report(_load_json(args.check_finding_report))
        print(json.dumps(res, indent=2))
        return 0 if res["passed"] else 1

    parser.print_help()
    return 2


if __name__ == "__main__":
    sys.exit(main())
