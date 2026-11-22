# 05. Connection Pooling, Partitioning, Autovacuum & Replicas

## 1. Purpose & Activation Conditions
Scale relational databases cleanly under Kubernetes/serverless concurrency and high-write growth — covering **multi-engine selection**, **`PgBouncer` transaction pooling**, **MVCC autovacuum tuning**, **declarative partitioning**, and **read-replica lag discipline**. Load when diagnosing `too many clients`, table bloat, replication lag, or choosing between database engines.

## 2. Prerequisites
- Baseline query plans (`03`), connection metrics (`pg_stat_activity`), and workload read/write profile.

## 3. Technical Principles & Constraints
- **Connection Multiplexing (`PgBouncer` Transaction Mode):** Every direct PostgreSQL backend process consumes ~5–10 MB RAM + CPU context switches. Letting 25 Kubernetes pods open 40 connections each (`1,000` connections) collapses throughput! Route pods through **`PgBouncer` (`pool_mode = transaction`)** sizing `default_pool_size` near `2–4 × DB CPU cores` (`total_app_pool <= 80%` of `max_connections`). Beware session-scoped features in transaction mode: use `SET LOCAL` (never `SET`), avoid session advisory locks, and verify prepared-statement support (`PgBouncer >= 1.21` `max_prepared_statements`).
- **MVCC Autovacuum & Bloat Control:** Every `UPDATE`/`DELETE` in Postgres creates dead tuples. Default `autovacuum_vacuum_scale_factor = 0.20` waits until **20%** of a 50M-row table (`10M` dead rows!) is dead before vacuuming — causing severe bloat and slow index scans! Override per-table autovacuum thresholds (`scale_factor = 0.01`, `threshold = 500`) on high-churn queues, outbox, and session tables, and monitor transaction-ID wraparound age (`age(datfrozenxid)`).
- **Declarative Range Partitioning:** Partition append-only high-growth tables (`audit_logs`, `event_stream`, `outbox_archive` exceeding `50–100M` rows) monthly via `PARTITION BY RANGE (created_at)` so retention pruning is an instant metadata `DROP TABLE partition_2025_01` instead of a bloated multi-hour `DELETE`!
- **Read-Replica Lag & Read-Your-Own-Writes Invariant:** Async streaming replicas lag behind the primary by milliseconds to seconds during heavy writes/backfills. **NEVER read immediately from an async replica right after a user write** (e.g., checkout redirect reading the order just created -> spurious `404`!). Route transactional writes and read-after-write flows to the primary; route reporting, exports, and analytics dashboards to replicas.

## 4. Architecture & Implementation
```sql
-- 1. Aggressive Per-Table Autovacuum Tuning on High-Churn Outbox / Queue Table
ALTER TABLE outbox_events SET (
  autovacuum_vacuum_scale_factor = 0.01,
  autovacuum_vacuum_threshold = 500,
  autovacuum_vacuum_cost_limit = 2000
);

-- 2. Monthly Declarative Range Partitioning for High-Volume Immutable Logs
CREATE TABLE audit_events (
  id          UUID NOT NULL,
  tenant_id   UUID NOT NULL,
  action      TEXT NOT NULL,
  created_at  TIMESTAMPTZ NOT NULL,
  PRIMARY KEY (created_at, id)
) PARTITION BY RANGE (created_at);

CREATE TABLE audit_events_2026_11 PARTITION OF audit_events
  FOR VALUES FROM ('2026-11-01 00:00:00+00') TO ('2026-12-01 00:00:00+00');

-- 3. Read-Only Bloat, Wraparound & Replication Lag Health Check
SELECT
  relname,
  n_live_tup,
  n_dead_tup,
  ROUND(100.0 * n_dead_tup / NULLIF(n_live_tup + n_dead_tup, 0), 2) AS dead_pct,
  last_autovacuum
FROM pg_stat_user_tables
WHERE n_dead_tup > 10000
ORDER BY n_dead_tup DESC
LIMIT 20;
```

