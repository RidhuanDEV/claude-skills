# 03 — Property-Based, State-Machine & Mutation Testing

## 1. Purpose & Activation Conditions
Go beyond example-based unit tests to uncover hidden corner cases in **financial/tax rounding**, **parsers/serializers**, **state machines (order/approval/payment lifecycles)**, and **concurrent idempotent workflows** using **Property-Based Testing (PBT)**, **Model-Based State-Machine Testing**, and **Mutation Testing**. Activate when testing money math, complex business invariants (`/shadow-domain`), parsers, codecs, or critical security/auth policies.

## 2. Prerequisites
- Pure or cleanly isolated domain logic (decoupled from direct I/O so generators can execute 200–1,000 randomized trials in `< 1s`).
- Explicitly stated domain invariants (e.g., conservation of money, idempotency, round-trip `decode(encode(x)) === x`, monotonic transitions).

## 3. Technical Principles & Constraints
- **Example Tests Find Known Bugs; Property Tests Find Unknown Bugs:** Humans instinctively write polite inputs (`100_000`, `"alice@example.com"`). Property generators (`fast-check`, `Hypothesis`, `proptest`, `rapid`) systematically attack empty strings, negative zero, `MAX_SAFE_INTEGER`, Unicode RTL/combining chars, duplicate IDs, and extreme rounding combinations, then **shrink** any failing case to the smallest human-readable counterexample!
- **5 High-ROI Domain Properties:**
  1. **Round-Trip / Invertibility:** `decode(encode(x))` equals `x` (canonical JSON, CSV exporters, cursor encoders, URL builders).
  2. **Conservation Invariant:** Sum of split invoice allocations + rounding remainder ALWAYS equals exact invoice total (zero Rp 1 phantom creation/destruction!).
  3. **Idempotency:** Applying the same normalized command or webhook event twice yields identical final state (`f(f(s, e), e) == f(s, e)`).
  4. **Monotonicity / Bounds:** Applying a `0..100%` discount NEVER yields a negative total and NEVER exceeds the original subtotal.
  5. **State-Machine Reachability:** Across arbitrary randomized sequences of commands (`submit`, `approve`, `cancel`, `refund`, `retry`), illegal states (e.g., `CANCELLED -> PAID` or `refundedAmount > paidAmount`) NEVER occur.
- **Deterministic Seed Replay:** Whenever a property test finds a counterexample, record its failing seed and promote the shrunk counterexample into a permanent regression example test so CI reproduces it deterministically every time.
- **Mutation Testing Mindset (Testing Your Tests):** High line coverage (`95%`) often hides weak assertions (tests execute lines without asserting results!). Run scoped mutation testing (`Stryker` for TS/JS, `mutmut` for Python, `cargo-mutants` for Rust) on high-risk modules (authz, billing, state machines) — if flipping `>=` to `>` or `&&` to `||` still leaves tests green, your assertions have a critical blind spot!

## 4. Architecture & Implementation

```ts
// Strict TypeScript Property-Based Conservation & Rounding Invariant Suite (fast-check style, 0 any, 0 casts)
export interface SplitResult {
  readonly sharesMinor: readonly number[]
  readonly totalMinor: number
}

/** Distributes integer minor units across N recipients using largest-remainder allocation (zero Rp 1 loss). */
export function splitMinorUnitsFairly(totalMinor: number, weights: readonly number[]): SplitResult {
  if (!Number.isInteger(totalMinor) || totalMinor < 0) {
    throw new RangeError('totalMinor must be a non-negative integer')
  }
  const weightSum = weights.reduce((acc, w) => acc + w, 0)
  if (weights.length === 0 || weightSum <= 0 || weights.some((w) => w < 0 || !Number.isFinite(w))) {
    throw new RangeError('weights must be non-empty non-negative numbers with positive sum')
  }

  const exact = weights.map((w, idx) => {
    const raw = (totalMinor * w) / weightSum
    const floored = Math.floor(raw)
    return { idx, floored, remainder: raw - floored }
  })

  let remaining = totalMinor - exact.reduce((acc, e) => acc + e.floored, 0)
  const sortedByRem = [...exact].sort((a, b) => b.remainder - a.remainder || a.idx - b.idx)
  const shares = exact.map((e) => e.floored)
  for (let i = 0; i < remaining; i += 1) {
    const target = sortedByRem[i]
    if (target) {
      shares[target.idx] = (shares[target.idx] ?? 0) + 1
    }
  }
  return { sharesMinor: shares, totalMinor }
}

// Deterministic pseudo-random property verifier (mirrors fast-check / Hypothesis invariant check)
export function verifySplitConservationProperty(seedTrials = 500): void {
  let state = 42_1337
  const nextInt = (max: number): number => {
    state = (state * 1_664_525 + 1_013_904_223) >>> 0
    return state % max
  }
  for (let t = 0; t < seedTrials; t += 1) {
    const total = nextInt(10_000_000)
    const count = 1 + nextInt(12)
    const weights = Array.from({ length: count }, () => 1 + nextInt(1000))
    const res = splitMinorUnitsFairly(total, weights)
    const sum = res.sharesMinor.reduce((a, b) => a + b, 0)
    if (sum !== total) {
      throw new Error(`Conservation violated: total=${total}, sum=${sum}`)
    }
    if (res.sharesMinor.some((s) => !Number.isInteger(s) || s < 0)) {
      throw new Error(`Invalid share detected for total=${total}`)
    }
  }
}
```

