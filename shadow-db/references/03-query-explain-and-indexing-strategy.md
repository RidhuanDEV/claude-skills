# 03. Query EXPLAIN & Indexing Strategy

## 1. Purpose & Activation Conditions
Diagnose slow SQL queries scientifically using `EXPLAIN (ANALYZE, BUFFERS)` and design high-selectivity composite, partial, covering (`INCLUDE`), GIN, BRIN, and foreign-key indexes without write-amplification bloat. Load when tuning slow queries, reviewing indexes, or verifying migration query plans.

## 2. Prerequisites
- Representative data volume/statistics (`ANALYZE` up to date) — never tune indexes solely on a 10-row dev table where Postgres legitimately chooses `Seq Scan`!

## 3. Technical Principles & Constraints
- **Measure Before Indexing (`EXPLAIN (ANALYZE, BUFFERS)`):** Inspect four exact plan signals on every slow query (wrap writes inside `BEGIN; EXPLAIN (ANALYZE, BUFFERS) ...; ROLLBACK;` on non-prod!):
  1. **Estimated vs Actual Rows:** A 10x–1000x mismatch signals stale statistics (`ANALYZE`), correlated columns (`CREATE STATISTICS`), or non-SARGable predicates!
  2. **Shared Buffers (`hit` vs `read`):** High `Buffers: shared hit=50000` means massive unnecessary page scans even if cached in RAM!
  3. **Rows Removed by Filter:** `Index Scan` discarding 95% of fetched rows means the index is missing a selective column or wrong column order!
  4. **Disk Spills (`Sort Method: external merge Disk`):** Signals missing matching `ORDER BY` index or undersized `work_mem`.
- **Composite B-Tree Column Ordering Rule (`Equality -> Sort -> Range`):**
  - Place **equality (`=`)** predicates first (leading with `tenant_id` on multi-tenant tables, followed by highest-selectivity equality columns like `status`), then `ORDER BY` / range (`>`, `<`, `BETWEEN`) columns last!
  - Example: `WHERE tenant_id = $1 AND status = 'PAID' AND created_at >= $2 ORDER BY created_at DESC, id DESC` -> index `(tenant_id, status, created_at DESC, id DESC)`.
- **Preserve SARGability (Never Wrap Indexed Columns in Functions):** `WHERE LOWER(email) = $1` or `WHERE DATE(created_at) = '2026-11-22'` **disables** a plain B-tree index! Fix with range predicates (`created_at >= '2026-11-22T00:00:00Z' AND created_at < '2026-11-23T00:00:00Z'`) or an explicit **Expression Index** (`ON users (tenant_id, LOWER(email))`).
- **Right Index Type & Zero-Downtime Creation:**
  - Always create/drop indexes on live tables using **`CREATE INDEX CONCURRENTLY`** (outside a transaction block) so writes never block!
  - Use **Partial Indexes** (`WHERE status = 'PENDING'` or `WHERE deleted_at IS NULL`) to shrink index size 10x–100x on hot work queues.
  - Use **Covering Indexes (`INCLUDE (col1, col2)`)** to enable `Index Only Scan` without bloating B-tree inner branch nodes.
  - Use **`GIN`** for `JSONB`/full-text/arrays and **`BRIN`** for naturally append-only multi-billion-row time-series logs (`1000x` smaller than B-tree!).

## 4. Architecture & Implementation
```sql
-- 1. Zero-downtime partial covering index for hot pending-orders queue (PostgreSQL)
SET lock_timeout = '3s';
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_orders_tenant_pending_created
  ON orders (tenant_id, created_at DESC, id DESC)
  INCLUDE (total_minor, currency)
  WHERE status = 'PENDING' AND deleted_at IS NULL;

-- 2. Read-only audit: find unused & duplicate indexes causing write amplification
SELECT
  schemaname,
  relname AS table_name,
  indexrelname AS index_name,
  idx_scan,
  pg_size_pretty(pg_relation_size(indexrelid)) AS index_size
FROM pg_stat_user_indexes
WHERE idx_scan = 0
  AND indexrelname NOT LIKE '%_pkey'
ORDER BY pg_relation_size(indexrelid) DESC
LIMIT 25;
```

