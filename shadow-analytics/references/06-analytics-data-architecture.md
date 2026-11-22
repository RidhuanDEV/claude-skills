# 06. Analytics Data Architecture

## 1. Purpose & Activation Conditions
Design scalable, auditable event-to-warehouse pipelines (Raw -> Staging Dedup -> Core Activity/Dimensional Marts), reconcile dual client+server streams, and handle late-arriving mobile events safely. Load when building dbt/SQL event pipelines, reconciling PostHog/GA4 with Postgres/BigQuery/ClickHouse, or modeling warehouse tables for funnels and experiments.

## 2. Prerequisites
- Versioned event contracts (`02-event-taxonomy-and-tracking-plans.md`), identity stitching (`03-identity-resolution.md`), and hybrid instrumentation (`05-analytics-instrumentation.md`).

## 3. Technical Principles & Constraints
- **Immutable Layered Architecture (Medallion / dbt Standard):**
  1. **Raw / Bronze (`raw_events`):** Append-only, partitioned by `ingested_date` (UTC), NEVER mutated in place. Preserves full raw JSON payload, `event_id`, `client_ts`, and `server_received_ts`.
  2. **Staging / Silver (`stg_events`):** Deduplicated strictly by `event_id` (earliest `server_received_ts` wins), bot/QA-filtered, clock-skew corrected, and typed into explicit columns.
  3. **Core / Gold (`fct_user_events`, `fct_sessions`, `fct_orders`, `fct_experiment_assignments`, `fct_experiment_exposures`):** Identity-resolved, business-logic-aligned marts that power BI dashboards and experiment analyses.
- **Clock Skew & Late-Arriving Events:** Mobile clients frequently have drifted local clocks (minutes or hours off) or stay offline on flights/subways before flushing queued events 24–72 hours later. Store BOTH `client_ts` (when user acted) and `server_received_ts` (authoritative ingestion timestamp), clamp impossible future timestamps (`client_ts > server_received_ts + 5m` -> clamp to `server_received_ts`), and run incremental dbt models with a **3-day lookback merge window** (plus weekly late-arrival backfill if mobile offline queues exceed 72h).
- **Dual-Stream Reconciliation:** When both client (`web`) and server (`backend`) emit events for the same workflow, separate analytical ownership clearly: server owns financial/order marts (`fct_orders`), while shared `event_id` or `order_id` reconciles client funnel completion against backend truth.

## 4. Architecture & Implementation
```sql
-- Incremental Silver deduplication + clock-skew clamping + 3-day late-arrival window (Postgres / BigQuery ANSI style)
WITH bounded_raw AS (
  SELECT
    event_id,
    event_name,
    schema_version,
    source,
    anonymous_id,
    user_id,
    CASE
      WHEN client_ts > server_received_ts + INTERVAL '5 minutes' THEN server_received_ts
      WHEN client_ts < server_received_ts - INTERVAL '30 days' THEN server_received_ts
      ELSE client_ts
    END AS event_ts,
    server_received_ts,
    properties,
    ROW_NUMBER() OVER (
      PARTITION BY event_id
      ORDER BY
        CASE WHEN source = 'server' THEN 0 ELSE 1 END, -- Prefer authoritative server payload if dual-emitted
        server_received_ts ASC
    ) AS rn
  FROM raw_events
  WHERE ingested_date >= CURRENT_DATE - INTERVAL '3 days'
    AND COALESCE(is_bot, FALSE) = FALSE
    AND environment = 'production'
)
SELECT
  event_id,
  event_name,
  schema_version,
  source,
  anonymous_id,
  user_id,
  event_ts,
  server_received_ts,
  properties
FROM bounded_raw
WHERE rn = 1;
```

