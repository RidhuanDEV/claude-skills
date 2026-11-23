# 04 — Collaborative Conflict Resolution, 6-Point Safe Cleanup & Git Recovery

## 1. Purpose & Activation Conditions
Resolve merge conflicts **without ever overwriting a teammate's logic**, remove finished worktrees/branches safely via the **6-Point Safe Cleanup Gate**, and recover cleanly from interrupted merges, rebases, or stash conflicts without corrupting `.git/` internals. Activate when resolving `UU` conflict markers, cleaning up finished feature worktrees, or rescuing an interrupted Git state.

## 2. Prerequisites
- Active conflict state (`git diff --name-only --diff-filter=U`) or candidate finished branch/worktree for cleanup.
- Explicit **Monarch `L4` approval (`--approve`)** before any branch deletion, worktree removal, or force cleanup!

## 3. Technical Principles & Constraints
- **Phase 3: Intent-Preserving Conflict Resolution (ZERO Blind `--ours` / `--theirs`!):**
  1. List all unmerged conflicted files: `git diff --name-only --diff-filter=U`.
  2. Read **BOTH** sides' actual commit history & intent BEFORE editing a single conflict marker:
     - `git log -p -n 3 HEAD -- <file>`
     - `git log -p -n 3 origin/<branch> -- <file>`
  3. **NEVER blindly run `git checkout --ours` or `--theirs` on source code!** Combine BOTH the Monarch's and the teammate's business invariants cleanly with strict typing (`0 any`, `0 as Type`, `0 !`, zero dead code).
  4. **Lockfile Conflict Rule:** NEVER hand-edit conflict markers inside `package-lock.json`, `pnpm-lock.yaml`, `uv.lock`, or `go.sum`! Resolve `package.json` / `pyproject.toml` / `go.mod` cleanly first, then regenerate the lockfile via the package manager (`npm install --package-lock-only`, `pnpm install --lockfile-only`, `uv lock`, `go mod tidy`).
  5. **Post-Resolution Proof:** Run `git diff --check` (guarantees zero stray `<<<<<<<` conflict markers or whitespace errors!), then run typecheck, linter, and unit/integration tests (`/shadow-test`)!
- **6-Point Safe Cleanup Gate (`FR-08` — `safe-cleanup`):** Refuses to remove a worktree or delete a branch unless ALL 6 conditions pass:
  1. Zero staged or unstaged edits (`UNCOMMITTED_CHANGES`).
  2. Zero untracked files (`UNTRACKED_FILES_PRESENT`).
  3. Zero unmerged commits relative to target branch (`UNMERGED_COMMITS`).
  4. Branch not checked out in another active worktree (`BRANCH_CHECKED_OUT_IN_WORKTREE`).
  5. No active agent ownership lock (unless `--release-agent-lock` explicitly confirmed) AND zero in-progress `MERGE`/`REBASE`/`CHERRY_PICK` state!
  6. Explicit `--approve` flag passed ONLY after Monarch `L4` confirmation!
- **Safe Recovery Discipline:** Never delete `.git/rebase-merge`, `.git/MERGE_HEAD`, or run `git reset --hard` / `git stash drop` blindly! Use Git's built-in transactional abort/prune commands (`git merge --abort`, `git rebase --abort`, `git worktree prune`) and remember `git reflog` preserves local reachable commits for ~30 days if recovery is ever needed!

## 4. Architecture & Implementation

### Collaborative Conflict Resolution & Safe Cleanup Commands (PowerShell)
```powershell
# 1. Inspect conflicted files & BOTH commit intents before editing
git diff --name-only --diff-filter=U
git log -p -n 3 HEAD -- src/orders/service.ts
git log -p -n 3 origin/main -- src/orders/service.ts

# 2. Verify zero leftover conflict markers after manual intent-preserving merge
git diff --check

# 3. Preview 6-Point Safe Cleanup (L0 read-only; add --approve ONLY after Monarch L4 confirmation!)
python "shadow-git/scripts/git_orchestrator.py" --repo . safe-cleanup `
  --branch feature-export `
  --target main `
  --release-agent-lock
