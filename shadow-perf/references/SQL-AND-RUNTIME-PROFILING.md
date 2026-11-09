# SQL-AND-RUNTIME-PROFILING — Pre-UAT Bottleneck Diagnosis

---

## 1. Database Query Profiling (`EXPLAIN ANALYZE`) via `shadow_db` MCP

Before UAT sign-off, inspect the top 5–10 queries executed by dashboards, reports, and list endpoints.

### A. PostgreSQL `EXPLAIN (ANALYZE, BUFFERS)` Red Flags
| Symptom in `EXPLAIN` Output | Root Cause | Concrete Fix |
| :--- | :--- | :--- |
| `Seq Scan on orders (cost=... rows=...)` with high `Rows Removed by Filter` | Missing index on `WHERE` / `JOIN` columns | Create composite B-Tree index matching equality columns first, then range/sort column: `CREATE INDEX CONCURRENTLY idx_orders_tenant_status_created ON orders (tenant_id, status, created_at DESC);` |
| `Sort Method: external merge Disk: 24500kB` | Sort exceeds `work_mem` and spills to disk | Add index matching `ORDER BY ... LIMIT` or increase session `work_mem`. |
| `Nested Loop` with `loops=5000` | N+1 or unindexed foreign key on inner table | Add index on foreign key column (`order_items.order_id`) or rewrite as batch query / `JOIN`. |
| `Filter: (lower(email) = '...')` bypassing index on `email` | Function call on indexed column prevents index usage | Create expression index `CREATE INDEX ON users (lower(email))` or use `citext`. |

### B. MySQL / MariaDB `EXPLAIN FORMAT=JSON` Red Flags
- `type: ALL` -> Full table scan! Must be `ref`, `eq_ref`, `range`, or `const`.
- `Using filesort` + `Using temporary` on large pagination queries -> Add composite covering index `(status, created_at, id)` and use keyset/cursor pagination (`WHERE created_at < ?`) instead of `OFFSET 50000`.

---

## 2. Backend & Connection Pool Checklist for Pre-UAT

1. **DB Connection Pool Sizing**:
   - Never leave pool size unbounded or tiny (default `5` in some ORMs). Set pool max to `(CPU cores * 2) + effective_spindle_count` per instance (typically `10–25` per Node/Python worker) and configure a connection timeout (`5000ms`).
2. **N+1 Query Elimination**:
   - Check ORM debug logs during a single list request: if fetching 20 items executes 21+ SQL queries, replace lazy loading with eager batch loading (`include` / `select_related` / `prefetch_related` / `With()`).
3. **Unbounded Export / Report Endpoints**:
   - Ensure Excel/CSV/PDF export endpoints stream rows in batches or run asynchronously via a background worker if row count exceeds `5,000`.
