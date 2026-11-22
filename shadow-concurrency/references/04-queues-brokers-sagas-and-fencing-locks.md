# 04. Queues, Brokers, Sagas & Fencing-Token Locks

## 1. Purpose & Activation Conditions
Select the right queue/broker architecture (Postgres `SKIP LOCKED` vs BullMQ vs RabbitMQ vs Kafka vs Temporal), orchestrate multi-service **Sagas** with idempotent compensations, protect distributed critical sections with **monotonic fencing tokens**, and implement atomic token-bucket rate limiting. Load when choosing queue infra, coordinating multi-step workflows, or debugging distributed lock races.

## 2. Prerequisites
- Core Outbox/Inbox durability (`01`, `02`) and retry/DLQ discipline (`03`).

## 3. Technical Principles & Constraints
- **Right-Sized Queue/Broker Selection (Avoid Premature Kafka!):**
  - **`< 500` jobs/sec + already on PostgreSQL:** Use **Postgres Outbox + `FOR UPDATE SKIP LOCKED`** — atomic with business data and zero extra broker ops!
  - **High-throughput app jobs & delayed schedules:** **Redis/Valkey + BullMQ** or **NATS JetStream** (still require DB-level idempotency!).
  - **Complex AMQP routing & competing consumers:** **RabbitMQ Quorum Queues** (avoid deprecated Classic Mirrored Queues).
  - **Replayable multi-service event log (`> 10k` msg/s):** **Kafka / Redpanda** (partition strictly by `tenantId` or `aggregateId` to preserve causal entity order!).
  - **Long-running multi-step workflows with timers/human approvals:** **Temporal** (or durable DB state machine).
