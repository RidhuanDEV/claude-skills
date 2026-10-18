# DATA-AUTOMATION — Scripting, ETL, Batch Processing & Data Pipelines

Use when building CLI tools, automation scripts, data migration scripts, ETL/ELT pipelines, CSV/Excel/JSON/Parquet
processors, scheduled cron jobs, or data validation and reporting utilities.

## 1. Core principles for scripts & pipelines

- **Idempotency is mandatory**: running a script or pipeline twice on the same input window must not duplicate rows,
  corrupt state, or double-send notifications. Use natural/deterministic upsert keys (`ON CONFLICT DO UPDATE`),
  watermarks, or processed-batch ledger tables.
- **Dry-run by default for mutating scripts**: any script that mutates databases, deletes files, or calls external APIs
  should support a `--dry-run` mode that logs the exact planned changes and summary counts before execution.
- **Fail explicitly and safely**: validate CLI arguments, input file existence, schema headers, and environment variables
  at startup before processing row 1.

## 2. Streaming, memory & batch discipline

- **Never load unbounded datasets into memory**: stream large CSV, JSONL, Excel, or DB result sets using iterators/streams
  (Node `stream/promises` + `readline`, Python generators / `polars` / chunked `pandas`, Go `bufio.Scanner`).
- **Chunked batch writes**: write to databases or APIs in bounded batches (e.g., 500–2,000 records per batch) rather than
  1 row at a time (too slow, N+1 network round-trips) or 1,000,000 rows in a single transaction (locks tables, OOM).
- **Bounded concurrency**: use worker pools / semaphores (`p-limit`, `asyncio.Semaphore`, Go worker channels) with rate
  limiting when enriching records via external APIs.

## 3. Schema validation & data cleansing

- **Treat every input file/feed as untrusted**:
  - Normalize encoding (UTF-8, strip BOM), trim whitespace, handle Windows CRLF vs LF line endings.
  - Validate every row against a strict schema (Zod, Pydantic, custom typed parser) before transformation.
- **Explicit data types**:
  - **Money & decimals**: parse into integer minor units or `Decimal` (`decimal.js`, Python `Decimal`); never use IEEE-754
    floating point (`number`/`float`) for currency aggregations.
  - **Dates & timezones**: parse with explicit format and timezone into UTC (`TIMESTAMPTZ` / ISO-8601); reject ambiguous
    `01/02/2026` strings unless locale is explicitly configured.
  - **Identifiers & leading zeros**: keep phone numbers, NIK/NPWP, postal codes, and SKU codes as `string`, never numeric
    (Excel/CSV parsers silently strip leading zeros and corrupt 16-digit IDs into scientific notation `1.23E+15`).
- **Quarantine / dead-letter handling**: decide upfront whether a malformed row aborts the entire transaction (all-or-nothing)
  or goes to a structured **rejected/quarantine report** (`row_number`, `raw_data`, `error_reason`) while valid rows proceed.

## 4. Excel / CSV / JSON export & reporting

- **CSV injection protection**: neutralize cells starting with `=`, `+`, `-`, `@`, `\t`, or `\r` when exporting
  user-supplied strings to CSV/Excel so opening the file in spreadsheet software cannot execute formulas.
- **Atomic file output**: write output files to a temporary path (`output.csv.tmp`) and rename atomically on completion
  so downstream consumers never read a half-written file from a crashed job.
- **Summary telemetry**: at the end of every run, emit a structured summary:
  `Total Read | Valid Processed | Inserted | Updated | Skipped (Unchanged) | Failed/Quarantined | Duration`.

## 5. Cross-platform shell & CLI ergonomics

- Respect the host OS: on Windows, write PowerShell-compatible commands or cross-platform Node/Python scripts; use
  path join utilities (`node:path`, `pathlib.Path`) instead of hardcoded `/` or `\`.
- Handle signals (`SIGINT`, `SIGTERM`): flush open file handles, roll back uncommitted transactions, and exit with a
  non-zero exit code on failure so schedulers/CI detect errors.

## 6. Anti-patterns

`SELECT *` loading millions of rows into RAM · row-by-row `INSERT` inside a `for` loop · parsing CSV with `.split(',')`
(breaks on quoted commas and newlines) · storing 16-digit IDs or phone numbers as integers/floats · silent `try/catch`
that skips failed rows without logging or counting them · mutating production data without `--dry-run` or backup verification.
