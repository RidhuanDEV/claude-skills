# 01 — SLI, SLO & Multi-Window Error Budget Engineering

## 1. Purpose & Activation Conditions
Define user-meaningful **Service Level Indicators (SLIs)**, **Service Level Objectives (SLOs)**, **Error Budgets**, and **multi-window burn-rate alerts** that eliminate alert fatigue while catching real customer-impacting degradations fast. Activate when defining reliability targets for a new service, auditing noisy PagerDuty/Slack alerts, or implementing release freeze/error-budget governance.

## 2. Prerequisites
- Identified critical user journeys (e.g. login, checkout submit, invoice webhook ingestion, async settlement job).
- Access to bounded HTTP/worker metrics (request counters split by status class, latency histograms, queue lag/watermark timestamps).
- Explicit ownership agreement between Engineering and Product on what happens when the 28-day error budget reaches `0%`.

## 3. Technical Principles & Constraints
- **User-Centric SLIs Over Machine Metrics:** Measure success from the user's or caller's perspective (`good_events / valid_events`), not CPU percentage. Exclude synthetic health checks and client `4xx` validation errors from availability failure counts unless `429`/`401` indicates an auth/rate-limit outage.
- **Rolling 28-Day (or 30-Day) Window:** Rolling 28 days covers exactly 4 weekends/weekdays, preventing calendar-month boundary distortions.
- **Multi-Window, Multi-Burn-Rate Alerting (Google SRE Workbook):**
  - Every burn-rate alert MUST pair a **long window** (detects sustained budget consumption) with a **short confirmation window** (`1/12` of the long window) so the alert resolves quickly once the outage stops instead of paging for an extra 55 minutes.
- **Error Budget Policy:** Remaining budget `> 0%` allows normal feature deploys; depleted budget (`<= 0%`) shifts sprint priority to reliability, rollback hardening, and postmortem actions until the window recovers.

## 4. Architecture & Implementation

### Standard SLO & Multi-Window Burn-Rate Formulae
For a 28-day availability SLO of `99.9%` (allowed error budget `B = 1 - 0.999 = 0.001`, or `40.32` minutes):
- **Fast Burn (P1 Critical Page):** Consumes `2%` of the 28-day budget in `1h` -> burn rate `14.4x` (`error_ratio > 14.4 * 0.001 = 1.44%`) confirmed over `5m`.
- **Medium Burn (P1/P2 High Page):** Consumes `5%` of the 28-day budget in `6h` -> burn rate `6x` (`error_ratio > 6 * 0.001 = 0.6%`) confirmed over `30m`.
- **Slow Burn (P2 Ticket — Business Hours):** Consumes `10%` of the 28-day budget in `3d` -> burn rate `1x` (`error_ratio > 0.1%`) confirmed over `6h`.

```yaml
# Prometheus Recording & Multi-Window Burn-Rate Alert Rules (Versioned in Git)
groups:
  - name: checkout_slo_recording
    interval: 30s
    rules:
      - record: slo:checkout_http_error_ratio:5m
        expr: |
          sum(rate(http_server_requests_total{service="checkout",status_class="5xx"}[5m]))
          /
          clamp_min(sum(rate(http_server_requests_total{service="checkout",route_template!="/health"}[5m])), 1)
      - record: slo:checkout_http_error_ratio:1h
        expr: |
          sum(rate(http_server_requests_total{service="checkout",status_class="5xx"}[1h]))
          /
          clamp_min(sum(rate(http_server_requests_total{service="checkout",route_template!="/health"}[1h])), 1)
      - record: slo:checkout_http_error_ratio:30m
        expr: |
          sum(rate(http_server_requests_total{service="checkout",status_class="5xx"}[30m]))
          /
          clamp_min(sum(rate(http_server_requests_total{service="checkout",route_template!="/health"}[30m])), 1)
      - record: slo:checkout_http_error_ratio:6h
        expr: |
          sum(rate(http_server_requests_total{service="checkout",status_class="5xx"}[6h]))
          /
          clamp_min(sum(rate(http_server_requests_total{service="checkout",route_template!="/health"}[6h])), 1)

  - name: checkout_slo_alerts
    rules:
      - alert: CheckoutErrorBudgetFastBurn
        expr: |
          slo:checkout_http_error_ratio:1h > (14.4 * 0.001)
          and
          slo:checkout_http_error_ratio:5m > (14.4 * 0.001)
        labels:
          severity: critical
          service: checkout
        annotations:
          summary: "Checkout API fast error-budget burn (14.4x over 1h & 5m)"
          runbook_url: "https://runbooks.internal/checkout/fast-burn"
          triage_command: "kubectl logs -l app=checkout --since=10m | jq 'select(.statusCode >= 500)'"
```

```ts
// Strict TypeScript Burn-Rate & Remaining Error Budget Calculator (0 any, 0 casts)
export interface SloSpec {
  readonly sloTarget: number // e.g. 0.999
  readonly windowDays: number // e.g. 28
}

export interface ErrorBudgetSnapshot {
  readonly allowedErrorRatio: number
  readonly budgetMinutes: number
  readonly consumedFraction: number
  readonly remainingFraction: number
  readonly fastBurnThresholdRatio: number
}

export function computeErrorBudget(spec: SloSpec, observedErrorRatio: number): ErrorBudgetSnapshot {
  const allowedErrorRatio = Math.max(0, 1 - spec.sloTarget)
  const budgetMinutes = spec.windowDays * 24 * 60 * allowedErrorRatio
  const consumedFraction = allowedErrorRatio === 0 ? 1 : observedErrorRatio / allowedErrorRatio
  const remainingFraction = Math.max(0, 1 - consumedFraction)
  return {
    allowedErrorRatio,
    budgetMinutes: Number(budgetMinutes.toFixed(2)),
    consumedFraction: Number(consumedFraction.toFixed(4)),
    remainingFraction: Number(remainingFraction.toFixed(4)),
    fastBurnThresholdRatio: Number((allowedErrorRatio * 14.4).toFixed(6)),
  }
}
```

