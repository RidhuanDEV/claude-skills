# Online Zero-Downtime DDL, Chunked Backfills, CDC & Privacy Erasure

## 1. Core Concepts
Production data lifecycle engineering evolves live database schemas and migrates multi-million-row datasets with **zero downtime**, **bounded lock acquisition (`lock_timeout`)**, **idempotent keyset-chunked backfills**, **Change Data Capture (CDC)**, and **resurrection-proof privacy erasure**.

## 2. Technical Rules & Migration Selection Matrix

| Schema Operation | Lock-Safe Production Technique (PostgreSQL) | Forbidden Operation on Hot Tables |
| :--- | :--- | :--- |
| **Add Index** | `CREATE INDEX CONCURRENTLY idx_... ON tbl (...);` (outside tx block) | Plain `CREATE INDEX` (blocks all writes for minutes) |
| **Add Foreign Key / Check** | `ALTER TABLE ... ADD CONSTRAINT ... NOT VALID;` then `VALIDATE CONSTRAINT ...;` | Immediate `ADD CONSTRAINT` (takes `SHARE ROW EXCLUSIVE` full scan) |
| **Add Non-Null Column** | 1. Add nullable column -> 2. Backfill in chunks -> 3. Add `CHECK NOT NULL NOT VALID` -> 4. `VALIDATE` -> 5. `SET NOT NULL` (PG 12+) | `ADD COLUMN ... NOT NULL` without default or with volatile rewrite |
| **Rename / Change Column Type** | **Expand -> Dual-Write + Backfill -> Switch Reads -> Contract** across 2+ deploys | Direct `RENAME COLUMN` or `ALTER COLUMN TYPE` while old app pods run |

## 3. Implementation Examples
```sql
-- 1. Lock-Safe Online DDL Wrapper (Aborts Fast Instead of Queueing App Traffic Behind Lock)
SET lock_timeout = '3s';
SET statement_timeout = '30s';

ALTER TABLE orders ADD COLUMN IF NOT EXISTS currency_code VARCHAR(3);
ALTER TABLE orders
  ADD CONSTRAINT chk_orders_currency_not_null
  CHECK (currency_code IS NOT NULL) NOT VALID;
```
```ts
// 2. Idempotent Keyset-Paginated Backfill Loop with Throttle & Cursor Checkpoint
export async function runChunkedBackfill(
  fetchBatchAfterId: (lastId: string, limit: number) => Promise<ReadonlyArray<{ readonly id: string }>>,
  updateBatch: (ids: ReadonlyArray<string>) => Promise<number>,
  onCheckpoint: (lastId: string, totalUpdated: number) => Promise<void>,
  startCursor = '',
  batchSize = 1000,
  pauseMs = 75,
): Promise<number> {
  let cursor = startCursor
  let total = 0
  while (true) {
    const rows = await fetchBatchAfterId(cursor, batchSize)
    if (rows.length === 0) break
    const ids = rows.map((r) => r.id)
    total += await updateBatch(ids)
    const lastRow = rows[rows.length - 1]
    if (!lastRow) break
    cursor = lastRow.id
    await onCheckpoint(cursor, total)
    await new Promise<void>((resolve) => setTimeout(resolve, pauseMs))
  }
  return total
}
```

## 4. Best Practices
- For CDC (`Debezium` / PostgreSQL logical replication slots), always set `max_slot_wal_keep_size` in `postgresql.conf` so a stalled CDC consumer cannot fill 100% of primary disk with retained WAL segments.
- Persist an external **Erasure Tombstone Ledger** (respecting `legal_hold = true`) and replay tombstones immediately after any backup restore before re-enabling search or API traffic.

## 5. Anti-patterns (WRONG vs RIGHT)
- **WRONG:** Running `UPDATE orders SET currency_code = 'IDR' WHERE currency_code IS NULL;` in a single transaction across 10M rows (locks the table, bloats MVCC 2x, and stalls replication).
- **RIGHT:** Backfill in `1,000`-row keyset-paginated batches with a `50–200ms` throttle pause and replica-lag check.
- **WRONG:** Using `OFFSET 500000 LIMIT 1000` for batch jobs (degrades to `O(N^2)` sequential scans).
- **RIGHT:** Use keyset cursor pagination (`WHERE id > :last_id ORDER BY id ASC LIMIT 1000`).

## 6. Production Considerations
- Rehearse every migration + rollback + tombstone replay against a staging/ephemeral clone before production execution (`L4_HIGH_IMPACT` requires explicit approval).
