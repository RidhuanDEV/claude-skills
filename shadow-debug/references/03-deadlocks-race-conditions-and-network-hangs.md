# 03 — Deadlocks, Race Conditions, Pool Starvation & Silent Network Hangs

## 1. Purpose & Activation Conditions
Isolate and permanently eliminate concurrency failures — **PostgreSQL/InnoDB deadlocks**, **check-then-act lost updates**, **async worker double execution**, **connection pool exhaustion**, and **missing outbound HTTP timeouts / DNS hangs** — using lock-wait graphs and deterministic local barrier reproduction tests. Activate when investigating intermittent `40P01 deadlock detected`, duplicate charges/emails, hanging requests, or `pool acquire timeout` bugs.

## 2. Prerequisites
- Redacted error logs, W3C `traceparent` timelines, and (for DB locks) read-only (`L0`) lock-wait output (`pg_locks`/`pg_stat_activity` or InnoDB `SHOW ENGINE INNODB STATUS`).
- Local or ephemeral isolated database for deterministic concurrency barrier reproduction (`L1`).

## 3. Technical Principles & Constraints
- **Eliminate Deadlocks Structurally via Deterministic Lock Ordering:** Deadlocks occur when Transaction 1 locks row `A` then requests `B`, while Transaction 2 simultaneously locks `B` then requests `A` (cycle in wait-for graph). Fix structurally by ALWAYS acquiring multi-row locks in **strict ascending primary-key order** (`ORDER BY id ASC FOR UPDATE`) AND keeping transactions ultra-short (zero external HTTP calls inside DB transactions!).
- **Fix Check-Then-Act Races Atomically (Never In Application RAM):** Reading `balance = SELECT balance ...`, checking `if (balance >= amount)` in Node/Python, and running `UPDATE ... SET balance = balance - $1` allows two concurrent requests to both pass the `if` check and overdraft! Fix with atomic conditional update (`UPDATE accounts SET balance = balance - $1 WHERE id = $2 AND balance >= $1 RETURNING balance`), optimistic locking (`WHERE version = $expected`), or `SELECT ... FOR UPDATE`.
- **Reproduce Races Deterministically With Barriers (NEVER Load-Test Production!):** You do NOT need `k6` with 500 VUs to reproduce a race condition! Two concurrent promises/goroutines synchronized at a deterministic local **barrier** (`Promise.all([transfer(A, B), transfer(B, A)])` or `sync.WaitGroup` + `go test -race`) reproduce deadlocks and lost updates in `< 50ms` reliably 100% of the time!
- **Every Outbound Network Call Requires Explicit Bounded Timeouts:** Node `fetch`, Python `requests.get(url)` (default timeout = **INFINITE**!), and Go default `http.Client{}` (timeout = **INFINITE**!) hang forever when an upstream firewall silently drops TCP packets — gradually draining every worker thread and DB connection in the service! Always enforce connect + total timeout (`AbortSignal.timeout(8000)`, `requests.get(..., timeout=(3, 10))`, `http.Client{Timeout: 10 * time.Second}`).

## 4. Architecture & Implementation

```sql
-- 1. Read-Only (L0) PostgreSQL Blocking-Chain Query (Finds Exact Blocker PID & Query)
SELECT
  blocked.pid AS blocked_pid,
  blocked.query AS blocked_query,
  blocking.pid AS blocking_pid,
  blocking.state AS blocking_state,
  ROUND(EXTRACT(EPOCH FROM (now() - blocking.xact_start))::numeric, 2) AS blocking_xact_sec,
  LEFT(blocking.query, 140) AS blocking_query
FROM pg_stat_activity blocked
JOIN LATERAL unnest(pg_blocking_pids(blocked.pid)) AS blocker_pid ON true
JOIN pg_stat_activity blocking ON blocking.pid = blocker_pid
ORDER BY blocking_xact_sec DESC;

-- 2. Structurally Deadlock-Free Multi-Account Lock Acquisition (Ascending ID Order!)
-- Lock BOTH accounts in a single deterministic ORDER BY id ASC query before mutating:
SELECT id, balance_minor
FROM accounts
WHERE id IN ($1, $2)
ORDER BY id ASC
FOR UPDATE;
```

```ts
// Deterministic Local Concurrency Barrier Test (Reproduces Race/Deadlock in <50ms, 0 any, 0 casts)
export interface Barrier {
  wait(): Promise<void>
}

export function createSyncBarrier(parties: number): Barrier {
  let arrived = 0
  let releaseAll: (() => void) | undefined
  const gate = new Promise<void>((resolve) => {
    releaseAll = resolve
  })
  return {
    async wait(): Promise<void> {
      arrived += 1
      if (arrived >= parties && releaseAll) {
        releaseAll()
      }
      await gate
    },
  }
}

// Strict Bounded Outbound HTTP Fetch Helper (Prevents Infinite Socket Hangs)
export async function fetchWithBoundedTimeout(
  url: string,
  init: Omit<RequestInit, 'signal'>,
  timeoutMs = 8000,
): Promise<Response> {
  const signal = AbortSignal.timeout(timeoutMs)
  return fetch(url, { ...init, signal })
}
```

