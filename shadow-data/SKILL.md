---
name: shadow-data
description: "Application Data Lifecycle & Migrations. Use when writing zero-downtime Expand-Contract database migrations, deterministic seeds, safe backfills, bulk import/export streaming, or ACID transaction locking. Do NOT use for live DB introspection or Pentaho/DW ETL (/shadow-db)."
---

# Shadow Data (`/shadow-data`) — Data Lifecycle, Safe Migrations & Transaction Integrity

While `/shadow-db` handles live database introspection, ERDs, and Data Warehouse/Pentaho generation, use **`/shadow-data`** whenever managing **how data changes, moves, and stays consistent** throughout the application's lifecycle.

---

## 1. Zero-Downtime Schema Migration Pattern (Expand -> Migrate -> Contract)

Never run destructive or table-locking DDL (`DROP COLUMN`, `RENAME COLUMN`, adding `NOT NULL` without default on huge tables) in a single deployment while old application instances are still serving traffic.

| Phase | Action | Evidence before proceeding |
| --- | --- | --- |
| Expand | Inspect engine/version, DDL locking and mixed-version writers. Add compatible structures first. | Exercise current and previous application versions and verify rollback with both writing. |
| Backfill | Use resumable batches with stable keys. Set size and pause thresholds against observed lock wait, replica lag and latency budgets. | Interrupt and resume one batch. Reconcile row counts and values, including writes concurrent with backfill. |
| Switch | Enable the new read path within the authorized rollout and compare results. | Record parity, monitored window, owner and tested read fallback. |
| Contract | Inventory old readers, writers, jobs and rollback versions. Retire the old representation only after the retention window, owner decision and separate destructive-change authorization. | Missing telemetry or an external consumer with unknown status holds the contract phase. |

- **Ephemeral Migration Verification Container Cleanup**: Whenever verifying migrations against an ephemeral Docker database (`*-migration-verification` / `*-test-*`), always launch with `docker run --rm --label shadow.ephemeral=true` and wrap the run in `try / finally` (`trap EXIT`) executing `docker rm -f -v <container>` (or `docker compose -p <project>-migtest down -v --rmi local --remove-orphans`) so zero stopped containers, volumes, or temporary images remain after verification passes.

---

## 2. Transaction Integrity & Concurrency Control

1. **Atomic Multi-Step Writes**:
   - Wrap related writes (e.g., creating an order, decrementing inventory, and inserting an outbox event) inside a single database transaction (`BEGIN ... COMMIT`).
   - **Never perform external network/HTTP/SMTP calls inside an open DB transaction**, as slow external responses hold row locks and exhaust the DB connection pool.
2. **Preventing Lost Updates & Race Conditions**:
   - For financial balances, stock counts, and quota deductions, use atomic SQL updates (`UPDATE wallets SET balance = balance - $1 WHERE id = $2 AND balance >= $1`), pessimistic row locks (`SELECT ... FOR UPDATE`), or optimistic concurrency (`version = version + 1 WHERE id = $1 AND version = $2`).
3. **Monetary & Numeric Precision**:
   - Never store currency or exact quantities as `FLOAT` / `DOUBLE` / JS `number` floats. Use integer minor units (`BIGINT` cents/rupiah) or `NUMERIC(18, 2)`.
4. **Isolation Anomalies, Lock Budgets & Outbox/CDC Boundary**:
   - Explicitly match transaction isolation level (`READ COMMITTED` + atomic `UPDATE ... WHERE` or `SERIALIZABLE` with retry on `40001` / `40P01`) against read-skew, write-skew, and phantom-read hazards.
   - Set explicit `lock_timeout` and `statement_timeout` on online DDL/backfill sessions so migrations never queue behind slow queries and block production traffic.
   - Coordinate durable outbox/CDC event inserts inside the same transaction with `/shadow-concurrency`.

---

## 3. Deterministic Seeding & Bulk Import/Export Rules

1. **Idempotent Seeding (`db:seed`)**:
   - Seed scripts must use `UPSERT` (`ON CONFLICT DO UPDATE` / `ON DUPLICATE KEY UPDATE`) so running `db:seed` multiple times never fails with duplicate key errors or creates duplicate master rows.
   - Separate **System Reference Seeds** (roles, permissions, regions, status codes — safe for production) from **Demo/Dummy Seeds** (fake users/orders — strictly blocked when `NODE_ENV=production`).
2. **Safe Bulk Import & Export**:
   - **Imports (CSV/Excel)**: Validate all rows against schema rules first, report exact row/column line errors to the user, and insert in bounded batches (`500–1,000` rows per batch).
   - **Exports**: Stream large datasets via cursor/chunked queries rather than loading $100,000+$ ORM objects into RAM at once.

---

## 4. Data Retention, Archival & Soft-Delete Hygiene

- When using soft deletes (`deleted_at TIMESTAMPTZ`), remember that unique constraints must use partial indexes (`CREATE UNIQUE INDEX ... WHERE deleted_at IS NULL`) so a deleted email/code can be reused later.
- Define archival/retention policies for high-growth log/telemetry tables (e.g., monthly declarative partitioning `PARTITION BY RANGE (created_at)`).

---

## 5. Execution Approval & Migration Boundary (`L1` vs `L4`)
- Authoring additive Expand-only migrations locally is `L1_SAFE_VERIFICATION`. Running destructive DDL (`DROP`, `TRUNCATE`, `RENAME`, `migrate reset`) or executing migrations against staging/production/unknown databases is **`L4: HIGH_IMPACT`** and NEVER authorized by a bug fix without explicit Monarch approval and verified backup/rollback (`shadow-monarch/scripts/execution_approval_gate.py`).

Run the isolated SQLite example with `python -m unittest discover -s tests` from this skill directory. It shows how a legacy writer can invalidate rows behind a completed cursor and how to detect it. Production lock behavior, replicas and independent consumers require evidence from the owning environment.

## Deep Engineering Reference (Load On-Demand)
- For lock-safe zero-downtime DDL (`lock_timeout`, `CREATE INDEX CONCURRENTLY`, `NOT VALID` constraints, `pg_repack`, `gh-ost`), throttled keyset backfills, CDC (`Debezium`) vs outbox, and UU PDP/GDPR erasure tombstone/crypto-shredding -> read [Online DDL, chunked backfills & CDC](references/online-ddl-and-cdc.md).
