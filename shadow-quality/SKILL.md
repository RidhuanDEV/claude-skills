---
name: shadow-quality
description: Code Quality Gate, Static Analysis, Strict Typecheck & Linting, Cyclomatic/Cognitive Complexity Reduction, Dead Code & Duplication Elimination, Dependency Hygiene, and Architecture Layer Conformance Review. Trigger with /shadow-quality.
---

# Shadow Quality (`/shadow-quality`) — Static Analysis, Architecture Conformance & Code Review Gate

Use this skill during development or at **SDLC Stage 4 (Verification Gate)** to verify that the codebase meets strict production quality standards before entering Pre-UAT or Release.

---

## 1. The 6 Mandatory Quality Checks

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

### 6. Structured Code Review Output Format
When asked to review code or a PR, report findings ordered by severity:
- `[CRITICAL]` Security vulnerability, data loss/corruption risk, broken auth/tenant isolation, or crash in production.
- `[HIGH]` Broken business requirement, race condition, N+1 query on large table, or missing transaction rollback.
- `[MEDIUM]` Missing edge-case handling, missing validation, or architectural boundary violation.
- `[LOW / NIT]` Naming clarity, dead code removal, or minor readability improvement.
*(Every finding must include exact `file:line`, impact explanation, and concrete replacement code).*
