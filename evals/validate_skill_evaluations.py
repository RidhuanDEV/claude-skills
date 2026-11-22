#!/usr/bin/env python3
"""Offline Skill Evaluation, Reference Guide & Wave Readiness Validator (L0/L1).

Zero third-party dependencies (Python 3 stdlib only).
Audits Shadow Army skills for:
  1. Zero broken relative `references/...` links in SKILL.md (supports nested subdirs!)
  2. `## Reference Guide` & 100% reference indexing on upgraded specialist skills
  3. `evaluations.md` scenario count (supports table rows, `### ID` headings, YAML specs, and falsification probes)
     plus explicit negative/safety guards
  4. Per-wave readiness summary with explicit PASS / WARN / FAIL / NOT_RUN reporting
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
MD_LINK_RE = re.compile(r"\[[^\]]+\]\((references/[^)#\s]+)\)")
EVAL_TABLE_ID_RE = re.compile(r"^\|\s*\*\*([A-Z0-9_-]+)\*\*\s*\|", re.MULTILINE)
EVAL_HEADING_ID_RE = re.compile(r"^###\s+([A-Z0-9_-]+-EVAL-\d+)\b", re.MULTILINE)
YAML_ID_RE = re.compile(r"^\s*id:\s*([a-zA-Z0-9_-]+)\s*$", re.MULTILINE)
PROBE_ROW_RE = re.compile(r"^\|\s*`?[^|\n-]+`?\s*\|\s*[^|\n]+\|", re.MULTILINE)

# Skills upgraded to the W0+ modular specialist standard
UPGRADED_SPECIALIST_SKILLS = {
    "shadow-accessibility",
    "shadow-ai-eng",
    "shadow-analytics",
    "shadow-api",
    "shadow-auth",
    "shadow-browser",
    "shadow-cache",
    "shadow-concurrency",
    "shadow-data",
    "shadow-db",
    "shadow-debug",
    "shadow-domain",
    "shadow-email",
    "shadow-eval",
    "shadow-integrate",
    "shadow-observe",
    "shadow-perf",
    "shadow-privacy",
    "shadow-quality",
    "shadow-realtime",
    "shadow-resilience",
    "shadow-search",
    "shadow-sec",
    "shadow-seo",
    "shadow-test",
}


def _count_eval_scenarios(eval_text: str) -> int:
    table_ids = EVAL_TABLE_ID_RE.findall(eval_text)
    heading_ids = EVAL_HEADING_ID_RE.findall(eval_text)
    yaml_ids = YAML_ID_RE.findall(eval_text)
    structured = max(len(table_ids), len(heading_ids), len(yaml_ids))
    if structured > 0:
        return structured
    # Fallback for legacy falsification-probe tables (e.g., shadow-video / shadow-illustration)
    rows = [m.group(0) for m in PROBE_ROW_RE.finditer(eval_text) if "---" not in m.group(0)]
    return max(0, len(rows) - 1) if len(rows) > 1 else 0


def audit_skill(skill_dir: Path, strict_eval_required: bool = False) -> dict[str, Any]:
    skill_md_path = skill_dir / "SKILL.md"
    if not skill_md_path.exists():
        return {"skill": skill_dir.name, "status": "FAIL", "errors": ["Missing SKILL.md"], "warnings": []}

    text = skill_md_path.read_text(encoding="utf-8", errors="ignore")
    refs_dir = skill_dir / "references"
    ref_files = (
        sorted(p.relative_to(skill_dir).as_posix() for p in refs_dir.rglob("*.md"))
        if refs_dir.exists()
        else []
    )
    linked_refs = sorted({m.group(1) for m in MD_LINK_RE.finditer(text)})

    errors: list[str] = []
    warnings: list[str] = []

    has_ref_guide = "## Reference Guide" in text
    broken_links = [rel for rel in linked_refs if not (skill_dir / rel).exists()]
    orphan_refs = [rel for rel in ref_files if rel not in linked_refs]

    if broken_links:
        errors.append(f"Broken reference links in SKILL.md: {broken_links}")
    if ref_files and not has_ref_guide:
        warnings.append("Has references/*.md but missing standardized '## Reference Guide' heading.")
    if ref_files and orphan_refs:
        warnings.append(f"Unindexed reference files not linked in SKILL.md: {orphan_refs}")

    eval_path = skill_dir / "evaluations.md"
    eval_scenarios = 0
    has_fail_guard = False
    if eval_path.exists():
        eval_text = eval_path.read_text(encoding="utf-8", errors="ignore")
        eval_scenarios = _count_eval_scenarios(eval_text)
        has_fail_guard = bool(
            re.search(
                r"\b(?:Fail Red Flags|must_not|Red Flags|Forbidden|Anti-Pattern|Falsification probes|pass/reject|rejects|refuse|NEVER)\b",
                eval_text,
                re.IGNORECASE,
            )
        )
        if eval_scenarios < 4:
            errors.append(f"evaluations.md has only {eval_scenarios} scenarios (minimum 4 expected).")
        if not has_fail_guard:
            errors.append("evaluations.md missing explicit negative/safety guard ('Fail Red Flags', 'must_not', or falsification refusal).")
    elif strict_eval_required:
        errors.append("Missing evaluations.md required for upgraded specialist skill.")

    scripts = sorted(f.name for f in (skill_dir / "scripts").glob("*.py")) if (skill_dir / "scripts").exists() else []
    tests = sorted(f.name for f in (skill_dir / "tests").glob("test_*.py")) if (skill_dir / "tests").exists() else []

    if strict_eval_required and ref_files and (not has_ref_guide or orphan_refs):
        errors.append("Upgraded specialist skill must index 100% of references/*.md inside '## Reference Guide'.")

    status = "FAIL" if errors else ("WARN" if warnings else "PASS")
    return {
        "skill": skill_dir.name,
        "status": status,
        "has_ref_guide": has_ref_guide,
        "references_count": len(ref_files),
        "indexed_references_count": len([r for r in linked_refs if r not in broken_links]),
        "scripts_count": len(scripts),
        "tests_count": len(tests),
        "has_evaluations_md": eval_path.exists(),
        "evaluation_scenarios": eval_scenarios,
        "live_llm_eval_status": "NOT_RUN",
        "errors": errors,
        "warnings": warnings,
    }


def audit_repository(repo_root: Path = REPO_ROOT, strict_skills: set[str] | None = None) -> dict[str, Any]:
    strict_set = set(UPGRADED_SPECIALIST_SKILLS)
    if strict_skills:
        strict_set.update(strict_skills)

    skill_dirs = sorted(p.parent for p in repo_root.glob("*/SKILL.md"))
    results = [audit_skill(d, strict_eval_required=(d.name in strict_set)) for d in skill_dirs]

    failed = [r for r in results if r["status"] == "FAIL"]
    with_eval = [r for r in results if r["has_evaluations_md"]]
    missing_ref_guide = [r["skill"] for r in results if r["references_count"] > 0 and not r["has_ref_guide"]]

    return {
        "tool": "validate_skill_evaluations.py",
        "total_skills": len(results),
        "strict_skills_checked": sorted(s for s in strict_set if (repo_root / s / "SKILL.md").exists()),
        "skills_with_evaluations_md": len(with_eval),
        "total_evaluation_scenarios": sum(r["evaluation_scenarios"] for r in with_eval),
        "skills_missing_ref_guide_count": len(missing_ref_guide),
        "skills_missing_ref_guide": missing_ref_guide,
        "failed_count": len(failed),
        "all_passed": len(failed) == 0,
        "live_llm_eval_status": "NOT_RUN (requires explicit L3 approval & external model API budget)",
        "failures": failed,
        "skills": results,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate Shadow Army skill Reference Guides and evaluations.md")
    parser.add_argument("--repo", default=str(REPO_ROOT), help="Path to repository root")
    parser.add_argument(
        "--strict-skills",
        nargs="*",
        default=[],
        help="Additional skill names to enforce strict evaluations.md + 100% Reference Guide indexing",
    )
    parser.add_argument("--summary-only", action="store_true", help="Omit per-skill full array for compact CLI output")
    args = parser.parse_args(argv)

    report = audit_repository(Path(args.repo), strict_skills=set(args.strict_skills))
    if args.summary_only:
        compact = {k: v for k, v in report.items() if k != "skills"}
        print(json.dumps(compact, indent=2))
    else:
        print(json.dumps(report, indent=2))
    return 0 if report["all_passed"] else 1


if __name__ == "__main__":
    sys.exit(main())
