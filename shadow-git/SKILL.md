---
name: shadow-git
description: "Use when comparing or syncing Git branches, inspecting merge-tree conflicts, managing worktrees, or resolving merges."
---

# Shadow Git v2.0 (`/shadow-git`) — Branching, Worktrees & Parallel Multi-Agent Orchestrator

Use this skill whenever the **Monarch** asks to manage branches, create/inspect/clean Git worktrees, run parallel agents across isolated features, integrate completed branches independently into `main`, sync unfinished branches with `main`, pull safely, or predict/resolve merge conflicts.

- **Owner:** Branching strategy detection (`FR-01`), isolated Git worktree lifecycle & parallel path-ownership manifests (`FR-02`/`FR-03`), independent integration & safe forward-sync (`FR-04`/`FR-05`), `git merge-tree` + semantic risk prediction (`FR-06`), intent-preserving conflict resolution, and 6-point safe cleanup (`FR-08`).
- **Boundaries:** SemVer release tagging & production rollout (`shadow-release`), sprint task breakdown (`shadow-plan`), AI session context snapshots (`handoff`), and automated test suite authoring (`shadow-test`).

> [!CAUTION]
> **Read-Only Default (`L0` vs `L4`):** Never execute Git syncs or mutations merely because a session starts. Run read-only reconnaissance/previews first (`health`, `detect-strategy`, `predict-conflicts`, commands without `--approve`). Executing `--approve` merges, rebases, force-pushes, branch deletions, worktree removals, or `git push` is **`L4_HIGH_IMPACT`** requiring explicit **Monarch** approval (`shadow-monarch/scripts/execution_approval_gate.py`).

## Reference Guide

Load ONLY the 1–2 modular playbooks needed for the active Git collaboration subtask:

| Module | Topic | Load When |
| :--- | :--- | :--- |
| [01-branching-strategy-detection-and-safe-sync.md](references/01-branching-strategy-detection-and-safe-sync.md) | `detect-strategy`, read-only pre-pull reconnaissance, dirty-tree backup stash, `SHARED_BRANCH_REBASE_BLOCKED` guard | Pulling teammate updates, syncing feature branches with `main`, checking repo branch model |
| [02-worktrees-and-parallel-agent-ownership.md](references/02-worktrees-and-parallel-agent-ownership.md) | Sibling worktrees (`worktree-create`), `.git/shadow-worktrees/agents_registry.json`, disjoint `allowed_paths`, `check-parallel-scope`, independent integration | Coordinating parallel developers or multi-agent worktrees without collisions |
| [03-merge-tree-conflict-prediction-and-semantic-risks.md](references/03-merge-tree-conflict-prediction-and-semantic-risks.md) | `git merge-tree --write-tree`, Hard Git Conflicts vs 4 Semantic Risks (`PARALLEL_SCHEMA_MIGRATIONS`, `API_CONTRACT`, `CONFIG`, `LOCKFILE`), SHA freshness | Predicting merge conflicts and silent cross-branch regressions before merging |
| [04-collaborative-conflict-resolution-cleanup-and-recovery.md](references/04-collaborative-conflict-resolution-cleanup-and-recovery.md) | Two-sided `git log -p` resolution (zero blind `--ours`/`--theirs`), lockfile regeneration, 6-point `safe-cleanup`, `merge/rebase --abort` recovery | Resolving `UU` conflicts safely, cleaning finished worktrees, or recovering interrupted Git states |
| [evaluations.md](evaluations.md) | Graded specialist evaluation scenarios (`GIT-EVAL-01..07`) | Auditing dirty-tree safety, shared-branch rebase blocking, semantic risk checks, and cleanup gates |

---

## 1. Natural-Language Intent to Command Routing (`scripts/git_orchestrator.py`)

| Monarch Natural-Language Intent | Orchestrator Command (`python "shadow-git/scripts/git_orchestrator.py" ...`) |
| :--- | :--- |
| *"Cek strategi branch repo ini"* | `--repo <path> detect-strategy` |
| *"Cek semua worktree dan branch aktif"* / *"Health report"* | `--repo <path> health --stale-days 14` |
| *"Buat worktree baru untuk fitur RAG"* | `--repo <path> worktree-create --branch feature-rag --path ../feature-rag --base main --agent Agent-RAG --task TASK-01 --allowed-paths rag/` |
| *"Kerjakan fitur A dan B secara paralel"* | `worktree-create` per branch + `--repo <path> check-parallel-scope --base main` |
| *"Prediksi conflict sebelum merge"* | `--repo <path> predict-conflicts --source <feature-branch> --target main` |
| *"Branch C sudah selesai, cek apakah aman merge ke main"* | `--repo <path> integrate-feature --branch <branch-C> --target main` *(add `--approve` ONLY after Monarch `L4` confirmation)* |
| *"Sync branch A dan B dengan main terbaru"* | `--repo <path> sync-from-main --branch <branch-A> --main main --strategy merge` *(add `--approve` to execute)* |
| *"Bersihkan worktree yang sudah selesai"* | `--repo <path> safe-cleanup --branch <branch-C> --target main --release-agent-lock` *(add `--approve` to execute)* |

---

## 2. Core Non-Negotiable Collaboration Invariants

1. **Disjoint Path Ownership & Serialized Shared Contracts:** Partition parallel worktrees by disjoint `allowed_paths`; serialize shared contracts (`openapi.yaml`, `schema.prisma`, `package.json`, migration indexes) into a base branch or coordinator gate. Record both commit SHAs + merge base on every preview and re-resolve immediately before integration — re-run checks if either moved!
2. **Semantic Risks Even on Clean `merge-tree`:** Check `PARALLEL_SCHEMA_MIGRATIONS`, `API_CONTRACT_MODIFICATION`, `SHARED_CONFIGURATION_CHANGE`, and `LOCKFILE_DIVERGENCE`, and run producer/consumer contract + typecheck + test suites on the combined integrated tree even when touched paths are disjoint.
3. **Zero Blind `--ours`/`--theirs` & 6-Point Safe Cleanup:** Inspect both sides' `git log -p`, merge both intents cleanly (`0 any`/`0 as Type`), regenerate lockfiles via package manager, verify `git diff --check` + tests, and require all 6 checks (`0` uncommitted, `0` untracked, `0` unmerged commits, not checked out elsewhere, no active lock/merge/rebase, explicit `--approve`) before removing worktrees/branches.

```powershell
python -m unittest discover -s shadow-git/tests -v
```
