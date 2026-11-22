# 03. Retries, Circuit Breakers & `UNKNOWN` Mutation Recovery

## 1. Purpose & Activation Conditions
Handle transient external outages, rate limits, and **ambiguous mutation timeouts (`UNKNOWN`)** without causing cascading thread exhaustion or duplicate financial charges — combining **Circuit Breakers**, **Full-Jitter Retries**, and **`reconcile_unknown.py` inquiry-first recovery**. Load when engineering outbound payment/transfer calls or hardening external HTTP reliability.

## 2. Prerequisites
- Bounded HTTP timeouts (`01`), `shadow-integrate/scripts/reconcile_unknown.py`, and idempotency keys (`shadow-api` Module `04`).

## 3. Technical Principles & Constraints
- **CRITICAL Rule — Never Treat an Outbound Mutation Timeout as `FAILED`!** When an outbound `POST /charge` or `POST /disbursement` times out (`ETIMEDOUT` / `ECONNRESET` / `504`), the remote bank/gateway MAY have already executed the transfer!
  1. Immediately persist local state as **`UNKNOWN_PENDING_RECONCILE`** alongside the exact `local_operation_id`, `idempotency_key`, `provider_account`, and `payload_hash`.
  2. **Query Provider Status Inquiry API First** (when supported by evidence): verify the terminal inquiry response is authenticated AND bound to the **exact same provider account, operation, transaction ID, and amount** before settling `SUCCESS` or `FAILED`!
  3. **Safe Replay Boundary:** Blindly replaying the mutation is permitted **ONLY** inside the provider's documented idempotency deduplication window with the **exact identical** `idempotency_key`, payload, account, and operation under a verified provider idempotency guarantee — NEVER after window expiry or when idempotency is unverified (escalate to manual reconciliation instead!).
  4. A transport acknowledgement (`202` / `HTTP 200 accepted`) leaves business settlement `PENDING` until terminal confirmation arrives.
- **Retry ONLY Safe Transient Errors:** Retry `408`, `429` (honoring `Retry-After`!), `502`, `503`, `504`, and pre-connect network errors using **Exponential Backoff + Full Jitter** (`<= 3` attempts on sync paths). NEVER retry `400`, `401`, `403`, `404`, or `422`!
- **Circuit Breaker (`CLOSED -> OPEN -> HALF_OPEN`):** When consecutive upstream failures cross `failureThreshold` (e.g., 5 failures in 30s), trip `OPEN` for `cooldownMs` (e.g., 30s) to fail fast immediately instead of tying up worker pools; allow exactly **1 probe** in `HALF_OPEN` before closing again!

## 4. Architecture & Implementation
```typescript
export type BreakerState = 'CLOSED' | 'OPEN' | 'HALF_OPEN';

export class CircuitBreaker {
  private state: BreakerState = 'CLOSED';
  private failures = 0;
  private openedAtMs = 0;
  private probeInFlight = false;

  public constructor(
    private readonly failureThreshold: number,
    private readonly cooldownMs: number
  ) {}

  public async execute<T>(fn: () => Promise<T>, nowMs: number = Date.now()): Promise<T> {
    if (this.state === 'OPEN') {
      if (nowMs - this.openedAtMs < this.cooldownMs) {
        throw new Error('CIRCUIT_OPEN: upstream quarantined');
      }
      if (this.probeInFlight) {
        throw new Error('CIRCUIT_HALF_OPEN_BUSY: single probe active');
      }
      this.state = 'HALF_OPEN';
      this.probeInFlight = true;
    }

    try {
      const result = await fn();
      this.failures = 0;
      this.state = 'CLOSED';
      return result;
    } catch (err: unknown) {
      this.failures += 1;
      if (this.state === 'HALF_OPEN' || this.failures >= this.failureThreshold) {
        this.state = 'OPEN';
        this.openedAtMs = Date.now();
      }
      throw err;
    } finally {
      this.probeInFlight = false;
    }
  }
}
```
Offline ambiguous-mutation decision verifier (`L0`/`L1`, zero external network calls):
```powershell
python "shadow-integrate/scripts/reconcile_unknown.py" --self-test
python "shadow-integrate/scripts/reconcile_unknown.py" --assess path/to/unknown_record.json
python -m unittest discover -s "shadow-integrate/tests" -v
```

