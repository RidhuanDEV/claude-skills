#!/usr/bin/env python3
"""
Shadow-Git v2.0 — Advanced Git Branching, Worktree & Parallel Development Orchestrator
Read-only by default. Supports:
- FR-01: Branching Strategy Detection (Trunk-Based, Short/Long-Lived Feature, Release/Hotfix, Git Flow)
- FR-02: Safe Git Worktree Lifecycle (add, list, remove, prune, dirty/untracked & checked-out guards)
- FR-03: Parallel Multi-Agent Isolation (agent ownership, allowed scope, shared-module overlap detection)
- FR-04: Independent Feature Integration (merge ready branch C into main while A & B continue)
- FR-05: Safe Forward Integration / Sync From Main (merge default, shared-branch rebase protection)
- FR-06: Enhanced Conflict Prediction (Git content/rename/mode conflicts vs Semantic risks: migrations, API, config, lockfiles)
- FR-07: Branch & Worktree Health Inspection (ahead/behind, upstream, dirty/untracked, stale threshold, readiness)
- FR-08: 6-Point Safe Cleanup Gate (never force-remove dirty/untracked/unmerged/active-agent worktrees)
- v1.0 Preservation: Pre-pull recon, backup stash, and conflict inspection.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

SKILL_ROOT = Path(__file__).resolve().parent.parent

SECRET_REDACT_PATTERNS = [
    re.compile(r"(https?://[^:\s]+:)([^@\s]+)(@)"),
    re.compile(r"\b(gh[pousr]_[A-Za-z0-9_]{20,})\b"),
    re.compile(r"\b(AKIA[0-9A-Z]{16})\b"),
]


def redact_secrets(text: str) -> str:
    out = text
    out = SECRET_REDACT_PATTERNS[0].sub(r"\1[REDACTED_TOKEN]\3", out)
    for pat in SECRET_REDACT_PATTERNS[1:]:
        out = pat.sub("[REDACTED_SECRET]", out)
    return out


def run_git(
    repo_dir: Path,
    args: list[str],
    check: bool = False,
) -> tuple[int, str, str]:
    """Run a git command in repo_dir and redact any credentials from stdout/stderr."""
    proc = subprocess.run(
        ["git", *args],
        cwd=str(repo_dir),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    out = redact_secrets(proc.stdout.strip())
    err = redact_secrets(proc.stderr.strip())
    if check and proc.returncode != 0:
        raise RuntimeError(f"git {' '.join(args)} failed (code {proc.returncode}): {err or out}")
    return proc.returncode, out, err


def get_git_common_dir(repo_dir: Path) -> Path:
    code, out, _ = run_git(repo_dir, ["rev-parse", "--git-common-dir"], check=True)
    p = Path(out)
    return p if p.is_absolute() else (repo_dir / p).resolve()


def get_registry_path(repo_dir: Path) -> Path:
    common = get_git_common_dir(repo_dir)
    reg_dir = common / "shadow-worktrees"
    reg_dir.mkdir(parents=True, exist_ok=True)
    return reg_dir / "agents_registry.json"


def load_agent_registry(repo_dir: Path) -> dict[str, Any]:
    reg_path = get_registry_path(repo_dir)
    if reg_path.exists():
        try:
            return json.loads(reg_path.read_text(encoding="utf-8"))
        except Exception:
            return {"worktrees": {}}
    return {"worktrees": {}}


def save_agent_registry(repo_dir: Path, data: dict[str, Any]) -> None:
    reg_path = get_registry_path(repo_dir)
    reg_path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


# ============================================================================
# FR-01: BRANCHING STRATEGY DETECTION
# ============================================================================
def detect_branching_strategy(repo_dir: Path) -> dict[str, Any]:
    _, branches_raw, _ = run_git(repo_dir, ["branch", "-a", "--format=%(refname:short)"])
    branches = [b.strip() for b in branches_raw.splitlines() if b.strip()]

    has_develop = any(b in ("develop", "dev", "origin/develop", "origin/dev") for b in branches)
    has_release = any(b.startswith(("release/", "origin/release/")) for b in branches)
    has_hotfix = any(b.startswith(("hotfix/", "origin/hotfix/")) for b in branches)
    feature_branches = [
        b for b in branches if b.startswith(("feature/", "feat/", "feature-", "feat-", "research/"))
    ]

    primary_trunk = "main"
    for candidate in ("main", "master", "trunk"):
        if candidate in branches or f"origin/{candidate}" in branches:
            primary_trunk = candidate
            break

    if has_develop and (has_release or has_hotfix):
        strategy = "git-flow"
    elif has_develop:
        strategy = "dual-branch-develop-main"
    elif has_release and not has_develop:
        strategy = "release-branching"
    elif len(feature_branches) > 0:
        strategy = "trunk-with-feature-branches"
    else:
        strategy = "trunk-based"

    return {
        "detected_strategy": strategy,
        "primary_trunk": primary_trunk,
        "integration_target": "develop" if has_develop else primary_trunk,
        "has_develop_branch": has_develop,
        "has_release_branches": has_release,
        "has_hotfix_branches": has_hotfix,
        "feature_branch_count": len(feature_branches),
        "all_branches": branches,
    }


# ============================================================================
# FR-02 & FR-07: WORKTREE & BRANCH HEALTH INSPECTION
# ============================================================================
def detect_ongoing_operations(wt_path: Path) -> list[str]:
    """Detect ongoing merge, rebase, cherry-pick, or bisect in a worktree."""
    code, git_dir_out, _ = run_git(wt_path, ["rev-parse", "--git-dir"])
    if code != 0:
        return []
    gdir = Path(git_dir_out)
    if not gdir.is_absolute():
        gdir = (wt_path / gdir).resolve()

    ops: list[str] = []
    if (gdir / "MERGE_HEAD").exists():
        ops.append("MERGE_IN_PROGRESS")
    if (gdir / "rebase-merge").exists() or (gdir / "rebase-apply").exists():
        ops.append("REBASE_IN_PROGRESS")
    if (gdir / "CHERRY_PICK_HEAD").exists():
        ops.append("CHERRY_PICK_IN_PROGRESS")
    if (gdir / "BISECT_LOG").exists():
        ops.append("BISECT_IN_PROGRESS")
    return ops


def inspect_worktree_status(wt_path: Path) -> dict[str, Any]:
    if not wt_path.exists():
        return {"exists": False, "dirty": False, "staged": 0, "unstaged": 0, "untracked": 0, "conflicted": 0, "modified_files": []}

    _, status_out, _ = run_git(wt_path, ["status", "--porcelain"])
    staged = 0
    unstaged = 0
    untracked = 0
    conflicted = 0
    modified_files: list[str] = []

    for line in status_out.splitlines():
        if len(line) < 3:
            continue
        xy = line[:2]
        fpath = line[3:].strip()
        modified_files.append(fpath)
        if xy in ("UU", "AA", "DD", "AU", "UA", "DU", "UD"):
            conflicted += 1
        elif xy == "??":
            untracked += 1
        else:
            if xy[0] not in (" ", "?"):
                staged += 1
            if xy[1] not in (" ", "?"):
                unstaged += 1

    ongoing = detect_ongoing_operations(wt_path)
    return {
        "exists": True,
        "dirty": (staged + unstaged + untracked + conflicted) > 0,
        "clean": (staged + unstaged + untracked + conflicted) == 0,
        "staged_count": staged,
        "unstaged_count": unstaged,
        "untracked_count": untracked,
        "conflicted_count": conflicted,
        "ongoing_operations": ongoing,
        "modified_files": modified_files,
    }


def list_worktrees_detailed(repo_dir: Path) -> list[dict[str, Any]]:
    _, out, _ = run_git(repo_dir, ["worktree", "list", "--porcelain"], check=True)
    registry = load_agent_registry(repo_dir).get("worktrees", {})

    worktrees: list[dict[str, Any]] = []
    current: dict[str, Any] = {}
    for line in out.splitlines() + [""]:
        if not line.strip():
            if current.get("path"):
                wt_path = Path(current["path"])
                st = inspect_worktree_status(wt_path)
                b_short = current.get("branch_short", "(detached)")
                agent_meta = registry.get(b_short) or registry.get(str(wt_path.resolve()))
                current["status"] = st
                current["agent_ownership"] = agent_meta
                worktrees.append(current)
            current = {}
            continue
        if line.startswith("worktree "):
            current["path"] = str(Path(line[len("worktree "):].strip()).resolve())
        elif line.startswith("HEAD "):
            current["head"] = line[len("HEAD "):].strip()
        elif line.startswith("branch "):
            ref = line[len("branch "):].strip()
            current["branch_ref"] = ref
            current["branch_short"] = ref.replace("refs/heads/", "")
        elif line == "detached":
            current["detached"] = True
            current["branch_short"] = "(detached)"
        elif line.startswith("locked"):
            current["locked"] = True
        elif line.startswith("prunable"):
            current["prunable"] = True

    return worktrees


def get_ahead_behind(repo_dir: Path, branch_a: str, branch_b: str) -> tuple[int, int]:
    """Return (ahead, behind) of branch_a relative to branch_b."""
    code, out, _ = run_git(repo_dir, ["rev-list", "--left-right", "--count", f"{branch_a}...{branch_b}"])
    if code != 0 or not out:
        return 0, 0
    parts = out.split()
    if len(parts) == 2:
        return int(parts[0]), int(parts[1])
    return 0, 0


def inspect_health_report(
    repo_dir: Path,
    target_branch: str | None = None,
    stale_days: int = 14,
) -> dict[str, Any]:
    """Generate comprehensive read-only Branch & Worktree Health Report (FR-07)."""
    strategy_info = detect_branching_strategy(repo_dir)
    base_target = target_branch or strategy_info["integration_target"]
    worktrees = list_worktrees_detailed(repo_dir)
    wt_by_branch = {w.get("branch_short"): w for w in worktrees if w.get("branch_short")}

    _, cur_branch, _ = run_git(repo_dir, ["branch", "--show-current"])
    _, fmt_out, _ = run_git(
        repo_dir,
        [
            "for-each-ref",
            "--format=%(refname:short)|%(upstream:short)|%(objectname:short)|%(committerdate:unix)|%(committerdate:iso8601)|%(subject)",
            "refs/heads/",
        ],
    )

    now_ts = int(time.time())
    branches_report: list[dict[str, Any]] = []

    for line in fmt_out.splitlines():
        if not line.strip():
            continue
        parts = line.split("|", 5)
        if len(parts) < 6:
            continue
        b_name, upstream, sha, ts_str, iso_date, subject = parts
        commit_ts = int(ts_str) if ts_str.isdigit() else now_ts
        age_days = round((now_ts - commit_ts) / 86400.0, 2)
        is_stale = age_days >= stale_days and b_name not in (base_target, "main", "master", "develop")

        ahead_target, behind_target = get_ahead_behind(repo_dir, b_name, base_target)
        ahead_up, behind_up = (get_ahead_behind(repo_dir, b_name, upstream) if upstream else (0, 0))

        wt_info = wt_by_branch.get(b_name)
        is_dirty = wt_info["status"]["dirty"] if wt_info else False

        # Quick conflict check against base_target
        has_conflict = False
        if b_name != base_target and ahead_target > 0:
            m_code, _, _ = run_git(repo_dir, ["merge-tree", "--write-tree", base_target, b_name])
            has_conflict = m_code != 0

        if b_name == base_target:
            rec_action = "PRIMARY_INTEGRATION_BRANCH"
            merge_ready = False
        elif is_dirty:
            rec_action = "COMMIT_OR_STASH_LOCAL_CHANGES"
            merge_ready = False
        elif has_conflict:
            rec_action = f"RESOLVE_CONFLICTS_WITH_{base_target.upper()}"
            merge_ready = False
        elif behind_target > 0 and ahead_target > 0:
            rec_action = f"SYNC_FROM_{base_target.upper()}_OR_INTEGRATE_IF_READY"
            merge_ready = True
        elif ahead_target > 0:
            rec_action = f"READY_FOR_INDEPENDENT_MERGE_INTO_{base_target.upper()}"
            merge_ready = True
        elif behind_target > 0:
            rec_action = f"FAST_FORWARD_FROM_{base_target.upper()}"
            merge_ready = False
        else:
            rec_action = "UP_TO_DATE"
            merge_ready = False

        branches_report.append({
            "branch": b_name,
            "is_current": b_name == cur_branch,
            "upstream": upstream or None,
            "has_upstream": bool(upstream),
            "ahead_of_upstream": ahead_up,
            "behind_upstream": behind_up,
            "ahead_of_target": ahead_target,
            "behind_target": behind_target,
            "diverged_from_target": ahead_target > 0 and behind_target > 0,
            "last_commit": {"sha": sha, "date": iso_date, "subject": subject, "age_days": age_days},
            "stale": is_stale,
            "stale_threshold_days": stale_days,
            "worktree_path": wt_info["path"] if wt_info else None,
            "dirty": is_dirty,
            "agent_owner": wt_info.get("agent_ownership") if wt_info else None,
            "potential_conflict_with_target": has_conflict,
            "merge_ready": merge_ready,
            "recommended_action": rec_action,
        })

    return {
        "repository": str(repo_dir.resolve()),
        "current_branch": cur_branch,
        "strategy": strategy_info,
        "integration_target": base_target,
        "worktrees": worktrees,
        "branches": branches_report,
    }


# ============================================================================
# FR-02 & FR-03: SAFE WORKTREE CREATION & PARALLEL MULTI-AGENT ISOLATION
# ============================================================================
def create_isolated_worktree(
    repo_dir: Path,
    branch_name: str,
    worktree_path: Path,
    base_ref: str = "HEAD",
    agent_id: str | None = None,
    task_id: str | None = None,
    allowed_paths: list[str] | None = None,
    depends_on_branches: list[str] | None = None,
) -> dict[str, Any]:
    """Safely create an isolated Git worktree and register agent task scope (FR-02, FR-03)."""
    worktrees = list_worktrees_detailed(repo_dir)
    for w in worktrees:
        if w.get("branch_short") == branch_name:
            raise RuntimeError(
                f"BRANCH_ALREADY_CHECKED_OUT: Branch '{branch_name}' is already checked out in worktree '{w['path']}'."
            )
        if Path(w["path"]).resolve() == worktree_path.resolve():
            raise RuntimeError(
                f"WORKTREE_PATH_IN_USE: Path '{worktree_path}' is already registered as a worktree for '{w.get('branch_short')}'."
            )

    if worktree_path.exists() and any(worktree_path.iterdir()):
        raise RuntimeError(f"TARGET_DIR_NOT_EMPTY: Worktree target directory '{worktree_path}' is not empty.")

    # Check if branch already exists locally
    code, _, _ = run_git(repo_dir, ["show-ref", "--verify", "--quiet", f"refs/heads/{branch_name}"])
    if code == 0:
        run_git(repo_dir, ["worktree", "add", str(worktree_path), branch_name], check=True)
    else:
        run_git(repo_dir, ["worktree", "add", "-b", branch_name, str(worktree_path), base_ref], check=True)

    reg = load_agent_registry(repo_dir)
    ownership_record = {
        "branch": branch_name,
        "worktree_path": str(worktree_path.resolve()),
        "agent_id": agent_id or "unassigned",
        "task_id": task_id,
        "allowed_paths": allowed_paths or ["*"],
        "depends_on_branches": depends_on_branches or [],
        "status": "ACTIVE",
        "created_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    }
    reg.setdefault("worktrees", {})[branch_name] = ownership_record
    save_agent_registry(repo_dir, reg)

    return {
        "status": "WORKTREE_CREATED",
        "branch": branch_name,
        "worktree_path": str(worktree_path.resolve()),
        "ownership": ownership_record,
    }


def check_parallel_agent_scopes(repo_dir: Path, base_branch: str = "main") -> dict[str, Any]:
    """Check all active worktrees for scope violations and overlapping file modifications across agents (FR-03)."""
    worktrees = list_worktrees_detailed(repo_dir)
    file_to_branches: dict[str, list[str]] = {}
    scope_violations: list[dict[str, Any]] = []

    for w in worktrees:
        b_name = w.get("branch_short", "")
        if not b_name or b_name in (base_branch, "(detached)"):
            continue
        wt_path = Path(w["path"])
        _, committed_diff, _ = run_git(repo_dir, ["diff", "--name-only", f"{base_branch}...{b_name}"])
        touched = set(f.strip() for f in committed_diff.splitlines() if f.strip())
        for mod_f in w.get("status", {}).get("modified_files", []):
            touched.add(mod_f)

        owner_meta = w.get("agent_ownership") or {}
        allowed = owner_meta.get("allowed_paths", ["*"])
        if "*" not in allowed:
            for tf in sorted(touched):
                if not any(tf.startswith(prefix.rstrip("*")) for prefix in allowed):
                    scope_violations.append({
                        "branch": b_name,
                        "agent_id": owner_meta.get("agent_id"),
                        "file": tf,
                        "allowed_paths": allowed,
                    })

        for tf in touched:
            file_to_branches.setdefault(tf, []).append(b_name)

    shared_overlaps = {
        f: branches for f, branches in file_to_branches.items() if len(branches) > 1
    }
    return {
        "base_branch": base_branch,
        "overlapping_files_across_worktrees": shared_overlaps,
        "has_overlapping_edits": len(shared_overlaps) > 0,
        "scope_violations": scope_violations,
        "has_scope_violations": len(scope_violations) > 0,
    }


# ============================================================================
# FR-06: ENHANCED CONFLICT PREDICTION & SEMANTIC RISK CLASSIFIER
# ============================================================================
def predict_conflicts_and_risks(
    repo_dir: Path,
    source_ref: str,
    target_ref: str,
) -> dict[str, Any]:
    """
    Predict both Git-level merge conflicts (via git merge-tree --write-tree)
    AND semantic integration risks (migrations, API specs, shared config, lockfiles) (FR-06).
    """
    code, mt_out, mt_err = run_git(repo_dir, ["merge-tree", "--write-tree", target_ref, source_ref])
    has_git_conflict = code != 0
    combined_mt = f"{mt_out}\n{mt_err}"

    content_conflicts: list[str] = []
    rename_delete_conflicts: list[str] = []
    mode_conflicts: list[str] = []

    for line in combined_mt.splitlines():
        if "CONFLICT (content):" in line:
            m = re.search(r"Merge conflict in (.+)$", line)
            content_conflicts.append(m.group(1).strip() if m else line)
        elif "CONFLICT (rename" in line or "CONFLICT (modify/delete" in line or "CONFLICT (delete" in line:
            rename_delete_conflicts.append(line.strip())
        elif "CONFLICT (file mode" in line or "mode" in line.lower() and "conflict" in line.lower():
            mode_conflicts.append(line.strip())

    # Inspect files changed on both sides since merge-base for semantic risks
    _, mb_out, _ = run_git(repo_dir, ["merge-base", target_ref, source_ref])
    merge_base = mb_out.strip()

    target_changed: set[str] = set()
    source_changed: set[str] = set()
    if merge_base:
        _, t_diff, _ = run_git(repo_dir, ["diff", "--name-only", f"{merge_base}..{target_ref}"])
        _, s_diff, _ = run_git(repo_dir, ["diff", "--name-only", f"{merge_base}..{source_ref}"])
        target_changed = {f.strip() for f in t_diff.splitlines() if f.strip()}
        source_changed = {f.strip() for f in s_diff.splitlines() if f.strip()}

    all_changed = target_changed | source_changed
    both_touched = target_changed & source_changed

    # Detect file mode changes explicitly
    _, mode_diff, _ = run_git(repo_dir, ["diff", "--summary", f"{target_ref}...{source_ref}"])
    for mline in mode_diff.splitlines():
        if "mode change" in mline:
            mode_conflicts.append(mline.strip())

    # Semantic risk classification
    migration_files = [
        f for f in all_changed
        if any(k in f.lower() for k in ("migration", "migrations/", "prisma/migrations", "alembic/versions", "flyway"))
    ]
    target_migrations = [f for f in target_changed if f in migration_files]
    source_migrations = [f for f in source_changed if f in migration_files]

    api_contract_files = [
        f for f in all_changed
        if any(
            k in f.lower()
            for k in ("openapi.yaml", "openapi.json", "swagger", "postman_collection", "routes", "controller", ".proto", ".graphql")
        )
    ]
    shared_config_files = [
        f for f in all_changed
        if any(
            k in f.lower()
            for k in (".env", "docker-compose", "dockerfile", "tsconfig", "package.json", "pyproject.toml", "go.mod", "cargo.toml")
        )
    ]
    lockfiles = [
        f for f in all_changed
        if any(
            f.lower().endswith(lk)
            for lk in ("package-lock.json", "pnpm-lock.yaml", "yarn.lock", "poetry.lock", "cargo.lock", "composer.lock", "go.sum")
        )
    ]

    semantic_risks: list[dict[str, Any]] = []
    if target_migrations and source_migrations:
        semantic_risks.append({
            "type": "PARALLEL_SCHEMA_MIGRATIONS",
            "severity": "HIGH",
            "target_files": target_migrations,
            "source_files": source_migrations,
            "recommendation": "Verify migration sequence numbers/timestamps and run full expand-contract DB migration test (/shadow-data).",
        })
    if api_contract_files:
        semantic_risks.append({
            "type": "API_CONTRACT_MODIFICATION",
            "severity": "MEDIUM",
            "files": api_contract_files,
            "recommendation": "Validate OpenAPI 3.1 spec and run consumer/provider contract tests (/shadow-api & /shadow-test).",
        })
    if shared_config_files:
        semantic_risks.append({
            "type": "SHARED_CONFIGURATION_CHANGE",
            "severity": "MEDIUM",
            "files": shared_config_files,
            "recommendation": "Review shared dependencies and environment variables for compatibility across active worktrees.",
        })
    if lockfiles and (set(lockfiles) & both_touched):
        semantic_risks.append({
            "type": "LOCKFILE_DIVERGENCE",
            "severity": "MEDIUM",
            "files": sorted(list(set(lockfiles) & both_touched)),
            "recommendation": "Never hand-edit lockfile conflict markers; merge manifest file first and regenerate lockfile via package manager.",
        })

    ahead, behind = get_ahead_behind(repo_dir, source_ref, target_ref)
    return {
        "source_ref": source_ref,
        "target_ref": target_ref,
        "merge_base": merge_base,
        "divergent_history": ahead > 0 and behind > 0,
        "source_ahead_of_target": ahead,
        "source_behind_target": behind,
        "has_git_conflicts": has_git_conflict,
        "git_conflicts": {
            "content_conflicts": content_conflicts,
            "rename_or_delete_conflicts": rename_delete_conflicts,
            "file_mode_changes": mode_conflicts,
        },
        "both_modified_files": sorted(list(both_touched)),
        "has_semantic_risks": len(semantic_risks) > 0,
        "semantic_risks": semantic_risks,
        "safe_to_merge_automatically": (not has_git_conflict) and ahead > 0,
    }


# ============================================================================
# FR-04: INDEPENDENT FEATURE INTEGRATION (Merge C while A & B remain in progress)
# ============================================================================
def integrate_feature_branch(
    repo_dir: Path,
    feature_branch: str,
    target_branch: str = "main",
    approve: bool = False,
) -> dict[str, Any]:
    """
    Evaluate or execute independent integration of a ready feature branch into target_branch
    without waiting for unrelated in-progress feature branches (FR-04).
    """
    worktrees = list_worktrees_detailed(repo_dir)
    wt_by_branch = {w.get("branch_short"): w for w in worktrees}

    # Check if feature_branch or target_branch has uncommitted changes in its worktree
    feat_wt = wt_by_branch.get(feature_branch)
    target_wt = wt_by_branch.get(target_branch)

    blockers: list[str] = []
    if feat_wt and feat_wt["status"]["dirty"]:
        blockers.append(f"Feature branch '{feature_branch}' has uncommitted/untracked files in worktree '{feat_wt['path']}'.")
    if target_wt and target_wt["status"]["dirty"]:
        blockers.append(f"Target branch '{target_branch}' has uncommitted/untracked files in worktree '{target_wt['path']}'.")

    # Check declared branch dependencies in agent registry
    reg = load_agent_registry(repo_dir).get("worktrees", {})
    feat_meta = reg.get(feature_branch, {})
    for dep_branch in feat_meta.get("depends_on_branches", []):
        ahead_dep, _ = get_ahead_behind(repo_dir, dep_branch, target_branch)
        if ahead_dep > 0:
            blockers.append(
                f"Required dependency branch '{dep_branch}' has {ahead_dep} unmerged commit(s) not yet in '{target_branch}'."
            )

    prediction = predict_conflicts_and_risks(repo_dir, feature_branch, target_branch)
    if prediction["has_git_conflicts"]:
        blockers.append(f"Git merge conflicts detected between '{feature_branch}' and '{target_branch}'.")
    if prediction["source_ahead_of_target"] == 0:
        blockers.append(f"Branch '{feature_branch}' has 0 new commits ahead of '{target_branch}'.")

    if not approve:
        return {
            "mode": "READ_ONLY_PREVIEW",
            "feature_branch": feature_branch,
            "target_branch": target_branch,
            "ready_to_integrate": len(blockers) == 0,
            "blockers": blockers,
            "conflict_and_risk_report": prediction,
            "message": "Pass --approve after Monarch authorization and test/security gate verification to execute merge.",
        }

    if blockers:
        raise RuntimeError(f"INTEGRATION_BLOCKED: {'; '.join(blockers)}")

    # Execute merge in target_wt if target_branch is checked out in a worktree, otherwise checkout in repo_dir
    exec_dir = Path(target_wt["path"]) if target_wt else repo_dir
    if not target_wt:
        run_git(exec_dir, ["checkout", target_branch], check=True)

    run_git(
        exec_dir,
        ["merge", "--no-ff", feature_branch, "-m", f"Merge branch '{feature_branch}' into {target_branch}"],
        check=True,
    )
    _, new_head, _ = run_git(exec_dir, ["rev-parse", "--short", "HEAD"], check=True)

    return {
        "mode": "EXECUTED",
        "status": "MERGED",
        "feature_branch": feature_branch,
        "target_branch": target_branch,
        "merge_commit": new_head,
        "semantic_risks_for_post_merge_verification": prediction["semantic_risks"],
    }


# ============================================================================
# FR-05: FORWARD INTEGRATION / SYNC FROM MAIN INTO ACTIVE FEATURE BRANCHES
# ============================================================================
def sync_feature_from_main(
    repo_dir: Path,
    feature_branch: str,
    main_branch: str = "main",
    strategy: str = "merge",
    allow_shared_rebase: bool = False,
    approve: bool = False,
) -> dict[str, Any]:
    """
    Bring latest changes from main_branch into an unfinished feature_branch (FR-05).
    Defaults to 'merge'. Protects shared/published branches from unsafe 'rebase'.
    """
    worktrees = list_worktrees_detailed(repo_dir)
    wt_by_branch = {w.get("branch_short"): w for w in worktrees}
    feat_wt = wt_by_branch.get(feature_branch)

    # Check if branch has an upstream or is marked shared
    _, upstream, _ = run_git(repo_dir, ["for-each-ref", "--format=%(upstream:short)", f"refs/heads/{feature_branch}"])
    reg = load_agent_registry(repo_dir).get("worktrees", {})
    is_shared = bool(upstream.strip()) or reg.get(feature_branch, {}).get("shared", False)

    blockers: list[str] = []
    if strategy == "rebase" and is_shared and not allow_shared_rebase:
        blockers.append(
            f"SHARED_BRANCH_REBASE_BLOCKED: Branch '{feature_branch}' tracks upstream '{upstream}' or is shared. "
            "Default to --strategy merge, or pass --allow-shared-rebase with explicit approval."
        )

    if feat_wt and feat_wt["status"]["dirty"]:
        blockers.append(
            f"DIRTY_WORKTREE_PROTECTED: Worktree '{feat_wt['path']}' for branch '{feature_branch}' has uncommitted/untracked changes. "
            "Commit or create an explicit backup stash before syncing."
        )

    prediction = predict_conflicts_and_risks(repo_dir, main_branch, feature_branch)
    if prediction["has_git_conflicts"]:
        blockers.append(
            f"CONFLICT_PREDICTED: Syncing '{main_branch}' into '{feature_branch}' will conflict on: "
            f"{prediction['git_conflicts']['content_conflicts'] or prediction['git_conflicts']['rename_or_delete_conflicts']}"
        )

    if not approve:
        return {
            "mode": "READ_ONLY_PREVIEW",
            "feature_branch": feature_branch,
            "main_branch": main_branch,
            "selected_strategy": strategy,
            "is_shared_or_published": is_shared,
            "safe_to_sync": len(blockers) == 0,
            "blockers": blockers,
            "prediction": prediction,
        }

    if blockers:
        raise RuntimeError(f"SYNC_BLOCKED: {'; '.join(blockers)}")

    exec_dir = Path(feat_wt["path"]) if feat_wt else repo_dir
    if not feat_wt:
        run_git(exec_dir, ["checkout", feature_branch], check=True)

    if strategy == "rebase":
        run_git(exec_dir, ["rebase", main_branch], check=True)
    else:
        run_git(
            exec_dir,
            ["merge", "--no-ff", main_branch, "-m", f"Sync '{main_branch}' into '{feature_branch}'"],
            check=True,
        )

    ahead, behind = get_ahead_behind(repo_dir, feature_branch, main_branch)
    return {
        "mode": "EXECUTED",
        "status": "SYNCED",
        "feature_branch": feature_branch,
        "main_branch": main_branch,
        "strategy_used": strategy,
        "ahead_of_main": ahead,
        "behind_main": behind,
    }


# ============================================================================
# FR-08: 6-POINT SAFE WORKTREE & BRANCH CLEANUP GATE
# ============================================================================
def safe_cleanup(
    repo_dir: Path,
    branch_name: str,
    target_branch: str = "main",
    remove_worktree: bool = True,
    delete_branch: bool = False,
    release_agent_lock: bool = False,
    approve: bool = False,
) -> dict[str, Any]:
    """
    Enforce the 6-Point Safety Gate before removing a worktree or branch (FR-08):
    1. Check staged, unstaged, and untracked changes.
    2. Check whether the branch is merged into its intended target.
    3. Check whether the branch is checked out in another worktree.
    4. Check whether another agent still owns/uses it.
    5. Detect ongoing merge, rebase, or cherry-pick operations.
    6. Require explicit --approve confirmation.
    """
    worktrees = list_worktrees_detailed(repo_dir)
    wt_by_branch = {w.get("branch_short"): w for w in worktrees}
    wt_info = wt_by_branch.get(branch_name)

    reg = load_agent_registry(repo_dir)
    agent_meta = reg.get("worktrees", {}).get(branch_name)

    blockers: list[str] = []

    # 1 & 5. Check dirty, untracked, and ongoing git operations
    if wt_info:
        st = wt_info["status"]
        if st["staged_count"] > 0 or st["unstaged_count"] > 0:
            blockers.append(
                f"UNCOMMITTED_CHANGES: Worktree '{wt_info['path']}' has {st['staged_count']} staged and {st['unstaged_count']} unstaged file(s)."
            )
        if st["untracked_count"] > 0:
            blockers.append(
                f"UNTRACKED_FILES_PRESENT: Worktree '{wt_info['path']}' has {st['untracked_count']} untracked file(s) ({st['modified_files']}). Never discard untracked work."
            )
        if st["ongoing_operations"]:
            blockers.append(
                f"ONGOING_GIT_OPERATION: Worktree '{wt_info['path']}' has active operation(s): {st['ongoing_operations']}."
            )

    # 2. Check whether branch is merged into target_branch
    ahead, _ = get_ahead_behind(repo_dir, branch_name, target_branch)
    if ahead > 0:
        blockers.append(
            f"UNMERGED_COMMITS: Branch '{branch_name}' has {ahead} commit(s) not merged into '{target_branch}'."
        )

    # 3. If deleting branch without removing worktree, check if checked out in any worktree
    if delete_branch and not remove_worktree and wt_info:
        blockers.append(
            f"BRANCH_CHECKED_OUT_IN_WORKTREE: Branch '{branch_name}' is currently checked out at '{wt_info['path']}'."
        )

    # 4. Check active agent ownership
    if agent_meta and agent_meta.get("status") == "ACTIVE" and not release_agent_lock:
        blockers.append(
            f"ACTIVE_AGENT_OWNERSHIP: Worktree/branch '{branch_name}' is actively owned by agent '{agent_meta.get('agent_id')}' (task '{agent_meta.get('task_id')}'). Pass --release-agent-lock when work is handed off or completed."
        )

    if not approve:
        return {
            "mode": "READ_ONLY_PREVIEW",
            "branch": branch_name,
            "worktree_path": wt_info["path"] if wt_info else None,
            "safe_to_clean": len(blockers) == 0,
            "blockers": blockers,
            "message": "Pass --approve to execute cleanup after verifying all 6 safety checks pass.",
        }

    if blockers:
        raise RuntimeError(f"SAFE_CLEANUP_BLOCKED: {'; '.join(blockers)}")

    actions_taken: list[str] = []
    if remove_worktree and wt_info:
        run_git(repo_dir, ["worktree", "remove", wt_info["path"]], check=True)
        run_git(repo_dir, ["worktree", "prune"], check=True)
        actions_taken.append(f"Removed worktree '{wt_info['path']}' and pruned stale metadata")

    if delete_branch:
        run_git(repo_dir, ["branch", "-d", branch_name], check=True)
        actions_taken.append(f"Deleted merged branch '{branch_name}'")

    if branch_name in reg.get("worktrees", {}):
        reg["worktrees"][branch_name]["status"] = "CLEANED_UP"
        save_agent_registry(repo_dir, reg)

    return {
        "mode": "EXECUTED",
        "status": "CLEANED",
        "branch": branch_name,
        "actions_taken": actions_taken,
    }


# ============================================================================
# SECTION 6: AUTOMATED ACCEPTANCE TEST SUITE (13 SCENARIOS IN TEMP REPOS)
# ============================================================================
def run_acceptance_suite() -> dict[str, Any]:
    results: list[dict[str, Any]] = []

    def record(test_id: str, name: str, passed: bool, evidence: dict[str, Any]) -> None:
        results.append({
            "test_id": test_id,
            "name": name,
            "status": "PASS" if passed else "FAIL",
            "evidence": evidence,
        })

    with tempfile.TemporaryDirectory(prefix="shadow_git_at_") as tmp_root_str:
        tmp_root = Path(tmp_root_str)
        origin_bare = tmp_root / "origin.git"
        main_repo = tmp_root / "Tejas" / "main"
        wt_a = tmp_root / "Tejas" / "feature-rag"
        wt_b = tmp_root / "Tejas" / "feature-sitaba"
        wt_c = tmp_root / "Tejas" / "feature-export"

        # Initialize bare remote + main repository
        origin_bare.mkdir(parents=True, exist_ok=True)
        run_git(origin_bare, ["init", "--bare"], check=True)

        main_repo.mkdir(parents=True, exist_ok=True)
        run_git(main_repo, ["init", "-b", "main"], check=True)
        run_git(main_repo, ["config", "user.name", "Shadow Architect"], check=True)
        run_git(main_repo, ["config", "user.email", "architect@shadow.local"], check=True)

        (main_repo / "README.md").write_text("# Tejas Enterprise Platform\n", encoding="utf-8")
        (main_repo / "shared.ts").write_text("export const VERSION = '1.0.0';\n", encoding="utf-8")
        run_git(main_repo, ["add", "."], check=True)
        run_git(main_repo, ["commit", "-m", "chore: initial main commit"], check=True)
        run_git(main_repo, ["remote", "add", "origin", str(origin_bare)], check=True)
        run_git(main_repo, ["push", "-u", "origin", "main"], check=True)

        # ---------------------------------------------------------------------
        # AT-01: Create three isolated feature worktrees (A: feature-rag, B: feature-sitaba, C: feature-export)
        # ---------------------------------------------------------------------
        res_a = create_isolated_worktree(
            main_repo, "feature-rag", wt_a, "main",
            agent_id="Agent-Alpha", task_id="TASK-RAG-01", allowed_paths=["rag/", "shared.ts"]
        )
        res_b = create_isolated_worktree(
            main_repo, "feature-sitaba", wt_b, "main",
            agent_id="Agent-Beta", task_id="TASK-SITABA-02", allowed_paths=["sitaba/", "migrations/"]
        )
        res_c = create_isolated_worktree(
            main_repo, "feature-export", wt_c, "main",
            agent_id="Agent-Gamma", task_id="TASK-EXPORT-03", allowed_paths=["export/", "openapi.yaml"]
        )
        wt_list = list_worktrees_detailed(main_repo)
        record(
            "AT-01",
            "Create three isolated feature worktrees (feature-rag, feature-sitaba, feature-export)",
            len(wt_list) == 4 and wt_a.exists() and wt_b.exists() and wt_c.exists(),
            {"worktree_count": len(wt_list), "branches": [w.get("branch_short") for w in wt_list]},
        )

        # ---------------------------------------------------------------------
        # AT-02: Detect a branch already checked out elsewhere
        # ---------------------------------------------------------------------
        duplicate_blocked = False
        try:
            create_isolated_worktree(main_repo, "feature-rag", tmp_root / "Tejas" / "dup-rag", "main")
        except RuntimeError as exc:
            if "BRANCH_ALREADY_CHECKED_OUT" in str(exc):
                duplicate_blocked = True
        record(
            "AT-02",
            "Detect and block checking out a branch already active in another worktree",
            duplicate_blocked,
            {"duplicate_checkout_blocked": duplicate_blocked},
        )

        # ---------------------------------------------------------------------
        # AT-03: Make independent commits in A, B, and C
        # ---------------------------------------------------------------------
        (wt_a / "rag").mkdir(exist_ok=True)
        (wt_a / "rag" / "retriever.ts").write_text("export const topK = 5;\n", encoding="utf-8")
        run_git(wt_a, ["add", "."], check=True)
        run_git(wt_a, ["commit", "-m", "feat(rag): add vector retriever"], check=True)

        (wt_b / "sitaba").mkdir(exist_ok=True)
        (wt_b / "sitaba" / "module.ts").write_text("export const sitabaEnabled = true;\n", encoding="utf-8")
        (wt_b / "migrations").mkdir(exist_ok=True)
        (wt_b / "migrations" / "002_sitaba.sql").write_text("CREATE TABLE sitaba (id INT);\n", encoding="utf-8")
        run_git(wt_b, ["add", "."], check=True)
        run_git(wt_b, ["commit", "-m", "feat(sitaba): add sitaba module and migration"], check=True)

        (wt_c / "export").mkdir(exist_ok=True)
        (wt_c / "export" / "docx.ts").write_text("export function exportDocx() { return true; }\n", encoding="utf-8")
        (wt_c / "openapi.yaml").write_text("openapi: 3.1.0\npaths:\n  /export: {}\n", encoding="utf-8")
        run_git(wt_c, ["add", "."], check=True)
        run_git(wt_c, ["commit", "-m", "feat(export): complete docx export and openapi spec"], check=True)

        ahead_a, _ = get_ahead_behind(main_repo, "feature-rag", "main")
        ahead_b, _ = get_ahead_behind(main_repo, "feature-sitaba", "main")
        ahead_c, _ = get_ahead_behind(main_repo, "feature-export", "main")
        record(
            "AT-03",
            "Make independent commits in worktrees A, B, and C with isolated git states",
            ahead_a == 1 and ahead_b == 1 and ahead_c == 1,
            {"ahead_a": ahead_a, "ahead_b": ahead_b, "ahead_c": ahead_c},
        )

        # ---------------------------------------------------------------------
        # AT-04: Integrate C into main independently without merging A or B
        # ---------------------------------------------------------------------
        preview_c = integrate_feature_branch(main_repo, "feature-export", "main", approve=False)
        merged_c = integrate_feature_branch(main_repo, "feature-export", "main", approve=True)
        run_git(main_repo, ["push", "origin", "main"], check=True)

        ahead_a_after, behind_a_after = get_ahead_behind(main_repo, "feature-rag", "main")
        ahead_b_after, behind_b_after = get_ahead_behind(main_repo, "feature-sitaba", "main")
        ahead_c_after, _ = get_ahead_behind(main_repo, "feature-export", "main")
        record(
            "AT-04",
            "Integrate completed branch C (feature-export) into main while A and B remain unmerged",
            preview_c["ready_to_integrate"]
            and merged_c["status"] == "MERGED"
            and ahead_c_after == 0
            and ahead_a_after == 1
            and behind_a_after > 0
            and ahead_b_after == 1,
            {
                "c_merged_commit": merged_c["merge_commit"],
                "a_ahead_behind_main": [ahead_a_after, behind_a_after],
                "b_ahead_behind_main": [ahead_b_after, behind_b_after],
            },
        )

        # ---------------------------------------------------------------------
        # AT-05: Report ahead/behind, missing upstream, and divergent history accurately
        # ---------------------------------------------------------------------
        health_before_sync = inspect_health_report(main_repo, target_branch="main", stale_days=14)
        b_map = {b["branch"]: b for b in health_before_sync["branches"]}
        at05_pass = (
            b_map["feature-rag"]["diverged_from_target"] is True
            and b_map["feature-rag"]["ahead_of_target"] == 1
            and b_map["feature-rag"]["behind_target"] >= 1
            and b_map["feature-rag"]["has_upstream"] is False
            and b_map["main"]["has_upstream"] is True
        )
        record(
            "AT-05",
            "Report ahead/behind counts, missing upstream, and divergent history accurately",
            at05_pass,
            {
                "feature_rag_ahead": b_map["feature-rag"]["ahead_of_target"],
                "feature_rag_behind": b_map["feature-rag"]["behind_target"],
                "feature_rag_diverged": b_map["feature-rag"]["diverged_from_target"],
                "feature_rag_has_upstream": b_map["feature-rag"]["has_upstream"],
            },
        )

        # ---------------------------------------------------------------------
        # AT-06: Protect a shared/published branch from unsafe automatic rebase
        # ---------------------------------------------------------------------
        run_git(wt_a, ["push", "-u", "origin", "feature-rag"], check=True)
        rebase_preview = sync_feature_from_main(
            main_repo, "feature-rag", "main", strategy="rebase", allow_shared_rebase=False, approve=False
        )
        shared_rebase_blocked = (not rebase_preview["safe_to_sync"]) and any(
            "SHARED_BRANCH_REBASE_BLOCKED" in b for b in rebase_preview["blockers"]
        )
        record(
            "AT-06",
            "Protect a published/shared branch from unsafe automatic rebase onto main",
            shared_rebase_blocked,
            {"safe_to_sync": rebase_preview["safe_to_sync"], "blockers": rebase_preview["blockers"]},
        )

        # ---------------------------------------------------------------------
        # AT-07: Handle dirty worktrees safely during sync (never overwrite uncommitted work)
        # ---------------------------------------------------------------------
        (wt_a / "rag" / "uncommitted_draft.ts").write_text("// draft work in progress\n", encoding="utf-8")
        dirty_sync_preview = sync_feature_from_main(
            main_repo, "feature-rag", "main", strategy="merge", approve=False
        )
        dirty_blocked = (not dirty_sync_preview["safe_to_sync"]) and any(
            "DIRTY_WORKTREE_PROTECTED" in b for b in dirty_sync_preview["blockers"]
        )
        # Clean up the temporary draft file into a stash or remove after verifying protection
        (wt_a / "rag" / "uncommitted_draft.ts").unlink()
        record(
            "AT-07",
            "Block sync/merge from overwriting uncommitted or untracked files in a dirty worktree",
            dirty_blocked,
            {"dirty_worktree_blocked": dirty_blocked, "blockers": dirty_sync_preview["blockers"]},
        )

        # ---------------------------------------------------------------------
        # AT-08: Synchronize updated main (with C) into unfinished branches A and B safely
        # ---------------------------------------------------------------------
        sync_a = sync_feature_from_main(main_repo, "feature-rag", "main", strategy="merge", approve=True)
        sync_b = sync_feature_from_main(main_repo, "feature-sitaba", "main", strategy="merge", approve=True)
        c_file_in_a = (wt_a / "export" / "docx.ts").exists()
        c_file_in_b = (wt_b / "export" / "docx.ts").exists()
        record(
            "AT-08",
            "Synchronize updated main (containing C) into unfinished branches A and B via safe merge",
            sync_a["status"] == "SYNCED"
            and sync_b["status"] == "SYNCED"
            and sync_a["behind_main"] == 0
            and sync_b["behind_main"] == 0
            and c_file_in_a
            and c_file_in_b,
            {
                "a_behind_main": sync_a["behind_main"],
                "b_behind_main": sync_b["behind_main"],
                "c_changes_present_in_a_and_b": c_file_in_a and c_file_in_b,
            },
        )

        # ---------------------------------------------------------------------
        # AT-09: Predict a real content conflict AND semantic integration risk (parallel migrations)
        # ---------------------------------------------------------------------
        # Modify shared.ts conflictingly in main and feature-rag, plus add a migration in main
        (main_repo / "shared.ts").write_text("export const VERSION = '2.0.0-main';\n", encoding="utf-8")
        (main_repo / "migrations").mkdir(exist_ok=True)
        (main_repo / "migrations" / "001_main_init.sql").write_text("CREATE TABLE users (id INT);\n", encoding="utf-8")
        run_git(main_repo, ["add", "."], check=True)
        run_git(main_repo, ["commit", "-m", "feat(main): bump shared version and add 001 migration"], check=True)

        (wt_a / "shared.ts").write_text("export const VERSION = '1.5.0-rag-custom';\n", encoding="utf-8")
        run_git(wt_a, ["add", "."], check=True)
        run_git(wt_a, ["commit", "-m", "feat(rag): customize shared version"], check=True)

        pred_a = predict_conflicts_and_risks(main_repo, "feature-rag", "main")
        pred_b = predict_conflicts_and_risks(main_repo, "feature-sitaba", "main")
        has_migration_risk = any(r["type"] == "PARALLEL_SCHEMA_MIGRATIONS" for r in pred_b["semantic_risks"])

        record(
            "AT-09",
            "Predict real content conflict (shared.ts) and semantic migration risk (001 vs 002 SQL)",
            pred_a["has_git_conflicts"]
            and ("shared.ts" in pred_a["git_conflicts"]["content_conflicts"])
            and (not pred_b["has_git_conflicts"])
            and has_migration_risk,
            {
                "a_content_conflicts": pred_a["git_conflicts"]["content_conflicts"],
                "b_git_conflict": pred_b["has_git_conflicts"],
                "b_semantic_risks": [r["type"] for r in pred_b["semantic_risks"]],
            },
        )

        # ---------------------------------------------------------------------
        # AT-10: Block destructive cleanup without approval or when active agent owns worktree
        # ---------------------------------------------------------------------
        cleanup_no_approve = safe_cleanup(
            main_repo, "feature-export", target_branch="main", remove_worktree=True, delete_branch=True, approve=False
        )
        active_agent_blocked = False
        try:
            safe_cleanup(
                main_repo, "feature-export", target_branch="main",
                remove_worktree=True, delete_branch=True, release_agent_lock=False, approve=True
            )
        except RuntimeError as exc:
            if "ACTIVE_AGENT_OWNERSHIP" in str(exc):
                active_agent_blocked = True

        record(
            "AT-10",
            "Block cleanup when approval is omitted or when active agent still owns worktree",
            cleanup_no_approve["mode"] == "READ_ONLY_PREVIEW" and active_agent_blocked,
            {
                "preview_only_without_approve": cleanup_no_approve["mode"] == "READ_ONLY_PREVIEW",
                "active_agent_ownership_blocked": active_agent_blocked,
            },
        )

        # ---------------------------------------------------------------------
        # AT-11: Preserve untracked files during cleanup (block removal of worktree with untracked files)
        # ---------------------------------------------------------------------
        untracked_note = wt_c / "UNTRACKED_AGENT_NOTES.md"
        untracked_note.write_text("Important local research notes\n", encoding="utf-8")
        untracked_blocked = False
        try:
            safe_cleanup(
                main_repo, "feature-export", target_branch="main",
                remove_worktree=True, delete_branch=True, release_agent_lock=True, approve=True
            )
        except RuntimeError as exc:
            if "UNTRACKED_FILES_PRESENT" in str(exc):
                untracked_blocked = True

        file_still_intact = untracked_note.exists()
        untracked_note.unlink()
        record(
            "AT-11",
            "Preserve untracked files during cleanup by blocking worktree removal",
            untracked_blocked and file_still_intact,
            {"untracked_removal_blocked": untracked_blocked, "untracked_file_preserved": file_still_intact},
        )

        # ---------------------------------------------------------------------
        # AT-12: Execute safe cleanup of merged worktree C once clean and agent lock released
        # ---------------------------------------------------------------------
        clean_res = safe_cleanup(
            main_repo, "feature-export", target_branch="main",
            remove_worktree=True, delete_branch=True, release_agent_lock=True, approve=True
        )
        record(
            "AT-12",
            "Safely remove worktree and branch for completed/merged feature C after all 6 checks pass",
            clean_res["status"] == "CLEANED" and not wt_c.exists(),
            {"actions_taken": clean_res["actions_taken"], "wt_c_removed": not wt_c.exists()},
        )

        # ---------------------------------------------------------------------
        # AT-13: Verify existing v1.0 /shadow-git workflow (fetch, merge-tree, backup stash + pop)
        # ---------------------------------------------------------------------
        (wt_b / "sitaba" / "local_wip.ts").write_text("export const wip = 1;\n", encoding="utf-8")
        run_git(wt_b, ["stash", "push", "-u", "-m", "shadow-pre-pull-backup-test"], check=True)
        _, stash_list, _ = run_git(wt_b, ["stash", "list"], check=True)
        has_named_stash = "shadow-pre-pull-backup-test" in stash_list
        run_git(wt_b, ["stash", "pop"], check=True)
        restored_ok = (wt_b / "sitaba" / "local_wip.ts").exists()
        record(
            "AT-13",
            "Verify existing v1.0 /shadow-git named backup stash (git stash push -u) and restoration",
            has_named_stash and restored_ok,
            {"named_backup_stash_created": has_named_stash, "untracked_wip_restored": restored_ok},
        )

    passed_count = sum(1 for r in results if r["status"] == "PASS")
    return {
        "suite": "Shadow-Git v2.0 Acceptance Test Suite",
        "executed_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "total_tests": len(results),
        "passed": passed_count,
        "failed": len(results) - passed_count,
        "all_passed": passed_count == len(results),
        "results": results,
    }


# ============================================================================
# CLI ROUTER
# ============================================================================
def main() -> int:
    parser = argparse.ArgumentParser(description="Shadow-Git v2.0 — Branching, Worktree & Parallel Development CLI")
    parser.add_argument("--repo", default=".", help="Path to Git repository (default: current directory)")
    parser.add_argument("--selftest", action="store_true", help="Run quick environment & Git version check")
    parser.add_argument("--acceptance-suite", action="store_true", help="Run all 13 isolated temp-repo acceptance tests")

    sub = parser.add_subparsers(dest="cmd")

    sub.add_parser("detect-strategy", help="[FR-01] Detect repository branching strategy and primary integration target")

    p_health = sub.add_parser("health", help="[FR-07] Generate read-only Branch & Worktree Health Report")
    p_health.add_argument("--target", default=None, help="Target integration branch (auto-detected if omitted)")
    p_health.add_argument("--stale-days", type=int, default=14, help="Days threshold for stale indicator (default: 14)")

    p_wt_add = sub.add_parser("worktree-create", help="[FR-02/FR-03] Create an isolated worktree with agent ownership scope")
    p_wt_add.add_argument("--branch", required=True, help="Feature branch name")
    p_wt_add.add_argument("--path", required=True, help="Target worktree directory path")
    p_wt_add.add_argument("--base", default="HEAD", help="Base ref to branch from (default: HEAD)")
    p_wt_add.add_argument("--agent", default="Shadow-Agent", help="Assigned agent ID")
    p_wt_add.add_argument("--task", default=None, help="Assigned task/story ID")
    p_wt_add.add_argument("--allowed-paths", nargs="*", default=["*"], help="Allowed directory/file prefixes")
    p_wt_add.add_argument("--depends-on", nargs="*", default=[], help="Upstream feature branches required before merge")

    sub.add_parser("worktree-list", help="[FR-02/FR-03] List all worktrees with dirty status and agent ownership")

    p_scope = sub.add_parser("check-parallel-scope", help="[FR-03] Check parallel worktrees for scope violations & shared file overlaps")
    p_scope.add_argument("--base", default="main", help="Base branch (default: main)")

    p_pred = sub.add_parser("predict-conflicts", help="[FR-06] Predict Git conflicts & semantic risks between two refs")
    p_pred.add_argument("--source", required=True, help="Source branch/ref")
    p_pred.add_argument("--target", required=True, help="Target branch/ref")

    p_int = sub.add_parser("integrate-feature", help="[FR-04] Independently integrate a completed feature branch into target")
    p_int.add_argument("--branch", required=True, help="Completed feature branch")
    p_int.add_argument("--target", default="main", help="Target branch (default: main)")
    p_int.add_argument("--approve", action="store_true", help="Execute merge (if omitted, runs read-only preview)")

    p_sync = sub.add_parser("sync-from-main", help="[FR-05] Forward-integrate latest main into an unfinished feature branch")
    p_sync.add_argument("--branch", required=True, help="Unfinished feature branch")
    p_sync.add_argument("--main", default="main", help="Main/integration branch (default: main)")
    p_sync.add_argument("--strategy", choices=["merge", "rebase"], default="merge", help="Sync strategy (default: merge)")
    p_sync.add_argument("--allow-shared-rebase", action="store_true", help="Explicitly allow rebasing a shared/published branch")
    p_sync.add_argument("--approve", action="store_true", help="Execute sync (if omitted, runs read-only preview)")

    p_clean = sub.add_parser("safe-cleanup", help="[FR-08] Safely remove a completed worktree and/or merged branch")
    p_clean.add_argument("--branch", required=True, help="Branch to clean up")
    p_clean.add_argument("--target", default="main", help="Target branch where commits must be merged (default: main)")
    p_clean.add_argument("--keep-worktree", action="store_true", help="Do not remove the worktree directory")
    p_clean.add_argument("--delete-branch", action="store_true", help="Also delete the local branch ref (git branch -d)")
    p_clean.add_argument("--release-agent-lock", action="store_true", help="Confirm agent ownership lock can be released")
    p_clean.add_argument("--approve", action="store_true", help="Execute cleanup (if omitted, runs read-only preview)")

    args = parser.parse_args()
    repo_dir = Path(args.repo).resolve()

    if args.selftest:
        _, ver, _ = run_git(Path.cwd(), ["--version"], check=True)
        print(json.dumps({"status": "PASS", "git_version": ver, "orchestrator": "Shadow-Git v2.0"}, indent=2))
        return 0

    if args.acceptance_suite:
        summary = run_acceptance_suite()
        out_dir = SKILL_ROOT / "output"
        out_dir.mkdir(parents=True, exist_ok=True)
        (out_dir / "acceptance_report_git_v2.json").write_text(
            json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8"
        )
        print(json.dumps(summary, indent=2, ensure_ascii=False))
        return 0 if summary["all_passed"] else 1

    try:
        if args.cmd == "detect-strategy":
            print(json.dumps(detect_branching_strategy(repo_dir), indent=2, ensure_ascii=False))
            return 0
        if args.cmd == "health":
            print(json.dumps(inspect_health_report(repo_dir, args.target, args.stale_days), indent=2, ensure_ascii=False))
            return 0
        if args.cmd == "worktree-create":
            res = create_isolated_worktree(
                repo_dir,
                args.branch,
                Path(args.path),
                args.base,
                args.agent,
                args.task,
                args.allowed_paths,
                args.depends_on,
            )
            print(json.dumps(res, indent=2, ensure_ascii=False))
            return 0
        if args.cmd == "worktree-list":
            print(json.dumps(list_worktrees_detailed(repo_dir), indent=2, ensure_ascii=False))
            return 0
        if args.cmd == "check-parallel-scope":
            print(json.dumps(check_parallel_agent_scopes(repo_dir, args.base), indent=2, ensure_ascii=False))
            return 0
        if args.cmd == "predict-conflicts":
            print(json.dumps(predict_conflicts_and_risks(repo_dir, args.source, args.target), indent=2, ensure_ascii=False))
            return 0
        if args.cmd == "integrate-feature":
            res = integrate_feature_branch(repo_dir, args.branch, args.target, args.approve)
            print(json.dumps(res, indent=2, ensure_ascii=False))
            return 0
        if args.cmd == "sync-from-main":
            res = sync_feature_from_main(
                repo_dir, args.branch, args.main, args.strategy, args.allow_shared_rebase, args.approve
            )
            print(json.dumps(res, indent=2, ensure_ascii=False))
            return 0
        if args.cmd == "safe-cleanup":
            res = safe_cleanup(
                repo_dir,
                args.branch,
                args.target,
                remove_worktree=not args.keep_worktree,
                delete_branch=args.delete_branch,
                release_agent_lock=args.release_agent_lock,
                approve=args.approve,
            )
            print(json.dumps(res, indent=2, ensure_ascii=False))
            return 0
    except Exception as exc:
        print(json.dumps({"status": "ERROR", "error": str(exc)}, indent=2, ensure_ascii=False))
        return 1

    parser.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
