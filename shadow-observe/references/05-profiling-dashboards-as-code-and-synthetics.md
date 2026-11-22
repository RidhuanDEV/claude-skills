# 05 — Golden Signals (RED/USE), Continuous Profiling, Dashboards-as-Code & Synthetics

## 1. Purpose & Activation Conditions
Design high-signal **RED & USE dashboards versioned as code**, deploy external **synthetic blackbox probes** for user-journey uptime verification, and wire **low-overhead continuous profiling** to connect latency/CPU anomalies directly to exact code lines. Activate when designing service dashboards, provisioning alerting/dashboard GitOps, or adding uptime monitoring.

## 2. Prerequisites
- Metric scraping (Prometheus/VictoriaMetrics), log aggregation (Loki), and tracing (Tempo/Jaeger) endpoints available via `/shadow-ops`.
- Git repository structure for provisioned dashboards (`observability/dashboards/*.json`) and alert rules (`observability/alerts/*.yaml`).

## 3. Technical Principles & Constraints
- **RED Method (Request-Driven Services):** Every API/service overview dashboard starts at the top row with **R**ate (RPS), **E**rrors (5xx ratio + SLO burn), and **D**uration (`p50`, `p95`, `p99` histograms with trace exemplars).
- **USE Method (Infrastructure & Pools):** Every resource layer (DB connections, Redis memory, worker thread pools, CPU, disk I/O, network sockets) tracks **U**tilization, **S**aturation (queue depth / pool wait time), and **E**rrors.
- **Dashboards-as-Code (Zero ClickOps Drift):** Never leave production dashboards solely inside a mutable Grafana SQLite/Postgres DB. Store dashboards in Git (Grafana JSON provisioning, Grafonnet, or Terraform) with automated schema validation so staging, prod, and DR rebuild identically.
- **Synthetic Probes Measure What Internal Metrics Miss:** If DNS expires, TLS breaks, or Nginx rejects connections at the edge, backend application metrics show `0` errors (`0` traffic!). Always run external blackbox probes (HTTP + TLS expiry + critical read-only login/catalog flow) from outside the cluster.
- **Continuous Profiling (< 1–2% CPU Overhead):** Use sampling profilers (Pyroscope / Parca / Go `pprof` / Node V8 inspector CPU profiles / `py-spy`) linked by `span_id` so CPU regressions pinpoint exact functions without needing a local repro.

## 4. Architecture & Implementation

### 3-Row Actionable Service Dashboard Blueprint
| Row | Purpose | Panels (Max 3–4 Per Row) | Action / Drill-Down Link |
| :--- | :--- | :--- | :--- |
| **Row 1: SLO & Customer Symptoms (RED)** | Answer "Are users hurting right now?" in `< 5s` | 28d Error Budget Remaining · Request Rate by `route_template` · 5xx Error Ratio · Latency `p50/p95/p99` with Trace Exemplars | Click exemplar -> Tempo trace; click route -> filtered Loki wide events |
| **Row 2: Dependency & Pool Saturation (USE)** | Answer "Which dependency is stalling?" | DB Pool Active/Waiting · Slow SQL p95 · Redis Hit Ratio & Latency · Outbound HTTP 3rd-Party p95/Errors · Queue Lag & DLQ Count | Jump to DB/Queue dashboard or `/shadow-perf` window diagnostics |
| **Row 3: Runtime & Release Context** | Correlate regressions with deploys/runtime | Deployment SHA Annotations · Event-Loop Lag / GC Pause · Heap Used vs Limit · Continuous CPU Flamegraph Link | Compare `service.version` before vs after deploy |

```yaml
# Prometheus Blackbox Exporter Synthetic Probe (Edge + TLS + Health Readiness)
scrape_configs:
  - job_name: synthetic_blackbox_https
    metrics_path: /probe
    params:
      module: [http_2xx_tls]
    scrape_interval: 30s
    static_configs:
      - targets:
          - https://api.example.com/health/ready
          - https://app.example.com/
    relabel_configs:
      - source_labels: [__address__]
        target_label: __param_target
      - source_labels: [__param_target]
        target_label: instance
      - target_label: __address__
        replacement: blackbox-exporter:9115
```

```ts
// Strict TypeScript Readiness vs Liveness Health Probe Contract (0 any, 0 casts)
export interface DependencyCheckResult {
  readonly name: string
  readonly healthy: boolean
  readonly latencyMs: number
  readonly reason?: string
}

export interface ReadinessPayload {
  readonly status: 'ready' | 'degraded'
  readonly releaseSha: string
  readonly checkedAt: string
  readonly dependencies: readonly DependencyCheckResult[]
}

export async function buildReadinessProbe(
  releaseSha: string,
  checks: ReadonlyArray<{ readonly name: string; readonly ping: () => Promise<void> }>,
): Promise<{ readonly httpStatus: 200 | 503; readonly body: ReadinessPayload }> {
  const results: DependencyCheckResult[] = []
  for (const check of checks) {
    const start = performance.now()
    try {
      await check.ping()
      results.push({ name: check.name, healthy: true, latencyMs: Math.round(performance.now() - start) })
    } catch (err: unknown) {
      results.push({
        name: check.name,
        healthy: false,
        latencyMs: Math.round(performance.now() - start),
        reason: err instanceof Error ? err.message : 'dependency_check_failed',
      })
    }
  }
  const allHealthy = results.every((r) => r.healthy)
  return {
    httpStatus: allHealthy ? 200 : 503,
    body: {
      status: allHealthy ? 'ready' : 'degraded',
      releaseSha,
      checkedAt: new Date().toISOString(),
      dependencies: results,
    },
  }
}
```

