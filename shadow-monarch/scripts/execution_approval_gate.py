#!/usr/bin/env python3
"""
Execution Approval Gate & Intent Boundary Enforcer (execution_approval_gate.py)

Centralized fail-closed permission classifier, testing-boundary guard, sub-agent scope
validator, approval-persistence checker, and 7-part approval contract formatter for
Shadow Monarch and all 52 Shadow Army skills.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

LEVEL_ORDER: dict[str, int] = {
    "L0_READ_ONLY": 0,
    "L1_SAFE_VERIFICATION": 1,
    "L2_SCOPE_EXPANSION": 2,
    "L3_RESOURCE_INTENSIVE": 3,
    "L4_HIGH_IMPACT": 4,
}

SAFE_AUTO_ENVS = {"local", "development", "dev", "isolated_sandbox", "sandbox", "test_sandbox"}
RESTRICTED_ENVS = {"staging", "production", "prod", "live"}
VALID_APPROVAL_STATES = {"APPROVED_PENDING", "EXECUTED", "DENIED", "DEFERRED", "EXPIRED", "REVOKED"}

# Intent -> maximum automatic permission level allowed without explicit user approval
INTENT_MAX_AUTO_LEVEL: dict[str, str] = {
    "code_review": "L0_READ_ONLY",
    "debug": "L1_SAFE_VERIFICATION",
    "unit_test": "L1_SAFE_VERIFICATION",
    "ui_implementation": "L1_SAFE_VERIFICATION",
    "feature_implementation": "L1_SAFE_VERIFICATION",
    "refactor_in_scope": "L1_SAFE_VERIFICATION",
    "db_fix": "L1_SAFE_VERIFICATION",
    "perf_optimization": "L1_SAFE_VERIFICATION",
    "general": "L1_SAFE_VERIFICATION",
}

L4_CMD_RE = re.compile(
    r"\b(?:DROP\s+(?:TABLE|COLUMN|DATABASE|SCHEMA)|TRUNCATE\s+TABLE|prisma\s+migrate\s+reset|"
    r"git\s+push|git\s+reset\s+--hard|git\s+clean\s+-fd|terraform\s+apply|"
    r"kubectl\s+(?:apply|delete|rollout)|install\.ps1|install\.sh|rm\s+-rf|FLUSHALL|FLUSHDB)\b",
    re.IGNORECASE,
)
L3_CMD_RE = re.compile(
    r"\b(?:k6\s+run|locust\b|wrk\b|artillery\b|vegeta\b|hey\b|ab\s+-|"
    r"stress[- ]test|soak[- ]test|load[- ]test|fuzz(?:ing)?\s+--(?:corpus|runs=?\d{3,})|"
    r"run_evals\.py\s+[^\n]*--agent|mass[- ]api)\b",
    re.IGNORECASE,
)
L2_CMD_RE = re.compile(
    r"\b(?:playwright\s+test\b|cypress\s+run\b|broad[- ]e2e|unrelated[- ]refactor|"
    r"npm\s+install\s+\S|pnpm\s+add\s+\S|pip\s+install\s+\S)\b",
    re.IGNORECASE,
)
L1_CMD_RE = re.compile(
    r"\b(?:tsc\s+--noEmit|ruff\s+check|mypy\b|pyright\b|eslint\b|"
    r"vitest\s+run|pytest\b|go\s+test\b|cargo\s+test|phpunit\b|pest\b|"
    r"shadow_gate\.py|--self-test|--audit-descriptions|--validate)\b",
    re.IGNORECASE,
)
L0_CMD_RE = re.compile(
    r"\b(?:git\s+status|git\s+diff|git\s+log|git\s+show|git\s+merge-tree|"
    r"read_file|Select-String|rg\b|EXPLAIN\b|SELECT\b|SHOW\b|ls\b|dir\b)\b",
    re.IGNORECASE,
)


def _norm_env(env: str | None) -> str:
    val = (env or "").strip().lower()
    if val in SAFE_AUTO_ENVS or val in RESTRICTED_ENVS:
        return val
    return "unknown"


def _paths_within_allowed(targets: list[str], allowed: list[str]) -> bool:
    if not targets:
        return True
    if not allowed:
        return False
    norm_allowed = [a.replace("\\", "/").rstrip("/") for a in allowed if a.strip()]
    if "*" in norm_allowed:
        return True
    for tgt in targets:
        t = tgt.replace("\\", "/").lstrip("./")
        if not any(t == a or t.startswith(a + "/") for a in norm_allowed):
            return False
    return True


def _infer_required_level(req: dict[str, Any]) -> tuple[str, list[str]]:
    """Deterministically classify action into L0..L4 using conservative fail-closed rules."""
    reasons: list[str] = []
    cmd = str(req.get("command") or "")
    action_type = str(req.get("action_type") or "").strip().lower()
    user_intent = str(req.get("user_intent") or "general").strip().lower()
    env = _norm_env(req.get("environment"))
    target_paths: list[str] = [str(x) for x in (req.get("target_paths") or [])]
    allowed_paths: list[str] = [str(x) for x in (req.get("requested_modules") or req.get("allowed_paths") or [])]
    is_mutation = bool(req.get("is_mutation", False)) or action_type in {
        "edit_file",
        "write_file",
        "delete_file",
        "migration",
        "destructive_migration",
        "deploy",
        "infra_change",
        "secret_rotation",
        "git_push",
        "global_install",
    }
    is_destructive = bool(req.get("is_destructive", False))

    # Unknown or restricted target environment fails conservatively
    if env == "unknown":
        reasons.append("Target environment is `unknown`; failing closed as L4_HIGH_IMPACT.")
        return "L4_HIGH_IMPACT", reasons

    if env in RESTRICTED_ENVS and (is_mutation or is_destructive or action_type in {"load_test", "stress_test", "broad_e2e", "unit_test", "migration", "deploy", "command"} or L3_CMD_RE.search(cmd) or L4_CMD_RE.search(cmd)):
        reasons.append(f"Targeted restricted environment `{env}`.")
        return "L4_HIGH_IMPACT", reasons

    if is_destructive or action_type in {"destructive_migration", "deploy", "infra_change", "secret_rotation", "git_push", "global_install", "external_data_transfer", "replace_auth_sdk"} or L4_CMD_RE.search(cmd):
        reasons.append("High-impact/destructive/auth-SDK-replacement action matches L4 criteria.")
        return "L4_HIGH_IMPACT", reasons

    if action_type in {"stress_test", "load_test", "soak_test", "fuzzing", "large_benchmark", "mass_api", "high_cost_eval"} or L3_CMD_RE.search(cmd):
        reasons.append("Resource/cost-intensive operation matches L3 criteria.")
        return "L3_RESOURCE_INTENSIVE", reasons

    # Scope expansion checks (L2)
    if action_type in {"broad_e2e", "unrelated_refactor", "extra_feature", "unrequested_dependency", "change_framework_or_package_manager", "add_unrequested_infrastructure", "major_architecture_dependency"} or L2_CMD_RE.search(cmd):
        if not (user_intent == "broad_e2e" and action_type == "broad_e2e"):
            reasons.append("Scope-expanding action matches L2 criteria.")
            return "L2_SCOPE_EXPANSION", reasons

    if action_type == "refactor" and user_intent in {"feature_implementation", "ui_implementation", "bug_fix", "db_fix", "unit_test"}:
        reasons.append(f"Refactoring during `{user_intent}` is L2 scope expansion unless explicitly requested.")
        return "L2_SCOPE_EXPANSION", reasons

    if allowed_paths and target_paths and not _paths_within_allowed(target_paths, allowed_paths):
        if is_mutation or action_type in {"edit_file", "write_file", "refactor"}:
            reasons.append("Target paths fall outside `requested_modules` / `allowed_paths` (L2 scope expansion).")
            return "L2_SCOPE_EXPANSION", reasons

    if is_mutation or action_type in {"unit_test", "lint", "typecheck", "local_verification", "self_test", "edit_file", "write_file", "in_scope_migration"} or L1_CMD_RE.search(cmd):
        reasons.append("Bounded verification or in-scope local edit matches L1 criteria.")
        return "L1_SAFE_VERIFICATION", reasons

    if action_type in {"read", "inspect", "static_analysis", "code_review", "log_analysis"} or L0_CMD_RE.search(cmd):
        reasons.append("Non-mutating inspection matches L0_READ_ONLY.")
        return "L0_READ_ONLY", reasons

    # Default fail-closed for unrecognized non-L0 commands
    reasons.append("Unclassified execution action treated conservatively as L2_SCOPE_EXPANSION.")
    return "L2_SCOPE_EXPANSION", reasons


def build_approval_contract(req: dict[str, Any], required_level: str, block_reasons: list[str]) -> dict[str, Any]:
    """Build the mandatory 7-part Explicit Approval Contract (§3)."""
    action_label = str(req.get("command") or req.get("action_description") or req.get("action_type") or "Requested operation")
    env = _norm_env(req.get("environment"))
    targets = req.get("target_paths") or ["<specify exact targets>"]
    rps = req.get("rps")
    duration = req.get("duration_sec")
    impact = (
        f"Up to {rps} req/s for {duration}s; temporary CPU/DB/network utilization."
        if rps and duration
        else str(req.get("estimated_impact") or "Potential persistent state, resource, or cost impact; quantify before execution.")
    )
    return {
        "required_level": required_level,
        "1_proposed_action": action_label,
        "2_why_necessary": str(req.get("rationale") or "; ".join(block_reasons)),
        "3_exact_target_environment": {"environment": env, "targets": targets},
        "4_expected_side_effects": str(req.get("side_effects") or "May mutate target state, write data, or consume compute/quota."),
        "5_estimated_resource_impact": impact,
        "6_rollback_or_recovery_plan": str(req.get("rollback_plan") or "Revert local workspace/transaction or restore verified pre-action backup before execution."),
        "7_safer_alternatives": str(req.get("safer_alternative") or "Perform L0 read-only inspection or bounded L1 local unit/mock verification first."),
        "permission_question": f"This action is classified as {required_level} against `{env}` ({', '.join(targets)}). May I execute it under these explicit bounds?",
        "blocking_reasons": block_reasons,
    }


def _verify_approval(req: dict[str, Any], required_level: str, approval: dict[str, Any] | None) -> tuple[bool, list[str]]:
    """Fail-closed validation of persistent task approval (§6)."""
    if not approval:
        return False, [f"Missing explicit user approval record for {required_level} action."]

    status = str(approval.get("execution_status") or "").strip().upper()
    if status in {"DENIED", "DEFERRED", "REVOKED", "EXPIRED", "EXECUTED"}:
        return False, [f"BLOCKED_EXPLICITLY_DENIED: approval `execution_status` is `{status}` (must be `APPROVED_PENDING`)."]
    if status != "APPROVED_PENDING":
        return False, ["BLOCKED_APPROVAL_INVALID_STATUS: unrecognized or missing `execution_status`."]

    errors: list[str] = []
    if str(approval.get("task_id") or "") != str(req.get("task_id") or ""):
        errors.append("BLOCKED_APPROVAL_SCOPE_MISMATCH: `task_id` mismatch (approval cannot cross tasks).")
    if approval.get("project_path") and req.get("project_path") and str(approval["project_path"]) != str(req["project_path"]):
        errors.append("BLOCKED_APPROVAL_SCOPE_MISMATCH: `project_path` mismatch (approval cannot cross projects).")

    approved_lvl = str(approval.get("permission_level") or "L0_READ_ONLY")
    if LEVEL_ORDER.get(approved_lvl, -1) < LEVEL_ORDER.get(required_level, 99):
        errors.append(f"BLOCKED_APPROVAL_SCOPE_MISMATCH: approved level `{approved_lvl}` < required `{required_level}`.")

    env = _norm_env(req.get("environment"))
    allowed_envs = {_norm_env(e) for e in (approval.get("allowed_environments") or [])}
    if env not in allowed_envs or env == "unknown":
        errors.append(f"BLOCKED_APPROVAL_SCOPE_MISMATCH: environment `{env}` not in approved environments `{sorted(allowed_envs)}`.")

    targets = [str(x) for x in (req.get("target_paths") or [])]
    exact_targets = [str(x) for x in (approval.get("exact_targets") or [])]
    if targets and not _paths_within_allowed(targets, exact_targets):
        errors.append("BLOCKED_APPROVAL_SCOPE_MISMATCH: action target paths exceed approved `exact_targets`.")

    limits = approval.get("resource_limits") or {}
    if req.get("rps") is not None and limits.get("max_rps") is not None and float(req["rps"]) > float(limits["max_rps"]):
        errors.append(f"BLOCKED_APPROVAL_SCOPE_MISMATCH: requested RPS ({req['rps']}) exceeds approved limit ({limits['max_rps']}).")
    if req.get("duration_sec") is not None and limits.get("max_duration_sec") is not None and float(req["duration_sec"]) > float(limits["max_duration_sec"]):
        errors.append(f"BLOCKED_APPROVAL_SCOPE_MISMATCH: requested duration ({req['duration_sec']}s) exceeds limit ({limits['max_duration_sec']}s).")

    return len(errors) == 0, errors


def evaluate_execution_request(req: dict[str, Any], approval: dict[str, Any] | None = None) -> dict[str, Any]:
    """Run §1 Pre-Execution Assessment & enforce §2-§6 authorization gates."""
    user_intent = str(req.get("user_intent") or "general").strip().lower()
    env = _norm_env(req.get("environment"))
    required_level, level_reasons = _infer_required_level(req)

    # Check if an explicit DENY / DEFER record exists even for L0/L1
    if approval and str(approval.get("execution_status") or "").upper() in {"DENIED", "DEFERRED", "REVOKED"}:
        reason = f"Action explicitly marked `{approval['execution_status']}` in task approval record."
        return {
            "decision": "BLOCKED",
            "status": "BLOCKED",
            "code": "BLOCKED_EXPLICITLY_DENIED",
            "permission_level": required_level,
            "environment": env,
            "requires_approval": True,
            "reasons": [reason],
            "approval_contract": build_approval_contract(req, required_level, [reason]),
        }

    # Check testing / intent boundary (§4)
    intent_max = INTENT_MAX_AUTO_LEVEL.get(user_intent, "L1_SAFE_VERIFICATION")
    boundary_violation: str | None = None
    action_type = str(req.get("action_type") or "").strip().lower()
    if user_intent == "code_review" and (bool(req.get("is_mutation")) or required_level != "L0_READ_ONLY"):
        boundary_violation = "Testing/Intent boundary violation: `code_review` is strictly `L0_READ_ONLY`; modifications are prohibited."

    if boundary_violation is None and env in SAFE_AUTO_ENVS and LEVEL_ORDER[required_level] <= LEVEL_ORDER[intent_max]:
        return {
            "decision": "ALLOW",
            "status": "PASS",
            "code": "ALLOWED_IN_SCOPE",
            "permission_level": required_level,
            "environment": env,
            "requires_approval": False,
            "reasons": level_reasons,
        }

    # Otherwise check explicit valid approval (§3, §6) — except code_review mutation cannot silently bypass L0 unless explicitly approved with matching L2+ level
    ok, approval_errors = _verify_approval(req, required_level, approval)
    if ok and not (user_intent == "code_review" and not approval):
        return {
            "decision": "ALLOW",
            "status": "PASS",
            "code": "ALLOWED_BY_EXPLICIT_APPROVAL",
            "permission_level": required_level,
            "environment": env,
            "requires_approval": False,
            "approval_id": approval.get("approval_id") if approval else None,
            "reasons": level_reasons + ["Verified matching active `APPROVED_PENDING` record."],
        }

    all_reasons = ([boundary_violation] if boundary_violation else []) + level_reasons + approval_errors
    code = "BLOCKED_UNKNOWN_ENVIRONMENT" if env == "unknown" else "BLOCKED_REQUIRES_APPROVAL"
    if any("DENIED" in r for r in all_reasons):
        code = "BLOCKED_EXPLICITLY_DENIED"
    elif any("SCOPE_MISMATCH" in r for r in all_reasons):
        code = "BLOCKED_APPROVAL_SCOPE_MISMATCH"
    elif boundary_violation:
        code = "BLOCKED_INTENT_BOUNDARY"

    return {
        "decision": "BLOCKED",
        "status": "BLOCKED",
        "code": code,
        "permission_level": required_level,
        "environment": env,
        "requires_approval": True,
        "reasons": all_reasons,
        "approval_contract": build_approval_contract(req, required_level, all_reasons),
    }


def check_subagent_authorization(parent_scope: dict[str, Any], subagent_req: dict[str, Any]) -> dict[str, Any]:
    """Enforce §5 Sub-Agent Authorization Inheritance."""
    errors: list[str] = []
    sub_level, _ = _infer_required_level(subagent_req)
    explicit_sub_level = str(subagent_req.get("requested_permission_level") or sub_level)
    effective_sub_rank = max(LEVEL_ORDER.get(sub_level, 4), LEVEL_ORDER.get(explicit_sub_level, 4))

    parent_max = str(parent_scope.get("max_permission_level") or "L0_READ_ONLY")
    if effective_sub_rank > LEVEL_ORDER.get(parent_max, 0):
        errors.append(
            f"BLOCKED_SUBAGENT_LEVEL_UPGRADE: sub-agent requested `{explicit_sub_level}` (effective rank {effective_sub_rank}) > parent max `{parent_max}`."
        )

    sub_env = _norm_env(subagent_req.get("environment"))
    parent_envs = {_norm_env(e) for e in (parent_scope.get("allowed_environments") or [])}
    if sub_env not in parent_envs or sub_env == "unknown":
        errors.append(f"BLOCKED_SUBAGENT_ENV_EXPANSION: `{sub_env}` not allowed by parent `{sorted(parent_envs)}`.")

    sub_paths = [str(p) for p in (subagent_req.get("target_paths") or [])]
    parent_paths = [str(p) for p in (parent_scope.get("allowed_paths") or [])]
    if sub_paths and not _paths_within_allowed(sub_paths, parent_paths):
        errors.append("BLOCKED_SUBAGENT_SCOPE_EXPANSION: target_paths exceed parent allowed_paths.")

    action_name = str(subagent_req.get("action_type") or "").strip().lower()
    denied = {str(x).strip().lower() for x in (parent_scope.get("denied_actions") or [])}
    if action_name in denied:
        errors.append(f"BLOCKED_PARENT_DENIED_ACTION: `{action_name}` is explicitly denied/deferred by parent.")

    auth_source = str(subagent_req.get("approval_source") or "").strip().lower()
    if effective_sub_rank >= 2 and auth_source in {"orchestrator_recommendation", "orchestrator_instruction", "agent_self_approval"}:
        errors.append("BLOCKED_ORCHESTRATOR_NOT_USER_AUTH: orchestrator recommendation cannot substitute for user authorization.")

    return {
        "decision": "ALLOW" if not errors else "BLOCKED",
        "status": "PASS" if not errors else "BLOCKED",
        "effective_level": explicit_sub_level,
        "errors": errors,
    }


def run_self_test() -> dict[str, Any]:
    """Run all 10 §7 Mandatory Negative Tests + 4 Positive L0/L1/Approved-L3 Tests."""
    probes: list[dict[str, Any]] = []

    # NEG-01: UI task must NOT trigger stress testing
    r1 = evaluate_execution_request({
        "task_id": "T-01",
        "user_intent": "ui_implementation",
        "action_type": "stress_test",
        "command": "k6 run 03-stress-spike.k6.js",
        "environment": "local",
    })
    probes.append({"probe": "NEG-01: UI task blocks unapproved stress test", "passed": r1["decision"] == "BLOCKED" and r1["permission_level"] == "L3_RESOURCE_INTENSIVE", "code": r1["code"]})

    # NEG-02: Debugging task must NOT trigger production load testing
    r2 = evaluate_execution_request({
        "task_id": "T-02",
        "user_intent": "debug",
        "action_type": "load_test",
        "command": "k6 run load.js",
        "environment": "production",
    })
    probes.append({"probe": "NEG-02: Debug task blocks production load test", "passed": r2["decision"] == "BLOCKED" and r2["permission_level"] == "L4_HIGH_IMPACT", "code": r2["code"]})

    # NEG-03: Code review must NOT modify source files
    r3 = evaluate_execution_request({
        "task_id": "T-03",
        "user_intent": "code_review",
        "action_type": "edit_file",
        "target_paths": ["src/auth/service.ts"],
        "requested_modules": ["src/auth"],
        "is_mutation": True,
        "environment": "local",
    })
    probes.append({"probe": "NEG-03: Code review blocks source file edits (L0 only)", "passed": r3["decision"] == "BLOCKED" and r3["code"] == "BLOCKED_INTENT_BOUNDARY", "code": r3["code"]})

    # NEG-04: Unit test request must NOT trigger broad E2E execution
    r4 = evaluate_execution_request({
        "task_id": "T-04",
        "user_intent": "unit_test",
        "action_type": "broad_e2e",
        "command": "npx playwright test",
        "environment": "local",
    })
    probes.append({"probe": "NEG-04: Unit test request blocks broad E2E execution", "passed": r4["decision"] == "BLOCKED" and r4["permission_level"] == "L2_SCOPE_EXPANSION", "code": r4["code"]})

    # NEG-05: Feature request must NOT trigger unrelated refactoring
    r5 = evaluate_execution_request({
        "task_id": "T-05",
        "user_intent": "feature_implementation",
        "action_type": "refactor",
        "target_paths": ["src/billing/legacy.ts"],
        "requested_modules": ["src/auth"],
        "is_mutation": True,
        "environment": "local",
    })
    probes.append({"probe": "NEG-05: Feature request blocks unrelated refactoring", "passed": r5["decision"] == "BLOCKED" and r5["permission_level"] == "L2_SCOPE_EXPANSION", "code": r5["code"]})

    # NEG-06: Database fix must NOT trigger destructive migrations
    r6 = evaluate_execution_request({
        "task_id": "T-06",
        "user_intent": "db_fix",
        "action_type": "destructive_migration",
        "command": "DROP TABLE orders;",
        "is_mutation": True,
        "is_destructive": True,
        "environment": "local",
    })
    probes.append({"probe": "NEG-06: Database fix blocks destructive migration (L4)", "passed": r6["decision"] == "BLOCKED" and r6["permission_level"] == "L4_HIGH_IMPACT", "code": r6["code"]})

    # NEG-07: Sub-agent cannot bypass parent boundaries or use orchestrator instructions as user auth
    r7 = check_subagent_authorization(
        {
            "max_permission_level": "L1_SAFE_VERIFICATION",
            "allowed_environments": ["local"],
            "allowed_paths": ["src/auth"],
            "denied_actions": ["stress_test"],
        },
        {
            "requested_permission_level": "L3_RESOURCE_INTENSIVE",
            "action_type": "stress_test",
            "target_paths": ["src/billing/invoice.ts"],
            "environment": "local",
            "approval_source": "orchestrator_recommendation",
        },
    )
    probes.append({"probe": "NEG-07: Sub-agent boundary escalation blocked", "passed": r7["decision"] == "BLOCKED" and len(r7["errors"]) >= 3, "errors": r7["errors"]})

    # NEG-08: Unknown environments classified conservatively (never auto L1)
    r8 = evaluate_execution_request({
        "task_id": "T-08",
        "user_intent": "unit_test",
        "action_type": "unit_test",
        "command": "pytest tests/unit/test_db.py",
        "environment": "customer_cluster_42",
    })
    probes.append({"probe": "NEG-08: Unknown environment fails closed conservatively", "passed": r8["decision"] == "BLOCKED" and r8["code"] == "BLOCKED_UNKNOWN_ENVIRONMENT", "code": r8["code"]})

    # NEG-09: Explicitly denied actions are NOT executed
    r9 = evaluate_execution_request(
        {
            "task_id": "T-09",
            "user_intent": "perf_optimization",
            "action_type": "load_test",
            "environment": "local",
        },
        approval={
            "approval_id": "APR-09",
            "task_id": "T-09",
            "user_approved_action": "k6 load test",
            "permission_level": "L3_RESOURCE_INTENSIVE",
            "exact_targets": ["http://localhost:3000"],
            "allowed_environments": ["local"],
            "execution_status": "DENIED",
        },
    )
    probes.append({"probe": "NEG-09: Denied action blocked even on local env", "passed": r9["decision"] == "BLOCKED" and r9["code"] == "BLOCKED_EXPLICITLY_DENIED", "code": r9["code"]})

    # NEG-10: Previously granted approval NOT reused outside its task/target/resource bounds
    r10 = evaluate_execution_request(
        {
            "task_id": "T-10-OTHER",
            "project_path": "/repo/app",
            "user_intent": "debug",
            "action_type": "load_test",
            "environment": "local",
            "target_paths": ["http://localhost:3000/api"],
            "rps": 500,
            "duration_sec": 60,
        },
        approval={
            "approval_id": "APR-10",
            "task_id": "T-10",
            "project_path": "/repo/app",
            "user_approved_action": "k6 run",
            "permission_level": "L3_RESOURCE_INTENSIVE",
            "exact_targets": ["http://localhost:3000/api"],
            "allowed_environments": ["local"],
            "resource_limits": {"max_rps": 100, "max_duration_sec": 60},
            "execution_status": "APPROVED_PENDING",
        },
    )
    probes.append({"probe": "NEG-10: Stale/cross-task/over-budget approval rejected", "passed": r10["decision"] == "BLOCKED" and r10["code"] == "BLOCKED_APPROVAL_SCOPE_MISMATCH", "code": r10["code"]})

    # NEG-11: Unauthorized SSO/Auth SDK replacement blocked (L4)
    r11 = evaluate_execution_request({
        "task_id": "T-11",
        "user_intent": "feature_implementation",
        "action_type": "replace_auth_sdk",
        "target_paths": ["package.json", "src/auth"],
        "is_mutation": True,
        "environment": "local",
    })
    probes.append({"probe": "NEG-11: Unauthorized auth/SSO SDK replacement blocked (L4)", "passed": r11["decision"] == "BLOCKED" and r11["permission_level"] == "L4_HIGH_IMPACT", "code": r11["code"]})

    # NEG-12: Unapproved framework/infrastructure addition blocked (L2)
    r12 = evaluate_execution_request({
        "task_id": "T-12",
        "user_intent": "feature_implementation",
        "action_type": "add_unrequested_infrastructure",
        "command": "add Redis and Kafka containers",
        "environment": "local",
    })
    probes.append({"probe": "NEG-12: Unrequested infrastructure/framework deviation blocked (L2)", "passed": r12["decision"] == "BLOCKED" and r12["permission_level"] == "L2_SCOPE_EXPANSION", "code": r12["code"]})

    # POS-01: Code review L0 read-only allowed cleanly without prompt
    p1 = evaluate_execution_request({
        "task_id": "P-01",
        "user_intent": "code_review",
        "action_type": "read",
        "command": "git diff --stat",
        "environment": "local",
    })
    probes.append({"probe": "POS-01: Code review L0 read-only runs automatically", "passed": p1["decision"] == "ALLOW" and p1["permission_level"] == "L0_READ_ONLY"})

    # POS-02: Feature implementation bounded L1 verification allowed cleanly without prompt
    p2 = evaluate_execution_request({
        "task_id": "P-02",
        "user_intent": "feature_implementation",
        "action_type": "unit_test",
        "command": "pytest tests/unit/test_auth.py",
        "target_paths": ["tests/unit/test_auth.py"],
        "requested_modules": ["tests/unit", "src/auth"],
        "environment": "local",
    })
    probes.append({"probe": "POS-02: Bounded local L1 verification runs automatically", "passed": p2["decision"] == "ALLOW" and p2["permission_level"] == "L1_SAFE_VERIFICATION"})

    # POS-03: Properly scoped APPROVED_PENDING L3 local load test allowed
    p3 = evaluate_execution_request(
        {
            "task_id": "P-03",
            "project_path": "/repo/app",
            "user_intent": "debug",
            "action_type": "load_test",
            "command": "k6 run local-test.js",
            "target_paths": ["tests/perf/local-test.js"],
            "environment": "local",
            "rps": 100,
            "duration_sec": 60,
        },
        approval={
            "approval_id": "APR-P03",
            "task_id": "P-03",
            "project_path": "/repo/app",
            "user_approved_action": "k6 run local-test.js",
            "permission_level": "L3_RESOURCE_INTENSIVE",
            "exact_targets": ["tests/perf"],
            "allowed_environments": ["local"],
            "resource_limits": {"max_rps": 100, "max_duration_sec": 60},
            "execution_status": "APPROVED_PENDING",
        },
    )
    probes.append({"probe": "POS-03: Bounded APPROVED_PENDING L3 local load test allowed", "passed": p3["decision"] == "ALLOW"})

    # POS-04: Valid sub-agent inside parent bounds allowed
    p4 = check_subagent_authorization(
        {
            "max_permission_level": "L1_SAFE_VERIFICATION",
            "allowed_environments": ["local"],
            "allowed_paths": ["src/auth"],
            "denied_actions": ["stress_test"],
        },
        {
            "requested_permission_level": "L1_SAFE_VERIFICATION",
            "action_type": "unit_test",
            "target_paths": ["src/auth/auth.spec.ts"],
            "environment": "local",
        },
    )
    probes.append({"probe": "POS-04: Sub-agent within parent bounds allowed", "passed": p4["decision"] == "ALLOW"})

    passed_count = sum(1 for pr in probes if pr["passed"])
    return {
        "tool": "execution_approval_gate.py",
        "total_probes": len(probes),
        "passed": passed_count,
        "failed": len(probes) - passed_count,
        "all_passed": passed_count == len(probes),
        "results": probes,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Shadow Monarch User Intent Boundary & Execution Approval Gate")
    parser.add_argument("--assess", default=None, help="Path to JSON file containing {'request': ..., 'approval': optional}")
    parser.add_argument("--check-subagent", default=None, help="Path to JSON file containing {'parent_scope': ..., 'subagent_request': ...}")
    parser.add_argument("--format-approval-request", default=None, help="Path to JSON file containing {'request': ...} to render 7-part approval contract")
    parser.add_argument("--verify-approval", default=None, help="Path to JSON file containing {'request': ..., 'approval': ...} to verify persisted approval")
    parser.add_argument("--out", default=None, help="Optional output file path for JSON report")
    parser.add_argument("--self-test", action="store_true", help="Run 10 mandatory negative tests + 4 positive workflow tests")
    args = parser.parse_args()

    result: dict[str, Any]
    exit_code = 0

    if args.self_test:
        result = run_self_test()
        exit_code = 0 if result["all_passed"] else 1
    elif args.assess:
        payload = json.loads(Path(args.assess).read_text(encoding="utf-8-sig"))
        req = payload.get("request", payload)
        approval = payload.get("approval")
        result = evaluate_execution_request(req, approval)
        exit_code = 0 if result["decision"] == "ALLOW" else 2
    elif args.check_subagent:
        payload = json.loads(Path(args.check_subagent).read_text(encoding="utf-8-sig"))
        result = check_subagent_authorization(payload["parent_scope"], payload["subagent_request"])
        exit_code = 0 if result["decision"] == "ALLOW" else 2
    elif args.format_approval_request:
        payload = json.loads(Path(args.format_approval_request).read_text(encoding="utf-8-sig"))
        req = payload.get("request", payload)
        inferred_level, reasons = _infer_required_level(req)
        req_level = str(payload.get("required_level") or inferred_level)
        result = build_approval_contract(req, req_level, payload.get("blocking_reasons") or reasons)
        exit_code = 0
    elif args.verify_approval:
        payload = json.loads(Path(args.verify_approval).read_text(encoding="utf-8-sig"))
        req = payload.get("request", payload)
        approval = payload.get("approval")
        inferred_level, _ = _infer_required_level(req)
        req_level = str(payload.get("required_level") or inferred_level)
        ok, errs = _verify_approval(req, req_level, approval)
        result = {"status": "PASS" if ok else "BLOCKED", "valid": ok, "required_level": req_level, "errors": errs}
        exit_code = 0 if ok else 2
    else:
        parser.print_help()
        return 0

    rendered = json.dumps(result, indent=2, ensure_ascii=False)
    if args.out:
        out_path = Path(args.out)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(rendered + "\n", encoding="utf-8")
    print(rendered)
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
