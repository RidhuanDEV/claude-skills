from __future__ import annotations

import ast
import importlib.util
from pathlib import Path
import sys
import tempfile
import unittest

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "mutation_smoke.py"
_spec = importlib.util.spec_from_file_location("mutation_smoke", SCRIPT)
assert _spec is not None and _spec.loader is not None
mutation_smoke = importlib.util.module_from_spec(_spec)
sys.modules["mutation_smoke"] = mutation_smoke  # dataclasses resolve their module through sys.modules
_spec.loader.exec_module(mutation_smoke)


def make_skill(root: Path, script: str, test: str) -> None:
    (root / "skill" / "scripts").mkdir(parents=True)
    (root / "skill" / "tests").mkdir()
    (root / "skill" / "scripts" / "gate.py").write_text(script, encoding="utf-8")
    (root / "skill" / "tests" / "test_gate.py").write_text(test, encoding="utf-8")


class MutationSmokeTests(unittest.TestCase):
    def test_each_site_yields_exactly_one_mutation(self) -> None:
        source = "def f(a, b):\n    return a == 1 and not b\n"
        mutants = {mutation_smoke._mutate(source, site) for site in mutation_smoke._sites(ast.parse(source))}
        self.assertEqual(mutants, {
            "def f(a, b):\n    return a != 1 and (not b)",
            "def f(a, b):\n    return a == 1 and b",
            "def f(a, b):\n    return a == 1 or not b",
        })

    def test_name_main_guard_is_never_mutated(self) -> None:
        source = "if __name__ == '__main__':\n    pass\n"
        self.assertEqual(mutation_smoke._sites(ast.parse(source)), [])

    def test_real_tests_kill_mutants_and_theater_does_not(self) -> None:
        self.assertEqual(mutation_smoke.self_test(), [])

    def test_baseline_failure_is_reported_and_script_restored(self) -> None:
        script = "def gate(x):\n    return x is True\n"
        failing = "import unittest\nclass T(unittest.TestCase):\n    def test_x(self):\n        self.fail('broken')\n"
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            make_skill(root, script, failing)
            report = mutation_smoke.smoke_skill(root, "skill", 5, 60)
            self.assertEqual(report["status"], "BASELINE_FAIL")
            self.assertEqual((root / "skill" / "scripts" / "gate.py").read_text(encoding="utf-8"), script)

    def test_skill_without_python_scripts_is_not_applicable(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "skill" / "tests").mkdir(parents=True)
            self.assertEqual(mutation_smoke.smoke_skill(root, "skill", 5, 60)["status"], "NO_PYTHON_SCRIPTS")


if __name__ == "__main__":
    unittest.main()
