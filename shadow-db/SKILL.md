---
name: shadow-db
description: "Inspect live databases (PostgreSQL, MySQL, MariaDB, SQL Server/MSSQL, MongoDB, SQLite), run safe read-only queries, auto-generate DBML/Mermaid ERDs, compare schemas across databases, and generate Cross-DB ETL & Data Warehouse Star Schemas (Postgres, MySQL, MSSQL, ClickHouse, BigQuery). Trigger with /shadow-db."
---

# /shadow-db — Multi-Engine Database Inspector, Schema Diff, Auto-ERD & Cross-DB ETL/Warehouse Generator

Use this skill whenever the **Monarch** invokes `/shadow-db` or works on database inspection, query performance (`EXPLAIN ANALYZE`), cross-database migration (e.g. MySQL ↔ PostgreSQL ↔ SQL Server), or ETL / Data Warehouse Star Schema (`dim_*` / `fact_*`) design.

Connects to the **`shadow_db` MCP server** (`inspect_database_schema`, `run_readonly_query`, `generate_dbml_and_erd`, `compare_database_schemas`, `generate_cross_db_etl_and_warehouse`) and pairs with `shadow-monarch/reference/DATABASE.md`, `reference/DATA-AUTOMATION.md`, and `reference/DATA-ANALYTICS-ML.md`.

## Supported Engines (Auto-Detected from `.env` or DSN)

1. **PostgreSQL / Supabase / Neon / TimescaleDB / CockroachDB / Redshift** (`postgres://`)
2. **MySQL / MariaDB / TiDB / SingleStore** (`mysql://`, `mariadb://`)
3. **Microsoft SQL Server / Azure SQL** (`mssql://`, `sqlserver://`)
4. **MongoDB** (`mongodb://`, `mongodb+srv://`)
5. **SQLite** (`sqlite://`, `.db`, `.sqlite`)

## Workflow

1. **Live Schema Introspection & Safe Read-Only Query (`inspect_database_schema`, `run_readonly_query`)**:
   - Automatically reads `DATABASE_URL` or `DB_*` from `<projectPath>/.env`.
   - Enforces a strict Read-Only SQL Gate (`SELECT`, `EXPLAIN`, `SHOW`, `PRAGMA` only).
2. **Auto-Generate ERD (`generate_dbml_and_erd`)**:
   - Generates `docs/db/schema.dbml` (dbdiagram.io) and `docs/db/ERD.md` (Mermaid `erDiagram`) from the live database.
3. **Cross-Database Schema Comparison (`compare_database_schemas`)**:
   - Compares two live databases (even across different engines, e.g., MySQL vs PostgreSQL) and lists missing tables, missing columns, and type differences.
4. **Cross-DB Migration & Data Warehouse ETL (`generate_cross_db_etl_and_warehouse`)**:
   - Translates any live source schema into target DDL (`01_target_ddl_<engine>.sql`), Data Warehouse **Star Schema (`dim_*` & `fact_*`)** (`02_star_schema_warehouse_<engine>.sql`), and an idempotent incremental ETL sync blueprint (`03_etl_migration_blueprint.md`) for `postgres`, `mysql`, `mssql`, `clickhouse`, or `bigquery`.