## 5. Platform/Vendor Variations
- **Prometheus / Grafana Alerting / VictoriaMetrics:** Use recording rules (`slo:*`) to pre-aggregate ratios across short (`5m`, `30m`) and long (`1h`, `6h`, `3d`) windows so alert evaluation remains sub-second and immune to raw histogram query timeouts.
- **Datadog / Honeycomb / Cloud Monitoring:** Native SLO burn-rate monitors implement the exact same multi-window formula; export them via Terraform/IaC so alerts cannot drift silently in the UI.
- **Low-Traffic Internal APIs (`< 5 req/min`):** A single 500 error in a 5-minute window can falsely trip a 14.4x ratio; add a minimum request volume guard (`and sum(increase(http_server_requests_total[5m])) >= 10`) or rely on synthetic probe availability SLIs.

## 6. Decision Matrix & Trade-Offs

| Journey Type | Primary SLI | Typical SLO Target | Alerting Strategy | Trade-Off |
| :--- | :--- | :--- | :--- | :--- |
| **Interactive Checkout / Auth API** | Good HTTP responses (`!5xx` and `<= 400ms`) / valid requests | `99.9%` availability, `p95 <= 400ms` | Multi-window burn rate (`1h/5m` P1, `6h/30m` P2) | Balances fast incident detection vs zero overnight noise |
| **Async Webhook / Queue Consumer** | Jobs processed within `< 5m` freshness / total enqueued | `99.5%` freshness, `0` unacknowledged DLQ silent drops | Queue age + DLQ growth alert (`> 0` poison msgs for 10m) | Avoids false alarms during bursty traffic if worker catches up |
| **Scheduled Nightly ETL / Billing** | Batch completion before SLA cutoff (`06:00 WIB`) & row completeness | `99%` on-time runs | Dead-man's switch (`absent()` / heartbeat miss) | Better than error-rate ratios when run count is 1/day |
| **Low-Traffic B2B Admin Portal** | Synthetic canary success + valid request availability | `99.5%` | Minimum volume guard + blackbox probe alert | Prevents 1 single glitch from waking on-call at 03:00 |

## 7. Real Production Scenario
A SaaS invoicing platform had 47 Prometheus alerts (`CPU > 75%`, `Heap > 70%`, `DB connections > 50%`) waking engineers 15 times per week while missing a silent `1.8%` payment-callback `502` spike that lasted 4 hours. Replacing machine-threshold pages with 3 journey SLOs (Checkout API `99.9%`, Webhook Freshness `99.5%`, PDF Worker `99.5%`) and multi-window burn-rate alerts cut pages from 15/week to 1.2/week and reduced mean time to detect (MTTD) real 5xx incidents from 4 hours to 4 minutes.

## 8. Failure Modes & Edge Cases
- **WRONG:** Setting `SLO = 100%` or paging immediately whenever `CPU > 80% for 2m`.
  **RIGHT:** Set realistic error budgets (`99.9%` = 40.3 min/28d) tied to customer pain, page on multi-window burn rate with a linked `runbook_url`, and keep CPU/RAM on diagnostic dashboards (except true capacity cliffs like disk `< 15%` free or TLS expiry `< 14d`).
- **WRONG:** Averaging `p95` across microservices or computing availability over all requests including `/health` probes (90% of traffic!).
  **RIGHT:** Exclude `/health` and `/metrics` from valid SLI denominators, compute latency SLIs from histogram bucket proportions (`le="0.4"`), and never average percentiles.
- **WRONG:** Alerting on a single `1h` window without a `5m` confirmation window (stays firing 55 minutes after the bug is fixed).
  **RIGHT:** Always combine `long_window` AND `short_window` (`1h & 5m`, `6h & 30m`).

## 9. Testing & Verification
- Run `python shadow-observe/scripts/telemetry_hygiene_verifier.py --check-metrics-config path/to/alerts.json` to catch missing `runbook_url`, single-window burn-rate alerts, and cause-only CPU pages.
- Run `promtool test rules` in CI with synthetic error-spike timelines to prove the fast-burn alert fires within 5 minutes and resolves within 5 minutes after recovery.

## 10. Operational Considerations
- Review error-budget consumption weekly during sprint planning; if budget drops below `20%`, prioritize root-cause stability tickets from `/shadow-maintain`.
- Keep alert annotations actionable: include `runbook_url`, exact service dashboard URL with pre-filled time window, and safe read-only triage commands.

## 11. Authoritative References
- Beyer, Murphy, Rensin, Kawahara & Thorne — *The Site Reliability Workbook* (Google SRE, Ch. 2 "Implementing SLOs" & Ch. 5 "Alerting on SLOs").
- Sloth / OpenSLO Specification (v1.0) — Declarative SLO & multi-window burn-rate generation.
- Prometheus Best Practices — Recording Rules & Alerting (`promtool test rules`).

## 12. Limitations & When NOT to Use
- Do NOT use `shadow-observe` to provision Terraform/Docker/Kubernetes infrastructure for Prometheus/Grafana stacks — route infra provisioning to `/shadow-ops`.
- Do NOT invent artificial `99.999%` SLOs when upstream dependencies (e.g., payment gateway or cloud DB) only guarantee `99.9%`.
