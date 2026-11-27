"""Check the dated facts registry and scan skill content for stale facts.

Usage:
    python facts_registry_check.py --repo . [--today 2026-11-27] [--json report.json]

Fails (exit 1) when:
  * the registry is malformed, an ID repeats, or review_by is before verified_on;
  * a fact's review_by date has passed (the fact must be re-verified);
  * a stale_pattern appears in skill content on a line that does not match the fact's
    allow_context (for example "RFC 7489" without saying it is obsolete);
  * a fact names required_in skills whose content never mentions required_token.

Scanned: */SKILL.md, */evaluations.md, */references/**/*.md, */scripts/*.py, the monarch
reference modules, README.md and evals/README.md. Vendored upstream folders (references/vendor,
external-upstreams) are reported as skipped, because their text belongs to the upstream project.
"""

from __future__ import annotations

import argparse
from dataclasses import asdict, dataclass
from datetime import date
import json
from pathlib import Path
import re
import sys

REGISTRY = Path("shadow-monarch/reference/facts-registry.json")
REQUIRED_KEYS = ("id", "statement", "value", "source_url", "publisher", "verified_on", "review_by", "stale_patterns")
VENDOR_PARTS = ("vendor", "external-upstreams")
SCAN_GLOBS = (
    "*/SKILL.md", "*/evaluations.md", "*/references/**/*.md", "*/scripts/*.py",
    "shadow-monarch/reference/*.md", "README.md", "evals/README.md",
)


@dataclass(frozen=True)
class Finding:
    kind: str
    fact: str
    path: str
    line: int
    text: str


@dataclass(frozen=True)
class Fact:
    id: str
    review_by: date
    patterns: tuple[re.Pattern[str], ...]
    allow: re.Pattern[str] | None
    required_in: tuple[str, ...]
    required_token: str | None


def _iso(value: object) -> date | None:
    try:
        return date.fromisoformat(value) if isinstance(value, str) else None
    except ValueError:
        return None


def _parse_fact(fact: object, seen: set[str]) -> tuple[Fact | None, Finding | None]:
    """Validate one registry entry; return a Fact or the schema problem that rejects it."""
    where = REGISTRY.as_posix()
    if not isinstance(fact, dict) or any(key not in fact for key in REQUIRED_KEYS):
        label = fact.get("id") if isinstance(fact, dict) and isinstance(fact.get("id"), str) else "?"
        return None, Finding("SCHEMA", str(label), where, 0, "Missing required keys.")
    label = fact["id"]
    if not isinstance(label, str) or not label:
        return None, Finding("SCHEMA", "?", where, 0, "id must be a non-empty string.")
    if label in seen:
        return None, Finding("DUPLICATE_ID", label, where, 0, "ID listed twice.")
    seen.add(label)
    verified, review = _iso(fact["verified_on"]), _iso(fact["review_by"])
    if verified is None or review is None or review < verified:
        return None, Finding("SCHEMA", label, where, 0, "Invalid verified_on/review_by dates.")
    if not isinstance(fact["source_url"], str) or not fact["source_url"].startswith("https://"):
        return None, Finding("SCHEMA", label, where, 0, "source_url must be https.")
    patterns, allow_text = fact["stale_patterns"], fact.get("allow_context")
    required, token = fact.get("required_in", []), fact.get("required_token")
    if not isinstance(patterns, list) or not all(isinstance(item, str) for item in patterns):
        return None, Finding("SCHEMA", label, where, 0, "stale_patterns must be a list of strings.")
    if allow_text is not None and not isinstance(allow_text, str):
        return None, Finding("SCHEMA", label, where, 0, "allow_context must be a string.")
    if not isinstance(required, list) or not all(isinstance(item, str) for item in required) or (
        required and not isinstance(token, str)
    ):
        return None, Finding("SCHEMA", label, where, 0, "required_in needs a list of skills and a required_token.")
    try:
        compiled = tuple(re.compile(item) for item in patterns)
        allow = re.compile(allow_text) if allow_text else None
    except re.error as error:
        return None, Finding("SCHEMA", label, where, 0, f"Bad regex: {error}")
    return Fact(label, review, compiled, allow, tuple(required), token if isinstance(token, str) else None), None


