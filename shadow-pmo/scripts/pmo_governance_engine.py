#!/usr/bin/env python3
"""
Shadow PMO Governance Engine (pmo_governance_engine.py)

Deterministic PERT + Critical Path Method (CPM) + seeded Monte Carlo
schedule risk simulation (P50/P80/P90) + EVM + contractual CR triage.
"""

from __future__ import annotations

import argparse
import json
import math
import random
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "shadow-monarch" / "scripts"))
from shadow_input import run_checked_cli, strict_bool


def _number(container: dict[str, Any], field: str, owner: str) -> float:
    value = container.get(field)
    if type(value) not in (int, float) or not math.isfinite(value):
        raise ValueError(f"{owner}.{field} must be a finite JSON number.")
    return float(value)


def _topological_order(tasks: list[dict[str, Any]]) -> list[str]:
    by_id = {t["id"]: t for t in tasks}
    in_deg = {t["id"]: 0 for t in tasks}
    adj: dict[str, list[str]] = {t["id"]: [] for t in tasks}
    for t in tasks:
        for pred in t.get("predecessors", []):
            if pred not in by_id:
                raise ValueError(f"Task '{t['id']}' references unknown predecessor '{pred}'.")
            adj[pred].append(t["id"])
            in_deg[t["id"]] += 1

    queue = [tid for tid, deg in in_deg.items() if deg == 0]
    order: list[str] = []
    while queue:
        curr = queue.pop(0)
        order.append(curr)
        for nxt in adj[curr]:
            in_deg[nxt] -= 1
            if in_deg[nxt] == 0:
                queue.append(nxt)
    if len(order) != len(tasks):
        raise ValueError("Cycle detected in WBS task dependency graph.")
    return order


def analyze_schedule_and_evm(spec: dict[str, Any]) -> dict[str, Any]:
    """Compute PERT, CPM forward/backward pass, seeded Monte Carlo P50/P80/P90, and EVM."""
    tasks = spec.get("tasks", [])
    if not tasks:
        raise ValueError("tasks list cannot be empty.")

    order = _topological_order(tasks)
    by_id: dict[str, dict[str, Any]] = {}
    succs: dict[str, list[str]] = {t["id"]: [] for t in tasks}
    for t in tasks:
        o = _number(t, "optimistic", str(t["id"]))
        m = _number(t, "most_likely", str(t["id"]))
        p = _number(t, "pessimistic", str(t["id"]))
        if not (0 <= o <= m <= p):
            raise ValueError(f"Task '{t['id']}' must satisfy 0 <= optimistic <= most_likely <= pessimistic.")
        expected = (o + 4.0 * m + p) / 6.0
        sigma = (p - o) / 6.0
        by_id[t["id"]] = {
            **t,
            "expected": expected,
            "sigma": sigma,
        }
        for pred in t.get("predecessors", []):
            succs[pred].append(t["id"])

    # Forward pass
    es: dict[str, float] = {}
    ef: dict[str, float] = {}
    for tid in order:
        preds = by_id[tid].get("predecessors", [])
        es[tid] = max((ef[p] for p in preds), default=0.0)
        ef[tid] = es[tid] + by_id[tid]["expected"]

    project_cpm_duration = max(ef.values(), default=0.0)

    # Backward pass
    ls: dict[str, float] = {}
    lf: dict[str, float] = {}
    for tid in reversed(order):
        lf[tid] = min((ls[s] for s in succs[tid]), default=project_cpm_duration)
        ls[tid] = lf[tid] - by_id[tid]["expected"]

    task_outputs: list[dict[str, Any]] = []
    critical_path: list[str] = []
    for tid in order:
        flt = round(ls[tid] - es[tid], 4)
        is_crit = abs(flt) < 1e-4
        if is_crit:
            critical_path.append(tid)
        task_outputs.append({
            "id": tid,
            "name": by_id[tid].get("name", tid),
            "expected_days": round(by_id[tid]["expected"], 2),
            "sigma_days": round(by_id[tid]["sigma"], 2),
            "es": round(es[tid], 2),
            "ef": round(ef[tid], 2),
            "ls": round(ls[tid], 2),
            "lf": round(lf[tid], 2),
            "total_float": round(flt, 2),
            "is_critical": is_crit,
        })

    # Seeded Monte Carlo simulation (triangular distribution across DAG)
    iterations = int(spec.get("monte_carlo_iterations", 2000))
    if iterations < 1:
        raise ValueError("monte_carlo_iterations must be at least 1.")
    seed = int(spec.get("seed", 42))
    rng = random.Random(seed)
    durations: list[float] = []
    for _ in range(iterations):
        sim_ef: dict[str, float] = {}
        for tid in order:
            t = by_id[tid]
            o, m, p = float(t["optimistic"]), float(t["most_likely"]), float(t["pessimistic"])
            d = o if o == p else rng.triangular(o, p, m)
            start = max((sim_ef[pred] for pred in t.get("predecessors", [])), default=0.0)
            sim_ef[tid] = start + d
        durations.append(max(sim_ef.values(), default=0.0))

    durations.sort()
    p50 = round(durations[int(0.50 * (iterations - 1))], 2)
    p80 = round(durations[int(0.80 * (iterations - 1))], 2)
    p90 = round(durations[int(0.90 * (iterations - 1))], 2)

    evm_out: dict[str, Any] = {}
    if "evm" in spec:
        evm = spec["evm"]
        bac = _number(evm, "bac", "evm")
        pv = _number(evm, "pv", "evm")
        ev = _number(evm, "ev", "evm")
        ac = _number(evm, "ac", "evm")
        # Undefined ratios stay None instead of reporting a healthy 1.0.
        cpi = round(ev / ac, 4) if ac > 0 else None
        spi = round(ev / pv, 4) if pv > 0 else None
        eac = round(bac / cpi, 2) if cpi else None
        evm_out = {
            "bac": bac, "pv": pv, "ev": ev, "ac": ac,
            "cv": round(ev - ac, 2), "sv": round(ev - pv, 2),
            "cpi": cpi, "spi": spi, "eac": eac,
        }

    return {
        "deterministic_cpm_days": round(project_cpm_duration, 2),
        "critical_path_ids": critical_path,
        "monte_carlo": {"iterations": iterations, "seed": seed, "p50_days": p50, "p80_days": p80, "p90_days": p90},
        "tasks": task_outputs,
        "evm": evm_out,
    }


