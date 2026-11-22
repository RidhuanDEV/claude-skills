# 03 — SQL Query Plan Analysis, Pool Contention & Database Bottlenecks

## 1. Purpose & Activation Conditions
Diagnose slow SQL queries, cardinality skew, disk sort spills, ORM N+1 amplification, and database connection-pool exhaustion safely using telemetry and query plans without causing production side effects or lock storms. Activate during Pre-UAT performance gates or explicit SQL profiling investigations.

## 2. Prerequisites
- One degraded query fingerprint, one healthy control, aligned UTC window, pool wait metrics (`active`, `idle`, `waiting`), and read-only (`L0`) access to `pg_stat_statements` / MySQL `performance_schema` or an isolated staging database clone.
- Redacted sample parameters (never expose real PII or tokens in shared plan dumps).

## 3. Technical Principles & Constraints
- **Static `EXPLAIN` BEFORE `EXPLAIN ANALYZE`:** In PostgreSQL, **`EXPLAIN ANALYZE` ACTUALLY EXECUTES THE STATEMENT!** Running `EXPLAIN ANALYZE DELETE ...` or `EXPLAIN ANALYZE UPDATE ...` mutates rows, fires triggers, advances sequences, and acquires row locks (and triggers/external side effects cannot always be undone even inside `BEGIN; ... ROLLBACK;`). Always inspect static `EXPLAIN` first, restrict `EXPLAIN (ANALYZE, BUFFERS)` to read-only `SELECT` statements on an approved role/target with `statement_timeout`, and never run `EXPLAIN ANALYZE` blindly on mutating queries in production.
- **Measure Buffers, Not Just Milliseconds:** Execution time fluctuates wildly between cold disk and warm OS page cache; inspect `shared hit` vs `shared read` buffer blocks (`BUFFERS`) and `rows removed by filter` to quantify true I/O work.
- **Pool Saturation While DB CPU Is Low (`< 30%`):** Almost NEVER fixed by blindly bumping `pool_max` from `20` to `200`! Low DB CPU + high pool wait means connections are **held idle-in-transaction**, blocked on **row/table locks**, leaking without `release()`, or waiting on slow external HTTP calls made *inside* an open DB transaction. Raising per-pod pools across 10 replicas (`10 * 100 = 1,000` connections) pushes thrashing directly into PostgreSQL.
- **Index Trade-Off Discipline:** Every new index accelerates reads at the expense of write amplification (extra WAL + B-tree maintenance + HOT update prevention). Compare actual selectivity, tenant skew, and write volume on a representative dataset before recommending an index, and coordinate DDL rollout with `/shadow-db` (`CREATE INDEX CONCURRENTLY`).

## 4. Architecture & Implementation

### Evidence-Driven SQL Bottleneck Diagnostic Matrix

