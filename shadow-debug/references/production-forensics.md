# Production Forensics: CPU, Memory, Deadlocks, Networking & Flaky Tests

## 1. Core Concepts
Scientific debugging replaces guesswork with **causal hypothesis falsification**: rank `>= 2` competing hypotheses, define a disconfirming observation for each, capture low-overhead forensic evidence (flamegraphs, 3-snapshot heap diffs, lock wait graphs, bisect commits), and prove the fix with a **Red-Before (`FAIL`) -> Green-After (`PASS`)** regression test.

## 2. Technical Rules & Symptom-to-Tool Matrix

| Symptom Class | Primary Forensic Tool | Disconfirming Evidence to Collect |
| :--- | :--- | :--- |
| **High CPU / Event-Loop Lag** | Node `--cpu-prof`/Clinic.js, Python `py-spy`, Go `pprof` | Flamegraph wide plateau (ReDoS regex, sync crypto/JSON, N+1 serialization loop). |
| **Steady RAM Growth / OOM** | 3-Snapshot Heap Diff (Baseline -> Action -> GC -> Action -> GC) | Retained object delta (`Map`/`Set` without eviction, unremoved `EventEmitter` listener, closure). |
| **Intermittent 500 / Hang** | W3C `traceparent` timeline + DB `pg_locks` / `pg_stat_activity` | Lock wait chain, exhausted connection pool, or missing outbound `AbortSignal.timeout`. |
| **Regression After Recent Commits** | `git bisect run <repro-test-cmd>` | Exact first bad commit SHA where invariant broke. |
| **Flaky CI Test** | Repeat isolated run (`--repeat 20`) with fixed clock/seed | Classify into clock/timezone, async race, shared DB state, unseeded RNG, or network dependency. |

## 3. Implementation Examples
```ts
// 1. Event-Loop Lag & Memory Growth Watchdog Probe (Safe Non-Mutating Diagnostic)
import { monitorEventLoopDelay } from 'node:perf_hooks'

export function startRuntimeForensicSampler(intervalMs = 5000): { readonly stop: () => void } {
  const histogram = monitorEventLoopDelay({ resolution: 20 })
  histogram.enable()
  const timer = setInterval(() => {
    const mem = process.memoryUsage()
    const p99LagMs = Number((histogram.percentile(99) / 1e6).toFixed(2))
    const heapUsedMb = Number((mem.heapUsed / (1024 * 1024)).toFixed(2))
    histogram.reset()
    process.stderr.write(JSON.stringify({ event: 'runtime.forensic.sample', p99LagMs, heapUsedMb }) + '\n')
  }, intervalMs)
  timer.unref()
  return {
    stop: () => {
      clearInterval(timer)
      histogram.disable()
    },
  }
}
```

## 4. Best Practices
- Always eliminate deadlocks structurally by acquiring multi-row locks in **deterministic ascending primary-key order** (`SELECT ... WHERE id IN (...) ORDER BY id ASC FOR UPDATE`).
- Redact tokens, cookies, passwords, and NIKs before pasting any log or trace timeline into bug reports or test fixtures.

## 5. Anti-patterns (WRONG vs RIGHT)
- **WRONG:** "Fixing" a flaky test or race condition by adding `await new Promise(r => setTimeout(r, 3000))` or wrapping the failing line in `try { ... } catch {}`.
- **RIGHT:** Await the deterministic state transition/event signal, isolate shared mutable state, and write a reproduction test that fails reliably before the patch and passes after.
- **WRONG:** Running load/stress tests (`k6`) against staging/production during a debugging task without `L3`/`L4` approval.
- **RIGHT:** Reproduce concurrency/race bugs locally using bounded deterministic barrier tests (`Promise.all` against an ephemeral local instance).

## 6. Production Considerations
- Separate **Immediate Mitigation** (feature-flag off, config rollback, traffic drain) from **Permanent Root-Cause Remediation** during live incidents (`/shadow-maintain`).
