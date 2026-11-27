from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from copy import deepcopy
from pathlib import Path
from types import ModuleType
from typing import Any

SCRIPT_PATH = Path(__file__).resolve().parents[1] / "scripts" / "pmo_governance_engine.py"


def _load_module() -> ModuleType:
    spec = importlib.util.spec_from_file_location("pmo_governance_engine_under_test", SCRIPT_PATH)
    if spec is None or spec.loader is None:
        raise ImportError(f"Cannot load {SCRIPT_PATH}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


pmo = _load_module()
InvalidInput: type[ValueError] = sys.modules["shadow_input"].InvalidInput

WBS: dict[str, Any] = {
    "seed": 42,
    "monte_carlo_iterations": 3000,
    "tasks": [
        {"id": "T1", "name": "Discovery", "optimistic": 4, "most_likely": 5, "pessimistic": 9, "predecessors": []},
        {"id": "T2", "name": "Backend API", "optimistic": 8, "most_likely": 10, "pessimistic": 18, "predecessors": ["T1"]},
        {"id": "T3", "name": "Mobile UI", "optimistic": 7, "most_likely": 10, "pessimistic": 16, "predecessors": ["T1"]},
        {"id": "T4", "name": "UAT & Cutover", "optimistic": 3, "most_likely": 5, "pessimistic": 9, "predecessors": ["T2", "T3"]},
    ],
    "evm": {"bac": 1_000_000_000, "pv": 500_000_000, "ev": 450_000_000, "ac": 500_000_000},
}

CR_FLAGS = (
    "violates_signed_acceptance_criteria", "within_warranty_period", "required_for_signed_statutory_compliance",
    "listed_in_exclusion_register", "introduces_net_new_workflow_or_integration", "contract_clause_ambiguous",
)


def _run_cli(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run([sys.executable, "-B", str(SCRIPT_PATH), *args],
                          capture_output=True, text=True, timeout=60, check=False)


class ScheduleTests(unittest.TestCase):
    def test_cpm_critical_path_and_pert(self) -> None:
        res = pmo.analyze_schedule_and_evm(deepcopy(WBS))
        # T1 5.5 + T2 11 + T4 5.33 = 21.83; T3 (10.5) has 0.5 day float.
        self.assertEqual(res["deterministic_cpm_days"], 21.83)
        self.assertEqual(res["critical_path_ids"], ["T1", "T2", "T4"])
        t3 = next(t for t in res["tasks"] if t["id"] == "T3")
        self.assertEqual(t3["total_float"], 0.5)
        self.assertFalse(t3["is_critical"])

    def test_monte_carlo_monotonic_reproducible_and_merge_bias(self) -> None:
        res = pmo.analyze_schedule_and_evm(deepcopy(WBS))
        mc = res["monte_carlo"]
        self.assertGreaterEqual(mc["p90_days"], mc["p80_days"])
        self.assertGreaterEqual(mc["p80_days"], mc["p50_days"])
        self.assertGreater(mc["p80_days"], res["deterministic_cpm_days"])
        self.assertEqual(pmo.analyze_schedule_and_evm(deepcopy(WBS)), res)

    def test_evm_ratios_exact(self) -> None:
        evm = pmo.analyze_schedule_and_evm(deepcopy(WBS))["evm"]
        self.assertEqual((evm["cpi"], evm["spi"]), (0.9, 0.9))
        self.assertEqual((evm["cv"], evm["sv"]), (-50_000_000, -50_000_000))
        self.assertEqual(evm["eac"], round(1_000_000_000 / 0.9, 2))

    def test_evm_undefined_ratios_not_reported_healthy(self) -> None:
        # Previously ac=0 / pv=0 reported CPI/SPI 1.0 (on plan) and ev=0 reported EAC = BAC.
        for evm, field in (({"bac": 100, "pv": 50, "ev": 40, "ac": 0}, "cpi"),
                           ({"bac": 100, "pv": 0, "ev": 40, "ac": 50}, "spi"),
                           ({"bac": 100, "pv": 50, "ev": 0, "ac": 50}, "eac")):
            with self.subTest(field=field):
                out = pmo.analyze_schedule_and_evm(dict(deepcopy(WBS), evm=evm))["evm"]
                self.assertIsNone(out[field])

    def test_evm_wrong_types_rejected(self) -> None:
        for value in ("500", True, None, float("nan")):
            evm = dict(WBS["evm"], ac=value)
            with self.subTest(value=repr(value)), self.assertRaises(ValueError):
                pmo.analyze_schedule_and_evm(dict(deepcopy(WBS), evm=evm))

    def test_empty_or_missing_tasks_rejected(self) -> None:
        for spec in ({}, {"tasks": []}):
            with self.subTest(spec=spec), self.assertRaises(ValueError):
                pmo.analyze_schedule_and_evm(spec)

    def test_cycle_and_unknown_predecessor_rejected(self) -> None:
        cycle = {"tasks": [
            {"id": "A", "optimistic": 1, "most_likely": 2, "pessimistic": 3, "predecessors": ["B"]},
            {"id": "B", "optimistic": 1, "most_likely": 2, "pessimistic": 3, "predecessors": ["A"]},
        ]}
        unknown = {"tasks": [{"id": "A", "optimistic": 1, "most_likely": 2, "pessimistic": 3, "predecessors": ["Z"]}]}
        for spec in (cycle, unknown):
            with self.assertRaises(ValueError):
                pmo.analyze_schedule_and_evm(spec)

    def test_invalid_pert_values_rejected(self) -> None:
        for o, m, p in ((10, 5, 12), (1, 5, 4), (-1, 2, 3), ("1", 2, 3), (True, 2, 3), (1, None, 3)):
            spec = {"tasks": [{"id": "A", "optimistic": o, "most_likely": m, "pessimistic": p, "predecessors": []}]}
            with self.subTest(o=o, m=m, p=p), self.assertRaises(ValueError):
                pmo.analyze_schedule_and_evm(spec)

    def test_non_positive_iterations_rejected(self) -> None:
        for iterations in (0, -5):
            with self.subTest(iterations=iterations), self.assertRaises(ValueError):
                pmo.analyze_schedule_and_evm(dict(deepcopy(WBS), monte_carlo_iterations=iterations))


class ChangeRequestTests(unittest.TestCase):
    def test_net_new_is_paid_cr_candidate_with_human_gate(self) -> None:
        res = pmo.evaluate_change_request({"cr_id": "CR-101", "introduces_net_new_workflow_or_integration": True})
        self.assertEqual(res["proposed_classification"], "PAID_CHANGE_REQUEST_CANDIDATE")
        self.assertIs(res["requires_human_approval"], True)
        self.assertIs(res["is_binding_legal_verdict"], False)

    def test_exclusion_register_overrides(self) -> None:
        res = pmo.evaluate_change_request({"listed_in_exclusion_register": True, "violates_signed_acceptance_criteria": True})
        self.assertEqual(res["proposed_classification"], "PAID_CHANGE_REQUEST_CANDIDATE")

    def test_signed_ac_violation_is_defect(self) -> None:
        res = pmo.evaluate_change_request({"violates_signed_acceptance_criteria": True, "within_warranty_period": True})
        self.assertEqual(res["proposed_classification"], "IN_SCOPE_DEFECT")
        net_new_bug = pmo.evaluate_change_request({"violates_signed_acceptance_criteria": True,
                                                   "introduces_net_new_workflow_or_integration": True})
        self.assertNotEqual(net_new_bug["proposed_classification"], "IN_SCOPE_DEFECT")

    def test_statutory_vs_ambiguous(self) -> None:
        statutory = pmo.evaluate_change_request({"required_for_signed_statutory_compliance": True})
        self.assertEqual(statutory["proposed_classification"], "IMPLICIT_STATUTORY_OR_BASELINE_OBLIGATION")
        ambiguous = pmo.evaluate_change_request({"required_for_signed_statutory_compliance": True, "contract_clause_ambiguous": True})
        self.assertEqual(ambiguous["proposed_classification"], "SCOPE_CLARIFICATION_REVIEW")

    def test_empty_request_routes_to_clarification(self) -> None:
        self.assertEqual(pmo.evaluate_change_request({})["proposed_classification"], "SCOPE_CLARIFICATION_REVIEW")

    def test_string_and_wrong_type_flags_rejected(self) -> None:
        for flag in CR_FLAGS:
            for value in ("true", "false", 1, None, []):
                with self.subTest(flag=flag, value=repr(value)), self.assertRaises(InvalidInput):
                    pmo.evaluate_change_request({flag: value})


class CliTests(unittest.TestCase):
    def test_self_test_passes(self) -> None:
        result = _run_cli("--self-test")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertTrue(json.loads(result.stdout)["all_passed"])

    def test_string_flag_exits_invalid_input(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "cr.json"
            path.write_text(json.dumps({"listed_in_exclusion_register": "false"}), encoding="utf-8")
            result = _run_cli("--evaluate-cr", str(path))
        self.assertEqual(result.returncode, 2, result.stdout + result.stderr)
        self.assertEqual(json.loads(result.stdout)["status"], "INVALID_INPUT")


if __name__ == "__main__":
    unittest.main()
