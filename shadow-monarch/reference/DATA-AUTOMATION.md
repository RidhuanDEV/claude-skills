# DATA-AUTOMATION — Pentaho (PDI), Airflow, Cron Orchestration & Enterprise ETL Pipelines

Use when building Pentaho Data Integration (PDI / Kettle `.ktr` & `.kjb`), Apache Hop, Apache Airflow DAGs, scheduled Cron
jobs (`node-cron`, `gocron`, `APScheduler`, `systemd` timers, Windows Task Scheduler), cross-database ETL/ELT migrations
(PostgreSQL, MySQL, SQL Server, Oracle, ClickHouse, BigQuery), or high-volume CSV/Excel/JSON/Parquet processors.

## 1. Core principles for enterprise ETL & scheduled jobs

- **Idempotency is mandatory**: running a Pentaho job, Airflow task, or Cron script twice on the same time window must
  **never** duplicate rows, corrupt balances, or double-send alerts. Always use:
  - Deterministic Upsert (`INSERT ... ON CONFLICT DO UPDATE`, `ON DUPLICATE KEY UPDATE`, `MERGE INTO`, or Pentaho `Insert / Update` step).
  - Or `DELETE FROM target WHERE partition_date = ${RUN_DATE}` inside the same transaction before inserting the window.
- **Watermark & Audit Ledger (`etl_job_runs` & `etl_watermarks`)**:
  - Maintain a metadata table tracking `job_name`, `last_successful_watermark` (`TIMESTAMPTZ` or monotonic ID), `rows_read`,
    `rows_inserted`, `rows_updated`, `rows_rejected`, `status` (`RUNNING`, `SUCCESS`, `FAILED`), `started_at`, `finished_at`,
    and `error_message`.
  - Advance `last_successful_watermark` **only after** the target batch commits successfully, using a safety lookback overlap
    (e.g., `- 5 minutes`) to catch late-committed transactions.
- **Distributed Mutual Exclusion (Anti-Overlap Lock)**:
  - A 5-minute Cron job that takes 7 minutes to run will overlap and corrupt data unless locked.
  - Enforce a non-blocking lock at startup: PostgreSQL `SELECT pg_try_advisory_lock(hashtext('job_name'))`, MySQL `GET_LOCK('job_name', 0)`,
    Redis `SET lock:job_name 1 NX EX 3600`, or OS `flock` / PID lockfile. If already locked, log `SKIPPED_ALREADY_RUNNING` and exit `0`.

## 2. Pentaho Data Integration (PDI / Kettle `.ktr` & `.kjb`) Engineering Rules

When generating, reviewing, or automating Pentaho Kettle workloads:

- **Separation of Concerns (`.kjb` vs `.ktr`)**:
  - **Jobs (`.kjb`, run via `kitchen.sh` / `kitchen.bat`)**: handle **orchestration, control flow, transaction boundaries, pre-flight checks** (`Check DB connections`, `SQL` watermark fetch, `Set Variables`, `Transformation` execution, `Success`, `Mail`/Webhook alert on failure). Never do row-level data processing inside a Job.
  - **Transformations (`.ktr`, run via `pan.sh` / `pan.bat`)**: handle **parallel streaming row movement** (`Table Input` → `Select Values` → `Database Lookup` / `Stream Lookup` → `Insert / Update` or `Table Output`). All steps in a `.ktr` initialize and stream simultaneously—never assume step B waits for step A to finish unless gated by a `Blocking Step` or separate `.ktr` in a parent `.kjb`.
- **Parameterized Connections & Variables (`kettle.properties` / JNDI)**:
  - **NEVER hardcode database passwords or production IPs** inside `.ktr` or `.kjb` XML files. Use parameterized variables:
    `${SRC_DB_HOST}`, `${SRC_DB_PORT}`, `${SRC_DB_NAME}`, `${SRC_DB_USER}`, `${SRC_DB_PASS}` and `${TGT_DB_HOST}`, etc.
