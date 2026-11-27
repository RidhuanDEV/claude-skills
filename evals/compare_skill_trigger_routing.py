
"""Compare router versions on a frozen English/Indonesian trigger corpus."""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from hashlib import sha256
import json
from pathlib import Path
import re
import subprocess
import sys
from typing import Any, Callable

ROOT = Path(__file__).resolve().parents[1]
ROUTER = ROOT / "shadow-monarch" / "scripts" / "skill_router.py"
sys.path.insert(0, str(ROUTER.parent))
import skill_router

FIXTURES = (
    ROOT / "evals" / "fixtures" / "wave2-trigger-holdout-a.json",
    ROOT / "evals" / "fixtures" / "wave2-trigger-holdout-b.json",
)
DEFAULT_BASELINE = "1dbe3b5b5c57cc38ca2e518c4323aa2c7b4ff857"
RECALL_TARGET = 0.90
PRECISION_TARGET = 0.95
LANGUAGES = ("en", "id")
ADJUDICATIONS = ROOT / "evals" / "fixtures" / "wave2-trigger-adjudications.json"


def digest(paths: tuple[Path, ...]) -> str:
    hash_context = sha256()
    for path in paths:
        hash_context.update(path.relative_to(ROOT).as_posix().encode())
        hash_context.update(b"\0")
        hash_context.update(path.read_bytes().replace(b"\r\n", b"\n"))
        hash_context.update(b"\0")
    return hash_context.hexdigest()


def candidate_digest() -> str:
    catalog = sorted(ROOT.glob("*/SKILL.md"))
    return digest((
        ROUTER, ROUTER.with_name("skill_retrieval.py"), ROUTER.with_name("skill_lexicon_id.py"), *catalog,
    ))


def load_cases(paths: tuple[Path, ...], catalog: set[str]) -> list[dict[str, Any]]:
    cases: list[dict[str, Any]] = []
    ids: set[str] = set()
    prompts: set[str] = set()
    positives: Counter[tuple[str, str]] = Counter()
    near_misses: Counter[tuple[str, str]] = Counter()
    for path in paths:
        rows = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(rows, list):
            raise ValueError(f"{path.name} must contain an array of cases.")
        for row in rows:
            if not isinstance(row, dict) or not isinstance(row.get("id"), str) or not row["id"].strip():
                raise ValueError(f"{path.name} contains a case without an ID.")
            case_id = row["id"]
            prompt = row.get("prompt")
            if not isinstance(prompt, str) or not prompt.strip() or row.get("language") not in LANGUAGES:
                raise ValueError(f"{case_id} must label a nonblank prompt as en or id.")
            key = " ".join(prompt.casefold().split())
            if case_id in ids or key in prompts:
                raise ValueError(f"{case_id} duplicates another case or prompt.")
            ids.add(case_id)
            prompts.add(key)

            expected = row.get("expected_primary")
            excluded = row.get("exclude", [])
            if expected is not None and (not isinstance(expected, str) or expected not in catalog):
                raise ValueError(f"{case_id} has an unknown expected primary skill.")
            if not isinstance(excluded, list) or any(
                not isinstance(skill, str) or skill not in catalog or skill == expected for skill in excluded
            ) or len(set(excluded)) != len(excluded):
                raise ValueError(f"{case_id} has an invalid exclusion list.")
            if excluded:
                for skill in excluded:
                    near_misses[skill, row["language"]] += 1
            elif expected is None:
                raise ValueError(f"{case_id} has no positive label or negative judgment.")
            else:
                positives[expected, row["language"]] += 1
            cases.append(row)

    missing = [
        f"{skill}/{language}" for skill in sorted(catalog) for language in LANGUAGES
        if positives[skill, language] < 3 or near_misses[skill, language] < 1
    ]
    if missing:
        raise ValueError("Insufficient held-out judgments for: " + ", ".join(missing))
    return cases


