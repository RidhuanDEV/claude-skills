# 02 — Runtime CPU, Memory Leak & Event-Loop Forensics

## 1. Purpose & Activation Conditions
Diagnose silent runtime pathologies that emit **zero stack traces** — including **event-loop stalls**, **ReDoS catastrophic regex backtracking**, **steady heap growth / `OOMKilled` crashes**, **file descriptor / socket leaks**, and **goroutine/thread leaks** — using low-overhead runtime profiling and 3-snapshot heap differential analysis. Activate when services freeze, lag intermittently, or get OOM-killed under normal traffic without clear application errors.

## 2. Prerequisites
- Reproducible workload or captured runtime forensic snapshot (`--cpu-prof`, heap snapshots, `py-spy`, `pprof`, or `monitorEventLoopDelay` metrics).
- Clean separation from load-testing scope: use bounded local reproduction (`L1`) rather than unapproved live production load tests (`L3`/`L4`).

## 3. Technical Principles & Constraints
- **Event-Loop Lag Forensics (Node.js & Async Python):** Because a single JS/asyncio event loop multiplexes all concurrent I/O, ONE synchronous `250ms` CPU spike (`JSON.parse` on huge body, unguarded catastrophic regex `(a+)+$`, synchronous `crypto.pbkdf2Sync`/`fs.readFileSync`, massive `Array.sort`/XLSX build) freezes ALL concurrent requests simultaneously, making healthy DB/Redis spans look slow! Always measure `monitorEventLoopDelay` `p99` alongside CPU profiles.
- **3-Snapshot Heap Diff Protocol (Proving True Leaks):** Never call a single high memory reading a "leak":
  - Take **Snapshot 1** after warm-up + idle GC drain.
  - Run `N` iterations of the suspected flow, pause for GC drain, take **Snapshot 2**.
  - Run `N` more iterations, pause for GC drain, take **Snapshot 3**.
  - Inspect objects allocated between **S1 and S2** that are **STILL retained in S3** (Delta `S3 ∩ (S2 - S1)`). True leaks show linear retainer growth (unbounded module-level `Map`/`Set`, unremoved `EventEmitter.on` listener, closure pinning `Buffer`/`Request`, unclosed stream/timer).
- **Native / Off-Heap RSS Leaks:** If container `RSS` climbs monotonically until `OOMKilled` while V8/Python `heapUsed` stays completely flat, suspect **native C/C++ memory** (Sharp/libvips image buffers, PDF/Chromium child processes not closed via `browser_close`, unclosed SQLite/FFI handles, glibc arena fragmentation)!
- **Goroutine & File Descriptor Leaks:** Track `runtime.NumGoroutine()` (Go) and `/proc/<pid>/fd` count — unclosed HTTP response bodies (`defer resp.Body.Close()` missing!) or channels waiting forever without `ctx.Done()` silently exhaust OS sockets (`EMFILE: too many open files`) and memory.

## 4. Architecture & Implementation

### Symptom-to-Forensic-Tool Matrix

| Symptom Class | Primary Forensic Tool | Exact Culprit Signature |
| :--- | :--- | :--- |
| **Event-Loop Freeze / 100% 1-Core CPU** | Node `--cpu-prof` / Clinic Flame, `py-spy`, Go `pprof` | Wide flat plateau on top of flamegraph (ReDoS regex, sync crypto, huge JSON/XML parse) |
| **V8/Python Heap OOM** | 3-Snapshot Heap Diff (`--heapsnapshot-signal=SIGUSR2`, `memray`/`tracemalloc`) | Growing retained count in `Map`/`Set`, listener arrays, or retained request closures |
| **Flat Heap + Rising Container RSS OOM** | OS `smaps` / `ps` child tree / `jemalloc` / `lsof` | Orphan Chromium/ffmpeg child processes, native C image/PDF buffers, unclosed FDs |
| **Go Slow Leak / Hang** | `/debug/pprof/goroutine?debug=2` | Thousands of goroutines parked on `chan receive` / `semacquire` without `ctx.Done()` |
| **`EMFILE` / Socket Exhaustion** | `lsof -p <pid>` / `ss -tanp` / `Get-NetTCPConnection` | Unclosed HTTP response bodies, missing `keepAlive` agent reuse, leaked file handles |

