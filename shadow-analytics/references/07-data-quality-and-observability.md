# 07. Data Quality & Observability

## 1. Purpose & Activation Conditions
Prevent silent data corruption (broken event payloads, dropped SDK traffic, stale pipelines, schema drift) through ingestion validation, quarantine/DLQ routing, freshness & volume anomaly alerts, and CI tracking-plan gates. Load when hardening analytics reliability, investigating sudden metric drops/spikes, or setting up data observability monitors.

## 2. Prerequisites
- Typed event contracts (`02-event-taxonomy-and-tracking-plans.md`) and layered warehouse tables (`06-analytics-data-architecture.md`).

## 3. Technical Principles & Constraints
- **Five Pillars of Analytics Data Quality:**
  1. **Schema Validity:** Exact property names, types, enum values, and required fields match `schema_version`.
  2. **Completeness:** Event counts reconcile with backend source-of-truth counts (e.g., `Order_Completed` vs `orders` table `< 0.5%` drift).
  3. **Freshness:** Time since latest ingested/modeled event stays within defined SLA (`< 15 min` streaming, `< 2h` hourly batch).
  4. **Uniqueness:** Duplicate `event_id` rate monitored before and after Silver dedup (sudden spike indicates client retry loop bug).
  5. **Distribution Stability:** Null rates, enum cardinality, and key numeric ranges (`price_minor > 0`) stay within historical control bounds.
- **Quarantine / DLQ Over Silent Drop or Cast-to-Zero:** When an event fails schema validation at ingestion, NEVER silently swallow it and NEVER cast `"Rp 50.000"` to `0` (which silently corrupts average revenue!). Route invalid events into `raw_events_quarantine` with `validation_error`, `producer_version`, and `ingested_at`, and page the owning team if quarantine rate exceeds `0.5%`.
- **Shift-Left CI Contract Enforcement:** Catch broken event names, missing required fields, and PII leaks in Pull Requests BEFORE mobile/web builds ship (mobile releases take weeks to age out).

## 4. Architecture & Implementation
```typescript
export interface ValidationIssue {
  readonly field: string;
  readonly reason: string;
}

export interface IngestDecision {
  readonly route: 'valid_stream' | 'quarantine_dlq';
  readonly issues: readonly ValidationIssue[];
}

const FORBIDDEN_PII_KEYS = new Set(['email', 'phone', 'nik', 'npwp', 'password', 'token']);

export function validateOrderCompletedPayload(raw: unknown): IngestDecision {
  const issues: ValidationIssue[] = [];
  if (typeof raw !== 'object' || raw === null) {
    return { route: 'quarantine_dlq', issues: [{ field: 'root', reason: 'Payload must be an object' }] };
  }
  const obj = Object.entries(raw);
  const map = new Map<string, unknown>(obj);

  for (const key of map.keys()) {
    if (FORBIDDEN_PII_KEYS.has(key.toLowerCase())) {
      issues.push({ field: key, reason: 'Raw PII key forbidden in analytics payload' });
    }
  }
  const orderId = map.get('order_id');
  if (typeof orderId !== 'string' || orderId.trim().length === 0) {
    issues.push({ field: 'order_id', reason: 'Required non-empty string' });
  }
  const subtotal = map.get('subtotal_minor');
  if (typeof subtotal !== 'number' || !Number.isFinite(subtotal) || subtotal < 0) {
    issues.push({ field: 'subtotal_minor', reason: 'Must be a non-negative finite integer/number (never formatted string)' });
  }
  return issues.length === 0
    ? { route: 'valid_stream', issues: [] }
    : { route: 'quarantine_dlq', issues };
}
```
Warehouse freshness, null-rate & volume anomaly check SQL:
```sql
-- Daily critical event health & schema drift monitor
WITH hourly AS (
  SELECT
    event_name,
    date_trunc('hour', server_received_ts) AS hr,
    COUNT(*) AS cnt,
    AVG(CASE WHEN properties->>'subtotal_minor' IS NULL THEN 1.0 ELSE 0.0 END) AS subtotal_null_rate
  FROM stg_events
  WHERE server_received_ts >= NOW() - INTERVAL '8 days'
    AND event_name IN ('Checkout_Started', 'Order_Completed', 'Experiment_Assigned')
  GROUP BY 1, 2
),
baseline AS (
  SELECT
    event_name,
    EXTRACT(HOUR FROM hr) AS hour_of_day,
    AVG(cnt) AS mean_cnt,
    STDDEV_POP(cnt) AS std_cnt
  FROM hourly
  WHERE hr < date_trunc('hour', NOW()) - INTERVAL '1 hour'
  GROUP BY 1, 2
)
SELECT
  h.event_name,
  h.hr,
  h.cnt,
  ROUND(b.mean_cnt::numeric, 1) AS expected_cnt,
  ROUND(((h.cnt - b.mean_cnt) / NULLIF(b.std_cnt, 0))::numeric, 2) AS z_score,
  ROUND(h.subtotal_null_rate::numeric, 4) AS subtotal_null_rate
FROM hourly h
JOIN baseline b
  ON h.event_name = b.event_name
 AND EXTRACT(HOUR FROM h.hr) = b.hour_of_day
WHERE h.hr = date_trunc('hour', NOW()) - INTERVAL '1 hour';
```

