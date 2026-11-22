# 05 — Queue & Reliability Engineering (`ADVANCED`)

## 1. Purpose & Activation Conditions
Load when building reliable email dispatch pipelines (`email_outbox`, BullMQ/Postgres `SKIP LOCKED`), isolating OTP priority lanes from promo surges, tuning retry/DLQ policies, or implementing per-domain MX backpressure.

## 2. Prerequisites
Modules `01`–`03` and `/shadow-concurrency` (Transactional Outbox & retry patterns).

## 3. Technical Principles & Constraints
- **Transactional Outbox Atomicity:** Write domain state (`orders`/`users`) AND `email_outbox` row in ONE database transaction so commits never drop emails and rolled-back transactions never send phantom confirmations.
- **Priority Bulkhead Lanes:** Run **separate queues & workers** for `TRANSACTIONAL_SECURITY` (OTP/reset, `< 5s` p95 SLA), `TRANSACTIONAL_RECEIPT` (`< 30s`), and `MARKETING_BULK` (rate-paced background). Never let an 80,000-message campaign sit ahead of a login OTP!
- **Per-Destination MX Rate Pacing & Coalescing:** Large bursts to `gmail.com` or `yahoo.com` trigger `4.7.28` deferrals. Pace bulk workers per destination domain and coalesce chatty notifications (e.g., 15 comments in 5 minutes -> 1 digest).

## 4. Architecture & Implementation
```sql
CREATE TABLE email_outbox (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  idempotency_key text NOT NULL UNIQUE,
  stream text NOT NULL CHECK (stream IN ('TRANSACTIONAL_SECURITY', 'TRANSACTIONAL_RECEIPT', 'SUBSCRIBED_DIGEST', 'MARKETING_BULK')),
  priority smallint NOT NULL DEFAULT 50, -- 1 = OTP/Security, 20 = Receipt, 80 = Marketing
  recipient_hmac bytea NOT NULL,
  recipient_domain text NOT NULL,        -- e.g. 'gmail.com' for per-MX pacing
  template_id text NOT NULL,
  payload_json jsonb NOT NULL,
  status text NOT NULL DEFAULT 'PENDING' CHECK (status IN ('PENDING', 'PROCESSING', 'SENT', 'SUPPRESSED', 'DLQ_FAILED')),
  attempts int NOT NULL DEFAULT 0,
  next_attempt_at timestamptz NOT NULL DEFAULT now(),
  provider_message_id text,
  last_error_code text,
  created_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX idx_email_outbox_lane_due
  ON email_outbox (priority ASC, next_attempt_at ASC)
  WHERE status = 'PENDING';
```
Claim rows safely across concurrent workers with `SELECT ... FROM email_outbox WHERE status = 'PENDING' AND next_attempt_at <= now() ORDER BY priority, next_attempt_at FOR UPDATE SKIP LOCKED LIMIT 25`.

## 5. Platform / Vendor Variations
- **BullMQ / Redis:** Use dedicated queues (`email:critical`, `email:bulk`) with BullMQ rate-limiter group keys by `recipient_domain` and `attempts: 5` exponential backoff with jitter.
- **PostgreSQL-Only Stack (Right-Sized):** `email_outbox` + `FOR UPDATE SKIP LOCKED` handles tens of thousands of emails/hour cleanly without adding Redis infrastructure.

## 6. Decision Matrix & Trade-Offs
| Error Type on Send | Retry Policy | DLQ / Action |
| :--- | :--- | :--- |
| Pre-accept `429` / `503` / `4.x.x` defer | Full-jitter exponential backoff (`30s -> 2m -> 10m -> 1h`, max `24h` bulk / `5m` OTP) | Fail to `DLQ_FAILED` after max attempts; **expire OTPs past TTL (`10m`) rather than delivering stale codes!** |
| `5.1.1` Hard Bounce / `400` Bad Payload | **0 retries** | Mark `SUPPRESSED` or `DLQ_FAILED` immediately |
| Recipient exists in `email_suppressions` | **Skip pre-send (`0` ESP call)** | Mark `SUPPRESSED` cleanly |
| Ambiguous POST timeout (`ETIMEDOUT` after write) | **Do NOT blindly re-send** | Reconcile via provider idempotency key / lookup API before deciding |

## 7. Real Production Scenario
A marketing blast queued 80,000 promo emails into a single FIFO BullMQ queue; login OTPs sat behind the backlog for 18 minutes, causing customer lockouts and expired OTP retries. Splitting `email:critical` (dedicated concurrency + `expires_at` TTL drop) from `email:bulk` (rate-limited per MX domain) kept OTP delivery under `1.8s` even during peak promo campaigns.

## 8. Failure Modes & Edge Cases (`WRONG` vs `RIGHT`)
- **WRONG:** Retrying expired 5-minute login OTPs 2 hours later after an outage (confuses users & floods inboxes with dead codes!).
  **RIGHT:** Enforce `expires_at` on time-sensitive OTP/security rows; skip and mark `EXPIRED` if `now() > expires_at`.
- **WRONG:** Replaying an entire DLQ backlog at full speed after an incident without re-checking `email_suppressions`.
  **RIGHT:** Always pass DLQ replays through the suppression gate and rate-limiter.

## 9. Testing & Verification
Write integration tests proving: (1) duplicate `idempotency_key` inserts are rejected/ignored cleanly, (2) critical priority=1 OTP overtakes 1,000 pending bulk rows, (3) expired OTPs are not dispatched, and (4) suppressed `recipient_hmac` rows never hit `EmailProviderPort.send()`.

## 10. Operational Considerations
Monitor `queue_depth{stream}`, `time_to_first_attempt_p95{stream}`, `dlq_count`, and `suppressed_skips` (Module `10`).

## 11. Authoritative References
- `/shadow-concurrency` (`04-queues-brokers-sagas-and-fencing-locks.md`); PostgreSQL `SKIP LOCKED` & BullMQ Rate Limiting documentation.

## 12. Limitations & When NOT to Use
Do not store plaintext OTPs or reset secrets indefinitely in `email_outbox.payload_json` — purge or redact `payload_json` immediately upon `SENT`/`EXPIRED` completion.
