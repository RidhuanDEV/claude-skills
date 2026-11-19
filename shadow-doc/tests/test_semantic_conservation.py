from __future__ import annotations

import unittest


def verify_semantic_conservation(
    baseline_schema: dict[str, object],
    candidate_schema: dict[str, object],
) -> dict[str, object]:
    base_cols = set(baseline_schema.get("required_columns", []))
    cand_cols = set(candidate_schema.get("required_columns", []))
    missing_cols = sorted(base_cols - cand_cols)
    if missing_cols:
        return {
            "status": "SEMANTIC_REGRESSION",
            "missing_columns": missing_cols,
            "title_changed": baseline_schema.get("title") != candidate_schema.get("title"),
        }
    return {
        "status": "CONSERVED",
        "missing_columns": [],
        "title_changed": baseline_schema.get("title") != candidate_schema.get("title"),
    }


class SemanticConservationTests(unittest.TestCase):
    def test_e14_catches_removed_exception_column_while_allowing_title_wording_change(self) -> None:
        baseline = {
            "title": "UAT Sign-Off Matrix",
            "required_columns": ["req_id", "test_case", "status", "exception_notes"],
        }
        title_only_change = {
            "title": "Staging UAT Sign-Off Matrix (Rev 2)",
            "required_columns": ["req_id", "test_case", "status", "exception_notes"],
        }
        dropped_column = {
            "title": "UAT Sign-Off Matrix",
            "required_columns": ["req_id", "test_case", "status"],
        }

        res_ok = verify_semantic_conservation(baseline, title_only_change)
        self.assertEqual(res_ok["status"], "CONSERVED")
        self.assertTrue(res_ok["title_changed"])

        res_bad = verify_semantic_conservation(baseline, dropped_column)
        self.assertEqual(res_bad["status"], "SEMANTIC_REGRESSION")
        self.assertEqual(res_bad["missing_columns"], ["exception_notes"])


if __name__ == "__main__":
    unittest.main()
