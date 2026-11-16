# User Intent Boundary & Execution Approval Protocol (`L0`–`L4`)

> **Core Principle:** The **Monarch's (user's) request** defines the authorized execution scope. An agent's recommendation does **not** constitute user authorization. Shadow Army may proactively recommend improvements, tests, or refactors, but MUST NOT execute `L2`–`L4` actions without explicit user approval.

---

## 1. Mandatory Pre-Execution Assessment (8-Point Check)

Before executing any command, script, tool call, test, or file/infra modification, evaluate:
1. **Direct Necessity:** Is this action strictly necessary to satisfy the current user request?
2. **Scope Classification:** Is it explicitly requested, reasonably implied inside `L0`/`L1`, or outside scope (`L2`+)?
3. **Target Inventory:** Which exact files, tables, services, DBs, containers, or external endpoints are affected?
4. **State Persistence:** Does it modify persistent disk, database, lockfile, Git history/remote, or live runtime state?
5. **Resource & Cost Impact:** Can it trigger high CPU, RAM, disk I/O, network egress, API floods, or monetary/LLM billing spikes?
6. **Environment Classification:** Is the target `local`, `development`, `isolated_sandbox`, `staging`, `production`, or `unknown`? **Unknown environments MUST fail closed (never assume safe).**
7. **Reversibility:** Can effects be rolled back cleanly and deterministically?
8. **Authorization Level:** Which permission tier (`L0`–`L4`) applies under `execution_approval_gate.py`?

---

## 2. Permission Levels (`L0`–`L4`)

| Level | Category | Concrete Actions | Execution Policy |
|---|---|---|---|
| **`L0_READ_ONLY`** | Inspection | Read files, inspect configs/logs, `git status/diff/log`, static AST checks, read-only `SELECT`/`EXPLAIN` on verified non-prod targets | **Auto-allowed** when within task scope |
| **`L1_SAFE_VERIFICATION`** | Bounded Local Verification | Relevant lint, `tsc --noEmit`, `mypy`/`ruff`, bounded module unit tests, `shadow_gate.py --repo .`, deterministic `--self-test` scripts, in-scope code edits when task authorizes editing | **Auto-allowed** ONLY when intent allows mutation/execution, target paths match scope, and env is `local`/`development`/`isolated_sandbox` |
| **`L2_SCOPE_EXPANSION`** | Scope Expansion | Unrequested refactoring, edits outside requested modules, broad E2E suites (`playwright test` full suite during unit-test/minor UI asks), unrequested features or dependencies | **Explicit Monarch approval required** |
| **`L3_RESOURCE_INTENSIVE`** | Resource / Cost Intensive | Load/stress/soak/spike testing (`k6`, `locust`, `wrk`), high-volume fuzzing, large benchmarks, mass API bursts, high-cost live LLM eval/judge batches | **Action-specific Monarch approval required** |
| **`L4_HIGH_IMPACT`** | Destructive / Prod / Remote | Production deploys, destructive SQL/DDL (`DROP`, `TRUNCATE`, `migrate reset`), prod infra/firewall changes, external data transmission, secret/permission changes, `git push`/`reset --hard`, global home installs, **or any mutation on `staging`/`production`/`unknown` environments** | **Explicit approval + verified target + impact review + tested rollback required** |

---

## 3. Explicit 7-Part Approval Contract

Whenever an action requires approval (`L2`, `L3`, `L4`), stop before execution and present:
1. **Proposed action** (exact command/operation and bounds).
2. **Why it is necessary** (evidence or hypothesis it resolves).
3. **Exact target / environment** (`local`, `staging`, `production`, exact paths/DBs).
4. **Expected side effects** (state writes, restarts, locks, temporary data).
5. **Estimated resource impact** (RPS, duration, CPU/DB load, API/token cost if measurable).
6. **Rollback or recovery plan** (exact restore/revert procedure).
7. **Safer alternatives** (e.g., unit/mock check or dry-run read-only preview) + explicit permission question.

*Example:*
> *"To investigate the suspected concurrency issue, I recommend a controlled load test. This will send up to 100 requests per second for 60 seconds against the local test environment. It may temporarily increase CPU and database load. Safe alternative: inspect lock contention queries read-only first (`L0`). May I execute this test?"*

Never interpret silence, unrelated instructions, or prior unrelated approvals as authorization.

---

## 4. Mandatory Testing Boundaries

- **Code Review (`L0_READ_ONLY`):** Strictly read-only — NEVER modify source files or run mutating commands during review.
- **Debugging:** Diagnosing a bug authorizes `L0` inspection and bounded `L1` local reproduction; it does **not** authorize `L3` stress/load testing or `L4` production tampering.
- **Unit Testing:** Authorizes bounded `L1` unit/module tests; does **not** authorize `L2` broad E2E suites or `L3` load testing.
- **Feature Implementation:** Permits changes required inside requested modules; does **not** authorize `L2` unrelated refactoring across other modules.
- **Performance Optimization:** Permits `L0`/`L1` profiling on local/sandbox; does **not** automatically authorize testing production infrastructure (`L4`).
- **Database Fixes:** Fixes in local/dev do **not** authorize destructive schema resets or drops (`L4`).

---

## 5. Sub-Agent Authorization & Escalation

Delegated Shadow Army sub-agents MUST inherit the parent task's exact authorization envelope (`max_permission_level`, `allowed_paths`, `allowed_environments`, `denied_actions`). Sub-agents MUST NEVER:
- Expand authorized file/environment scope.
- Upgrade permission tiers (e.g., `L1` -> `L2`/`L3`/`L4`).
- Treat orchestrator recommendations or internal routing prompts as user authorization.
- Execute any action denied or deferred by the parent task or Monarch.

All `L2`–`L4` requests MUST escalate cleanly back to the primary orchestrator for explicit Monarch approval.

---

## 6. Approval Persistence & Scope Lock

Persist active task approvals explicitly using the schema enforced by `execution_approval_gate.py`:
- `approval_id`, `task_id`, `project_path`
- `user_approved_action`, `permission_level`
- `exact_targets[]`, `allowed_environments[]`, `resource_limits{}` (`max_rps`, `max_duration_sec`, `max_requests`)
- `relevant_constraints[]`, `approval_timestamp_or_turn`
- `execution_status` (`APPROVED_PENDING | EXECUTED | DENIED | DEFERRED | EXPIRED | REVOKED`)

An approval NEVER carries over across projects, unrelated `task_id`s, higher resource limits, broader environments, or after `DENIED`/`DEFERRED`/`EXECUTED`.

---

## 7. Fail-Closed Enforcement CLI

Run `python "shadow-monarch/scripts/execution_approval_gate.py"` to validate assessments, sub-agent delegation envelopes, and approval records deterministically (exits non-zero / `status: "BLOCKED"` on missing approval).
