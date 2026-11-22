# 02 — Latency Decomposition, Percentile Integrity & Stored-Window Diagnosis

## 1. Purpose & Activation Conditions
Prevent false bottleneck diagnoses by separating **generator pressure**, **network/edge latency**, **application runtime queuing**, **database/upstream I/O**, and **multi-stage AI/RAG pipelines** using aligned measurement windows and `diagnose_window.mjs`. Activate when interpreting completed load-test results, investigating a slow page/API/RAG request, or comparing candidate releases.

## 2. Prerequisites
- Aligned UTC start/end timestamps (`start`, `end`) from the same warm-up policy, dataset, release SHA, and route cohort.
- Both client-side load generator telemetry (`targetRps`, `achievedRps`, `generatorCpuPct`, `clientP95Ms`, `droppedIterations`) and server-side telemetry (`serviceCpuPct`, `serverP95Ms`, error/timeout counts).

## 3. Technical Principles & Constraints
- **Never Average Percentiles (`p95`/`p99`):** The arithmetic mean of route A's `p95` (`100ms`) and route B's `p95` (`900ms`) is mathematically meaningless (`500ms` is NOT the combined `p95`). Always aggregate raw latency histograms (`HdrHistogram` / Prometheus buckets) or report per-route/cohort percentiles separately alongside sample counts (`N`).
- **Discard Warm-Up Intervals:** JIT compilation (V8 TurboFan, JVM C2), TLS session caches, cold DB buffer pools, and pool pre-warming distort the first `2–5` minutes of a run. Report steady-state windows separately from cold-start behavior.
- **Include Errors & Timeouts in Latency Analysis:** A server that starts returning fast `503` errors in `2ms` makes average/p95 latency look *better* while customers are failing! Always pair latency percentiles with error rate, timeout count, and achieved vs offered RPS.
- **Generator vs Service Bottleneck Separation:** High `clientP95Ms` while `serverP95Ms` stays low and `generatorCpuPct` is saturated (`> 80%`) with `achievedRps < targetRps` proves the **load generator** is the bottleneck, NOT the application.
- **Multi-Stage Pipeline Decomposition (e.g., RAG Slow TTFT):** When a RAG endpoint has healthy DB (`20ms`) and healthy LLM tokens/sec (`45 tok/s`) yet Time-To-First-Token (TTFT) is `4.2s`, decompose every intermediate span: `auth -> query_embed -> vector_search -> rerank -> prompt_assembly -> llm_ttft -> stream_flush`.

## 4. Architecture & Implementation

### Stored-Window Diagnostic CLI (`diagnose_window.mjs`)
```json
{
  "window": { "start": "2026-11-22T10:05:00Z", "end": "2026-11-22T10:20:00Z" },
  "targetRps": 200,
  "achievedRps": 142,
  "generatorCpuPct": 93,
  "serviceCpuPct": 28,
  "clientP95Ms": 1450,
  "serverP95Ms": 110,
  "limits": { "cpuPct": 80, "minDeliveryRatio": 0.9, "p95Ms": 400 }
}
```

```powershell
# Analyze saved aligned telemetry window (L0 read-only evidence diagnosis)
node shadow-perf/scripts/diagnose_window.mjs path/to/window.json
```

### Multi-Stage Latency Budget Breakdown Table (API & RAG TTFT Example)
| Pipeline Stage | Healthy Budget (`p95`) | Measured (`p95`) | Share of Total | Discriminating Check |
| :--- | :--- | :--- | :--- | :--- |
| **Client / Generator / TLS** | `<= 25ms` | `20ms` | `0.5%` | Compare `clientP95Ms - serverP95Ms` + `generatorCpuPct` |
| **Auth + Tenant Context** | `<= 15ms` | `12ms` | `0.3%` | Check JWKS cache hit vs remote IdP introspection |
| **Embedding + Hybrid Retrieval** | `<= 120ms` | `95ms` | `2.3%` | Inspect `pgvector`/OpenSearch query span + prefilter selectivity |
| **Cross-Encoder Reranker (Suspect!)** | `<= 150ms` | **`3,150ms`** | **`76.5%`** | Synchronous serial rerank of 200 chunks on CPU instead of top-25 batch! |
| **Prompt Assembly + LLM TTFT** | `<= 800ms` | `840ms` | `20.4%` | Check prompt prefix cache hit & prompt token length |
| **Total End-to-End TTFT** | `<= 1,110ms` | **`4,117ms`** | `100%` | Target reranker candidate count (`200 -> 25`) before touching DB/LLM |

```ts
// Strict TypeScript Stage Latency Budget Tracker (0 any, 0 casts)
export interface StageTiming {
  readonly stage: string
  readonly durationMs: number
  readonly budgetMs: number
}

export interface StageReport {
  readonly totalMs: number
  readonly dominantStage: string
  readonly overBudgetStages: readonly StageTiming[]
}

export function analyzeStageTimings(stages: readonly StageTiming[]): StageReport {
  let totalMs = 0
  let dominant: StageTiming | undefined
  const overBudget: StageTiming[] = []
  for (const s of stages) {
    totalMs += s.durationMs
    if (!dominant || s.durationMs > dominant.durationMs) {
      dominant = s
    }
    if (s.durationMs > s.budgetMs) {
      overBudget.push(s)
    }
  }
  return {
    totalMs: Number(totalMs.toFixed(2)),
    dominantStage: dominant ? dominant.stage : 'none',
    overBudgetStages: overBudget,
  }
}
```