def evaluate_change_request(req: dict[str, Any]) -> dict[str, Any]:
    """Classify a client request using contractual hierarchy and mandate human CCB sign-off."""
    violates_signed_ac = strict_bool(req.get("violates_signed_acceptance_criteria", False), "violates_signed_acceptance_criteria")
    within_warranty = strict_bool(req.get("within_warranty_period", False), "within_warranty_period")
    statutory_in_scope = strict_bool(req.get("required_for_signed_statutory_compliance", False), "required_for_signed_statutory_compliance")
    explicitly_excluded = strict_bool(req.get("listed_in_exclusion_register", False), "listed_in_exclusion_register")
    net_new_capability = strict_bool(req.get("introduces_net_new_workflow_or_integration", False), "introduces_net_new_workflow_or_integration")
    ambiguous_clause = strict_bool(req.get("contract_clause_ambiguous", False), "contract_clause_ambiguous")

    if explicitly_excluded or (net_new_capability and not violates_signed_ac):
        classification = "PAID_CHANGE_REQUEST_CANDIDATE"
        rationale = "Request introduces net-new functionality or falls under signed Contract Exclusion Register."
    elif violates_signed_ac and (within_warranty or not net_new_capability):
        classification = "IN_SCOPE_DEFECT"
        rationale = "Observed behavior fails signed FSD/UAT acceptance criteria within active scope/warranty."
    elif statutory_in_scope and not ambiguous_clause:
        classification = "IMPLICIT_STATUTORY_OR_BASELINE_OBLIGATION"
        rationale = "Necessary to fulfill regulatory/NFR obligation already committed in signed baseline."
    else:
        classification = "SCOPE_CLARIFICATION_REVIEW"
        rationale = "Contract/KAK/FSD precedence contains ambiguity requiring formal CCB & legal clarification."

    return {
        "cr_id": req.get("cr_id", "CR-UNASSIGNED"),
        "proposed_classification": classification,
        "rationale": rationale,
        "contract_precedence_checked": ["Master Contract", "Addenda", "KAK/SOW", "Signed FSD/AC", "Exclusion Register"],
        "requires_human_approval": True,
        "approval_authority": req.get("approval_authority", "Change Control Board (CCB) & Authorized Contract Signatory"),
        "is_binding_legal_verdict": False,
    }


