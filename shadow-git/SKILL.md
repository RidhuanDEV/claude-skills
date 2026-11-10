---
name: shadow-git
description: Advanced Git Branching, Worktree Management, Parallel Multi-Agent Development, Independent Feature Integration, Forward Sync from Main, Pre-Pull Dry-Run Conflict & Semantic Risk Detection (git merge-tree), Safe Pull with Stash Protection, and 6-Point Safe Cleanup. Trigger with /shadow-git.
---

# Shadow Git v2.0 (`/shadow-git`) — Branching, Worktree & Parallel Multi-Agent Orchestrator

Use this skill whenever the **Monarch** asks to manage branches, create/inspect/clean Git worktrees, run parallel agents across isolated features, integrate completed branches independently into `main`, sync unfinished branches with `main`, pull safely, or predict/resolve merge conflicts.

- **Conditional Activation & Read-Only Default**: Do **not** execute Git synchronization or branch mutations automatically merely because a session starts. Always run read-only inspection/previews first (`health`, `predict-conflicts`, or commands without `--approve`) and require explicit **Monarch** authorization before merge, rebase, force-push, branch deletion, or worktree removal.
- **Detailed Architectural Reference**: Load [`references/WORKTREE-AND-PARALLEL-AGENTS.md`](references/WORKTREE-AND-PARALLEL-AGENTS.md) for the branching strategy matrix, worktree ownership manifest, conflict taxonomy, and recovery playbooks.

---

## 1. Natural-Language Intent to Command Routing (`scripts/git_orchestrator.py`)

| Monarch Natural-Language Intent | Orchestrator Command (`python ".../shadow-git/scripts/git_orchestrator.py" ...`) |
| :--- | :--- |
| *"Cek strategi branch repo ini"* | `detect-strategy --repo <path>` |
| *"Cek semua worktree dan branch aktif"* / *"Health report"* | `health --repo <path> --stale-days 14` |
| *"Buat worktree baru untuk fitur RAG"* | `worktree-create --repo <path> --branch feature-rag --path ../feature-rag --base main --agent Agent-RAG --task TASK-01 --allowed-paths rag/` |
| *"Kerjakan fitur A dan B secara paralel"* | `worktree-create` for each branch + `check-parallel-scope --repo <path> --base main` |
| *"Prediksi conflict sebelum merge"* | `predict-conflicts --repo <path> --source <feature-branch> --target main` |
| *"Branch C sudah selesai, cek apakah aman merge ke main"* | `integrate-feature --repo <path> --branch <branch-C> --target main` *(add `--approve` only after Monarch confirmation)* |
| *"Sync branch A dan B dengan main terbaru"* | `sync-from-main --repo <path> --branch <branch-A> --main main --strategy merge` *(add `--approve` to execute)* |
| *"Bersihkan worktree yang sudah selesai"* | `safe-cleanup --repo <path> --branch <branch-C> --target main --release-agent-lock` *(add `--approve` to execute)* |

---

## 2. Core Workflows (`FR-01` .. `FR-08`)

### A. Branching Strategy Detection (`FR-01`)
Never assume every project uses Git Flow. Run `detect-strategy` first to identify:
- **Trunk-Based (`main` only)**, **Short-Lived Feature Branches (GitHub Flow)**, **Long-Lived Feature/Research Branches**, **Release/Hotfix Branches**, or **Git Flow (`main` + `develop`)**.

### B. Git Worktree Lifecycle & Parallel Multi-Agent Isolation (`FR-02`, `FR-03`)
When multiple agents work in parallel (e.g., `Tejas/main`, `Tejas/feature-rag`, `Tejas/feature-sitaba`, `Tejas/feature-export`):
1. Create an isolated worktree per agent via `worktree-create` (automatically blocks if the branch is already checked out elsewhere or if the target directory is non-empty).
2. Each worktree registers an ownership & scope manifest (`.git/shadow-worktrees/agents_registry.json`) with `agent_id`, `task_id`, `allowed_paths`, and `depends_on_branches`.
3. Run `check-parallel-scope` to detect if two parallel worktrees are modifying the same shared file or violating their allowed path scope.
4. When pausing an agent's worktree, save state via `/handoff` (`shadow_handoff` MCP).

### C. Independent Feature Integration (`FR-04`)
When Branch C (`feature-export`) is completed while Branch A (`feature-rag`) and Branch B (`feature-sitaba`) are still in progress:
1. Run `integrate-feature --branch feature-export --target main` (Read-Only Preview) to verify:
   - Worktrees are clean (`0` uncommitted/untracked files).
   - Required `depends_on_branches` are already merged.
   - Zero Git conflicts (`git merge-tree --write-tree`) and semantic risks are listed.
2. Run `/shadow-test` and `/shadow-sec` inside Branch C's worktree.
3. Upon explicit **Monarch** approval, execute `integrate-feature --branch feature-export --target main --approve` (or open a PR per repository policy without bypassing protected branch rules).