### Property & Mutation Ecosystem Matrix

| Stack | Property-Based Library | State-Machine Support | Mutation Testing Tool |
| :--- | :--- | :--- | :--- |
| **TypeScript / JS** | `fast-check` | `fc.modelRun` / `fc.commands` | `StrykerJS` (`@stryker-mutator/core`) |
| **Python** | `Hypothesis` (`@given`) | `RuleBasedStateMachine` | `mutmut` / `cosmic-ray` |
| **Go** | `pgregory.net/rapid` + native `go test -fuzz` | `rapid.StateMachine` | `gremlins` |
| **Rust** | `proptest` / `quickcheck` | `proptest-state-machine` | `cargo-mutants` |
| **Java / Kotlin** | `jqwik` / `Kotest Property` | Stateful `ActionSequence` | `PITest` (`pitest`) |

## 5. Platform/Vendor Variations
- **Go Native Fuzzing (`func FuzzParser(f *testing.F)`):** Built straight into the Go stdlib (`go test -fuzz=FuzzParser -fuzztime=15s`); keep fuzzing bounded in time during `L1` local checks and promote discovered crash corpora into `testdata/fuzz/` as deterministic regression tests.
- **Python Hypothesis Profiles:** Define a `ci` profile (`max_examples=200, derandomize=True`) so PR builds stay fast and reproducible while nightly builds run `max_examples=2000`.
- **Scoped Mutation Runs:** Running Stryker/PITest on an entire 100k-LOC repo takes hours (`L3`); ALWAYS scope mutation runs strictly to high-risk changed files (`--mutate "src/billing/**/*.ts,src/auth/**/*.ts"`).

## 6. Decision Matrix & Trade-Offs

| Technique | Ideal Target | Runtime Cost | Blind Spot |
| :--- | :--- | :--- | :--- |
| **Example-Based Unit Tests** | Clear business rules & documented regressions | Milliseconds | Misses unexpected edge combinations |
| **Property-Based Testing** | Money/tax math, parsers, encoders, RBAC policies | `50–500ms` (`200` trials) | Requires articulating invariants cleanly |
| **Model-Based State Machine** | Order/payment/approval workflows, caches, queues | `200ms–2s` | Only tests modeled command set |
| **Scoped Mutation Testing** | Billing, authz, idempotency, safety gates | `10–90s` (scoped) | Equivalent mutants require brief triage |

## 7. Real Production Scenario
A marketplace split settlement amounts across seller + platform fee + affiliate commission using `Math.round(total * pct)`. All 15 example unit tests passed cleanly, yet monthly accounting reconciliation drifted by `Rp 14,280` across 40,000 orders because `Math.round` on 3-way splits (`33.33%`) routinely created or lost `Rp 1`. Adding a single `fast-check` conservation property immediately found the minimal counterexample `total = 100, weights = [1, 1, 1] -> [33, 33, 33] (sum 99 != 100)` in `8ms` and validated the largest-remainder fix permanently.

## 8. Failure Modes & Edge Cases
- **WRONG:** Re-implementing the exact production formula inside the property test (`expect(calc(x)).toBe(sameFormula(x))`) — if the formula is wrong, both agree!
  **RIGHT:** Assert **independent invariants** (conservation sum, bounds, monotonicity, round-trip invertibility, or comparison against a simple brute-force reference oracle).
- **WRONG:** Running unseeded random tests in CI without printing the failing seed (creates unreproducible "ghost" failures).
  **RIGHT:** Always log/pin seeds (`fast-check` prints `{ seed, path }` automatically; Hypothesis persists `.hypothesis/examples`) and commit shrunk counterexamples as permanent unit tests.
- **WRONG:** Running unbounded mutation testing across the whole monorepo on every commit.
  **RIGHT:** Scope mutation testing strictly to changed high-risk financial/auth/invariant modules or scheduled nightly CI.

## 9. Testing & Verification
- Verify every property test fails when you deliberately introduce a 1-line mutant (e.g., drop the remainder loop or flip `<=` to `<`) — proving the property has real fault-detection power!
- Verify property suites complete in `< 2s` locally so developers run them continuously.

## 10. Operational Considerations
- Commit Hypothesis/Go-fuzz discovered crash corpora to version control so regressions never re-enter.
- Track mutation kill score (`>= 80%`) strictly on critical financial, authorization, and state-machine packages — never chase vanity mutation scores on trivial DTO/UI boilerplate.

## 11. Authoritative References
- Claessen & Hughes — *QuickCheck: A Lightweight Tool for Random Testing of Haskell Programs*.
- Nicolas Dubien — *fast-check Documentation* (Model-Based & Property Testing).
- David R. MacIver — *Hypothesis Documentation* (Rule-Based Stateful Testing).

## 12. Limitations & When NOT to Use
- Do NOT force property-based tests onto simple static CRUD mappers or cosmetic CSS layouts where straightforward example/integration tests are clearer and faster to maintain.
- Unbounded multi-hour fuzzing or whole-repo mutation campaigns are `L3_RESOURCE_INTENSIVE` and require explicit approval before running.
