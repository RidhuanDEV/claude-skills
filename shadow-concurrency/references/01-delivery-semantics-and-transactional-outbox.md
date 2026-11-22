# 01. Delivery Semantics & Transactional Outbox

## 1. Purpose & Activation Conditions
Eliminate dual-write inconsistency (DB committed but queue event lost, or queue event sent before DB rollback) by enforcing **At-Least-Once Delivery + Idempotent Deduplication** via the **Transactional Outbox** pattern. Load when triggering emails, webhooks, notifications, or cross-service events from database writes.

## 2. Prerequisites
- Relational database supporting ACID transactions (`shadow-data`) and explicit business state transitions (`shadow-domain`).

## 3. Technical Principles & Constraints
- **Reject the "Exactly-Once External Side Effect" Myth:** Over an unreliable network, an external side effect (SMTP send, payment charge, third-party webhook) **CANNOT** be guaranteed "exactly-once" by the sender alone — a worker can always crash AFTER the remote server executes the request and BEFORE the local DB marks it `SENT`!
- **Canonical Ordering Invariant (`commit -> outbox -> dispatch -> ack`):**
  1. Write the domain mutation AND the `outbox_events` row (`event_id`, `idempotency_key`, `event_type`, `payload`, `status = 'PENDING'`, `available_at`) inside the **exact same ACID DB transaction**.
  2. Never publish to RabbitMQ/Kafka/BullMQ/SMTP BEFORE `COMMIT` (consumers read uncommitted/rolled-back rows -> phantom side effects!).
  3. A separate relay worker polls or tails committed outbox rows via `SELECT ... FOR UPDATE SKIP LOCKED`, dispatches with the persistent `idempotency_key`, and transitions `PENDING -> SENT` only after confirmed delivery/acceptance!
- **Atomic Worker Claiming (`SKIP LOCKED` / Lease Expiry):** Multiple parallel relay workers MUST claim disjoint batches atomically (`FOR UPDATE SKIP LOCKED` + setting `locked_until = NOW() + INTERVAL '60 seconds'` and `status = 'IN_PROGRESS'`) so crashed workers' stuck jobs automatically recover after lease expiry without blocking healthy workers!

## 4. Architecture & Implementation
```sql
-- Authoritative Transactional Outbox Table with Lease Recovery & Priority Ordering (PostgreSQL)
CREATE TABLE outbox_events (
  id              UUID PRIMARY KEY,                 -- UUIDv7
  tenant_id       UUID NOT NULL,
  aggregate_type  TEXT NOT NULL,
  aggregate_id    TEXT NOT NULL,
  event_type      TEXT NOT NULL,                    -- e.g. 'email.otp.v1', 'order.paid.v1'
  idempotency_key TEXT NOT NULL UNIQUE,
  payload         JSONB NOT NULL,
  status          TEXT NOT NULL DEFAULT 'PENDING' CHECK (status IN ('PENDING', 'IN_PROGRESS', 'SENT', 'DEAD_LETTER')),
  attempts        INTEGER NOT NULL DEFAULT 0,
  max_attempts    INTEGER NOT NULL DEFAULT 5,
  available_at    TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  locked_until    TIMESTAMPTZ,
  last_error      TEXT,
  created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Partial index keeps active polling tiny even when historical archive grows
CREATE INDEX idx_outbox_claimable ON outbox_events (available_at, id)
  WHERE status IN ('PENDING', 'IN_PROGRESS');

-- Atomic crash-recoverable batch claim by competing relay workers
WITH claimed AS (
  SELECT id
  FROM outbox_events
  WHERE (status = 'PENDING' AND available_at <= NOW())
     OR (status = 'IN_PROGRESS' AND locked_until <= NOW()) -- Reclaim crashed worker lease!
  ORDER BY available_at ASC, id ASC
  FOR UPDATE SKIP LOCKED
  LIMIT $1
)
UPDATE outbox_events o
SET status       = 'IN_PROGRESS',
    attempts     = o.attempts + 1,
    locked_until = NOW() + INTERVAL '60 seconds'
FROM claimed c
WHERE o.id = c.id
RETURNING o.*;
```

