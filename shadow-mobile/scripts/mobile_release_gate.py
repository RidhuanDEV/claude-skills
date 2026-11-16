#!/usr/bin/env python3
"""
Shadow Mobile Release Gate (mobile_release_gate.py)

Deterministic static auditor for OWASP MASVS v2.1.0, Android/iOS manifests,
Play Integrity vs deprecated SafetyNet, PrivacyInfo.xcprivacy, and signing hygiene.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

SKIP_DIRS = {".git", "node_modules", "build", ".gradle", "Pods", "DerivedData", ".dart_tool", "__pycache__"}

ANDROID_CLEARTEXT_TRUE = re.compile(r'android:usesCleartextTraffic\s*=\s*["\']true["\']', re.IGNORECASE)
ANDROID_DEBUGGABLE_TRUE = re.compile(r'android:debuggable\s*=\s*["\']true["\']', re.IGNORECASE)
DEPRECATED_SAFETYNET = re.compile(r"play-services-safetynet|SafetyNet\.getClient", re.IGNORECASE)
IOS_ATS_ARBITRARY_TRUE = re.compile(r"<key>\s*NSAllowsArbitraryLoads\s*</key>\s*<true\s*/>", re.IGNORECASE | re.DOTALL)
HARDCODED_KEYSTORE_PASS = re.compile(
    r"""\b(?:storePassword|keyPassword)\s*(?:=|:)\s*["'](?!\$\{)([^"'\r\n]{4,})["']""",
    re.IGNORECASE,
)
SAFE_GRADLE_ENV = re.compile(r"(?:System\.getenv|findProperty|providers\.environmentVariable|keystoreProperties)", re.IGNORECASE)
EXPORTED_NON_LAUNCHER = re.compile(
    r"<(?:service|receiver|provider)\b[^>]*android:exported\s*=\s*[\"']true[\"'][^>]*>",
    re.IGNORECASE,
)


def audit_mobile_text(content: str, file_name: str = "<snippet>") -> list[dict[str, Any]]:
    """Audit a single mobile config/manifest/source text for MASVS & store release blockers."""
    findings: list[dict[str, Any]] = []
    lower_name = file_name.lower()
    is_debug_variant = "debug" in lower_name or "test" in lower_name

    if ANDROID_CLEARTEXT_TRUE.search(content) and not is_debug_variant:
        findings.append({
            "rule_id": "MASVS_NETWORK_CLEARTEXT_ENABLED",
            "severity": "HIGH",
            "masvs": "MASVS-NETWORK",
            "file": file_name,
            "message": "android:usesCleartextTraffic=\"true\" enabled in non-debug manifest.",
            "remediation": "Set android:usesCleartextTraffic=\"false\" in main AndroidManifest.xml.",
        })

    if ANDROID_DEBUGGABLE_TRUE.search(content) and not is_debug_variant:
        findings.append({
            "rule_id": "MASVS_CODE_DEBUGGABLE_ENABLED",
            "severity": "CRITICAL",
            "masvs": "MASVS-CODE",
            "file": file_name,
            "message": "android:debuggable=\"true\" hardcoded in manifest.",
            "remediation": "Remove android:debuggable=\"true\" from main manifest so release builds stay non-debuggable.",
        })

    for match in EXPORTED_NON_LAUNCHER.finditer(content):
        tag = match.group(0)
        if "android:permission" not in tag.lower():
            findings.append({
                "rule_id": "MASVS_PLATFORM_EXPORTED_WITHOUT_PERMISSION",
                "severity": "HIGH",
                "masvs": "MASVS-PLATFORM",
                "file": file_name,
                "message": "Exported Android service/receiver/provider lacks android:permission guard.",
                "remediation": "Set android:exported=\"false\" or enforce signature-level android:permission.",
            })

    if DEPRECATED_SAFETYNET.search(content):
        findings.append({
            "rule_id": "MASVS_RESILIENCE_DEPRECATED_SAFETYNET",
            "severity": "HIGH",
            "masvs": "MASVS-RESILIENCE",
            "file": file_name,
            "message": "Deprecated Google SafetyNet Attestation API detected.",
            "remediation": "Migrate to Google Play Integrity API (com.google.android.play:integrity) with server-side verification.",
        })

    if IOS_ATS_ARBITRARY_TRUE.search(content) and not is_debug_variant:
        findings.append({
            "rule_id": "MASVS_NETWORK_IOS_ATS_BYPASS",
            "severity": "HIGH",
            "masvs": "MASVS-NETWORK",
            "file": file_name,
            "message": "NSAllowsArbitraryLoads is set to <true/> in Info.plist.",
            "remediation": "Set NSAllowsArbitraryLoads to <false/> for production App Store compliance.",
        })

    for line in content.splitlines():
        if HARDCODED_KEYSTORE_PASS.search(line) and not SAFE_GRADLE_ENV.search(line):
            findings.append({
                "rule_id": "MASVS_CRYPTO_HARDCODED_SIGNING_SECRET",
                "severity": "CRITICAL",
                "masvs": "MASVS-CRYPTO / Release Security",
                "file": file_name,
                "message": "Hardcoded Android keystore storePassword/keyPassword detected.",
                "remediation": "Read signing secrets from System.getenv(...) or git-ignored keystore.properties.",
            })

    return findings


def scan_mobile_repo(root: Path) -> dict[str, Any]:
    findings: list[dict[str, Any]] = []
    scanned = 0
    has_ios_plist = False
    has_privacy_manifest = False

    target_names = {"androidmanifest.xml", "build.gradle", "build.gradle.kts", "info.plist", "privacyinfo.xcprivacy"}
    files = [
        p for p in root.rglob("*")
        if p.is_file()
        and not any(part in SKIP_DIRS for part in p.parts)
        and (p.name.lower() in target_names or p.suffix.lower() in {".kt", ".java", ".swift", ".dart"})
    ]

    for fpath in files:
        lname = fpath.name.lower()
        if lname == "info.plist":
            has_ios_plist = True
        if lname == "privacyinfo.xcprivacy":
            has_privacy_manifest = True
        try:
            text = fpath.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        scanned += 1
        findings.extend(audit_mobile_text(text, str(fpath)))

    if has_ios_plist and not has_privacy_manifest:
        findings.append({
            "rule_id": "MASVS_PRIVACY_MISSING_XCPRIVACY",
            "severity": "HIGH",
            "masvs": "MASVS-PRIVACY / Apple App Store",
            "file": str(root),
            "message": "iOS Info.plist detected without PrivacyInfo.xcprivacy privacy manifest.",
            "remediation": "Add PrivacyInfo.xcprivacy declaring Required Reason APIs and collected data types.",
        })

    return {
        "target": str(root),
        "scanned_files": scanned,
        "finding_count": len(findings),
        "status": "PASS" if not findings else "FINDINGS_DETECTED",
        "findings": findings,
    }


def run_self_test() -> dict[str, Any]:
    """Execute >=5 precision probes and >=3 recall probes (Rule 22)."""
    precision_cases = [
        (
            "PRECISION-1: Hardened main AndroidManifest.xml",
            '<application android:usesCleartextTraffic="false" android:allowBackup="false"><activity android:name=".MainActivity" android:exported="true"><intent-filter><action android:name="android.intent.action.MAIN"/></intent-filter></activity><service android:name=".SyncService" android:exported="false"/></application>',
            "android/app/src/main/AndroidManifest.xml",
        ),
        (
            "PRECISION-2: Gradle signingConfig reading System.getenv",
            'signingConfigs { release { storePassword System.getenv("ANDROID_STORE_PASSWORD") ?: "" } }',
            "android/app/build.gradle",
        ),
        (
            "PRECISION-3: Debug-only manifest allowing localhost Metro cleartext",
            '<application android:usesCleartextTraffic="true" />',
            "android/app/src/debug/AndroidManifest.xml",
        ),
        (
            "PRECISION-4: Production iOS Info.plist with ATS enforced",
            "<key>NSAppTransportSecurity</key><dict><key>NSAllowsArbitraryLoads</key><false/></dict>",
            "ios/Runner/Info.plist",
        ),
        (
            "PRECISION-5: Modern Play Integrity API dependency",
            'implementation("com.google.android.play:integrity:1.4.0")',
            "android/app/build.gradle.kts",
        ),
    ]
    recall_cases = [
        (
            "RECALL-1: Production AndroidManifest with cleartext enabled",
            '<application android:usesCleartextTraffic="true" />',
            "android/app/src/main/AndroidManifest.xml",
            "MASVS_NETWORK_CLEARTEXT_ENABLED",
        ),
        (
            "RECALL-2: Deprecated SafetyNet dependency",
            'implementation "com.google.android.gms:play-services-safetynet:18.0.1"',
            "android/app/build.gradle",
            "MASVS_RESILIENCE_DEPRECATED_SAFETYNET",
        ),
        (
            "RECALL-3: Production Info.plist disabling ATS",
            "<key>NSAllowsArbitraryLoads</key><true/>",
            "ios/Runner/Info.plist",
            "MASVS_NETWORK_IOS_ATS_BYPASS",
        ),
        (
            "RECALL-4: Hardcoded keystore storePassword in build.gradle",
            'signingConfigs { release { storePassword = "superSecretPassword123" } }',
            "android/app/build.gradle",
            "MASVS_CRYPTO_HARDCODED_SIGNING_SECRET",
        ),
    ]

    results: list[dict[str, Any]] = []
    for name, snippet, fname in precision_cases:
        hits = audit_mobile_text(snippet, fname)
        results.append({"probe": name, "passed": len(hits) == 0, "finding_count": len(hits)})

    for name, snippet, fname, expected in recall_cases:
        hits = audit_mobile_text(snippet, fname)
        rules = {h["rule_id"] for h in hits}
        results.append({"probe": name, "passed": expected in rules, "matched_rules": sorted(rules)})

    passed = sum(1 for r in results if r["passed"])
    return {
        "tool": "mobile_release_gate.py",
        "total_probes": len(results),
        "passed": passed,
        "failed": len(results) - passed,
        "all_passed": passed == len(results),
        "results": results,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Shadow Mobile — OWASP MASVS v2.1.0 & Store Release Auditor")
    parser.add_argument("--scan", default=None, help="Mobile project directory to scan")
    parser.add_argument("--self-test", action="store_true", help="Run precision & recall probes")
    args = parser.parse_args()

    if args.self_test:
        res = run_self_test()
        print(json.dumps(res, indent=2))
        return 0 if res["all_passed"] else 1

    if args.scan:
        res = scan_mobile_repo(Path(args.scan))
        print(json.dumps(res, indent=2))
        return 0 if res["finding_count"] == 0 else 1

    parser.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
