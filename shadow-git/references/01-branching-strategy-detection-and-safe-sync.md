# 01 — Branching Strategy Detection & Safe Team Branch Synchronization

## 1. Purpose & Activation Conditions
Inspect repository branching conventions objectively before proposing merges, pull incoming teammate commits without losing uncommitted local work, and prevent destructive shared-history rewrites (`rebase`/`--force`). Activate whenever syncing branches with teammates, pulling from `origin`, or onboarding into an existing team repository.

## 2. Prerequisites
- Git `>= 2.38` (required for non-mutating `git merge-tree --write-tree`).
- Read-only (`L0`) repository access — **NEVER** run `commit`, `push`, `merge`, `rebase`, `reset --hard`, or `clean -fd` automatically without explicit Monarch `L4` authorization!

## 3. Technical Principles & Constraints
- **Detect Strategy — Never Assume Git Flow (`FR-01`):** Run `git_orchestrator.py --repo . detect-strategy` first to identify the actual repository convention (Trunk-Based, GitHub Flow short-lived feature branches, Long-Lived Feature/Research branches, Release/Hotfix, or Git Flow `main` + `develop`).
- **Phase 1: Non-Mutating Pre-Pull Reconnaissance (`L0_READ_ONLY`):** Always run read-only inspection BEFORE touching the working tree:
  - `git status -sb` (check dirty/untracked state)
  - `git branch -vv` (check tracking upstream & ahead/behind counts)
  - `git fetch --all --prune` (refresh remote refs safely without modifying local branches)
  - `git log HEAD..origin/<branch> --oneline --stat` (inspect incoming teammate commits!)
  - `git merge-tree --write-tree HEAD origin/<branch>` (dry-run conflict detection touching zero files!)
- **Phase 2: Safe Pull & Dirty-Tree Protection:**
  - Clean tree + linear (`0` ahead, `0` conflicts): `git pull --ff-only origin <branch>`.
  - Clean tree + diverged (`> 0` ahead, `0` conflicts): `git pull --no-rebase origin <branch>` (preserves shared history).
  - Uncommitted local changes exist: protect first with an explicit timestamped backup stash (`git stash push -u -m "shadow-pre-pull-backup-YYYYMMDD-HHMMSS"`) ONLY when authorized, pull safely, then restore via `git stash pop` (never implicit `stash drop`!).
- **Shared-Branch Rebase Guard (`FR-05`):** Default forward-sync (`sync-from-main`) to `--strategy merge` (`git merge --no-ff main`) for ANY pushed, shared, or long-lived branch. `git_orchestrator.py` automatically blocks `--strategy rebase` on branches tracking a remote upstream (`SHARED_BRANCH_REBASE_BLOCKED`) — never rewrite pushed team history or force-push without explicit `L4` approval and risk disclosure!

## 4. Architecture & Implementation

### Branching Strategy Taxonomy (`FR-01`)

| Strategy | Repo Indicators | Integration Target | Safe Forward-Sync Policy |
| :--- | :--- | :--- | :--- |
| **Trunk-Based Development** | Single `main`/`trunk`, tiny `< 1–2d` branches + flags | `main` | Fast-forward or `merge main`; rebase strictly on unpushed local commits |
| **GitHub Flow (Short-Lived)** | `main` + `feature/*` / `fix/*` via PR | `main` | `git merge --no-ff main` (or local rebase ONLY if unpushed & solo) |
| **Long-Lived Feature / Research** | Multi-week `feature-*` / `research/*` | `main` (or `develop`) | **Always `git merge main`** — never rebase shared history |
| **Release & Hotfix** | `main` + `release/v*` + `hotfix/*` | `main` + active `release/*` | Merge hotfix to `main` & cherry-pick/merge to `release/*` |
| **Git Flow** | Both `main` and `develop` + `feature/*` | `develop` (feat) / `main` (rel) | Sync `develop` into `feature/*` via `merge` |

### Read-Only Reconnaissance & Safe Sync Commands (PowerShell)
```powershell
# 1. Read-Only Reconnaissance (L0 — Zero Working-Tree Mutation)
python "shadow-git/scripts/git_orchestrator.py" --repo . detect-strategy
git status -sb
git branch -vv
git fetch --all --prune
git log HEAD..origin/main --oneline --stat
git merge-tree --write-tree HEAD origin/main

# 2. Preview forward-sync into feature branch (Read-Only unless --approve granted!)
python "shadow-git/scripts/git_orchestrator.py" --repo . sync-from-main --branch feature-rag --main main --strategy merge
```

## 5. Platform/Vendor Variations
- **Protected Branches & PR Policies (GitHub / GitLab / Bitbucket):** Respect branch protection rules (required status checks, CODEOWNERS approvals, signed commits) — open a PR rather than attempting direct pushes to protected `main`.
- **Windows Line-Ending Traps (`core.autocrlf`):** Ensure `.gitattributes` enforces `* text=auto` and `*.sh text eol=lf` so teammates on Windows and macOS/Linux don't generate 500-line fake CRLF merge conflicts on untouched files!

## 6. Decision Matrix & Trade-Offs

| Sync Command | Preserves Shared SHAs? | Needs `--force`? | Safe on Team Branches? |
| :--- | :---: | :---: | :---: |
| **`git pull --ff-only`** | Yes | No | **Best** when strictly behind |
| **`git merge --no-ff main`** | **Yes** | **No** | **Default** for shared/pushed branches |
| **`git rebase main`** | **NO** (rewrites SHAs!) | **YES** if pushed! | **ONLY** strictly local, unpushed, solo branches |

## 7. Real Production Scenario
A developer ran `git pull --rebase && git push --force` on a shared `feature-checkout` branch where a teammate had pushed 3 backend commits an hour earlier, silently wiping the teammate's commits from `origin`! Adopting `git_orchestrator.py` read-only reconnaissance (`merge-tree`) + `SHARED_BRANCH_REBASE_BLOCKED` guard + default `--strategy merge` prevented every subsequent history-rewrite incident.

## 8. Failure Modes & Edge Cases
- **WRONG:** Running `git pull` blindly while 6 local files have unstaged edits, or running `git clean -fd` / `git reset --hard` to "get a clean slate."
  **RIGHT:** Always inspect `git status -sb` + `git merge-tree` first, protect local work with a named backup stash (`-u`), and require explicit `L4` authorization before any destructive discard.
- **WRONG:** Ignoring `git fetch --prune` (leaves stale deleted remote branches tricking strategy detection and conflict checks into comparing outdated refs!).
  **RIGHT:** Always refresh refs with `git fetch --all --prune` before predicting conflicts or syncing.

## 9. Testing & Verification
- Run `python shadow-git/scripts/git_orchestrator.py --repo . health --stale-days 14` to audit branch freshness, upstream tracking, and worktree cleanliness safely (`L0`).
- Run `python -m unittest discover -s shadow-git/tests -v`.

## 10. Operational Considerations
- Inspect `git log -p HEAD..origin/<branch>` BEFORE merging incoming teammate changes so you understand new DB migrations, env vars, or API contracts added by teammates.

## 11. Authoritative References
- Git Official Documentation — `git-merge-tree(1)`, `git-pull(1)`, `git-rebase(1)` (*The Perils of Rebasing*).
- `shadow-git/scripts/git_orchestrator.py`.

## 12. Limitations & When NOT to Use
- Do NOT activate `shadow-git` automatically on every chat turn solely because a repo uses Git — run Git syncs only when syncing/branching/integrating is actually relevant to the Monarch's task.