## 5. Platform/Vendor Variations
- **PostgreSQL vs MySQL InnoDB Deadlocks:** PostgreSQL detects deadlocks after `deadlock_timeout` (default `1s`) and aborts one transaction with SQLSTATE `40P01`; InnoDB detects immediately (`Error 1213`) AND also creates **gap-lock deadlocks** under `REPEATABLE READ` during `INSERT ... ON DUPLICATE KEY UPDATE` or range deletes — check `SHOW ENGINE INNODB STATUS` `LATEST DETECTED DEADLOCK`.
- **Node.js `undici`/`fetch` + DNS (`getaddrinfo`) Hangs:** Exhausting Node's default 4-thread `libuv` threadpool (`UV_THREADPOOL_SIZE=4`) via concurrent DNS lookups + `fs` + `crypto` stalls unrelated requests! Check threadpool contention and keep `keepAlive` HTTP agents bounded.
- **Connection Pool Self-Deadlock:** Opening nested DB transactions where outer function acquires Connection #1 and inner helper borrows Connection #2 from a pool of size `10` under `10` concurrent requests causes **100% permanent deadlock** (all 10 outer calls hold 10 connections while waiting forever for Connection #11!). Fix by explicitly passing the `tx` handle into inner helpers rather than borrowing a second pool connection!

## 6. Decision Matrix & Trade-Offs

| Concurrency Failure Pattern | Root Mechanism | Structural Fix | Never Do This |
| :--- | :--- | :--- | :--- |
| **2-Way Transfer Deadlock (`40P01`)** | Cyclic lock order (`A->B` vs `B->A`) | Lock all target IDs in ascending `ORDER BY id ASC FOR UPDATE` | Adding random `sleep()` before lock |
| **Overdraft / Double Spend** | Check-then-act outside atomic lock | Atomic `WHERE balance >= $1` or `FOR UPDATE` / optimistic `version` | In-memory JS mutex across multi-pod API |
| **Nested-TX Pool Deadlock** | Borrowing 2nd connection inside active TX | Pass `tx` context into child repositories; forbid nested pool acquire | Increasing `pool_max` endlessly |
| **Slow Hanging Worker / Zero Errors** | Missing HTTP/DNS/DB timeout (`timeout=None`) | Explicit `AbortSignal.timeout` + `statement_timeout` + `idle_in_transaction` timeout | Restarting pods without adding timeouts |

## 7. Real Production Scenario
An order-fulfillment service randomly hung until all 25 DB connections timed out whenever 12+ bulk orders ran together, while DB CPU sat at `3%`. Inspecting `pg_blocking_pids` showed zero SQL lock cycles — instead, 25 connections were `idle in transaction` waiting on the application! Code inspection revealed a classic **pool self-deadlock**: `processOrder()` checked out Transaction Connection #1, then called `auditLogger.write()` which tried to borrow a *second* connection from the same 25-connection pool! Under 25 concurrent requests, all 25 slots were held by `processOrder()`, so `auditLogger.write()` waited forever. Passing the active `tx` handle (or moving non-transactional audit writes after `COMMIT`) fixed the hang completely and was locked in with a 3-connection pool barrier regression test.

## 8. Failure Modes & Edge Cases
- **WRONG:** Using a Node.js in-process `async-mutex` to serialize bank account debits on a 4-replica Kubernetes deployment (each pod has its own RAM mutex -> races still corrupt DB across pods!).
  **RIGHT:** Enforce concurrency invariants inside the shared transactional datastore (row locks, atomic conditional `UPDATE`, unique constraints, or optimistic version checks — `/shadow-concurrency`).
- **WRONG:** Calling `requests.post(webhook_url, json=payload)` in Python without `timeout=(3, 10)` inside a synchronous web worker.
  **RIGHT:** Always specify explicit `(connect_timeout, read_timeout)` AND move non-critical external webhooks to a Transactional Outbox worker.

## 9. Testing & Verification
- Reproduce every race/deadlock locally with `createSyncBarrier(2)` + `Promise.all` (or `go test -race` / Python `threading.Barrier`) on an ephemeral test DB with a tiny pool (`pool_max = 3`) to expose pool self-deadlocks immediately (`FAIL` before fix -> `PASS` after fix).

## 10. Operational Considerations
- Set defensive PostgreSQL role timeouts (`statement_timeout`, `lock_timeout = '3s'`, `idle_in_transaction_session_timeout = '15s'`) so an unexpected bug fails fast with an observable error instead of hanging the entire cluster.

## 11. Authoritative References
- PostgreSQL Documentation — *Explicit Locking, Deadlocks & `pg_blocking_pids()`*.
- Martin Kleppmann — *Designing Data-Intensive Applications* (Ch. 7 Transactions, Lost Updates & Write Skew).
- Go Memory Model & Data Race Detector (`go test -race`).

## 12. Limitations & When NOT to Use
- Do NOT trigger multi-minute `k6` stress tests against staging/prod to hunt a race condition (`shadow-perf` `L3`/`L4`) — reproduce deterministically locally first (`L1`).
- For broad distributed queue/outbox/DLQ redesigns discovered during debugging, hand architecture implementation to `/shadow-concurrency`.