## 5. Platform / Vendor Variations
| Tooling | Strength | Best Fit |
| --- | --- | --- |
| **dbt Tests + Elementary / Soda** | Declarative SQL tests (`unique`, `not_null`, `accepted_values`, volume/freshness anomalies) in git | Warehouse-first teams |
| **Snowplow Iglu / Segment Protocols** | Edge schema enforcement & automatic bad-rows quarantine bucket | High-volume multi-platform product teams |
| **Monte Carlo / Bigeye / Metaplane** | Automated ML anomaly detection + downstream BI lineage | Mature multi-domain data orgs |
| **Custom CI Script (`analytics_experiment_verifier.py`)** | Zero-cost deterministic contract + PII + SRM gate in GitHub Actions | Every codebase from Day 1 |

## 6. Decision Matrix & Trade-Offs (Alert Severity)
| Condition | Severity | Automated Action |
| --- | --- | --- |
| **Raw PII key detected in production event** | CRITICAL (Page) | Strip/quarantine at edge, rotate/purge leaked vendor rows, fix producer |
| **`Order_Completed` warehouse vs ledger drift `> 1%`** | CRITICAL (Page) | Halt revenue reporting / active revenue A/B decisions; inspect ingest & outbox |
| **Quarantine rate `> 1%` for a critical event** | HIGH (Alert Slack/Pager) | Identify `app_version` / commit causing drift; backfill from quarantine once fixed |
| **Non-critical UI event volume drop `> 30%` vs same-hour 7d baseline** | MEDIUM (Alert Slack) | Check recent frontend release for removed/renamed tracking call |

## 7. Real Production Scenario
An Android release formats `subtotal_minor` using `NumberFormat.getCurrencyInstance()` (`"Rp 50.000"`) instead of integer `50000`. Without schema validation, the warehouse ETL runs `TRY_CAST(subtotal_minor AS NUMERIC)` -> `NULL`, silently dropping Android revenue to \$0 for 5 days until an executive spots the chart. With edge contract validation (`validateOrderCompletedPayload`) + quarantine alert on `quarantine_rate > 0.5%` + CI contract tests, the malformed type is caught in PR CI — and even if bypassed, alerts within 15 minutes while preserving every raw payload in `raw_events_quarantine` for lossless replay.

## 8. Failure Modes & Edge Cases
- **WRONG:** Using `COALESCE(TRY_CAST(price AS NUMERIC), 0)` to "keep the pipeline green" (silently turns broken numbers into valid-looking zeros and wrecks averages).
- **RIGHT:** Route type mismatches to `raw_events_quarantine` with exact error reason and alert on quarantine volume.
- **WRONG:** Setting static alert thresholds (`cnt < 1000/hr`) that page every night at 03:00 WIB due to normal diurnal traffic troughs.
- **RIGHT:** Compare against same-hour-of-day and same-day-of-week rolling baselines (`z_score` or seasonal IQR bounds).

## 9. Testing & Verification
- Add CI tracking-plan contract tests running `python shadow-analytics/scripts/analytics_experiment_verifier.py --check-event` on golden fixtures emitted by your actual frontend/backend event builders.
- Chaos-test the quarantine pipeline in staging by sending 1 malformed event (string price) and 1 PII-tainted event; assert both land in `raw_events_quarantine` (NOT `stg_events`) and trigger the alert metric.

## 10. Operational Considerations
- Always attach `app_version` / `git_sha` and `platform` (`web`/`ios`/`android`/`server`) to every event envelope so when a schema-drift alert fires, you pinpoint the exact offending release in seconds.
- Keep quarantine replay scripts idempotent (preserving original `event_id` and `server_received_ts`) so repaired events merge cleanly without double counting.

## 11. Authoritative References
- dbt Labs — *Data Tests & Source Freshness* (`https://docs.getdbt.com/docs/build/data-tests`).
- Snowplow — *Failed Events & Recovery Architecture* (`https://docs.snowplow.io/docs/pipeline-components-and-applications/failed-events/`).
- Google SRE / Data Observability Principles — *Freshness, Completeness & Lineage*.

## 12. Limitations & When NOT to Use
- Alerting on every single low-volume exploratory button click produces severe alert fatigue; reserve paging alerts for Tier-1 KPIs, revenue events, experiment assignment/exposure streams, and PII-leak detectors.
- Automated anomaly detection cannot detect a bug that existed since Day 1 (stable baseline is already wrong); always pair anomaly monitors with cross-system reconciliation against backend operational tables.
