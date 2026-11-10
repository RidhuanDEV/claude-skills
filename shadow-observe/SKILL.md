---
name: shadow-observe
description: Actionable Production Observability & SRE: SLI/SLO definitions, Multi-Window Error Budget Burn Alerts, Distributed Tracing (OpenTelemetry), Structured Log Correlation, Dashboard Health, and Alert-to-Runbook Escalation. Pairs with /shadow-ops. Trigger with /shadow-observe.
---

# Shadow Observe (`/shadow-observe`) — SLI/SLO, Error Budgets, Tracing & Actionable Alerting

While `/shadow-ops` provisions the monitoring stack (Prometheus, Loki, Grafana), **`/shadow-observe`** governs **what to measure, when to page a human, and how to turn telemetry into fast root-cause diagnosis**.

---

## 1. Defining Measurable SLIs, SLOs & Error Budgets

Every production service must define explicit **Service Level Indicators (SLIs)** and **Service Level Objectives (SLOs)**:

| SLI Category | Metric Formula | Standard SLO Target (28-Day Window) | Allowed Error Budget (28 Days) |
| :--- | :--- | :--- | :--- |
| **Availability** | $\frac{\text{Total Valid Requests} - \text{5xx Responses}}{\text{Total Valid Requests}}$ | `99.9%` | `40.3 minutes` downtime / `0.1%` failed requests |
| **Latency (Interactive API)** | Proportion of requests with duration $\le 400\text{ms}$ (`p95`) and $\le 900\text{ms}$ (`p99`) | `95% < 400ms`, `99% < 900ms` | `5%` slow requests |
| **Async / Queue Freshness** | Proportion of background jobs / ETL watermarks processed within `< 5 minutes` | `99.5% < 5m` | `0.5%` delayed jobs |

---

## 2. Actionable Alerting & Escalation Rules (Zero Alert Fatigue)

1. **Every Paging Alert Must Link to a Runbook Action**:
   - Never create an alert that has no clear mitigation step. Every alert annotation must include `runbook_url` or exact triage commands (`docker compose logs`, `SELECT * FROM pg_stat_activity`, rollback command).
2. **Multi-Window Burn Rate Alerting**:
   - **Critical Page (P1 — Immediate Action)**: Fast burn where `> 2%` of the 28-day error budget is consumed in `1 hour` (and still burning over the last `5 minutes`).
   - **Warning Ticket (P2 — Next Business Hours)**: Slow burn where `> 5%` of the error budget is consumed in `6 hours`.
3. **Symptom-First, Cause-Second**:
   - Page on **user-visible symptoms** (5xx spike, latency breach, queue stall, disk `< 15%` free, TLS cert expiring `< 14 days`), not noisy transient CPU spikes.

---

## 3. End-to-End Trace & Log Correlation (`requestId` / `traceId`)

Ensure a single `X-Request-Id` / W3C `traceparent` flows unbroken across:
1. **Frontend UI Error Boundary / Toast** -> displays `Ref ID: req_01H...` so a client reporting a bug on WhatsApp/Email gives the exact lookup key.
2. **Nginx / Reverse Proxy Access Log** -> logs `$http_x_request_id`.
3. **Backend Structured JSON Log** -> every log line includes `"requestId": "req_01H..."`, `"userId"`, `"tenantId"`, `"route"`, `"durationMs"`.
4. **Database / Queue Worker** -> passes `requestId` in job metadata and SQL comments (`/* req_id=req_01H... */`) for slow-query tracing.
