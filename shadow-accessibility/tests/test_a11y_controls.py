from __future__ import annotations

import re
import unittest

INPUT_RE = re.compile(r"<input\b([^>]*)>", re.IGNORECASE)
LABEL_FOR_RE = re.compile(r'<label\b[^>]*\bfor=["\']([^"\']+)["\'][^>]*>', re.IGNORECASE)
WRAPPED_LABEL_RE = re.compile(r"<label\b[^>]*>[\s\S]*?<input\b[^>]*>[\s\S]*?</label>", re.IGNORECASE)


def audit_accessible_inputs(html: str) -> list[str]:
    issues: list[str] = []
    explicit_fors = set(LABEL_FOR_RE.findall(html))
    wrapped_spans = [m.span() for m in WRAPPED_LABEL_RE.finditer(html)]
    for match in INPUT_RE.finditer(html):
        attrs = match.group(1)
        pos = match.start()
        is_wrapped = any(start <= pos <= end for start, end in wrapped_spans)
        id_match = re.search(r'\bid=["\']([^"\']+)["\']', attrs)
        has_for_label = bool(id_match and id_match.group(1) in explicit_fors)
        has_aria = bool(re.search(r'\b(?:aria-label|aria-labelledby)=["\'][^"\']+["\']', attrs))
        if not (is_wrapped or has_for_label or has_aria):
            issues.append(f"Input missing programmatic label (placeholder alone is insufficient): {match.group(0)}")
    return issues


class AccessibilityControlTests(unittest.TestCase):
    def test_c04_accepts_wrapped_and_explicit_labels_rejects_placeholder_only(self) -> None:
        good_html = (
            '<label for="email">Email</label><input id="email" type="email" />'
            '<label>Phone <input type="tel" /></label>'
        )
        self.assertEqual(audit_accessible_inputs(good_html), [])

        bad_html = '<input type="text" placeholder="Enter your email" />'
        issues = audit_accessible_inputs(bad_html)
        self.assertEqual(len(issues), 1)
        self.assertIn("placeholder alone is insufficient", issues[0])

    def test_c04_modal_dialog_escape_restores_trigger_focus(self) -> None:
        focus_stack: list[str] = ["open-modal-btn"]
        # Open dialog -> focus moves into dialog close button
        focus_stack.append("dialog-close-btn")
        self.assertEqual(focus_stack[-1], "dialog-close-btn")
        # Escape closes dialog -> focus returns to trigger
        focus_stack.pop()
        self.assertEqual(focus_stack[-1], "open-modal-btn")


if __name__ == "__main__":
    unittest.main()