```

### Git Troubleshooting & Non-Destructive Recovery Matrix

| Interrupted / Broken Git State | Safe Recovery Procedure | NEVER Do This |
| :--- | :--- | :--- |
| **Interrupted Merge (`MERGE_IN_PROGRESS`)** | `git status`; abort cleanly with `git merge --abort` to restore pre-merge state | Deleting `.git/MERGE_HEAD` manually |
| **Interrupted Rebase (`REBASE_IN_PROGRESS`)** | Run `git rebase --abort` inside the affected worktree | Deleting `.git/rebase-merge/` manually |
| **Worktree folder deleted externally** | `git worktree list` -> `git worktree prune --verbose` | Leaving stale locks in `.git/worktrees/` |
| **Conflict during `git stash pop` (`UU`)** | Git KEEPS the stash entry safely! Resolve markers -> `git diff --check` -> run tests -> ONLY then `git stash drop` | Running `git stash drop` before verifying resolution |
| **Committed to wrong feature branch** | `git cherry-pick <sha>` onto correct worktree/branch first, verify commit exists, then safely move branch pointer | Running `git reset --hard HEAD~1` with uncommitted files |

## 5. Platform/Vendor Variations
- **Git `rerere` (Reuse Recorded Resolution):** On long-lived parallel branches, enabling `git config rerere.enabled true` lets Git remember verified conflict resolutions cleanly during repeated forward-syncs — still review every auto-applied resolution with `git diff` + tests!
- **Three-Way Diff Style (`zdiff3`):** Set `git config merge.conflictStyle zdiff3` so conflict blocks display **common ancestor (`|||||||`)** alongside `HEAD` and incoming changes — makes understanding what BOTH sides intentionally changed 3x clearer!

## 6. Decision Matrix & Trade-Offs

| Resolution / Cleanup Action | Safety Level | Requires `L4` Monarch Approval? |
| :--- | :---: | :---: |
| **`git status`, `git log -p`, `git diff --check`, `safe-cleanup` preview** | `L0_READ_ONLY` | No |
| **Intent-preserving edit of conflicted source files + local tests** | `L1` (in active merge task) | No (when merge itself was approved) |
| **`safe-cleanup --approve`, `git branch -D`, `git worktree remove --force`, `git push --force`** | **`L4_HIGH_IMPACT`** | **YES (Mandatory!)** |

## 7. Real Production Scenario
During a busy sprint sync, a developer hit a conflict in `src/auth/middleware.ts` and ran `git checkout --ours src/auth/middleware.ts` to clear the error quickly — silently reverting a critical tenant-IDOR fix a teammate had merged 2 hours earlier! Switching to mandatory two-sided `git log -p` inspection (`zdiff3`), `git diff --check`, and full `/shadow-test` + `/shadow-sec` verification before committing merge resolutions caught 100% of overlapping security invariants on subsequent merges.

## 8. Failure Modes & Edge Cases
- **WRONG:** Hand-editing 2,000 lines of conflict markers inside `package-lock.json` (creates subtly broken dependency hashes that fail `npm ci` in CI!).
  **RIGHT:** Merge `package.json` cleanly, then regenerate `package-lock.json` via `npm install --package-lock-only` and run `npm ci` to prove lockfile integrity.
- **WRONG:** Deleting a feature branch with `git branch -D` before confirming all its commits landed in `main` or verifying `0` untracked WIP files in its worktree.
  **RIGHT:** Always use the 6-Point Safe Cleanup Gate (`git_orchestrator.py safe-cleanup`).

## 9. Testing & Verification
- Always execute `git diff --check` + full project typecheck + affected `/shadow-test` suites after resolving any conflict.
- Run `python -m unittest discover -s shadow-git/tests -v`.

## 10. Operational Considerations
- After merging parallel worktrees into `main` and completing `safe-cleanup`, run `shadow-release` pre-flight gates before tagging or deploying.

## 11. Authoritative References
- Git Official Documentation — `git-diff(1)` (`--check`), `git-stash(1)`, `git-worktree(1)` (`prune`), `merge.conflictStyle = zdiff3`.
- `shadow-git/scripts/git_orchestrator.py` (`FR-08` 6-Point Safe Cleanup).

## 12. Limitations & When NOT to Use
- Never use `shadow-git` to bypass branch protection rules, force-push over signed audit commits, or alter release tags already deployed to production without explicit `L4` incident/Monarch authority.
