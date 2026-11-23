# 02 — Seam Injection, Pure Domain Extraction & Zero-Breakage Wrapper Signatures

## 1. Purpose & Activation Conditions
Untangle monstrous legacy controllers, God classes, and global-coupled functions (`Date.now()`, `process.env`, raw ORM/SDK singletons) into testable, readable pure helpers **without breaking a single existing caller signature or importing a heavy DI container**. Activate when breaking up a complex function (`> 100` lines / high cyclomatic complexity) or making legacy I/O code unit-testable.

## 2. Prerequisites
- Passing characterization tests (`01`) and complete caller inventory (grep across workspace confirming every call site).

## 3. Technical Principles & Constraints
- **What Is a Seam (Michael Feathers)?** A seam is a place where you can alter behavior in tests **without editing the code in that place** — achieved cleanly via **narrow dependency parameters with default production bindings** (`deps: BillingDeps = defaultBillingDeps` or `now: () => Date = () => new Date()`).
- **Zero-Breakage Optional-Parameter Default Pattern:** Existing callers calling `calculateInvoice(orderId)` continue working with **zero changes**, while new characterization & unit tests call `calculateInvoice(orderId, { clock: frozenClock, repo: fakeRepo })` deterministically in `< 2ms`!
- **Functional Core, Imperative Shell Extraction:**
  1. **Step 1 — Extract Pure Calculation Core:** Pull pure branching/pricing/validation math out of the HTTP/DB handler into a pure function accepting plain typed inputs and returning a plain typed result (zero DB, zero `Date.now()`, zero `Math.random()`, zero `console.log`).
  2. **Step 2 — Keep Thin Imperative Shell:** The original route/service reads inputs, loads DB state, invokes the pure core, persists result, and triggers side effects in the exact preserved order (`04`).
  3. **Step 3 — Preserve Exact Public Exports:** Keep the original exported function name and TypeScript signature intact (`0 any`, `0 as Type`, `0 !`) unless an explicit `/shadow-compat` breaking plan exists!
- **No Unsolicited DI Frameworks:** Never install `tsyringe`, `inversify`, or rewrite plain modules into OOP class hierarchies just to pass a `Clock` or `Repository` port — plain typed interfaces and default function arguments work cleanly in TypeScript, Python, Go, and Rust with zero runtime magic!

## 4. Architecture & Implementation

```ts
// Strict TypeScript Zero-Breakage Seam Injection & Pure Core Extraction (0 any, 0 casts, 0 !)
export interface PricingPorts {
  readonly now: () => Date
  readonly isHoliday: (isoDate: string) => boolean
}

const DEFAULT_PRICING_PORTS: PricingPorts = {
  now: () => new Date(),
  isHoliday: () => false,
}

export interface DiscountInput {
  readonly subtotalCents: number
  readonly tier: 'VIP' | 'STANDARD'
  readonly isoDate: string
  readonly isHoliday: boolean
}

// 1. Extracted Pure Functional Core (100% deterministic, zero I/O, trivially testable)
export function computeLegacyDiscountCore(input: DiscountInput): number {
  if (input.subtotalCents < 0) {
    throw new RangeError('INVALID_SUBTOTAL')
  }
  const rate = input.tier === 'VIP' ? 0.15 : input.isHoliday ? 0.05 : 0
  // Preserves exact legacy Math.floor rounding semantics
  return Math.floor(input.subtotalCents * rate)
}

// 2. Preserved Public Entrypoint with Default Production Seam (0 caller breakage!)
export function calculateOrderDiscount(
  subtotalCents: number,
  tier: 'VIP' | 'STANDARD',
  ports: PricingPorts = DEFAULT_PRICING_PORTS,
): number {
  const isoDate = ports.now().toISOString().slice(0, 10)
  return computeLegacyDiscountCore({
    subtotalCents,
    tier,
    isoDate,
    isHoliday: ports.isHoliday(isoDate),
  })
}
```

### Safe Seam Extraction Technique Selection Matrix

