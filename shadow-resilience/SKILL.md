---
name: shadow-resilience
description: "Disaster Recovery & Business Continuity. Use when running automated DB backup restore drills (RPO/RTO verification), chaos/fault injection, circuit breakers, or graceful degradation planning."
---

# Shadow Resilience (`/shadow-resilience`) — Disaster Recovery Drills, RPO/RTO & Graceful Degradation

A backup that has never been restored is **not** a backup. Use **`/shadow-resilience`** to verify that the application survives dependency outages and can be recovered within contractual **RPO** (Recovery Point Objective) and **RTO** (Recovery Time Objective).

---

## 1. Automated Backup Restore Drill Protocol (Proving RPO & RTO)

> [!CAUTION]
> **Strict Isolation Rule**: Always execute restore drills against an **isolated temporary container or staging database** (`db_restore_drill_temp`), NEVER overwriting the live production database!

### The 5-Step Restore Drill Verification
1. **Fetch Latest Production Backup Artifact**: Pull the latest `.dump` / `.sql.gz` from backup storage and verify its `.sha256` checksum.
2. **Spin Up Ephemeral Restore Container**: Launch an isolated Postgres/MySQL/MariaDB container (`--rm --label shadow.ephemeral=true` on a temporary local port) inside a `try / finally` (`trap EXIT`) block.
3. **Measure technical restore time**.
   - Run `pg_restore` or `gunzip < backup.sql.gz | mysql` and record elapsed wall-clock seconds.
4. **Measure business recovery**. Start the recovery clock at the agreed disruption timestamp and stop after an authorized representative completes the critical workflow with its IAM, data and network dependencies restored.
   - Compare a known durable transaction or heartbeat sequence at disruption with the recovered checkpoint in the same timeline. An idle table supplies no loss estimate. Record RPO as unmeasured when checkpoint coverage is missing. Missing decryption keys or consumer validation leave recovery unverified.
5. **Tear Down & Log Drill Evidence**:
   - Always execute `docker rm -f -v <container>` (and `docker image rm -f <temp-image>` if a custom image was built) in the `finally` block so zero stopped containers or orphan volumes remain, then write an auditable drill report (`docs/ops/restore-drill-YYYY-MM.md` — compatible with `/shadow-doc` monthly maintenance reports!).

---

## 2. Graceful Degradation & Fault-Isolation Patterns

Design the application so a non-critical subsystem failure never takes down the entire system:

| Failure Scenario | Bad Behavior (Fragile) | Resilient Behavior (`/shadow-resilience`) |
| :--- | :--- | :--- |
| **Redis Cache Down** | Every API call throws `500 Internal Server Error` | Log warning, bypass cache (or serve stale in-memory fallback with rate limit), keep core auth/transactions working. |
| **SMTP / WhatsApp Gateway Down** | User registration or order approval hangs for 60s then fails `500` | Commit DB transaction + write to `outbox_events`; background worker retries delivery when gateway recovers. |
| **Analytics / Export Worker OOM** | Crashes main API process sharing the same container | Isolate heavy report/export workers into a separate process/container with bounded memory limits. |
| **Database Connection Spike** | App opens 1,000 raw connections and crashes Postgres | Enforce bounded connection pool (`max: 20`) + `PgBouncer` + fast queue timeout (`5s`) returning `503 Retry-After`. |

---

## 3. Scoped Fault Injection, Bulkheads & Queue Recovery
- Run failure-injection tests strictly against isolated staging/test fixtures (never live production without explicit authorization): inject dependency HTTP 503s, broker disconnects, and slow-consumer stalls.
- Isolate critical APIs from heavy export/AI workers using separate pools/queues (**bulkheads**) and verify dead-letter queue replay procedures (`/shadow-concurrency`) restore backlog safely without exceeding DB pool budgets.

For an existing isolated drill, run `python shadow-resilience/scripts/drill_evidence.py drill.json` on its recorded measurements. Provide offset-aware ISO timestamps in `disruption_at`, `business_verified_at` and `recovered_checkpoint_at`. Set `required_dependencies_verified`, `consumer_workflow_passed` and `checkpoint_verified_in_source_timeline` from drill receipts. Retain those receipts with the report. Exit 1 identifies incomplete measurements. Compare each measured value to the business owner's agreed objective.

## Reference Guide

| Task / Scenario | Load Reference |
| :--- | :--- |
| Bulkhead Concurrency Semaphores, Stale-Cache Fallback, Feature Shedding & Ephemeral Restore Drills | [references/degradation-bulkheads-and-drills.md](references/degradation-bulkheads-and-drills.md) |

Do not load unrelated references unnecessarily.
