---
name: shadow-observe
description: "Use when instrumenting SLI/SLO, burn-rate alerts, OpenTelemetry traces, logs, or metric cardinality. Not for load testing (/shadow-perf)."
---

# Shadow Observe (`/shadow-observe`) — Production Observability, SLOs, Tracing & Telemetry Hygiene

While `/shadow-ops` provisions the monitoring infrastructure (Prometheus, Loki, Tempo, Grafana), **`/shadow-observe`** governs **what to measure, when to page a human, how to prevent cardinality and PII leaks, and how to turn telemetry into fast root-cause handoffs**.

- **Owner:** SLIs/SLOs & error budgets, multi-window burn-rate alerts, W3C `traceparent` / OpenTelemetry tracing, structured JSON wide-event logging & redaction, cardinality/sampling cost controls, RED/USE dashboards-as-code, synthetic probes, and incident timeline packets.
- **Boundaries:** Infrastructure provisioning (`shadow-ops`), causal bug root-cause debugging (`shadow-debug`), post-prod SLA/postmortems (`shadow-maintain`), Pre-UAT load testing (`shadow-perf`), cloud/LLM cost allocation (`shadow-finops`), and product funnels (`shadow-analytics`).

## Reference Guide

Load ONLY the 1–2 modular playbooks needed for the active observability subtask:

| Module | Topic | Load When |
| :--- | :--- | :--- |
| [01-sli-slo-and-error-budgets.md](references/01-sli-slo-and-error-budgets.md) | User-centric SLIs, 28d SLOs, multi-window burn-rate alerts, error-budget policy | Defining SLOs, replacing noisy CPU alerts, writing Prometheus burn-rate rules |
| [02-opentelemetry-tracing-and-semantic-conventions.md](references/02-opentelemetry-tracing-and-semantic-conventions.md) | W3C `traceparent`, OTel auto/manual spans, queue span links, SQL commenter correlation | Wiring end-to-end distributed tracing across API, DB, and async workers |
| [03-structured-logging-and-pii-redaction.md](references/03-structured-logging-and-pii-redaction.md) | Canonical wide events, `pino`/`structlog`/`slog`/Monolog recipes, PII/Bearer redaction, anti-CRLF | Setting up backend JSON logs, removing `console.log`, fixing secret/NIK leaks |
| [04-cardinality-control-sampling-and-telemetry-cost.md](references/04-cardinality-control-sampling-and-telemetry-cost.md) | Prometheus cardinality limits, route normalization, OTel tail-based sampling, collector topology | Preventing TSDB OOM, designing tail sampling (`100%` 5xx/slow), cutting ingest cost |
| [05-profiling-dashboards-as-code-and-synthetics.md](references/05-profiling-dashboards-as-code-and-synthetics.md) | RED/USE 3-row dashboards-as-code, blackbox TLS/edge synthetics, `/health/live` vs `/ready`, profiling | Designing Grafana GitOps dashboards, external uptime probes, continuous profiling |
| [06-incident-timelines-and-debug-handoff.md](references/06-incident-timelines-and-debug-handoff.md) | 5-minute `L0` triage workflow, 4-dimension blast-radius triangulation, runbooks, `/shadow-debug` handoff | Triaging firing alerts or customer `Ref ID` incidents without destroying evidence |
| [evaluations.md](evaluations.md) | Graded specialist evaluation scenarios (`OBS-EVAL-01..08`) | Auditing SRE alerting, cardinality safety, PII redaction, and incident triage |

---

## 1. Core SLO & Actionable Alerting Invariants

| SLI Category | Metric Formula | Standard SLO Target (28-Day Window) | Allowed Error Budget (28 Days) |
| :--- | :--- | :--- | :--- |
| **Availability** | $\frac{\text{Total Valid Requests} - \text{5xx Responses}}{\text{Total Valid Requests}}$ (excluding `/health`) | `99.9%` | `40.3 minutes` downtime / `0.1%` failed requests |
| **Latency (Interactive API)** | Proportion of requests $\le 400\text{ms}$ (`p95`) and $\le 900\text{ms}$ (`p99`) | `95% < 400ms`, `99% < 900ms` | `5%` slow requests |
| **Async / Queue Freshness** | Proportion of background jobs / ETL watermarks processed `< 5 minutes` | `99.5% < 5m` | `0.5%` delayed jobs |

1. **Every Paging Alert Requires `runbook_url` / Triage Action:** Never page a human without an actionable mitigation path.
2. **Multi-Window Burn Rate Only:** Pair long + short confirmation windows (`1h & 5m` fast burn at `14.4x` for P1 page; `6h & 30m` at `6x` for P2).
3. **Symptom-First, Cause-Second:** Page on customer-visible symptoms (`5xx`, latency breach, queue stall) or hard capacity cliffs (disk `< 15%`, TLS `< 14d`), not transient CPU spikes.

---

## 2. Correlation, Cardinality & Redaction Non-Negotiables

1. **Unbroken Correlation Loop (`Ref ID` -> Trace -> Log -> SQL):** Echo `X-Request-Id` to frontend error UI (`Ref ID: req_01...`), log `$http_x_request_id` at Nginx, propagate W3C `traceparent` via `AsyncLocalStorage`/`contextvars`/`context.Context` into canonical wide events (`http.request.completed`), queue headers, and SQL comments.
2. **Strict Metric Cardinality Floor:** NEVER attach unbounded IDs (`user_id`, `request_id`, `trace_id`, `email`, raw UUID URLs) as Prometheus metric labels or Loki stream labels — keep them inside structured JSON logs, OTel spans, and trace exemplars.
3. **Fail-Closed Redaction & Audit Separation:** Strip `Authorization`, cookies, `password`, `token`, `secret`, `nik`, `otp`, and raw `\r\n` newlines before shipping telemetry. Keep immutable business/security audit trails in append-only database tables, separate from ephemeral operational logs.
4. **Tail-Based OTel Sampling:** Retain `100%` of `5xx`/error and slow (`> p95`) traces while sampling `5–10%` of healthy `2xx` traces and dropping `200 OK` `/health` noise.

---

## 3. Deterministic Telemetry Hygiene Verification

Validate metrics/alerts/sampling configs and captured JSON log samples deterministically before shipping:

```powershell
python shadow-observe/scripts/telemetry_hygiene_verifier.py --self-test
python shadow-observe/scripts/telemetry_hygiene_verifier.py --check-metrics-config path/to/alerts_and_metrics.json
python shadow-observe/scripts/telemetry_hygiene_verifier.py --check-log-sample path/to/wide_event.json
python -m unittest discover -s shadow-observe/tests -v
```
