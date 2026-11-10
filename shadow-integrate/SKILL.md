---
name: shadow-integrate
description: External & Third-Party Integration Engineering: Payment Gateways, Webhooks (HMAC Signature + Replay Protection), SMTP/Notifications, Government/Partner REST & SOAP APIs, Timeouts, Exponential Backoff Retries, Circuit Breakers, and Transactional Outbox. Trigger with /shadow-integrate.
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
   - Attach an `Idempotency-Key` when retrying mutating `POST` requests so a network timeout after server execution never double-charges a user.
3. **Anti-Corruption Adapter Layer**:
   - Wrap every third-party SDK/API behind a clean internal interface (`PaymentProvider`, `NotificationGateway`) and validate raw external JSON responses at the boundary before mapping into internal domain types.
   - Redact API keys, `Authorization` headers, and PII from all request/response integration logs.

---

## 2. Inbound Webhook Security & Idempotency Protocol

When receiving webhooks from external providers (Payment status, GitHub/GitLab, WhatsApp, courier tracking):
1. **Verify Cryptographic Signature (`HMAC-SHA256` / Asymmetric Signature) on Raw Body**:
   - Compare signatures using constant-time comparison (`crypto.timingSafeEqual` / `hmac.compare_digest`).
2. **Replay Attack Protection**:
   - Reject webhook payloads whose timestamp header is older than `5 minutes`.
3. **Deduplicate by Provider `event_id` (`webhook_events` Ledger)**:
   - Providers deliver webhooks *at-least-once*. Insert `provider_event_id` with a `UNIQUE` constraint before processing; if already processed, return `200 OK` immediately without re-running side effects.
4. **Fast `200 OK` + Async Queue Processing**:
   - Persist the verified webhook payload and enqueue background processing so the webhook endpoint responds within `< 500ms`.

---

## 3. Transactional Outbox Pattern (For Reliable Side Effects)

When a database transaction must trigger an email, webhook, or message queue event:
- Do NOT send the email/HTTP call inside the DB transaction.
- Instead, insert an `outbox_events` record inside the same DB transaction, and let a background worker poll/stream and deliver it with retries (`PENDING -> PROCESSING -> PUBLISHED | DEAD_LETTER`).
