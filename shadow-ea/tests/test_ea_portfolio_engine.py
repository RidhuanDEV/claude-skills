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

SCRIPT_PATH = Path(__file__).resolve().parents[1] / "scripts" / "ea_portfolio_engine.py"


def _load_module() -> ModuleType:
    spec = importlib.util.spec_from_file_location("ea_portfolio_engine_under_test", SCRIPT_PATH)
    if spec is None or spec.loader is None:
        raise ImportError(f"Cannot load {SCRIPT_PATH}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


ea = _load_module()

ALL_DOMAINS = [
    "PROSES_BISNIS", "DATA_DAN_INFORMASI", "INFRASTRUKTUR_SPBE",
    "APLIKASI_SPBE", "KEAMANAN_SPBE", "LAYANAN_SPBE",
]

GOV_SPEC: dict[str, Any] = {
    "org_type": "GOVERNMENT_SPBE",
    "spbe_domains_covered": ALL_DOMAINS,
    "applications": [
        {"system_id": "SYS-SIMPEG-1", "name": "SIMPEG Pusat", "business_capability": "HR Management",
         "business_value": 4.5, "tech_health": 2.0, "data_owner": "BKD"},
        {"system_id": "SYS-SIMPEG-2", "name": "Absensi Silo", "business_capability": "HR Management",
         "business_value": 2.5, "tech_health": 1.5, "data_owner": "Unit B"},
        {"system_id": "SYS-PORTAL", "name": "Portal Layanan Publik", "business_capability": "Citizen Portal",
         "business_value": 4.8, "tech_health": 4.2, "data_owner": "Diskominfo"},
    ],
    "abb_sbb_gaps": [{"abb_id": "ABB-IAM-SSO", "candidate_sbb": "Keycloak OIDC HA"}],
}


def _quadrants(result: dict[str, Any]) -> dict[str, str]:
    return {c["system_id"]: c["time_quadrant"] for c in result["portfolio_time_catalog"]}


def _run_cli(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run([sys.executable, "-B", str(SCRIPT_PATH), *args],
                          capture_output=True, text=True, timeout=30, check=False)


class ClassifyTimeTests(unittest.TestCase):
    def test_quadrant_boundaries(self) -> None:
        self.assertEqual(ea.classify_time(3.5, 3.0), "INVEST")
        self.assertEqual(ea.classify_time(3.5, 2.99), "MIGRATE")
        self.assertEqual(ea.classify_time(3.49, 3.0), "TOLERATE")
        self.assertEqual(ea.classify_time(3.49, 2.99), "ELIMINATE")

    def test_redundant_duplicate_below_4_is_eliminated(self) -> None:
        self.assertEqual(ea.classify_time(3.9, 4.5, is_duplicate_redundant=True), "ELIMINATE")
        self.assertEqual(ea.classify_time(4.0, 4.5, is_duplicate_redundant=True), "INVEST")


class AnalyzePortfolioTests(unittest.TestCase):
    def test_complete_spbe_portfolio_passes_and_classifies(self) -> None:
        res = ea.analyze_portfolio(deepcopy(GOV_SPEC))
        self.assertTrue(res["valid"])
        self.assertEqual(_quadrants(res), {"SYS-SIMPEG-1": "MIGRATE", "SYS-SIMPEG-2": "ELIMINATE", "SYS-PORTAL": "INVEST"})
        self.assertEqual(len(res["duplicate_capability_groups"]), 1)
        self.assertEqual(res["traceable_findings"][0]["finding_id"], "EA-DUP-HR_MANAGEMENT")
        self.assertIn("shadow-modernize", res["traceable_findings"][0]["downstream_handoff"])

    def test_four_togaf_domains_fail_spbe(self) -> None:
        spec = deepcopy(GOV_SPEC)
        spec["spbe_domains_covered"] = ALL_DOMAINS[:4]
        res = ea.analyze_portfolio(spec)
        self.assertFalse(res["valid"])
        self.assertEqual(set(res["spbe_6_domain_validation"]["missing_domains"]), {"KEAMANAN_SPBE", "LAYANAN_SPBE"})

    def test_spbe_domains_wrong_type_or_missing_fail(self) -> None:
        for value in ("PROSES_BISNIS", [], None):
            spec = deepcopy(GOV_SPEC)
            if value is None:
                del spec["spbe_domains_covered"]
            else:
                spec["spbe_domains_covered"] = value
            with self.subTest(value=repr(value)):
                self.assertFalse(ea.analyze_portfolio(spec)["valid"])

    def test_unassigned_data_owner_fails_spbe(self) -> None:
        for owner in ("UNASSIGNED", " ", None, False):
            spec = deepcopy(GOV_SPEC)
            if owner is None:
                del spec["applications"][2]["data_owner"]
            else:
                spec["applications"][2]["data_owner"] = owner
            with self.subTest(owner=repr(owner)):
                res = ea.analyze_portfolio(spec)
                self.assertFalse(res["valid"])
                self.assertEqual(res["spbe_6_domain_validation"]["unassigned_data_owners"], ["SYS-PORTAL"])

    def test_general_enterprise_skips_spbe_and_has_no_false_duplicates(self) -> None:
        res = ea.analyze_portfolio({"org_type": "GENERAL_ENTERPRISE", "applications": [
            {"system_id": "SYS-ERP", "name": "ERP", "business_capability": "Finance", "business_value": 4.5, "tech_health": 4.0},
            {"system_id": "SYS-CRM", "name": "CRM", "business_capability": "Sales", "business_value": 3.0, "tech_health": 4.0},
        ]})
        self.assertTrue(res["valid"])
        self.assertFalse(res["spbe_6_domain_validation"]["required"])
        self.assertEqual(res["duplicate_capability_groups"], [])
        self.assertEqual(_quadrants(res), {"SYS-ERP": "INVEST", "SYS-CRM": "TOLERATE"})

    def test_abb_gap_requires_both_ids(self) -> None:
        for gap in ({"abb_id": "ABB-01"}, {"candidate_sbb": "Keycloak"}, {"abb_id": "", "candidate_sbb": "Keycloak"}):
            spec = deepcopy(GOV_SPEC)
            spec["abb_sbb_gaps"] = [gap]
            with self.subTest(gap=gap):
                res = ea.analyze_portfolio(spec)
                self.assertFalse(res["valid"])
                self.assertEqual(len(res["abb_sbb_errors"]), 1)

    def test_empty_or_wrong_type_applications_rejected(self) -> None:
        for apps in ([], None, "SYS-1", {"system_id": "SYS-1"}, ["SYS-1"]):
            spec: dict[str, Any] = {"org_type": "BUMN"}
            if apps is not None:
                spec["applications"] = apps
            with self.subTest(apps=repr(apps)), self.assertRaises(ValueError):
                ea.analyze_portfolio(spec)

    def test_missing_or_non_numeric_scores_rejected(self) -> None:
        # Previously a missing score silently defaulted to 3.0 and produced a TIME verdict.
        for field in ("business_value", "tech_health"):
            for value in (None, "4.5", "true", True, float("nan"), 0.5, 6):
                spec = deepcopy(GOV_SPEC)
                if value is None:
                    del spec["applications"][0][field]
                else:
                    spec["applications"][0][field] = value
                with self.subTest(field=field, value=repr(value)), self.assertRaises(ValueError):
                    ea.analyze_portfolio(spec)

    def test_missing_system_id_rejected(self) -> None:
        spec = deepcopy(GOV_SPEC)
        del spec["applications"][0]["system_id"]
        with self.assertRaises(ValueError):
            ea.analyze_portfolio(spec)


class CliTests(unittest.TestCase):
    def test_self_test_passes(self) -> None:
        result = _run_cli("--self-test")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertTrue(json.loads(result.stdout)["all_passed"])

    def test_analyze_exit_codes(self) -> None:
        bad = deepcopy(GOV_SPEC)
        bad["spbe_domains_covered"] = ALL_DOMAINS[:4]
        with tempfile.TemporaryDirectory() as folder:
            for spec, expected in ((GOV_SPEC, 0), (bad, 1)):
                path = Path(folder) / "portfolio.json"
                path.write_text(json.dumps(spec), encoding="utf-8")
                with self.subTest(expected=expected):
                    self.assertEqual(_run_cli("--analyze-portfolio", str(path)).returncode, expected)


if __name__ == "__main__":
    unittest.main()
