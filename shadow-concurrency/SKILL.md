---
name: shadow-concurrency
description: "Asynchronous & Distributed Workflow Correctness Specialist. Use when designing or fixing message queues, retries/backoff, transactional outbox/inbox deduplication, crash-before-ack recovery, monotonic fencing-token locks, sagas, or DLQ poison messages. Do NOT use for third-party payment HTTP/HMAC adapters (/shadow-integrate), WebSocket/SSE client reconnect UX (/shadow-realtime), or standalone SQL schema design (/shadow-data, /shadow-db)."
---

# Shadow Concurrency (`/shadow-concurrency`) — Async Workflows, Outbox/Inbox & Distributed Locks

- **Owner:** Consistency, delivery semantics, transactional outbox/inbox deduplication, crash-before-ack recovery, full-jitter retries, DLQ replay, sagas, and monotonic fencing-token locks.
- **Boundaries:** External HTTP/HMAC payment adapters (`/shadow-integrate`), WebSocket/SSE stream resume (`/shadow-realtime`), SQL migration DDL (`/shadow-data`/`/shadow-db`).

## 1. Core Invariants & Non-Claims

1. **No False Exactly-Once Claims:** External side effects (SMTP, payment APIs, webhooks) cannot guarantee unassisted "exactly-once"; engineer for **At-Least-Once Delivery + Idempotent Deduplication**.
2. **Durable Commit Before Ack (`commit -> outbox -> dispatch -> ack`):** Insert domain state + `outbox_events` inside one ACID DB transaction; claim via `FOR UPDATE SKIP LOCKED` with lease expiry; deduplicate consumers atomically inside `inbox_dedup` in the same DB transaction as state updates.
3. **Bounded Backoff, Backpressure & DLQ:** Classify transient vs permanent failures, apply exponential backoff + full jitter, cap concurrency & drain cleanly on `SIGTERM`, and route poison messages to DLQ with audited throttled replay.
4. **Monotonic Fencing Tokens & Right-Sized Brokers:** Start with Postgres `SKIP LOCKED` (`< 500` jobs/s) before Kafka; pair distributed lease locks with storage-checked monotonic `fencing_token` guards (`WHERE fencing_token < $token`).

## 2. Playbooks & Deterministic Replay Checker

Read [`methodologies/DURABLE-ASYNC-OUTBOX-AND-IDEMPOTENCY.md`](methodologies/DURABLE-ASYNC-OUTBOX-AND-IDEMPOTENCY.md) and [`playbooks/STATE-MACHINE-AND-FAILURE-MATRIX.md`](playbooks/STATE-MACHINE-AND-FAILURE-MATRIX.md), then verify offline (`L0`/`L1`):
```powershell
python "shadow-concurrency/scripts/concurrency_invariant_checker.py" --self-test
python "shadow-concurrency/scripts/concurrency_invariant_checker.py" --verify-workflow path/to/workflow.json
python -m unittest discover -s "shadow-concurrency/tests" -v
```
Graded specialist scenarios live in [evaluations.md](evaluations.md) (7 scenarios including crash-after-SMTP-before-ack duplicates, dual-write Redis outage, wallet replay double-credit, poison spin-loops, and zombie GC locks).

## Reference Guide

Load **only** the 1–2 modules matching the active subtask (never load all 4 at once):

| Task / Scenario | Tier | Load Reference |
| :--- | :--- | :--- |
| At-least-once semantics, Transactional Outbox SQL, `FOR UPDATE SKIP LOCKED` & lease recovery | CORE | [references/01-delivery-semantics-and-transactional-outbox.md](references/01-delivery-semantics-and-transactional-outbox.md) |
| Atomic `inbox_dedup` transactions, crash-before-ack recovery & monotonic version ordering | CORE | [references/02-inbox-deduplication-and-crash-before-ack.md](references/02-inbox-deduplication-and-crash-before-ack.md) |
| Failure classification, Full-Jitter exponential backoff, backpressure, `SIGTERM` drain & DLQ replay | CORE | [references/03-retries-backoff-backpressure-and-dlq.md](references/03-retries-backoff-backpressure-and-dlq.md) |
| Queue/broker selection (PG/BullMQ/RabbitMQ/Kafka/Temporal), Sagas, fencing tokens & token bucket | ADVANCED | [references/04-queues-brokers-sagas-and-fencing-locks.md](references/04-queues-brokers-sagas-and-fencing-locks.md) |

Do not load unrelated references unnecessarily.
