# sub-OBSERVABILITY-PROFILING — OpenTelemetry, PromQL, LogQL, Grafana & Performance Profiling

Use when instrumenting applications with OpenTelemetry (OTel), writing Prometheus (`PromQL`) or Loki (`LogQL`) queries,
designing Grafana dashboards and alert rules, or profiling database queries (`EXPLAIN ANALYZE`), CPU bottlenecks, and
memory leaks. Pair with `CLOUD-SRE.md` and `DEVOPS.md`.

## 1. OpenTelemetry (OTel) instrumentation rules

- **Context propagation**: propagate `traceparent` / `tracestate` (W3C Trace Context) across every boundary:
  Browser/Mobile → API Gateway → Backend Service → Message Queue headers (Kafka/RabbitMQ/BullMQ) → Worker → Database/External HTTP.
- **Span & attribute discipline**:
  - Follow OTel Semantic Conventions (`http.request.method`, `http.route`, `http.response.status_code`, `db.system`, `db.operation.name`).
  - **Span names must be low-cardinality templates**: `GET /api/v1/orders/{id}`, **NEVER** `GET /api/v1/orders/948123`
    (putting dynamic IDs in span or metric names explodes time-series cardinality).
  - Put high-cardinality identifiers (`order.id`, `user.id`, `tenant.id`) in **Span Attributes** and **Structured Logs**,
    never in **Metric Labels**.
- **Error recording**: on exceptions, call `span.recordException(err)` and `span.setStatus({ code: SpanStatusCode.ERROR, message: err.message })`.
- **Log-to-Trace correlation**: inject `trace_id` and `span_id` automatically into every structured JSON log line.

## 2. Prometheus (`PromQL`) & Metric authoring rules

- **Metric types**:
  - `Counter` (`_total` suffix): monotonically increasing counts (`http_requests_total`, `orders_created_total`).
  - `Histogram` (`_bucket`, `_sum`, `_count`): request duration and payload sizes. Choose bucket boundaries matching your
    SLO targets (e.g., `[0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1, 2.5, 5, 10]` seconds).
  - `Gauge`: current point-in-time values (`db_pool_active_connections`, `queue_depth_messages`).
- **Cardinality limit (strict rule)**: never put `user_id`, `email`, `ip_address`, `request_id`, or raw URL paths into
  Prometheus labels. Keep total label combinations per metric bounded ($< 1,000$ active series per instance).
- **Essential `PromQL` patterns**:
  - **Request Rate (RPS)**: `sum by (service, route) (rate(http_requests_total[5m]))`
  - **Error Ratio (%)**:
    ```promql
    sum by (service) (rate(http_requests_total{status=~"5.."}[5m]))
    /
    sum by (service) (rate(http_requests_total[5m]))
    ```
  - **Latency Quantile (`p95`)**:
    ```promql
    histogram_quantile(0.95, sum by (le, service, route) (rate(http_request_duration_seconds_bucket[5m])))
    ```

## 3. Loki (`LogQL`) & Grafana dashboard design

- **`LogQL` query order (fastest to slowest)**:
  1. Stream selector (`{service="order-api", env="prod"}`)
  2. Line filter (`|= "PAYMENT_FAILED"` or `!= "healthz"`) — filter raw text *before* JSON parsing!
  3. Parser (`| json`)
  4. Label/field filter (`| duration_ms > 1000`)
- **Grafana dashboard hierarchy**:
  - Row 1: **SLO & Golden Signals Overview** (Availability %, Error Budget Burn, Total RPS, Global p50/p95/p99 Latency).
  - Row 2: **Service & Route Breakdown** (Top slowest routes, 4xx vs 5xx by endpoint).
  - Row 3: **Dependencies & Saturation** (DB connection pool usage, slow queries, Redis hit ratio/latency, Queue lag/DLQ depth, CPU/Memory/Event-Loop lag).

## 4. Database (`EXPLAIN ANALYZE`) & Runtime Profiling rules

- **PostgreSQL query profiling**:
  - Run `EXPLAIN (ANALYZE, BUFFERS, VERBOSE, SETTINGS)` (wrap inside `BEGIN; ... ROLLBACK;` if profiling `UPDATE`/`DELETE`).
  - Inspect: `Seq Scan` with high `Rows Removed by Filter` (needs index), `Bitmap Heap Scan` with `Lossy` pages (`work_mem` too small),
    `Sort Method: external merge Disk` (`work_mem` spill), large mismatch between `Estimated rows` and `Actual rows` (run `ANALYZE`),
    and high `Buffers: shared read` + `Temp read/written`.
- **CPU & Memory leak profiling**:
  - **CPU**: capture 30–60s flamegraphs (`pprof` in Go, `py-spy` in Python, `0x` / `--cpu-prof` in Node, JFR/async-profiler in JVM);
    look for wide flat plateaus (sync JSON parsing, regex backtracking, crypto on main thread, N+1 serialization).
  - **Memory leak**: take two heap snapshots separated by sustained traffic under load; compare retained object delta
    (unbounded module-level `Map`/cache without LRU/TTL, unremoved event listeners, closures holding large request buffers).
