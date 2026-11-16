# State Machine, Failure Matrix & Recovery Runbook

## 1. Failure Boundary Matrix
| Stage | Durable State Before Action | Action | Failure Recovery |
|---|---|---|---|
| `PENDING -> PROCESSING` | Atomic DB claim + `attempt_count + 1` | Lease with visibility timeout `T_lease` | Reclaimer resets expired leases where `attempt_count < max_attempts` |
| `PROCESSING -> COMPLETED` | Side effect recorded in `inbox_dedup` / `outbox.sent_at` | Broker `ACK` | On crash before `ACK`, broker redelivers -> worker hits dedup key -> skips side effect and `ACK`s cleanly |
| `PROCESSING -> DLQ` | `attempt_count >= max_attempts` | Persist `last_error` (redacted) in `dlq_jobs` | Manual inspect -> fix root bug -> replay via idempotent replay CLI |