## 5. Platform / Vendor Variations
| Relay Mechanism | Latency | Infra Complexity | Best Fit |
| :--- | :---: | :---: | :--- |
| **PostgreSQL `FOR UPDATE SKIP LOCKED` Poller** | `50–500ms` | **Minimal (0 extra brokers)** | `< 500` events/sec, most SaaS & fintech services |
| **Postgres `LISTEN`/`NOTIFY` + `SKIP LOCKED` Fallback** | `< 20ms` | Low | Low-latency OTP/realtime notifications (keep periodic poll fallback since `NOTIFY` is non-durable!) |
| **Debezium WAL Outbox Event Router -> Kafka** | `< 50ms` | High | High-throughput multi-service event meshes (`> 1,000` events/sec) |

## 6. Decision Matrix & Trade-Offs
| Publishing Pattern | Survives DB Rollback? | Survives Broker Outage? | Verdict |
| :--- | :---: | :---: | :--- |
| **Direct `await queue.add()` inside HTTP handler** | No (dual-write race!) | No (drops event!) | **FORBIDDEN for critical side effects** |
| **Transactional Outbox (`commit -> outbox -> dispatch`)** | **YES** | **YES (buffered safely in DB)** | **Mandatory standard** |

## 7. Real Production Scenario
An order API executes `await db.orders.create(order)` and then `await bullmq.add('send-receipt', order)`. During a 90-second Redis failover, 310 customer orders commit in PostgreSQL while `bullmq.add` throws `ECONNREFUSED`, permanently losing receipt emails and fulfillment triggers. Moving event emission into `outbox_events` inside the order commit transaction ensures zero lost triggers — once Redis/SMTP recovers, the relay drains all 310 rows automatically.

## 8. Failure Modes & Edge Cases
- **WRONG:** Deleting or marking an outbox row `SENT` *before* the downstream broker/SMTP server confirms acceptance (crash loses the message permanently!).
- **RIGHT:** Transition `IN_PROGRESS -> SENT` strictly AFTER confirmed broker/ESP acceptance, preserving `idempotency_key` across retries.
- **WRONG:** Letting completed `SENT` outbox rows accumulate forever without retention/partitioning (bloats table and slows autovacuum — `shadow-db` Module `05`).
- **RIGHT:** Tune aggressive per-table autovacuum (`scale_factor = 0.01`) and prune/archive `SENT` rows older than 7–14 days in bounded batches or monthly partitions.

## 9. Testing & Verification
- Run `python shadow-concurrency/scripts/concurrency_invariant_checker.py --self-test` and `python -m unittest discover -s shadow-concurrency/tests -v`.
- Integration-test competing workers: spawn 5 concurrent claimers against 10 outbox rows -> assert every row is claimed by **at most 1** worker simultaneously (`SKIP LOCKED`), and simulate an expired `locked_until` lease -> assert clean reclaim!

## 10. Operational Considerations
- Alert on `COUNT(*) WHERE status = 'PENDING' AND available_at < NOW() - INTERVAL '5 minutes'` (stuck relay worker) and `status = 'DEAD_LETTER' > 0`.

## 11. Authoritative References
- Chris Richardson — *Pattern: Transactional Outbox* (`https://microservices.io/patterns/data/transactional-outbox.html`).
- PostgreSQL Documentation — *`FOR UPDATE SKIP LOCKED`* (`https://www.postgresql.org/docs/current/sql-select.html#SQL-FOR-UPDATE-SHARE`).

## 12. Limitations & When NOT to Use
- Do NOT put high-volume ephemeral UI clickstream telemetry (`Page_Viewed`) into an OLTP PostgreSQL outbox table — reserve Transactional Outbox strictly for durable domain/financial/notification side effects!
