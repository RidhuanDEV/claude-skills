# 04 — Cardinality Control, Tail-Based Sampling & Telemetry Cost Governance

## 1. Purpose & Activation Conditions
Prevent Prometheus TSDB memory blowups, Loki index explosions, and runaway SaaS observability bills by enforcing strict **metric cardinality budgets**, **OTel Collector tail-based sampling**, **metric relabeling**, and **telemetry tiering**. Activate when designing Prometheus histograms/counters, configuring OTel sampling rates, or diagnosing spiking observability costs.

## 2. Prerequisites
- Inventory of active Prometheus metrics (`count by (__name__) ({__name__=~".+"})`), Loki stream counts, and daily OTel trace/log GB ingestion rates.
- Defined critical latency thresholds (`p95`/`p99`) and error classes (`5xx`, domain exceptions) that MUST survive trace sampling.

## 3. Technical Principles & Constraints
- **Cardinality Multiplication Law:** Total time series = `product(distinct_values_per_label) * bucket_count` (for histograms). A histogram with 12 buckets × 5 methods × 50 routes × 10,000 `tenant_id`s creates `30,000,000` active series — instantly OOM-killing Prometheus.
- **Right Signal for High Cardinality:**
  - **Prometheus Metrics:** Low cardinality ONLY (`service`, `env`, `method`, `route_template`, `status_class`, `region`). Never `user_id`, `request_id`, `trace_id`, `ip_address`, `email`, `order_id`, or raw URL paths.
  - **OTel Spans & Structured Logs:** Safe home for bounded high-cardinality identifiers (`tenantId`, `userId`, `requestId`, `orderId`) once PII-redacted.
  - **Prometheus Exemplars:** Attach a single sampled `trace_id` to histogram buckets without creating new metric series.
- **Tail-Based Sampling Over Blind Head Sampling:** Head-based sampling (`1%–5%`) decides *before* the request finishes, silently discarding `95%–99%` of rare `500` errors and `3s` outliers. Route traces through an OTel Collector tail-sampling gateway that keeps **100% of error traces**, **100% of slow traces (`> p95`)**, and **5–10% of fast healthy `2xx` traces**, while dropping `/health` and `/metrics`.
- **Native Histograms / Exponential Buckets:** Prefer Prometheus native histograms or carefully bounded bucket edges (`[0.05, 0.1, 0.25, 0.5, 1, 2.5, 5]`) instead of 30 default fine-grained buckets on every route.

## 4. Architecture & Implementation

```yaml
# OpenTelemetry Collector Gateway: Redaction + Tail-Based Sampling + Cost Guardrails
processors:
  memory_limiter:
    check_interval: 1s
    limit_mib: 1024
    spike_limit_mib: 256

  attributes/redact:
    actions:
      - key: http.request.header.authorization
        action: delete
      - key: http.request.header.cookie
        action: delete
      - key: db.statement
        action: hash

  filter/drop_health:
    error_mode: ignore
    traces:
      span:
        - 'attributes["http.route"] == "/health"'
        - 'attributes["http.route"] == "/ready"'
        - 'attributes["http.route"] == "/metrics"'

  tail_sampling:
    decision_wait: 10s
    num_traces: 50000
    expected_new_traces_per_sec: 2000
    policies:
      - name: keep-errors
        type: status_code
        status_code: { status_codes: [ERROR] }
      - name: keep-http-5xx
        type: numeric_attribute
        numeric_attribute: { key: http.response.status_code, min_value: 500, max_value: 599 }
      - name: keep-slow-traces
        type: latency
        latency: { threshold_ms: 800 }
      - name: sample-healthy-baseline
        type: probabilistic
        probabilistic: { sampling_percentage: 5 }

  batch:
    timeout: 2s
    send_batch_size: 1024
```

```ts
// Strict TypeScript Route Template & Cardinality Guard Middleware (0 any, 0 casts)
const UUID_SEGMENT_RE = /\/[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}(?=\/|$)/g
const NUMERIC_SEGMENT_RE = /\/\d+(?=\/|$)/g
const KNOWN_ROUTES = new Set<string>([
  '/api/v1/orders',
  '/api/v1/orders/:id',
  '/api/v1/checkout',
  '/api/v1/webhooks/payment',
  '/health',
])

export function normalizeMetricRoute(matchedRoute: string | undefined, rawPath: string): string {
  const candidate = (matchedRoute ?? rawPath.split('?')[0] ?? '/')
    .replace(UUID_SEGMENT_RE, '/:id')
    .replace(NUMERIC_SEGMENT_RE, '/:id')
  return KNOWN_ROUTES.has(candidate) ? candidate : '/unmatched'
}
```

