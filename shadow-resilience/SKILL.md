---
name: shadow-resilience
description: Disaster Recovery (DR), Automated Backup Restore Drills, RPO/RTO Verification, Graceful Degradation, Circuit Breakers, Chaos/Failure Injection, and Business Continuity Planning. Pairs with /shadow-ops. Trigger with /shadow-resilience.
---

# Shadow Resilience (`/shadow-resilience`) — Disaster Recovery Drills, RPO/RTO & Graceful Degradation

A backup that has never been restored is **not** a backup. Use **`/shadow-resilience`** to verify that the application survives dependency outages and can be recovered within contractual **RPO** (Recovery Point Objective) and **RTO** (Recovery Time Objective).

---

## 1. Automated Backup Restore Drill Protocol (Proving RPO & RTO)

> [!CAUTION]
> **Strict Isolation Rule**: Always execute restore drills against an **isolated temporary container or staging database** (`db_restore_drill_temp`), NEVER overwriting the live production database!

### The 5-Step Restore Drill Verification
1. **Fetch Latest Production Backup Artifact**: Pull the latest `.dump` / `.sql.gz` from backup storage and verify its `.sha256` checksum.
2. **Spin Up Ephemeral Restore Container**: Launch an isolated Postgres/MySQL container (`postgres:16-alpine` on a temporary local port).
3. **Execute Restore & Measure Duration (`Actual RTO`)**:
   - Run `pg_restore` or `gunzip < backup.sql.gz | mysql` and record elapsed wall-clock seconds.
4. **Verify Data Integrity & Recency (`Actual RPO`)**:
   - Query row counts on core transaction tables (`users`, `orders`, `audit_logs`) and check `MAX(created_at)` to verify the data lag is within the target RPO.
5. **Tear Down & Log Drill Evidence**:
   - Destroy the temporary container and write an auditable drill report (`docs/ops/restore-drill-YYYY-MM.md` — compatible with `/shadow-doc` monthly maintenance reports!).

---

## 2. Graceful Degradation & Fault-Isolation Patterns

Design the application so a non-critical subsystem failure never takes down the entire system:

| Failure Scenario | Bad Behavior (Fragile) | Resilient Behavior (`/shadow-resilience`) |
| :--- | :--- | :--- |
| **Redis Cache Down** | Every API call throws `500 Internal Server Error` | Log warning, bypass cache (or serve stale in-memory fallback with rate limit), keep core auth/transactions working. |
| **SMTP / WhatsApp Gateway Down** | User registration or order approval hangs for 60s then fails `500` | Commit DB transaction + write to `outbox_events`; background worker retries delivery when gateway recovers. |
| **Analytics / Export Worker OOM** | Crashes main API process sharing the same container | Isolate heavy report/export workers into a separate process/container with bounded memory limits. |
| **Database Connection Spike** | App opens 1,000 raw connections and crashes Postgres | Enforce bounded connection pool (`max: 20`) + `PgBouncer` + fast queue timeout (`5s`) returning `503 Retry-After`. |
