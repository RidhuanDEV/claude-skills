from __future__ import annotations

import unittest


def assess_control_effectiveness(
    *,
    control_id: str,
    regulation_snapshot: str,
    design_evidence_present: bool,
    quarterly_samples_collected: int,
    required_samples: int,
) -> dict[str, object]:
    design_rating = "EFFECTIVE" if design_evidence_present else "DEFICIENT"
    if quarterly_samples_collected < required_samples:
        operating_rating = "PENDING_SAMPLE"
        overall = "INCOMPLETE_OPERATING_EVIDENCE"
    else:
        operating_rating = "EFFECTIVE"
        overall = "EFFECTIVE" if design_rating == "EFFECTIVE" else "DEFICIENT"
    return {
        "control_id": control_id,
        "regulation_snapshot": regulation_snapshot,
        "design_effectiveness": design_rating,
        "operating_effectiveness": operating_rating,
        "overall_status": overall,
    }


class GrcDatedRegisterTests(unittest.TestCase):
    def test_t04_e07_missing_quarterly_sample_rates_design_only_and_preserves_dated_snapshot(self) -> None:
        q3 = assess_control_effectiveness(
            control_id="A.8.24",
            regulation_snapshot="POJK-11-2022+PADK-1-2026@2026-09-30",
            design_evidence_present=True,
            quarterly_samples_collected=2,
            required_samples=4,
        )
        self.assertEqual(q3["design_effectiveness"], "EFFECTIVE")
        self.assertEqual(q3["operating_effectiveness"], "PENDING_SAMPLE")
        self.assertEqual(q3["overall_status"], "INCOMPLETE_OPERATING_EVIDENCE")

        q4 = assess_control_effectiveness(
            control_id="A.8.24",
            regulation_snapshot="POJK-11-2022+PADK-1-2026@2026-12-31",
            design_evidence_present=True,
            quarterly_samples_collected=4,
            required_samples=4,
        )
        self.assertEqual(q4["overall_status"], "EFFECTIVE")
        self.assertNotEqual(q3["regulation_snapshot"], q4["regulation_snapshot"])


if __name__ == "__main__":
    unittest.main()
