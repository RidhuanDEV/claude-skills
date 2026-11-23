# 03 — Non-Mutating `git merge-tree` Conflict Prediction & Semantic Integration Risks

## 1. Purpose & Activation Conditions
Predict **both Hard Git Conflicts AND Semantic Integration Risks** before mutating any branch or working directory using Git `>= 2.38` `git merge-tree --write-tree` and `git_orchestrator.py predict-conflicts`. Activate before merging feature branches into `main`, syncing `main` into active worktrees, or reviewing concurrent PRs touching schemas, APIs, or lockfiles.

## 2. Prerequisites
- Git `>= 2.38` installed locally (`git --version`) and refreshed remote refs (`git fetch --all --prune`).

## 3. Technical Principles & Constraints
- **Clean Git Merge (`exit 0`) != Safe Software Integration!** Git only checks text-line overlap — two branches can merge with **zero** Git conflict markers and still break production completely!
- **Separate Two Distinct Risk Classes (`FR-06`):**
  1. **Hard Git Conflicts (Block Merge Immediately):**
     - Overlapping content line edits in the same file.
     - Rename / modify-delete conflicts (`rename/delete`, `modify/delete`).
     - File mode conflicts (`100644` vs `100755`).
     - Unrelated / divergent histories.
  2. **Semantic Integration Risks (Flagged Even When `git merge-tree` Exits `0`!):**
     - **`PARALLEL_SCHEMA_MIGRATIONS` (`HIGH`):** Both branches added database migration files (`migrations/`, `prisma/migrations/`, `alembic/versions/`) — risks duplicate sequence timestamps, conflicting constraints, or broken linear Alembic heads (`/shadow-data`)!
     - **`API_CONTRACT_MODIFICATION` (`MEDIUM`):** Concurrent or producer-only changes to `openapi.yaml`, routes, controllers, GraphQL schemas, or `.proto` files that may break another branch's consumer (`/shadow-api`, `/shadow-compat`)!
     - **`SHARED_CONFIGURATION_CHANGE` (`MEDIUM`):** Edits to `.env.example`, `package.json`, `tsconfig.json`, or `docker-compose.yml` affecting runtime flags or compiler strictness!
     - **`LOCKFILE_DIVERGENCE` (`MEDIUM`):** Concurrent updates to `package-lock.json`, `pnpm-lock.yaml`, `uv.lock`, `poetry.lock`, `go.sum`, or `Cargo.lock`!
- **SHA & Merge-Base Freshness Gate (`test_worktree_semantic_order.py`):** Always record `(source_sha, target_sha, merge_base)` with every conflict prediction preview. Re-resolve both refs right before executing the actual merge — if either ref advanced since preview, **invalidate the old preview and re-run both conflict prediction and cross-boundary contract tests!**

## 4. Architecture & Implementation

```powershell
# 1. Pure Git non-mutating dry-run merge check (L0 — touches zero working tree files!)
git merge-tree --write-tree HEAD origin/main

# 2. Full Shadow Git conflict + semantic risk prediction (L0 read-only JSON report)
python "shadow-git/scripts/git_orchestrator.py" --repo . predict-conflicts --source feature-export --target main
```

### Hard Git Conflicts vs Semantic Integration Risks Matrix

| Risk Code | Severity | Example Trigger | Mandatory Post-Merge Gate |
| :--- | :---: | :--- | :--- |
| **Hard Git Conflict** | `BLOCKER` | Overlapping edits or rename/delete on same path | Manual intent-preserving merge (`04`), zero `--ours`/`--theirs` |
| **`PARALLEL_SCHEMA_MIGRATIONS`** | `HIGH` | Branch A added `0042_add_tax.sql` & `main` added `0042_add_notes.sql` | Re-sequence / verify linear migration chain (`alembic heads`, `/shadow-data`) |
| **`API_CONTRACT_MODIFICATION`** | `MEDIUM` | Branch A changed `/v1/orders` response while Branch B consumes `/v1/orders` | Run producer/consumer contract tests & OpenAPI diff (`/shadow-api`, `/shadow-compat`) |
| **`SHARED_CONFIGURATION_CHANGE`** | `MEDIUM` | Concurrent edits to `.env.example`, `tsconfig.json`, `docker-compose.yml` | Verify env parity, `tsc --noEmit`, and Compose hardening (`/shadow-ops`) |
| **`LOCKFILE_DIVERGENCE`** | `MEDIUM` | Both branches added npm/Python deps | Merge manifest cleanly, regenerate lockfile via package manager, verify SBOM (`/shadow-supplychain`) |

