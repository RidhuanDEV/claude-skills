# 02. Inbox Deduplication & Crash-Before-Ack Recovery

## 1. Purpose & Activation Conditions
Design consumers and workers that remain 100% correct under duplicate deliveries, crash-after-send-before-ack failures, and out-of-order event arrivals using **Transactional Inbox Deduplication** and monotonic state guards. Load when implementing queue workers, webhook consumers, or debugging duplicate emails/charges.

## 2. Prerequisites
- At-least-once delivery model (`01-delivery-semantics-and-transactional-outbox.md`) and explicit idempotency key per logical message.

## 3. Technical Principles & Constraints
- **The Crash-Before-Ack Failure Window:** Every queue consumer executes two separate systems: (1) local work / external side effect, and (2) `ack()` to the queue/outbox. If the worker crashes or loses network connectivity **between (1) and (2)**, the queue MUST redeliver the job to another worker!
  - **For Internal DB Consumers (Inbox Pattern):** Achieve **effectively-once** state changes by inserting `message_id` into `inbox_dedup (consumer_name, message_id)` with a `PRIMARY KEY` **inside the EXACT SAME DB transaction** as the domain mutation! If redelivered, `ON CONFLICT DO NOTHING` returns 0 inserted rows -> skip work cleanly and `ack()`!
  - **For External Side Effects (SMTP, Payment API, Webhook):** Pass the exact persistent **`idempotency_key`** to the external receiver (e.g., Resend `Idempotency-Key`, Stripe `Idempotency-Key`, or `Message-ID`). If the external protocol lacks idempotency (raw SMTP!), persist an atomic state guard (`DISPATCHING` -> check provider inquiry/logs before blindly resending) and **NEVER claim "guaranteed zero-duplicate raw SMTP"**!
- **Ordering & Monotonic State Guards:** Even partitioned queues can deliver retries out of order relative to newer events. Guard consumer projections with monotonic version/timestamp checks (`WHERE EXCLUDED.aggregate_version > target.last_applied_version`) so a delayed retry of `OrderCreated (v1)` NEVER overwrites `OrderPaid (v2)`!

## 4. Architecture & Implementation
```sql
-- Transactional Inbox Deduplication Table (Guarantees At-Most-Once Internal Processing)
CREATE TABLE inbox_dedup (
  consumer_name  TEXT NOT NULL,
  message_id     TEXT NOT NULL,
  processed_at   TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  PRIMARY KEY (consumer_name, message_id)
);
```
Atomic Inbox consumer handler (strict TypeScript, zero casts):
```typescript
export interface InboxTransaction {
  tryClaimMessage(consumerName: string, messageId: string): Promise<boolean>; // INSERT ... ON CONFLICT DO NOTHING RETURNING 1
  applyDomainEffect(): Promise<void>;
}

export async function processMessageWithInboxDedup(
  consumerName: string,
  messageId: string,
  runInTx: (fn: (tx: InboxTransaction) => Promise<'APPLIED' | 'DUPLICATE_SKIPPED'>) => Promise<'APPLIED' | 'DUPLICATE_SKIPPED'>
): Promise<'APPLIED' | 'DUPLICATE_SKIPPED'> {
  return runInTx(async (tx) => {
    const claimed = await tx.tryClaimMessage(consumerName, messageId);
    if (!claimed) {
      // Already processed in an earlier committed transaction -> safe no-op, caller can ack() cleanly!
      return 'DUPLICATE_SKIPPED';
    }
    await tx.applyDomainEffect();
    return 'APPLIED';
  });
}
```

## 5. Platform / Vendor Variations
| Consumer Side Effect | Crash-Before-Ack Protection | Effective Guarantee |
| :--- | :--- | :--- |
| **Internal DB Projection / Ledger** | `inbox_dedup` `PRIMARY KEY` in same ACID transaction | **Effectively-once** (mathematically exact inside DB) |
| **Idempotent External REST API (Stripe/Resend/Xendit)** | Forward persistent `Idempotency-Key` + persist `UNKNOWN` on timeout (`/shadow-integrate`) | **Effectively-once** inside provider dedup window |
| **Non-Idempotent Raw SMTP Relay** | Persist `DISPATCH_ATTEMPTED` + deterministic `Message-ID`; do NOT blindly auto-retry ambiguous post-DATA timeout | At-least-once (or manual inquiry); **never falsely claim exactly-once** |

## 6. Decision Matrix & Trade-Offs
| Deduplication Approach | Survives Worker Crash? | Survives Process Restart? | Verdict |
| :--- | :---: | :---: | :--- |
| **In-Memory `Set<string>`** | **NO** | **NO** | **FORBIDDEN for durable consumers** |
| **Redis `SET NX EX` (Separate from DB)** | Partial (non-atomic with DB commit!) | Until TTL/failover | Weak — prefer DB `inbox_dedup` |
| **DB `inbox_dedup` Inside Same ACID Tx** | **YES** | **YES** | **Gold standard for all internal consumers** |

## 7. Real Production Scenario
A notification worker sends an email via raw SMTP, then crashes before marking the BullMQ job complete (`crash-before-ack`). BullMQ re-queues the job after the 30s lock expires, sending a second identical email — and when a downstream Postgres consumer had no `inbox_dedup` table, a RabbitMQ redelivery credited a user's loyalty wallet twice! Adding `inbox_dedup` inside the wallet credit transaction guarantees single credit on arbitrary replays, while switching email dispatch to an idempotency-key-capable ESP adapter (`Resend`/`SES` + outbox state machine) stops duplicate emails cleanly.

## 8. Failure Modes & Edge Cases
- **WRONG:** Inserting into `inbox_dedup` in Transaction 1, committing, and executing the domain mutation in Transaction 2 (crash between Tx1 and Tx2 permanently drops the message without executing it!).
- **RIGHT:** Claim `inbox_dedup` AND execute the domain mutation inside the **exact same ACID DB transaction** (`processMessageWithInboxDedup`).
- **WRONG:** Acknowledging (`ack`) a queue message at the *start* of the handler ("auto-ack") before processing succeeds.
- **RIGHT:** Disable auto-ack; acknowledge strictly AFTER durable commit succeeds!

## 9. Testing & Verification
- **Mandatory Crash-Before-Ack Test:** Execute `processMessageWithInboxDedup(consumer, 'msg-1')` -> simulate simulated crash before `ack()` -> invoke exact same `(consumer, 'msg-1')` a second time -> assert second run returns `'DUPLICATE_SKIPPED'` and domain ledger balance changed **once**!
- Run `python shadow-concurrency/scripts/concurrency_invariant_checker.py --self-test` (blocks false exactly-once external side-effect claims!).

## 10. Operational Considerations
- Partition or prune `inbox_dedup` records older than your broker/webhook maximum replay window (`7–30 days`) so the dedup index remains compact in RAM.

## 11. Authoritative References
- Pat Helland — *Idempotence Is Not a Medical Condition* (ACM Queue, 2012).
- Enterprise Integration Patterns — *Idempotent Receiver* (`https://www.enterpriseintegrationpatterns.com/patterns/messaging/IdempotentReceiver.html`).

## 12. Limitations & When NOT to Use
- `inbox_dedup` only deduplicates messages sharing the same deterministic `message_id`/`idempotency_key`; if an upstream producer generates a brand-new random ID on every retry, fix producer key stability first (`shadow-api` Module `04`, `shadow-analytics` Module `02`).
