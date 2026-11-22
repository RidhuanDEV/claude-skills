# 02 — Bulkheads, Circuit Breakers & Adaptive Load Shedding

## 1. Purpose & Activation Conditions
Prevent one slow subsystem, traffic spike, or noisy tenant from cascading into a full-system outage by enforcing **Bulkhead Isolation** (separate concurrency semaphores, connection pools, and worker containers), **Circuit Breakers** (fast-failing dead dependencies), and **Priority Load Shedding** (`503 Retry-After`). Activate when designing multi-workload APIs, hardening external dependencies, or diagnosing cascading timeouts across shared pools.

## 2. Prerequisites
- Classified endpoints by business criticality (**Tier 0:** Auth, Health, Checkout/Payments; **Tier 1:** Core CRUD; **Tier 2:** Heavy PDF/CSV Exports, BI Analytics, AI/LLM Assistants, Recommendations).
- Bounded timeout policies on every DB query, Redis client, and outbound HTTP call.

## 3. Technical Principles & Constraints
- **Ship-Compartment Bulkheads:** Just as watertight bulkheads stop one hull puncture from sinking an entire ship, separate **concurrency semaphores**, **DB connection pools**, and **OS worker containers** guarantee that 50 concurrent PDF/Excel exports or a hanging LLM provider can saturate ONLY the `export` bulkhead (`maxConcurrent = 4` -> fast `503 Retry-After: 10`), leaving 100% of checkout and login slots untouched!
- **Three-State Circuit Breaker (`CLOSED -> OPEN -> HALF_OPEN`):**
  - **CLOSED:** Requests pass normally; sliding window tracks failure ratio / slow-call ratio (`> 50%` over `>= 10` calls).
  - **OPEN:** Dependency is failing — reject calls locally in `< 1ms` (no 10-second socket hang!) and invoke graceful fallback (`03`) while a cooldown timer (`15–60s`) runs.
  - **HALF_OPEN:** Allow ONLY `1–3` bounded probe calls through; if they succeed, close the circuit; if they fail, re-open immediately without flooding the recovering dependency!
- **Priority-Based Load Shedding (Protect Tier 0 Under Overload):** When service queue wait time exceeds budget (`> 200ms` local queue wait) or concurrency hits ceiling, shed **Tier 2** requests FIRST (`503 Service Unavailable` + `Retry-After` header) rather than letting FIFO queues delay ALL requests past every caller's timeout (goodput drops to `0` under un-shedded overload!).
- **Beware Retry Amplification (`3x * 3x * 3x = 27x`!):** If Frontend retries 3x -> API Gateway retries 3x -> Backend Service retries 3x on a saturated DB, a 1x load spike becomes a **27x retry storm**! Enforce **Retry Budgets** (never retry more than `10%` of current traffic), retry ONLY idempotent transient failures with **full jitter**, and NEVER retry once a circuit breaker is `OPEN`!

## 4. Architecture & Implementation

```ts
// Strict TypeScript Bulkhead Concurrency Semaphore + 3-State Circuit Breaker (0 any, 0 casts)
export class BulkheadRejectedError extends Error {
  public readonly retryAfterSec: number
  public constructor(bucket: string, limit: number, retryAfterSec = 5) {
    super(`BULKHEAD_SATURATED: pool '${bucket}' reached limit (${limit})`)
    this.retryAfterSec = retryAfterSec
  }
}

export class BulkheadSemaphore {
  private active = 0

  public constructor(
    private readonly name: string,
    private readonly maxConcurrent: number,
  ) {
    if (maxConcurrent <= 0) {
      throw new RangeError('maxConcurrent must be positive')
    }
  }

  public getActiveCount(): number {
    return this.active
  }

  public async run<T>(task: () => Promise<T>): Promise<T> {
    if (this.active >= this.maxConcurrent) {
      throw new BulkheadRejectedError(this.name, this.maxConcurrent)
    }
    this.active += 1
    try {
      return await task()
    } finally {
      this.active -= 1
    }
  }
}

export type CircuitState = 'CLOSED' | 'OPEN' | 'HALF_OPEN'

export class CircuitOpenError extends Error {
  public constructor(name: string) {
    super(`CIRCUIT_OPEN: dependency '${name}' is temporarily short-circuited`)
  }
}

export class CircuitBreaker {
  private state: CircuitState = 'CLOSED'
  private consecutiveFailures = 0
  private openedAtMs = 0
  private halfOpenProbesInFlight = 0

  public constructor(
    private readonly name: string,
    private readonly failureThreshold: number,
    private readonly cooldownMs: number,
    private readonly now: () => number = Date.now,
  ) {}

  public getState(): CircuitState {
    if (this.state === 'OPEN' && this.now() - this.openedAtMs >= this.cooldownMs) {
      return 'HALF_OPEN'
    }
    return this.state
  }

  public async execute<T>(work: () => Promise<T>): Promise<T> {
    const current = this.getState()
    if (current === 'OPEN') {
      throw new CircuitOpenError(this.name)
    }
    if (current === 'HALF_OPEN') {
      if (this.halfOpenProbesInFlight >= 1) {
        throw new CircuitOpenError(this.name)
      }
      this.state = 'HALF_OPEN'
      this.halfOpenProbesInFlight += 1
    }
    try {
      const result = await work()
      this.consecutiveFailures = 0
      this.state = 'CLOSED'
      return result
    } catch (err: unknown) {
      this.consecutiveFailures += 1
      if (this.state === 'HALF_OPEN' || this.consecutiveFailures >= this.failureThreshold) {
        this.state = 'OPEN'
        this.openedAtMs = this.now()
      }
      throw err
    } finally {
      if (this.halfOpenProbesInFlight > 0) {
        this.halfOpenProbesInFlight -= 1
      }
    }
  }
}
```

