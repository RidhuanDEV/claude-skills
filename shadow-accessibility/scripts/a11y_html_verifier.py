#!/usr/bin/env python3
"""Deterministic WCAG 2.2 AA accessibility HTML & contrast verifier for shadow-accessibility.

Audits HTML/CSS fragments for:
  1. Programmatic input labeling (explicit <label for>, wrapped <label>, aria-label/labelledby; rejects placeholder-only)
  2. Non-semantic clickable traps (<div onclick> / <span onclick>)
  3. Positive tabindex (> 0) breaking visual keyboard order
  4. Missing <img> alt attributes (allows decorative alt="")
  5. Skipped heading hierarchy (e.g. <h1> -> <h3>) & missing <html lang>
  6. Suppressed focus outlines (`outline: none` / `outline: 0`) without `:focus-visible` ring
  7. Exact WCAG 2.2 relative luminance contrast ratio (4.5:1 normal text, 3.0:1 large/UI)
Zero external dependencies (Python stdlib only).
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

INPUT_RE = re.compile(r"<input\b([^>]*)>", re.IGNORECASE)
LABEL_FOR_RE = re.compile(r'<label\b[^>]*\bfor=["\']([^"\']+)["\'][^>]*>', re.IGNORECASE)
WRAPPED_LABEL_RE = re.compile(r"<label\b[^>]*>[\s\S]*?<input\b[^>]*>[\s\S]*?</label>", re.IGNORECASE)
CLICKABLE_NON_SEMANTIC_RE = re.compile(r"<(?:div|span)\b([^>]*\bonclick\s*=[^>]*)>", re.IGNORECASE)
POSITIVE_TABINDEX_RE = re.compile(r'\btabindex=["\']?\s*([1-9]\d*)\s*["\']?', re.IGNORECASE)
IMG_RE = re.compile(r"<img\b([^>]*)>", re.IGNORECASE)
HEADING_RE = re.compile(r"<h([1-6])\b", re.IGNORECASE)
HTML_TAG_RE = re.compile(r"<html\b([^>]*)>", re.IGNORECASE)
OUTLINE_NONE_RE = re.compile(r"outline\s*:\s*(?:none|0)\b", re.IGNORECASE)

NON_LABEL_INPUT_TYPES = frozenset({"hidden", "submit", "button", "reset", "image"})


def _channel_to_linear(hex_val: int) -> float:
    srgb = hex_val / 255.0
    return srgb / 12.92 if srgb <= 0.03928 else ((srgb + 0.055) / 1.055) ** 2.4


def relative_luminance(hex_color: str) -> float:
    cleaned = hex_color.strip().lstrip("#")
    if len(cleaned) == 3:
        cleaned = "".join(c * 2 for c in cleaned)
    if len(cleaned) != 6 or not re.fullmatch(r"[0-9a-fA-F]{6}", cleaned):
        raise ValueError(f"Invalid hex color: {hex_color}")
    r = _channel_to_linear(int(cleaned[0:2], 16))
    g = _channel_to_linear(int(cleaned[2:4], 16))
    b = _channel_to_linear(int(cleaned[4:6], 16))
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def contrast_ratio(fg_hex: str, bg_hex: str) -> float:
    l1 = relative_luminance(fg_hex)
    l2 = relative_luminance(bg_hex)
    lighter, darker = max(l1, l2), min(l1, l2)
    return round((lighter + 0.05) / (darker + 0.05), 2)


def audit_html(html: str) -> list[dict[str, str]]:
    """Audit an HTML (and optional inline <style>) snippet against core WCAG 2.2 AA structural rules."""
    violations: list[dict[str, str]] = []
    if not isinstance(html, str) or not html.strip():
        return [{"code": "EMPTY_HTML", "detail": "HTML input must be a non-empty string."}]

    # 1. <html lang="..."> when full document present
    html_match = HTML_TAG_RE.search(html)
    if html_match and not re.search(r'\blang=["\'][a-zA-Z-]+["\']', html_match.group(1), re.IGNORECASE):
        violations.append({
            "code": "MISSING_HTML_LANG",
            "detail": "Document <html> element is missing a valid `lang` attribute (needed by screen readers).",
        })

    # 2. Programmatic labels on form inputs
    explicit_fors = set(LABEL_FOR_RE.findall(html))
    wrapped_spans = [m.span() for m in WRAPPED_LABEL_RE.finditer(html)]
    for match in INPUT_RE.finditer(html):
        attrs = match.group(1)
        type_match = re.search(r'\btype=["\']([^"\']+)["\']', attrs, re.IGNORECASE)
        if type_match and type_match.group(1).strip().lower() in NON_LABEL_INPUT_TYPES:
            continue
        pos = match.start()
        is_wrapped = any(start <= pos <= end for start, end in wrapped_spans)
        id_match = re.search(r'\bid=["\']([^"\']+)["\']', attrs, re.IGNORECASE)
        has_for_label = bool(id_match and id_match.group(1) in explicit_fors)
        has_aria = bool(re.search(r'\b(?:aria-label|aria-labelledby)=["\'][^"\']+["\']', attrs, re.IGNORECASE))
        if not (is_wrapped or has_for_label or has_aria):
            violations.append({
                "code": "UNLABELED_INPUT",
                "detail": f"Input missing programmatic label (placeholder alone is insufficient): {match.group(0)}",
            })

    # 3. Non-semantic clickable <div>/<span onclick>
    for match in CLICKABLE_NON_SEMANTIC_RE.finditer(html):
        violations.append({
            "code": "NON_SEMANTIC_CLICKABLE",
            "detail": f"Clickable non-semantic element detected (`{match.group(0)[:60]}`); use native `<button>` or `<a href>`.",
        })

    # 4. Positive tabindex > 0
    for match in POSITIVE_TABINDEX_RE.finditer(html):
        violations.append({
            "code": "POSITIVE_TABINDEX",
            "detail": f"Positive `tabindex=\"{match.group(1)}\"` disrupts natural visual keyboard tab order; use `0` or `-1`.",
        })

    # 5. <img> missing alt attribute (alt="" is permitted for decorative images)
    for match in IMG_RE.finditer(html):
        attrs = match.group(1)
        if not re.search(r'\balt\s*=', attrs, re.IGNORECASE):
            violations.append({
                "code": "IMG_MISSING_ALT",
                "detail": f"Image missing `alt` attribute (use descriptive text or `alt=\"\"` if purely decorative): {match.group(0)}",
            })

    # 6. Skipped heading levels (e.g. h1 -> h3)
    levels = [int(m.group(1)) for m in HEADING_RE.finditer(html)]
    for prev, curr in zip(levels, levels[1:]):
        if curr > prev + 1:
            violations.append({
                "code": "SKIPPED_HEADING_LEVEL",
                "detail": f"Heading hierarchy jumps from <h{prev}> directly to <h{curr}>; keep sequential heading levels.",
            })

    # 7. Outline suppression without :focus-visible replacement
    if OUTLINE_NONE_RE.search(html) and ":focus-visible" not in html.lower():
        violations.append({
            "code": "FOCUS_OUTLINE_REMOVED",
            "detail": "`outline: none` / `outline: 0` found without a visible `:focus-visible` indicator.",
        })

    return violations


def run_self_test() -> dict[str, Any]:
    probes: list[tuple[str, bool]] = []

    # PRECISION-1: Semantic HTML with landmarks, labels, decorative alt="", sequential headings passes
    good_html = (
        '<html lang="id"><body><a href="#main">Skip to main content</a>'
        '<main id="main"><h1>Daftar Pesanan</h1><h2>Filter</h2>'
        '<label for="email">Email</label><input id="email" type="email" />'
        '<label>Telepon <input type="tel" /></label>'
        '<input type="hidden" name="csrf" value="abc" />'
        '<img src="/divider.svg" alt="" /><button type="submit">Kirim</button></main></body></html>'
    )
    v = audit_html(good_html)
    probes.append(("PRECISION-1: Clean semantic HTML with labels, decorative alt & sequential headings passes", len(v) == 0))

    # RECALL-1: Placeholder-only input rejected
    v = audit_html('<form><input type="text" placeholder="Masukkan email" /></form>')
    probes.append(("RECALL-1: Rejects placeholder-only input without programmatic label", {x["code"] for x in v} == {"UNLABELED_INPUT"}))

    # RECALL-2: Clickable <div onclick> and positive tabindex="2" rejected
    v = audit_html('<div onclick="submitForm()" tabindex="2">Simpan</div>')
    codes = {x["code"] for x in v}
    probes.append((
        "RECALL-2: Rejects non-semantic clickable <div> and positive tabindex",
        {"NON_SEMANTIC_CLICKABLE", "POSITIVE_TABINDEX"}.issubset(codes),
    ))

    # RECALL-3: Missing <html lang>, missing img alt, and h1 -> h3 skip rejected
    v = audit_html('<html><body><h1>Judul</h1><h3>Subbagian</h3><img src="/hero.png" /></body></html>')
    codes = {x["code"] for x in v}
    probes.append((
        "RECALL-3: Rejects missing <html lang>, missing <img> alt & skipped h1->h3 heading",
        {"MISSING_HTML_LANG", "IMG_MISSING_ALT", "SKIPPED_HEADING_LEVEL"}.issubset(codes),
    ))

    # RECALL-4: Focus outline: none without :focus-visible rejected
    v = audit_html('<style>button:focus { outline: none; }</style><button>OK</button>')
    codes = {x["code"] for x in v}
    probes.append(("RECALL-4: Rejects outline:none without :focus-visible replacement", "FOCUS_OUTLINE_REMOVED" in codes))

    # PRECISION-2: WCAG contrast calculator distinguishes AA pass vs fail accurately
    pass_ratio = contrast_ratio("#111827", "#FFFFFF")
    fail_ratio = contrast_ratio("#9CA3AF", "#FFFFFF")
    probes.append((
        "PRECISION-2: Contrast ratio calculator passes #111827/#FFFFFF (>=4.5) and flags #9CA3AF/#FFFFFF (<4.5)",
        pass_ratio >= 4.5 and fail_ratio < 4.5,
    ))

    # BOUNDARY-1: Empty HTML rejected gracefully
    v = audit_html("   ")
    probes.append(("BOUNDARY-1: Rejects empty HTML input gracefully", len(v) == 1 and v[0]["code"] == "EMPTY_HTML"))

    passed = sum(1 for _, ok in probes if ok)
    return {
        "tool": "a11y_html_verifier.py",
        "total_probes": len(probes),
        "passed": passed,
        "failed": len(probes) - passed,
        "all_passed": passed == len(probes),
        "results": [{"probe": name, "passed": ok} for name, ok in probes],
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Verify WCAG 2.2 AA structural HTML accessibility and color contrast.")
    parser.add_argument("--self-test", action="store_true", help="Run built-in precision/recall falsification probes.")
    parser.add_argument("--check-html", type=Path, help="Path to HTML file to audit.")
    parser.add_argument("--check-contrast", nargs=2, metavar=("FG_HEX", "BG_HEX"), help="Compute WCAG contrast ratio.")
    args = parser.parse_args(argv)

    if args.self_test:
        report = run_self_test()
        print(json.dumps(report, indent=2))
        return 0 if report["all_passed"] else 1

    if args.check_contrast:
        fg, bg = args.check_contrast
        ratio = contrast_ratio(fg, bg)
        result = {
            "fg": fg,
            "bg": bg,
            "ratio": ratio,
            "pass_aa_normal_text_4_5": ratio >= 4.5,
            "pass_aa_large_or_ui_3_0": ratio >= 3.0,
            "pass_aaa_normal_text_7_0": ratio >= 7.0,
        }
        print(json.dumps(result, indent=2))
        return 0 if ratio >= 3.0 else 1

    if args.check_html:
        html = args.check_html.read_text(encoding="utf-8")
        violations = audit_html(html)
        output = {"status": "PASS" if not violations else "FAIL", "violation_count": len(violations), "violations": violations}
        print(json.dumps(output, indent=2))
        return 0 if not violations else 1

    parser.print_help()
    return 2


if __name__ == "__main__":
    sys.exit(main())
