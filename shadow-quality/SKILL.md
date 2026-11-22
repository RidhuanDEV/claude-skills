---
name: shadow-quality
description: "Code Quality, Static Analysis & Drift Gate. Use when running strict typechecks, lint, shadow_gate.py, complexity reduction, dead code cleanup, or brownfield convention drift audits."
---

# Shadow Quality (`/shadow-quality`) — Static Analysis, Architecture Conformance & Code Review Gate

Use this skill during development or at **SDLC Stage 4 (Verification Gate)** to verify that the codebase meets strict production quality standards before entering Pre-UAT or Release.

---

## 1. The 7 Mandatory Quality Checks

### 1. Strict Compiler & Type Safety Gate (`0 Errors`, `0 Warnings`)
- **TypeScript**: Verify `tsc --noEmit` passes with zero errors, zero `any`, zero `as Type` / `<Type>` / `!` typecasting, and zero `@ts-ignore` / `@ts-expect-error`.
- **Python**: Verify `ruff check .` and `mypy` / `pyright` pass cleanly.
- **Go / Rust / Java / PHP / .NET**: Verify native compiler and static analyzers (`golangci-lint`, `cargo clippy`, `phpstan`) report zero issues.

### 2. Dead Code & Orphan Artifact Elimination
Scan modified modules and clean up:
- Unused imports, variables, helper functions, and unreferenced DTOs/types/interfaces.
- Orphan frontend components, unused props/state variables, and obsolete CSS classes.
- Commented-out code blocks and debug statements (`console.log`, `print()`, `var_dump()`, `dd()`).

### 3. Cyclomatic & Cognitive Complexity Control
- Functions exceeding ~40–50 lines or nesting deeper than 3 levels (`if -> for -> if -> try`) must be refactored using **guard clauses (early returns)** and small, pure domain helper functions.
- Eliminate copy-pasted validation or mapping logic across controllers/services by extracting shared, typed utilities.

### 4. Architecture Layer Conformance & Fitness Rules
Verify strict directional dependencies and architectural fitness checks:
- **Controllers / UI Components** -> call **Services / Use Cases** (never raw SQL/ORM queries inside controllers or React components).
- **Services** -> enforce business rules and transactions, calling **Repositories / Adapters**.
- **Cross-Module Isolation**: Module A must not import internal repository files of Module B.
- **Forbidden Dependency & Change-Risk Scoring**: Reject circular package imports, unapproved cross-domain table joins, and schema/output drift; emit structured check statuses (`PASS | FAIL | NOT_RUN | BLOCKED | NOT_APPLICABLE`) with exact `command` and `exit_code` proof.

### 5. Contract Synchronization Check
- Verify that every backend route parameter, request DTO, and response shape matches `openapi.yaml`, `postman_collection.json` (`/shadow-api`), and frontend consumer types (`100%` parity).

### 6. Architecture & Convention Drift Gate (Brownfield Codebase Intelligence)
For brownfield codebases, run the unified deterministic quality, drift & Docker leak gate before completing the task:
```powershell
python "shadow-quality/scripts/shadow_gate.py" --repo . --check-docker-leaks
# For a job with a trusted provisioning ledger, preview the owned containers:
python "shadow-quality/scripts/shadow_gate.py" --repo . --check-docker-leaks --docker-run-id $jobId --docker-ledger $ledger
# With explicit cleanup authorization, repeat with --cleanup-docker-leaks in place of --check-docker-leaks.
# Or run convention drift standalone:
python "shadow-quality/scripts/codebase_intelligence.py" audit-drift --repo-dir . [--changed-files ...]
```
A bare check reports Docker as NOT_RUN. For a measured container check, the provisioning job records a version-1 JSON ledger with `repo` (canonical absolute repo path using forward slashes), `run_id`, and `container_ids` (full IDs). Label provisioned containers with `shadow.repo`, `shadow.run` and `shadow.ephemeral=true`. Protect the ledger from untrusted repo inputs. Preview uses IDs plus labels; cleanup rechecks identity and terminal state. Keep volumes and images under the provisioning job's separate lifecycle. A missing ledger cannot establish zero leaks.

