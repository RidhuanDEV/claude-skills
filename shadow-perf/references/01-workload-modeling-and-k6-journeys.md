# 01 — Workload Modeling, k6 Journey Compilation & Pre-UAT Execution Safety

## 1. Purpose & Activation Conditions
Design scientifically defensible load, smoke, spike, and soak experiments derived from authoritative API contracts and real traffic mixes, using the offline `openapi_to_k6_scaffold.mjs` compiler with strict `L3`/`L4` execution approval boundaries. Activate **ONLY** when entering a **Pre-UAT / Staging Readiness Gate** or when the Monarch explicitly requests load/stress/spike benchmarking — NEVER automatically during feature coding.

## 2. Prerequisites
- Authoritative resolved OpenAPI contract (JSON or project-parsed YAML) and its exact revision SHA from the API owner (avoid stale copied specs).
- Defined business journeys, target environment allowlist (staging or isolated loopback — NEVER unapproved production), synthetic test identities, cleanup ownership, and pre-agreed SLO/stop thresholds.
- Explicit scope-specific **`L3` (`L4` if touching shared/live environments)** approval before executing any traffic generation beyond local in-memory dry-run validation.

## 3. Technical Principles & Constraints
- **Open-Loop (Arrival-Rate) vs Closed-Loop (Concurrency) Modeling:**
  - Use **Arrival-Rate (`constant-arrival-rate` / `ramping-arrival-rate`)** for independent external user arrivals (public APIs, webhooks, checkout surges) so slow responses do NOT artificially throttle offered load (**coordinated omission prevention**).
  - Use **Closed-Loop Concurrency (`ramping-vus` with realistic think time)** ONLY when modeling a fixed pool of interactive operators (e.g., 50 call-center agents waiting for one screen before clicking the next).
- **One Question Per Test Type:**
  - **Smoke (`1–3 VUs`, `1–2m`):** Proves journey wiring, status contracts, auth, and cleanup work.
  - **Load (expected peak + `20–50%` headroom, `15–30m`):** Measures steady-state latency, errors, and utilization after warm-up discard.
  - **Spike (`3–10x` burst, rapid ramp & recovery):** Validates admission control, autoscaling, queueing, and post-spike recovery.
  - **Soak (steady load, `2–12h`):** Exposes slow memory leaks, connection leaks, disk/WAL growth, and cache fragmentation.
- **Exact Contract Status & Synthetic Isolation:** Validate exact expected success status (`201` on create, `200` on read) and semantic body assertions (created ID, tenant echo, cursor continuity). Never treat `401`/`403`/`404` as "handled" inside a positive journey. Use per-run prefixes or disposable test tenants so write traffic cleans up cleanly.
- **Zero Secrets in Templates & Explicit Loopback Guard:** The offline scaffold CLI (`openapi_to_k6_scaffold.mjs`) requires an explicit loopback `BASE_URL`, matching `APPROVED_PROFILE`, disables cross-origin redirects (preventing credential leakage), and rejects auth/header/cookie routes unless paired with a project-owned credential adapter.

## 4. Architecture & Implementation

### Offline Journey Fixture & Dry-Run Compilation Workflow
```json
{
  "steps": [
    {
      "operation": "POST /orders",
      "expect": 201,
      "body": { "label": "synthetic-load-run-01", "items": [{ "sku": "SKU-001", "qty": 1 }] },
      "capture": { "name": "createdOrderId", "field": "id" }
    },
    {
      "operation": "GET /orders/{id}",
      "expect": 200,
      "path": { "id": "$createdOrderId" }
    }
  ],
  "mock": [
    { "method": "POST", "path": "/orders", "status": 201, "response": { "id": "ord-syn-17" } },
    { "method": "GET", "path": "/orders/ord-syn-17", "status": 200 }
  ]
}
```

```powershell
# 1. Validate journey wiring offline in memory (L0/L1 — writes no files, sends zero network traffic)
node shadow-perf/scripts/openapi_to_k6_scaffold.mjs --spec api.json --journey fixture.json --dry-run

# 2. Generate inert profile templates (smoke / load / spike — starts at 1 iteration, refuses to overwrite)
node shadow-perf/scripts/openapi_to_k6_scaffold.mjs --spec api.json --journey fixture.json --out tests/perf-candidate

# 3. Verify the offline scaffold tool unit tests
node --test shadow-perf/tests/scaffold.test.mjs
```

### Arrival-Rate Volume & Safety Budget Calculator
```ts
// Strict TypeScript Pre-Execution Load Budget Estimator (0 any, 0 casts)
export interface JourneyBudgetInput {
  readonly targetRps: number
  readonly durationSec: number
  readonly stepsPerIteration: number
  readonly retryRateRatio: number
  readonly writeStepsPerIteration: number
}

export interface JourneyBudgetEstimate {
  readonly totalIterations: number
  readonly estimatedHttpRequests: number
  readonly estimatedDbWrites: number
}

export function estimateLoadBudget(input: JourneyBudgetInput): JourneyBudgetEstimate {
  const totalIterations = Math.ceil(input.targetRps * input.durationSec)
  const retryMultiplier = 1 + Math.max(0, input.retryRateRatio)
  const estimatedHttpRequests = Math.ceil(totalIterations * input.stepsPerIteration * retryMultiplier)
  const estimatedDbWrites = Math.ceil(totalIterations * input.writeStepsPerIteration)
  return { totalIterations, estimatedHttpRequests, estimatedDbWrites }
}
```

