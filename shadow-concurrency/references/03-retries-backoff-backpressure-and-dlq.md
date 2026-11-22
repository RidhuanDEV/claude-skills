# 03. Retries, Backoff, Backpressure & Poison DLQ

## 1. Purpose & Activation Conditions
Design resilient worker retry policies, full-jitter exponential backoff, bounded concurrency / backpressure, graceful `SIGTERM` draining, and poison-message **Dead-Letter Queue (DLQ)** replay runbooks. Load when configuring queue retry schedules, handling thundering herds, or recovering stuck/poison worker jobs.

## 2. Prerequisites
- Outbox/Inbox idempotency (`01`, `02`) and clear distinction between transient (`429`/`503`/timeout) vs permanent (`400`/`422`/schema error) failures.

## 3. Technical Principles & Constraints
- **Never Retry Forever & Never Retry Permanent Errors:**
  - **Retryable (Transient):** Network timeout, DNS transient, HTTP `408`, `429` (respecting `Retry-After`!), `502`, `503`, `504`, DB `40001`/`40P01`.
  - **Non-Retryable (Immediate DLQ):** JSON schema violation, invalid recipient/input (`400`/`422`), authentication misconfiguration (`401`/`403` -> alert & pause worker!).
- **Exponential Backoff + Full Jitter (Stop Thundering Herds!):** Fixed `5s` retries synchronize 10,000 failed jobs into synchronized retry storms that keep a recovering downstream service knocked down! Compute `delayMs = random(0, min(maxCapMs, baseMs * 2^attempt))` and enforce a hard `maxAttempts` ceiling (`3–8` depending on SLA) before routing to **DLQ**!
- **Bounded Concurrency & Backpressure:** Always cap per-worker prefetch/concurrency (`concurrency <= poolSize * 0.6`), enforce per-tenant fairness queues (one noisy tenant submitting 100k jobs MUST NOT starve other tenants' OTPs!), and bound in-memory queues so traffic spikes shed load gracefully instead of OOM-killing workers!
- **Graceful `SIGTERM` Shutdown (`Zero In-Flight Aborts`):** On container/Kubernetes `SIGTERM`:
  1. Immediately stop polling/accepting new jobs,
  2. Extend visibility leases for currently executing jobs while draining up to `SHUTDOWN_GRACE_MS` (`20–25s`, strictly `< K8s terminationGracePeriodSeconds`),
  3. Close DB/Redis pools cleanly and exit `0`!
- **Audited DLQ Replay Runbook:** A DLQ without alerting and a replay tool is just a silent black hole! Alert immediately on DLQ growth, inspect root cause, fix the bug/payload first, and replay in bounded throttled batches preserving original `idempotency_key`.

## 4. Architecture & Implementation
```typescript
export type ErrorClass = 'transient_retryable' | 'permanent_dlq' | 'auth_pause_worker';

export function classifyWorkerFailure(httpStatus: number | null, isNetworkTimeout: boolean): ErrorClass {
  if (isNetworkTimeout || httpStatus === 408 || httpStatus === 429 || (httpStatus !== null && httpStatus >= 500)) {
    return 'transient_retryable';
  }
  if (httpStatus === 401 || httpStatus === 403) {
    return 'auth_pause_worker';
  }
  return 'permanent_dlq';
}

export function computeFullJitterBackoffMs(
  attempt: number,
  baseDelayMs = 500,
  capDelayMs = 60_000,
  retryAfterSec?: number,
  rand01: () => number = Math.random
): number {
  const expCap = Math.min(capDelayMs, baseDelayMs * 2 ** Math.max(0, attempt - 1));
  const jittered = Math.floor(rand01() * expCap);
  if (retryAfterSec !== undefined && retryAfterSec > 0) {
    return Math.min(capDelayMs, Math.max(jittered, retryAfterSec * 1000));
  }
  return Math.max(50, jittered);
}
```
Bounded DLQ inspection & safe idempotent replay SQL:
```sql
-- 1. Inspect top DLQ error groups before replaying (NEVER blind-replay unfixed bugs!)
SELECT event_type, LEFT(last_error, 120) AS err_summary, COUNT(*) AS cnt
FROM outbox_events
WHERE status = 'DEAD_LETTER'
GROUP BY 1, 2
ORDER BY cnt DESC;

-- 2. Throttled replay of 100 fixed DLQ jobs preserving exact original idempotency_key
UPDATE outbox_events
SET status = 'PENDING', attempts = 0, available_at = NOW(), locked_until = NULL
WHERE id IN (
  SELECT id FROM outbox_events
  WHERE status = 'DEAD_LETTER' AND event_type = $1
  ORDER BY created_at ASC
  LIMIT 100
);
```

## 5. Platform / Vendor Variations
| Queue / Broker | Visibility Timeout / Lease | Native DLQ Mechanism |
| :--- | :--- | :--- |
| **PostgreSQL Outbox** | `locked_until` column reclaimed on expiry | `status = 'DEAD_LETTER'` when `attempts >= max_attempts` |
| **BullMQ (Redis/Valkey)** | `lockDuration` (default `30s`; auto-renewed by worker heartbeat) | `failed` set (`removeOnFail: false` or bounded keep count) |
| **AWS SQS** | `VisibilityTimeout` (`>= 6 × handler timeout`) | Redrive Policy (`maxReceiveCount`) -> dedicated SQS DLQ |
| **RabbitMQ (Quorum Queues)** | Consumer `delivery-limit` + `prefetch` (`basic.qos`) | `x-dead-letter-exchange` routing to DLQ |

## 6. Decision Matrix & Trade-Offs
| Backoff Formula | Spread Under Outage | Avg Wait | Verdict |
| :--- | :---: | :---: | :--- |
| **Fixed Interval (`5s, 5s, 5s`)** | Terrible (retry storms!) | Low | **Avoid** |
| **Pure Exponential (`1s, 2s, 4s, 8s`)** | Poor (synchronized waves) | Medium | Suboptimal |
| **Full Jitter (`rand(0, min(cap, base * 2^n))`)** | **Best (smooths load cleanly)** | Low–Medium | **AWS/SRE Recommended Standard** |

## 7. Real Production Scenario
A malformed webhook payload triggers a `TypeError` inside a RabbitMQ worker configured with `requeue: true` and no `delivery-limit`. The single poison message loops 400 times/second, pegging worker CPU at 100% and starving 15,000 legitimate payment jobs behind it. Adding `classifyWorkerFailure` (sending `permanent_dlq` errors straight to DLQ on attempt 1), `max_attempts = 5` with Full Jitter for transient errors, and `prefetch = 10` restores healthy queue throughput immediately.

## 8. Failure Modes & Edge Cases
- **WRONG:** Re-queuing a poison message immediately to the head of the queue (`requeue: true` with 0 delay and infinite retries -> infinite CPU spin loop!).
- **RIGHT:** Enforce bounded `maxAttempts`, Full Jitter delay on transient failures, and immediate DLQ routing on permanent/schema errors.
- **WRONG:** Replaying 50,000 DLQ messages all at once in a single burst (triggers a second outage on downstream services!).
- **RIGHT:** Replay DLQ items in bounded rate-limited batches (`100–500` at a time) AFTER verifying the root-cause fix on a 5-message canary!

## 9. Testing & Verification
- Unit-test `classifyWorkerFailure` (`429`/`503`/timeout -> retry, `400`/`422` -> DLQ, `401` -> pause) and `computeFullJitterBackoffMs` (bounded `<= capDelayMs`, honors `Retry-After`).
- Inject a poison payload in staging and verify it lands cleanly in `DEAD_LETTER` without stalling concurrent healthy jobs.

## 10. Operational Considerations
- Monitor 4 queue SLOs (`/shadow-observe`): (1) oldest pending job age (`queue_lag_sec`), (2) retry ratio (`retries / completions`), (3) DLQ inflow rate (page on transactional DLQ `> 0`), and (4) worker crash/lease-expiry count.

## 11. Authoritative References
- Marc Brooker (AWS Architecture Blog) — *Exponential Backoff and Jitter* (`https://aws.amazon.com/blogs/architecture/exponential-backoff-and-jitter/`).
- Google SRE Book — *Handling Overload & Cascading Failures* (`https://sre.google/sre-book/addressing-cascading-failures/`).

## 12. Limitations & When NOT to Use
- Retries and DLQs handle *asynchronous* background jobs cleanly; for synchronous user-facing HTTP reads, keep total retry budget tiny (`<= 1–2` fast retries inside timeout ceiling) and fail fast via Circuit Breakers (`/shadow-integrate`).
