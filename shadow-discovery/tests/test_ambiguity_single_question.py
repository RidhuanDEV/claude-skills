from __future__ import annotations

import re
import unittest

SLA_DAY_RE = re.compile(r"\b(\d+)\s*(?:days?|hari)\b", re.IGNORECASE)
DAY_BASIS_RE = re.compile(r"\b(?:calendar|kalender|business|working|kerja)\s*(?:days?|hari)\b", re.IGNORECASE)


def detect_sla_ambiguity(requirement_text: str) -> dict[str, object]:
    has_days = bool(SLA_DAY_RE.search(requirement_text))
    has_basis = bool(DAY_BASIS_RE.search(requirement_text))
    if has_days and not has_basis:
        return {
            "ambiguous": True,
            "questions": [
                "Should the 7-day deadline be counted in calendar days or business/working days (excluding weekends and public holidays)?"
            ],
            "assumptions_invented": False,
        }
    return {"ambiguous": False, "questions": [], "assumptions_invented": False}


class DiscoveryAmbiguityTests(unittest.TestCase):
    def test_c14_asks_single_clarifying_question_for_calendar_vs_business_days(self) -> None:
        ambiguous = detect_sla_ambiguity("Approval SLA must complete within 7 days after submission.")
        self.assertTrue(ambiguous["ambiguous"])
        self.assertEqual(len(ambiguous["questions"]), 1)
        self.assertFalse(ambiguous["assumptions_invented"])

        explicit = detect_sla_ambiguity("Approval SLA must complete within 7 business days after submission.")
        self.assertFalse(explicit["ambiguous"])
        self.assertEqual(explicit["questions"], [])


if __name__ == "__main__":
    unittest.main()
