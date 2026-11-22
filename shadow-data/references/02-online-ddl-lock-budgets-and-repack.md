# 02. Online DDL, Lock Budgets & Table Repacking

## 1. Purpose & Activation Conditions
Execute schema changes on busy production tables without causing lock-queue pileups, table rewrites, or connection-pool meltdowns — using `lock_timeout` retry wrappers, `CREATE INDEX CONCURRENTLY`, `NOT VALID` constraint validation, `pg_repack`, and MySQL `gh-ost`. Load before authoring or reviewing DDL migrations targeting hot tables.

## 2. Prerequisites
- Engine version awareness (PostgreSQL 11+ fast constant `ADD COLUMN ... DEFAULT`; PG 12+ `SET NOT NULL` using validated `CHECK`; MySQL 8 `ALGORITHM=INSTANT`), plus `/shadow-db` lock diagnostics.

## 3. Technical Principles & Constraints
- **Mandatory Lock & Statement Budgets:** Every production DDL session MUST begin with:
  `SET lock_timeout = '3s'; SET statement_timeout = '30s';`
  Why: Even a 1ms `ALTER TABLE` briefly requests `ACCESS EXCLUSIVE`. If a 40-second reporting query is running, an unbounded `ALTER TABLE` queues behind it — and **every incoming checkout query queues behind the `ALTER TABLE`**, causing an immediate full outage! Failing fast after `3s` and retrying with jitter avoids outages completely.
- **Non-Blocking PostgreSQL DDL Playbook:**
  - **Indexes:** ALWAYS `CREATE INDEX CONCURRENTLY` / `DROP INDEX CONCURRENTLY` outside any explicit `BEGIN ... COMMIT` block. If interrupted, inspect `pg_index.indisvalid = false` and drop the invalid index before retrying!
  - **Foreign Keys & `CHECK` Constraints:** ALWAYS split into two steps: (1) `ALTER TABLE child ADD CONSTRAINT fk_x FOREIGN KEY (parent_id) REFERENCES parent(id) NOT VALID;` (brief metadata lock only, blocks new bad writes immediately), then (2) `ALTER TABLE child VALIDATE CONSTRAINT fk_x;` (takes `SHARE UPDATE EXCLUSIVE` — reads/writes stay 100% online!).
  - **Bloat Reclaim Without Downtime:** NEVER run `VACUUM FULL` on a live production table (holds `ACCESS EXCLUSIVE` for minutes/hours!). Use **`pg_repack`** to rebuild bloated tables/indexes online!
- **MySQL 8 Online DDL (`ALGORITHM=INSTANT` vs `gh-ost`):** Prefer native `ALGORITHM=INSTANT` for additive trailing columns; for table-rebuilding MySQL alterations on huge tables (`> 10M` rows), use **`gh-ost`** (triggerless binlog-driven shadow-table swap with replica-lag throttling) instead of blocking `ALTER TABLE`.

## 4. Architecture & Implementation
```sql
-- Lock-Safe 2-Step Non-Null & Foreign Key Addition (PostgreSQL 12+, Zero Write Blocking)
SET lock_timeout = '3s';
SET statement_timeout = '30s';

-- Step 1: Add nullable column & create supporting FK index concurrently (run index outside tx!)
ALTER TABLE payments ADD COLUMN IF NOT EXISTS merchant_id UUID;
-- CREATE INDEX CONCURRENTLY idx_payments_merchant ON payments (merchant_id);

-- Step 2: After chunked backfill completes, attach constraints NOT VALID then VALIDATE online
ALTER TABLE payments
  ADD CONSTRAINT chk_payments_merchant_not_null CHECK (merchant_id IS NOT NULL) NOT VALID;
ALTER TABLE payments
  ADD CONSTRAINT fk_payments_merchant FOREIGN KEY (merchant_id) REFERENCES merchants (id) NOT VALID;

-- Step 3: Validate without blocking reads or writes (raise statement_timeout for scan, keep lock_timeout short)
SET statement_timeout = '15min';
ALTER TABLE payments VALIDATE CONSTRAINT chk_payments_merchant_not_null;
ALTER TABLE payments VALIDATE CONSTRAINT fk_payments_merchant;

-- Step 4 (PG 12+): Instantly promote validated CHECK into native NOT NULL & drop redundant CHECK
SET lock_timeout = '3s';
ALTER TABLE payments ALTER COLUMN merchant_id SET NOT NULL;
ALTER TABLE payments DROP CONSTRAINT chk_payments_merchant_not_null;
```