def load_registry(repo: Path) -> tuple[list[Fact], list[Finding]]:
    """Parse and validate the registry; return usable facts plus schema findings."""
    try:
        data = json.loads((repo / REGISTRY).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        return [], [Finding("REGISTRY_UNREADABLE", "-", REGISTRY.as_posix(), 0, str(error))]
    entries = data.get("facts") if isinstance(data, dict) else None
    if not isinstance(entries, list) or not entries:
        return [], [Finding("REGISTRY_EMPTY", "-", REGISTRY.as_posix(), 0, "No facts listed.")]
    facts: list[Fact] = []
    problems: list[Finding] = []
    seen: set[str] = set()
    for entry in entries:
        fact, problem = _parse_fact(entry, seen)
        if fact is not None:
            facts.append(fact)
        if problem is not None:
            problems.append(problem)
    return facts, problems


def content_files(repo: Path) -> tuple[list[Path], list[str]]:
    files: set[Path] = set()
    skipped: set[str] = set()
    registry = (repo / REGISTRY).resolve()
    for pattern in SCAN_GLOBS:
        for path in repo.glob(pattern):
            if not path.is_file() or path.resolve() == registry:
                continue
            relative = path.relative_to(repo)
            if any(part in VENDOR_PARTS for part in relative.parts):
                skipped.add("/".join(relative.parts[:3]))
                continue
            files.add(path)
    return sorted(files), sorted(skipped)


def scan(repo: Path, facts: list[Fact], files: list[Path]) -> list[Finding]:
    findings: list[Finding] = []
    texts = {path: path.read_text(encoding="utf-8", errors="replace") for path in files}
    for fact in facts:
        for path, text in texts.items():
            for number, line in enumerate(text.splitlines(), start=1):
                if any(pattern.search(line) for pattern in fact.patterns) and not (fact.allow and fact.allow.search(line)):
                    findings.append(Finding("STALE_FACT", fact.id, path.relative_to(repo).as_posix(), number, line.strip()[:160]))
        for skill in fact.required_in:
            skill_text = "\n".join(text for path, text in texts.items() if path.relative_to(repo).parts[0] == skill)
            if fact.required_token and fact.required_token not in skill_text:
                findings.append(Finding("MISSING_REQUIRED_FACT", fact.id, skill, 0, f"{fact.required_token} not mentioned."))
    return findings


def check(repo: Path, today: date) -> dict[str, object]:
    facts, problems = load_registry(repo)
    overdue = [
        Finding("OVERDUE_REVIEW", fact.id, REGISTRY.as_posix(), 0, f"review_by {fact.review_by.isoformat()} has passed.")
        for fact in facts if fact.review_by < today
    ]
    files, skipped = content_files(repo)
    findings = problems + overdue + scan(repo, facts, files)
    return {
        "status": "PASS" if not findings else "FAIL",
        "facts": len(facts),
        "files_scanned": len(files),
        "skipped_vendored": skipped,
        "findings": [asdict(finding) for finding in findings],
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--repo", type=Path, default=Path("."))
    parser.add_argument("--today", type=date.fromisoformat, default=date.today())
    parser.add_argument("--json", type=Path)
    args = parser.parse_args(argv)
    report = check(args.repo.resolve(), args.today)
    if args.json:
        args.json.write_text(json.dumps(report, indent=2), encoding="utf-8")
    findings = report["findings"]
    count = len(findings) if isinstance(findings, list) else 0
    print(f"{report['status']}: {report['facts']} facts, {report['files_scanned']} files, {count} findings")
    for finding in findings if isinstance(findings, list) else []:
        print(f"  {finding['kind']:22} {finding['fact']:24} {finding['path']}:{finding['line']}  {finding['text']}")
    return 0 if report["status"] == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
