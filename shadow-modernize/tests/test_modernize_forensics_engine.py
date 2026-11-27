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

SCRIPT_PATH = Path(__file__).resolve().parents[1] / "scripts" / "modernize_forensics_engine.py"


def _load_module() -> ModuleType:
    spec = importlib.util.spec_from_file_location("modernize_forensics_engine_under_test", SCRIPT_PATH)
    if spec is None or spec.loader is None:
        raise ImportError(f"Cannot load {SCRIPT_PATH}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


mod = _load_module()

STABLE_LEGACY: dict[str, Any] = {
    "system_id": "SYS-CORE-LEDGER",
    "business_rule_complexity": "HIGH",
    "production_stability_high": True,
    "has_automated_tests": False,
    "horizon_years": 3,
    "annual_legacy_ops_cost": 1_000_000_000,
    "strangler_build_cost": 1_800_000_000,
    "rewrite_build_cost": 3_200_000_000,
    "encapsulate_build_cost": 900_000_000,
    "risk_dimensions": {
        "code_dependencies": {"score": 4.0, "confidence": "HIGH", "evidence_refs": ["EVD-CODE-1"]},
        "architecture_coupling": {"score": 4.0, "confidence": "HIGH", "evidence_refs": ["EVD-ARCH-1"]},
        "data_integrity": {"score": 3.0, "confidence": "HIGH", "evidence_refs": ["EVD-DB-1"]},
        "operations_slo": {"score": 1.5, "confidence": "HIGH", "evidence_refs": ["EVD-OPS-1"]},
        "security_supply_chain": {"score": 3.5, "confidence": "MEDIUM", "evidence_refs": ["EVD-SEC-1"]},
        "business_criticality": {"score": 5.0, "confidence": "HIGH", "evidence_refs": ["EVD-BIZ-1"]},
    },
}

COST_FIELDS = ("annual_legacy_ops_cost", "rewrite_build_cost", "strangler_build_cost", "encapsulate_build_cost", "horizon_years")


def _tco(result: dict[str, Any], strategy: str) -> float:
    return next(o["total_risk_adjusted_tco"] for o in result["options_tco_ranked"] if o["strategy"] == strategy)


def _run_cli(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run([sys.executable, "-B", str(SCRIPT_PATH), *args],
                          capture_output=True, text=True, timeout=60, check=False)


class EvaluateOptionsTests(unittest.TestCase):
    def test_stable_rule_heavy_core_avoids_blind_rewrite(self) -> None:
        res = mod.evaluate_modernization_options(deepcopy(STABLE_LEGACY))
        self.assertEqual(res["status"], "EVALUATED")
        self.assertNotEqual(res["recommended_strategy"], "FULL_REWRITE")
        self.assertTrue(res["archaeology_prerequisite_required"])
        self.assertEqual(len(res["risk_vector"]), 6)
        self.assertEqual(res["low_confidence_dimensions"], [])

    def test_recommendation_is_cheapest_option(self) -> None:
        res = mod.evaluate_modernization_options(deepcopy(STABLE_LEGACY))
        totals = [o["total_risk_adjusted_tco"] for o in res["options_tco_ranked"]]
        self.assertEqual(totals, sorted(totals))
        self.assertEqual(res["recommended_strategy"], res["options_tco_ranked"][0]["strategy"])
        cheap_rewrite = dict(deepcopy(STABLE_LEGACY), rewrite_build_cost=10, business_rule_complexity="LOW")
        self.assertEqual(mod.evaluate_modernization_options(cheap_rewrite)["recommended_strategy"], "FULL_REWRITE")

    def test_tco_components_reconcile(self) -> None:
        res = mod.evaluate_modernization_options(deepcopy(STABLE_LEGACY))
        for opt in res["options_tco_ranked"]:
            with self.subTest(strategy=opt["strategy"]):
                total = round(opt["build_cost"] + opt["coexistence_and_ops_cost"] + opt["risk_adjusted_penalty"], 2)
                self.assertEqual(total, opt["total_risk_adjusted_tco"])

    def test_higher_rewrite_cost_raises_rewrite_tco(self) -> None:
        base = mod.evaluate_modernization_options(deepcopy(STABLE_LEGACY))
        exp = mod.evaluate_modernization_options(dict(deepcopy(STABLE_LEGACY), rewrite_build_cost=5_000_000_000))
        self.assertGreater(_tco(exp, "FULL_REWRITE"), _tco(base, "FULL_REWRITE"))

    def test_low_confidence_dimension_surfaced(self) -> None:
        spec = deepcopy(STABLE_LEGACY)
        spec["risk_dimensions"]["operations_slo"] = {"score": 2.0, "confidence": "LOW", "evidence_refs": []}
        self.assertIn("operations_slo", mod.evaluate_modernization_options(spec)["low_confidence_dimensions"])

    def test_custom_weights_shift_composite_risk(self) -> None:
        spec = deepcopy(STABLE_LEGACY)
        spec["dimension_weights"] = {d: 0.0 for d in spec["risk_dimensions"]}
        spec["dimension_weights"]["operations_slo"] = 1.0
        self.assertEqual(mod.evaluate_modernization_options(spec)["composite_reference_risk_0_5"], 1.5)

    def test_missing_cost_inputs_fail_closed(self) -> None:
        # Previously missing costs fell back to hidden Rp defaults and still ranked a strategy.
        for field in COST_FIELDS:
            spec = deepcopy(STABLE_LEGACY)
            del spec[field]
            with self.subTest(field=field):
                res = mod.evaluate_modernization_options(spec)
                self.assertEqual(res["status"], "INSUFFICIENT_EVIDENCE")
                self.assertIsNone(res["recommended_strategy"])
                self.assertEqual(res["missing_cost_inputs"], [field])
                self.assertNotIn("options_tco_ranked", res)

    def test_partial_evidence_without_costs_fails_closed(self) -> None:
        res = mod.evaluate_modernization_options({"risk_dimensions": {"operations_slo": {"score": 2.0, "evidence_refs": ["E1"]}}})
        self.assertEqual(res["status"], "INSUFFICIENT_EVIDENCE")
        self.assertIsNone(res["recommended_strategy"])
        self.assertEqual(len(res["missing_risk_dimensions"]), 5)
        self.assertEqual(set(res["missing_cost_inputs"]), set(COST_FIELDS))

    def test_missing_weighted_dimension_fails_closed(self) -> None:
        spec = deepcopy(STABLE_LEGACY)
        del spec["risk_dimensions"]["security_supply_chain"]
        res = mod.evaluate_modernization_options(spec)
        self.assertEqual(res["status"], "INSUFFICIENT_EVIDENCE")
        self.assertEqual(res["missing_risk_dimensions"], ["security_supply_chain"])
        spec["dimension_weights"] = {d: (0.0 if d == "security_supply_chain" else 0.2) for d in STABLE_LEGACY["risk_dimensions"]}
        self.assertEqual(mod.evaluate_modernization_options(spec)["status"], "EVALUATED")

    def test_empty_or_evidence_free_input_rejected(self) -> None:
        for spec in ({}, {"risk_dimensions": {"operations_slo": {"evidence_refs": ["E1"]}}},
                     {"risk_dimensions": {"operations_slo": {"score": 2.0, "evidence_refs": []}}}):
            with self.subTest(spec=spec), self.assertRaises(mod.InvalidInput):
                mod.evaluate_modernization_options(spec)

    def test_wrong_type_cost_inputs_rejected(self) -> None:
        for field, value in (("rewrite_build_cost", "3000000000"), ("rewrite_build_cost", True), ("rewrite_build_cost", 0),
                             ("annual_legacy_ops_cost", -1), ("annual_legacy_ops_cost", float("inf")),
                             ("horizon_years", "3"), ("horizon_years", 3.5), ("horizon_years", True), ("horizon_years", 0)):
            with self.subTest(field=field, value=repr(value)), self.assertRaises(mod.InvalidInput):
                mod.evaluate_modernization_options(dict(deepcopy(STABLE_LEGACY), **{field: value}))

    def test_string_flags_rejected(self) -> None:
        for field in ("production_stability_high", "has_automated_tests"):
            for value in ("false", "true", 0, None):
                with self.subTest(field=field, value=repr(value)), self.assertRaises(mod.InvalidInput):
                    mod.evaluate_modernization_options(dict(deepcopy(STABLE_LEGACY), **{field: value}))

    def test_wrong_type_risk_entries_rejected(self) -> None:
        for dims in ("not-a-dict", {"operations_slo": "4"}, {"operations_slo": {"score": "4", "evidence_refs": ["E"]}},
                     {"operations_slo": {"score": 6, "evidence_refs": ["E"]}}, {"operations_slo": {"score": 2, "evidence_refs": [" "]}}):
            spec = deepcopy(STABLE_LEGACY)
            spec["risk_dimensions"] = dims if isinstance(dims, str) else {**spec["risk_dimensions"], **dims}
            with self.subTest(dims=dims), self.assertRaises(mod.InvalidInput):
                mod.evaluate_modernization_options(spec)

    def test_tests_present_lifts_archaeology_guard(self) -> None:
        res = mod.evaluate_modernization_options(dict(deepcopy(STABLE_LEGACY), has_automated_tests=True))
        self.assertFalse(res["archaeology_prerequisite_required"])


class ScanRepoTests(unittest.TestCase):
    def test_scan_detects_signals(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root / "package.json").write_text("{}", encoding="utf-8")
            (root / ".github" / "workflows").mkdir(parents=True)
            (root / ".github" / "workflows" / "ci.yml").write_text("on: push", encoding="utf-8")
            (root / "db").mkdir()
            (root / "db" / "001.sql").write_text("select 1;", encoding="utf-8")
            (root / "node_modules").mkdir()
            (root / "node_modules" / "package.json").write_text("{}", encoding="utf-8")
            res = mod.scan_repo_forensics(root)
        self.assertEqual(res["method"], "read_only_static_scan")
        self.assertEqual([m["path"] for m in res["manifests"]], ["package.json"])
        self.assertTrue(res["signals"]["has_ci_pipeline"])
        self.assertFalse(res["signals"]["has_automated_tests"])
        self.assertEqual(res["signals"]["migration_artifacts_count"], 1)
        self.assertGreaterEqual(len(res["limitations"]), 1)

    def test_missing_repo_raises(self) -> None:
        with tempfile.TemporaryDirectory() as folder, self.assertRaises(FileNotFoundError):
            mod.scan_repo_forensics(Path(folder) / "missing")


class CliTests(unittest.TestCase):
    def test_evaluate_exit_codes(self) -> None:
        partial = deepcopy(STABLE_LEGACY)
        del partial["rewrite_build_cost"]
        invalid = dict(deepcopy(STABLE_LEGACY), has_automated_tests="false")
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "profile.json"
            for spec, expected, status in ((STABLE_LEGACY, 0, "EVALUATED"), (partial, 1, "INSUFFICIENT_EVIDENCE"),
                                           (invalid, 2, "INVALID_INPUT"), ({}, 2, "INVALID_INPUT")):
                path.write_text(json.dumps(spec), encoding="utf-8")
                with self.subTest(status=status, expected=expected):
                    result = _run_cli("--evaluate-options", str(path))
                    self.assertEqual(result.returncode, expected, result.stdout + result.stderr)
                    self.assertEqual(json.loads(result.stdout)["status"], status)


if __name__ == "__main__":
    unittest.main()
