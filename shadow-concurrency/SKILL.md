---
name: shadow-concurrency
description: "Asynchronous & Distributed Workflow Correctness. Use when designing or fixing message queues, retries, transactional outbox/inbox, idempotency keys, optimistic/pessimistic locks, DLQ poison messages, or crash-before-ack recovery. Do NOT use for third-party API HTTP client setup (shadow-integrate), WebSocket/SSE client reconnect UX (shadow-realtime), or standalone SQL schema design (shadow-data/shadow-db)."
---

# `/shadow-concurrency` — Asynchronous & Distributed Workflow Correctness

- **Owner:** Consistency, ordering, locking, idempotency, retry budgets, DLQ, and crash-safe asynchronous execution.
- **Boundaries:** HTTP/HMAC provider adapters (`shadow-integrate`), WebSocket/SSE connection resume (`shadow-realtime`), SQL migration scripts (`shadow-data`/`shadow-db`).

## 1. Preconditions, Non-Claims & Safety Rules
- **No False Exactly-Once Claims:** External side effects (SMTP email, payment webhook, third-party API) **cannot** be guaranteed "exactly-once" without receiver idempotency or two-phase protocols; design for **at-least-once delivery + idempotent deduplication**.
- **Durable State Before Ack:** Never acknowledge a queue job or commit an external trigger before persisting durable DB state / Transactional Outbox row (`commit -> outbox -> dispatch -> ack`).

## 2. 8-Step Concurrency & Durability Playbook
Read [`methodologies/DURABLE-ASYNC-OUTBOX-AND-IDEMPOTENCY.md`](methodologies/DURABLE-ASYNC-OUTBOX-AND-IDEMPOTENCY.md) and [`playbooks/STATE-MACHINE-AND-FAILURE-MATRIX.md`](playbooks/STATE-MACHINE-AND-FAILURE-MATRIX.md):
1. **Map State Transitions & Failure Boundaries:** Identify DB commit vs queue ack vs external API boundaries.
2. **Select Delivery & Consistency Semantics:** At-least-once + idempotency key vs at-most-once; choose CAS / optimistic version (`version = version + 1`) vs pessimistic row lock (`SELECT ... FOR UPDATE SKIP LOCKED`).
3. **Write Invariants:** Single logical side effect per `idempotency_key`; monotonic state transitions; bounded retry attempts.
4. **Atomic Persistence & Outbox:** Write domain mutation + outbox/inbox row in the same ACID DB transaction.
5. **Retry-Safe Dispatch, Backoff & Poison DLQ:** Bounded exponential backoff + jitter; route poison messages past `max_attempts` to Dead-Letter Queue (`DLQ`) with replay runbook.
6. **Failure Injection & Replay Verification:** Simulate DB-commit-succeeds/ack-fails, double-claim by 2 workers, out-of-order events, and downstream outage.
7. **Verify Backpressure & Queue Retention:** Enforce queue bounds, worker concurrency caps, and DLQ alert thresholds.
8. **Emit Contract & Runbook:** Output state machine, failure matrix, delivery guarantee statement, and replay recovery steps.

## 3. Examples & Deterministic Checker
- **Happy Path:** Worker claims job with `UPDATE ... WHERE status='PENDING' RETURNING *`, checks `inbox_dedup(idempotency_key)` before SMTP send, retries on 503, routes to DLQ after 5 fails.
- **Adversarial / Must-Reject:** Handler sends email and deletes/acks job without durable outbox or claims "guaranteed exactly-once external email" -> **BLOCKED** by `concurrency_invariant_checker.py`.

```powershell
python "shadow-concurrency/scripts/concurrency_invariant_checker.py" --self-test
python "shadow-concurrency/scripts/concurrency_invariant_checker.py" --verify-workflow path/to/workflow.json
```
