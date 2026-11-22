# 04 — Runtime CPU/Memory Profiling, Event-Loop Lag & Capacity Sizing

## 1. Purpose & Activation Conditions
Isolate application-layer CPU hotspots, Node.js event-loop blocking, Python GIL / Go scheduler contention, true memory leaks vs healthy cache growth, and mathematically size capacity using Little's Law & queueing theory. Activate when window diagnosis (`02`) confirms **service pressure** or steady-state soak degradation inside application runtimes.

## 2. Prerequisites
- Confirmed service-layer bottleneck (load generator healthy, DB/downstream I/O ruled out or quantified separately).
- Repeatable steady-state workload window plus a post-load **drain interval** (`3–5 minutes` of zero/minimal traffic) for memory leak verification.

## 3. Technical Principles & Constraints
- **Post-Drain Memory Proof (Leak vs Cache vs Delayed GC):** A monotonically rising heap graph during a 15-minute load ramp does NOT automatically prove a memory leak — it may be a bounded LRU cache warming up, V8/JVM lazy GC deferral, or test fixture retention! Always compare heap baseline -> peak under steady load -> **post-drain + forced/idle GC** across 3 consecutive load cycles. True leaks show a rising **post-drain sawtooth floor** and growing retained object count in heap snapshot diffs.
- **Event-Loop Lag (Node.js / Async Python):** A single-threaded event loop serving 200 concurrent requests stalls ALL 200 requests when one request executes `120ms` of synchronous CPU work (`JSON.parse` on 25MB payload, `bcrypt` on main thread, catastrophic regex backtracking ReDoS, synchronous `fs.readFileSync`, massive synchronous sorting/PDF rendering). Measure `monitorEventLoopDelay` `p99` alongside CPU profiles.
- **Little's Law & Queueing Knee (`L = \lambda \times W`):** Average concurrency `L` equals arrival rate `\lambda` times mean service time `W`. Once a single-server queue crosses `~70–80%` utilization (`\rho -> 1`), waiting latency explodes nonlinearly (`1 / (1 - \rho)`). Size headroom for `<= 65–70%` sustained peak utilization so transient traffic jitter does not trigger runaway queueing collapse.
- **Reproducible Before/After Flamegraph Diffs:** Never optimize based on intuition ("this loop looks slow"). Capture a CPU/allocation profile before the change, apply the smallest targeted fix, and prove the reduction on the exact same workload and hardware.

## 4. Architecture & Implementation

### Runtime Profiling Toolkit by Stack

| Runtime | CPU Flamegraph Tool | Memory / Heap Diff Tool | Concurrency / Stall Signal |
| :--- | :--- | :--- | :--- |
| **Node.js / TypeScript** | `node --cpu-prof`, Clinic.js Flame, `0x`, Pyroscope | `--heapsnapshot-signal=SIGUSR2` (3-snapshot diff in DevTools) | `perf_hooks.monitorEventLoopDelay()` (`p99 > 20ms` = stall) |
| **Python (FastAPI/Django)** | `py-spy top` / `py-spy record --format speedscope` (zero-restart) | `tracemalloc`, `memray` (native C + Python allocations) | Asyncio loop lag callback (`loop.time()` drift), worker queue depth |
| **Go** | `net/http/pprof` (`/debug/pprof/profile?seconds=30`) | `/debug/pprof/heap`, `alloc_space` vs `inuse_space` | Goroutine leak count (`/debug/pprof/goroutine`), mutex/block profile |
| **PHP / Laravel** | Excimer / Tideways / XHProf (NEVER Xdebug in staging perf!) | `memory_get_peak_usage(true)` per Octane/FPM worker | PHP-FPM `listen queue` & `max_children` exhaustion |