| Observation | Plausible Explanations | Discriminating Evidence & Safe Decision |
| :--- | :--- | :--- |
| **Sequential scan (`Seq Scan` / MySQL `ALL`)** | Small table (`< 5k` rows), low-selectivity filter (`> 15–20%` rows), stale stats, or non-SARGable predicate (`LOWER(col) = ...`, `col + 1 = ...`) | Check `actual rows / total rows` and predicate SARGability. A Seq Scan is faster than 50,000 random heap lookups! Test candidate index on an isolated clone and check write amplification. |
| **Huge Estimated vs Actual Row Skew (`est=10, act=250,000`)** | Skewed multi-tenant distribution (1 whale tenant = 80% rows), correlated columns (`city` + `zip`), recent bulk load without `ANALYZE` | Inspect `pg_stats` MCV/histogram and multi-tenant fixtures (small vs whale tenant). Consider `CREATE STATISTICS` (extended stats) or `ALTER TABLE ... ALTER COLUMN ... SET STATISTICS 500` + `ANALYZE`. |
| **Sort spills to disk (`external merge Disk: 48MB`)** | Large working set, wide `SELECT *` projection, low `work_mem`, or missing composite index supporting `ORDER BY` | Shrink projection (avoid fetching `TEXT`/`JSONB` blobs into sort buffer) and add an index matching `(tenant_id, created_at DESC)`. Beware raising global `work_mem` recklessly under high concurrency (OOM risk!). |
| **Repeated inner-loop work / N+1** | Valid `Nested Loop` on small outer set (`5` rows) vs missing FK index vs application ORM sending 100 separate `SELECT`s | Compare SQL execution count per HTTP request (`dbQueryCount` in wide event) against plan `loops=N`. Fix ORM N+1 via `IN (...)` batching/DataLoader or explicit `JOIN` while bounding memory. |
| **Pool timeouts while DB CPU is low** | Row locks (`FOR UPDATE`), `idle in transaction`, external HTTP call inside TX, undersized pool, or leaked connections | Query `pg_stat_activity` (`state`, `wait_event_type`, `wait_event`, `now() - xact_start`) and `pg_locks`. Move external HTTP/email calls outside DB transactions and add `idle_in_transaction_session_timeout`. |
| **Slow export or deep pagination (`OFFSET 50000`)** | Repeated offset scanning & discarding rows, connection held during slow client download | Switch to **keyset/seek pagination** (`WHERE (created_at, id) < ($1, $2) ORDER BY created_at DESC, id DESC LIMIT 50`) or async background export job to object storage. |

```sql
-- Read-Only (L0) PostgreSQL Lock & Long-Transaction Diagnostic Query
SELECT
  pid,
  state,
  wait_event_type,
  wait_event,
  ROUND(EXTRACT(EPOCH FROM (now() - xact_start))::numeric, 2) AS xact_age_sec,
  ROUND(EXTRACT(EPOCH FROM (now() - query_start))::numeric, 2) AS query_age_sec,
  LEFT(query, 140) AS query_snippet
FROM pg_stat_activity
WHERE datname = current_database()
  AND state <> 'idle'
  AND pid <> pg_backend_pid()
ORDER BY xact_age_sec DESC NULLS LAST
LIMIT 20;

-- Safe Read-Only Plan Inspection on Approved Staging Copy (Bounded Timeout)
SET LOCAL statement_timeout = '3000ms';
EXPLAIN (ANALYZE, BUFFERS, FORMAT TEXT)
SELECT id, status, total_cents, created_at
FROM orders
WHERE tenant_id = 'tenant_whale_01'
  AND status = 'paid'
ORDER BY created_at DESC, id DESC
LIMIT 50;
```

## 5. Platform/Vendor Variations
- **PostgreSQL (14–17):** Always use `EXPLAIN (ANALYZE, BUFFERS)` for read-only SELECT verification; watch for `Heap Fetches` on `Index Only Scan` (high heap fetches indicate lagging autovacuum visibility map); put PgBouncer (`transaction` pooling mode) in front of stateless horizontally scaled apps (`shadow-db`).
- **MySQL 8.x / MariaDB:** Use `EXPLAIN FORMAT=TREE` and `EXPLAIN ANALYZE` (MySQL 8.0.18+); watch `Using filesort` + `Using temporary` and InnoDB `innodb_buffer_pool_size` hit ratio.
- **Prisma / TypeORM / SQLAlchemy / Eloquent:** ORMs routinely hide N+1 queries inside lazy getters and default to `SELECT *` including giant JSON/text columns that blow up sort buffers. Enable per-request query-count instrumentation (`dbQueryCount`) in integration tests to fail CI on N+1 regressions (`> 10` queries on a list endpoint).

## 6. Decision Matrix & Trade-Offs