def apply_adjudications(
    cases: list[dict[str, Any]], path: Path, catalog: set[str],
) -> tuple[list[dict[str, Any]], list[dict[str, str]]]:
    rows = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(rows, list):
        raise ValueError("Adjudication file must contain an array.")
    originals = {case["id"]: case for case in cases}
    prompts = {" ".join(case["prompt"].casefold().split()) for case in cases}
    replacements: dict[str, dict[str, Any]] = {}
    evidence: list[dict[str, str]] = []
    for row in rows:
        if not isinstance(row, dict) or not isinstance(row.get("original_id"), str):
            raise ValueError("Every adjudication must name its original case.")
        original_id = row["original_id"]
        original = originals.get(original_id)
        if original_id in replacements or original is None or not original.get("exclude"):
            raise ValueError(f"{original_id} must be a unique existing near-miss.")
        replacement = row.get("case")
        reason = row.get("reason")
        if not isinstance(replacement, dict) or not isinstance(reason, str) or not reason.strip():
            raise ValueError(f"{original_id} requires a replacement case and an audit reason.")
        proposed_id = replacement.get("id")
        prompt = replacement.get("prompt")
        expected = replacement.get("expected_primary")
        if (
            proposed_id != original_id + "-adjudicated" or proposed_id in originals
            or replacement.get("language") != original["language"]
            or replacement.get("exclude") != original["exclude"]
            or "expected_primary" not in replacement
            or (expected is not None and (
                not isinstance(expected, str) or expected not in catalog or expected in original["exclude"]
            ))
            or not isinstance(prompt, str) or not prompt.strip()
        ):
            raise ValueError(f"{original_id} must preserve its language and tested exclusion with a valid new case.")
        normalized = " ".join(prompt.casefold().split())
        if normalized in prompts:
            raise ValueError(f"{original_id} must use a distinct replacement prompt.")
        prompts.add(normalized)
        replacements[original_id] = replacement
        evidence.append({"original_id": original_id, "replacement_id": proposed_id, "reason": reason})
    return [replacements.get(case["id"], case) for case in cases], evidence


def score_route(
    router: Callable[[str], dict[str, Any]], cases: list[dict[str, Any]], catalog: set[str],
) -> dict[str, Any]:
    counts: dict[str, Counter[str]] = defaultdict(Counter)
    languages: dict[str, Counter[str]] = defaultdict(Counter)
    case_results = []
    retrieval_diagnostics: Counter[str] = Counter()
    for case in cases:
        decision = router(case["prompt"])
        active = set(decision["companion_skills"]) | set(decision["always_on_ui_skills"])
        routing = decision["routing_decision"]
        primary = routing["primary_skill"]
        if routing.get("primary_source") == "fallback" or (
            "primary_source" not in routing and primary == "shadow-monarch" and primary not in active
        ):
            primary = None
        actual = primary
        active.update(routing.get("supporting_skills", ()))
        active.update(routing.get("risk_review_skills", ()))
        if actual is not None:
            active.add(actual)
        expected = case["expected_primary"]
        excludes = case.get("exclude", [])
        language = languages[case["language"]]
        if actual is not None:
            counts[actual]["predicted"] += 1
            if actual == expected:
                counts[actual]["correct_predictions"] += 1
        if not excludes:
            counts[expected]["positives"] += 1
            counts[expected]["correct_positives"] += int(actual == expected)
            language["positives"] += 1
            language["correct_positives"] += int(actual == expected)
            if "retrieval_candidates" in decision:
                shortlist = [candidate["skill"] for candidate in decision["retrieval_candidates"]]
                if actual == expected:
                    retrieval_diagnostics["correct_owner"] += 1
                    if shortlist and shortlist[0] != expected:
                        retrieval_diagnostics["correct_with_other_lexical_leader"] += 1
                elif shortlist and shortlist[0] == expected:
                    retrieval_diagnostics["missed_lexical_leader"] += 1
                elif expected in shortlist:
                    retrieval_diagnostics["missed_shortlist_member"] += 1
                else:
                    retrieval_diagnostics["missed_outside_shortlist"] += 1
        for skill in excludes:
            counts[skill]["near_misses"] += 1
            counts[skill]["quiet_near_misses"] += int(skill not in active)
            language["near_misses"] += 1
            language["quiet_near_misses"] += int(skill not in active)
        case_results.append({
            "id": case["id"],
            "expected_primary": expected,
            "primary": actual,
            "unexpectedly_active": sorted(active.intersection(excludes)),
        })

    by_skill = {}
    for skill in sorted(catalog):
        row = counts[skill]
        recall = row["correct_positives"] / row["positives"]
        precision = row["correct_predictions"] / row["predicted"] if row["predicted"] else None
        specificity = row["quiet_near_misses"] / row["near_misses"]
        passed = recall >= RECALL_TARGET and precision is not None and precision >= PRECISION_TARGET
        by_skill[skill] = {
            **dict(row), "recall": recall, "precision": precision, "near_miss_specificity": specificity,
            "meets_target": passed and specificity >= PRECISION_TARGET,
        }
    totals = sum(counts.values(), Counter())
    exact = sum(row["primary"] == row["expected_primary"] for row in case_results)
    total_skills = len(catalog)
    return {
        "case_count": len(case_results),
        "primary_exact": exact,
        "skills_meeting_target": sum(row["meets_target"] for row in by_skill.values()),
        "primary_recall": totals["correct_positives"] / totals["positives"],
        "primary_precision": totals["correct_predictions"] / totals["predicted"] if totals["predicted"] else None,
        "near_miss_specificity": totals["quiet_near_misses"] / totals["near_misses"],
        "by_skill": by_skill,
        "by_language": {key: dict(value) for key, value in sorted(languages.items())},
        "retrieval_diagnostics": dict(retrieval_diagnostics),
        "cases": case_results,
        "passed": total_skills > 0 and all(row["meets_target"] for row in by_skill.values()),
    }


