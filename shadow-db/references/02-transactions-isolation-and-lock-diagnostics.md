# 02. Transactions, Isolation Levels & Lock Diagnostics

## 1. Purpose & Activation Conditions
Prevent concurrency anomalies (lost updates, write skew, deadlocks, lock-queue outages) by selecting the right SQL isolation level, enforcing lock-ordering invariants, and diagnosing live lock chains via `pg_locks` and `pg_stat_activity`. Load when debugging deadlocks, race conditions, or blocked migrations.

## 2. Prerequisites
- Read-only diagnostic access (`shadow_db` MCP `run_readonly_query` on verified local/dev DBs) and clear transactional boundaries (`/shadow-data`).

## 3. Technical Principles & Constraints
- **Understand MVCC & Isolation Anomalies (PostgreSQL Defaults to `READ COMMITTED`):**
  - **`READ COMMITTED`:** Readers never block writers and writers never block readers, **BUT** read-then-write in app code (`SELECT balance -> compute -> UPDATE`) suffers **Lost Updates**! Fix via atomic `UPDATE ... SET balance = balance - $1 WHERE id = $2 AND balance >= $1`, `SELECT ... FOR UPDATE`, or CAS `WHERE version = $expected`.
  - **`REPEATABLE READ` (Snapshot Isolation):** Prevents non-repeatable reads and phantom reads in PostgreSQL, **BUT** still permits **Write Skew** (two transactions read disjoint rows from the same snapshot and both violate a cross-row invariant, e.g., two doctors going off-call simultaneously!).
  - **`SERIALIZABLE` (SSI):** Prevents write skew completely; requires **mandatory application retry loop** on PostgreSQL `SQLSTATE 40001` (`serialization_failure`)!
- **Deadlock Prevention Invariant (`SQLSTATE 40P01`):** Deadlocks occur when Tx1 locks Row A then waits for Row B while Tx2 locks Row B then waits for Row A. Eliminate deadlocks structurally by acquiring locks in a **strictly deterministic canonical order** (`ORDER BY id ASC FOR UPDATE`) AND keeping transactions ultra-short (ZERO external HTTP/SMTP/LLM calls inside `BEGIN ... COMMIT`!).
- **Lock-Queue Pileup Defense (`SET lock_timeout`):** An `ALTER TABLE` needing `ACCESS EXCLUSIVE` lock will wait behind a 20-second reporting `SELECT`, AND **every new incoming `SELECT`/`INSERT` queues behind the waiting `ALTER TABLE`** — freezing the entire production app! ALWAYS set `SET lock_timeout = '3s'` on DDL so migrations abort cleanly instead of queueing live traffic!
- **Idle-in-Transaction Hygiene:** Set `idle_in_transaction_session_timeout = '15s'` and `statement_timeout = '10s'` on OLTP app roles so crashed/buggy clients cannot hold row locks and stall autovacuum indefinitely.

## 4. Architecture & Implementation
```sql
-- 1. Read-Only Live Blocking-Lock & Idle-in-Transaction Diagnostic Query (PostgreSQL)
SELECT
  blocked.pid AS blocked_pid,
  blocked.usename AS blocked_user,
  blocking.pid AS blocking_pid,
  blocking.state AS blocking_state,
  NOW() - blocking.xact_start AS blocking_tx_age,
  LEFT(blocked.query, 120) AS blocked_query,
  LEFT(blocking.query, 120) AS blocking_query
FROM pg_catalog.pg_locks blocked_locks
JOIN pg_catalog.pg_stat_activity blocked ON blocked.pid = blocked_locks.pid
JOIN pg_catalog.pg_locks blocking_locks
  ON blocking_locks.locktype = blocked_locks.locktype
 AND blocking_locks.database IS NOT DISTINCT FROM blocked_locks.database
 AND blocking_locks.relation IS NOT DISTINCT FROM blocked_locks.relation
 AND blocking_locks.page IS NOT DISTINCT FROM blocked_locks.page
 AND blocking_locks.tuple IS NOT DISTINCT FROM blocked_locks.tuple
 AND blocking_locks.virtualxid IS NOT DISTINCT FROM blocked_locks.virtualxid
 AND blocking_locks.transactionid IS NOT DISTINCT FROM blocked_locks.transactionid
 AND blocking_locks.pid != blocked_locks.pid
JOIN pg_catalog.pg_stat_activity blocking ON blocking.pid = blocking_locks.pid
WHERE NOT blocked_locks.granted;

-- 2. Deadlock-Free Deterministic Lock Ordering for Two-Account Ledger Transfer
BEGIN;
SELECT id, balance_minor
FROM wallets
WHERE tenant_id = $1 AND id IN ($2, $3)
ORDER BY id ASC
FOR UPDATE;
-- Now debit source (verifying balance >= amount) and credit destination safely
COMMIT;
```