def run_self_test() -> dict[str, Any]:
    """Execute PERT/CPM/Monte Carlo numerical property tests + CR adversarial probes."""
    results: list[dict[str, Any]] = []

    wbs = {
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
    sched = analyze_schedule_and_evm(wbs)
    mc = sched["monte_carlo"]
    # Precision-1: P90 >= P80 >= P50 monotonicity & EVM math exact
    mono_ok = mc["p90_days"] >= mc["p80_days"] >= mc["p50_days"] > 0
    evm_ok = sched["evm"]["cpi"] == 0.9 and sched["evm"]["spi"] == 0.9
    results.append({
        "probe": "PRECISION-1: CPM critical path + Monte Carlo P90>=P80>=P50 + exact EVM CPI/SPI",
        "passed": mono_ok and evm_ok and "T1" in sched["critical_path_ids"] and "T4" in sched["critical_path_ids"],
    })

    # Precision-2: Deterministic seed produces exact identical percentiles on rerun
    results.append({
        "probe": "PRECISION-2: Seeded Monte Carlo simulation is 100% reproducible",
        "passed": analyze_schedule_and_evm(wbs) == sched,
    })

    # Precision-3: CR defect vs candidate Paid CR classification respects human approval gate
    cr_paid = evaluate_change_request({
        "cr_id": "CR-101",
        "introduces_net_new_workflow_or_integration": True,
        "violates_signed_acceptance_criteria": False,
    })
    cr_bug = evaluate_change_request({
        "cr_id": "CR-102",
        "violates_signed_acceptance_criteria": True,
        "within_warranty_period": True,
    })
    results.append({
        "probe": "PRECISION-3: CR triage separates PAID_CHANGE_REQUEST_CANDIDATE vs IN_SCOPE_DEFECT & enforces non-binding AI gate",
        "passed": (
            cr_paid["proposed_classification"] == "PAID_CHANGE_REQUEST_CANDIDATE"
            and cr_bug["proposed_classification"] == "IN_SCOPE_DEFECT"
            and cr_paid["requires_human_approval"] is True
            and cr_paid["is_binding_legal_verdict"] is False
        ),
    })

    # Recall-1: Ambiguous contract clause escalates to SCOPE_CLARIFICATION_REVIEW
    cr_ambig = evaluate_change_request({"cr_id": "CR-103", "contract_clause_ambiguous": True})
    results.append({
        "probe": "RECALL-1: Ambiguous contract clause routes to SCOPE_CLARIFICATION_REVIEW",
        "passed": cr_ambig["proposed_classification"] == "SCOPE_CLARIFICATION_REVIEW",
    })

    # Recall-2: Dependency cycle in WBS raises ValueError
    cycle_caught = False
    try:
        analyze_schedule_and_evm({
            "tasks": [
                {"id": "A", "optimistic": 1, "most_likely": 2, "pessimistic": 3, "predecessors": ["B"]},
                {"id": "B", "optimistic": 1, "most_likely": 2, "pessimistic": 3, "predecessors": ["A"]},
            ]
        })
    except ValueError:
        cycle_caught = True
    results.append({"probe": "RECALL-2: Rejects cyclic dependency DAG in WBS", "passed": cycle_caught})

    # Recall-3: Invalid PERT bounds (O > M) rejected
    pert_caught = False
    try:
        analyze_schedule_and_evm({
            "tasks": [{"id": "A", "optimistic": 10, "most_likely": 5, "pessimistic": 12, "predecessors": []}]
        })
    except ValueError:
        pert_caught = True
    results.append({"probe": "RECALL-3: Rejects invalid PERT estimate ordering (O > M)", "passed": pert_caught})

    # Precision-4: Merge bias check — two parallel risky paths yield P80 > deterministic CPM
    results.append({
        "probe": "PRECISION-4: Merge bias reflected in P80 exceeding deterministic CPM",
        "passed": mc["p80_days"] > sched["deterministic_cpm_days"],
    })

    # Precision-5: Explicit exclusion register overrides into PAID_CHANGE_REQUEST_CANDIDATE
    cr_excl = evaluate_change_request({"cr_id": "CR-104", "listed_in_exclusion_register": True})
    results.append({
        "probe": "PRECISION-5: Contract Exclusion Register item triggers PAID_CHANGE_REQUEST_CANDIDATE",
        "passed": cr_excl["proposed_classification"] == "PAID_CHANGE_REQUEST_CANDIDATE",
    })

    passed = sum(1 for r in results if r["passed"])
    return {
        "tool": "pmo_governance_engine.py",
        "total_probes": len(results),
        "passed": passed,
        "failed": len(results) - passed,
        "all_passed": passed == len(results),
        "results": results,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Shadow PMO Contractual & Schedule Risk Engine")
    parser.add_argument("--analyze-schedule", default=None)
    parser.add_argument("--evaluate-cr", default=None)
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()

    if args.self_test:
        res = run_self_test()
        print(json.dumps(res, indent=2))
        return 0 if res["all_passed"] else 1
    if args.analyze_schedule:
        spec = json.loads(Path(args.analyze_schedule).read_text(encoding="utf-8"))
        print(json.dumps(analyze_schedule_and_evm(spec), indent=2))
        return 0
    if args.evaluate_cr:
        req = json.loads(Path(args.evaluate_cr).read_text(encoding="utf-8"))
        print(json.dumps(evaluate_change_request(req), indent=2))
        return 0

    parser.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(run_checked_cli(main))
