---
name: shadow-db
description: Inspect live databases (PostgreSQL, MySQL, MariaDB, SQL Server/MSSQL, MongoDB, SQLite), run safe read-only queries, auto-generate DBML/Mermaid ERDs, compare schemas across databases, enforce zero-downtime migration safety, and generate Cross-DB ETL, Pentaho (.ktr/.kjb), Cron/Airflow & Data Warehouse Star Schemas. Pairs with /shadow-data and /shadow-resilience. Trigger with /shadow-db.
---

# `/shadow-db` — Multi-Engine Database Inspector, Schema Diff, Auto-ERD, Migration Safety & Data Warehouse Generator

Use this skill whenever the **Monarch** invokes `/shadow-db` or works on database inspection, query performance (`EXPLAIN ANALYZE`), zero-downtime schema evolution, cross-database migration (e.g. MySQL ↔ PostgreSQL ↔ SQL Server), or ETL / Data Warehouse Star Schema (`dim_*` / `fact_*`) + Pentaho PDI (`.ktr`/`.kjb`) design.

Connects to the **`shadow_db` MCP server** (`inspect_database_schema`, `run_readonly_query`, `generate_dbml_and_erd`, `compare_database_schemas`, `generate_cross_db_etl_and_warehouse`) and pairs with **`/shadow-data`** (data lifecycle & migrations) and **`/shadow-resilience`** (backup restore compatibility).

---

## 1. Supported Engines (Auto-Detected from `.env` or DSN)

1. **PostgreSQL / Supabase / Neon / TimescaleDB / CockroachDB / Redshift** (`postgres://`)
2. **MySQL / MariaDB / TiDB / SingleStore** (`mysql://`, `mariadb://`)
3. **Microsoft SQL Server / Azure SQL** (`mssql://`, `sqlserver://`)
4. **MongoDB** (`mongodb://`, `mongodb+srv://`)
5. **SQLite** (`sqlite://`, `.db`, `.sqlite`)

---

## 2. Core Capabilities & Workflow

1. **Read-Only by Default Inspection (`inspect_database_schema`, `run_readonly_query`)**:
   - Automatically reads `DATABASE_URL` or `DB_*` from `<projectPath>/.env`.
   - Enforces a strict Read-Only SQL Gate (`SELECT`, `EXPLAIN`, `SHOW`, `PRAGMA` only). Any schema mutation or data deletion requires explicit confirmation from the **Monarch**.
2. **Auto-Generate ERD (`generate_dbml_and_erd`)**:
   - Generates `docs/db/schema.dbml` ([dbdiagram.io](https://dbdiagram.io)) and `docs/db/ERD.md` (Mermaid `erDiagram`) from the live database.
3. **Cross-Database Schema Drift & Compatibility Check (`compare_database_schemas`)**:
   - Compares two live databases (e.g. Local vs Staging/Production, or MySQL vs PostgreSQL) and identifies missing tables, missing columns, and type mismatches before deployment.
4. **Migration Safety & Restore Compatibility (Integrated with `/shadow-data`)**:
   - Audits pending migrations to prevent table-locking operations (`DROP COLUMN`, `RENAME COLUMN`, or unindexed foreign keys on large tables) and ensures backup restore compatibility with `/shadow-resilience`.
5. **Cross-DB Migration, Data Warehouse Star Schema, Pentaho PDI & Cron (`generate_cross_db_etl_and_warehouse`)**:
   - Generates 6 production-ready artifacts in `docs/db/etl/`:
     1. `01_target_ddl_<engine>.sql` (translated DDL for `postgres`, `mysql`, `mssql`, `clickhouse`, or `bigquery`)
     2. `02_star_schema_warehouse_<engine>.sql` (`dim_*` & `fact_*` Star Schema with surrogate keys and audit timestamps)
     3. `03_etl_migration_blueprint.md` (batch chunking, watermark strategy, and idempotent upsert patterns)
     4. `04_pentaho_sync_transformation.ktr` (Pentaho Spoon Transformation XML with parameterized connections)
     5. `05_pentaho_master_job.kjb` (Pentaho Master Job XML with DB pre-check and failure alert hops)
     6. `06_cron_and_airflow_orchestrator.py` (Python Cron runner with anti-overlap file lock + Apache Airflow DAG)
