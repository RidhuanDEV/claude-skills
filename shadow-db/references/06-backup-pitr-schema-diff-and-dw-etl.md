# 06. Backup/PITR, Schema Diff, `shadow_db` MCP & DW/ETL Integrity

## 1. Purpose & Activation Conditions
Operate live read-only database inspection (`shadow_db` MCP), cross-environment schema diffing, Point-in-Time Recovery (PITR) compatibility checks, and honest cross-database ETL / Star Schema Data Warehouse / Pentaho PDI (`.ktr`/`.kjb`) engineering. Load when inspecting live DBs, generating ERDs/diffs, auditing restore readiness, or generating cross-DB DW/ETL artifacts.

## 2. Prerequisites
- Verified target environment identity (never run against an unknown host — fails closed `BLOCKED_UNKNOWN_ENVIRONMENT`), `shadow_db` MCP tools, and coordination with `/shadow-resilience` for backup restore drills.

## 3. Technical Principles & Constraints
- **Read-Only Default & Fail-Closed Environment Gate (`L0` vs `L4`):**
  - `shadow_db` MCP (`inspect_database_schema`, `run_readonly_query`, `generate_dbml_and_erd`, `compare_database_schemas`) strictly permits `SELECT`, `EXPLAIN`, `SHOW`, and `PRAGMA` on verified local/dev DBs (`L0`/`L1`).
  - ANY schema DDL mutation, data modification, or staging/production/unknown DB access is **`L4_HIGH_IMPACT`** requiring explicit Monarch approval + verified backup!
- **Backup & PITR Restore Compatibility (`/shadow-resilience`):**
  - A backup you have never restored is NOT a backup! Coordinate with `/shadow-resilience` to run scheduled restore drills (`pg_basebackup` + WAL archiving PITR) in ephemeral isolated containers (`--rm --label shadow.ephemeral=true`), verifying RPO/RTO AND replaying privacy erasure tombstones (`shadow-privacy`) after restore!
  - Verify schema migrations do not break logical dump/restore ordering (e.g., custom functions referenced in check constraints or missing extension versions).
- **Honest Cross-DB ETL & Data Warehouse Verification (`generate_cross_db_etl_and_warehouse`):**
  - `generate_cross_db_etl_and_warehouse` writes **6 draft artifacts** (`01_target_ddl`, `02_star_schema_warehouse`, `03_etl_migration_blueprint`, `04_pentaho_sync_transformation.ktr`, `05_pentaho_master_job.kjb`, `06_cron_and_airflow_orchestrator.py`).
  - **CRITICAL Truthfulness Rule:** Generating these files proves **file generation ONLY** — NEVER claim a cross-DB or DW migration is verified until you independently verify:
    1. **Target Type & Precision Parity:** Exact `DECIMAL(30,8)`/`NUMERIC` scale (never silently narrowed to `FLOAT`), UTC `TIMESTAMPTZ`, `NULL` vs `''` (Oracle/MySQL vs Postgres), and identifier quoting,
    2. **Syntax & Dry-Run Execution:** Target engine parses DDL and executes against a throwaway sandbox cleanly,
    3. **Checkpoint Restartability:** Interrupting mid-batch and restarting resumes cleanly via watermark + idempotent `UPSERT` with zero duplicate rows,
    4. **Source-to-Target Reconciliation:** Row counts, sum/checksums of monetary columns, and NULL-rate parity match within `0.0%` tolerance!

## 4. Architecture & Implementation
```sql
-- Cross-DB / Star Schema Reconciliation Verification Query (Run on Source & Target, Compare Exact Totals)
SELECT
  COUNT(*) AS total_rows,
  COUNT(DISTINCT order_id) AS distinct_keys,
  SUM(total_minor) AS sum_total_minor,
  COUNT(*) FILTER (WHERE customer_id IS NULL) AS null_customer_count,
  MIN(updated_at) AS min_updated_at,
  MAX(updated_at) AS max_updated_at
FROM fact_orders
WHERE updated_at >= $1 AND updated_at < $2;
```
Offline DDL + RLS gate before executing any generated SQL:
```powershell
python "shadow-db/scripts/sql_migration_safety_verifier.py" --self-test
python "shadow-db/scripts/sql_migration_safety_verifier.py" --check-ddl docs/db/etl/01_target_ddl_postgres.sql
```

