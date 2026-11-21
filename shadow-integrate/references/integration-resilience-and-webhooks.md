# External Integration Resilience, Webhooks & Reconciliation Patterns

> Use this playbook when implementing external HTTP integrations, payment/ERP webhooks (`SNAP BI`, `Midtrans`, `Xendit`, `Stripe`), circuit breakers, retries, or ambiguous-mutation reconciliation.

## 1. Core Concepts
External third-party networks fail asymmetrically: a request can commit at the payment gateway while the HTTP response times out (`UNKNOWN` outcome). Production integrations preserve consistency through **atomic Transactional Outbox publishing**, **idempotent Inbox deduplication**, **timing-safe webhook verification**, **bounded jittered retries with Circuit Breakers**, and **authenticated status reconciliation**.

## 2. Technical Rules & Decision Matrix

| Integration Scenario | Pattern to Pick | Mandatory Guards |
| :--- | :--- | :--- |
| Sync External Read / Idempotent Query | Bounded Timeout + Full-Jitter Retry + **Circuit Breaker** | `AbortSignal.timeout(ms)`, retry ONLY `429`/network/`5xx`, honor `Retry-After` |
| Outbound Payment / Mutation | **Transactional Outbox** + `Idempotency-Key` + `reconcile_unknown.py` | Persist `PENDING` + outbox row in one DB tx; reconcile unknown outcomes via provider inquiry |
| Inbound Webhooks (`Midtrans`, `Xendit`, `Stripe`, `SNAP BI`) | **Raw-Body HMAC Verifier** + Replay Window + **Inbox Dedup** | `crypto.timingSafeEqual`, max timestamp skew (`300s`), unique constraint on `(provider, event_id)` |
| Delayed / Dropped Webhook Recovery | **Scheduled Reconciliation Cron** | Query provider status API for `PENDING` rows past SLA (`> 5m`); confirm identical `operation_id` & `amount` |

## 3. Implementation Examples

### Strict-TS Circuit Breaker (`CLOSED -> OPEN -> HALF_OPEN`) & Full-Jitter Retry
```ts
export type BreakerState = "CLOSED" | "OPEN" | "HALF_OPEN";

export class CircuitBreaker {
  private state: BreakerState = "CLOSED";
  private failures = 0;
  private openedAt = 0;
  private probeInFlight = false;

  public constructor(
    private readonly failureThreshold: number,
    private readonly cooldownMs: number,
  ) {}

  public async execute<T>(fn: () => Promise<T>, nowMs: number = Date.now()): Promise<T> {
    if (this.state === "OPEN") {
      if (nowMs - this.openedAt < this.cooldownMs) {
        throw new Error("CIRCUIT_OPEN: upstream dependency quarantined");
      }
      if (this.probeInFlight) {
        throw new Error("CIRCUIT_HALF_OPEN_BUSY: probe already running");
      }
      this.state = "HALF_OPEN";
      this.probeInFlight = true;
    }

    try {
      const result = await fn();
      this.failures = 0;
      this.state = "CLOSED";
      return result;
    } catch (err: unknown) {
      this.failures += 1;
      if (this.state === "HALF_OPEN" || this.failures >= this.failureThreshold) {
        this.state = "OPEN";
        this.openedAt = Date.now();
      }
      throw err;
    } finally {
      this.probeInFlight = false;
    }
  }
}

export async function withFullJitterRetry<T>(
  op: (signal: AbortSignal) => Promise<T>,
  maxAttempts = 3,
  baseDelayMs = 200,
  timeoutMs = 5000,
): Promise<T> {
  for (let attempt = 0; attempt < maxAttempts; attempt += 1) {
    try {
      return await op(AbortSignal.timeout(timeoutMs));
    } catch (err: unknown) {
      if (attempt === maxAttempts - 1) throw err;
      const capMs = Math.min(8000, baseDelayMs * 2 ** attempt);
      const jitterMs = Math.floor(Math.random() * capMs);
      await new Promise<void>((resolve) => setTimeout(resolve, jitterMs));
    }
  }
  throw new Error("UNREACHABLE_RETRY_EXHAUSTED");
}
```

### Timing-Safe Raw-Body HMAC Webhook Verifier + Replay Guard
```ts
import { createHmac, timingSafeEqual } from "node:crypto";

export function verifyWebhookHmac(
  rawBody: Buffer,
  headerSignatureHex: string,
  timestampSec: number,
  activeSecrets: readonly string[],
  maxSkewSec = 300,
  nowSec: number = Math.floor(Date.now() / 1000),
): boolean {
  if (Math.abs(nowSec - timestampSec) > maxSkewSec) return false;
  const provided = Buffer.from(headerSignatureHex, "hex");
  const payload = Buffer.concat([Buffer.from(`${timestampSec}.`, "utf8"), rawBody]);

  for (const secret of activeSecrets) {
    const expected = createHmac("sha256", secret).update(payload).digest();
    if (provided.length === expected.length && timingSafeEqual(provided, expected)) {
      return true;
    }
  }
  return false;
}
```

## 4. Best Practices
- Support an array of `activeSecrets` (`[current, previous]`) during webhook secret rotation so in-flight webhooks verified during deployment cutover do not spuriously fail.
- Compute HMAC digests over the **unparsed raw request bytes** before `JSON.parse`, because JSON key reordering or float formatting breaks signature equality.
- Validate both transaction identity (`order_id`/`reference_no`) AND minor-unit amount + currency from signed webhook/inquiry responses before transitioning internal ledger states.

## 5. Anti-Patterns (`WRONG` vs `RIGHT`)
- **WRONG (`===` string comparison & un-jittered retries on `400`):** Using `sig === expectedHex` (timing side-channel) and retrying HTTP `400`/`401`/`422` validation errors or non-idempotent POSTs on fixed 1s intervals (thundering herd + double charges).
  **RIGHT:** Use `crypto.timingSafeEqual` on equal-length buffers, fail fast on `4xx` client errors (except `408`/`429`), apply Full Jitter, and attach deterministic `Idempotency-Key` headers.
- **WRONG (Assuming timeout equals transaction failure):** Marking a payment `FAILED` when an outbound bank/QRIS HTTP call times out.
  **RIGHT:** Mark `UNKNOWN_PENDING_RECONCILE`, run `python scripts/reconcile_unknown.py --assess record.json`, and settle state strictly from an authenticated terminal inquiry bound to the same operation ID.

## 6. Production Considerations
- **Observability & Alerting:** Emit structured logs with `provider`, `operationId`, `breakerState`, `attempt`, and `latencyMs` while strictly redacting `Authorization`, webhook secrets, and card/PII payloads.
- **Dead-Letter Quarantine:** After exhausted retries on inbound webhooks, acknowledge `200` only after persisting atomically to a durable Inbox/DLQ table — or return `500` intentionally when your durable write fails so the provider retries safely.