Review the following violation categories:
- `DOCKER_TEST_MISSING_CLEANUP` / `DOCKER_TEST_IMAGE_MISSING_CLEANUP` / `DOCKER_EPHEMERAL_CONTAINER_LEAK`: Test, migration-verification, or restore-drill scripts running `docker run` without `--rm` + `docker rm -f -v`, running `docker compose up` without `down -v --rmi local --remove-orphans`, building temporary test images without removing them, or leaving exited `*-test-*` / `*-migration-verification*` containers in Docker.
- `UNEXPECTED_ARCHITECTURAL_LAYER`: Unsolicited new folder/layer (e.g. `domain/` or `usecases/` in simple MVC apps).
- `MODULE_SYSTEM_DRIFT`: CommonJS `require` vs ESM `import` mismatch with package convention.
- `TYPESCRIPT_IN_JS_PROJECT`: TypeScript syntax/extensions introduced into a plain JavaScript project.
- `DIRECT_DB_ACCESS_IN_CONTROLLER`: Bypassing established repository or service layers with direct DB calls.
- `INCONSISTENT_NAMING`: Deviating from dominant file/function naming conventions without justification.
- `UNSOLICITED_STATE_STORE`: Introducing a competing client state library (e.g. Redux when Zustand exists).
- `UNSOLICITED_ORM_HTTP_CLIENT`: Introducing competing database access or HTTP libraries.
- `SECURITY_EXCEPTION_SQL_INJECTION`: **Level 1 Safety Override** — Flags legacy raw SQL string interpolation. Security always overrides legacy habits; convert to parameterized queries while preserving naming and structure.

**Enforce the Minimal Change Policy**:
- Zero unrelated refactoring or code cleanup in files outside the task scope.
- Zero unsolicited architectural or dependency migrations.
- Zero reformatting or whitespace tampering on untouched lines/files.

### 7. Structured Code Review Output Format
When asked to review code or a PR, report findings ordered by severity:
- `[CRITICAL]` Security vulnerability, data loss/corruption risk, broken auth/tenant isolation, or crash in production.
- `[HIGH]` Broken business requirement, race condition, N+1 query on large table, or missing transaction rollback.
- `[MEDIUM]` Missing edge-case handling, missing validation, architectural boundary violation, or convention drift.
- `[LOW / NIT]` Naming clarity, dead code removal, or minor readability improvement.
*(Every finding must include exact `file:line`, impact explanation, and concrete replacement code).*

## 2. Execution Approval & Intent Boundary (`L0`–`L2`)
- Lint, strict typecheck, and `shadow_gate.py` are `L0`/`L1` on verified local workspaces, whereas **code review requests are strictly `L0_READ_ONLY`** (`0` source file mutations during review). Unrequested cross-module edits/cleanup require `L2` Monarch approval (`shadow-monarch/scripts/execution_approval_gate.py`).
- **Official-First & Code Review Checks (`OFFICIAL-FIRST-DEPENDENCY-POLICY.md`):** Flag PRs/changes that hand-write framework boilerplate instead of official generators, add unverified registry packages or floating `latest` pins in prod, replace local/SSO SDKs (`file:../sdk/...`) without approval, or invent unsupported SDK methods.

## Reference Guide

| Task / Scenario | Load Reference |
| :--- | :--- |
| Strict `tsconfig`, ESLint Boundary Fitness Rules, `shadow_gate.py`, Dead-Code Triage & Drift Audits | [references/fitness-functions-and-drift-gates.md](references/fitness-functions-and-drift-gates.md) |
| Skill Evaluation Harness (`validate_skill_evaluations.py`), Baseline Regression & Non-Compensatory Safety Gates | [references/skill-evaluation-and-regression-gates.md](references/skill-evaluation-and-regression-gates.md) |

Graded specialist scenarios live in [evaluations.md](evaluations.md) (6 scenarios). Do not load unrelated references unnecessarily.