```ts
// Safe Non-Mutating Event-Loop Lag & RSS-vs-Heap Forensic Watchdog (Strict TS: 0 any, 0 casts)
import { monitorEventLoopDelay } from 'node:perf_hooks'

export interface RuntimeForensicSample {
  readonly event: 'runtime.forensic.sample'
  readonly ts: string
  readonly p99EventLoopLagMs: number
  readonly heapUsedMb: number
  readonly rssMb: number
  readonly externalMb: number
}

export function startRuntimeForensicSampler(
  onSample: (sample: RuntimeForensicSample) => void,
  intervalMs = 5000,
): { readonly stop: () => void } {
  const histogram = monitorEventLoopDelay({ resolution: 20 })
  histogram.enable()
  const timer = setInterval(() => {
    const mem = process.memoryUsage()
    const toMb = (bytes: number): number => Number((bytes / (1024 * 1024)).toFixed(2))
    const sample: RuntimeForensicSample = {
      event: 'runtime.forensic.sample',
      ts: new Date().toISOString(),
      p99EventLoopLagMs: Number((histogram.percentile(99) / 1e6).toFixed(2)),
      heapUsedMb: toMb(mem.heapUsed),
      rssMb: toMb(mem.rss),
      externalMb: toMb(mem.external),
    }
    histogram.reset()
    onSample(sample)
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

## 5. Platform/Vendor Variations
- **Node.js `EventEmitter` Leaks:** Node prints `MaxListenersExceededWarning` at 11 listeners — NEVER silence it with `emitter.setMaxListeners(1000)`! That hides the exact listener leak until OOM! Find where `.on(...)` is registered inside a per-request handler without `.off(...)` or `{ once: true }`.
- **Python `memray` vs `tracemalloc`:** `tracemalloc` only sees Python allocations; use Bloomberg `memray` when Pandas, NumPy, Pillow, or lxml native C extensions leak memory outside Python's heap.
- **Playwright / Headless Browser Workers:** Always close both `page.close()` / `context.close()` AND `browser.close()` in `try/finally` — leaked Chromium renderer processes consume `300–600MB` RSS each!

## 6. Decision Matrix & Trade-Offs

| Forensic Pattern | Diagnostic Precision | Production Overhead | Safe Locally (`L1`)? |
| :--- | :--- | :--- | :--- |
| **`monitorEventLoopDelay` + `memoryUsage()`** | Isolates CPU stall vs Heap vs Native RSS | Negligible (`< 0.1%`) | Yes |
| **Sampling CPU Profile (`--cpu-prof` / `py-spy` / `pprof`)** | Pinpoints exact hot function line | Low (`1–2%`) | Yes |
| **Full V8 Heap Snapshot (`SIGUSR2`)** | Pinpoints exact retainer chain | **HIGH** (pauses process `1–5s` + 2x RAM spike!) | Yes (NEVER on live un-drained prod pod!) |
| **OS FD / Process Tree Audit** | Pinpoints leaked sockets / zombie children | Minimal | Yes |

## 7. Real Production Scenario
An API gateway froze for `6–12 seconds` whenever certain customers submitted email/address strings, tripping Kubernetes readiness probes with zero logged exceptions. Capturing a 15-second `--cpu-prof` flamegraph during a local repro showed 98% CPU inside a single line: an email-validation regex `^([a-zA-Z0-9._-]+)+@` suffering exponential **ReDoS backtracking** on a 42-character string missing `@`. Replacing it with a linear-time validator + length cap (`<= 254` chars) cut execution time from `8,400ms` to `0.02ms` and added a permanent adversarial ReDoS unit test.

## 8. Failure Modes & Edge Cases
- **WRONG:** Silencing `MaxListenersExceededWarning` with `setMaxListeners(0)` or scheduling a nightly `cron` `docker restart` to "fix" an OOM crash.
  **RIGHT:** Capture a 3-snapshot heap diff or RSS process tree, locate the exact uncleaned retainer (`Map`, listener, child process, or unclosed response body), fix the lifecycle leak, and prove flat post-drain memory.
- **WRONG:** Triggering a full V8 heap snapshot on a busy production pod already sitting at 85% container RAM limit (immediately triggers kernel OOMKill!).
  **RIGHT:** Drain the pod from traffic first (with `L4` approval) or reproduce locally/in staging against isolated fixtures.

## 9. Testing & Verification
- For memory leaks: write a bounded local soak test (e.g., 5,000 iterations of the leaking handler), verify `rssMb`/`heapUsedMb` delta grows unbounded before the fix (`FAIL`) and stays bounded after the fix (`PASS`).
- For ReDoS / CPU stalls: add a deterministic adversarial input test asserting execution completes in `< 20ms`.

## 10. Operational Considerations
- Remember to remove temporary forensic stdout/stderr samplers or disable debug profiling ports (`:9229`, `/debug/pprof`) before committing production code.
- Hand verified multi-hour soak benchmarks or cluster capacity re-sizing to `/shadow-perf` under proper Pre-UAT approval.

## 11. Authoritative References
- Node.js Official Diagnostics Guides — *Memory, Flamegraphs & `perf_hooks`*.
- Go Diagnostics Documentation — *Profiling (`pprof`) & Execution Tracer*.
- OWASP — *Regular Expression Denial of Service (ReDoS) Prevention*.

## 12. Limitations & When NOT to Use
- Do NOT confuse healthy bounded cache warmup or lazy garbage collection with a memory leak — always verify across post-drain GC intervals (`shadow-perf/references/04-runtime-cpu-memory-profiling-and-capacity-sizing.md`).
- Do NOT run invasive live-production heap dumps without draining the replica and obtaining `L4` authorization.
