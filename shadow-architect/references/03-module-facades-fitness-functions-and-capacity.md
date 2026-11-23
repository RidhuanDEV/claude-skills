# 03 — Module Public Facades, Architectural Fitness Functions & Capacity Sizing

## 1. Purpose & Activation Conditions
Keep a Modular Monolith cleanly decoupled over years of rapid feature delivery using **strict typed `public.ts` module facades**, **automated Architectural Fitness Functions** (enforcing acyclic dependencies & zero cross-module DB table imports in CI), and **quantitative back-of-the-envelope capacity sizing**. Activate when laying out module directories, adding CI boundary lint gates, or validating whether infrastructure fits traffic/storage/RAM budgets.

## 2. Prerequisites
- Defined domain modules (e.g., `auth`, `orders`, `billing`, `catalog`) and baseline traffic/retention assumptions from `/shadow-discovery`.

## 3. Technical Principles & Constraints
- **One Public Entrypoint Per Module (`public.ts` / `api.py` / Go `pkg` vs `internal/`):**
  - Module A (`orders`) may import ONLY `modules/billing/public.ts` (exported DTOs, ports/interfaces, public facade functions, domain event types).
  - Module A MUST **NEVER** import `modules/billing/internal/*`, `modules/billing/repositories/*`, or query `billing_*` SQL tables directly!
  - Enforcing this in-process guarantees that if `billing` ever needs to become a standalone service later, you only swap the implementation behind `BillingPort` — zero caller rewrites!
- **Automated Architectural Fitness Functions (Enforce In CI, Not Slide Decks!):** Architecture rules documented only in Confluence rot within 3 sprints. Encode them mechanically:
  1. **Zero Cross-Module Internal Imports:** `eslint-plugin-boundaries`, `dependency-cruiser`, Go `internal/` packages, Python `import-linter`, or Java ArchUnit failing CI on illegal imports.
  2. **Acyclic Module Dependency Graph:** Zero circular `orders <-> billing` imports (`madge --circular` / `dependency-cruiser` exits non-zero!).
  3. **Strict Layer & Complexity Ceilings:** Max p95 latency budget, zero raw SQL outside repositories, strict TypeScript (`0 any`, `0 as Type`, `0 !`).
- **Back-of-the-Envelope Capacity Sizing Math:** Before selecting VM/DB sizes or extra tiers:
  - **Traffic:** `avgRps = (DAU * reqPerUserPerDay) / 86_400`; `peakRps = avgRps * peakFactor` (typically `3–5x`, or `10x` for flash/deadline portals!).
  - **Storage (5-Year Horizon):** `yearlyGb = (avgRowBytes * recordsPerDay * 365 * 1.35 /* index + bloat overhead */) / 1e9`, plus object storage growth (`uploadsPerDay * avgFileMb`).
  - **DB Memory & Connections:** PostgreSQL `shared_buffers ~= 25%` of DB RAM, working hot-index set fits in OS page cache, total connections across all app pods `<=` PgBouncer/DB core budget (`shadow-db`).

## 4. Architecture & Implementation

```ts
// Strict TypeScript Module Public Facade Contract (modules/billing/public.ts — 0 any, 0 casts)
export interface InvoiceSummaryDto {
  readonly id: string
  readonly tenantId: string
  readonly amountMinor: number
  readonly status: 'DRAFT' | 'ISSUED' | 'PAID'
}

export interface BillingModulePort {
  getInvoiceByOrderId(tenantId: string, orderId: string): Promise<InvoiceSummaryDto | null>
}

// modules/orders/internal/checkout_view.ts — imports ONLY ../billing/public.ts!
export async function buildOrderBillingView(
  billing: BillingModulePort,
  tenantId: string,
  orderId: string,
): Promise<{ readonly orderId: string; readonly invoiceStatus: string }> {
  const invoice = await billing.getInvoiceByOrderId(tenantId, orderId)
  return {
    orderId,
    invoiceStatus: invoice ? invoice.status : 'UNBILLED',
  }
}

// Back-of-the-Envelope Capacity Estimator (Strict TS)
export interface SizingInputs {
  readonly dau: number
  readonly requestsPerUserPerDay: number
  readonly peakMultiplier: number
  readonly avgRowBytes: number
  readonly newRowsPerDay: number
  readonly retentionYears: number
}

export interface CapacityEstimate {
  readonly avgRps: number
  readonly peakRps: number
  readonly estimatedDbGbWithOverhead: number
}

export function estimateBaselineCapacity(input: SizingInputs): CapacityEstimate {
  const avgRps = (input.dau * input.requestsPerUserPerDay) / 86_400
  const peakRps = avgRps * input.peakMultiplier
  const rawBytes = input.avgRowBytes * input.newRowsPerDay * 365 * input.retentionYears
  const withIndexAndBloatGb = (rawBytes * 1.35) / 1_000_000_000
  return {
    avgRps: Number(avgRps.toFixed(2)),
    peakRps: Number(peakRps.toFixed(2)),
    estimatedDbGbWithOverhead: Number(withIndexAndBloatGb.toFixed(2)),
  }
}
```

