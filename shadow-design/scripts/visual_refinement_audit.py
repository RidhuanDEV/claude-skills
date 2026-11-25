#!/usr/bin/env python3
"""Offline structural audit for visual refinement reviews (competing emphasis, alarm cues, keyboard reachability).

Zero external dependencies (Python stdlib only) and zero network access.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass, field
from html.parser import HTMLParser
from pathlib import Path
from typing import Any


INTERACTIVE_TAGS = {"button", "a", "input", "select", "textarea", "summary"}
ACCENT_CLASS_TOKENS = {"primary", "cta", "accent", "btn-primary", "bg-accent", "highlight-cta"}
ALARM_ROLES = {"alert", "status"}
ALARM_CLASS_TOKENS = {"alarm", "alert", "critical", "danger", "emergency"}
INLINE_STYLE_ACCENT_RE = re.compile(r"background(?:-color)?\s*:\s*([^;]+)", re.I)


@dataclass
class ElementRecord:
    tag: str
    attrs: dict[str, str]
    text_parts: list[str] = field(default_factory=list)
    line: int = 0

    @property
    def text(self) -> str:
        return " ".join(" ".join(self.text_parts).split())

    @property
    def classes(self) -> set[str]:
        return {c.strip().lower() for c in self.attrs.get("class", "").split() if c.strip()}

    @property
    def is_interactive(self) -> bool:
        if self.tag in INTERACTIVE_TAGS:
            if self.tag == "a" and "href" not in self.attrs:
                return False
            return True
        return self.attrs.get("role", "").lower() in {"button", "link", "menuitem", "tab"}

    @property
    def is_keyboard_reachable(self) -> bool:
        if not self.is_interactive:
            return False
        if "disabled" in self.attrs or "hidden" in self.attrs:
            return False
        if self.attrs.get("aria-hidden", "").lower() == "true":
            return False
        style = self.attrs.get("style", "").lower().replace(" ", "")
        if "display:none" in style or "visibility:hidden" in style:
            return False
        tabindex = self.attrs.get("tabindex")
        if tabindex is not None:
            try:
                if int(tabindex.strip()) < 0:
                    return False
            except ValueError:
                return False
        return True

    @property
    def is_alarm(self) -> bool:
        role = self.attrs.get("role", "").lower()
        return role in ALARM_ROLES or bool(self.classes & ALARM_CLASS_TOKENS) or "data-alarm" in self.attrs

    def accent_signature(self) -> str | None:
        matched_classes = sorted(self.classes & ACCENT_CLASS_TOKENS)
        if matched_classes:
            return f"class:{','.join(matched_classes)}"
        style = self.attrs.get("style", "")
        m = INLINE_STYLE_ACCENT_RE.search(style)
        if m:
            val = m.group(1).strip().lower()
            if val not in {"transparent", "none", "inherit", "#fff", "#ffffff", "white", "#000", "#000000"}:
                return f"bg:{val}"
        return None


class _DOMCollector(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.elements: list[ElementRecord] = []
        self._stack: list[ElementRecord] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attr_map = {k.lower(): ("" if v is None else v) for k, v in attrs}
        rec = ElementRecord(tag=tag.lower(), attrs=attr_map, line=self.getpos()[0])
        self.elements.append(rec)
        if tag.lower() not in {"input", "img", "br", "hr", "meta", "link"}:
            self._stack.append(rec)

    def handle_endtag(self, tag: str) -> None:
        low = tag.lower()
        for idx in range(len(self._stack) - 1, -1, -1):
            if self._stack[idx].tag == low:
                del self._stack[idx:]
                break

    def handle_data(self, data: str) -> None:
        if self._stack and data.strip():
            self._stack[-1].text_parts.append(data.strip())


def audit_html(html: str, primary_id: str | None = None) -> dict[str, Any]:
    """Audit an HTML snippet/document for visual refinement regressions and competing cues."""
    if not html or not html.strip():
        raise ValueError("HTML input is empty.")

    parser = _DOMCollector()
    parser.feed(html)
    parser.close()

    elements = parser.elements
    if not elements:
        raise ValueError("No HTML elements found.")

    findings: list[dict[str, Any]] = []
    preserved_cues: list[dict[str, Any]] = []

    # Locate primary interactive control
    primary: ElementRecord | None = None
    if primary_id:
        for el in elements:
            if el.attrs.get("id") == primary_id:
                primary = el
                break
        if primary is None:
            findings.append(
                {
                    "severity": "BLOCKER",
                    "code": "PRIMARY_ACTION_MISSING",
                    "line": 1,
                    "detail": f"Primary control id='{primary_id}' was not found in the document.",
                }
            )
    else:
        for el in elements:
            if el.is_interactive and el.accent_signature():
                primary = el
                break

    # Keyboard reachability check on primary action (DES-11)
    if primary is not None and not primary.is_keyboard_reachable:
        findings.append(
            {
                "severity": "BLOCKER",
                "code": "PRIMARY_ACTION_UNREACHABLE_BY_KEYBOARD",
                "line": primary.line,
                "element": primary.attrs.get("id") or primary.tag,
                "detail": (
                    f"Primary control <{primary.tag}> ('{primary.text}') is removed from sequential "
                    f"keyboard focus (tabindex={primary.attrs.get('tabindex')!r}, "
                    f"disabled={'disabled' in primary.attrs}, aria-hidden={primary.attrs.get('aria-hidden')!r})."
                ),
            }
        )

    # Competing non-interactive emphasis check (DES-09) vs legitimate alarm retention (DES-10)
    primary_sig = primary.accent_signature() if primary else None
    for el in elements:
        if el is primary:
            continue
        if el.is_alarm:
            has_text = bool(el.text)
            if has_text:
                preserved_cues.append(
                    {
                        "code": "ALARM_EMPHASIS_PRESERVED",
                        "line": el.line,
                        "element": el.attrs.get("id") or el.tag,
                        "text": el.text[:100],
                    }
                )
            else:
                findings.append(
                    {
                        "severity": "HIGH",
                        "code": "ALARM_COLOR_ONLY_NO_TEXT",
                        "line": el.line,
                        "element": el.attrs.get("id") or el.tag,
                        "detail": "Alarm element lacks explicit text; state must not rely on color alone.",
                    }
                )
            continue

        if not el.is_interactive and el.text:
            sig = el.accent_signature()
            if sig and (primary_sig is None or sig == primary_sig or bool(el.classes & ACCENT_CLASS_TOKENS)):
                findings.append(
                    {
                        "severity": "MEDIUM",
                        "code": "COMPETING_NON_INTERACTIVE_EMPHASIS",
                        "line": el.line,
                        "element": el.attrs.get("id") or el.tag,
                        "text": el.text[:100],
                        "detail": (
                            f"Non-interactive <{el.tag}> ('{el.text[:60]}') shares primary accent emphasis ({sig}), "
                            "competing with the primary action."
                        ),
                    }
                )

    has_blocker = any(f["severity"] == "BLOCKER" for f in findings)
    has_findings = bool(findings)
    verdict = "REJECT" if has_blocker else ("REVISE" if has_findings else "PASS")
    tab_order = [
        {"tag": el.tag, "id": el.attrs.get("id", ""), "text": el.text[:60], "line": el.line}
        for el in elements
        if el.is_keyboard_reachable
    ]
    return {
        "verdict": verdict,
        "primary_control": (
            {"tag": primary.tag, "id": primary.attrs.get("id", ""), "text": primary.text[:60], "reachable": primary.is_keyboard_reachable}
            if primary
            else None
        ),
        "focusable_count": len(tab_order),
        "tab_order": tab_order,
        "findings": findings,
        "preserved_cues": preserved_cues,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("html_file", type=Path, help="Path to local HTML fixture or built screen")
    parser.add_argument("--primary-id", help="Exact DOM id of the primary task action to verify")
    args = parser.parse_args(argv)

    if not args.html_file.is_file():
        print(json.dumps({"status": "ERROR", "reason": f"File not found: {args.html_file}"}))
        return 2

    try:
        html = args.html_file.read_text(encoding="utf-8-sig")
        result = audit_html(html, primary_id=args.primary_id)
    except (OSError, UnicodeDecodeError, ValueError) as exc:
        print(json.dumps({"status": "ERROR", "reason": str(exc)}))
        return 2

    print(json.dumps(result, indent=2))
    return 0 if result["verdict"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
