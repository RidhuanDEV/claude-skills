# 04. PostgreSQL Row-Level Security (RLS) & `SECURITY DEFINER`

## 1. Purpose & Activation Conditions
Enforce multi-tenant database isolation via PostgreSQL / Supabase **Row-Level Security (RLS)** without triggering catastrophic sequential scans, and harden `SECURITY DEFINER` helper RPCs against `search_path` privilege escalation. Load when designing Postgres/Supabase RLS policies, tenant-scoped `SET LOCAL` pooling, or elevated SQL helper functions.

## 2. Prerequisites
- Authenticated server tenant context (`shadow-auth`), indexed `tenant_id` / `user_id` columns (`03`), and PgBouncer transaction-mode awareness (`05`).

## 3. Technical Principles & Constraints
- **Defense-in-Depth Multi-Tenant Isolation:** `ALTER TABLE ... ENABLE ROW LEVEL SECURITY` + `FORCE ROW LEVEL SECURITY` enforces tenant predicates inside Postgres even if an ORM query or developer forgets `WHERE tenant_id = $2`! Write explicit separate policies for `SELECT`, `INSERT` (`WITH CHECK`), `UPDATE` (`USING` + `WITH CHECK`), and `DELETE` (`USING`), scoped explicitly `TO authenticated` (never implicit `PUBLIC`).
- **InitPlan Caching Invariant (`(SELECT auth.uid())` — 10x–100x Speedup!):** Bare `auth.uid()`, `auth.jwt()`, or `current_setting('app.tenant_id', true)` inside an RLS policy can be re-evaluated **per scanned row**! Wrapping it in a scalar subquery **`(SELECT auth.uid())`** or **`(SELECT current_setting('app.tenant_id', true)::uuid)`** lets PostgreSQL evaluate the expression **once per statement** via an InitPlan and use the leading `(tenant_id, ...)` B-tree index cleanly!
- **PgBouncer Transaction Pooling `SET LOCAL` Invariant (CRITICAL):** When using `PgBouncer` in `pool_mode = transaction`, ALWAYS set tenant context inside the active transaction using **`SET LOCAL app.tenant_id = '...'`** (auto-resets on `COMMIT`/`ROLLBACK`). NEVER use session-level `SET app.tenant_id = ...` — it leaks Tenant A's identity onto the next pooled connection serving Tenant B!
- **Hardened `SECURITY DEFINER` Functions:** Any function running with creator privileges (`SECURITY DEFINER`) MUST declare **`SET search_path = ''`**, fully schema-qualify EVERY table/function (`public.tenant_memberships`), `REVOKE ALL FROM PUBLIC`, and `GRANT EXECUTE` strictly to the minimal role (`authenticated`) to eliminate schema-shadowing privilege escalation.

