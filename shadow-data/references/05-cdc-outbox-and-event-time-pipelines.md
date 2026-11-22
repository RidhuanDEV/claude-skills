# 05. CDC, Transactional Outbox & Event-Time Pipelines

## 1. Purpose & Activation Conditions
Design reliable data movement pipelines between OLTP databases, downstream search indexes, analytics warehouses, and microservices — choosing accurately between **Transactional Outbox** vs **Log-Based CDC (Debezium)** while enforcing WAL disk safety, idempotent upserts, and late-arriving event-time handling. Load when synchronizing OLTP changes to search/warehouse or designing CDC/ETL pipelines.

## 2. Prerequisites
- Relational source schema (`shadow-db`), coordination with `/shadow-concurrency` (worker/retry/DLQ) and `/shadow-analytics` (warehouse modeling).

## 3. Technical Principles & Constraints
- **Transactional Outbox vs Log-Based CDC (Pick the Right Tool!):**
  - **Transactional Outbox (Default for Domain Events & Integrations):** Insert explicit versioned event contracts (`outbox_events`) inside the same ACID transaction as the domain mutation. Pros: decouples downstream consumers from internal DB table schemas, zero WAL slot disk risk, works on every relational DB.
  - **Log-Based CDC (`Debezium` / PostgreSQL Logical Replication):** Tails database WAL directly to replicate high-volume row changes into ClickHouse/BigQuery/Kafka with low source-query load. Cons: couples downstream to physical table schemas (unless paired with Debezium Outbox Event Router!) AND carries **WAL Disk-Full Risk**!
- **CRITICAL PostgreSQL Logical Replication Safety (`max_slot_wal_keep_size`):** If a Debezium/CDC consumer crashes on Friday night and stays down all weekend, an uncapped logical replication slot retains EVERY single WAL segment indefinitely until the primary DB disk hits **100% and crashes production**! ALWAYS configure `max_slot_wal_keep_size` (e.g., `20GB`–`50GB`), monitor slot lag bytes (`pg_replication_slots` + `pg_wal_lsn_diff`), and keep an automated snapshot re-bootstrap procedure ready!
- **Event-Time vs Processing-Time & Late Arrivals:** Distinguish when a domain event occurred (`event_ts` / `updated_at`) from when the pipeline ingested it (`ingested_at`). Drive incremental watermarks on a **monotonic ingestion/commit watermark** with an explicit **late-arrival merge window** and idempotent `UPSERT` (`ON CONFLICT (id) DO UPDATE WHERE EXCLUDED.version > target.version`) so out-of-order replays never overwrite newer state with stale data!
- **Data Lineage & Schema Contracts:** Attach `schema_version`, `source_service`, and `correlation_id` to every emitted record so warehouse/search pipelines detect breaking upstream column drops BEFORE ingestion fails!

## 4. Architecture & Implementation
```sql
-- 1. Idempotent Monotonic Upsert Preventing Out-of-Order Stale Event Overwrites (PostgreSQL)
INSERT INTO search_documents_projection (doc_id, tenant_id, title, body, source_version, updated_at)
VALUES ($1, $2, $3, $4, $5, $6)
ON CONFLICT (doc_id) DO UPDATE
SET title          = EXCLUDED.title,
    body           = EXCLUDED.body,
    source_version = EXCLUDED.source_version,
    updated_at     = EXCLUDED.updated_at
WHERE EXCLUDED.source_version > search_documents_projection.source_version;

-- 2. Read-Only PostgreSQL Logical Replication Slot WAL Lag Monitor (Alert Before Disk Full!)
SELECT
  slot_name,
  active,
  pg_size_pretty(pg_wal_lsn_diff(pg_current_wal_lsn(), restart_lsn)) AS retained_wal_size,
  wal_status
FROM pg_replication_slots
WHERE slot_type = 'logical';
```
Debezium / CDC PostgreSQL mandatory guard configuration (`postgresql.conf`):
```ini
wal_level = logical
max_slot_wal_keep_size = '32GB'   # Hard ceiling prevents crashed CDC consumer from filling primary disk!
```

