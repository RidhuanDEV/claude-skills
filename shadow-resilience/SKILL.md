---
name: shadow-resilience
description: "Disaster Recovery & Business Continuity. Use when running automated DB backup restore drills (RPO/RTO verification), UU PDP erasure tombstone replay after restore, bulkhead isolation, circuit breakers, graceful degradation, rate-limited DLQ replay, or scoped staging fault injection. Do NOT use for infra provisioning (shadow-ops) or durable queue design (shadow-concurrency)."
---

# Shadow Resilience (`/shadow-resilience`) — Disaster Recovery Drills, RPO/RTO, Bulkheads & Graceful Degradation

A backup that has never been restored is **not** a backup. Use **`/shadow-resilience`** to verify that applications survive dependency outages gracefully and recover within contractual **RPO** (Recovery Point Objective) and **RTO** (Recovery Time Objective) without resurrecting erased personal data.

- **Owner:** Automated ephemeral backup restore drills & `drill_evidence.py` RPO/RTO receipts, post-restore UU PDP `erasure_tombstones` replay, bulkhead semaphores & circuit breakers, graceful degradation / `stale-if-error` fallbacks, rate-limited DLQ replay, and scoped fault injection (`L1`/`L3`/`L4`).
- **Boundaries:** Cloud/backup infrastructure provisioning (`shadow-ops`), durable outbox/queue schema design (`shadow-concurrency`), production SLO/alert setup (`shadow-observe`), and post-incident SLA/Harwat tracking (`shadow-maintain`).

## Reference Guide

Load ONLY the 1–2 modular playbooks needed for the active resilience subtask:

| Module | Topic | Load When |
| :--- | :--- | :--- |
| [01-automated-backup-restore-drills-and-rpo-rto.md](references/01-automated-backup-restore-drills-and-rpo-rto.md) | Ephemeral container restore drills, honest business RPO/RTO (`drill_evidence.py`), UU PDP `erasure_tombstones` replay, leak-proof teardown | Verifying DB backups, proving contractual RPO/RTO, preventing erased PII resurrection |
| [02-bulkheads-circuit-breakers-and-load-shedding.md](references/02-bulkheads-circuit-breakers-and-load-shedding.md) | `BulkheadSemaphore`, separate DB pools, 3-state Circuit Breaker, priority load shedding (`503 Retry-After`), retry budgets | Stopping heavy exports/AI workers or slow 3rd-party APIs from cascading into core API outages |
| [03-graceful-degradation-and-stale-fallbacks.md](references/03-graceful-degradation-and-stale-fallbacks.md) | Redis bypass/stale fallback, SMTP/WhatsApp outbox deferral, optional widget shedding, kill-switches, fail-closed auth/money rule | Designing resilient degradation matrices so soft dependency failures never cause blanket `500`s |
| [04-staging-fault-injection-and-dlq-recovery.md](references/04-staging-fault-injection-and-dlq-recovery.md) | Blast-radius progression (`L1` -> `L3` -> `L4`), poison-filtered rate-limited DLQ replay with health pause guard, GameDays | Recovering large backlogged DLQs safely or planning approved staging chaos drills |
| [evaluations.md](evaluations.md) | Graded specialist evaluation scenarios (`RES-EVAL-01..07`) | Auditing RPO/RTO honesty, erasure rehydration, bulkheads, safe DLQ replay, and `L4` drill isolation |

---

## 1. Automated Backup Restore Drill Protocol (Proving RPO & RTO)

> [!CAUTION]
> **Strict Isolation Rule (`L4` Guardrail)**: Always execute restore drills against an **isolated temporary container or disposable staging database** (`db_restore_drill_temp`), NEVER overwriting the live production database!

### The 5-Step Restore Drill Verification
1. **Fetch & Verify Latest Artifact:** Pull the latest `.dump` / `.sql.gz` / WAL archive and verify its `.sha256` checksum and separately stored decryption key.
2. **Spin Up Ephemeral Restore Container:** Launch an isolated Postgres/MySQL/MariaDB container (`--rm --label shadow.ephemeral=true` on `127.0.0.1:0`) inside a guaranteed `try / finally` (`trap EXIT`) block.
3. **Measure Technical Restore + Replay Erasure Tombstones:** Run `pg_restore` / `mysql` recording wall-clock seconds, then replay out-of-band UU PDP/GDPR `erasure_tombstones` BEFORE validating traffic so deleted user PII never resurrects (`test_restore_rehydration.py`).
4. **Measure Honest Business Recovery (`RTO` & `RPO`):** Start the recovery clock at `disruption_at` and stop at `business_verified_at` ONLY after an authorized representative completes the critical workflow with IAM, data, and network dependencies restored. Compare a known durable transaction/heartbeat sequence at disruption with `recovered_checkpoint_at` in the same timeline (an idle table supplies no loss estimate — mark RPO unmeasured when checkpoint coverage or keys are missing).
5. **Tear Down & Record Drill Evidence:** Execute `docker rm -f -v <container>` in `finally` (zero Docker leaks via `shadow_gate.py --check-docker-leaks`), validate receipts via `drill_evidence.py`, and archive an auditable monthly report (`docs/ops/restore-drill-YYYY-MM.md`).

---

## 2. Graceful Degradation, Bulkheads & Scoped Fault Recovery

- **Bulkheads:** Isolate heavy PDF/Excel exports, BI reports, and AI workers behind bounded `BulkheadSemaphore` limits, dedicated DB pools/read replicas, and separate containers so surges fast-fail (`503 Retry-After`) without starving Tier-0 auth/checkout.
- **Graceful Degradation (Never Fail-Open on Auth/Money!):** Bypass/stale-fallback Redis outages (with DB bulkhead), defer SMTP/WhatsApp notifications via `outbox_events`, shed non-critical UI widgets via runtime kill-switches — while keeping authentication, authorization, and financial ledger writes strictly **fail-closed**.
- **Scoped Fault Injection & Safe DLQ Replay:** Keep local CI fault stubs at `L1`; obtain explicit `L3`/`L4` approval before shared staging/production chaos tests. Replay large DLQ backlogs strictly after poison-pill filtering, canary testing, and rate-limiting with automatic DB-pool pause guards.

---

## 3. Deterministic Drill Evidence & Rehydration Verification

Run `drill_evidence.py` on recorded offset-aware ISO timestamps (`disruption_at`, `business_verified_at`, `recovered_checkpoint_at`) and boolean receipts (`required_dependencies_verified`, `consumer_workflow_passed`, `checkpoint_verified_in_source_timeline`). Exit `1` identifies incomplete measurements:

```powershell
python shadow-resilience/scripts/drill_evidence.py path/to/drill_receipt.json
python -m unittest discover -s shadow-resilience/tests -v
```