def load_selections(path: Path, cases: list[dict[str, Any]]) -> dict[str, str]:
    """Read stage-two owner choices keyed by case ID; every case needs exactly one choice."""
    rows = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(rows, dict) or not all(isinstance(key, str) and isinstance(value, str) for key, value in rows.items()):
        raise ValueError("Selections must map each case ID to a skill name or 'none'.")
    missing = sorted(case["id"] for case in cases if case["id"] not in rows)
    if missing:
        raise ValueError(f"{len(missing)} cases have no stage-two selection, e.g. {missing[0]}.")
    return {case["prompt"]: rows[case["id"]] for case in cases}


def two_stage_router(selections: dict[str, str]) -> Callable[[str], dict[str, Any]]:
    """Route with the model's validated owner choice; choices outside the shortlist are rejected."""
    def route(prompt: str) -> dict[str, Any]:
        return skill_router.route_prompt(prompt, selected_owner=selections[prompt])
    return route


def selection_summary(selections: dict[str, str]) -> dict[str, int]:
    statuses: Counter[str] = Counter()
    for prompt, choice in selections.items():
        decision = skill_router.route_prompt(prompt, selected_owner=choice)["routing_decision"]
        statuses[decision["owner_selection"]["status"]] += 1
    return dict(sorted(statuses.items()))


def shortlist_recall(cases: list[dict[str, Any]]) -> dict[str, Any]:
    """Share of positive cases whose labelled owner is among the stage-one candidates."""
    positives = [case for case in cases if not case.get("exclude")]
    missed = [
        case["id"] for case in positives
        if case["expected_primary"] not in skill_router.route_prompt(case["prompt"])["routing_decision"]["owner_candidates"]
    ]
    return {"positives": len(positives), "covered": len(positives) - len(missed), "missed": missed}


def baseline_router(revision: str) -> Callable[[str], dict[str, Any]]:
    if not re.fullmatch(r"[a-f0-9]{40}", revision):
        raise ValueError("Use a full trusted local commit SHA for the baseline.")
    git_path = ROUTER.relative_to(ROOT).as_posix()
    source = subprocess.check_output(
        ["git", "show", f"{revision}:{git_path}"], cwd=ROOT, timeout=15,
    )
    namespace = {"__file__": str(ROUTER), "__name__": "baseline_skill_router"}
    exec(compile(source, f"{revision}:{git_path}", "exec"), namespace)
    return namespace["route_prompt"]