| Legacy Coupling Culprit | Clean Seam Technique | Caller Impact |
| :--- | :--- | :--- |
| **Hardcoded `Date.now()` / `new Date()`** | Optional `now: () => Date = () => new Date()` parameter | **Zero** (100% backward compatible) |
| **Hardcoded `Math.random()` / `crypto.randomUUID()`** | Optional `rand` / `idGen` parameter with production default | **Zero** |
| **Direct global DB / HTTP SDK call inside 300-line handler** | Narrow `Ports` interface (`<= 3` methods) with default prod adapter | **Zero** |
| **Deeply nested `if/else` (cyclomatic complexity `> 15`)** | Guard clauses + pure decision helper function in same file/module | **Zero** |

## 5. Platform/Vendor Variations
- **Python:** Use `typing.Protocol` for narrow seams (`class Clock(Protocol): def now(self) -> datetime: ...`) with default parameter `clock: Clock = SystemClock()` — zero monkeypatching needed!
- **Go:** Define small 1–2 method consumer-side interfaces (`type Clock interface { Now() time.Time }`) and keep unexported helper functions in the same package (`internal/`) while preserving exported signatures.
- **PHP / Laravel:** Inject narrow interfaces or callable defaults cleanly into service methods while preserving existing controller route bindings and FormRequests.

## 6. Decision Matrix & Trade-Offs

| Refactor Scope | Technique | Risk | Best For |
| :--- | :--- | :---: | :--- |
| **1 complex file (`150–400` lines)** | Pure helper extraction + guard clauses | Very Low | Immediate readability & complexity reduction |
| **Untestable I/O-coupled service** | Narrow `Ports` seam with default prod binding | Low | Making legacy billing/auth logic deterministic |
| **Giant 20-method God interface** | Split into cohesive 2–3 method focused ports | Low–Medium | Breaking circular dependencies cleanly |

## 7. Real Production Scenario
A 520-line `settlementController.ts` mixed Express `req/res`, raw `new Date()`, 6 PostgreSQL queries, and Indonesian holiday fee logic in one giant function that nobody dared touch. Extracting `computeSettlementCore()` (pure 80-line function) and adding an optional `SettlementPorts` seam kept the Express route signature 100% untouched, enabled 24 deterministic characterization & boundary tests running in `12ms`, and cut cyclomatic complexity from `34` to `6`.

## 8. Failure Modes & Edge Cases
- **WRONG:** Turning a simple 40-line function into 7 tiny over-abstracted files (`Factory`, `Strategy`, `AbstractBase`, `Manager`, `Provider`, `DTO`, `Adapter`) that obscure control flow!
  **RIGHT:** Extract ONLY seams that meaningfully reduce complexity, isolate pure logic from I/O, or break real coupling — match the repository's local simplicity!
- **WRONG:** Changing exported parameter order or return type from `null` to `undefined` while extracting helpers.
  **RIGHT:** Keep every existing exported signature and `null`/`undefined` contract 100% identical to the Invariant Ledger.

## 9. Testing & Verification
- Run characterization tests on BOTH the original public entrypoint (`calculateOrderDiscount`) AND newly extracted pure core (`computeLegacyDiscountCore`) confirming zero regressions.
- Run strict typecheck (`tsc --noEmit` / `mypy` / `go test`) verifying `0 any`, `0 as Type`, `0 !`.

## 10. Operational Considerations
- Keep diffs compact and cohesive (1 logical seam extraction per PR/step) so human reviewers can verify equivalence in `< 10` minutes.

## 11. Authoritative References
- Michael Feathers — *Working Effectively with Legacy Code* (Ch. 4 "The Seam Model" & Ch. 9 "Sprout/Wrap Method").
- Gary Bernhardt — *Functional Core, Imperative Shell*.

## 12. Limitations & When NOT to Use
- When replacing an entire live hot-path algorithm or migrating across datastore/service boundaries where dual-run verification is needed, use **Branch-by-Abstraction / Strangler Seams (`03`)** rather than simple in-file extraction.