## 5. Platform/Vendor Variations
- **Alembic (Python) Multi-Head Failure:** Two parallel branches branching from migration `rev_a` produce two Alembic heads (`rev_b` and `rev_c`) with ZERO Git conflicts — production `alembic upgrade head` then crashes with `Multiple head revisions are present`! Always run `alembic heads` (assert count === `1`) or create an explicit merge revision after `PARALLEL_SCHEMA_MIGRATIONS`!
- **Prisma / Knex / Laravel Migrations:** Two parallel migrations editing the same table can pass Git merge yet fail at SQL execution order (e.g., index referencing a renamed column). Always run a fresh ephemeral DB migration test (`shadow-test`) on the combined merged tree!

## 6. Decision Matrix & Trade-Offs

| Pre-Merge Check | Touches Working Tree? | Catches Semantic Regressions? | Speed |
| :--- | :---: | :---: | :--- |
| **Blind `git merge`** | Yes (leaves dirty `UU` markers!) | No | Fast but messy |
| **`git merge-tree --write-tree`** | **No (`L0` safe!)** | Hard Git conflicts only | `< 100ms` |
| **`git_orchestrator.py predict-conflicts`** | **No (`L0` safe!)** | **Yes (Git + 4 semantic risk classes)** | `< 200ms` |

## 7. Real Production Scenario
Two feature branches (`feature-discount` and `feature-invoice`) merged into `main` with `0` Git merge conflicts because they touched completely disjoint directories (`discounts/` and `invoices/`). However, `feature-discount` renamed an exported field in `shared/pricing.ts` while `feature-invoice` imported the old name AND both added Alembic migration files! Running `predict-conflicts` caught `PARALLEL_SCHEMA_MIGRATIONS` + `API_CONTRACT_MODIFICATION` before merge, and running `tsc --noEmit` + `alembic heads` + integration tests on the combined tree caught both silent breaks before reaching `main`.

## 8. Failure Modes & Edge Cases
- **WRONG:** Skipping cross-boundary typecheck and contract tests after merging two branches simply because their modified file lists had zero overlap.
  **RIGHT:** Even disjoint file edits can break producer/consumer types, SQL migration chains, or runtime invariants — always run full typecheck + contract + affected integration tests on the combined tree!
- **WRONG:** Relying on a stale conflict preview from yesterday after 4 new PRs merged into `main`.
  **RIGHT:** Pin `(source_sha, target_sha, merge_base)` and re-run prediction if either SHA changed.

## 9. Testing & Verification
- Run `python -m unittest discover -s shadow-git/tests -v` (`test_worktree_semantic_order.py` validates SHA freshness and semantic ordering!).
- Review `shadow-git/output/acceptance_report_git_v2.json` for expected `git_orchestrator.py` v2 contract outputs.

## 10. Operational Considerations
- Integrate `git merge-tree` / `predict-conflicts` into multi-agent coordinator gates so merge conflicts surface hours before final PR integration rather than blocking release day.

## 11. Authoritative References
- Git Official Documentation — `git-merge-tree(1)` (`--write-tree`, Git 2.38+).
- ISO/IEC/IEEE 12207 & NIST SP 800-218 (SSDF) Pre-Merge Provenance & Verification.

## 12. Limitations & When NOT to Use
- `predict-conflicts` uses path/pattern heuristics for semantic risk detection — it flags high-risk boundaries early, while **compilers, schema linters, and automated integration tests (`/shadow-test`)** remain the final proof of semantic correctness!