## 5. Platform / Vendor Variations
| Engine | Default Isolation | Lock Behavior Caveat |
| :--- | :--- | :--- |
| **PostgreSQL** | `READ COMMITTED` | True MVCC; `FOR UPDATE` locks rows without gap locks; `40001`/`40P01` require retry |
| **MySQL 8 (InnoDB)** | `REPEATABLE READ` | Uses **Next-Key / Gap Locks** on range updates/selects `FOR UPDATE`, which cause unexpected deadlocks on concurrent inserts! |
| **SQL Server (MSSQL)** | `READ COMMITTED` (locking unless `RCSI` enabled!) | Without `READ_COMMITTED_SNAPSHOT ON`, readers can block writers |

## 6. Decision Matrix & Trade-Offs
| Concurrency Hazard | Best DB Mechanism | App Retry Required? |
| :--- | :--- | :---: |
| Single-row balance/stock decrement | Atomic `UPDATE ... WHERE balance >= $1` | No |
| Two-row transfer (`A -> B`) | `SELECT ... WHERE id IN ($a,$b) ORDER BY id ASC FOR UPDATE` | Yes (`40P01` safety retry) |
| Competing background job workers | `SELECT ... FOR UPDATE SKIP LOCKED LIMIT $n` | No |
| Cross-row invariant (`>= 1` doctor on call) | `SERIALIZABLE` (or parent lock row `FOR UPDATE`) | **YES (`40001`)** |
| Low-contention user form edits | Optimistic CAS (`WHERE id = $1 AND version = $2`) | Client reloads on `409` |

## 7. Real Production Scenario
During peak payroll disbursement, concurrent wallet transfers between paired merchant accounts randomly fail with `ERROR: deadlock detected (40P01)` while an unrelated migration (`ALTER TABLE orders ADD CONSTRAINT fk_...`) waits behind an analytics query and freezes checkout for 4 minutes. Locking paired wallets via `ORDER BY id ASC FOR UPDATE`, separating analytics onto a read replica, and enforcing `SET lock_timeout = '3s'` + `NOT VALID` constraints resolves both incidents permanently.

## 8. Failure Modes & Edge Cases
- **WRONG:** Opening `BEGIN;`, calling Stripe/Midtrans HTTP API (`3–8 seconds`), then running `COMMIT;` (holds DB connections & row locks hostage during network latency and collapses the pool!).
- **RIGHT:** Commit `PENDING` + outbox row in `< 10ms`, close transaction, execute external HTTP call outside any DB transaction, then finalize in a second short transaction.
- **WRONG:** Wrapping `SERIALIZABLE` transactions without catching and retrying `SQLSTATE 40001`.
- **RIGHT:** Implement bounded exponential-jitter retries (`<= 3–5` attempts) specifically for `40001` (serialization failure) and `40P01` (deadlock detected).

## 9. Testing & Verification
- Run `python shadow-db/scripts/sql_migration_safety_verifier.py --check-ddl <mig.sql>` to ensure `lock_timeout` and non-blocking DDL patterns are enforced.
- Write a local concurrency integration test spawning 10 parallel transfers (`A->B` and `B->A`) asserting `0` lost rupiah (`SUM(balances)` constant) and `0` unhandled deadlocks.

## 10. Operational Considerations
- Alert when `pg_stat_activity` shows any `idle in transaction` session `> 30s` or `wait_event_type = 'Lock'` count `> 5` sustained for `60s` (`/shadow-observe`).

## 11. Authoritative References
- PostgreSQL Documentation — *Chapter 13: Concurrency Control (Transaction Isolation & Explicit Locking)* (`https://www.postgresql.org/docs/current/mvcc.html`).
- Martin Kleppmann — *Designing Data-Intensive Applications* (Ch. 7: Transactions & Weak Isolation Levels).

## 12. Limitations & When NOT to Use
- Do NOT blindly set global `default_transaction_isolation = 'serializable'` on high-write OLTP workloads without retry wrappers and load profiling — it causes high abort rates on hot tables.
