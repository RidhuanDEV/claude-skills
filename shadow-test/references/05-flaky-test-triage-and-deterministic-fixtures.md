# 05 — Flaky Test Triage, Deterministic Clocks & Race-Free Fixtures

## 1. Purpose & Activation Conditions
Eliminate intermittent ("flaky") CI test failures permanently by diagnosing and removing non-determinism (**wall-clock/timezone dependence**, **arbitrary `sleep()` synchronization**, **shared mutable DB/global state**, **unseeded randomness**, and **accidental external network calls**) instead of hiding bugs behind `retries: 5`. Activate whenever a test passes locally yet fails intermittently in CI, or when reviewing tests containing `setTimeout`/`time.sleep`.

## 2. Prerequisites
- Reproducible command to stress a suspected flaky test in isolation (`--repeat=20` / `pytest-repeat` / `go test -count=20 -race`).
- Access to clock injection (`vi.useFakeTimers()`, `freezegun`, `clockwork`), RNG seeding, and DB transaction rollback hooks.

## 3. Technical Principles & Constraints
- **Retries Hide Real Production Bugs:** Adding `retries: 3` without root-cause diagnosis masks genuine race conditions, connection leaks, and timezone bugs until they strike production customers — AND erodes developer trust in CI!
- **The 5 Root Causes of Test Flakiness (Deterministic Classification):**
  1. **Wall-Clock / Timezone / Month-End Drift:** Tests using `new Date()` / `datetime.now()` fail at midnight UTC, leap days, DST shifts, or month-end (`Jan 31 + 1 month`). **Fix:** Inject a frozen UTC clock (`2026-11-22T10:00:00Z`) via `vi.useFakeTimers()`, `freezegun`, or an injected `Clock` interface.
  2. **Arbitrary `sleep()` / `waitForTimeout()` Synchronization:** Waiting `500ms` for an async worker works on an idle laptop and fails under CI CPU contention. **Fix:** Await explicit deterministic completion events, barrier promises, or bounded condition polling (`expect.poll` / `waitFor`) with clear failure diagnostics.
  3. **Shared Mutable State & Order Dependency:** Hardcoded IDs (`email: "test@example.com"`), shared global singletons, or uncommitted dirty DB rows cause parallel workers to collide. **Fix:** Unique per-test scoped identifiers, per-test `SAVEPOINT` rollback, and fresh fixtures per test (`resetAllMocks`/`clearCaches` in `afterEach`).
  4. **Unseeded Randomness & Unordered Collections:** `ORDER BY` omitted from SQL queries (Postgres returns rows in arbitrary heap order after `UPDATE`!) or `Math.random()` generating edge collisions. **Fix:** Always assert deterministic `ORDER BY` in SQL or sort/set-compare unordered results explicitly, and seed deterministic PRNGs.
  5. **Accidental Live Network Calls:** Unit/integration tests hitting real DNS, Stripe sandbox, or external avatars flake whenever external servers hiccup. **Fix:** Block all outbound non-loopback network sockets in unit/integration test setups (`nock.disableNetConnect()`, `MSW { onUnhandledRequest: 'error' }`, `pytest-socket`).

## 4. Architecture & Implementation

```ts
// Strict TypeScript Deterministic Clock + Bounded Event-Condition Poller (Zero Raw Sleep, 0 any, 0 casts)
export interface Clock {
  now(): Date
}

export function createFrozenClock(isoUtc: string): { readonly clock: Clock; readonly advanceMs: (ms: number) => void } {
  let currentMs = Date.parse(isoUtc)
  if (Number.isNaN(currentMs)) {
    throw new Error(`Invalid ISO UTC timestamp: ${isoUtc}`)
  }
  return {
    clock: { now: () => new Date(currentMs) },
    advanceMs: (ms: number) => {
      currentMs += ms
    },
  }
}

export async function waitForCondition(
  predicate: () => Promise<boolean>,
  opts: { readonly timeoutMs: number; readonly intervalMs?: number; readonly label: string },
): Promise<void> {
  const deadline = Date.now() + opts.timeoutMs
  const stepMs = opts.intervalMs ?? 20
  while (Date.now() < deadline) {
    if (await predicate()) {
      return
    }
    await new Promise<void>((resolve) => {
      const timer = setTimeout(resolve, stepMs)
      timer.unref()
    })
  }
  throw new Error(`Condition '${opts.label}' did not become true within ${opts.timeoutMs}ms`)
}
```

### Flake Reproduction & Triage Commands by Stack

| Stack | Repeat / Stress Command | Randomize Order Flag | Block External Network |
| :--- | :--- | :--- | :--- |
| **Vitest / Jest** | `vitest run --retry=0` (loop 20x) | `--sequence.shuffle` | `MSW` `onUnhandledRequest: 'error'` |
| **Python (`pytest`)** | `pytest --count=20 tests/test_flaky.py` | `pytest-randomly` | `pytest --disable-socket --allow-hosts=127.0.0.1` |
| **Go** | `go test -race -count=20 -run TestFlaky ./...` | `go test -shuffle=on ./...` | `httptest.NewServer` local loopback only |
| **PHP / Pest** | `pest --repeat=20` | `--order-by=random` | `Http::preventStrayRequests()` |