## 5. Platform / Vendor Variations
| Warehouse Engine | Partitioning / Clustering Best Practice | Dedup / Cost Trade-Off |
| --- | --- | --- |
| **BigQuery** | Partition by `DATE(server_received_ts)`, cluster by `(event_name, canonical_user_id)` | Avoid `SELECT *` on raw JSON; incremental `MERGE` with 3-day partition filter cuts scan cost 90%+ |
| **ClickHouse** | `ORDER BY (event_name, toDate(event_ts), canonical_user_id)` | `ReplacingMergeTree` deduplicates asynchronously on merge — ALWAYS use `FINAL` or `argMin`/window query for exact counts |
| **Snowflake** | Cluster large event tables by `(DATE(event_ts), event_name)` | Use dynamic tables / dbt incremental `merge` with `event_id` predicate pushdown |
| **PostgreSQL** | Declarative monthly/daily range partitioning on `event_ts` + BRIN/B-tree on `(event_name, event_ts)` | Suitable up to tens/hundreds of millions of rows; offload to ClickHouse/DuckDB/BigQuery before analytical scans contend with OLTP |

## 6. Decision Matrix & Trade-Offs
| Modeling Pattern | Query Simplicity | Schema Flexibility | Best Used For |
| --- | --- | --- | --- |
| **Activity Schema (Single `event_stream` Table)** | High for funnels/retention | Very high | Behavioral product analytics & self-serve cohorts |
| **Dimensional Star Schema (`fct_orders`, `dim_users`)** | Highest for Finance/BI | Medium | Revenue, subscriptions, unit economics, executive KPIs |
| **Hybrid (Activity Stream + Dimensional Facts)** | High across both teams | High | **Recommended** for scaling SaaS / e-commerce |

## 7. Real Production Scenario
A mobile fintech app runs an incremental midnight warehouse job that only reads `WHERE DATE(event_ts) = CURRENT_DATE - 1`. Commuters who complete actions offline at 23:50 and regain signal at 00:15 arrive on the next day's ingestion partition with yesterday's `event_ts`, so the midnight job permanently misses 6.4% of late-arriving mobile events. Switching partitioning to `ingested_date` with a 3-day incremental merge lookback recovers 99.8% of late events without full-table rebuilds.

## 8. Failure Modes & Edge Cases
- **WRONG:** Partitioning raw ingestion tables by untrusted `client_ts` (a single device with its system clock set to `2099-01-01` or `1970-01-01` creates garbage partitions or fails warehouse partition limits).
- **RIGHT:** Partition raw ingestion strictly by authoritative `server_received_ts` / `ingested_date`, and clamp anomalous `client_ts` in Silver staging.
- **WRONG:** Running heavy ad-hoc funnel/cohort SQL directly on the production OLTP PostgreSQL primary database.
- **RIGHT:** Replicate to a dedicated analytics warehouse (ClickHouse/BigQuery/Snowflake) or at minimum an isolated read replica with strict statement timeouts.

## 9. Testing & Verification
- Run dbt/SQL automated tests on `stg_events`: `unique(event_id)`, `not_null(event_id, event_name, event_ts)`, and a daily reconciliation test asserting `ABS(warehouse_orders - billing_ledger_orders) / billing_ledger_orders < 0.005`.
- Inject synthetic duplicate `event_id` rows (one client, one server) and a future-dated `client_ts` in staging; assert Silver outputs exactly 1 row with server precedence and clamped timestamp.

## 10. Operational Considerations
- Monitor warehouse scan bytes / query cost per model (`/shadow-finops`); unpartitioned JSON extraction on billion-row event tables is the #1 cloud analytics cost explosion.
- Document table SLAs (`stg_events` fresh within 15m; `fct_experiment_metrics` fresh daily by 06:00 UTC) so product teams know when numbers are final.

## 11. Authoritative References
- dbt Labs — *How We Structure Our dbt Projects* (`https://docs.getdbt.com/best-practices/how-we-structure/1-guide-overview`).
- ClickHouse Documentation — *ReplacingMergeTree & Deduplication Semantics* (`https://clickhouse.com/docs/en/engines/table-engines/mergetree-family/replacingmergetree`).
- Kimball Group — *Dimensional Modeling Techniques* (`https://www.kimballgroup.com/data-warehouse-business-intelligence-resources/`).

## 12. Limitations & When NOT to Use
- Do NOT spin up Kafka + Spark + Snowflake on Day 1 for an early-stage app with `< 100k` events/day; PostHog/Mixpanel + a clean Postgres read replica or DuckDB/BigQuery batch sync is orders of magnitude simpler and cheaper.
- Activity-stream tables alone should not replace ACID relational tables for transactional billing or inventory checks.