## 5. Platform / Vendor Variations (Cross-Engine Translation Traps)
| Source -> Target | High-Risk Silent Semantic Drift | Mandatory Verification |
| :--- | :--- | :--- |
| **MySQL -> PostgreSQL** | `TINYINT(1)` bool, `0000-00-00` zero dates, case-insensitive default collations, `UNSIGNED BIGINT` overflow | Map `UNSIGNED BIGINT` -> `NUMERIC(20,0)`, sanitize zero dates, test case-sensitive uniqueness |
| **MSSQL -> PostgreSQL** | `DATETIME2` (no TZ) vs `TIMESTAMPTZ`, `UNIQUEIDENTIFIER` casing, `BIT` vs `BOOLEAN`, `IDENTITY` sequences | Reset target PG sequence (`setval`) after initial load! |
| **OLTP -> Star Schema DW (`dim_*`/`fact_*`)** | SCD Type 2 effective dates (`valid_from`/`valid_to`), late-arriving facts, surrogate keys | Verify every fact FK resolves to valid dimension surrogate key (or explicit `Unknown` member `-1`) |

## 6. Decision Matrix & Trade-Offs
| Task | `shadow_db` MCP Tool | Approval Level |
| :--- | :--- | :---: |
| Inspect tables/indexes/FKs on verified local DB | `inspect_database_schema` / `generate_dbml_and_erd` | `L0_READ_ONLY` |
| Run `EXPLAIN (ANALYZE, BUFFERS)` on local `SELECT` | `run_readonly_query` | `L0`/`L1` |
| Compare Local vs Staging schema drift | `compare_database_schemas` (read-only metadata) | `L0` (if staging read approved) |
| Execute DDL / restore / ETL load into Staging/Prod | Native migration tool / Pentaho / Airflow | **`L4_HIGH_IMPACT` (Explicit Monarch Approval)** |

## 7. Real Production Scenario
A team generates MySQL-to-PostgreSQL DDL and Pentaho `.ktr` jobs using `generate_cross_db_etl_and_warehouse`, glances at the files, and marks the ticket `"Migration Ready"`. During actual staging dry-run, MySQL `0000-00-00 00:00:00` timestamps crash PostgreSQL, `UNSIGNED BIGINT` overflows signed `BIGINT`, and PostgreSQL sequences aren't fast-forwarded (`setval`), causing `23505 duplicate key` on the first new insert! Enforcing the 4-point independent ETL verification checklist catches all 3 defects in staging before cutover.

## 8. Failure Modes & Edge Cases
- **WRONG:** Presenting generated `docs/db/etl/*.sql` / `.ktr` drafts as `"verified working ETL"` without running target DDL parsing, restart tests, and row/checksum reconciliation.
- **RIGHT:** Explicitly label generated files as `DRAFT` until syntax, restartability, and checksum reconciliation execute with observed `PASS` output.
- **WRONG:** Leaving ephemeral Docker PostgreSQL test containers running after a local DDL or restore check (`Rule #29`).
- **RIGHT:** Always pass `--rm --label shadow.ephemeral=true` and tear down in `try/finally`.

## 9. Testing & Verification
- Run `python shadow-db/scripts/sql_migration_safety_verifier.py --self-test` and `python -m unittest discover -s shadow-db/tests -v`.
- Validate cross-DB schema drift via `compare_database_schemas` and confirm exact source-vs-target reconciliation queries (`COUNT`, `SUM`, `MIN/MAX`).

## 10. Operational Considerations
- Keep `docs/db/schema.dbml` and `docs/db/ERD.md` regenerated after major schema milestones so onboarding engineers and architects share one accurate picture of live constraints.

## 11. Authoritative References
- PostgreSQL Documentation — *Chapter 26: Backup and Restore (PITR & WAL Archiving)* (`https://www.postgresql.org/docs/current/backup.html`).
- Kimball Group — *Star Schema Dimensional Modeling* (`https://www.kimballgroup.com/`).

## 12. Limitations & When NOT to Use
- Do NOT use `shadow_db` MCP for high-frequency application migrations or backfill orchestration — use `/shadow-data` (Expand-Contract, chunked backfills, ACID locking) and versioned migration tools (`Prisma`, `Drizzle`, `Flyway`, `Alembic`, `golang-migrate`).
