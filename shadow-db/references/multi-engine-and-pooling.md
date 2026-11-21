# Multi-Engine Database Architecture, Connection Pooling & Tuning

## 1. Core Concepts
Database engineering spans **engine workload alignment (OLTP PostgreSQL/MySQL vs Time-Series TimescaleDB/ClickHouse vs Document MongoDB vs OLAP Star Schema)**, **connection-pool multiplexing (`PgBouncer`)**, **MVCC autovacuum tuning**, and **cross-engine precision preservation**.

## 2. Technical Rules & Engine Selection Matrix

| Workload Pattern | Choose Engine | Critical Production Invariant |
| :--- | :--- | :--- |
| **Core ACID / Financial / Multi-Tenant OLTP** | PostgreSQL (default) or MySQL 8 (InnoDB) | Store money as integer minor units or `NUMERIC(19,4)`/`DECIMAL(30,8)` (never `FLOAT`), timestamps as UTC `TIMESTAMPTZ`, index `(tenant_id, ...)`. |
| **High-Ingest Telemetry / Audit Events** | TimescaleDB (PG hypertables) or ClickHouse | Partition by time chunk; batch inserts (`>= 1,000` rows in ClickHouse); avoid single-row point `UPDATE`s on columnar tables. |
| **Polymorphic Catalogs / Dynamic Attributes** | PostgreSQL `JSONB` + `GIN` index (or MongoDB) | Include explicit `schema_version`, cap nested array sizes, and validate JSON shape at application boundary. |
| **Connection Multiplexing (Serverless / K8s)** | `PgBouncer` (`pool_mode = transaction`) | Size `default_pool_size` to fit DB CPU cores (`~2–4 * cores`); configure prepared-statement compatibility (`max_prepared_statements` or disable client unnamed statements). |

## 3. Implementation Examples
```sql
-- 1. Diagnostic Query: Detect Blocking Locks & Long-Running Idle-in-Transaction Sessions (PostgreSQL)
SELECT
  blocked.pid AS blocked_pid,
  blocked.usename AS blocked_user,
  blocking.pid AS blocking_pid,
  blocking.state AS blocking_state,
  NOW() - blocking.xact_start AS blocking_tx_age,
  LEFT(blocked.query, 120) AS blocked_query,
  LEFT(blocking.query, 120) AS blocking_query
FROM pg_catalog.pg_locks blocked_locks
JOIN pg_catalog.pg_stat_activity blocked ON blocked.pid = blocked_locks.pid
JOIN pg_catalog.pg_locks blocking_locks
  ON blocking_locks.locktype = blocked_locks.locktype
  AND blocking_locks.database IS NOT DISTINCT FROM blocked_locks.database
  AND blocking_locks.relation IS NOT DISTINCT FROM blocked_locks.relation
  AND blocking_locks.page IS NOT DISTINCT FROM blocked_locks.page
  AND blocking_locks.tuple IS NOT DISTINCT FROM blocked_locks.tuple
  AND blocking_locks.virtualxid IS NOT DISTINCT FROM blocked_locks.virtualxid
  AND blocking_locks.transactionid IS NOT DISTINCT FROM blocked_locks.transactionid
  AND blocking_locks.pid != blocked_locks.pid
JOIN pg_catalog.pg_stat_activity blocking ON blocking.pid = blocking_locks.pid
WHERE NOT blocked_locks.granted;

-- 2. Aggressive Autovacuum Tuning on High-Churn Outbox / Queue Table
ALTER TABLE outbox_events SET (
  autovacuum_vacuum_scale_factor = 0.01,
  autovacuum_vacuum_threshold = 500,
  autovacuum_vacuum_cost_limit = 2000
);
```

## 4. Best Practices
- Always run `EXPLAIN (ANALYZE, BUFFERS)` inside a rolled-back transaction (`BEGIN; EXPLAIN (ANALYZE, BUFFERS) ...; ROLLBACK;`) on non-prod/staging data to verify index usage and buffer hits vs disk reads.
- Set `idle_in_transaction_session_timeout = '15s'` and `statement_timeout = '10s'` on OLTP application roles so stuck transactions never hold locks indefinitely.

## 5. Anti-patterns (WRONG vs RIGHT)
- **WRONG:** Letting 20 Kubernetes pods each open a pool of 50 connections (`1,000` direct PostgreSQL connections -> memory exhaustion & context-switch collapse) or reading immediately from an async read-replica right after a write.
- **RIGHT:** Route app pods through `PgBouncer` transaction pooling (`total_app_pool <= 80%` of DB capacity) and pin read-after-write queries to the primary instance.
- **WRONG:** Narrowing `DECIMAL(30,8)` to `FLOAT` or `NUMERIC(18,2)` silently during cross-DB ETL.
- **RIGHT:** Preserve exact scale/precision, composite keys, and `NULL` vs empty-string distinctions across source and target engines.

## 6. Production Considerations
- Monitor transaction ID wraparound age (`age(datfrozenxid)`), dead-tuple ratio (`n_dead_tup / n_live_tup`), connection saturation, and replica replication lag (`pg_stat_replication`).