def compare(
    revision: str, freeze: str | None, fixtures: tuple[Path, ...] = FIXTURES, selections_path: Path | None = None,
) -> dict[str, Any]:
    actual_digest = candidate_digest()
    if freeze is not None and freeze != actual_digest:
        raise ValueError("Candidate sources differ from the requested freeze SHA-256.")
    catalog = skill_router.get_known_skill_names()
    original = load_cases(fixtures, catalog)
    if fixtures == FIXTURES:
        cases, adjudications = apply_adjudications(original, ADJUDICATIONS, catalog)
    else:
        cases, adjudications = original, []
    before_router = baseline_router(revision)
    baseline = score_route(before_router, cases, catalog)
    deterministic = score_route(skill_router.route_prompt, cases, catalog)
    selections = load_selections(selections_path, cases) if selections_path else None
    candidate_router = two_stage_router(selections) if selections else skill_router.route_prompt
    candidate = score_route(candidate_router, cases, catalog) if selections else deterministic
    original_baseline = score_route(before_router, original, catalog)
    original_candidate = score_route(candidate_router, original, catalog)
    return {
        "mode": "two_stage" if selections else "deterministic",
        "fixtures": [path.relative_to(ROOT).as_posix() for path in fixtures],
        "deterministic_stage": {
            key: deterministic[key] for key in (
                "primary_exact", "primary_recall", "primary_precision", "near_miss_specificity", "skills_meeting_target",
            )
        },
        "shortlist_recall": shortlist_recall(cases),
        "selection_status": selection_summary(selections) if selections else {},
        "adjudications": adjudications,
        "original_near_miss_specificity": {
            "baseline": original_baseline["near_miss_specificity"],
            "candidate": original_candidate["near_miss_specificity"],
        },
        "baseline_revision": revision,
        "candidate_sha256": actual_digest,
        "fixture_sha256": {
            path.name: sha256(path.read_bytes()).hexdigest()
            for path in (*fixtures, *((ADJUDICATIONS,) if fixtures == FIXTURES else ()), *((selections_path,) if selections_path else ()))
        },
        "metadata_audit": skill_router.audit_descriptions(),
        "baseline": baseline,
        "candidate": candidate,
        "status": "PASS" if candidate["passed"] else "FAIL",
    }


def percentage(value: float | None) -> str:
    return f"{value:.1%}" if value is not None else "—"