## 5. Platform / Vendor Variations
| Index Type | Best Workload | Pitfall / Overhead |
| :--- | :--- | :--- |
| **B-Tree Composite** | Multi-tenant equality + range + keyset pagination | Leftmost-prefix rule; too many indexes slow `INSERT`/`UPDATE` & block HOT updates! |
| **Partial B-Tree (`WHERE ...`)** | Queues (`status = 'PENDING'`), active rows (`deleted_at IS NULL`) | Query `WHERE` clause MUST syntactically imply the index predicate to match! |
| **GIN (`jsonb_path_ops` / `tsvector`)** | JSONB containment `@>`, full-text search, array overlap | Higher write maintenance cost; use `fastupdate` awareness |
| **BRIN** | Append-only immutable audit/telemetry tables (`> 50M` rows) | Useless if rows are heavily updated/scattered out of physical time order |

## 6. Decision Matrix & Trade-Offs
| Query Pattern | Bad Index | Optimal Index |
| :--- | :--- | :--- |
| `WHERE tenant_id = $1 AND created_at > $2` | `(created_at, tenant_id)` | **`(tenant_id, created_at DESC)`** |
| `WHERE LOWER(email) = $1` | `(email)` | **`(LOWER(email))`** (or `citext`) |
| `WHERE status = 'PENDING'` (0.5% of 10M rows) | Full `(status)` | **`(created_at) WHERE status = 'PENDING'`** |
| `WHERE title ILIKE '%invoice%'` | Plain B-tree `(title)` | **`pg_trgm` GIN** (`gin_trgm_ops`) or FTS (`/shadow-search`) |

## 7. Real Production Scenario
A dashboard query `SELECT id, total_minor FROM orders WHERE tenant_id = $1 AND status = 'PAID' AND created_at >= $2 ORDER BY created_at DESC LIMIT 20` takes `1.9 seconds` despite having an index on `(created_at)`. `EXPLAIN (ANALYZE, BUFFERS)` reveals Postgres scans 480,000 recent rows across all tenants and discards 99.2% (`Rows Removed by Filter`). Adding `CREATE INDEX CONCURRENTLY idx_orders_tenant_status_created ON orders (tenant_id, status, created_at DESC, id DESC) INCLUDE (total_minor)` switches the plan to `Index Only Scan` touching 4 buffers (`0.8ms` — a **2,300x speedup**).

## 8. Failure Modes & Edge Cases
- **WRONG:** Creating 12 single-column indexes on every column of a table (kills write throughput, prevents PostgreSQL HOT updates, bloats RAM/disk, and rarely helps multi-column queries!).
- **RIGHT:** Consolidate into 3–5 purposeful composite/partial indexes validated against `pg_stat_statements` top slow queries.
- **WRONG:** Running `CREATE INDEX` inside a default ORM migration transaction wrapper (cannot run `CONCURRENTLY` inside a transaction -> silently blocks all writes!).
- **RIGHT:** Disable transaction wrapping specifically for `CREATE INDEX CONCURRENTLY` migrations (`-- prisma / knex / alembic transactional=false`) and check `pg_index.indisvalid` if a concurrent build fails!

## 9. Testing & Verification
- Run `python shadow-db/scripts/sql_migration_safety_verifier.py --check-ddl <mig.sql>` to ensure every index uses `CONCURRENTLY`.
- Inspect `EXPLAIN (ANALYZE, BUFFERS)` before and after index creation on staging-scale data; confirm `Seq Scan` / high `Rows Removed by Filter` disappears.

## 10. Operational Considerations
- Enable `pg_stat_statements` on every PostgreSQL instance and review top 10 queries by `total_exec_time` AND `shared_blks_read` monthly (`/shadow-perf`).

## 11. Authoritative References
- PostgreSQL Documentation — *Chapter 11: Indexes* & *Chapter 14: Using EXPLAIN* (`https://www.postgresql.org/docs/current/indexes.html`).
- Markus Winand — *Use The Index, Luke!* (`https://use-the-index-luke.com/`).

## 12. Limitations & When NOT to Use
- Never add B-tree indexes to tiny lookup tables (`< 500` rows, `1–2` pages) — Postgres will ignore them for faster sequential scans anyway.