```ts
// Strict TypeScript Little's Law & Utilization Headroom Estimator + Event-Loop Guard (0 any, 0 casts)
export interface CapacityModelInput {
  readonly targetPeakRps: number
  readonly avgServiceTimeMs: number
  readonly targetMaxUtilization: number // e.g. 0.65
  readonly concurrencyPerReplica: number
}

export interface CapacitySizingResult {
  readonly requiredConcurrentCapacity: number
  readonly recommendedReplicas: number
  readonly estimatedUtilizationAtPeak: number
}

export function sizeServiceCapacity(input: CapacityModelInput): CapacitySizingResult {
  const meanServiceSec = input.avgServiceTimeMs / 1000
  // Little's Law: L = lambda * W
  const rawConcurrency = input.targetPeakRps * meanServiceSec
  const safeUtilization = Math.min(0.85, Math.max(0.3, input.targetMaxUtilization))
  const requiredConcurrentCapacity = rawConcurrency / safeUtilization
  const recommendedReplicas = Math.max(2, Math.ceil(requiredConcurrentCapacity / input.concurrencyPerReplica))
  const totalSlots = recommendedReplicas * input.concurrencyPerReplica
  const estimatedUtilizationAtPeak = Number((rawConcurrency / totalSlots).toFixed(3))
  return {
    requiredConcurrentCapacity: Number(requiredConcurrentCapacity.toFixed(2)),
    recommendedReplicas,
    estimatedUtilizationAtPeak,
  }
}
```

### Three-Snapshot Memory Leak Verification Protocol
1. **Snapshot 1 (Baseline Warmed):** Run 5 minutes of steady traffic, pause load for 2 minutes (drain), allow GC to settle, capture Snapshot 1.
2. **Snapshot 2 (Mid-Soak):** Run 20 minutes of steady traffic, pause 2 minutes (drain), capture Snapshot 2.
3. **Snapshot 3 (Late-Soak):** Run another 20 minutes of steady traffic, pause 2 minutes (drain), capture Snapshot 3.
4. **Compare (`Snapshot 3 - Snapshot 2` objects allocated between S1 and S2 that STILL survive at S3):** Only objects growing monotonically across S1 -> S2 -> S3 post-drain are true leaks (common culprits: unbounded `Map`/`Set` caches, unremoved `EventEmitter` listeners, closures capturing request buffers, unclosed AbortControllers/streams).

## 5. Platform/Vendor Variations
- **Node.js Worker Threads & Streams:** Offload heavy CPU tasks (image resizing, CSV/XLSX generation, PDF rendering, crypto hashing, zlib compression of large buffers) to `worker_threads` or dedicated async job workers, and stream large payloads (`pipeline()`) instead of `Buffer.concat` in memory.
- **Containerized CPU Limits (Kubernetes / Docker CFS Throttling):** Even when average container CPU looks like `45%`, tight Kubernetes `limits.cpu` (e.g., `500m`) triggers Linux CFS quota throttling every 100ms period, causing mysterious `80–150ms` p99 spikes! Inspect `container_cpu_cfs_throttled_periods_total`.
- **PHP-FPM / Gunicorn Worker Sizing:** Under-sizing workers causes `502` queue timeouts at low CPU; over-sizing workers causes RAM swap thrashing (`OOMKilled`). Size `max_workers <= floor((available_ram_mb * 0.75) / p95_worker_rss_mb)`.

## 6. Decision Matrix & Trade-Offs