## 5. Platform/Vendor Variations
- **Grafana Provisioning (`/etc/grafana/provisioning/dashboards`):** Mount Git-tracked JSON dashboards as read-only (`allowUiUpdates: false`) in production; develop edits in staging Grafana, export JSON, open a PR, and let CI deploy.
- **Liveness (`/health/live`) vs Readiness (`/health/ready`) in Kubernetes/Docker:**
  - `/health/live`: Checks ONLY in-process event-loop/deadlock liveness — NEVER queries PostgreSQL or Redis (otherwise a 5-second DB blip causes Kubernetes to kill-loop every healthy app pod!).
  - `/health/ready`: Checks critical local/DB dependencies with short timeouts (`<= 1500ms`) so load balancers stop routing traffic to broken pods without restarting them unnecessarily.
- **Continuous Profiling:** Pyroscope / Grafana Phlare (`@pyroscope/nodejs`, `pyroscope-io` Python, Go `runtime/pprof`) or Parca (eBPF kernel-level zero-code CPU profiling on Linux hosts).

## 6. Decision Matrix & Trade-Offs

| Telemetry Signal | Answers Which Question? | Overhead | Blind Spot If Used Alone |
| :--- | :--- | :--- | :--- |
| **RED Metrics + SLOs** | "Is the service degrading & how fast?" | Very Low | Cannot show *which* code line or tenant broke |
| **USE Saturation Metrics** | "Is a queue, pool, disk, or CPU saturated?" | Very Low | Does not prove user-visible errors |
| **External Synthetic Probes** | "Can an outside user reach TLS/DNS/Edge?" | Minimal | Only covers scripted canary paths, not full traffic |
| **Continuous Profiling** | "Which exact function consumes CPU/heap?" | `1–2%` CPU | Does not capture external network wait or SQL locks |

## 7. Real Production Scenario
An e-commerce API showed `0.00%` error rate in Prometheus during a 22-minute outage because an expired TLS wildcard certificate at the Cloudflare/Nginx edge rejected all customer handshakes before traffic ever reached Node.js pods. Adding external blackbox synthetic probes (`probe_ssl_earliest_cert_expiry - time() < 86400 * 14` + `probe_success == 0`) caught the next misconfigured DNS renewal 13 days before expiry.

## 8. Failure Modes & Edge Cases
- **WRONG:** Checking PostgreSQL + Redis + external payment gateway inside Kubernetes `livenessProbe` (`/health/live`).
  **RIGHT:** Keep `/health/live` purely process-local; put DB connectivity checks in `/health/ready` with bounded timeouts and NEVER call paid/rate-limited 3rd-party APIs inside high-frequency health probes.
- **WRONG:** Building a 45-panel "wall of charts" dashboard with mismatched time ranges and no deployment markers.
  **RIGHT:** Limit overview dashboards to 3 crisp rows (RED -> USE -> Runtime/Deploy markers), shared time picker, and drill-down links to traces and logs.
- **WRONG:** Editing production Grafana panels manually in the browser without exporting JSON to Git.
  **RIGHT:** Version all dashboards and alert YAML in Git and validate them in CI before deploy.

## 9. Testing & Verification
- Validate Prometheus alert rules with `promtool check rules` and Grafana JSON dashboards via CI JSON schema/linter checks.
- Test `/health/live` returns `200` even when a downstream dependency is unreachable, while `/health/ready` flips cleanly to `503` within `< 2s`.

## 10. Operational Considerations
- Always overlay CI/CD deployment annotations (`git sha`, release tag) on RED latency/error panels so release-correlated regressions jump off the screen immediately.
- Alert on `probe_ssl_earliest_cert_expiry < 14 days` (warning) and `< 5 days` (critical page) as a true capacity/expiry cliff.

## 11. Authoritative References
- Brendan Gregg — *The USE Method (Utilization, Saturation, Errors)* (brendangregg.com/usemethod.html).
- Tom Wilkie — *The RED Method for Microservices Monitoring*.
- Kubernetes Documentation — *Configure Liveness, Readiness and Startup Probes*.

## 12. Limitations & When NOT to Use
- Do NOT run heavy synthetic browser/load tests every 10 seconds against production endpoints (causes synthetic self-DDoS and pollutes product analytics — filter synthetic bots out of `/shadow-analytics` and keep stress testing inside `/shadow-perf` Pre-UAT gates).
- Do NOT expose internal dependency hostnames, connection strings, or stack traces on public unauthenticated `/health/ready` endpoints; restrict detailed JSON dependency output to internal/authenticated networks.