### Automated Fitness Function Enforcement Matrix

| Stack | Boundary / Acyclic Fitness Tool | Enforced Rule Example |
| :--- | :--- | :--- |
| **TypeScript / JS** | `dependency-cruiser` or `eslint-plugin-boundaries` | Forbid `modules/A/**` importing `modules/B/internal/**`; forbid circular deps |
| **Python** | `import-linter` (`contracts` in `pyproject.toml`) | Independence contract across domain packages + layered inward-only contract |
| **Go** | Native `internal/` package visibility (compiler-enforced!) | Compiler rejects any external package importing `modules/billing/internal` |
| **Java / Kotlin** | `ArchUnit` (`@ArchTest`) | No cyclic slices; controllers cannot access JPA repositories directly |
| **C# / .NET** | `NetArchTest` / `ArchUnitNET` + project references | Internal classes stay `internal`; public contracts in `*.Contracts` |

## 5. Platform/Vendor Variations
- **PostgreSQL Schema-Per-Module (`auth.*`, `orders.*`, `billing.*`):** Even inside one PostgreSQL database, assigning each module its own schema (`CREATE SCHEMA billing`) makes accidental cross-module `JOIN`s glaringly obvious in code review and lets you audit table ownership automatically!
- **Monorepo Workspace Packages (`pnpm workspaces`, Turborepo, Nx):** Map each domain module to a workspace package (`@app/billing`) exporting ONLY its `public.ts` in `package.json` `"exports"` map — Node/TS itself rejects deep internal imports at compile time!

## 6. Decision Matrix & Trade-Offs

| Boundary Enforcement | Setup Cost | Prevents Drift Over Time? | Runtime Overhead |
| :--- | :--- | :--- | :--- |
| **Wiki / Verbal Agreement Only** | Zero | **No** (erodes within 1–2 sprints) | Zero |
| **CI Lint (`dependency-cruiser` / `import-linter` / Go `internal/`)** | Low (`30 min`) | **Yes (100% automated in PR)** | **Zero** (in-process calls!) |
| **Network Microservice Split** | Very High | Yes | High (serialization, network hops, Sagas) |

## 7. Real Production Scenario
A growing 14-developer SaaS Modular Monolith started accumulating circular imports (`orders -> billing -> notifications -> orders`), turning every PR into merge conflicts and breaking unit-test isolation. Adding a 25-line `dependency-cruiser` config forbidding cross-module `internal/` imports and circular dependencies exposed 19 hidden boundary leaks; refactoring them behind typed `public.ts` facades + domain events took 2 days and prevented 100% of new coupling leaks across the next 18 months.

## 8. Failure Modes & Edge Cases
- **WRONG:** Creating a giant dumping-ground folder `src/shared/` or `src/common/` holding 60% of the app's business models and DB repositories (silently collapses module boundaries back into a monolith tangle!).
  **RIGHT:** Keep `shared/` strictly for domain-agnostic technical primitives (`Clock`, `Logger`, `MoneyMinor`, `Result`, HTTP error types) — domain entities belong exclusively inside their owning module!
- **WRONG:** Sizing server capacity from `avgRps` alone (`50,000 DAU -> 5.8 avg RPS`) when 80% of traffic arrives in a 15-minute flash sale or government 08:00 WIB clock-in burst (`peakMultiplier = 15–30x`!).
  **RIGHT:** Model realistic **peak-window burst ratios** explicitly and document uncertainty bands rather than flat daily averages (`evals/decision-trials.md`).

## 9. Testing & Verification
- Wire the module boundary fitness check (`depcruise`, `import-linter`, `ArchUnit`) directly into PR CI so illegal imports fail fast before code review.
- Cross-check capacity estimates against real staging benchmarks when entering Pre-UAT (`/shadow-perf`).

## 10. Operational Considerations
- Pair domain boundary metrics with code-owner assignments (`CODEOWNERS`) per `modules/<domain>/` directory so domain owners automatically review public facade changes.

## 11. Authoritative References
- Neal Ford, Rebecca Parsons & Patrick Kua — *Building Evolutionary Architectures (2nd Ed.)* (Fitness Functions).
- `dependency-cruiser` / `import-linter` / `ArchUnit` Documentation.

## 12. Limitations & When NOT to Use
- Do NOT construct heavy 5-layer Clean Architecture / DTO-mapper ceremonies inside a single 200-line CRUD module — enforce boundaries **between modules**, while keeping each module's internals as simple as its domain complexity warrants!