| Candidate Fix | Read Speedup | Write / Storage Penalty | Rollback Safety | When to Choose |
| :--- | :--- | :--- | :--- | :--- |
| **Remove `SELECT *` / Narrow Projection** | Medium (avoids TOAST/disk sort) | **Zero** | Instant | Always first — free win |
| **Keyset Pagination (replacing `OFFSET`)** | High (constant O(log N)) | **Zero** | Medium (API cursor contract) | Lists `> 1,000` rows or infinite scroll |
| **Composite Covering Index (`INCLUDE`)** | Very High | Medium (write amp + disk) | Safe via `CONCURRENTLY` | Proven high-frequency read bottleneck on selective predicate |
| **Move External HTTP Out of DB TX** | Massive (unblocks pool!) | **Zero** | Safe | Any pool exhaustion where DB CPU `< 40%` |
| **Raise `pool_max` on App Pods** | Often Negative! | High DB RAM & context-switch | Instant | ONLY after verifying `sum(pods * pool_max)` fits PgBouncer/DB core budget |

## 7. Real Production Scenario
During Pre-UAT load testing at `80 RPS`, an order-approval endpoint hit `DB_POOL_ACQUIRE_TIMEOUT` after 45 seconds even though PostgreSQL CPU never crossed `14%`. Inspecting `pg_stat_activity` showed 40 connections stuck in `idle in transaction` for `2.5–4.0s` each: the controller opened a DB transaction, updated `orders.status`, then synchronously called an external PDF/WhatsApp notification webhook *before* `COMMIT`. Moving the external webhook to a Transactional Outbox worker (`shadow-concurrency`) dropped p95 latency from `4,100ms` to `38ms` and peaked pool usage at `6/40` connections.

## 8. Failure Modes & Edge Cases
- **WRONG:** Running `EXPLAIN ANALYZE DELETE FROM audit_logs WHERE created_at < now() - interval '90 days'` on production to "check if it uses an index."
  **RIGHT:** Run static `EXPLAIN` (no `ANALYZE`) first, and if timing a mutating query on an approved staging clone, wrap in an isolated transaction only after confirming zero irreversible side effects/triggers and bounded `statement_timeout`.
- **WRONG:** Testing query plans only against a small tenant (`100` rows) when production has a whale tenant (`4,000,000` rows).
  **RIGHT:** Always benchmark plans against **both small and whale tenant fixtures** to detect cardinality skew and plan flips.
- **WRONG:** Adding 6 single-column indexes on every filterable column instead of 1–2 well-ordered composite indexes matching equality-first, range/sort-last (`tenant_id, status, created_at DESC`).
  **RIGHT:** Design composite indexes aligned with query predicates and verify via `shadow-db/scripts/sql_migration_safety_verifier.py`.

## 9. Testing & Verification
- Add an automated N+1 query-count budget test in integration suites (e.g., assert `GET /api/v1/orders?limit=50` executes `<= 3` SQL statements regardless of whether 5 or 50 orders exist).
- Capture before/after `EXPLAIN (ANALYZE, BUFFERS)` outputs on an isolated representative staging copy showing `shared hit + read` block reduction, not just warm-cache ms.

## 10. Operational Considerations
- Configure `statement_timeout` (e.g., `5–10s` for interactive web roles) and `idle_in_transaction_session_timeout` (`15–30s`) at the database role level so one stuck request cannot hold locks and starve the pool indefinitely.
- Coordinate every new index or schema change through `/shadow-db` zero-downtime `CONCURRENTLY` migrations and monitor `pg_stat_user_indexes` to drop unused indexes.

## 11. Authoritative References
- PostgreSQL Official Documentation — *Using EXPLAIN (`ANALYZE`, `BUFFERS`) & Planner Statistics*.
- Markus Winand — *Use The Index, Luke!* (Composite index ordering, keyset pagination, write amplification).
- HikariCP Wiki — *About Pool Sizing* (`connections = (core_count * 2) + effective_spindle_count` principle).

## 12. Limitations & When NOT to Use
- Do NOT execute schema migrations, `CREATE INDEX`, or `VACUUM FULL` inside `shadow-perf` — hand reversible DDL plans to `/shadow-db` and `/shadow-data`.
- Do NOT run heavy `EXPLAIN ANALYZE` profiling queries on a live primary database during peak customer hours without explicit `L4` approval and read-replica / staging isolation.
