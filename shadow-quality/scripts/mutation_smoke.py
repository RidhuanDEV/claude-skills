"""Mutation smoke test: do a skill's tests fail when its shipped Python scripts are subtly broken?

Usage:
    python mutation_smoke.py --repo . --skill shadow-auth [--max-mutants 12] [--timeout 120]
    python mutation_smoke.py --repo . --all [--max-mutants 8] [--json report.json]
    python mutation_smoke.py --self-test

For each script in <skill>/scripts/*.py the tool:
  1. rewrites the file through ast.unparse and checks that the skill's tests still pass (baseline);
  2. applies one small AST mutation at a time (comparison flips, and/or swap, dropped `not`,
     True/False swap), runs `python -m unittest discover -s <skill>/tests`, and records whether
     the suite failed (killed) or still passed (survived);
  3. restores the original bytes in try/finally and verifies the SHA-256.

Standard library only. It edits files in place, so run it on a clean working copy with no other
process writing to the skill folder. It never touches files outside <skill>/scripts.
"""

from __future__ import annotations

import argparse
import ast
from dataclasses import asdict, dataclass, field
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile

COMPARE_SWAPS: dict[type[ast.cmpop], type[ast.cmpop]] = {
    ast.Eq: ast.NotEq, ast.NotEq: ast.Eq, ast.Lt: ast.GtE, ast.GtE: ast.Lt, ast.Gt: ast.LtE, ast.LtE: ast.Gt,
    ast.Is: ast.IsNot, ast.IsNot: ast.Is, ast.In: ast.NotIn, ast.NotIn: ast.In,
}


@dataclass(frozen=True)
class Site:
    kind: str
    index: int
    line: int


@dataclass
class ScriptResult:
    script: str
    baseline: str
    mutants: int = 0
    killed: int = 0
    survived: list[str] = field(default_factory=list)


def _kind(node: ast.AST) -> str | None:
    """Classify a node as a mutation site; `__name__` guards are never mutated."""
    if isinstance(node, ast.Compare) and len(node.ops) == 1 and type(node.ops[0]) in COMPARE_SWAPS:
        return None if isinstance(node.left, ast.Name) and node.left.id == "__name__" else "compare"
    if isinstance(node, ast.BoolOp):
        return "boolop"
    if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.Not):
        return "not"
    if isinstance(node, ast.Constant) and isinstance(node.value, bool):
        return "bool"
    return None


def _post_order(node: ast.AST) -> list[ast.AST]:
    """Children before parents: the same order in which _Mutator decides on each node."""
    ordered: list[ast.AST] = []
    for child in ast.iter_child_nodes(node):
        ordered.extend(_post_order(child))
    ordered.append(node)
    return ordered


def _sites(tree: ast.AST) -> list[Site]:
    sites: list[Site] = []
    counters: dict[str, int] = {}
    for node in _post_order(tree):
        kind = _kind(node)
        if kind:
            sites.append(Site(kind, counters.get(kind, 0), getattr(node, "lineno", 0)))
            counters[kind] = counters.get(kind, 0) + 1
    return sites


class _Mutator(ast.NodeTransformer):
    """Apply exactly one mutation: the site-th node of the site's kind in post-order."""

    def __init__(self, site: Site) -> None:
        self.site = site
        self.seen: dict[str, int] = {}

    def _hit(self, node: ast.AST) -> bool:
        kind = _kind(node)
        if kind is None:
            return False
        index = self.seen.get(kind, 0)
        self.seen[kind] = index + 1
        return kind == self.site.kind and index == self.site.index

    def visit(self, node: ast.AST) -> ast.AST:
        node = self.generic_visit(node)
        if not self._hit(node):
            return node
        if isinstance(node, ast.Compare):
            node.ops = [COMPARE_SWAPS[type(node.ops[0])]()]
            return node
        if isinstance(node, ast.BoolOp):
            node.op = ast.Or() if isinstance(node.op, ast.And) else ast.And()
            return node
        if isinstance(node, ast.UnaryOp):
            return node.operand
        if isinstance(node, ast.Constant):
            return ast.copy_location(ast.Constant(value=not node.value), node)
        return node


def _mutate(source: str, site: Site) -> str:
    """Return the source with exactly one mutation applied at the given site."""
    tree = ast.parse(source)
    return ast.unparse(ast.fix_missing_locations(_Mutator(site).visit(tree)))


def _run_tests(repo: Path, skill: str, timeout: int) -> bool:
    """Return True when the skill's unittest suite passes."""
    try:
        completed = subprocess.run(
            [sys.executable, "-B", "-m", "unittest", "discover", "-s", str(repo / skill / "tests")],
            cwd=repo, capture_output=True, text=True, timeout=timeout, check=False,
        )
    except subprocess.TimeoutExpired:
        return False
    return completed.returncode == 0


def _spread(sites: list[Site], limit: int) -> list[Site]:
    if len(sites) <= limit:
        return sites
    step = len(sites) / limit
    return [sites[int(position * step)] for position in range(limit)]


