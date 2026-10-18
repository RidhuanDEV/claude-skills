# REFACTORING — Contract-Safe Refactoring & Dead Code Elimination

Use when refactoring frontend or backend code, cleaning up technical debt, modernizing legacy modules, splitting
monolithic files, or migrating internal patterns without breaking existing behavior.

## 1. Non-negotiable rule: Clean dead code during every refactor

Whenever you refactor, rename, extract, or replace logic in **frontend or backend**:
- **Never leave orphan code behind**. Actively hunt down and delete unused functions, old helper files, unreferenced
  DTOs/interfaces, dead React props/state/components, commented-out code blocks, obsolete route handlers, and unused
  imports/dependencies introduced or exposed by the refactor.
- Do not keep `_oldFunction`, `ComponentV1_Backup`, or unused feature flags "just in case".

## 2. Pre-refactor safety protocol

1. **Lock the external contract**: identify the public boundary (HTTP route + request/response schema, exported library
   signature, DB table/column contract, UI user-observable behavior). Internal structure can change; the external
   contract must remain identical unless a contract change was explicitly requested.
2. **Trace all callers and consumers**: search across the entire repository (controllers, services, tests, frontend API
   clients, shared types, background workers) before renaming or changing a signature.
3. **Establish a verification baseline**: run the existing type checker, linter, and relevant tests *before* touching
   code so you know whether failures are pre-existing or caused by your edit.

## 3. Systematic dead code audit checklist

After completing a structural change across layers, verify and remove:
- **Backend**:
  - Orphan service methods, repository queries, and private helpers no longer called by any controller, job, or event handler.
  - Unused DTO fields, validation decorators, mapper functions, exception classes, and DI module providers.
  - Unreachable conditional branches, obsolete config keys, and unused npm/pip/cargo/go packages when requested.
- **Frontend**:
  - Unused component props, dead local state (`useState`/`useMemo`/`useEffect` whose output is no longer rendered), and
    orphan event handlers.
  - Unreferenced UI components, hooks, context fields, Redux/Zustand store slices, and stale API client functions.
  - Orphan CSS classes, Tailwind helper constants, and unused icon/asset imports.
- **Shared / Types**:
  - Unused TypeScript interfaces, type aliases, enum members, and barrel (`index.ts`) re-exports that no consumer imports.
  - Strictly maintain explicit types: never replace a deleted type with `any` or typecasting (`as Type`).

## 4. Proven refactoring patterns

- **Extract by responsibility**: split a god-function/component along clear boundaries:
  - *Backend*: Controller (HTTP transport) → Validator/Pipe (input schema) → Service/Use-Case (domain orchestration) →
    Pure Domain Function (calculations/rules) → Repository (persistence).
  - *Frontend*: Page/Container (routing & layout) → Custom Hook (data fetching & state transitions) → Pure Presentational
    Components (rendering props) → Pure Domain Formatter/Validator.
- **Replace primitive obsession / stringly-typed conditionals**: convert repeated magic strings and boolean flags into
  discriminated unions and exhaustive `switch` checks (`never` exhaustiveness check).
- **Flatten deep nesting (Guard Clauses)**: handle invalid/empty/early-exit cases at the top of the function and return
  early instead of nesting `if/else` 4+ levels deep.
- **Strangler Fig for large legacy modules**: when migrating a critical module, introduce a clean boundary interface,
  route one slice at a time to the new implementation, verify with tests, and immediately delete the retired legacy slice.

## 5. Post-refactor verification

1. **Compiler & Type Check**: `tsc --noEmit` (with `noUnusedLocals` / `noUnusedParameters` mental or compiler check),
   `cargo check`, `go vet`, `dotnet build`, or `mypy`/`ruff`.
2. **Search for leftover references**: grep for old symbol names, deleted file paths, and TODO markers.
3. **Run focused tests**: confirm existing unit/integration/e2e tests pass and update test mocks only where internal
   wiring legitimately changed.

## 6. Anti-patterns

Commenting out old code instead of deleting it · leaving unused imports, props, or helper functions after moving logic ·
changing public API response field names during an "internal cleanup" · using `as Type` or `any` to force refactored
modules to compile · combining a massive formatting change across 50 files with a subtle business-logic refactor ·
creating pass-through wrapper classes that add indirection without value.