| Observed Runtime Symptom | Most Likely Root Cause | Verified Remediation |
| :--- | :--- | :--- |
| **Node event-loop `p99 > 50ms`, CPU `100%` on 1 core** | Sync CPU work on main thread (huge JSON, regex ReDoS, sync crypto/PDF) | Move to `worker_threads` / async queue; bound input payload size; fix regex |
| **Rising heap during load, flat after 3m drain** | Bounded cache warming or lazy GC (NOT a leak!) | Verify cache `maxEntries`; tune `--max-old-space-size` only if justified |
| **Rising post-drain floor across S1 -> S2 -> S3** | True memory leak (unbounded `Map`, listener leak, retained req closure) | Diff heap snapshots, replace raw `Map` with bounded LRU (`shadow-cache`), clean listeners |
| **Low avg CPU (`40%`), sharp `100ms` p99 spikes in K8s** | Linux CFS CPU throttling on tight container `limits.cpu` | Measure `cfs_throttled_periods`; widen burst quota or remove overly tight CPU cap |
| **High GC pause (`> 100ms`) + high allocation rate** | Short-lived garbage churn (rebuilding huge objects/strings per request) | Stream responses, reuse compiled regex/schemas/clients outside request handler |

## 7. Real Production Scenario
A Node.js reporting API crashed with `OOMKilled` every 6 hours under `40 RPS`. The team initially blamed Prisma connection pools. Running the 3-snapshot post-drain heap protocol revealed `180,000` retained `ExcelJS` workbook buffers held inside an unbounded in-process `Map<string, Buffer>` response cache with no `maxEntries` or TTL, plus a `210ms` event-loop stall whenever a `15MB` export serialized synchronously. Replacing the unbounded `Map` with bounded Redis/object-storage caching (`shadow-cache`) and streaming exports on a background worker flattened post-drain heap at `145MB` over a 12-hour soak and cut API p99 from `890ms` to `62ms`.

## 8. Failure Modes & Edge Cases
- **WRONG:** Leaving Xdebug or synchronous dev debuggers enabled while benchmarking PHP/Python/Node staging containers (inflates latency 5–20x and hides real hotspots).
  **RIGHT:** Benchmark strictly with production build flags (`NODE_ENV=production`, compiled bundles, opcache enabled, zero interactive debuggers).
- **WRONG:** Declaring a memory leak from a 3-minute heap climb without waiting for post-drain GC settlement.
  **RIGHT:** Always execute a post-drain 3-snapshot diff before changing memory limits or eviction policies.
- **WRONG:** Adding horizontal replicas to "fix" a single-row DB lock or an external API rate limit (doubles contention and cost with zero throughput gain!).
  **RIGHT:** Scale replicas ONLY when CPU/event-loop/worker capacity is the verified bottleneck and downstream DB/pool budgets can absorb the added concurrency.

## 9. Testing & Verification
- Verify CPU/memory improvements with identical before/after workload profiles on the same hardware revision, reporting `p50/p95/p99`, `eventLoopLagP99Ms`, `postDrainHeapMb`, `errorRate`, and `achievedRps`.
- Ensure ephemeral profiling containers or staging test runners clean up completely upon finish (zero orphan profilers or leaked heap dumps filling disk).

## 10. Operational Considerations
- Never expose `/debug/pprof` or Node inspector ports (`:9229`) on public interfaces — bind strictly to `127.0.0.1` or internal authenticated admin ports.
- Feed confirmed sizing curves (`RPS/replica`, `RAM/replica`) into `/shadow-presales` capacity models and `/shadow-ops` HPA autoscaling targets (`targetCPUUtilization ~ 60–65%`).

## 11. Authoritative References
- Brendan Gregg — *Flame Graphs* & *Systems Performance* (CPU/Memory/Off-CPU Profiling).
- Node.js Documentation — *Diagnostics (`monitorEventLoopDelay`, `--cpu-prof`, Heap Snapshots)*.
- Neil J. Gunther — *Universal Scalability Law (USL)* & Little's Law Queueing Fundamentals.

## 12. Limitations & When NOT to Use
- Do NOT tune micro-optimizations (`for` vs `.map`) when `90%` of request latency sits in SQL I/O or external HTTP calls — always follow Amdahl's Law and attack the dominant latency stage (`02`) first.
- Do NOT run invasive heap snapshots (`SIGUSR2` pauses the V8 world for `1–5s`!) on a live customer-serving production replica without draining it from the load balancer first (`L4` approval).