- **High-Throughput PDI Performance Tuning**:
  - **Commit Size**: set `Commit size` on `Table Output` / `Insert / Update` to `1000`–`5000` (never `1` or `0` unbounded).
  - **Enable Batch Mode**: check `Use batch update for inserts` on `Table Output` and enable `rewriteBatchedStatements=true` (MySQL) or `reWriteBatchedInserts=true` (PostgreSQL JDBC driver) for 10x–30x faster bulk writes.
  - **Push Down to SQL**: perform filtering (`WHERE updated_at >= '${LAST_WATERMARK}'`), projections, and same-database joins inside the `Table Input` SQL query rather than pulling millions of rows into PDI `Filter Rows` or `Merge Join`.
  - **Lookup Sizing**: use `Stream Lookup` (in-memory hash map) when the reference dimension table is small (<100k rows); use `Database Lookup` with cache enabled + indexed lookup keys when the dimension table is huge.
  - **Error Handling Hops**: attach a red **Error Handling Hop** from `Table Output` / `Insert / Update` / `Select Values` to a `Text File Output` or `Table Output (etl_quarantine_rows)` capturing `err_count`, `err_desc`, `err_field`, and `err_code` so 1 bad row does not crash a 500,000-row batch.
- **Headless CLI Execution (Cron / Systemd / Windows Task Scheduler)**:
  - Linux Cron: `0 * * * * /opt/data-integration/kitchen.sh -file="/etl/jobs/master_sync.kjb" -level=Basic >> /var/log/pdi/master_sync_$(date +\%F).log 2>&1`
  - Windows Task Scheduler / PowerShell: `C:\data-integration\kitchen.bat /file:"D:\etl\jobs\master_sync.kjb" /level:Basic /logfile:"D:\etl\logs\master_sync.log"`
  - Always check `$LASTEXITCODE` / `$?` (`0` = success, `1` = processing error, `2` =init error, `7`/`8`/`9` = load/command error).

## 3. Modern Orchestrators: Apache Airflow, Cron & Application Schedulers

- **Apache Airflow DAG Authoring**:
  - Set `catchup=False` by default unless historical backfilling is explicitly designed and idempotent.
  - Set `max_active_runs=1` to prevent overlapping DAG runs on slow warehouse loads.
  - Configure `retries=3`, `retry_delay=timedelta(minutes=5)`, `retry_exponential_backoff=True`, and `execution_timeout=timedelta(minutes=45)`.
  - **Never pass large DataFrames through XCom** (XCom is for small metadata like watermark timestamps, S3/MinIO object paths, or row counts). Write data directly from source to staging/warehouse or Parquet in object storage.
- **Application-Level Cron (`node-cron`, `BullMQ`, `gocron`, `APScheduler`)**:
  - Always specify an explicit IANA timezone (e.g. `timezone: 'Asia/Jakarta'`) so schedules do not shift by 7 hours when deployed to UTC containers.
  - Wrap every scheduled handler in a structured `try / catch / finally` that records job telemetry (`duration_ms`, `rows_affected`, `status`) and releases the advisory lock in `finally`.
  - Provide a manual trigger CLI or Admin endpoint (`--run-once` / `--dry-run`) so engineers can test the job without waiting for midnight.

## 4. Streaming, Memory & Schema Cleansing Discipline

- **Never load unbounded datasets into RAM**: stream large CSV, JSONL, Excel, or DB cursors in chunks of `1,000`–`5,000` rows.
- **Strict Type Normalization across Engines**:
  - **Money & Decimals**: map to `NUMERIC(18, 4)` / `DECIMAL(18, 4)`; never use `FLOAT`/`REAL` for financial columns.
  - **Timestamps**: normalize to UTC `TIMESTAMPTZ` / `DATETIME(3)` / `DateTime64(3)` (ClickHouse).
  - **Identifiers with Leading Zeros**: keep NIK, NPWP, phone numbers, postal codes, and invoice numbers as `VARCHAR`/`TEXT`.
- **CSV Injection & Atomic Writes**: neutralize leading `=`, `+`, `-`, `@` in spreadsheet exports and write files to `.tmp` before atomic rename.

## 5. Anti-patterns

Hardcoding production DB credentials inside `.ktr`/`.kjb` XML · running a 5-minute Cron job without an overlap lock (`pg_try_advisory_lock`) · using PDI `Table Output` without batch mode or error hop · passing 100MB datasets via Airflow XCom · `SELECT *` loading millions of rows into memory · mutating production tables without a watermark ledger or `--dry-run` mode.