def smoke_script(repo: Path, skill: str, script: Path, max_mutants: int, timeout: int) -> ScriptResult:
    original = script.read_bytes()
    digest = hashlib.sha256(original).hexdigest()
    source = original.decode("utf-8")
    result = ScriptResult(script=script.relative_to(repo).as_posix(), baseline="PASS")
    try:
        tree = ast.parse(source)
        script.write_text(ast.unparse(tree), encoding="utf-8")
        if not _run_tests(repo, skill, timeout):
            result.baseline = "FAIL"
            return result
        for site in _spread(_sites(tree), max_mutants):
            try:
                mutant = _mutate(source, site)
            except (KeyError, SyntaxError, ValueError):
                continue
            script.write_text(mutant, encoding="utf-8")
            result.mutants += 1
            if _run_tests(repo, skill, timeout):
                result.survived.append(f"{site.kind}@line{site.line}")
            else:
                result.killed += 1
    finally:
        script.write_bytes(original)
        if hashlib.sha256(script.read_bytes()).hexdigest() != digest:
            raise RuntimeError(f"Failed to restore {script}")
    return result


def smoke_skill(repo: Path, skill: str, max_mutants: int, timeout: int) -> dict[str, object]:
    scripts = sorted((repo / skill / "scripts").glob("*.py"))
    if not (repo / skill / "tests").is_dir():
        return {"skill": skill, "status": "NO_TESTS", "scripts": []}
    if not scripts:
        return {"skill": skill, "status": "NO_PYTHON_SCRIPTS", "scripts": []}
    results = [smoke_script(repo, skill, script, max_mutants, timeout) for script in scripts]
    mutants = sum(item.mutants for item in results)
    killed = sum(item.killed for item in results)
    baseline_failed = [item.script for item in results if item.baseline == "FAIL"]
    if baseline_failed:
        status = "BASELINE_FAIL"
    elif mutants == 0:
        status = "NO_MUTANTS"
    else:
        status = "PASS" if killed >= 1 else "FAIL"
    return {
        "skill": skill, "status": status, "mutants": mutants, "killed": killed,
        "score": round(killed / mutants, 3) if mutants else None,
        "scripts": [asdict(item) for item in results],
    }


SELF_TEST_SCRIPT = '''def gate(evidence):
    if not isinstance(evidence, dict):
        return False
    return evidence.get("verified") is True and evidence.get("count", 0) > 0
'''
SELF_TEST_GOOD = '''import importlib.util, unittest
from pathlib import Path
spec = importlib.util.spec_from_file_location("gate", Path(__file__).resolve().parents[1] / "scripts" / "gate.py")
gate = importlib.util.module_from_spec(spec); spec.loader.exec_module(gate)
class T(unittest.TestCase):
    def test_gate(self):
        self.assertTrue(gate.gate({"verified": True, "count": 1}))
        self.assertFalse(gate.gate({"verified": "true", "count": 1}))
        self.assertFalse(gate.gate({"verified": True, "count": 0}))
        self.assertFalse(gate.gate([]))
'''
SELF_TEST_THEATER = '''import unittest
class T(unittest.TestCase):
    def test_nothing(self):
        self.assertTrue(True)
'''


def self_test() -> list[str]:
    failures: list[str] = []
    for name, test_source, expect in (("good", SELF_TEST_GOOD, "PASS"), ("theater", SELF_TEST_THEATER, "FAIL")):
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            (repo / "skill" / "scripts").mkdir(parents=True)
            (repo / "skill" / "tests").mkdir()
            (repo / "skill" / "scripts" / "gate.py").write_text(SELF_TEST_SCRIPT, encoding="utf-8")
            (repo / "skill" / "tests" / "test_gate.py").write_text(test_source, encoding="utf-8")
            report = smoke_skill(repo, "skill", 20, 60)
            if report["status"] != expect:
                failures.append(f"{name}: expected {expect}, got {report['status']} ({report.get('killed')}/{report.get('mutants')})")
            if (repo / "skill" / "scripts" / "gate.py").read_text(encoding="utf-8") != SELF_TEST_SCRIPT:
                failures.append(f"{name}: script not restored")
    return failures


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--repo", type=Path, default=Path("."))
    target = parser.add_mutually_exclusive_group(required=True)
    target.add_argument("--skill")
    target.add_argument("--all", action="store_true")
    target.add_argument("--self-test", action="store_true")
    parser.add_argument("--max-mutants", type=int, default=12)
    parser.add_argument("--timeout", type=int, default=120)
    parser.add_argument("--json", type=Path)
    args = parser.parse_args(argv)
    if args.self_test:
        failures = self_test()
        print(json.dumps({"self_test": "FAIL" if failures else "PASS", "failures": failures}, indent=2))
        return 1 if failures else 0
    repo = args.repo.resolve()
    skills = [args.skill] if args.skill else sorted(path.parent.name for path in repo.glob("*/SKILL.md"))
    reports = []
    for skill in skills:
        report = smoke_skill(repo, skill, args.max_mutants, args.timeout)
        reports.append(report)
        print(f"{skill:28} {report['status']:18} killed {report.get('killed', '-')}/{report.get('mutants', '-')}", flush=True)
    if args.json:
        args.json.write_text(json.dumps(reports, indent=2), encoding="utf-8")
    failing = [item["skill"] for item in reports if item["status"] in {"FAIL", "BASELINE_FAIL"}]
    return 1 if failing else 0


if __name__ == "__main__":
    sys.exit(main())
