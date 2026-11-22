# 03. Chunked Resumable Backfills & Reconciliation

## 1. Purpose & Activation Conditions
Backfill millions of rows safely on live production databases with **keyset cursor batching**, **replica-lag & lock throttling**, **resumable checkpoints**, **concurrent legacy-writer drift detection**, and **provable reconciliation**. Load whenever populating new columns, migrating table layouts, or repairing historical data at scale.

## 2. Prerequisites
- Expanded schema + dual-write/trigger active (`01`), primary/unique stable cursor key (`id`), and verified `L4` execution authorization before touching staging/prod data.

## 3. Technical Principles & Constraints
- **NEVER Run Single-Transaction Full-Table `UPDATE`s:** Running `UPDATE orders SET currency = 'IDR' WHERE currency IS NULL` across 10M rows holds millions of row locks, doubles table disk size via MVCC dead tuples, stalls autovacuum, and triggers multi-minute read-replica lag!
- **6 Mandatory Production Backfill Invariants:**
  1. **Keyset Cursor Pagination Only:** Scan via `WHERE id > $cursor ORDER BY id ASC LIMIT $batchSize` (`O(log N)` constant) — NEVER `OFFSET` (`O(N^2)` sequential scans!).
  2. **Bounded Batch Size (`500–2,000` rows):** Commit each tiny batch in its own short transaction (`< 100ms`) with `SET LOCAL lock_timeout = '2s'`.
  3. **Adaptive Throttling & Autovacuum Breathing Room:** Sleep `50–250ms` between batches AND dynamically throttle/pause whenever **read-replica lag exceeds threshold** (e.g., `> 2s`) or DB CPU / lock waits spike!
  4. **Durable Resumable Checkpoint:** Persist `(job_id, last_completed_id, rows_processed, updated_at)` in a control table after each batch so crashes, deploys, or pauses resume cleanly with zero duplicate work (`idempotent WHERE new_col IS NULL`).
  5. **Mixed-Version Legacy-Writer Protection (CRITICAL):** If an older running app pod updates a row *behind* your completed keyset cursor without populating the new column (missing dual-write/trigger), your single-pass cursor misses it silently! Prevent this via a DB sync trigger (`01`) OR a **trailing reconciliation sweep** (`WHERE new_col IS NULL OR new_col != expected(old_col)`) proven in `shadow-data/tests/test_expand_backfill.py`!
  6. **Quantitative Reconciliation Gate Before Switch:** Confirm `missing_count === 0`, `mismatch_count === 0`, and exact `SUM(old) === SUM(new)` before flipping application reads!

## 4. Architecture & Implementation
```typescript
export interface BackfillMetrics {
  readonly replicaLagMs: number;
  readonly activeLockWaits: number;
}

export interface BackfillRunnerOptions {
  readonly startCursor: string;
  readonly batchSize: number;
  readonly basePauseMs: number;
  readonly maxReplicaLagMs: number;
  readonly fetchBatchAfterId: (lastId: string, limit: number) => Promise<readonly { readonly id: string }[]>;
  readonly updateBatchIdempotently: (ids: readonly string[]) => Promise<number>;
  readonly saveCheckpoint: (cursorId: string, totalUpdated: number) => Promise<void>;
  readonly readDbHealth: () => Promise<BackfillMetrics>;
}

export async function runThrottledResumableBackfill(opts: BackfillRunnerOptions): Promise<{
  readonly lastCursor: string;
  readonly totalUpdated: number;
  readonly throttlePauses: number;
}> {
  let cursor = opts.startCursor;
  let totalUpdated = 0;
  let throttlePauses = 0;

  while (true) {
    const health = await opts.readDbHealth();
    if (health.replicaLagMs > opts.maxReplicaLagMs || health.activeLockWaits > 3) {
      throttlePauses += 1;
      await new Promise<void>((resolve) => setTimeout(resolve, Math.max(opts.basePauseMs * 4, 500)));
      continue;
    }

    const batch = await opts.fetchBatchAfterId(cursor, opts.batchSize);
    if (batch.length === 0) break;

    const ids = batch.map((r) => r.id);
    totalUpdated += await opts.updateBatchIdempotently(ids);

    const last = batch[batch.length - 1];
    if (!last) break;
    cursor = last.id;
    await opts.saveCheckpoint(cursor, totalUpdated);
    await new Promise<void>((resolve) => setTimeout(resolve, opts.basePauseMs));
  }

  return { lastCursor: cursor, totalUpdated, throttlePauses };
}
```
Post-backfill reconciliation & drift-detection query:
```sql
-- Must return missing_new = 0 AND value_mismatch = 0 across full table before switching reads!
SELECT
  COUNT(*) AS total_rows,
  COUNT(*) FILTER (WHERE total_minor IS NULL AND legacy_total_decimal IS NOT NULL) AS missing_new,
  COUNT(*) FILTER (WHERE total_minor IS DISTINCT FROM ROUND(legacy_total_decimal * 100)::BIGINT) AS value_mismatch,
  COALESCE(SUM(total_minor), 0) AS sum_new_minor,
  COALESCE(SUM(ROUND(legacy_total_decimal * 100)::BIGINT), 0) AS sum_legacy_minor
FROM orders;
```

