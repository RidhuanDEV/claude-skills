# 04. ACID Transactions, Monetary Precision & Concurrency

## 1. Purpose & Activation Conditions
Enforce ACID correctness for financial balances, inventory decrements, quota deductions, and multi-table mutations without lost updates, negative balances, floating-point drift, or connection-pool exhaustion. Load when implementing payments, wallets, inventory, bookings, or transactional writes.

## 2. Prerequisites
- Integer minor-unit / `NUMERIC` schema design (`shadow-db` Module `01`) and isolation-level diagnostics (`shadow-db` Module `02`).

## 3. Technical Principles & Constraints
- **Zero External Network I/O Inside Open DB Transactions (CRITICAL):** NEVER call payment gateways, SMTP/email APIs, webhooks, S3, or LLM endpoints inside `BEGIN ... COMMIT`! A slow 8-second third-party timeout holds DB row locks and exhausts the connection pool across the entire app. Persist state + an `outbox_events` row in `< 10ms`, `COMMIT`, and dispatch external calls asynchronously (`/shadow-concurrency`).
- **Atomic Conditional Updates Over Read-Modify-Write:** For balances, stock counts, and rate quotas, NEVER run `SELECT balance` -> check in app -> `UPDATE balance = balance - amount` (two parallel requests both read `100` and double-spend to `-100`!). Use:
  - **Single-Row Atomic Guard:** `UPDATE wallets SET balance_minor = balance_minor - $1, version = version + 1 WHERE id = $2 AND tenant_id = $3 AND balance_minor >= $1 RETURNING balance_minor;` (check `rowCount === 1`!), OR
  - **Multi-Row Deterministic Pessimistic Lock:** `SELECT id, balance_minor FROM wallets WHERE id IN ($a, $b) ORDER BY id ASC FOR UPDATE;`, OR
  - **Optimistic Concurrency (CAS):** `UPDATE ... SET version = version + 1 WHERE id = $1 AND version = $expectedVersion`.