### D. Forward Integration / Sync From Main (`FR-05`)
After Branch C merges into `main`, bring updated `main` into unfinished branches A and B:
1. Default to `--strategy merge` (`git merge --no-ff main`) for shared, published, or long-lived branches.
2. **Shared-Branch Rebase Guard**: `sync-from-main` automatically blocks `--strategy rebase` if the branch tracks a remote upstream or is marked shared (`SHARED_BRANCH_REBASE_BLOCKED`). Never force-push without explicit approval and risk disclosure.
3. Predicts conflicts and blocks if the target worktree has uncommitted/untracked changes (`DIRTY_WORKTREE_PROTECTED`).

### E. Enhanced Conflict Prediction: Git Conflicts vs Semantic Risks (`FR-06`)
`predict-conflicts` distinguishes:
- **Hard Git Conflicts**: Content conflicts, rename/delete conflicts, file mode changes, and divergent histories.
- **Semantic Integration Risks** (flagged even when Git merge is clean):
  - `PARALLEL_SCHEMA_MIGRATIONS`: Both branches added DB migration files (`/shadow-data`).
  - `API_CONTRACT_MODIFICATION`: Changes to `openapi.yaml`, routes, controllers, `.proto`, `.graphql` (`/shadow-api`).
  - `SHARED_CONFIGURATION_CHANGE`: Edits to `.env*`, `package.json`, `tsconfig.json`, `docker-compose.yml`.
  - `LOCKFILE_DIVERGENCE`: Concurrent lockfile updates.

### F. 6-Point Safe Cleanup Gate (`FR-08`)
`safe-cleanup` refuses to remove a worktree or delete a branch unless all 6 checks pass:
1. Zero staged or unstaged changes (`UNCOMMITTED_CHANGES`).
2. Zero untracked files (`UNTRACKED_FILES_PRESENT`).
3. Zero unmerged commits relative to target branch (`UNMERGED_COMMITS`).
4. Not checked out in another active worktree (`BRANCH_CHECKED_OUT_IN_WORKTREE`).
5. No active agent ownership lock unless `--release-agent-lock` is confirmed (`ACTIVE_AGENT_OWNERSHIP`), and zero ongoing `MERGE`/`REBASE`/`CHERRY_PICK` operations.
6. Explicit `--approve` flag provided after **Monarch** confirmation.

---

## 3. Preserved v1.0 Team Branch Sync & Conflict Resolution Protocol

### Phase 1: Safe Pre-Pull Reconnaissance (Zero Working-Tree Mutation)
```powershell
git status -sb
git branch -vv
git fetch --all --prune
git log HEAD..origin/<target-branch> --oneline --stat
git merge-tree --write-tree HEAD origin/<target-branch>
```

### Phase 2: Safe Pull Execution Protocol
- **Clean working tree & `0` conflicts**:
  - `0` ahead commits: `git pull --ff-only origin <target-branch>`
  - Diverged (`>0` ahead, `0` conflicts): `git pull --no-rebase origin <target-branch>`
- **Uncommitted local changes exist**:
  - Create an explicit named backup stash (including untracked files) only when authorized:
    ```powershell
    git stash push -u -m "shadow-pre-pull-backup-$(Get-Date -Format 'yyyyMMdd-HHmmss')"
    ```
  - Pull safely, then restore with `git stash pop` (never run implicit `stash drop`).

### Phase 3: Intelligent Collaborative Conflict Resolution
1. List conflicted files: `git diff --name-only --diff-filter=U`
2. Inspect both sides' commit intent:
   - `git log -p -n 3 HEAD -- <file>`
   - `git log -p -n 3 origin/<target-branch> -- <file>`
3. **Never Blindly Apply `--ours` or `--theirs` on Source Code**:
   - Combine both contracts cleanly (`0 any`, `0 as Type` casting, zero dead code).
   - Regenerate lockfiles via the package manager (`npm install --package-lock-only`) after merging manifests.
4. Verify resolution: `git diff --check` + run project typecheck, linter, and unit tests (`/shadow-test`).

---

## 4. Ecosystem Integration Boundaries (`FR-09`)

- **`/shadow-monarch`**: Enforces approval gates, strict typing during conflict resolution, and read-only default behavior.
- **`/shadow-plan`**: Maps `TASK-*` IDs and `depends_on_branches` to isolated worktrees.
- **`/shadow-test`**: Runs module & integration regression tests inside each worktree before `integrate-feature` and after `sync-from-main`.
- **`/shadow-sec`**: Runs secret scanning and ASVS access-control checks before merging into `main`.
- **`/shadow-release`**: Verifies release tags, migration backward compatibility, and rollback SHAs after `main` integration.
- **`/handoff`**: Persists worktree path, branch name, and active task state across AI agent sessions (`shadow_handoff` MCP).