## 5. Platform/Vendor Variations
- **Laravel `Http::preventStrayRequests()` & `Carbon::setTestNow()`:** Built directly into Laravel — call both in `TestCase::setUp()` so every test has a frozen clock and crashes loudly on any accidental real HTTP call!
- **Node.js / Vitest Fake Timers + Async Promises:** When mixing `vi.useFakeTimers()` with `async/await` Promises, use `await vi.advanceTimersByTimeAsync(1000)` (NOT synchronous `advanceTimersByTime`) so microtasks resolve cleanly; ALWAYS call `vi.useRealTimers()` in `afterEach` so timers don't leak into subsequent files!
- **Port Collisions in Parallel Test Workers:** NEVER hardcode `listen(3000)` in integration tests — bind to ephemeral OS port `0` (`server.listen(0)` -> read `server.address().port`) so 8 parallel test workers never throw `EADDRINUSE`.

## 6. Decision Matrix & Trade-Offs

| Flake Symptom | Diagnostic Probe | Permanent Fix |
| :--- | :--- | :--- |
| **Fails only on 1st of month / after 17:00 WIB (00:00 UTC)** | Run with `TZ=UTC` and `TZ=Asia/Jakarta` + frozen midnight date | Inject UTC clock; store/compare UTC explicitly |
| **Passes alone, fails in full suite** | Run `--sequence.shuffle` or bisect preceding test | Remove global singleton mutation / roll back DB TX / reset env vars |
| **Fails intermittently under heavy CI CPU** | Search for `sleep`/`setTimeout`/unawaited promises | Replace fixed sleeps with event signals or bounded `waitForCondition`; run `-race` |
| **Fails with `EADDRINUSE` in parallel CI** | Check hardcoded ports (`3000`, `8080`) | Bind port `0` (ephemeral OS-assigned port) |
| **Fails when vendor sandbox is slow** | Enable `--disable-socket` / `preventStrayRequests` | Stub external boundary with recorded local fixture |

## 7. Real Production Scenario
A subscription billing suite failed ~8% of CI runs every evening after 00:00 UTC and intermittently on busy Mondays. Developers had added `retries: 4` in CI, burning 14 extra minutes per PR. Running `pytest --count=20 --disable-socket` exposed three exact bugs: (1) a trial-expiry test used `datetime.now()` locally while the service compared UTC dates, (2) two parallel tests inserted the same hardcoded email `billing@test.local`, and (3) a webhook test used `time.sleep(0.5)` to wait for a background task. Fixing all three (frozen UTC clock, UUID-scoped emails, explicit completion signal) cut CI retries to `0` and uncovered a real timezone off-by-one bug in production renewal billing!

## 8. Failure Modes & Edge Cases
- **WRONG:** Leaving `await new Promise(r => setTimeout(r, 2000))` in an async test or adding global `retries: 5` in `vitest.config.ts`.
  **RIGHT:** Synchronize on observable state transitions or deterministic promises, keep unit/integration retries at `0`, and diagnose flakes immediately.
- **WRONG:** Assuming `SELECT * FROM items` returns rows in insertion order without `ORDER BY` (breaks randomly after PostgreSQL autovacuum or tuple updates!).
  **RIGHT:** Include explicit `ORDER BY` in production queries whose order matters, or compare sets/sorted arrays in assertions.
- **WRONG:** Mutating `process.env.FEATURE_X = 'true'` inside a test without restoring the original value in `afterEach`/`finally`.
  **RIGHT:** Snapshot and restore `process.env` (or use `vi.stubEnv` + `vi.unstubAllEnvs()`, `monkeypatch.setenv`, `t.Setenv`).

## 9. Testing & Verification
- Run `python shadow-test/scripts/suite_hygiene_verifier.py --check-test-suite manifest.json` to detect raw `time.sleep`/`setTimeout`/`waitForTimeout` calls.
- Prove any flake fix by running the previously flaky test **`20–50` consecutive times** with shuffled order and zero retries (`PASS` 100%).

## 10. Operational Considerations
- If a genuine flake cannot be fixed within an urgent hotfix window, quarantine it explicitly with a tracked owner + deadline issue (NEVER silently delete or skip forever) and hand complex race investigation to `/shadow-debug`.

## 11. Authoritative References
- Martin Fowler — *Eradicating Non-Determinism in Tests*.
- Google Testing Blog — *Where Do Our Flaky Tests Come From?* & *Just Say No to More End-to-End Tests*.
- `references/vendor/GoldbergYoni_JS_Testing_Best_Practices.md` (Section: Test Isolation & Determinism).

## 12. Limitations & When NOT to Use
- Do NOT use fake timers (`vi.useFakeTimers()`) around real PostgreSQL/TCP socket drivers — fake timers hijack driver connection-timeout `setTimeout` handles and cause cryptic hangs! Only fake timers for pure application time/debounce logic (use `vi.useFakeTimers({ toFake: ['Date'] })` when testing DB-backed code that only reads `Date.now()`).
