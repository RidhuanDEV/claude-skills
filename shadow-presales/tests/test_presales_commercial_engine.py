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

SCRIPT_PATH = Path(__file__).resolve().parents[1] / "scripts" / "presales_commercial_engine.py"


def _load_module() -> ModuleType:
    spec = importlib.util.spec_from_file_location("presales_commercial_engine_under_test", SCRIPT_PATH)
    if spec is None or spec.loader is None:
        raise ImportError(f"Cannot load {SCRIPT_PATH}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


ps = _load_module()

BASE_CAP: dict[str, Any] = {
    "target_cpu_utilization": 0.60,
    "ha_instances": 2,
    "db_row_bytes": 1024,
    "rows_per_year": 5_000_000,
    "retention_years": 5,
    "db_index_overhead_pct": 0.35,
    "db_wal_headroom_pct": 0.30,
    "workload_classes": [
        {"name": "api_read", "rps_baseline": 80.0, "cpu_service_demand_sec": 0.015, "avg_latency_sec": 0.04, "mem_mb_per_concurrent": 4.0},
        {"name": "tx_write", "rps_baseline": 20.0, "cpu_service_demand_sec": 0.045, "avg_latency_sec": 0.08, "mem_mb_per_concurrent": 8.0},
    ],
}

COMM_OK: dict[str, Any] = {
    "years": 3,
    "discount_rate": 0.08,
    "target_margin_pct": 0.20,
    "ppn_rate": 0.11,
    "personnel_items": [
        {"role": "Lead Architect", "qty": 1, "months": 6, "unit_rate": 35_000_000, "is_umkk_pdn": True},
        {"role": "Engineers", "qty": 2, "months": 6, "unit_rate": 20_000_000, "is_umkk_pdn": True},
    ],
    "infra_capex_items": [{"item": "Enterprise DB License", "qty": 1, "unit_price": 150_000_000, "is_umkk_pdn": False}],
    "support_capex_items": [{"item": "Local VAPT & Training", "qty": 1, "unit_price": 60_000_000, "is_umkk_pdn": True}],
    "annual_opex_items": [{"item": "Cloud Hosting", "annual_cost": 180_000_000, "annual_uplift_pct": 0.05, "fx_exposed": True}],
}


def _run_cli(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run([sys.executable, "-B", str(SCRIPT_PATH), *args],
                          capture_output=True, text=True, timeout=60, check=False)


class CapacityTests(unittest.TestCase):
    def test_three_scenarios_monotonic_with_db_sensitivity(self) -> None:
        res = ps.compute_capacity_scenarios(deepcopy(BASE_CAP))
        sc = res["scenarios"]
        for metric in ("total_vcpu", "total_ram_gb", "total_rps"):
            with self.subTest(metric=metric):
                self.assertGreaterEqual(sc["stress"][metric], sc["expected"][metric])
                self.assertGreaterEqual(sc["expected"][metric], sc["conservative"][metric])
        self.assertGreater(sc["stress"]["total_rps"], sc["conservative"]["total_rps"])
        db = res["database_storage"]
        self.assertGreater(db["sensitivity_plus_20pct_index_gb"], db["provisioned_db_gb"])

    def test_cpu_sizing_formula(self) -> None:
        spec = deepcopy(BASE_CAP)
        spec["workload_classes"] = [{"name": "cpu", "rps_baseline": 100.0, "cpu_service_demand_sec": 0.3}]
        sc = ps.compute_capacity_scenarios(spec)["scenarios"]
        # 100 rps * 0.3 s / 0.60 utilisation = 50 vCPU; stress x3 = 150.
        self.assertEqual(sc["conservative"]["total_vcpu"], 50)
        self.assertEqual(sc["stress"]["total_vcpu"], 150)

    def test_higher_rps_never_reduces_vcpu(self) -> None:
        base = ps.compute_capacity_scenarios(deepcopy(BASE_CAP))
        doubled = deepcopy(BASE_CAP)
        doubled["workload_classes"][0]["rps_baseline"] = 240.0
        self.assertGreaterEqual(ps.compute_capacity_scenarios(doubled)["scenarios"]["expected"]["total_vcpu"],
                                base["scenarios"]["expected"]["total_vcpu"])

    def test_utilization_bounds(self) -> None:
        for util in (0.99, 0.05, 0.86):
            with self.subTest(util=util), self.assertRaises(ValueError):
                ps.compute_capacity_scenarios(dict(deepcopy(BASE_CAP), target_cpu_utilization=util))
        ps.compute_capacity_scenarios(dict(deepcopy(BASE_CAP), target_cpu_utilization=0.85))

    def test_empty_or_wrong_type_workloads_rejected(self) -> None:
        for workloads in (None, [], "api_read", ["api_read"]):
            spec = deepcopy(BASE_CAP)
            if workloads is None:
                del spec["workload_classes"]
            else:
                spec["workload_classes"] = workloads
            with self.subTest(workloads=repr(workloads)), self.assertRaises(ValueError):
                ps.compute_capacity_scenarios(spec)

    def test_missing_negative_or_string_workload_numbers_rejected(self) -> None:
        # Previously negative/zero RPS silently produced minimum HA sizing.
        for field in ("rps_baseline", "cpu_service_demand_sec"):
            for value in (None, -80.0, 0, "80", True, float("nan")):
                spec = deepcopy(BASE_CAP)
                if value is None:
                    del spec["workload_classes"][0][field]
                else:
                    spec["workload_classes"][0][field] = value
                with self.subTest(field=field, value=repr(value)), self.assertRaises(ps.InvalidInput):
                    ps.compute_capacity_scenarios(spec)


class CommercialTests(unittest.TestCase):
    def test_tco_reconciles_and_meets_umkk(self) -> None:
        res = ps.compute_tco_and_commercial(deepcopy(COMM_OK))
        tco = res["tco_multi_year"]
        self.assertTrue(tco["numerical_reconciled"])
        self.assertLess(tco["npv_tco_pre_tax"], tco["total_nominal_tco_pre_tax"])
        self.assertEqual(res["document_nature"], "PROVIDER_COMMERCIAL_RAB_ESTIMATE_NOT_OFFICIAL_PPK_HPS")
        self.assertTrue(res["perpres_46_2025_checks"]["meets_40pct_umkk_target"])
        # UMKK = (210M + 240M + 60M) / 660M
        self.assertEqual(res["perpres_46_2025_checks"]["umkk_pdn_share"], round(510 / 660, 4))

    def test_capex_margin_and_ppn_arithmetic(self) -> None:
        capex = ps.compute_tco_and_commercial(deepcopy(COMM_OK))["capex_breakdown"]
        self.assertEqual(capex["direct_cost_subtotal"], 660_000_000)
        self.assertEqual(capex["provider_bid_pre_tax"], 825_000_000)
        self.assertEqual(capex["ppn_amount"], round(825_000_000 * 0.11, 2))
        self.assertEqual(capex["provider_bid_incl_ppn"], round(825_000_000 * 1.11, 2))

    def test_opex_escalation_and_fx_stress(self) -> None:
        sched = ps.compute_tco_and_commercial(deepcopy(COMM_OK))["tco_multi_year"]["annual_opex_schedule"]
        self.assertEqual([y["opex_pre_tax"] for y in sched], [180_000_000, 189_000_000, 198_450_000])
        self.assertEqual(sched[0]["opex_fx_stress"], 198_000_000)

    def test_low_umkk_share_flagged(self) -> None:
        spec = deepcopy(COMM_OK)
        for group in ("personnel_items", "support_capex_items"):
            for item in spec[group]:
                item["is_umkk_pdn"] = False
        self.assertFalse(ps.compute_tco_and_commercial(spec)["perpres_46_2025_checks"]["meets_40pct_umkk_target"])

    def test_hps_authority_claim_blocked(self) -> None:
        with self.assertRaises(PermissionError):
            ps.compute_tco_and_commercial(dict(deepcopy(COMM_OK), claim_official_hps_authority=True))

    def test_empty_or_zero_cost_input_fails_closed(self) -> None:
        for spec in ({}, {"annual_opex_items": [{"annual_cost": 0}]},
                     {"infra_capex_items": [{"qty": 0, "unit_price": 100}]},
                     {"personnel_items": [{"qty": 1, "months": 0, "unit_rate": 1}], "annual_opex_items": []}):
            with self.subTest(spec=spec), self.assertRaises(ps.InvalidInput):
                ps.compute_tco_and_commercial(spec)

    def test_wrong_type_cost_items_rejected(self) -> None:
        for field, items in (("infra_capex_items", "none"), ("infra_capex_items", [1]),
                             ("infra_capex_items", [{"qty": True, "unit_price": 100}]),
                             ("infra_capex_items", [{"qty": 1, "unit_price": -100}]),
                             ("infra_capex_items", [{"qty": 1}]),
                             ("annual_opex_items", [{"annual_cost": "abc"}]),
                             ("annual_opex_items", [{"annual_cost": "inf"}])):
            with self.subTest(field=field, items=items), self.assertRaises(ps.InvalidInput):
                ps.compute_tco_and_commercial(dict(deepcopy(COMM_OK), **{field: items}))

    def test_string_flags_rejected(self) -> None:
        for value in ("true", "false", 1, None):
            cases: list[dict[str, Any]] = [dict(deepcopy(COMM_OK), claim_official_hps_authority=value),
                                           dict(deepcopy(COMM_OK), apply_margin_to_capex=value)]
            opex = deepcopy(COMM_OK)
            opex["annual_opex_items"][0]["fx_exposed"] = value
            umkk = deepcopy(COMM_OK)
            umkk["infra_capex_items"][0]["is_umkk_pdn"] = value
            cases += [opex, umkk]
            for spec in cases:
                with self.subTest(value=repr(value)), self.assertRaises(ps.InvalidInput):
                    ps.compute_tco_and_commercial(spec)

    def test_years_bounds(self) -> None:
        for years in (0, 11):
            with self.subTest(years=years), self.assertRaises(ValueError):
                ps.compute_tco_and_commercial(dict(deepcopy(COMM_OK), years=years))


class CliTests(unittest.TestCase):
    def test_self_test_passes(self) -> None:
        result = _run_cli("--self-test")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertTrue(json.loads(result.stdout)["all_passed"])

    def test_model_tco_exit_codes(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "tco.json"
            for spec, expected in ((COMM_OK, 0), ({}, 2)):
                path.write_text(json.dumps(spec), encoding="utf-8")
                with self.subTest(expected=expected):
                    result = _run_cli("--model-tco", str(path))
                    self.assertEqual(result.returncode, expected, result.stdout + result.stderr)
                    if expected == 2:
                        self.assertEqual(json.loads(result.stdout)["status"], "INVALID_INPUT")


if __name__ == "__main__":
    unittest.main()
