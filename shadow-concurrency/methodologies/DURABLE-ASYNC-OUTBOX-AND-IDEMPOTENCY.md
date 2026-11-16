# Durable Async Workflows, Transactional Outbox & Idempotency Methodology

## 1. Delivery Semantics & The Exactly-Once Fallacy
- **At-Least-Once + Idempotent Receiver** is the standard reliable pattern when external HTTP/SMTP networks sit outside your database transaction.
- **Idempotency vs Deduplication:** Deduplication ignores duplicate transport deliveries within a retention window; Idempotency guarantees repeated execution of the same logical command (`Idempotency-Key` + payload hash) produces the same persisted state and HTTP/business result without repeating side effects.

## 2. Adversarial Failure Modes & Required Controls
| Failure Case | Root Hazard | Mandatory Engineering Control |
|---|---|---|
| **DB Commit Succeeds / Queue Ack Fails** | Worker crashes before ack; broker redelivers job and sends duplicate email/payout | Atomic outbox/inbox table keyed by `(tenant_id, idempotency_key)` checked before side effect |
| **Two Workers Claim Same Job** | Read-then-update race executes job twice concurrently | Optimistic CAS (`UPDATE jobs SET status='RUNNING', locked_by=$1, version=version+1 WHERE id=$2 AND status='PENDING' AND version=$3`) or `FOR UPDATE SKIP LOCKED` |
| **Out-of-Order Webhooks / Events** | `cancelled` arrives before `created` or older status overwrites newer | Monotonic `sequence_no` / `event_version` guard rejecting stale transitions (`WHERE version < $incoming`) |
| **Poison Message Infinite Loop** | Malformed payload crashes worker forever, starving healthy queue items | Bounded `max_attempts` + exponential backoff with full jitter -> move to `DLQ` with triage alert |
| **Downstream Outage During Dispatch** | Synchronous retry bursts exhaust DB connections | Circuit breaker + scheduled outbox poller with backpressure limits |