- **Distributed Locks Need Monotonic Fencing Tokens (Kleppmann's Law):** NEVER assume a Redis lease lock (`SET key val NX PX 10000` / Redlock) alone guarantees mutual exclusion! If Worker 1 acquires Lock `token=33`, freezes for a 12-second GC pause, Worker 2 acquires Lock `token=34` and commits, then Worker 1 wakes up and writes stale data! **Fix:** The lock service issues a strictly **monotonic fencing token** (`33 < 34`), and the authoritative DB checks **`WHERE fencing_token < :incoming_token`** on every write — rejecting zombie Worker 1 atomically!
- **Saga Orchestration vs Choreography:** When a business workflow spans `>= 3` services (`Order -> ReserveInventory -> ChargePayment -> CreateShipment`), prefer **Saga Orchestration** (one durable state table tracking forward steps + explicit **idempotent compensating actions** `ReleaseInventory`, `RefundPayment`) rather than blind pub/sub choreography where partial failures are impossible to trace!
- **Atomic Token-Bucket Rate Limiting:** Evaluate rate-limit state atomically (Redis Lua script or single DB `UPDATE`), NEVER via non-atomic `GET -> compute -> SET`!

## 4. Architecture & Implementation
```sql
-- Monotonic Fencing Token Guard in Authoritative Storage (Blocks Zombie Lock Holders!)
UPDATE inventory_reservations
SET quantity      = $2,
    fencing_token = $3,
    updated_at    = NOW()
WHERE item_id = $1
  AND fencing_token < $3;
-- If affected_rows == 0 -> REJECT! A newer lock holder (token >= $3) already superseded this worker!
```
Deterministic Token-Bucket evaluator (embed inside atomic Redis Lua / DB row lock):
```typescript
export interface TokenBucketState {
  readonly tokens: number;
  readonly lastRefillMs: number;
}

export interface TokenBucketDecision {
  readonly allowed: boolean;
  readonly remaining: number;
  readonly retryAfterSec: number;
  readonly nextState: TokenBucketState;
}

export function evaluateTokenBucket(
  state: TokenBucketState,
  nowMs: number,
  capacity: number,
  refillPerSec: number,
  cost = 1
): TokenBucketDecision {
  const elapsedSec = Math.max(0, (nowMs - state.lastRefillMs) / 1000);
  const replenished = Math.min(capacity, state.tokens + elapsedSec * refillPerSec);
  if (replenished < cost) {
    const deficit = cost - replenished;
    return {
      allowed: false,
      remaining: Math.floor(replenished),
      retryAfterSec: Math.ceil(deficit / Math.max(refillPerSec, 0.001)),
      nextState: { tokens: replenished, lastRefillMs: nowMs },
    };
  }
  const remaining = replenished - cost;
  return {
    allowed: true,
    remaining: Math.floor(remaining),
    retryAfterSec: 0,
    nextState: { tokens: remaining, lastRefillMs: nowMs },
  };
}
```

## 5. Platform / Vendor Variations
| Engine | Ordering Scope | Multi-Consumer Replay | Operational Overhead |
| :--- | :--- | :---: | :---: |
| **Postgres `SKIP LOCKED`** | FIFO / priority query | Via archive table | **Lowest** |
| **BullMQ (Redis/Valkey)** | Per-queue FIFO / priority | Job history only | Low |
| **RabbitMQ Quorum Queues** | Per-queue (breaks on requeue/multi-consumer) | No (destructive pop) | Medium |
| **Kafka / Redpanda** | Strict per-partition (`key = aggregateId`) | **YES (offset replay)** | High |
| **Temporal** | Workflow execution history | **Deterministic workflow replay** | Medium–High |

## 6. Decision Matrix & Trade-Offs (Saga Coordination)
| Saga Style | Visibility & Debugging | Coupling | Best Fit |
| :--- | :---: | :---: | :--- |
| **Orchestration (Central Durable State Machine / Temporal)** | **Very High (1 table shows exact step)** | Explicit step calls | `>= 3` services, payments/refunds, complex compensations |
| **Choreography (Pub/Sub Events)** | Low (cyclic event spaghetti risk) | Loose | Simple 1-to-1 reactions (`OrderPaid -> SendReceipt`) |

## 7. Real Production Scenario
A ticket-booking platform uses a Redis `SET lock:event:42 workerId NX PX 10000` lock around seat inventory allocation. During a heavy GC pause on Worker A (`11.5s`), the lock expires and Worker B allocates the last VIP seat; Worker A resumes and overwrites the seat assignment, double-booking the same seat! Switching to PostgreSQL atomic conditional update (`WHERE available > 0`) — and adding a monotonic `fencing_token` guard (`WHERE fencing_token < $3`) on external storage writes — eliminates zombie-worker corruption completely.

## 8. Failure Modes & Edge Cases
- **WRONG:** Deploying Kafka + ZooKeeper/KRaft for a 2-service app processing 15 background jobs per minute ("resume-driven architecture").
- **RIGHT:** Start with PostgreSQL Outbox + `FOR UPDATE SKIP LOCKED` (or BullMQ if Redis already exists) and graduate to Kafka/Temporal only when proven throughput or replay scale demands it.
- **WRONG:** Assuming Saga compensating transactions (`RefundPayment`, `ReleaseStock`) can never fail or be called twice.
- **RIGHT:** Make EVERY Saga compensating step **idempotent** and retryable (a pivot-point failure MUST eventually converge cleanly via DLQ/reconciliation!).

## 9. Testing & Verification
- Test fencing-token rejection: apply write with `fencing_token = 10` -> succeed -> replay stale zombie write with `fencing_token = 9` -> assert `0` rows updated and state preserved!
- Test Saga compensation: inject failure at Step 3 (`ChargePayment` declined) -> verify Step 2 (`ReleaseInventory`) runs idempotently and order settles in `CANCELLED`!

## 10. Operational Considerations
- Monitor Saga stuck-in-intermediate-state counts (`status = 'COMPENSATING' AND updated_at < NOW() - INTERVAL '10 minutes'`) so half-completed Sagas trigger immediate alerts.

## 11. Authoritative References
- Martin Kleppmann — *How to Do Distributed Locking* (Fencing Tokens, `https://martin.kleppmann.com/2016/02/08/how-to-do-distributed-locking.html`).
- Chris Richardson — *Pattern: Saga* (`https://microservices.io/patterns/data/saga.html`).

## 12. Limitations & When NOT to Use
- Sagas provide **eventual consistency** (not ACID isolation — other users may briefly observe intermediate `PENDING` states); design domain states (`RESERVING`, `PENDING_PAYMENT`) explicitly to handle intermediate visibility (`shadow-domain`).
