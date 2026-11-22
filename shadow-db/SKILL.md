---
name: shadow-db
description: "Database Architecture, Live Inspection & SQL Performance Specialist. Use when inspecting live DBs via shadow_db MCP, diagnosing EXPLAIN ANALYZE/locks/deadlocks, designing composite/partial/FK indexes, hardening Postgres RLS ((SELECT auth.uid())) & SECURITY DEFINER, sizing PgBouncer/partitioning, generating DBML/Mermaid ERDs, or drafting Star Schema DW/Pentaho ETL. Do NOT use for app backfill workflows (/shadow-data)."
---

# Shadow DB (`/shadow-db`) — Multi-Engine Database Engineering, Inspection & SQL Tuning

Use this skill whenever the **Monarch** inspects live databases via **`shadow_db` MCP**, diagnoses `EXPLAIN (ANALYZE, BUFFERS)` query plans, MVCC/deadlocks, or connection-pool saturation, hardens PostgreSQL/Supabase RLS & `SECURITY DEFINER` RPCs, generates ERDs/schema diffs, or drafts cross-DB Data Warehouse / Pentaho PDI (`.ktr`/`.kjb`) ETL pipelines.

## 1. Supported Engines & `shadow_db` MCP Capabilities

Auto-detected from `.env` / DSN: **PostgreSQL** (Supabase/Neon/TimescaleDB/CockroachDB/Redshift), **MySQL / MariaDB / TiDB**, **Microsoft SQL Server / Azure SQL**, **MongoDB**, and **SQLite**.
- **`inspect_database_schema` & `run_readonly_query`:** Strictly read-only by default (`SELECT`, `EXPLAIN`, `SHOW`, `PRAGMA`). Unknown DB hosts fail closed (`BLOCKED_UNKNOWN_ENVIRONMENT`); any DDL/data mutation or staging/prod access is **`L4_HIGH_IMPACT`** requiring explicit Monarch approval.
- **`generate_dbml_and_erd` & `compare_database_schemas`:** Generates `docs/db/schema.dbml` + `docs/db/ERD.md` and detects cross-environment schema drift.
- **`generate_cross_db_etl_and_warehouse`:** Produces 6 **draft** artifacts under `docs/db/etl/` (`01_target_ddl`, `02_star_schema_warehouse`, `03_etl_migration_blueprint`, `04_pentaho_sync_transformation.ktr`, `05_pentaho_master_job.kjb`, `06_cron_and_airflow_orchestrator.py`). File generation alone does **NOT** verify execution — independently verify target precision (`DECIMAL`/`TIMESTAMPTZ`), DDL syntax, checkpoint restartability, and source-to-target reconciliation!

## 2. Core Database Engineering Non-Negotiables

1. **Precision & Relational Integrity:** Store currency as `BIGINT` minor units or `NUMERIC(19,4)` (never `FLOAT`), instants as UTC `TIMESTAMPTZ`, soft-delete uniqueness via partial indexes (`WHERE deleted_at IS NULL`), and index every referencing FK column.
2. **Lock-Safe DDL & Deadlock Hygiene:** Always set `SET lock_timeout`, use `CREATE INDEX CONCURRENTLY`, add FKs/checks with `NOT VALID` + `VALIDATE CONSTRAINT`, acquire multi-row locks in deterministic `ORDER BY id ASC FOR UPDATE` order, and keep external network I/O outside DB transactions.
3. **Measure First (`EXPLAIN (ANALYZE, BUFFERS)`):** Order composite B-tree columns `Equality (tenant_id first) -> Sort -> Range`, keep predicates SARGable, and verify InitPlan caching **`(SELECT auth.uid())`** + **`SET search_path = ''`** on `SECURITY DEFINER` functions.
4. **Pooling, Autovacuum & Replicas:** Multiplex pods via `PgBouncer` (`pool_mode = transaction` + **`SET LOCAL`** for tenant context — never session `SET`), tune per-table autovacuum on high-churn queues, and pin read-after-write queries to primary.

## 3. Deterministic Verification CLI & Scenario Benchmarks

Run offline checks (`L0`/`L1`, read-only SQL analysis) before claiming `VERIFIED-LOCAL`:
```powershell
python "shadow-db/scripts/sql_migration_safety_verifier.py" --self-test
python "shadow-db/scripts/sql_migration_safety_verifier.py" --check-ddl path/to/migration.sql
python "shadow-db/scripts/sql_migration_safety_verifier.py" --check-rls path/to/rls_policies.sql
python -m unittest discover -s "shadow-db/tests" -v
```
Graded specialist scenarios live in [evaluations.md](evaluations.md) (8 scenarios covering blocking FK outages, per-row RLS `auth.uid()` slowdowns, `SECURITY DEFINER` `search_path` hijack, `PgBouncer` exhaustion, deadlocks, unknown-host `L4` blocking, and honest ETL verification).

## Reference Guide

Load **only** the 1–2 modules matching the active subtask (never load all 6 at once):

| Task / Scenario | Tier | Load Reference |
| :--- | :--- | :--- |
| Relational schema design, `BIGINT`/`NUMERIC` money, UTC `TIMESTAMPTZ`, soft-delete partial unique & FK indexes | CORE | [references/01-relational-design-and-integrity-invariants.md](references/01-relational-design-and-integrity-invariants.md) |
| MVCC isolation (`40001`/`40P01`), deterministic lock ordering, `pg_locks` diagnostics & `lock_timeout` | CORE | [references/02-transactions-isolation-and-lock-diagnostics.md](references/02-transactions-isolation-and-lock-diagnostics.md) |
| `EXPLAIN (ANALYZE, BUFFERS)`, composite equality->sort->range ordering, partial/covering/GIN/BRIN & `CONCURRENTLY` | CORE | [references/03-query-explain-and-indexing-strategy.md](references/03-query-explain-and-indexing-strategy.md) |
| PostgreSQL / Supabase RLS (`(SELECT auth.uid())` InitPlan, `SET LOCAL`) & hardened `SECURITY DEFINER` | ADVANCED | [references/04-postgres-rls-and-security-definer.md](references/04-postgres-rls-and-security-definer.md) |
| Multi-engine choice, `PgBouncer` transaction pooling, autovacuum tuning, range partitioning & replica lag | ADVANCED | [references/05-connection-pooling-partitioning-and-replicas.md](references/05-connection-pooling-partitioning-and-replicas.md) |
| `shadow_db` MCP read-only inspection, schema diff, PITR restore drills & verified Star Schema / Pentaho DW ETL | OPERATIONAL | [references/06-backup-pitr-schema-diff-and-dw-etl.md](references/06-backup-pitr-schema-diff-and-dw-etl.md) |

Do not load unrelated references unnecessarily.
