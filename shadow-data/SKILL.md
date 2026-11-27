---
name: shadow-data
description: "Use when planning zero-downtime migrations, large backfills, expand-contract, retention, or lineage. Not for query tuning (/shadow-db)."
---

# Shadow Data (`/shadow-data`) — Zero-Downtime Migrations, Backfills & Data Lifecycle

Use this skill whenever the **Monarch** manages how application data evolves, moves, backfills, seeds, streams, or stays ACID-consistent across live deployments (while `/shadow-db` owns live DB inspection, ERDs, `EXPLAIN` tuning, RLS, and DW/Pentaho ETL).

## 1. Core Data Lifecycle Principles & Non-Negotiables

1. **Zero-Downtime Expand-Contract Migrations:** Never run single-step `DROP COLUMN`, `RENAME COLUMN`, `ALTER COLUMN TYPE`, or blocking `ADD CONSTRAINT` while old pods still serve traffic. Execute **Expand** (additive + dual-write/trigger, rollback-tested) -> **Backfill** (throttled keyset cursor + legacy-writer parity + reconciliation) -> **Switch Reads** (monitored parity) -> **Contract** (only after `0` legacy consumers verified AND separate **`L4`** destructive approval).
2. **Lock Budgets & Online DDL:** Prefix DDL sessions with `SET lock_timeout = '3s'; SET statement_timeout = '30s';`, build indexes `CONCURRENTLY` outside transactions, validate FKs/`CHECK`s via `NOT VALID` -> `VALIDATE CONSTRAINT`, and use `pg_repack` / `gh-ost` instead of `VACUUM FULL`.
3. **ACID Monetary Integrity & Zero Network I/O in Transactions:** Store money as `BIGINT` minor units or `NUMERIC(19,4)` (never `FLOAT`), use atomic conditional `UPDATE ... WHERE balance >= $1` / deterministic `ORDER BY id ASC FOR UPDATE` / CAS `version` + retry on `40001`/`40P01`, and NEVER perform HTTP/SMTP calls inside an open DB transaction.
4. **CDC Safety, Idempotent Seeds & Streaming Bulk I/O:** Always cap logical replication WAL with `max_slot_wal_keep_size`, guard projection upserts with monotonic `source_version`, separate idempotent `UPSERT` system seeds from prod-blocked demo seeds, stream large CSV exports with formula-injection neutralization, and clean up ephemeral Docker test DBs (`--rm --label shadow.ephemeral=true` + `try/finally`).
5. **Execution Approval Boundary (`L1` vs `L4`):** Authoring additive Expand migrations locally is `L1`; running destructive DDL (`DROP`/`TRUNCATE`/`RENAME`/`migrate reset`) or mutating staging/prod/unknown DBs is **`L4_HIGH_IMPACT`** requiring explicit Monarch approval + verified backup.

## 2. Deterministic Verification CLI & Scenario Benchmarks

Run offline checks (`L0`/`L1`) before claiming `VERIFIED-LOCAL`:
```powershell
python "shadow-data/scripts/data_migration_plan_verifier.py" --self-test
python "shadow-data/scripts/data_migration_plan_verifier.py" --check-backfill-plan path/to/backfill.json
python "shadow-data/scripts/data_migration_plan_verifier.py" --check-migration-phases path/to/phases.json
python "shadow-data/scripts/data_migration_plan_verifier.py" --check-seed-safety path/to/seed.json
python -m unittest discover -s "shadow-data/tests" -v
```
Notice `shadow-data/tests/test_expand_backfill.py` runs an isolated SQLite simulation proving how concurrent legacy writers invalidate rows behind a completed backfill cursor and how reconciliation catches it (production lock/replica behavior still requires staging evidence). Graded scenarios live in [evaluations.md](evaluations.md) (8 scenarios).

## Reference Guide

Load **only** the 1–2 modules matching the active subtask (never load all 6 at once):

| Task / Scenario | Tier | Load Reference |
| :--- | :--- | :--- |
| 4-phase Expand -> Backfill -> Switch -> Contract, dual-write/triggers & Docker cleanup | CORE | [references/01-expand-contract-zero-downtime-migrations.md](references/01-expand-contract-zero-downtime-migrations.md) |
| Lock-safe DDL (`lock_timeout`, `CONCURRENTLY`, `NOT VALID`, `pg_repack`, MySQL `gh-ost`) | CORE | [references/02-online-ddl-lock-budgets-and-repack.md](references/02-online-ddl-lock-budgets-and-repack.md) |
| Keyset-chunked resumable backfills, replica-lag throttling, legacy-writer drift & reconciliation | CORE | [references/03-chunked-resumable-backfills-and-reconciliation.md](references/03-chunked-resumable-backfills-and-reconciliation.md) |
| ACID balances/stock (`BIGINT`), atomic updates, `40001`/`40P01` retries & zero I/O in tx | CORE | [references/04-acid-transactions-money-and-concurrency.md](references/04-acid-transactions-money-and-concurrency.md) |
| Transactional Outbox vs Debezium CDC, `max_slot_wal_keep_size` & monotonic upserts | ADVANCED | [references/05-cdc-outbox-and-event-time-pipelines.md](references/05-cdc-outbox-and-event-time-pipelines.md) |
| Idempotent system vs prod-blocked demo seeds, streaming CSV/formula defense & partition retention | OPERATIONAL | [references/06-deterministic-seeds-bulk-io-and-retention.md](references/06-deterministic-seeds-bulk-io-and-retention.md) |

Do not load unrelated references unnecessarily.