## 5. Platform/Vendor Variations
- **k6 + Prometheus Remote Write:** Compare `http_req_waiting` (server TTFB) vs `http_req_connecting` / `http_req_tls_handshaking` (network/edge) vs `iteration_duration` (client scheduling).
- **Nginx / Envoy / Cloudflare Proxies:** Always log both `$request_time` (total client-to-proxy time including slow client upload/download) and `$upstream_response_time` (backend time) to instantly isolate slow mobile networks from slow backend code.
- **LLM / Streaming SSE Endpoints:** Measure **TTFT** (Time to First Token), **TPOT** (Time Per Output Token), and **Total Stream Duration** separately — standard HTTP `http_req_duration` lumps stream completion time with initial responsiveness and misleads latency budgets.

## 6. Decision Matrix & Trade-Offs

| `diagnose_window.mjs` Classification | Signal Pattern | Immediate Next Action |
| :--- | :--- | :--- |
| **`GENERATOR_PRESSURE`** | High `generatorCpuPct`, `achievedRps << targetRps`, high `clientP95Ms`, healthy `serverP95Ms` | Scale out load generator / reduce client JS JSON overhead; DO NOT optimize backend yet |
| **`SERVICE_PRESSURE`** | Healthy generator, `achievedRps ~= targetRps`, high `serverP95Ms` & saturated service CPU/pools | Profile backend SQL (`03`) and runtime CPU/memory (`04`) |
| **`MIXED_PRESSURE`** | Both generator and service exceed limits simultaneously | Fix generator saturation first, then re-run a clean controlled window |
| **`UNATTRIBUTED_DEGRADATION`** | High `serverP95Ms` while BOTH generator CPU and service CPU stay low (`< 50%`) | Suspect **waiting**, not compute: DB locks, connection pool wait, DNS/3rd-party HTTP wait, or event-loop/GC stalls |
| **`INSUFFICIENT_EVIDENCE`** | Missing timestamps, CPU, achieved RPS, or misaligned intervals | Collect complete aligned telemetry before drawing conclusions |

## 7. Real Production Scenario
A team complained that a RAG customer-support API had `4.1s` p95 latency and prepared to upgrade PostgreSQL and switch to a smaller LLM. Tracing the full stage waterfall showed PostgreSQL took `22ms` and LLM TTFT took `780ms`, while an unbatched synchronous cross-encoder reranker over `180` candidate chunks burned `3,150ms` in Node/Python IPC wait. Capping rerank input to top-25 RRF candidates cut p95 TTFT from `4.1s` to `1.05s` with zero loss in `NDCG@10` (`shadow-search`) and zero extra infra spend.

## 8. Failure Modes & Edge Cases
- **WRONG:** Taking the mean of `p95` across 5 microservices or 10 endpoints (`(80 + 120 + 950) / 3 = 383ms`) and declaring the `400ms` SLO passed.
  **RIGHT:** Compute percentiles over raw merged histogram buckets or report per-route/cohort `p50/p95/p99` with exact sample counts `N`.
- **WRONG:** Comparing release `v1.2` tested on an empty cold staging DB against release `v1.3` tested on a warmed cache with a different traffic mix.
  **RIGHT:** Hold release config, dataset size, cache regime, workload mix, and warm-up discard constant between baseline and candidate runs.
- **WRONG:** Declaring a "40% speedup" when the candidate started rejecting 15% of requests with fast `429`/`503` responses.
  **RIGHT:** Report latency strictly alongside `achievedRps`, error rate, timeout count, and successful completion counts.

## 9. Testing & Verification
- Run `node shadow-perf/scripts/diagnose_window.mjs` against saved window fixtures and verify deterministic classification (`GENERATOR_PRESSURE` vs `SERVICE_PRESSURE` vs `INSUFFICIENT_EVIDENCE`).
- Verify every performance comparison report states warm-up discard duration, sample count `N`, error rate, and cohort breakdown.

## 10. Operational Considerations
- Keep one **healthy control route** (e.g., lightweight `GET /api/v1/health/ping` or `GET /api/v1/catalog/:id`) in every load/diagnostic window so host-wide network/CPU saturation separates instantly from route-specific code regressions.
- Redact customer tokens, payload values, and SQL literals from exported trace/window artifacts before sharing.

## 11. Authoritative References
- Brendan Gregg — *Systems Performance: Enterprise and the Cloud* (2nd Ed., Latency Analysis & Methodologies).
- Gil Tene — *HdrHistogram & Latency Percentile Aggregation*.
- Shadow Perf Window Analyzer — `shadow-perf/scripts/diagnose_window.mjs`.

## 12. Limitations & When NOT to Use
- `diagnose_window.mjs` classifies pressure hypotheses from aggregate window metrics; CPU and p95 alone cannot prove root cause — always pair with queue wait, lock, or flamegraph evidence (`03` & `04`).
- Do NOT use `shadow-perf` for continuous production SLO alerting — route production monitoring to `/shadow-observe`.
