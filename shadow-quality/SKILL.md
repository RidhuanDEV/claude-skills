---
name: shadow-quality
description: Code Quality Gate, Static Analysis, Strict Typecheck & Linting, Cyclomatic/Cognitive Complexity Reduction, Dead Code & Duplication Elimination, Dependency Hygiene, and Architecture Layer Conformance Review. Trigger with /shadow-quality.
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

### 4. Architecture Layer Conformance
Verify strict directional dependencies:
- **Controllers / UI Components** -> call **Services / Use Cases** (never raw SQL/ORM queries inside controllers or React components).
- **Services** -> enforce business rules and transactions, calling **Repositories / Adapters**.
- **Cross-Module Isolation**: Module A must not import internal repository files of Module B.

### 5. Contract Synchronization Check
- Verify that every backend route parameter, request DTO, and response shape matches `openapi.yaml`, `postman_collection.json` (`/shadow-api`), and frontend consumer types (`100%` parity).

### 6. Architecture & Convention Drift Gate (Brownfield Codebase Intelligence)
For brownfield codebases, run the unified deterministic quality & drift gate before completing the task:
```powershell
python "shadow-quality/scripts/shadow_gate.py" --repo .
# Or run convention drift standalone:
python "shadow-quality/scripts/codebase_intelligence.py" audit-drift --repo-dir . [--changed-files ...]
```
Verify zero unapproved drift across the following violation categories:
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