## 5. Platform / Vendor Variations
| Scale Tier | Recommended Backfill Strategy | Extra Safeguard |
| :--- | :--- | :--- |
| **`< 100k` rows** | Single script with `1,000`-row keyset loop + `50ms` sleep | Run inside maintenance-safe app job with `lock_timeout = '3s'` |
| **`1M–50M` rows** | Dedicated resumable worker with `backfill_checkpoints` table + live `pg_stat_replication` lag throttle | Trigger manual `VACUUM` periodically if autovacuum lags behind dead tuples |
| **`> 100M` rows** | Partitioned parallel workers on non-overlapping ID/time ranges | Cap total DB write IOPS `< 30%` of primary headroom |

## 6. Decision Matrix & Trade-Offs
| Backfill Update Style | Idempotent on Re-Run? | Dead-Tuple Bloat | Recommendation |
| :--- | :---: | :---: | :--- |
| `UPDATE tbl SET new_col = ... WHERE id = ANY($1) AND new_col IS DISTINCT FROM ...` | **YES (skips unchanged rows!)** | Minimal | **Always include `IS DISTINCT FROM` guard!** |
| `UPDATE tbl SET new_col = ... WHERE id = ANY($1)` (unconditional) | Rewrites already-migrated rows | 2x unnecessary WAL + dead tuples | Avoid |

## 7. Real Production Scenario
During a 12M-row backfill, a legacy v1 worker updates 430 older orders *behind* the backfill cursor, overwriting `legacy_total_decimal` without updating `total_minor`. Because the engineer assumed `"cursor reached MAX(id) == 100% migrated"` without running reconciliation, switching reads served stale invoice totals for 430 customers! Running the reconciliation query (`value_mismatch = 430`) + enabling the Expand sync trigger (`01`) + running a targeted repair sweep catches and fixes 100% of drifted rows before cutover (`shadow-data/tests/test_expand_backfill.py`).

## 8. Failure Modes & Edge Cases
- **WRONG:** Running backfill inside a schema migration tool (`prisma migrate deploy`) on container startup (times out readiness probes, triggers Kubernetes crash-looping, and leaves migrations half-applied!).
- **RIGHT:** Keep DDL migrations fast (`< 5s` metadata only) and run data backfills asynchronously via dedicated resumable CLI/worker jobs!
- **WRONG:** Skipping the `WHERE new_col IS DISTINCT FROM ...` clause (re-updating already-backfilled rows wastes WAL I/O and triggers unnecessary replication lag).
- **RIGHT:** Always guard updates with `IS DISTINCT FROM` so resumed runs are fast no-ops on completed rows.

## 9. Testing & Verification
- Run `python shadow-data/scripts/data_migration_plan_verifier.py --check-backfill-plan <plan.json>`.
- Run `python -m unittest discover -s shadow-data/tests -v` (`test_expand_backfill.py` explicitly demonstrates legacy-writer invalidation behind the cursor and its detection!).

## 10. Operational Considerations
- Expose a live kill-switch / pause flag (`backfill_jobs.paused = true`) checked on every loop iteration so on-call SRE can pause a running backfill in `< 1 second` if production latency rises.

## 11. Authoritative References
- Stripe Engineering — *Online Migrations at Scale* (Dual-Write, Backfill & Reconciliation).
- PostgreSQL Documentation — *Monitoring Replication Lag (`pg_stat_replication`)* (`https://www.postgresql.org/docs/current/monitoring-stats.html`).

## 12. Limitations & When NOT to Use
- Local SQLite unit tests (`test_expand_backfill.py`) verify logical cursor/reconciliation correctness, NOT production PostgreSQL MVCC lock waits or replication lag — always measure real lock/lag budgets on staging-scale clones before production execution.