- **Exact Monetary Arithmetic (`BIGINT` Minor Units / `NUMERIC`):** NEVER store or compute money with IEEE-754 floating-point `FLOAT`/`DOUBLE`/decimal JS numbers! Use `BIGINT` minor units (`Rp 15000` -> `15000n` or integer cents) paired with explicit ISO-4217 currency code and deterministic rounding rules (half-to-even / banker's rounding or statutory tax rounding).
- **Double-Entry Ledger Discipline for Wallets & Financial Flows:** For real money movement, append immutable debit/credit journal rows (`SUM(debits) === SUM(credits)`) inside the same transaction as the cached balance update so every single rupiah is auditable and reconcilable!
- **Transient Serialization & Deadlock Retry Loop:** Automatically retry transient PostgreSQL `40001` (`serialization_failure`) and `40P01` (`deadlock_detected`) up to 3–5 times with exponential backoff + jitter ONLY when the transaction contains zero non-idempotent external side effects!

## 4. Architecture & Implementation
```typescript
export interface DbErrorLike {
  readonly code?: string;
}

const RETRYABLE_PG_CODES = new Set(['40001', '40P01']);

function isRetryablePgError(err: unknown): boolean {
  if (typeof err !== 'object' || err === null || !('code' in err)) return false;
  const code = err.code;
  return typeof code === 'string' && RETRYABLE_PG_CODES.has(code);
}

export async function runWithTxRetry<T>(
  txFn: () => Promise<T>,
  maxAttempts = 4,
  baseDelayMs = 25
): Promise<T> {
  for (let attempt = 1; attempt <= maxAttempts; attempt += 1) {
    try {
      return await txFn();
    } catch (err: unknown) {
      if (!isRetryablePgError(err) || attempt === maxAttempts) {
        throw err;
      }
      const jitterMs = Math.floor(Math.random() * baseDelayMs * 2 ** attempt);
      await new Promise<void>((resolve) => setTimeout(resolve, jitterMs));
    }
  }
  throw new Error('UNREACHABLE_TX_RETRY');
}
```
Atomic single-statement conditional debit + immutable ledger insert in one ACID transaction:
```sql
BEGIN;

WITH debited AS (
  UPDATE wallets
  SET balance_minor = balance_minor - $3,
      version = version + 1,
      updated_at = NOW()
  WHERE id = $1
    AND tenant_id = $2
    AND balance_minor >= $3
  RETURNING id, balance_minor
)
INSERT INTO wallet_ledger_entries (id, tenant_id, wallet_id, entry_type, amount_minor, balance_after_minor, reference_id)
SELECT $4, $2, id, 'DEBIT', $3, balance_minor, $5
FROM debited
RETURNING balance_after_minor;
-- If 0 rows returned -> INSUFFICIENT_FUNDS (atomic, zero race condition!)

COMMIT;
```

## 5. Platform / Vendor Variations
| Isolation / Concurrency Pattern | Best Fit | Watch-Out |
| :--- | :--- | :--- |
| **Atomic Conditional `UPDATE ... WHERE balance >= $1`** | Single-wallet debit, coupon quota, ticket stock | Fastest, zero deadlocks; add `CHECK (balance_minor >= 0)` in DB too! |
| **Deterministic `ORDER BY id ASC FOR UPDATE`** | Multi-row transfer (Wallet A -> Wallet B) | Always sort IDs canonically before locking to prevent `40P01` deadlocks |
| **Optimistic `WHERE version = $expected`** | Collaborative edits, approval workflows | Must map `rowCount === 0` to `409 Conflict` cleanly |
| **`SERIALIZABLE` + `runWithTxRetry`** | Complex cross-row invariants (shift scheduling, room overbooking) | Keep transactions short & indexed to minimize SSI false positives |

## 6. Decision Matrix & Trade-Offs
| Operation | Inside DB Transaction? | Why |
| :--- | :---: | :--- |
| Debit balance + Insert ledger row + Insert `outbox_events` | **YES (Same ACID Tx)** | All-or-nothing atomicity |
| Call Midtrans/Stripe HTTP API or send SMTP email | **NO (Strictly Outside Tx!)** | Prevents connection-pool exhaustion & un-rollbackable side effects |

## 7. Real Production Scenario
A marketplace checkout handler starts `BEGIN`, checks `stock > 0`, calls an external shipping-rate HTTP API (which stalls for 7s during courier downtime), then decrements stock and commits. Under a promo burst of 60 requests/sec, all 80 Postgres connections saturate inside 2 seconds and lock the `inventory` row for 7 seconds each, taking the entire site down. Moving the shipping-rate quote BEFORE `BEGIN` and using an atomic `UPDATE inventory SET available = available - $1 WHERE sku_id = $2 AND available >= $1` cuts transaction hold time from `7,000ms` to `2ms`.

## 8. Failure Modes & Edge Cases
- **WRONG:** Catching errors inside a transaction, swallowing them, and continuing to `COMMIT` a half-applied state (or retrying a transaction that already fired an external HTTP charge inside the block!).
- **RIGHT:** Keep DB transactions pure storage mutations (plus `outbox_events` insert) and roll back completely on any error.
- **WRONG:** Storing Rupiah/USD in JS float arithmetic (`0.1 + 0.2`) and `DOUBLE PRECISION` columns.
- **RIGHT:** Use integer minor units (`BIGINT`) or exact fixed-precision `NUMERIC(19,4)` end-to-end.

## 9. Testing & Verification
- Write a concurrent race integration test firing 20 parallel `$60` debits against a `$100` wallet; assert **exactly 1** succeeds, **19** return `INSUFFICIENT_FUNDS`, final `balance_minor === 40`, and `SUM(ledger)` reconciles to `40`.

## 10. Operational Considerations
- Run a nightly automated ledger-invariant check asserting `wallet.balance_minor === SUM(credits) - SUM(debits)` and alerting immediately on ANY non-zero discrepancy!

## 11. Authoritative References
- PostgreSQL Documentation — *Transaction Isolation & `SQLSTATE` Error Codes (`40001`, `40P01`)* (`https://www.postgresql.org/docs/current/errcodes-appendix.html`).
- Martin Kleppmann — *Designing Data-Intensive Applications* (Ch. 7).

## 12. Limitations & When NOT to Use
- Single-database ACID transactions cannot atomically span two separate databases or an external payment provider — use **Transactional Outbox + Idempotent Reconciliation** (`/shadow-concurrency`, `/shadow-integrate`) across service boundaries.
