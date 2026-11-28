# 04 — Brownfield Convention Preservation, 10-Facet Discovery & Official-First Policy

## 1. Purpose & Activation Conditions
Protect existing production codebases from **unsolicited architectural rewrites, dependency churn, and convention drift** by executing mandatory **10-Facet Codebase Discovery**, enforcing the **5-Level Convention Precedence Hierarchy**, and applying the **Official-First 5-Tier Dependency Policy**. Activate BEFORE proposing any structural change, new library, or new infrastructure component in an existing (brownfield) repository.

## 2. Prerequisites
- Read-only (`L0`) access to the target repository (`package.json`, `pyproject.toml`, `go.mod`, `AGENTS.md`, `CLAUDE.md`, nearby modules).
- Access to `shadow-quality/scripts/codebase_intelligence.py` and `shadow-monarch/scripts/official_first_verifier.py`.

## 3. Technical Principles & Constraints
- **Brownfield Architectural Preservation Law:** If an existing production codebase uses Layered MVC, Feature-Based folders, Express Routers, Laravel Controllers, or Minimalist FastAPI routes, **EXTEND IT IN ITS OWN STYLE**! Never force an unsolicited migration to Clean Architecture, Hexagonal Ports/Adapters, or DDD solely because you think it looks "cleaner" — every unsolicited architectural shift creates a split-brain codebase that confuses the human team!
- **Mandatory 10-Facet Discovery (`codebase_intelligence.py`):** Before designing changes in a brownfield repo, inspect and record `docs/engineering/CODEBASE_CONVENTIONS.md` across:
  1. Framework, Language & Runtime (exact patch version, CJS vs ESM)
  2. Project Structure & Module Boundaries (monorepo workspaces, internal SDK paths like `file:../sdk/sso-client`)
  3. Architectural Patterns (actual prevailing pattern, not idealized textbook label)
  4. Naming Conventions (file, folder, symbol, DB table casing)
  5. Code Formatting & Lint Rules
  6. API & Database Access Patterns (existing ORM/query builder/repository style)
  7. Error Handling & Validation (existing middleware, Zod/Joi/Pydantic/FormRequest)
  8. Authentication & Authorization (existing SSO SDK / session / JWT / RBAC middleware)
  9. State Management & Caching (existing frontend store / Redis key convention)
  10. Testing & Dependency Conventions (existing runner, mock style, package manager)
  - When legacy modules conflict internally, **document the ambiguity** and match the target module's closest 1–3 precedents rather than inventing a third incompatible convention!
- **5-Level Convention Precedence Hierarchy:**
  - **Level 1:** Explicit user requirements & non-negotiable safety/security invariants (SQLi, tenant isolation, secret hygiene).
  - **Level 2:** Applicable repository instruction files (`AGENTS.md`, `CLAUDE.md`, documented ADRs).
  - **Level 3:** Established patterns in the 1–3 closest existing modules.
  - **Level 4:** Shadow Army global defaults.
  - **Level 5:** Generic AI stylistic preferences (**NEVER** allowed to override Levels 1–4!).
- **Official-First 5-Tier Technology Hierarchy & 8-Field Decision Record:**
  - `1. Reuse existing repo capability -> 2. Official SDK/generator -> 3. Verified mature package (non-destructive npm view/context7 inspection first) -> 4. Justified small custom helper -> 5. Approved replacement`.
  - **NEVER** silently replace internal/local SSO SDKs (`your-org-sso` / `file:../sdk/sso-client`) with unverified registry packages or introduce extra infrastructure (`Docker`, `Redis`, `Kafka`, microservices) without an 8-field Decision Record and explicit Monarch approval!

## 4. Architecture & Implementation

### Mandatory Brownfield Discovery Command (`L0_READ_ONLY`)
```powershell
python "shadow-quality/scripts/codebase_intelligence.py" discover --repo-dir . --write-profile
```

### Canonical 8-Field Official-First Technology Decision Record
| Field | Example Entry (Verified Decision) |
| :--- | :--- |
| **Technology** | `PostgreSQL pg_trgm + FTS` (instead of adding Elasticsearch) |
| **Source** | PostgreSQL 16 built-in core extension |
| **Version** | `16.4` (already deployed in production) |
| **Trust status** | `Verified` (existing primary datastore) |
| **Compatibility** | `100%` compatible with existing Prisma/pg driver & backup pipeline |
| **Existing alternative** | Adding Elasticsearch cluster (`+4GB RAM`, sync pipeline, extra ops burden) |
| **Decision** | **Reuse existing PostgreSQL** up to `500k` rows (`< 30ms` p95); revisit via ADR only if corpus exceeds `1M` rows or needs dense vector scale |
| **Approval** | Auto-approved reuse (zero new infra/dependency added) |