## 5. Platform / Vendor Variations (Multi-Engine Workload Selection)
| Workload Pattern | Choose Engine | Critical Production Invariant |
| :--- | :--- | :--- |
| **Core ACID / Multi-Tenant OLTP** | **PostgreSQL** (default) or **MySQL 8 (InnoDB)** | `BIGINT`/`NUMERIC` money, UTC `TIMESTAMPTZ`, `PgBouncer`/ProxySQL pooling |
| **High-Ingest Time-Series / Analytics** | **TimescaleDB** (PG hypertables) or **ClickHouse** | Batch inserts (`>= 1,000` rows in ClickHouse); avoid point `UPDATE`s on columnar tables |
| **Polymorphic Document Store** | **PostgreSQL `JSONB` + GIN** (or **MongoDB**) | Explicit `schema_version`, bounded array sizes, schema validation at boundary |
| **Edge / Local Embedded Single-Writer** | **SQLite (`WAL` mode + `busy_timeout`)** | Great for single-node local tools; migrate to Postgres before multi-node concurrent writes |

## 6. Decision Matrix & Trade-Offs (PgBouncer Pool Modes)
| Pool Mode | Multiplexing Ratio | Prepared Statements / `SET` | Recommended For |
| :--- | :---: | :--- | :--- |
| **`transaction` (Default)** | **Very High (10x–50x)** | Use `SET LOCAL` + `PgBouncer >= 1.21` prepared-stmt support | Serverless, K8s web/API pods |
| **`session`** | Low (1:1 per client) | Full session state (`LISTEN`/`NOTIFY`, temp tables) | Dedicated workers needing `LISTEN`/`NOTIFY` |

## 7. Real Production Scenario
During a flash sale, 30 autoscaled Node.js pods each initialize a Prisma pool of 35 connections (`1,050` connections), hitting Postgres `max_connections = 500` and crashing checkout with `FATAL: sorry, too many clients already`. Putting `PgBouncer` in `transaction` mode (`default_pool_size = 60` on a 16-vCPU primary) + capping per-pod pools to `10` + pinning post-checkout reads to primary drops DB CPU from `98%` to `34%` and eliminates connection errors completely.

## 8. Failure Modes & Edge Cases
- **WRONG:** Fixing `too many clients` by raising Postgres `max_connections = 3000` (causes RAM exhaustion and severe lock/snapshot contention!).
- **RIGHT:** Keep Postgres `max_connections` modest (`100–300`) and multiplex high client concurrency through `PgBouncer` (`transaction` mode).
- **WRONG:** Forgetting to pre-create next month's partition (or lacking a `DEFAULT` partition / `pg_partman` automation), causing inserts to crash at `00:00:00` on the 1st of the month!
- **RIGHT:** Automate partition creation (`pg_partman` or scheduled cron creating 3 months ahead + monitoring alert if `< 2` future partitions exist).

## 9. Testing & Verification
- Verify app queries under a local `PgBouncer` `transaction`-mode container in staging (confirms zero accidental session-level `SET` leaks or incompatible unnamed prepared statements).
- Verify read-after-write flows route strictly to primary even when a read replica has simulated `500ms` lag.

## 10. Operational Considerations
- Monitor 4 vital DB health metrics continuously (`/shadow-observe`): (1) active vs waiting connections, (2) `dead_pct` & autovacuum lag, (3) `age(datfrozenxid)` (`alert > 1.2B`), and (4) `pg_stat_replication` byte/time lag.

## 11. Authoritative References
- PostgreSQL Documentation — *5.11 Table Partitioning* & *25.1 Routine Vacuuming* (`https://www.postgresql.org/docs/current/ddl-partitioning.html`).
- PgBouncer Documentation — *Pooling Modes & Prepared Statements* (`https://www.pgbouncer.org/features.html`).

## 12. Limitations & When NOT to Use
- Do NOT partition tables under `10–20 GB` (`< 20M` rows) unless driven by fast retention drops — premature partitioning adds query-planning overhead and requires including the partition key in every unique constraint!
