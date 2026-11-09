---
name: shadow-git
description: Safe Multi-Branch Team Collaboration, Pre-Pull Dry-Run Conflict Detection (git merge-tree), Safe Pull with Stash Protection, and Smart Conflict Resolution preserving both teammate and Monarch contracts. Trigger with /shadow-git.
---

# Shadow Git (`/shadow-git`) — Safe Team Branch Sync & Conflict Resolution

Use this skill whenever the **Monarch** works in a collaborative multi-branch repository and wants to check branch status, inspect teammate updates on `origin`, pull safely without losing uncommitted work, or resolve merge/rebase conflicts.

---

## 1. Phase 1: Safe Pre-Pull Reconnaissance (Zero Working-Tree Mutation)

Before pulling or switching branches, ALWAYS execute these read-only / remote-fetch checks in parallel:

```powershell
# 1. Check active branch, tracking upstream, and uncommitted local changes
git status -sb
git branch -vv

# 2. Fetch latest teammate commits from remote without touching local files
git fetch --all --prune
```

Then inspect what teammates pushed to the target branch (`origin/<current-branch>`, `origin/main`, or `origin/develop`):

```powershell
# 3. List incoming teammate commits and affected files
git log HEAD..origin/<target-branch> --oneline --stat

# 4. Run in-memory dry-run merge (Git 2.38+) to detect conflicts BEFORE pulling!
git merge-tree --write-tree HEAD origin/<target-branch>
```

---

## 2. Phase 2: Safe Pull Execution Protocol

### Case A: `git merge-tree` reports **0 conflicts** and local working tree is clean
- If local branch has `0` ahead commits:
  ```powershell
  git pull --ff-only origin <target-branch>
  ```
- If local branch has ahead commits (diverged, but no overlapping file conflicts):
  ```powershell
  git pull --no-rebase origin <target-branch>
  ```

### Case B: Uncommitted local changes exist in working tree
1. Check if any uncommitted local file overlaps with `git diff --name-only HEAD...origin/<target-branch>`.
2. Protect uncommitted work before pulling using a named stash (including untracked files):
   ```powershell
   git stash push -u -m "shadow-pre-pull-backup-$(Get-Date -Format 'yyyyMMdd-HHmmss')"
   ```
3. Pull from remote, then restore the stashed changes:
   ```powershell
   git stash pop
   ```
   *(If `git stash pop` hits a conflict, Git keeps the stash safely in `git stash list` until resolved!)*

---

## 3. Phase 3: Intelligent Collaborative Conflict Resolution

When `git pull`, `git merge`, `git rebase`, or `git stash pop` produces conflict markers (`<<<<<<<`, `=======`, `>>>>>>>`):

1. **List all conflicted files**:
   ```powershell
   git diff --name-only --diff-filter=U
   ```
2. **Understand BOTH the Monarch's and Teammate's Intent**:
   - Inspect the Monarch's recent commits on that file: `git log -p -n 3 HEAD -- <file>`
   - Inspect the teammate's incoming commits on that file: `git log -p -n 3 origin/<target-branch> -- <file>`
3. **Never Blindly Take `--ours` or `--theirs` on Source Code**:
   - Combine both sets of imports, routes, DTO fields, validation rules, and UI components cleanly.
   - Maintain strict TypeScript discipline (`0 any`, `0 as Type` casting) and remove dead/duplicate declarations.
   - Lockfiles (`package-lock.json`, `pnpm-lock.yaml`, `composer.lock`): regenerate cleanly using the package manager (`npm install --package-lock-only`) after merging `package.json`.
4. **Verify Conflict Resolution Before Reporting**:
   - Check zero leftover conflict markers: `git diff --check`
   - Run project typecheck, linter, and unit tests to guarantee neither the Monarch's nor the teammate's feature broke.
