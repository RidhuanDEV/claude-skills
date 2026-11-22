#!/usr/bin/env python3
"""
Shadow SEO Deterministic Audit Verifier (seo_audit_verifier.py)

Offline L0/L1 validator for:
1. Redirect maps (detects self-loops, cycles, redirect chains > 1 hop, invalid paths)
2. International hreflang clusters (reciprocity, self-reference, x-default, canonical alignment, BCP-47 check)
3. JSON-LD structured data safety (valid JSON, @context, raw '<' XSS breakout check)
4. Production SSR SEO page gate (accidental noindex, title/meta bounds, canonical https, single H1)
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

BCP47_RE = re.compile(r"^[a-z]{2,3}(?:-[A-Z][a-z]{3})?(?:-(?:[A-Z]{2}|\d{3}))?$")
INVALID_LOCALE_ALIASES = {"en-UK", "in-ID", "iw-IL", "zh-CH"}


def validate_redirect_map(redirects: dict[str, str]) -> dict[str, Any]:
    issues: list[dict[str, Any]] = []
    for source, direct_target in redirects.items():
        if not source.startswith("/") or not (direct_target.startswith("/") or direct_target.startswith("https://")):
            issues.append({"source": source, "kind": "INVALID_PATH", "path": [source, direct_target]})
            continue
        if source == direct_target:
            issues.append({"source": source, "kind": "SELF_LOOP", "path": [source, direct_target]})
            continue
        chain = [source]
        seen = {source}
        cursor = direct_target
        is_cycle = False
        while cursor in redirects:
            if cursor in seen:
                issues.append({"source": source, "kind": "CYCLE", "path": [*chain, cursor]})
                is_cycle = True
                break
            seen.add(cursor)
            chain.append(cursor)
            cursor = redirects[cursor]
        if not is_cycle and len(chain) > 1:
            issues.append({"source": source, "kind": "CHAIN_GT_1_HOP", "path": [*chain, cursor]})
    return {"checked": len(redirects), "issues": issues, "passed": len(issues) == 0}


def validate_hreflang_cluster(pages: list[dict[str, Any]]) -> dict[str, Any]:
    errors: list[str] = []
    by_url = {str(p["url"]): p for p in pages if "url" in p}

    for page in pages:
        url = str(page.get("url", ""))
        canonical = str(page.get("canonical_url", ""))
        locale = str(page.get("locale", ""))
        alternates = page.get("alternates", {})
        if not isinstance(alternates, dict):
            errors.append(f"{url}: alternates must be an object")
            continue
        if not url.startswith("https://"):
            errors.append(f"{url}: url must be absolute https://")
        if canonical != url:
            errors.append(f"{url}: canonical ({canonical}) differs from hreflang URL")
        if locale in INVALID_LOCALE_ALIASES or not BCP47_RE.match(locale):
            errors.append(f"{url}: invalid BCP-47 locale '{locale}'")
        if alternates.get(locale) != url:
            errors.append(f"{url}: missing self-referencing hreflang '{locale}'")
        if not alternates.get("x-default"):
            errors.append(f"{url}: missing 'x-default' fallback")
        for alt_lang, alt_url in alternates.items():
            if alt_lang == "x-default":
                if not str(alt_url).startswith("https://"):
                    errors.append(f"{url}: x-default must be absolute https://")
                continue
            if alt_lang in INVALID_LOCALE_ALIASES or not BCP47_RE.match(str(alt_lang)):
                errors.append(f"{url}: invalid alternate BCP-47 code '{alt_lang}'")
            peer = by_url.get(str(alt_url))
            if peer is None:
                errors.append(f"{url}: alternate '{alt_lang}' -> {alt_url} missing from cluster")
                continue
            if peer.get("alternates", {}).get(locale) != url:
                errors.append(f"{url}: non-reciprocal hreflang — {alt_url} does not link back to '{locale}'")
    return {"pages_checked": len(pages), "errors": errors, "passed": len(errors) == 0}


def validate_jsonld_script(raw_json_script: str) -> dict[str, Any]:
    errors: list[str] = []
    if "<" in raw_json_script or "</script" in raw_json_script.lower():
        errors.append("UNESCAPED_HTML_TAG: escape '<' as '\\u003c' inside <script type='application/ld+json'>")
    try:
        parsed = json.loads(raw_json_script)
    except json.JSONDecodeError as exc:
        errors.append(f"INVALID_JSON: {exc}")
        return {"errors": errors, "passed": False}
    if not isinstance(parsed, dict) or not str(parsed.get("@context", "")).startswith("https://schema.org"):
        errors.append("MISSING_SCHEMA_CONTEXT: @context must reference https://schema.org")
    if "@type" not in parsed and "@graph" not in parsed:
        errors.append("MISSING_TYPE_OR_GRAPH: JSON-LD must define @type or @graph")
    return {"errors": errors, "passed": len(errors) == 0}


def validate_ssr_seo_page(page: dict[str, Any]) -> dict[str, Any]:
    errors: list[str] = []
    url = str(page.get("url", "<unknown>"))
    env = str(page.get("environment", "production")).lower()
    has_noindex = bool(page.get("has_noindex", False))
    if env == "production" and has_noindex:
        errors.append(f"{url}: CRITICAL accidental noindex in production")
    if env != "production" and not has_noindex:
        errors.append(f"{url}: non-production host ({env}) missing X-Robots-Tag noindex")
    title = str(page.get("title", "")).strip()
    if not (15 <= len(title) <= 65):
        errors.append(f"{url}: title length {len(title)} outside 15..65")
    desc = str(page.get("meta_description", "")).strip()
    if not (50 <= len(desc) <= 165):
        errors.append(f"{url}: meta_description length {len(desc)} outside 50..165")
    canonical = str(page.get("canonical_url", ""))
    if not canonical.startswith("https://"):
        errors.append(f"{url}: canonical_url must be absolute https://")
    if int(page.get("h1_count", 0)) != 1:
        errors.append(f"{url}: expected exactly 1 <h1>, found {page.get('h1_count')}")
    if env == "production" and int(page.get("valid_jsonld_count", 0)) < 1:
        errors.append(f"{url}: missing parseable JSON-LD on indexable page")
    return {"url": url, "errors": errors, "passed": len(errors) == 0}


def run_self_test() -> dict[str, Any]:
    clean_redirects = validate_redirect_map({"/old-a": "/new-a", "/old-b": "https://example.com/new-b"})
    bad_redirects = validate_redirect_map({"/a": "/b", "/b": "/c", "/loop": "/loop", "/x": "/y", "/y": "/x"})

    clean_hreflang = validate_hreflang_cluster(
        [
            {
                "url": "https://example.com/id/harga",
                "canonical_url": "https://example.com/id/harga",
                "locale": "id-ID",
                "alternates": {
                    "id-ID": "https://example.com/id/harga",
                    "en": "https://example.com/en/pricing",
                    "x-default": "https://example.com/en/pricing",
                },
            },
            {
                "url": "https://example.com/en/pricing",
                "canonical_url": "https://example.com/en/pricing",
                "locale": "en",
                "alternates": {
                    "id-ID": "https://example.com/id/harga",
                    "en": "https://example.com/en/pricing",
                    "x-default": "https://example.com/en/pricing",
                },
            },
        ]
    )
    bad_hreflang = validate_hreflang_cluster(
        [
            {
                "url": "https://example.com/id/harga",
                "canonical_url": "https://example.com/en/pricing",
                "locale": "in-ID",
                "alternates": {"en-UK": "https://example.com/en/pricing"},
            }
        ]
    )

    safe_ld = validate_jsonld_script(r'{"@context":"https://schema.org","@type":"Product","name":"A \u003c B"}')
    xss_ld = validate_jsonld_script('{"@context":"https://schema.org","@type":"Product","name":"</script><script>x()</script>"}')
    prod_noindex = validate_ssr_seo_page(
        {
            "url": "https://example.com/",
            "environment": "production",
            "has_noindex": True,
            "title": "Valid Home Page Title Example",
            "meta_description": "A valid meta description exceeding fifty characters cleanly for testing.",
            "canonical_url": "https://example.com/",
            "h1_count": 1,
            "valid_jsonld_count": 1,
        }
    )

    probes = [
        ("PRECISION-1: Clean 1-hop redirect map passes", clean_redirects["passed"]),
        ("RECALL-1: Redirect chain, self-loop & cycle detected", not bad_redirects["passed"] and len(bad_redirects["issues"]) >= 3),
        ("PRECISION-2: Reciprocal id-ID/en/x-default hreflang cluster passes", clean_hreflang["passed"]),
        ("RECALL-2: Invalid locale (in-ID/en-UK), canonical mismatch & missing reciprocity rejected", not bad_hreflang["passed"] and len(bad_hreflang["errors"]) >= 4),
        ("PRECISION-3: Escaped JSON-LD passes", safe_ld["passed"]),
        ("RECALL-3: Unescaped </script> XSS payload in JSON-LD rejected", not xss_ld["passed"]),
        ("RECALL-4: Accidental production noindex rejected", not prod_noindex["passed"]),
    ]
    results = [{"probe": name, "passed": ok} for name, ok in probes]
    passed = sum(1 for r in results if r["passed"])
    return {
        "tool": "seo_audit_verifier.py",
        "total_probes": len(results),
        "passed": passed,
        "failed": len(results) - passed,
        "all_passed": passed == len(results),
        "results": results,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Shadow SEO Offline Audit Verifier")
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument("--check-redirects", default=None, help="JSON map of source -> target redirects")
    parser.add_argument("--check-hreflang", default=None, help="JSON list of localized page SEO specs")
    parser.add_argument("--check-jsonld", default=None, help="Raw JSON-LD file path")
    parser.add_argument("--check-ssr-page", default=None, help="JSON SSR SEO page payload")
    args = parser.parse_args()

    if args.self_test:
        res = run_self_test()
        print(json.dumps(res, indent=2))
        return 0 if res["all_passed"] else 1
    if args.check_redirects:
        res = validate_redirect_map(json.loads(Path(args.check_redirects).read_text(encoding="utf-8-sig")))
        print(json.dumps(res, indent=2))
        return 0 if res["passed"] else 1
    if args.check_hreflang:
        res = validate_hreflang_cluster(json.loads(Path(args.check_hreflang).read_text(encoding="utf-8-sig")))
        print(json.dumps(res, indent=2))
        return 0 if res["passed"] else 1
    if args.check_jsonld:
        res = validate_jsonld_script(Path(args.check_jsonld).read_text(encoding="utf-8-sig"))
        print(json.dumps(res, indent=2))
        return 0 if res["passed"] else 1
    if args.check_ssr_page:
        res = validate_ssr_seo_page(json.loads(Path(args.check_ssr_page).read_text(encoding="utf-8-sig")))
        print(json.dumps(res, indent=2))
        return 0 if res["passed"] else 1

    parser.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