## 5. Platform / Vendor Variations
| Failure Situation | Correct Action | Forbidden Action |
| :--- | :--- | :--- |
| **HTTP `400` / `422` Invalid Payload** | Fail immediately (`CONFIRMED_DECLINED`), fix bug | Retrying 5 times with backoff |
| **HTTP `429 Too Many Requests`** | Pause `>= Retry-After` seconds + Full Jitter | Tight retry loop hammering rate limit |
| **Timeout on `POST /payout` (Ambiguous)** | Persist `UNKNOWN` -> Call Authenticated Status Inquiry -> Assess via `reconcile_unknown.py` | Marking `FAILED` & letting user retry with a brand-new order ID! |
| **Provider Down (`503` x 10)** | Trip Circuit Breaker `OPEN`, buffer writes in Outbox (`/shadow-concurrency`) | Sending 1,000 requests/sec into dead upstream |

## 6. Decision Matrix & Trade-Offs (`UNKNOWN` Recovery — `reconcile_unknown.py`)
| Inquiry Supported? | Verified Idempotency Window Active? | Required Decision |
| :---: | :---: | :--- |
| **YES** | Any | **Query Authenticated Status Inquiry First** (verify account/op/tx match!) |
| No | **YES** (identical key/payload/account) | Safe bounded replay inside verified dedup window ONLY |
| No | **NO** (expired or unverified) | **HOLD -> Manual Reconciliation** (prevent double debit!) |

## 7. Real Production Scenario
A B2B payroll platform calls a bank disbursement API (`POST /transfers`) which times out at 8s. The naive client marks the transfer `FAILED`, refunds the company's internal wallet, and lets Finance click `"Retry Transfer"` with a fresh `reference_id` — executing TWO real bank transfers of `Rp 250.000.000`! Enforcing `UNKNOWN` persistence -> authenticated status inquiry -> `reconcile_unknown.py` decision gates eliminates double disbursements structurally (`shadow-integrate/tests/test_idempotency_recovery.py`).

## 8. Failure Modes & Edge Cases
- **WRONG:** Accepting a provider status inquiry response without verifying that `receipt.account === local.account`, `receipt.operation === local.operation`, and `receipt.transactionId === local.transactionId` (mismatched receipt corruption!).
- **RIGHT:** Bind every terminal inquiry receipt strictly to the identical account, operation, transaction ID, and minor-unit amount before finalizing state.
- **WRONG:** Retrying an ambiguous timeout with a **newly generated** `Idempotency-Key` (guarantees duplicate execution!).
- **RIGHT:** Persist the original `idempotency_key` in DB BEFORE the first outbound attempt and reuse it strictly inside the verified dedup window.

## 9. Testing & Verification
- Run `python shadow-integrate/scripts/reconcile_unknown.py --self-test` and `python -m unittest discover -s shadow-integrate/tests -v` (verifies timeout inquiry, mismatched receipt rejection, and expired-window manual escalation!).

## 10. Operational Considerations
- Alert whenever `COUNT(*) WHERE status = 'UNKNOWN_PENDING_RECONCILE' AND updated_at < NOW() - INTERVAL '5 minutes' > 0` so stuck financial mutations are resolved promptly before end-of-day bank settlement cutoffs.

## 11. Authoritative References
- Michael Nygard — *Release It! (2nd Ed.)* — Circuit Breakers, Timeouts & Bulkheads.
- AWS Builders' Library — *Timeouts, Retries, and Backoff with Jitter* (`https://aws.amazon.com/builders-library/timeouts-retries-and-backoff-with-jitter/`).

## 12. Limitations & When NOT to Use
- Circuit breakers protect your threads from a dying downstream, NOT from logic bugs in your own payloads (`4xx` validation errors MUST NOT trip the circuit breaker — only count transport/timeout/`5xx` failures!).