## 5. Platform/Vendor Variations
- **Prometheus / Mimir / Thanos:** Set `sample_limit` and `label_limit` per scrape job (`sample_limit: 10000`) and use `metric_relabel_configs` to drop accidental high-cardinality labels before ingestion crashes the TSDB. For distributed tail sampling across multiple OTel Collectors, deploy a two-tier collector topology using the `loadbalancingexporter` routed by `traceID` so all spans of the same trace hit the same tail-sampling collector instance!
- **SaaS Vendors (Datadog / New Relic / Grafana Cloud):** High-cardinality custom metrics and unindexed raw debug logs account for `60–80%` of surprise bills; enforce ingest drop rules at the OTel Collector edge before data crosses the paid network boundary (coordinate budget governance with `/shadow-finops`).
- **Kubernetes cAdvisor / kube-state-metrics:** Drop unused container/pod metric families (`container_tasks_state`, `container_memory_failures_total`) via `metric_relabel_configs` to cut scrape memory by `40–60%`.

## 6. Decision Matrix & Trade-Offs

| Sampling / Storage Mechanism | Incident Blind-Spot Risk | Collector RAM Overhead | Monthly Cost | Best Fit |
| :--- | :--- | :--- | :--- | :--- |
| **100% Unsampled Traces** | Zero | Low | Very High | Low-traffic dev/staging (`< 50 RPS`) |
| **Blind Head Sampling (`5%`)** | **High** (loses 95% of 5xx) | Minimal | Low | Avoid for error-sensitive production APIs |
| **Collector Tail Sampling (`100%` err/slow + `5%` ok)** | Very Low | Medium (buffers 10s in RAM) | Low–Medium | Production default for medium/high RPS |
| **Prometheus Exemplars on Histograms** | Low (links metric -> trace) | Negligible | Minimal | Jump from p99 metric spike to slow trace |

## 7. Real Production Scenario
A crawler bot hit 450,000 random 404 URLs (`/wp-login-98412.php`, `/orders/random-uuid`) on an API whose Prometheus middleware used `req.path` as the `route` label. Active time series spiked from 18,000 to 5.4 million in 12 minutes, OOM-killing Prometheus right during a billing release. Collapsing unmatched paths to `route_template="/unmatched"`, enforcing `sample_limit: 15000`, and running `telemetry_hygiene_verifier.py` in CI permanently closed the vulnerability.

## 8. Failure Modes & Edge Cases
- **WRONG:** Running 3 horizontally scaled OTel Collectors with `tail_sampling` behind a round-robin load balancer (spans of the same trace land on different collectors, causing partial/broken traces).
  **RIGHT:** Put a lightweight gateway layer with `loadbalancingexporter` (`routing_key: traceID`) in front of the tail-sampling collector tier so all spans for a `traceId` converge on one collector.
- **WRONG:** Adding `tenant_id` to Prometheus latency histograms when you have 5,000 B2B tenants.
  **RIGHT:** Keep Prometheus global or grouped by tier (`plan_tier="enterprise|pro|free"`), and slice per-tenant latency via structured wide-event logs or OTel span queries.
- **WRONG:** Logging `/health` and `/metrics` scrapes every 5 seconds from 20 pods (`345,600` useless log lines/day).
  **RIGHT:** Filter out `200 OK` health/readiness probes at middleware or OTel Collector edge, emitting logs only when health checks return non-200.

## 9. Testing & Verification
- Run `python shadow-observe/scripts/telemetry_hygiene_verifier.py --check-metrics-config metrics.json` to block high-cardinality labels and unsafe head-only sampling in CI.
- Query Prometheus TSDB status (`/api/v1/status/tsdb`) weekly in staging/prod to inspect `seriesCountByMetricName` and `labelValueCountByLabelName` top-10 offenders.

## 10. Operational Considerations
- Monitor the observability pipeline itself (`otelcol_processor_refused_spans`, `prometheus_tsdb_head_series`, `loki_discarded_bytes_total`) with capacity alerts so you know before telemetry goes dark.
- Review top-5 telemetry cost drivers monthly alongside `/shadow-finops`.

## 11. Authoritative References
- Prometheus Documentation — *Metric and Label Naming & Cardinality Limits*.
- OpenTelemetry Collector Contrib — *Tail Sampling Processor & Load-Balancing Exporter Architecture*.
- Grafana Labs — *Loki Labels Best Practices & Structured Metadata*.

## 12. Limitations & When NOT to Use
- Tail sampling adds a `5–15s` buffering delay and requires collector RAM proportional to `RPS * decision_wait`; for ultra-high-throughput (`> 50k RPS`) edge gateways, combine deterministic error/slow span metrics (`spanmetrics` connector) with targeted trace sampling.
- Do NOT use `shadow-observe` for cloud compute/LLM token FinOps showback — coordinate cost allocation with `/shadow-finops`.
