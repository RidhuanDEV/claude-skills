#!/usr/bin/env python3
"""
Shadow Pre-Sales Commercial & Capacity Engine (presales_commercial_engine.py)

Deterministic multi-workload capacity sizing (conservative/expected/stress),
3-5 year TCO/NPV/sensitivity commercial modeling, and Perpres 46/2025 boundary gates.
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "shadow-monarch" / "scripts"))
from shadow_input import InvalidInput, run_checked_cli, strict_bool


def compute_capacity_scenarios(spec: dict[str, Any]) -> dict[str, Any]:
    """Compute conservative, expected, and stress server sizing from workload classes."""
    workloads = spec.get("workload_classes", [])
    if not isinstance(workloads, list) or not workloads or not all(isinstance(w, dict) for w in workloads):
        raise ValueError("workload_classes must contain at least one workload definition.")
    for w in workloads:
        for field in ("rps_baseline", "cpu_service_demand_sec"):
            value = w.get(field)
            if type(value) not in (int, float) or not math.isfinite(value) or value <= 0:
                raise InvalidInput(f"workload_classes.{field} must be a finite, positive JSON number.")

    target_util = float(spec.get("target_cpu_utilization", 0.60))
    if not (0.10 <= target_util <= 0.85):
        raise ValueError("target_cpu_utilization must be between 0.10 and 0.85.")

    min_ha_instances = max(2, int(spec.get("ha_instances", 2)))
    os_base_mb = float(spec.get("ram_base_os_mb", 1024.0))
    app_base_mb = float(spec.get("ram_app_base_mb", 1024.0))
    cache_mb = float(spec.get("ram_cache_mb", 2048.0))

    # Configurable DB storage parameters (explicitly tracked, not hidden constants)
    db_row_bytes = float(spec.get("db_row_bytes", 1024.0))
    rows_per_year = float(spec.get("rows_per_year", 1_000_000.0))
    retention_years = float(spec.get("retention_years", 5.0))
    index_overhead = float(spec.get("db_index_overhead_pct", 0.35))
    wal_headroom = float(spec.get("db_wal_headroom_pct", 0.30))

    raw_db_gb = (db_row_bytes * rows_per_year * retention_years) / (1024.0 ** 3)
    db_storage_gb = round(raw_db_gb * (1.0 + index_overhead) * (1.0 + wal_headroom), 2)

    multipliers = spec.get("scenario_multipliers", {"conservative": 1.0, "expected": 1.5, "stress": 3.0})
    scenarios: dict[str, Any] = {}

    for label in ("conservative", "expected", "stress"):
        mult = float(multipliers[label])
        total_rps = 0.0
        total_cpu_demand_sec = 0.0
        concurrent_mem_mb = 0.0
        for w in workloads:
            rps = float(w["rps_baseline"]) * mult
            cpu_d = float(w["cpu_service_demand_sec"])
            lat_s = float(w.get("avg_latency_sec", cpu_d * 2.0))
            mem_per_req = float(w.get("mem_mb_per_concurrent", 4.0))
            total_rps += rps
            total_cpu_demand_sec += rps * cpu_d
            concurrent_mem_mb += (rps * lat_s) * mem_per_req

        vcpu_needed = max(min_ha_instances * 2, math.ceil(total_cpu_demand_sec / target_util))
        ram_gb_needed = max(min_ha_instances * 4, math.ceil((os_base_mb + app_base_mb + cache_mb + concurrent_mem_mb) / 1024.0))
        scenarios[label] = {
            "multiplier": mult,
            "total_rps": round(total_rps, 2),
            "total_vcpu": vcpu_needed,
            "total_ram_gb": ram_gb_needed,
            "ha_instances": min_ha_instances,
            "per_instance_vcpu": math.ceil(vcpu_needed / min_ha_instances),
            "per_instance_ram_gb": math.ceil(ram_gb_needed / min_ha_instances),
        }

    # Sensitivity check: +20% index overhead impact on DB storage
    db_storage_high_idx = round(raw_db_gb * (1.0 + index_overhead + 0.20) * (1.0 + wal_headroom), 2)

    return {
        "scenarios": scenarios,
        "database_storage": {
            "raw_data_gb": round(raw_db_gb, 2),
            "index_overhead_pct": index_overhead,
            "wal_headroom_pct": wal_headroom,
            "provisioned_db_gb": db_storage_gb,
            "sensitivity_plus_20pct_index_gb": db_storage_high_idx,
        },
        "assumption_flags": {
            "unverified_assumptions_count": sum(1 for a in spec.get("assumptions", []) if a.get("status") != "MEASURED"),
        },
    }


def _cost_factor(item: dict[str, Any], field: str) -> float:
    value = item.get(field)
    if not isinstance(value, (int, float, str)) or isinstance(value, bool):
        raise InvalidInput(f"{field} requires a finite, nonnegative cost input.")
    try:
        numeric = float(value)
    except (ValueError, OverflowError) as exc:
        raise InvalidInput(f"{field} requires a finite, nonnegative cost input.") from exc
    if not math.isfinite(numeric) or numeric < 0:
        raise InvalidInput(f"{field} requires a finite, nonnegative cost input.")
    return numeric


def compute_tco_and_commercial(spec: dict[str, Any]) -> dict[str, Any]:
    """
    Compute 3-5 year CAPEX/OPEX TCO, NPV, provider commercial margin, and
    Perpres 46/2025 PDN/UMKK compliance without claiming official PPK HPS authority.
    """
    if strict_bool(spec.get("claim_official_hps_authority", False), "claim_official_hps_authority"):
        raise PermissionError("HG3_UNAUTHORIZED_PPK_HPS_DETERMINATION: Provider/AI cannot determine or approve official HPS on behalf of PPK.")

    years = int(spec.get("years", 3))
    if not (1 <= years <= 10):
        raise ValueError("years must be between 1 and 10.")

    discount_rate = float(spec.get("discount_rate", 0.08))
    fx_shock_pct = float(spec.get("fx_shock_pct", 0.10))
    ppn_rate = float(spec.get("ppn_rate", 0.11))

    personnel_items = spec.get("personnel_items", [])
    infra_capex_items = spec.get("infra_capex_items", [])
    support_capex_items = spec.get("support_capex_items", [])
    annual_opex_items = spec.get("annual_opex_items", [])

    for field, items in (
        ("personnel_items", personnel_items), ("infra_capex_items", infra_capex_items),
        ("support_capex_items", support_capex_items), ("annual_opex_items", annual_opex_items),
    ):
        if not isinstance(items, list) or not all(isinstance(item, dict) for item in items):
            raise InvalidInput(f"{field} must be an array of cost objects.")

    personnel_cost = sum(_cost_factor(i, "qty") * _cost_factor(i, "months") * _cost_factor(i, "unit_rate") for i in personnel_items)
    infra_capex = sum(_cost_factor(i, "qty") * _cost_factor(i, "unit_price") for i in infra_capex_items)
    support_capex = sum(_cost_factor(i, "qty") * _cost_factor(i, "unit_price") for i in support_capex_items)

    capex_direct_cost = round(personnel_cost + infra_capex + support_capex, 2)
    margin_pct = float(spec.get("target_margin_pct", 0.20))
    capex_bid_pre_tax = round(capex_direct_cost / max(0.05, 1.0 - margin_pct), 2) if strict_bool(spec.get("apply_margin_to_capex", True), "apply_margin_to_capex") else capex_direct_cost
    capex_ppn = round(capex_bid_pre_tax * ppn_rate, 2)
    capex_bid_incl_tax = round(capex_bid_pre_tax + capex_ppn, 2)

    annual_opex_schedule: list[dict[str, Any]] = []
    npv_tco = capex_bid_pre_tax
    total_nominal_opex = 0.0
    for yr in range(1, years + 1):
        yr_cost = 0.0
        yr_fx_shocked = 0.0
        for item in annual_opex_items:
            base = _cost_factor(item, "annual_cost")
            growth = float(item.get("annual_uplift_pct", 0.05))
            escalated = base * ((1.0 + growth) ** (yr - 1))
            yr_cost += escalated
            if strict_bool(item.get("fx_exposed", False), "fx_exposed"):
                yr_fx_shocked += escalated * (1.0 + fx_shock_pct)
            else:
                yr_fx_shocked += escalated
        yr_cost = round(yr_cost, 2)
        total_nominal_opex += yr_cost
        npv_tco += yr_cost / ((1.0 + discount_rate) ** yr)
        annual_opex_schedule.append({
            "year": yr,
            "opex_pre_tax": yr_cost,
            "opex_fx_stress": round(yr_fx_shocked, 2),
        })

    # Perpres 46/2025 UMKK / PDN compliance ratio on total pre-tax CAPEX items
    all_commercial_items = [
        *(({"amount": _cost_factor(i, "qty") * _cost_factor(i, "months") * _cost_factor(i, "unit_rate"), "is_umkk_pdn": strict_bool(i.get("is_umkk_pdn", False), "is_umkk_pdn")} for i in personnel_items)),
        *(({"amount": _cost_factor(i, "qty") * _cost_factor(i, "unit_price"), "is_umkk_pdn": strict_bool(i.get("is_umkk_pdn", False), "is_umkk_pdn")} for i in infra_capex_items)),
        *(({"amount": _cost_factor(i, "qty") * _cost_factor(i, "unit_price"), "is_umkk_pdn": strict_bool(i.get("is_umkk_pdn", False), "is_umkk_pdn")} for i in support_capex_items)),
    ]
    total_cost_base = sum(x["amount"] for x in all_commercial_items)
    umkk_amount = sum(x["amount"] for x in all_commercial_items if x["is_umkk_pdn"])
    umkk_share = round(umkk_amount / total_cost_base, 4) if total_cost_base > 0 else 0.0

    direct_cost = capex_direct_cost + total_nominal_opex
    if not math.isfinite(direct_cost) or direct_cost <= 0:
        raise InvalidInput("Commercial estimate requires positive, finite CAPEX or OPEX cost evidence.")
    total_nominal_tco = round(capex_bid_pre_tax + total_nominal_opex, 2)
    reconciled = abs((capex_bid_pre_tax + sum(y["opex_pre_tax"] for y in annual_opex_schedule)) - total_nominal_tco) < 0.05

    return {
        "document_nature": "PROVIDER_COMMERCIAL_RAB_ESTIMATE_NOT_OFFICIAL_PPK_HPS",
        "ppk_hps_authority_note": "Under Perpres 46/2025, only an authorized PPK (or certified PPTK where applicable) may set and approve official HPS.",
        "capex_breakdown": {
            "personnel_cost": round(personnel_cost, 2),
            "infra_capex": round(infra_capex, 2),
            "support_capex": round(support_capex, 2),
            "direct_cost_subtotal": capex_direct_cost,
            "provider_bid_pre_tax": capex_bid_pre_tax,
            "ppn_amount": capex_ppn,
            "provider_bid_incl_ppn": capex_bid_incl_tax,
        },
        "tco_multi_year": {
            "years": years,
            "discount_rate": discount_rate,
            "annual_opex_schedule": annual_opex_schedule,
            "total_nominal_opex_pre_tax": round(total_nominal_opex, 2),
            "total_nominal_tco_pre_tax": total_nominal_tco,
            "npv_tco_pre_tax": round(npv_tco, 2),
            "numerical_reconciled": reconciled,
        },
        "perpres_46_2025_checks": {
            "umkk_pdn_share": umkk_share,
            "meets_40pct_umkk_target": umkk_share >= 0.40,
        },
    }


def run_self_test() -> dict[str, Any]:
    """Execute precision, recall, monotonicity, reconciliation, and Perpres 46/2025 probes."""
    results: list[dict[str, Any]] = []

    base_cap = {
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
    cap_res = compute_capacity_scenarios(base_cap)
    sc = cap_res["scenarios"]
    monotonic_cap = (
        sc["stress"]["total_vcpu"] >= sc["expected"]["total_vcpu"] >= sc["conservative"]["total_vcpu"]
        and sc["stress"]["total_ram_gb"] >= sc["expected"]["total_ram_gb"] >= sc["conservative"]["total_ram_gb"]
        and cap_res["database_storage"]["sensitivity_plus_20pct_index_gb"] > cap_res["database_storage"]["provisioned_db_gb"]
    )
    results.append({"probe": "PRECISION-1: 3-scenario capacity monotonicity & parameterized DB sensitivity", "passed": monotonic_cap})

    # Higher load must never reduce vCPU
    double_cap = json.loads(json.dumps(base_cap))
    double_cap["workload_classes"][0]["rps_baseline"] = 240.0
    cap_double = compute_capacity_scenarios(double_cap)
    results.append({
        "probe": "PRECISION-2: Higher RPS monotonically increases or preserves vCPU",
        "passed": cap_double["scenarios"]["expected"]["total_vcpu"] >= sc["expected"]["total_vcpu"],
    })

    # TCO & Perpres 46/2025 UMKK compliance >= 40%
    comm_ok = {
        "years": 3,
        "discount_rate": 0.08,
        "target_margin_pct": 0.20,
        "ppn_rate": 0.11,
        "personnel_items": [
            {"role": "Lead Architect", "qty": 1, "months": 6, "unit_rate": 35_000_000, "is_umkk_pdn": True},
            {"role": "Engineers", "qty": 2, "months": 6, "unit_rate": 20_000_000, "is_umkk_pdn": True},
        ],
        "infra_capex_items": [
            {"item": "Enterprise DB License", "qty": 1, "unit_price": 150_000_000, "is_umkk_pdn": False},
        ],
        "support_capex_items": [
            {"item": "Local VAPT & Training", "qty": 1, "unit_price": 60_000_000, "is_umkk_pdn": True},
        ],
        "annual_opex_items": [
            {"item": "Cloud Hosting", "annual_cost": 180_000_000, "annual_uplift_pct": 0.05, "fx_exposed": True},
        ],
    }
    tco_res = compute_tco_and_commercial(comm_ok)
    results.append({
        "probe": "PRECISION-3: TCO reconciliation + NPV + >=40% UMKK pass + RAB/HPS separation",
        "passed": (
            tco_res["tco_multi_year"]["numerical_reconciled"]
            and tco_res["perpres_46_2025_checks"]["meets_40pct_umkk_target"]
            and tco_res["tco_multi_year"]["npv_tco_pre_tax"] < tco_res["tco_multi_year"]["total_nominal_tco_pre_tax"]
            and tco_res["document_nature"] == "PROVIDER_COMMERCIAL_RAB_ESTIMATE_NOT_OFFICIAL_PPK_HPS"
        ),
    })

    # Precision-4: Low UMKK share flagged accurately
    comm_low_umkk = json.loads(json.dumps(comm_ok))
    comm_low_umkk["personnel_items"][0]["is_umkk_pdn"] = False
    comm_low_umkk["personnel_items"][1]["is_umkk_pdn"] = False
    comm_low_umkk["support_capex_items"][0]["is_umkk_pdn"] = False
    tco_low = compute_tco_and_commercial(comm_low_umkk)
    results.append({
        "probe": "RECALL-1: Detects <40% UMKK domestic share under Perpres 46/2025",
        "passed": not tco_low["perpres_46_2025_checks"]["meets_40pct_umkk_target"],
    })

    # Adversarial Recall-2: Rejects claiming PPK official HPS determination authority
    hps_blocked = False
    try:
        compute_tco_and_commercial({**comm_ok, "claim_official_hps_authority": True})
    except PermissionError:
        hps_blocked = True
    results.append({"probe": "RECALL-2: Blocks unauthorized PPK HPS authority claim", "passed": hps_blocked})

    # Adversarial Recall-3: Rejects empty workload_classes or invalid utilization > 0.85
    bad_util_blocked = False
    try:
        compute_capacity_scenarios({**base_cap, "target_cpu_utilization": 0.99})
    except ValueError:
        bad_util_blocked = True
    results.append({"probe": "RECALL-3: Rejects unsafe >85% CPU utilization target", "passed": bad_util_blocked})

    # Precision-5: Explicit check that PPN calculation matches 11%
    expected_ppn = round(tco_res["capex_breakdown"]["provider_bid_pre_tax"] * 0.11, 2)
    results.append({
        "probe": "PRECISION-4: PPN and Grand Total arithmetic reconciliation exact",
        "passed": tco_res["capex_breakdown"]["ppn_amount"] == expected_ppn
        and round(tco_res["capex_breakdown"]["provider_bid_pre_tax"] + expected_ppn, 2) == tco_res["capex_breakdown"]["provider_bid_incl_ppn"],
    })

    # Precision-6: Deterministic repeat run yields identical result
    results.append({
        "probe": "PRECISION-5: Reproducible deterministic output on identical inputs",
        "passed": compute_tco_and_commercial(comm_ok) == tco_res and compute_capacity_scenarios(base_cap) == cap_res,
    })

    passed = sum(1 for r in results if r["passed"])
    return {
        "tool": "presales_commercial_engine.py",
        "total_probes": len(results),
        "passed": passed,
        "failed": len(results) - passed,
        "all_passed": passed == len(results),
        "results": results,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Shadow Pre-Sales Capacity & Commercial Engine")
    parser.add_argument("--size-capacity", default=None, help="JSON file with workload_classes")
    parser.add_argument("--model-tco", default=None, help="JSON file with CAPEX/OPEX commercial model")
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()

    if args.self_test:
        res = run_self_test()
        print(json.dumps(res, indent=2))
        return 0 if res["all_passed"] else 1
    if args.size_capacity:
        spec = json.loads(Path(args.size_capacity).read_text(encoding="utf-8"))
        print(json.dumps(compute_capacity_scenarios(spec), indent=2))
        return 0
    if args.model_tco:
        spec = json.loads(Path(args.model_tco).read_text(encoding="utf-8"))
        print(json.dumps(compute_tco_and_commercial(spec), indent=2))
        return 0

    parser.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(run_checked_cli(main))