## 5. Platform / Vendor Variations
| Pattern / Tool | Schema Coupling | Source DB Load | Operational Complexity |
| :--- | :---: | :---: | :---: |
| **Transactional Outbox + Relay Worker** | **Decoupled (Explicit Event DTO)** | Low–Medium | **Low (Recommended default)** |
| **Debezium Outbox Event Router (WAL CDC on `outbox_events`)** | **Decoupled** | Very Low | Medium–High (Kafka/Connect + WAL slot monitoring) |
| **Raw Table Debezium CDC -> Warehouse (ELT)** | Coupled to OLTP columns | Very Low | Medium (watch schema changes & `max_slot_wal_keep_size`) |

## 6. Decision Matrix & Trade-Offs
| Pipeline Requirement | Choose | Why |
| :--- | :--- | :--- |
| Trigger email, webhook, or cross-service domain event | **Transactional Outbox** | Explicit versioned contract + zero WAL slot hazard |
| Replicate 50 OLTP tables continuously into BigQuery/ClickHouse | **Managed / Debezium CDC** (`max_slot_wal_keep_size` set!) | Captures deletes & updates without heavy `SELECT *` polling |
| Nightly small BI table sync (`< 1M` rows) | **Keyset/Watermark Batch ELT** | Simplest, zero streaming infra to operate |

## 7. Real Production Scenario
A payments company enables a PostgreSQL logical replication slot for Debezium to stream transactions into BigQuery without configuring `max_slot_wal_keep_size`. When a network policy change blocks the Kafka Connect pod over a holiday weekend, the inactive slot pins `480 GB` of WAL segments, exhausting the primary SSD and halting production transactions on Sunday morning. Setting `max_slot_wal_keep_size = '32GB'`, alerting when `active = false` for `> 10m` or `retained_wal_size > 10 GB`, and documenting automated snapshot re-sync eliminates disk-exhaustion outages permanently.

## 8. Failure Modes & Edge Cases
- **WRONG:** Doing `ON CONFLICT (id) DO UPDATE SET ...` **without** a `WHERE EXCLUDED.source_version > target.source_version` monotonicity guard (an out-of-order delayed CDC/queue retry silently reverts a `PAID` order back to `PENDING`!).
- **RIGHT:** Guard every projection upsert with monotonic `source_version` (or `updated_at` + LSN tie-breaker).
- **WRONG:** Writing `updated_at`-based incremental polling without overlap buffer (`WHERE updated_at > last_max_updated_at` misses uncommitted concurrent transactions whose `updated_at` timestamp was assigned before commit!).
- **RIGHT:** Use a tiny overlap lookback window (e.g., `>= last_watermark - INTERVAL '2 minutes'`) paired with idempotent monotonic `UPSERT`, or use logical LSN / monotonic sequence IDs.

## 9. Testing & Verification
- Test out-of-order replay in integration tests: apply `version = 2` (`PAID`), then replay older `version = 1` (`PENDING`); assert projection remains `PAID` (`version = 2`) with zero regression!
- Verify `pg_replication_slots` monitor alerts in staging when a test slot is paused.

## 10. Operational Considerations
- Pair every long-running CDC/ELT sync with a daily automated **count + sum reconciliation check** against the source OLTP table so silent dropped partitions or schema-drift stops are caught within 24h.

## 11. Authoritative References
- Debezium Documentation — *PostgreSQL Connector & Outbox Event Router* (`https://debezium.io/documentation/reference/stable/transformations/outbox-event-router.html`).
- PostgreSQL Documentation — *`max_slot_wal_keep_size` & Logical Replication* (`https://www.postgresql.org/docs/current/runtime-config-replication.html`).

## 12. Limitations & When NOT to Use
- Do NOT deploy Kafka + Debezium just to move 5,000 rows/day from Postgres to a reporting table; a simple Postgres `outbox_events` worker or scheduled watermark batch job has a fraction of the failure modes.