## 5. Platform/Vendor Variations
- **Database Pool Bulkheads (Postgres / PgBouncer):** Configure separate PgBouncer pools (`pool_size=25` for `web_core_role`, `pool_size=5` + read replica for `reporting_role`) so a runaway BI query can NEVER starve checkout connections.
- **Process / Container Isolation (Docker / Kubernetes):** Run heavy CPU/RAM workloads (Puppeteer/Playwright PDF export, ffmpeg video transcoding, ExcelJS 100k-row export, ML inference) in dedicated worker containers with explicit `mem_limit` and `cpus` caps so an OOMKill never crashes the customer-facing API process!
- **Reverse Proxy / Envoy / Nginx Rate & Concurrency Limits:** Enforce `limit_conn` / `limit_req` at the ingress edge for cheap protection before requests even allocate application memory.

## 6. Decision Matrix & Trade-Offs

| Pattern | Prevents Which Failure? | Customer Impact When Tripped | Operational Overhead |
| :--- | :--- | :--- | :--- |
| **In-Process `BulkheadSemaphore`** | Heavy route exhausting shared event loop/DB pool | Fast `503 Retry-After` ONLY on heavy route | Very Low |
| **Dedicated Worker Container + Queue** | Export/AI OOM killing core API process | Async `202 Accepted` status tracker | Low–Medium |
| **3-State Circuit Breaker** | Hanging 3rd-party API stalling threads for 30s | Instant fallback or fast error (`< 2ms`) | Low |
| **Priority Load Shedding** | Flash-sale overload collapsing goodput to `0%` | Tier-2 widgets shed; Tier-0 checkout succeeds | Medium |

## 7. Real Production Scenario
Every Friday at 16:00 WIB, regional managers exported 50,000-row XLSX financial reports simultaneously. Exports shared the main Node.js API container and its single 20-connection DB pool, pushing API latency to `30s` and triggering OOMKills that knocked out customer login and payments for 25 minutes. Isolating reports into a separate async worker container (`mem_limit: 1G`) backed by a dedicated 4-connection read-replica pool + `BulkheadSemaphore('export', 3)` kept Tier-0 login/checkout p95 flat at `42ms` even during peak month-end exports.

## 8. Failure Modes & Edge Cases
- **WRONG:** Counting client `400`/`404`/`422` validation errors as circuit-breaker failures (one buggy client sending 20 invalid payloads opens the circuit breaker and takes the dependency down for ALL customers!).
  **RIGHT:** Trip circuit breakers ONLY on infrastructure/availability faults (`5xx`, timeouts, connection resets) — NEVER on `4xx` client errors!
- **WRONG:** Allowing 500 concurrent requests through simultaneously when a circuit transitions from `OPEN` to `HALF_OPEN` (re-crashes the barely recovering dependency!).
  **RIGHT:** Gate `HALF_OPEN` to strictly `1–3` single probe requests at a time while other callers continue getting fast fallback/error until probes succeed.
- **WRONG:** Adding retries at every hop without jitter or retry budgets (amplifies a minor slowdown into a self-inflicted DDoS).
  **RIGHT:** Enforce single-layer bounded retries with full jitter and stop retrying immediately on `CircuitOpenError` or `4xx`.

## 9. Testing & Verification
- Write deterministic unit tests for `BulkheadSemaphore` (assert concurrency `max + 1` throws `BulkheadRejectedError` immediately and slots release cleanly inside `finally` even when tasks reject) and `CircuitBreaker` (`CLOSED -> OPEN -> cooldown -> HALF_OPEN single probe -> CLOSED / re-OPEN`).
- Verify `503` load-shed responses emit a valid `Retry-After` header and structured JSON error envelope.

## 10. Operational Considerations
- Emit Prometheus counters (`bulkhead_rejected_total{pool}`, `circuit_breaker_state{dependency}`) and alert ONLY when Tier-0 circuits stay `OPEN` past the SLO window (`/shadow-observe`).
- Coordinate outbound third-party webhook/payment breaker configurations cleanly with `/shadow-integrate`.

## 11. Authoritative References
- Michael Nygard — *Release It! (2nd Ed.)* — Stability Patterns: Bulkheads, Circuit Breakers, Timeouts & Handshaking.
- AWS Builders' Library — *Timeouts, Retries and Backoff with Jitter* & *Using Load Shedding to Avoid Overload*.

## 12. Limitations & When NOT to Use
- Do NOT put a circuit breaker in front of your **only** authoritative primary database for mandatory writes without an honest user-facing maintenance/read-only mode (fast-failing 100% of writes without fallback is just a faster outage — though shedding *secondary* queries to protect primary writes IS valuable!).
- Do NOT use in-process `BulkheadSemaphore` alone as a global multi-pod rate limiter — pair with Redis/API-gateway distributed rate limiting (`/shadow-api`) when cluster-wide caps are required.
