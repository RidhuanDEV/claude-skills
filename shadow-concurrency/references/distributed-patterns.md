# Distributed Concurrency: Sagas, Fencing Tokens, Queues & Rate Limiting

## 1. Core Concepts
Distributed systems cannot rely on in-memory mutexes or network exactly-once illusions. Correctness requires **Transactional Outbox + Inbox deduplication**, **monotonic fencing tokens** on storage writes, **idempotent Saga compensations**, and **atomic rate limiting**.

## 2. Technical Rules & Queue Selection Matrix

| Workload Profile | Choose Engine | Why / Operational Rule |
| :--- | :--- | :--- |
| `< 500 jobs/s`, already using PostgreSQL | **Postgres Outbox + `FOR UPDATE SKIP LOCKED`** | Atomic commit with business tables; zero extra broker infra. |
| High-throughput app jobs, delayed retries | **Redis/Valkey + BullMQ** or **NATS JetStream** | Fast scheduling; MUST enforce DB-level idempotency on consumers. |
| Complex routing, per-message ack/DLQ | **RabbitMQ (Quorum Queues)** | Explicit dead-letter exchanges and competing consumer fairness. |
| Replayable event stream, multi-service log | **Kafka / Redpanda** | Partition-ordered log; partition by `tenantId` or `aggregateId` to preserve causal order. |
| Multi-step workflows with human timers/sagas | **Temporal** (or DB durable state machine) | Built-in deterministic replay and saga compensation tracking. |

## 3. Implementation Examples
```sql
-- 1. Monotonic Fencing Token Enforcement in Authoritative Storage (Prevents Zombie Lock Writes)
UPDATE inventory_reservations
SET quantity = :new_qty,
    fencing_token = :incoming_token,
    updated_at = NOW()
WHERE item_id = :item_id
  AND fencing_token < :incoming_token;
-- If affected_rows == 0, reject write: a newer lock holder has already superseded this worker!
```
```ts
// 2. Atomic Token-Bucket Rate Limiter Logic (Deterministic Window Calculation)
export function evaluateTokenBucket(
  state: { readonly tokens: number; readonly lastRefillMs: number },
  nowMs: number,
  capacity: number,
  refillPerSec: number,
  cost = 1,
): { readonly allowed: boolean; readonly remaining: number; readonly retryAfterSec: number; readonly nextLastRefillMs: number } {
  const elapsedSec = Math.max(0, (nowMs - state.lastRefillMs) / 1000)
  const replenished = Math.min(capacity, state.tokens + elapsedSec * refillPerSec)
  if (replenished < cost) {
    const deficit = cost - replenished
    return {
      allowed: false,
      remaining: Math.floor(replenished),
      retryAfterSec: Math.ceil(deficit / Math.max(refillPerSec, 0.001)),
      nextLastRefillMs: nowMs,
    }
  }
  return { allowed: true, remaining: Math.floor(replenished - cost), retryAfterSec: 0, nextLastRefillMs: nowMs }
}
```

## 4. Best Practices
- Prefer **Saga Orchestration** when coordinating `>= 3` services (e.g. `Order -> Payment -> Inventory -> Shipping`) so every forward step and its **idempotent compensating step** are tracked in one durable state table.
- On `SIGTERM`, stop polling new jobs immediately, extend visibility leases for active jobs while draining up to `SHUTDOWN_GRACE_MS`, then close pools cleanly.

## 5. Anti-patterns (WRONG vs RIGHT)
- **WRONG:** Assuming a Redis lease lock (`SET resource owner NX PX 10000` / Redlock) prevents double writes on its own (a GC pause > 10s lets the paused worker write stale data after another worker acquires the lock!).
- **RIGHT:** Pair every lease lock with a **monotonic fencing token** checked (`WHERE fencing_token < :token`) by the database.
- **WRONG:** Publishing a queue event BEFORE `COMMIT` of the database transaction (consumers read uncommitted/rolled-back rows).
- **RIGHT:** Insert into an `outbox_events` table inside the same DB transaction, commit, then relay asynchronously.

## 6. Production Considerations
- Bound retry attempts with exponential backoff + full jitter (`base * 2^attempt * rand(0.5..1.5)`), route poison messages exceeding `maxAttempts` to a **Dead-Letter Queue (DLQ)** with alert telemetry, and provide an audited idempotent replay script.
