# PostgreSQL Row-Level Security (RLS), Indexing & Function Hardening

> Distilled from verified 1st-party PostgreSQL & Supabase engineering patterns (`supabase/agent-skills` `postgres-best-practices`). Load when designing multi-tenant Postgres RLS policies, composite/partial/covering indexes, foreign-key indexes, or `SECURITY DEFINER` RPC functions.

## 1. Core Concepts
PostgreSQL Row-Level Security (RLS) turns authorization into an implicit `WHERE` predicate enforced on every query—even when application code forgets a tenant filter—but naive RLS policies can silently degrade index scans into full sequential scans:
- **InitPlan Caching (`(SELECT auth.uid())`):** Bare `auth.uid()` or `current_setting('app.tenant_id', true)` inside an RLS policy can be re-evaluated **per scanned row**. Wrapping it in a scalar subquery `(SELECT auth.uid())` lets PostgreSQL compute the value **once per statement** via an InitPlan (often `10x–100x` faster on large tables).
- **`SECURITY DEFINER` Privilege Safety:** Functions running with creator privileges (`SECURITY DEFINER`) MUST pin **`SET search_path = ''`** (or an explicit immutable schema list) and schema-qualify object references (`public.orders`) to eliminate schema-spoofing privilege escalation.

## 2. Technical Rules & Decision Matrix

| Postgres / Supabase Concern | Pattern to Apply | Mandatory Verification |
| :--- | :--- | :--- |
| Multi-Tenant Table in Exposed Schema | `ALTER TABLE ... ENABLE ROW LEVEL SECURITY` + explicit `SELECT`/`INSERT`/`UPDATE`/`DELETE` policies | Verify cross-tenant read/write returns `0` rows / `42501` error |
| Per-Row RLS Function Overhead | Wrap session functions in **`(SELECT auth.uid())`** / **`(SELECT current_setting('app.tenant_id', true)::uuid)`** | Confirm `InitPlan` in `EXPLAIN (ANALYZE, BUFFERS)` |
| RLS & Foreign-Key Columns | Create explicit B-tree index on every `tenant_id`, `user_id`, and FK column used in joins/policies | PostgreSQL does NOT auto-index FKs; verify `Index Scan` |
| Multi-Column Filter + Sort Query | **Composite Index**: Equality columns first (highest selectivity) -> Range/Sort column last + optional `INCLUDE (...)` | Inspect `EXPLAIN (ANALYZE, BUFFERS)` for zero `Sort` disk spill |
| Sparse Active Queue / Soft-Delete Table | **Partial Index** (`WHERE deleted_at IS NULL` or `WHERE status = 'PENDING'`) | Dramatically smaller index footprint & faster autovacuum |
| Elevated Helper RPC (`SECURITY DEFINER`) | Add `SET search_path = ''` + `REVOKE ALL FROM PUBLIC` + explicit `GRANT EXECUTE` | Audit `pg_proc.proconfig` contains pinned `search_path` |

## 3. Implementation Examples

### Fast Tenant-Isolated RLS Policy + Composite & Partial Indexes
```sql
-- 1. Enable RLS strictly on every multi-tenant table
ALTER TABLE public.invoices ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.invoices FORCE ROW LEVEL SECURITY;

-- 2. Index RLS/FK columns + composite filter/sort + partial index for active work
CREATE INDEX CONCURRENTLY idx_invoices_tenant_status_created
  ON public.invoices (tenant_id, status, created_at DESC)
  INCLUDE (total_minor);

CREATE INDEX CONCURRENTLY idx_invoices_pending_queue
  ON public.invoices (tenant_id, created_at)
  WHERE status = 'PENDING';

-- 3. InitPlan-optimized RLS policy: (SELECT ...) evaluates ONCE per query, not per row
CREATE POLICY invoices_tenant_isolation_select
  ON public.invoices
  FOR SELECT
  TO authenticated
  USING (tenant_id = (SELECT current_setting('app.tenant_id', true)::uuid));

CREATE POLICY invoices_tenant_isolation_insert
  ON public.invoices
  FOR INSERT
  TO authenticated
  WITH CHECK (tenant_id = (SELECT current_setting('app.tenant_id', true)::uuid));
```

### Hardened `SECURITY DEFINER` Function (Zero Search-Path Hijack)
```sql
CREATE OR REPLACE FUNCTION public.get_tenant_membership_role(p_tenant_id uuid)
RETURNS text
LANGUAGE sql
STABLE
SECURITY DEFINER
SET search_path = ''
AS $$
  SELECT m.role
  FROM public.tenant_memberships AS m
  WHERE m.tenant_id = p_tenant_id
    AND m.user_id = (SELECT auth.uid())
  LIMIT 1;
$$;

REVOKE ALL ON FUNCTION public.get_tenant_membership_role(uuid) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION public.get_tenant_membership_role(uuid) TO authenticated;
```

## 4. Best Practices
- Always specify `TO authenticated` (or specific DB roles) on RLS policies instead of leaving roles implicit (`PUBLIC`) so anonymous traffic cannot trigger policy evaluation unnecessarily.
- Write separate policies for `SELECT`, `INSERT` (`WITH CHECK`), `UPDATE` (`USING` + `WITH CHECK`), and `DELETE` (`USING`) rather than one vague `FOR ALL` policy when write rules differ from read rules.
- Use `CREATE INDEX CONCURRENTLY` on live production tables so index creation never acquires an `ACCESS EXCLUSIVE` write lock (`/shadow-data`).

## 5. Anti-Patterns (`WRONG` vs `RIGHT`)
- **WRONG (Bare `auth.uid()` in RLS & unindexed `tenant_id` / FK):**
  ```sql
  -- Evaluates auth.uid() per row and triggers full Sequential Scan on 5M rows!
  CREATE POLICY bad_rls ON public.invoices FOR SELECT USING (user_id = auth.uid());
  ```
  **RIGHT:** Wrap `(SELECT auth.uid())` AND create a B-tree index on `(user_id)` or `(tenant_id, ...)`.
- **WRONG (`SECURITY DEFINER` without `SET search_path`):** Allowing attacker-controlled objects in writable schemas to shadow operators or functions inside a privileged RPC.
  **RIGHT:** Always declare `SET search_path = ''`, fully qualify `schema.table`, and restrict `EXECUTE` grants explicitly.

## 6. Production Considerations
- **Read-Only Planner Verification:** Validate every new RLS policy and composite index using `EXPLAIN (ANALYZE, BUFFERS)` inside a rolled-back transaction (`BEGIN; SET LOCAL ROLE authenticated; ...; ROLLBACK;`) to confirm `InitPlan` + `Index Scan` before deploying.
- **Connection Pooling Note:** When using `PgBouncer` in **Transaction Pooling** mode, set tenant context strictly with **`SET LOCAL app.tenant_id = '...'`** inside the transaction — NEVER session-level `SET` (which leaks tenant context across pooled clients!).