## 4. Architecture & Implementation
```sql
-- 1. Enable & Force RLS with InitPlan-cached tenant predicate + leading composite index
ALTER TABLE public.invoices ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.invoices FORCE ROW LEVEL SECURITY;

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_invoices_tenant_status_created
  ON public.invoices (tenant_id, status, created_at DESC)
  INCLUDE (total_minor);

CREATE POLICY invoices_tenant_select
  ON public.invoices FOR SELECT TO authenticated
  USING (tenant_id = (SELECT current_setting('app.tenant_id', true)::uuid));

CREATE POLICY invoices_tenant_insert
  ON public.invoices FOR INSERT TO authenticated
  WITH CHECK (tenant_id = (SELECT current_setting('app.tenant_id', true)::uuid));

CREATE POLICY invoices_tenant_update
  ON public.invoices FOR UPDATE TO authenticated
  USING (tenant_id = (SELECT current_setting('app.tenant_id', true)::uuid))
  WITH CHECK (tenant_id = (SELECT current_setting('app.tenant_id', true)::uuid));

-- 2. Hardened SECURITY DEFINER helper RPC (Zero search_path hijack)
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

## 5. Platform / Vendor Variations
| Environment | Tenant Context Injection | Critical Gotcha |
| :--- | :--- | :--- |
| **Supabase (PostgREST + JWT)** | `(SELECT auth.uid())` / `(SELECT auth.jwt()->>'tenant_id')` | Always wrap in `(SELECT ...)` + specify `TO authenticated` + index policy columns |
| **Self-Hosted Postgres + PgBouncer (`transaction` mode)** | `BEGIN; SELECT set_config('app.tenant_id', $1, true); ... COMMIT;` (`is_local = true`) | Session-level `SET` without `LOCAL` leaks across pooled tenants! |
| **Migration / Superuser Role (`BYPASSRLS`)** | Runs DDL migrations only — NEVER used by app web workers! | App runtime DB role MUST have `NOBYPASSRLS` |

## 6. Decision Matrix & Trade-Offs
| Multi-Tenant Isolation Layer | Stops Forgotten App `WHERE`? | Performance Overhead | Recommendation |
| :--- | :---: | :---: | :--- |
| **App `WHERE tenant_id = $1` Only** | No | Zero | Baseline minimum |
| **App `WHERE` + InitPlan RLS (`NOBYPASSRLS`)** | **YES (Defense-in-depth)** | Negligible (`< 2%` with index + InitPlan) | **Recommended for multi-tenant SaaS & regulated apps** |
| **Separate DB per Tenant** | **YES (Physical)** | High operational/migration overhead | Only for strict banking/enterprise single-tenant contracts |

## 7. Real Production Scenario
A Supabase multi-tenant SaaS adds `CREATE POLICY p ON orders FOR SELECT USING (user_id = auth.uid());` on a 600k-row table. Queries slow from `4ms` to `340ms` (`85x` regression) because Postgres invokes `auth.uid()` 600,000 times and scans sequentially. Wrapping `(SELECT auth.uid())`, adding `TO authenticated`, and creating `idx_orders_user_created` restores `Index Scan` with `InitPlan` in `3.5ms` — while keeping cross-tenant isolation 100% enforced.

## 8. Failure Modes & Edge Cases
- **WRONG:** Connecting the Node/Python web app to Postgres as the `postgres` superuser (or table owner without `FORCE ROW LEVEL SECURITY`), which silently **bypasses ALL RLS policies**!
- **RIGHT:** Run the application strictly under a dedicated `NOBYPASSRLS` role (`app_runtime`) and verify RLS with `SET LOCAL ROLE app_runtime` in integration tests.
- **WRONG:** Writing a complex correlated subquery join inside an RLS `USING` clause that runs on every single row of a large table without a `SECURITY DEFINER` cached helper or indexed join key.
- **RIGHT:** Index all join/policy keys and verify `InitPlan` + `Index Scan` via `EXPLAIN (ANALYZE, BUFFERS)`.

## 9. Testing & Verification
- Run `python shadow-db/scripts/sql_migration_safety_verifier.py --check-rls <rls.sql>` to catch uncached `auth.uid()` and unhardened `SECURITY DEFINER` functions offline.
- Run a two-tenant DB integration test as `NOBYPASSRLS` role: `SET LOCAL app.tenant_id = '<tenant_a>'` -> assert `SELECT` returns 0 rows from `tenant_b` AND `INSERT`/`UPDATE` with `tenant_b` raises PostgreSQL `42501` (`insufficient_privilege`).

## 10. Operational Considerations
- Audit `pg_tables.rowsecurity` in CI/staging to ensure every new table in `public` (or exposed schema) explicitly enables RLS before release.

## 11. Authoritative References
- PostgreSQL Documentation — *5.8 Row Security Policies* & *CREATE FUNCTION (`SECURITY DEFINER`)* (`https://www.postgresql.org/docs/current/ddl-rowsecurity.html`).
- Supabase Official Docs — *Row Level Security Performance & Best Practices* (`https://supabase.com/docs/guides/database/postgres/row-level-security`).

## 12. Limitations & When NOT to Use
- RLS does not replace application-level RBAC/ABAC checks for complex workflow rules (e.g., maker-checker self-approval rules — `/shadow-auth` & `/shadow-domain`); treat RLS strictly as the storage-layer tenant/ownership guardrail.