def markdown(report: dict[str, Any]) -> str:
    baseline, candidate = report["baseline"], report["candidate"]
    lines = [
        "# Wave 2 Routing Evaluation", "",
        f"**Held-out acceptance gate · {report['status']}**", "",
        f"Compared {candidate['case_count']} prompts across {len(candidate['by_skill'])} skills. "
        "Positive prompts are frozen. Audited near-miss replacements preserve the tested exclusions.",
        f"Baseline commit is {report['baseline_revision']}.",
        f"Candidate source SHA-256 is {report['candidate_sha256']}.",
        f"Mode is {report['mode']}. Fixtures: {', '.join(report['fixtures'])}.",
        f"Stage-one shortlist covers {report['shortlist_recall']['covered']}/{report['shortlist_recall']['positives']} positive owners.",
        *(
            [f"Stage-two selections: {', '.join(f'{key} {value}' for key, value in report['selection_status'].items())}."]
            if report["selection_status"] else []
        ),
        "",
        "| Metric | Baseline | Candidate |", "| --- | ---: | ---: |",
        f"| Exact primary owner | {baseline['primary_exact']}/{baseline['case_count']} | {candidate['primary_exact']}/{candidate['case_count']} |",
        *(
            f"| {label} | {percentage(baseline[key])} | {percentage(candidate[key])} |"
            for key, label in (
                ("primary_recall", "Primary recall"),
                ("primary_precision", "Primary precision"),
                ("near_miss_specificity", "Near-misses with the excluded skill inactive"),
            )
        ),
        f"| Skills meeting all three thresholds | {baseline['skills_meeting_target']} | {candidate['skills_meeting_target']} |",
        "",
        "The per-skill gate requires ≥90% recall, ≥95% primary precision, and ≥95% near-miss specificity. "
        "Recall uses six positive cases per skill. Precision includes all primary assignments. "
        "Specificity uses two near-misses per skill and checks primary, supporting, risk, and always-on skills.", "",
        "| Skill | Recall before → after | Precision before → after | Near-misses quiet before → after | Gate |",
        "| --- | ---: | ---: | ---: | --- |",
    ]
    for skill, after in candidate["by_skill"].items():
        before = baseline["by_skill"][skill]
        comparison = [
            f"{percentage(before[key])} → {percentage(after[key])}"
            for key in ("recall", "precision", "near_miss_specificity")
        ]
        lines.append("| " + " | ".join((skill, *comparison, "PASS" if after["meets_target"] else "FAIL")) + " |")

    lines.extend(("", "## Positive recall by language", "",
                  "| Language | Baseline | Candidate |", "| --- | ---: | ---: |"))
    for language in LANGUAGES:
        before = baseline["by_language"][language]
        after = candidate["by_language"][language]
        lines.append(
            f"| {language} | {before['correct_positives']}/{before['positives']} | "
            f"{after['correct_positives']}/{after['positives']} |"
        )

    diagnostics = candidate["retrieval_diagnostics"]
    if diagnostics:
        lines.extend(("", "## Positive routing diagnostics", "",
                      f"- Correct owner selected in {diagnostics.get('correct_owner', 0)} cases.",
                      f"- Correct owner missed despite ranking first lexically in {diagnostics.get('missed_lexical_leader', 0)} cases.",
                      f"- Correct owner missed with a lower shortlist rank in {diagnostics.get('missed_shortlist_member', 0)} cases.",
                      f"- Correct owner absent from the shortlist and selection in {diagnostics.get('missed_outside_shortlist', 0)} cases.",
                      f"- Lexical rank one would displace {diagnostics.get('correct_with_other_lexical_leader', 0)} correctly routed positives."))
    lines.extend(("", "## Near-miss adjudication", ""))
    original_near_miss = report["original_near_miss_specificity"]
    lines.append(
        f"On the original frozen negatives, baseline specificity was {percentage(original_near_miss['baseline'])} "
        f"and candidate specificity was {percentage(original_near_miss['candidate'])}."
    )
    lines.append("")
    lines.extend(
        f"- {row['original_id']} → {row['replacement_id']}. {row['reason']}"
        for row in report["adjudications"]
    )
    lines.extend(("", "## Reproduction", ""))
    lines.extend(f"- {name} · {fingerprint}" for name, fingerprint in report["fixture_sha256"].items())
    lines.extend(("", "Run the comparison offline with the archived candidate fingerprint.", "",
                  "python -B evals/compare_skill_trigger_routing.py --expect-candidate " + report["candidate_sha256"], ""))
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--baseline", default=DEFAULT_BASELINE)
    parser.add_argument("--expect-candidate", help="Verify the candidate's source fingerprint before opening fixtures.")
    parser.add_argument("--fingerprint", action="store_true", help="Print the candidate fingerprint without opening fixtures.")
    parser.add_argument("--markdown", type=Path, help="Write a per-skill Markdown report.")
    parser.add_argument("--fixtures", type=Path, nargs="+", help="Score these frozen fixture files instead of the default pair.")
    parser.add_argument("--selections", type=Path, help="Stage-two owner choices keyed by case ID (two-stage mode).")
    args = parser.parse_args()
    if args.fingerprint:
        print(candidate_digest())
        return 0
    try:
        fixtures = tuple(path.resolve() for path in args.fixtures) if args.fixtures else FIXTURES
        selections = args.selections.resolve() if args.selections else None
        report = compare(args.baseline, args.expect_candidate, fixtures, selections)
    except (ValueError, OSError, subprocess.SubprocessError) as exc:
        parser.error(str(exc))
    if args.markdown:
        args.markdown.write_text(markdown(report), encoding="utf-8", newline="\n")
    print(json.dumps(report, indent=2))
    return 0 if report["status"] == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