## 5. Platform / Vendor Variations
| Engine / Tool | Lock-Safe Mechanism | Specific Trap |
| :--- | :--- | :--- |
| **PostgreSQL 11+** | `ADD COLUMN ... DEFAULT <constant>` is instant metadata-only | **Volatile defaults** (`DEFAULT random()`, `uuid_generate_v4()` on old versions or expressions) still trigger full table rewrite! |
| **PostgreSQL (`pg_repack`)** | Online table/index bloat compaction | Requires `PRIMARY KEY` or `UNIQUE NOT NULL` index and free disk space `>= 2x` table size |
| **MySQL 8 (`gh-ost` / `pt-osc`)** | Shadow table + binlog cutover with `--max-lag-millis` throttle | Must verify foreign key constraints & triggers before running `gh-ost` |

## 6. Decision Matrix & Trade-Offs
| DDL Change | Safe Lock Mode | Safe Without Downtime? |
| :--- | :--- | :---: |
| `CREATE INDEX CONCURRENTLY` | `SHARE UPDATE EXCLUSIVE` | **YES** |
| `ADD CONSTRAINT ... NOT VALID` + `VALIDATE` | Brief `SHARE ROW EXCLUSIVE` -> `SHARE UPDATE EXCLUSIVE` | **YES** |
| `VACUUM FULL` / `CLUSTER` | `ACCESS EXCLUSIVE` (entire duration!) | **NO — use `pg_repack`** |
| `ALTER COLUMN TYPE` | `ACCESS EXCLUSIVE` (full rewrite!) | **NO — use Expand-Contract (`01`)** |

## 7. Real Production Scenario
A Prisma migration adds `ALTER TABLE transactions ADD COLUMN reference_code TEXT NOT NULL DEFAULT ''` AND `CREATE INDEX idx_tx_ref ON transactions(reference_code)` inside Prisma's default single transaction. On a 45M-row table, `CREATE INDEX` holds a `SHARE` lock for 9 minutes, halting every payment write nationwide. Splitting the index into a separate non-transactional `CREATE INDEX CONCURRENTLY` migration with `SET lock_timeout = '3s'` and validating via `sql_migration_safety_verifier.py` eliminates migration outages permanently.

## 8. Failure Modes & Edge Cases
- **WRONG:** Assuming a short `ALTER TABLE` can never hurt production because `"it finishes in 2 milliseconds on my laptop"`.
- **RIGHT:** Without `SET lock_timeout = '3s'`, even a 2ms `ALTER TABLE` waiting behind one long analytical `SELECT` blocks every new app query in the lock queue!
- **WRONG:** Leaving an `INVALID` index behind after a failed `CREATE INDEX CONCURRENTLY` (Postgres still pays write-maintenance cost on invalid indexes without using them for reads!).
- **RIGHT:** Always query `SELECT indexrelid::regclass FROM pg_index WHERE NOT indisvalid;` after concurrent index builds and `DROP INDEX CONCURRENTLY` any invalid remnants.

## 9. Testing & Verification
- Run `python shadow-db/scripts/sql_migration_safety_verifier.py --check-ddl <migration.sql>` in CI on EVERY new migration file before merge!
- Rehearse lock-timeout retry behavior in an ephemeral local Docker DB (`--rm --label shadow.ephemeral=true`) while a concurrent `SELECT pg_sleep(5)` holds a read lock.

## 10. Operational Considerations
- Wrap migration runners in a bounded retry loop (e.g., 5 attempts with 5–10s backoff) so a `lock_timeout` abort retries cleanly without manual engineer babysitting.

## 11. Authoritative References
- PostgreSQL Documentation — *Explicit Locking & Lock Modes* (`https://www.postgresql.org/docs/current/explicit-locking.html`).
- GitHub `gh-ost` Online Schema Migration (`https://github.com/github/gh-ost`).
- `pg_repack` Online Reorganization (`https://reorg.github.io/pg_repack/`).

## 12. Limitations & When NOT to Use
- `CREATE INDEX CONCURRENTLY` cannot run inside a multi-statement `BEGIN ... COMMIT` transaction block; split concurrent index migrations into standalone non-transactional migration files.
