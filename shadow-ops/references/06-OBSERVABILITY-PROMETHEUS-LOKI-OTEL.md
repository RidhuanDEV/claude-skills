# 06 — Observability: Prometheus, Grafana, Loki, Alerting & OpenTelemetry

Pair with [`vendor/OWASP_Logging_Cheat_Sheet.md`](vendor/OWASP_Logging_Cheat_Sheet.md).

---

## 1. Golden Signals & Structured JSON Logging

Every production service must emit structured JSON logs to `stdout` with:
- `timestamp` (ISO-8601 UTC)
- `level` (`info`, `warn`, `error`)
- `service` & `env`
- `requestId` / `traceId`
- `method`, `route` (low-cardinality template `/api/v1/orders/:id`), `statusCode`, `durationMs`
- **NEVER** log raw passwords, JWT tokens, API keys, credit cards, or NIK/KTP numbers.

---

## 2. Ready-to-Use Prometheus Alert Rules (`prometheus-alerts.yml`)

Alert on **symptoms that impact users** (SLO availability, high latency, disk saturation, DB connection exhaustion):

```yaml
groups:
  - name: production_slo_alerts
    rules:
      - alert: HighHttp5xxErrorRate
        expr: |
          (
            sum by (service) (rate(http_requests_total{status=~"5.."}[5m]))
            /
            clamp_min(sum by (service) (rate(http_requests_total[5m])), 1)
          ) > 0.02
        for: 3m
        labels:
          severity: critical
        annotations:
          summary: "High 5xx error rate on {{ $labels.service }} (> 2%)"
          description: "5xx rate is {{ $value | humanizePercentage }} over the last 5 minutes."

      - alert: HighApiLatencyP95
        expr: |
          histogram_quantile(0.95, sum by (le, service) (rate(http_request_duration_seconds_bucket[5m]))) > 0.8
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "p95 latency > 800ms on {{ $labels.service }}"

      - alert: HostDiskSpaceExhaustionSoon
        expr: |
          (node_filesystem_avail_bytes{fstype!~"tmpfs|overlay"} / node_filesystem_size_bytes{fstype!~"tmpfs|overlay"}) < 0.15
        for: 5m
        labels:
          severity: critical
        annotations:
          summary: "Disk free space < 15% on {{ $labels.instance }} ({{ $labels.mountpoint }})"
```