## 5. Platform/Vendor Variations
- **k6 (Grafana k6 Open Source / k6 Operator):** Supports `constant-arrival-rate` with `preAllocatedVUs` and `maxVUs`; always monitor `dropped_iterations` so you know immediately if the generator ran out of VUs to hold the requested arrival rate.
- **Authenticated / Multi-Tenant Journeys:** Supply a project-owned short-lived token fixture adapter injected via environment variable at runtime (never hardcoded in scripts, git, or k6 summary exports).
- **Cloud / Managed Staging Environments:** Check cloud NAT gateway port limits, WAF/Cloudflare rate limiters, and third-party payment/SMS sandbox quotas BEFORE running load — mock external paid/rate-limited vendors behind a deterministic wiremock/stub layer during staging load tests.

## 6. Decision Matrix & Trade-Offs

| Experiment Type | Traffic Model | Typical Duration | Primary Failure Mode Detected | Cleanup & Cost Risk |
| :--- | :--- | :--- | :--- | :--- |
| **Dry-Run Mock Replay** | In-memory fixture | `< 1s` | Broken contract paths, capture mismatches | Zero (no live traffic) |
| **Smoke Test** | `1–3 VUs` | `1–2m` | Env wiring, auth adapter, basic 5xx | Negligible |
| **Load Test** | Arrival-rate (`1x–1.5x` peak) | `15–30m` (+ `3–5m` warm-up) | Missing indexes, pool saturation, p95 SLO breach | Medium (synthetic DB cleanup needed) |
| **Spike Test** | Rapid burst (`3x–10x` peak) | `5–15m` + recovery window | Queue pile-up, autoscaler lag, non-recovery deadlock | High (requires strict abort thresholds) |
| **Soak Test** | Steady `0.7x–1x` peak | `2–12h` | Memory leaks, FD exhaustion, WAL/disk growth | High (requires storage monitoring) |

## 7. Real Production Scenario
Before a national flash-sale launch, a team ran a closed-loop `50 VUs` script with `sleep(1)` against staging and celebrated `p95 = 320ms`. However, under closed-loop VUs, when checkout slowed from 100ms to 1,200ms, each VU naturally sent half as many requests — hiding the throughput collapse (coordinated omission). Re-running with `constant-arrival-rate` at the true forecasted `120 req/s` immediately revealed `dropped_iterations > 30%` and PostgreSQL pool exhaustion at `75 req/s`, allowing the team to fix connection pooling and add an index 4 days before launch.

## 8. Failure Modes & Edge Cases
- **WRONG:** Timing an in-memory `--dry-run` mock fixture and reporting `p95 = 4ms` as service performance evidence.
  **RIGHT:** Treat `--dry-run` strictly as journey-wiring validation; real performance claims require an approved staging run with pinned service SHA, dataset revision, and cache state.
- **WRONG:** Leaving `redirect: follow` enabled in k6 when testing authenticated routes against a misconfigured proxy that redirects to an external domain (forwards `Authorization` headers!).
  **RIGHT:** Set `redirects: 0` (disabled) and assert exact status codes on an explicit allowlisted base origin.
- **WRONG:** Launching a `500 RPS` load test directly against production or without an explicit stop condition and cleanup owner.
  **RIGHT:** Enforce Pre-UAT ONLY + explicit `L3`/`L4` approval covering target, request volume budget, hard abort triggers (e.g., `http_req_failed > 2%` or `p95 > 2000ms` for 60s), and rollback/cleanup owner.

## 9. Testing & Verification
- Always run `node --test shadow-perf/tests/scaffold.test.mjs` after modifying scaffold logic or fixtures.
- Validate every new k6 journey with `--dry-run` first, then a `1-iteration` loopback smoke check before proposing an `L3` staging load window.

## 10. Operational Considerations
- Pin every benchmark report with a **Reproducibility Manifest**: `git_sha`, `openapi_rev`, `fixture_rev`, `dataset_rows`, `cache_state` (cold vs warm), `warmup_discard_sec`, `workload_mode`, `offered_vs_achieved_rps`, and `cleanup_verified`.
- Tag all k6 requests with a bounded `scenario` metric label (never raw dynamic URLs or user IDs) so Prometheus metrics do not suffer cardinality blowup during load tests.

## 11. Authoritative References
- Grafana k6 Documentation — *Open vs Closed Models (Arrival Rate Executors) & Threshold Aborts*.
- Gil Tene — *How NOT to Measure Latency (Coordinated Omission)*.
- Shadow Perf Offline Compiler — `shadow-perf/scripts/openapi_to_k6_scaffold.mjs`.

## 12. Limitations & When NOT to Use
- **NEVER** trigger `shadow-perf` automatically during normal feature coding or unit testing.
- Do NOT use synthetic k6 tests to measure real end-user browser Core Web Vitals (`LCP`/`INP`/`CLS`) — use RUM & CrUX telemetry under `/shadow-seo` and `/shadow-observe`.
