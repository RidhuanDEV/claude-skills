---
name: shadow-integrate
description: "External & Third-Party Integration Engineering. Use when integrating payment gateways (SNAP BI, Midtrans, Xendit, Stripe), HMAC webhooks with replay protection, SMTP/WhatsApp gateways, retries/circuit breakers, or Transactional Outbox."
---

# Shadow Integrate (`/shadow-integrate`) — Resilient Third-Party APIs, Webhooks & Outbox

Use this skill whenever integrating external services: payment gateways (Midtrans, Xendit, Stripe, SNAP BI), messaging/SMTP (WhatsApp, Email, FCM), government/enterprise APIs (SatuSehat, BSrE, Dukcapil, ERP), or incoming/outgoing webhooks.

---

## 1. Outbound Third-Party API Calls (Never Trust External Networks)

Every outbound HTTP call to an external provider MUST enforce:
1. **Explicit Connection & Read Timeouts**:
   - Never make an outbound `fetch` / `axios` / `httpx` / `http.Client` call with an infinite default timeout. Set explicit timeouts (e.g., `connectTimeout: 3000ms`, `responseTimeout: 8000ms`).
2. **Bounded Retry with Exponential Backoff + Full Jitter**:
   - Retry **ONLY** transient failures (`408`, `429 Too Many Requests` respecting `Retry-After`, `502`, `503`, `504`, network timeout).
   - **Never retry `400`, `401`, `403`, `404`, or `422` validation errors.**
   - After an ambiguous mutation timeout persist UNKNOWN and the correlation ID. Query provider status first if supported. Replay only inside the documented deduplication window with identical key, payload, account and operation under a verified provider guarantee. Otherwise reconcile manually. A transport acknowledgement alone leaves the business state pending.
3. **Anti-Corruption Adapter Layer**:
   - Wrap every third-party SDK/API behind a clean internal interface (`PaymentProvider`, `NotificationGateway`) and validate raw external JSON responses at the boundary before mapping into internal domain types.
   - Redact API keys, `Authorization` headers, and PII from all request/response integration logs.

---

## 2. Inbound Webhook Security & Idempotency Protocol

When receiving webhooks from external providers (Payment status, GitHub/GitLab, WhatsApp, courier tracking):
1. **Verify Cryptographic Signature (`HMAC-SHA256` / Asymmetric Signature) on Raw Body**:
   - Compare signatures using constant-time comparison (`crypto.timingSafeEqual` / `hmac.compare_digest`).
2. **Replay Attack Protection**:
   - Verify the provider-defined signed fields, timestamp unit, tolerable skew and retry window against its versioned contract. If timestamps are absent, use its documented replay mechanism. Prevent reordered notifications from reversing settled state unless a distinct verified reversal event permits it.
3. **Deduplicate by Provider `event_id` (`webhook_events` Ledger)**:
   - Providers deliver webhooks *at-least-once*. Insert `provider_event_id` with a `UNIQUE` constraint before processing; if already processed, return `200 OK` immediately without re-running side effects.
4. **Fast `200 OK` + Async Queue Processing**:
   - Durably accept the event and its processing obligation atomically before acknowledging under the provider contract. On redelivery distinguish pending work from an already applied effect.

---

## 3. Transactional Outbox Pattern (For Reliable Side Effects)

When a database transaction must trigger an email, webhook, or message queue event:
- Do NOT send the email/HTTP call inside the DB transaction.
- Instead, insert an `outbox_events` record inside the same DB transaction, and hand off durable locking, retry budgets, DLQ, and crash-before-ack idempotency semantics to `/shadow-concurrency`.
4. **Reconciliation & Partial Failure Safety**:
   - Pair asynchronous payment/ERP webhooks with scheduled **reconciliation jobs** (querying provider status APIs for unresolved `PENDING` transactions beyond SLA) so dropped webhooks or partial outages never leave ledger mismatches.

---

## 4. Official-First SDK Reuse & Publisher Verification (`OFFICIAL-FIRST-DEPENDENCY-POLICY.md`)
- Prefer official provider SDKs or existing trusted internal adapters over bespoke HTTP wrappers unless verified unmaintained/unsuitable. Inspect package publisher, upstream repo, engines, and advisories via `npm view` + `/context7` before installing, and emit the 8-field Decision Record.

Use `python scripts/reconcile_unknown.py --assess record.json` from this skill directory to review an ambiguous mutation offline. Supply the local operation ID, state, and only provider capabilities supported by evidence. A terminal inquiry must already be authenticated and bound to the same provider account, operation and transaction. The decision helper consumes those facts and makes no external calls. Run `--self-test` for the timeout, mismatched receipt and expired-window scenarios.