## 5. Platform/Vendor Variations
- **Monorepo Shared Packages (`packages/*`, `sdk/*`):** Always inspect root `pnpm-workspace.yaml` / `package.json` `"workspaces"` / `pyproject.toml` before assuming a utility or auth client doesn't exist — duplicate re-implementations of shared internal SDKs are a top source of security and contract drift!
- **Legacy Modernization Boundary:** When the Monarch explicitly asks for a full due-diligence audit comparing **Strangler Fig Refactor vs Full Rewrite 3–5 yr TCO**, delegate business-case due diligence to **`/shadow-modernize`** (and incremental behavior-preserving code extraction to **`/shadow-refactor`**).

## 6. Decision Matrix & Trade-Offs

| Repo Situation | Right Architectural Action | Forbidden Anti-Pattern |
| :--- | :--- | :--- |
| **Brownfield MVC repo + 1 new feature** | Match 1–3 closest existing MVC controllers/services | Introducing a brand-new Clean Architecture folder for 1 feature |
| **Brownfield repo has `file:../sdk/sso-client`** | Preserve & wire existing local SSO SDK | Installing lookalike npm package or rewriting auth from scratch |
| **Need background job in small Postgres app** | Evaluate Postgres `FOR UPDATE SKIP LOCKED` outbox first | Silently provisioning Kafka + Zookeeper without approval |
| **Two conflicting patterns in legacy repo** | Document conflict + match target module's local precedent | Inventing a 3rd brand-new pattern |

## 7. Real Production Scenario
An agent was asked to add a simple invoice-export endpoint to an existing Express + Knex MVC repository. Without running discovery, it introduced NestJS-style decorators, a new TypeORM connection alongside Knex, and a custom Clean Architecture folder tree — breaking builds and doubling DB connection counts! Enforcing `codebase_intelligence.py` 10-facet discovery + the 5-level Precedence Hierarchy ensured the new endpoint reused existing Knex pool, existing Zod middleware, and existing Express router conventions in 90 clean lines with zero extra dependencies.

## 8. Failure Modes & Edge Cases
- **WRONG:** Running `npm install some-new-pkg` to "try it out" before checking whether the repo already has an equivalent utility or inspecting package maintainers/engines/license via `npm view`.
  **RIGHT:** Check existing repo dependencies first; inspect candidate packages non-destructively (`npm view`, `/context7`), emit the 8-field Decision Record, and verify via `official_first_verifier.py`.
- **WRONG:** Dismissing `AGENTS.md` / existing module conventions as "legacy technical debt" and refactoring 15 untouched files during a feature ticket.
  **RIGHT:** Strictly respect Level 2 (`AGENTS.md`) and Level 3 (existing precedents); propose broader cleanups separately for explicit `L2` approval (`/shadow-refactor`).

## 9. Testing & Verification
- Verify `python shadow-quality/scripts/shadow_gate.py --repo .` passes zero brownfield drift violations.
- Verify `python shadow-monarch/scripts/official_first_verifier.py --self-test` and `python -m unittest discover -s shadow-architect/tests -v`.

## 10. Operational Considerations
- Keep `docs/engineering/CODEBASE_CONVENTIONS.md` updated whenever an approved ADR intentionally evolves a convention so both human developers and AI subagents remain aligned.

## 11. Authoritative References
- `shadow-monarch/reference/CODEBASE-INTELLIGENCE.md` (10-Facet Discovery & Brownfield Preservation).
- `shadow-monarch/reference/OFFICIAL-FIRST-DEPENDENCY-POLICY.md` (5-Tier Hierarchy & 8-Field Decision Record).
- `shadow-architect/evals/decision-trials.md` & `tests/test_boundary_levels.py`.

## 12. Limitations & When NOT to Use
- Do NOT blindly preserve **security vulnerabilities** (SQL injection, missing tenant auth checks, hardcoded secrets, `any` type bypasses) just because "legacy code did it that way" — Level 1 safety & security invariants ALWAYS override unsafe legacy patterns!
