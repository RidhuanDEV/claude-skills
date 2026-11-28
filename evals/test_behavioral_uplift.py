"""Lock the published Wave 5 behavioural result to its stored, blinded judgments."""

from __future__ import annotations

from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parent))
import score_behavioral_uplift as scoring  # noqa: E402


class BehavioralUpliftTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.summary = scoring.summarize(scoring.load_rows(scoring.DEFAULT_FIXTURES))

    def test_published_numbers_match_the_stored_judgments(self) -> None:
        summary = self.summary
        self.assertEqual(summary["valid_scenarios"], 57)
        self.assertEqual((summary["mean_skill_score"], summary["mean_baseline_score"], summary["mean_uplift"]), (9.51, 6.51, 3.0))
        self.assertEqual((summary["skill_full_passes"], summary["baseline_full_passes"]), (44, 4))
        self.assertEqual((summary["positive"], summary["ties"], summary["negative"]), (50, 6, 1))
        self.assertLess(summary["sign_test_one_sided_p"], 1e-10)

    def test_every_skill_has_exactly_one_scenario_and_exclusions_are_explained(self) -> None:
        skills = [row["skill"] for row in self.summary["rows"]]
        self.assertEqual(len(skills), len(set(skills)))
        self.assertEqual(len(skills), 59)
        self.assertEqual(set(self.summary["excluded"]), {"shadow-video", "shadow-monarch"})

    def test_ties_without_uplift_are_listed_for_follow_up(self) -> None:
        self.assertIn("antislop-copywriting", self.summary["no_uplift"])
        self.assertEqual(len(self.summary["no_uplift"]), 7)


class BehavioralRerunTests(unittest.TestCase):
    """Wave 5 follow-up: the 7 no-uplift skills plus shadow-video, re-measured after their fixes."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.summary = scoring.summarize(scoring.load_rows(scoring.DEFAULT_FIXTURES.parent / "wave5-rerun"))

    def test_rerun_numbers_match_the_stored_judgments(self) -> None:
        summary = self.summary
        self.assertEqual(summary["valid_scenarios"], 13)
        self.assertEqual(summary["excluded"], {})
        self.assertEqual((summary["mean_skill_score"], summary["mean_baseline_score"]), (9.85, 6.85))
        self.assertEqual((summary["skill_full_passes"], summary["baseline_full_passes"]), (13, 3))
        self.assertEqual((summary["positive"], summary["ties"], summary["negative"]), (13, 0, 0))
        self.assertEqual(summary["no_uplift"], [])

    def test_every_previous_no_uplift_skill_and_video_is_covered(self) -> None:
        skills = {row["skill"] for row in self.summary["rows"]}
        self.assertEqual(skills, {
            "antislop-copywriting", "shadow-ai-eng", "shadow-compat", "shadow-domain",
            "shadow-quality", "shadow-search", "shadow-illustration", "shadow-video",
        })


if __name__ == "__main__":
    unittest.main()
