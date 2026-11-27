"""Score the with-skill vs no-skill behavioural evaluation from stored, blinded judgments.

Usage:
    python evals/score_behavioral_uplift.py [--fixtures evals/fixtures/wave5-behavioral] [--json out.json]

Inputs (one graded scenario per skill):
  scenarios.json        qid, skill, prompt, pass_criteria, red_flags, a_is ("skill" or "baseline")
  judge-output-*.json   blinded grades for answer A and answer B; a later file overrides an
                        earlier one for the same qid (re-judging after a criteria correction)
Scenarios listed in EXCLUDED are reported but left out of the statistics.
"""

from __future__ import annotations

import argparse
from dataclasses import asdict, dataclass
import json
from math import comb
from pathlib import Path
import statistics
import sys

DEFAULT_FIXTURES = Path(__file__).resolve().parent / "fixtures" / "wave5-behavioral"
EXCLUDED = {
    "shadow-video": "evaluations.md has falsification probes but no graded prompt",
    "shadow-monarch": "the selected repo eval tested PMO/EVM, not orchestration",
}


@dataclass(frozen=True)
class Row:
    skill: str
    skill_score: int
    baseline_score: int
    skill_pass: bool
    baseline_pass: bool
    excluded: str | None


def load_rows(fixtures: Path) -> list[Row]:
    scenarios = json.loads((fixtures / "scenarios.json").read_text(encoding="utf-8"))
    grades: dict[str, dict[str, object]] = {}
    for path in sorted(fixtures.glob("judge-output-*.json")):
        grades.update(json.loads(path.read_text(encoding="utf-8")))
    rows: list[Row] = []
    for scenario in scenarios:
        grade = grades[scenario["qid"]]
        skill_side, base_side = ("A", "B") if scenario["a_is"] == "skill" else ("B", "A")
        skill_grade, base_grade = grade[skill_side], grade[base_side]
        if not isinstance(skill_grade, dict) or not isinstance(base_grade, dict):
            raise ValueError(f"{scenario['qid']}: malformed grade")
        rows.append(Row(
            scenario["skill"], int(skill_grade["score"]), int(base_grade["score"]),
            skill_grade["pass"] is True, base_grade["pass"] is True, EXCLUDED.get(scenario["skill"]),
        ))
    return rows


def summarize(rows: list[Row]) -> dict[str, object]:
    valid = [row for row in rows if row.excluded is None]
    deltas = [row.skill_score - row.baseline_score for row in valid]
    nonzero = [delta for delta in deltas if delta != 0]
    wins = sum(delta > 0 for delta in nonzero)
    p_value = sum(comb(len(nonzero), i) for i in range(wins, len(nonzero) + 1)) / 2 ** len(nonzero) if nonzero else 1.0
    return {
        "valid_scenarios": len(valid),
        "excluded": {row.skill: row.excluded for row in rows if row.excluded},
        "mean_skill_score": round(statistics.mean(row.skill_score for row in valid), 2),
        "mean_baseline_score": round(statistics.mean(row.baseline_score for row in valid), 2),
        "mean_uplift": round(statistics.mean(deltas), 2),
        "skill_full_passes": sum(row.skill_pass for row in valid),
        "baseline_full_passes": sum(row.baseline_pass for row in valid),
        "positive": wins, "ties": len(deltas) - len(nonzero), "negative": len(nonzero) - wins,
        "sign_test_one_sided_p": p_value,
        "no_uplift": sorted(row.skill for row in valid if row.skill_score <= row.baseline_score),
        "rows": [asdict(row) for row in rows],
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--fixtures", type=Path, default=DEFAULT_FIXTURES)
    parser.add_argument("--json", type=Path)
    args = parser.parse_args(argv)
    summary = summarize(load_rows(args.fixtures))
    if args.json:
        args.json.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps({key: value for key, value in summary.items() if key != "rows"}, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
