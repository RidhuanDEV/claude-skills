---
name: shadow-data
description: Data Lifecycle Engineering: Zero-Downtime Expand-Contract Schema Migrations, Deterministic Seeding, Safe Backfills, Bulk Import/Export Streaming, Transaction Integrity (ACID/Locking), and Data Retention/Archival. Pairs with /shadow-db. Trigger with /shadow-data.
---

# Shadow Data (`/shadow-data`) — Data Lifecycle, Safe Migrations & Transaction Integrity

While `/shadow-db` handles live database introspection, ERDs, and Data Warehouse/Pentaho generation, use **`/shadow-data`** whenever managing **how data changes, moves, and stays consistent** throughout the application's lifecycle.

---

## 1. Zero-Downtime Schema Migration Pattern (Expand -> Migrate -> Contract)

Never run destructive or table-locking DDL (`DROP COLUMN`, `RENAME COLUMN`, adding `NOT NULL` without default on huge tables) in a single deployment while old application instances are still serving traffic.

| Phase | Action | Compatibility Guarantee |
| :--- | :--- | :--- |
| **1. Expand** | Add new nullable column/table; add indexes concurrently (`CREATE INDEX CONCURRENTLY` in Postgres); deploy code that dual-writes to both old and new columns. | Old and new code versions both run safely; instant code rollback is 100% safe. |
| **2. Backfill** | Run a batched, throttled backfill script (`LIMIT 1000` per transaction with short sleep) to populate historical rows without locking the table or blowing up WAL replication lag. | Zero table lock; zero impact on live OLTP latency. |
| **3. Switch & Validate** | Enforce `NOT NULL` (using `CHECK (...) NOT VALID` then `VALIDATE CONSTRAINT`), switch reads to the new column. | Verified 100% data completeness before switching. |
| **4. Contract** | Remove dual-write code and drop the obsolete column in a subsequent release. | Clean schema with zero downtime. |

---

## 2. Transaction Integrity & Concurrency Control

1. **Atomic Multi-Step Writes**:
   - Wrap related writes (e.g., creating an order, decrementing inventory, and inserting an outbox event) inside a single database transaction (`BEGIN ... COMMIT`).
   - **Never perform external network/HTTP/SMTP calls inside an open DB transaction**, as slow external responses hold row locks and exhaust the DB connection pool.
2. **Preventing Lost Updates & Race Conditions**:
   - For financial balances, stock counts, and quota deductions, use atomic SQL updates (`UPDATE wallets SET balance = balance - $1 WHERE id = $2 AND balance >= $1`), pessimistic row locks (`SELECT ... FOR UPDATE`), or optimistic concurrency (`version = version + 1 WHERE id = $1 AND version = $2`).
3. **Monetary & Numeric Precision**:
   - Never store currency or exact quantities as `FLOAT` / `DOUBLE` / JS `number` floats. Use integer minor units (`BIGINT` cents/rupiah) or `NUMERIC(18, 2)`.

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
