#!/usr/bin/env python3
"""
Shadow Plan Sprint DAG & Governance Verifier (sprint_dag_verifier.py)

Zero third-party dependencies (Python 3 stdlib only).
Validates sprint plan JSON files for:
  1. Acyclic task dependency graph via Kahn's topological wave scheduler (PLAN_CYCLIC_DAG)
  2. Valid upstream dependency IDs (PLAN_UNKNOWN_DEPENDENCY)
  3. End-to-end FR / US|JOB / AC traceability on non-gate tasks (PLAN_MISSING_TRACEABILITY)
  4. Non-empty Definition of Ready & Definition of Done (PLAN_MISSING_DOR_DOD)
  5. Mandatory [APPROVAL-REQUIRED] tagging on L2/L3/L4 tasks (PLAN_MISSING_APPROVAL_TAG)
  6. Horizontal layer-slicing anti-pattern detection (PLAN_HORIZONTAL_LAYER_SMELL)
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "shadow-monarch" / "scripts"))
from shadow_input import run_checked_cli, strict_bool

APPROVAL_GATED_TIERS = {
    "L2",
    "L3",
    "L4",
    "L2_SCOPE_EXPANSION",
    "L3_RESOURCE_INTENSIVE",
    "L4_HIGH_IMPACT",
}
FR_ID_RE = re.compile(r"^FR-[A-Z0-9-]+$", re.IGNORECASE)
STORY_ID_RE = re.compile(r"^(?:US|JOB)-[A-Z0-9.-]+$", re.IGNORECASE)
AC_ID_RE = re.compile(r"^AC-[A-Z0-9-]+$", re.IGNORECASE)
HORIZONTAL_TITLE_RE = re.compile(
    r"\b(?:create|build|implement)\s+all\s+(?:\d+\s+)?(?:db\s+|database\s+|postgres\s+|mysql\s+)?(?:tables|schemas|endpoints|apis|screens|pages)\b",
    re.IGNORECASE,
)


def audit_sprint_plan(plan: dict[str, Any]) -> dict[str, Any]:
    """Audit a sprint plan dictionary and compute topological execution waves."""
    raw_tasks = plan.get("tasks", [])
    if not isinstance(raw_tasks, list):
        return {
            "status": "FAIL",
            "is_acyclic": False,
            "waves": [],
            "finding_count": 1,
            "findings": [
                {
                    "rule_id": "PLAN_INVALID_SCHEMA",
                    "severity": "CRITICAL",
                    "task_id": "<root>",
                    "message": "'tasks' must be a JSON array.",
                }
            ],
        }

    findings: list[dict[str, Any]] = []
    by_id: dict[str, dict[str, Any]] = {}
    in_degree: dict[str, int] = {}
    dependents: dict[str, list[str]] = {}

    for idx, task in enumerate(raw_tasks):
        if not isinstance(task, dict):
            findings.append(
                {
                    "rule_id": "PLAN_INVALID_SCHEMA",
                    "severity": "CRITICAL",
                    "task_id": f"<index:{idx}>",
                    "message": "Each task entry must be a JSON object.",
                }
            )
            continue
        task_id = str(task.get("task_id", "")).strip()
        if not task_id:
            findings.append(
                {
                    "rule_id": "PLAN_INVALID_SCHEMA",
                    "severity": "CRITICAL",
                    "task_id": f"<index:{idx}>",
                    "message": "Task missing non-empty 'task_id'.",
                }
            )
            continue
        if task_id in by_id:
            findings.append(
                {
                    "rule_id": "PLAN_DUPLICATE_TASK_ID",
                    "severity": "HIGH",
                    "task_id": task_id,
                    "message": f"Duplicate task_id '{task_id}' detected.",
                }
            )
            continue
        by_id[task_id] = task
        in_degree[task_id] = 0
        dependents[task_id] = []

    for task_id, task in by_id.items():
        deps = task.get("depends_on", [])
        if not isinstance(deps, list):
            deps = []
        seen_deps: set[str] = set()
        for dep in deps:
            dep_id = str(dep).strip()
            if dep_id in seen_deps:
                continue
            seen_deps.add(dep_id)
            if dep_id not in by_id:
                findings.append(
                    {
                        "rule_id": "PLAN_UNKNOWN_DEPENDENCY",
                        "severity": "HIGH",
                        "task_id": task_id,
                        "message": f"Task '{task_id}' depends on unknown task '{dep_id}'.",
                    }
                )
            else:
                dependents[dep_id].append(task_id)
                in_degree[task_id] += 1

        # Traceability check for non-gate / non-foundation feature tasks
        kind = str(task.get("kind", "feature")).strip().lower()
        if kind not in {"gate", "enabler"}:
            fr_ref = str(task.get("fr_ref", "")).strip()
            story_id = str(task.get("story_id", "")).strip()
            ac_refs = task.get("ac_refs", [])
            valid_acs = isinstance(ac_refs, list) and any(
                AC_ID_RE.match(str(a).strip()) for a in ac_refs
            )
            missing_parts: list[str] = []
            if not FR_ID_RE.match(fr_ref):
                missing_parts.append("fr_ref (FR-*)")
            if not STORY_ID_RE.match(story_id):
                missing_parts.append("story_id (US-* or JOB-*)")
            if not valid_acs:
                missing_parts.append("ac_refs (AC-*)")
            if missing_parts:
                findings.append(
                    {
                        "rule_id": "PLAN_MISSING_TRACEABILITY",
                        "severity": "HIGH",
                        "task_id": task_id,
                        "message": f"Task '{task_id}' missing required traceability fields: {', '.join(missing_parts)}.",
                    }
                )

        # DoR / DoD completeness check
        dor = task.get("definition_of_ready", [])
        dod = task.get("definition_of_done", [])
        if not (isinstance(dor, list) and len(dor) > 0) or not (isinstance(dod, list) and len(dod) > 0):
            findings.append(
                {
                    "rule_id": "PLAN_MISSING_DOR_DOD",
                    "severity": "MEDIUM",
                    "task_id": task_id,
                    "message": f"Task '{task_id}' must declare non-empty definition_of_ready and definition_of_done arrays.",
                }
            )

        # L2/L3/L4 [APPROVAL-REQUIRED] gate check
        tier = str(task.get("approval_tier", "L1")).strip().upper()
        title = str(task.get("title", "")).strip()
        approval_required = strict_bool(task.get("approval_required", False), "approval_required")
        if tier in APPROVAL_GATED_TIERS:
            has_tag = "[APPROVAL-REQUIRED" in title.upper()
            if not (approval_required and has_tag):
                findings.append(
                    {
                        "rule_id": "PLAN_MISSING_APPROVAL_TAG",
                        "severity": "CRITICAL",
                        "task_id": task_id,
                        "message": f"Task '{task_id}' with tier '{tier}' must set approval_required=true and include '[APPROVAL-REQUIRED]' in title.",
                    }
                )

        # Horizontal slicing anti-pattern check
        slice_type = str(task.get("slice_type", "vertical")).strip().lower()
        if slice_type == "horizontal" or HORIZONTAL_TITLE_RE.search(title):
            findings.append(
                {
                    "rule_id": "PLAN_HORIZONTAL_LAYER_SMELL",
                    "severity": "MEDIUM",
                    "task_id": task_id,
                    "message": f"Task '{task_id}' appears horizontally sliced by technical layer; prefer thin vertical slices.",
                }
            )

    # Kahn's topological wave scheduling
    frontier = sorted(tid for tid, deg in in_degree.items() if deg == 0)
    waves: list[list[str]] = []
    visited = 0
    remaining_deg = dict(in_degree)

    while frontier:
        waves.append(frontier)
        visited += len(frontier)
        next_frontier: list[str] = []
        for tid in frontier:
            for child in dependents[tid]:
                remaining_deg[child] -= 1
                if remaining_deg[child] == 0:
                    next_frontier.append(child)
        frontier = sorted(next_frontier)

    cyclic_nodes = sorted(tid for tid, deg in remaining_deg.items() if deg > 0)
    is_acyclic = visited == len(by_id) and len(cyclic_nodes) == 0
    if not is_acyclic:
        findings.append(
            {
                "rule_id": "PLAN_CYCLIC_DAG",
                "severity": "CRITICAL",
                "task_id": ",".join(cyclic_nodes),
                "message": f"Cyclic dependency detected involving tasks: {cyclic_nodes}. Extract a Wave 0 contract slice to break the cycle.",
            }
        )

    return {
        "status": "PASS" if not findings else "FINDINGS_DETECTED",
        "is_acyclic": is_acyclic,
        "task_count": len(by_id),
        "waves": waves,
        "cyclic_nodes": cyclic_nodes,
        "finding_count": len(findings),
        "findings": findings,
    }


def run_self_test() -> dict[str, Any]:
    """Run deterministic precision (3) and recall (4) probes (Rule 22)."""
    clean_plan = {
        "tasks": [
            {
                "task_id": "TASK-000",
                "title": "Define Order OpenAPI & Schema Expand Contract",
                "kind": "enabler",
                "approval_tier": "L1",
                "depends_on": [],
                "definition_of_ready": ["FR-ORD-001 locked"],
                "definition_of_done": ["OpenAPI 3.1 validated"],
            },
            {
                "task_id": "TASK-001",
                "title": "Order Approval Vertical Slice (DB + API + UI + QA)",
                "kind": "feature",
                "slice_type": "vertical",
                "fr_ref": "FR-ORD-001",
                "story_id": "US-014",
                "ac_refs": ["AC-ORD-001-01", "AC-ORD-001-02"],
                "approval_tier": "L1",
                "depends_on": ["TASK-000"],
                "definition_of_ready": ["OpenAPI contract agreed", "9-state UI spec attached"],
                "definition_of_done": ["200/403/409 tests pass", "shadow_gate.py clean"],
            },
            {
                "task_id": "GATE-PERF",
                "title": "Pre-UAT k6 Load Verification [APPROVAL-REQUIRED: L3]",
                "kind": "gate",
                "approval_tier": "L3",
                "approval_required": True,
                "depends_on": ["TASK-001"],
                "definition_of_ready": ["Staging UAT baseline green"],
                "definition_of_done": ["p95 <= 250ms recorded"],
            },
        ]
    }

    job_story_plan = {
        "tasks": [
            {
                "task_id": "TASK-JOB-1",
                "title": "Offline Draft Recovery Vertical Slice",
                "kind": "feature",
                "slice_type": "vertical",
                "fr_ref": "FR-OFF-003",
                "story_id": "JOB-03.1",
                "ac_refs": ["AC-OFF-003-01"],
                "approval_tier": "L1",
                "depends_on": [],
                "definition_of_ready": ["Offline queue contract locked"],
                "definition_of_done": ["Reconnect replay integration test green"],
            }
        ]
    }

    l4_tagged_plan = {
        "tasks": [
            {
                "task_id": "GATE-PROD",
                "title": "Production Release Deployment [APPROVAL-REQUIRED: L4]",
                "kind": "gate",
                "approval_tier": "L4_HIGH_IMPACT",
                "approval_required": True,
                "depends_on": [],
                "definition_of_ready": ["Berita Acara UAT signed"],
                "definition_of_done": ["Post-deploy smoke check passed"],
            }
        ]
    }

    cyclic_plan = {
        "tasks": [
            {
                "task_id": "T-A",
                "title": "Auth Claims Slice",
                "kind": "enabler",
                "approval_tier": "L1",
                "depends_on": ["T-B"],
                "definition_of_ready": ["Spec ready"],
                "definition_of_done": ["Tests pass"],
            },
            {
                "task_id": "T-B",
                "title": "Audit Envelope Slice",
                "kind": "enabler",
                "approval_tier": "L1",
                "depends_on": ["T-A"],
                "definition_of_ready": ["Spec ready"],
                "definition_of_done": ["Tests pass"],
            },
        ]
    }

    untagged_l3_plan = {
        "tasks": [
            {
                "task_id": "T-LOAD",
                "title": "Run 500 VU staging stress test",
                "kind": "gate",
                "approval_tier": "L3",
                "approval_required": False,
                "depends_on": [],
                "definition_of_ready": ["Staging ready"],
                "definition_of_done": ["Report saved"],
            }
        ]
    }

    missing_trace_plan = {
        "tasks": [
            {
                "task_id": "T-ORPHAN",
                "title": "Add export button",
                "kind": "feature",
                "approval_tier": "L1",
                "depends_on": [],
                "definition_of_ready": ["Mockup ready"],
                "definition_of_done": ["Merged"],
            }
        ]
    }

    horizontal_plan = {
        "tasks": [
            {
                "task_id": "T-HORIZ",
                "title": "Create all 25 postgres tables for sprint 1",
                "kind": "feature",
                "slice_type": "horizontal",
                "fr_ref": "FR-001",
                "story_id": "US-001",
                "ac_refs": ["AC-001-01"],
                "approval_tier": "L1",
                "depends_on": [],
                "definition_of_ready": ["ERD ready"],
                "definition_of_done": ["Tables migrated"],
            }
        ]
    }

    precision_cases = [
        ("PRECISION-1: Clean vertical acyclic plan with L3 approval gate", clean_plan),
        ("PRECISION-2: Valid JOB-ID vertical slice plan", job_story_plan),
        ("PRECISION-3: Properly tagged L4_HIGH_IMPACT release gate", l4_tagged_plan),
    ]
    recall_cases = [
        ("RECALL-1: Circular A <-> B dependency detected", cyclic_plan, "PLAN_CYCLIC_DAG"),
        ("RECALL-2: Untagged L3 stress test blocked", untagged_l3_plan, "PLAN_MISSING_APPROVAL_TAG"),
        ("RECALL-3: Feature task missing FR/US/AC traceability", missing_trace_plan, "PLAN_MISSING_TRACEABILITY"),
        ("RECALL-4: Horizontal layer-slicing anti-pattern flagged", horizontal_plan, "PLAN_HORIZONTAL_LAYER_SMELL"),
    ]

    results: list[dict[str, Any]] = []
    for name, payload in precision_cases:
        res = audit_sprint_plan(payload)
        results.append(
            {
                "probe": name,
                "passed": res["finding_count"] == 0 and res["is_acyclic"],
                "finding_count": res["finding_count"],
                "waves": res["waves"],
            }
        )

    for name, payload, expected_rule in recall_cases:
        res = audit_sprint_plan(payload)
        matched = {f["rule_id"] for f in res["findings"]}
        results.append(
            {
                "probe": name,
                "passed": expected_rule in matched,
                "matched_rules": sorted(matched),
            }
        )

    passed = sum(1 for r in results if r["passed"])
    return {
        "tool": "sprint_dag_verifier.py",
        "total_probes": len(results),
        "passed": passed,
        "failed": len(results) - passed,
        "all_passed": passed == len(results),
        "results": results,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Shadow Plan — Sprint DAG, Traceability & Approval Gate Verifier")
    parser.add_argument("--check-plan", default=None, help="Path to sprint plan JSON file")
    parser.add_argument("--self-test", action="store_true", help="Run precision & recall probes")
    args = parser.parse_args(argv)

    if args.self_test:
        res = run_self_test()
        print(json.dumps(res, indent=2))
        return 0 if res["all_passed"] else 1

    if args.check_plan:
        plan_path = Path(args.check_plan)
        try:
            data = json.loads(plan_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            print(json.dumps({"status": "ERROR", "message": str(exc)}, indent=2))
            return 1
        res = audit_sprint_plan(data)
        print(json.dumps(res, indent=2))
        return 0 if res["finding_count"] == 0 else 1

    parser.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(run_checked_cli(main))
