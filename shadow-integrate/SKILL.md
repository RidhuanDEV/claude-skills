---
name: shadow-integrate
description: "Use when integrating payment gateways, HMAC webhooks, third-party retries, or ambiguous transaction reconciliation."
---

# Shadow Integrate (`/shadow-integrate`) — Resilient Third-Party APIs, Webhooks & Reconciliation

Use this skill whenever the **Monarch** integrates external services: payment gateways (`SNAP BI`, `Midtrans`, `Xendit`, `Stripe`), messaging/government/enterprise APIs (`WhatsApp`, `SatuSehat`, `BSrE`, `ERP`), inbound/outbound webhooks, or payment reconciliation jobs.

## 1. Core Integration Principles & Non-Negotiables

1. **Official-First Adapters & Explicit Timeouts:** Reuse trusted internal adapters or verify official SDK provenance (`npm view` + `/context7`) before installing (`OFFICIAL-FIRST-DEPENDENCY-POLICY.md`). Wrap every vendor behind an internal Anti-Corruption Port with explicit connect (`2–3s`) & response (`5–10s`) timeouts (`AbortSignal.timeout`), validated boundary responses, and redacted `Authorization`/secret logs.
2. **Hardened Inbound Webhooks (`Raw Body -> Timing-Safe -> Durable Inbox -> Fast 200`):** Verify cryptographic signatures (`HMAC-SHA256` / SHA-512 / RSA) strictly over **raw unparsed bytes** using `crypto.timingSafeEqual` with dual-secret rotation arrays. Enforce replay windows, insert `UNIQUE (provider, provider_event_id)` into `webhook_inbox_events` BEFORE returning `200`, validate `orderId`/`currency`/`amountMinor`, and prevent out-of-order notifications from reverting `SETTLED` state.
3. **Never Treat Mutation Timeouts as `FAILED` (`UNKNOWN` Recovery):** Persist `UNKNOWN_PENDING_RECONCILE` + correlation ID on ambiguous timeouts; query authenticated provider Status Inquiry first (verifying identical account/operation/tx/amount); replay ONLY inside a verified provider deduplication window with identical key/payload/account — otherwise escalate to manual reconciliation.
4. **Retries, Circuit Breakers & Reconciliation Safety Net:** Retry ONLY transient errors (`408`, `429` honoring `Retry-After`, `502/503/504`) with Exponential Backoff + Full Jitter (`0` retries on `400/401/403/404/422`), isolate outages via Circuit Breakers, use Transactional Outbox (`/shadow-concurrency`) for durable triggers, NEVER settle orders from browser return URLs, and run 5–15m + `T+1` reconciliation jobs.

## 2. Deterministic Offline Verification CLI & Scenario Benchmarks

Run offline checks (`L0`/`L1`, zero external network calls) before claiming `VERIFIED-LOCAL`:
```powershell
python "shadow-integrate/scripts/reconcile_unknown.py" --self-test
python "shadow-integrate/scripts/reconcile_unknown.py" --assess path/to/unknown_record.json
python -m unittest discover -s "shadow-integrate/tests" -v
```
Supply `reconcile_unknown.py --assess` strictly with verified local operation ID, state, and evidence-backed provider capabilities (a terminal inquiry must set verified to true and match operation_id, account, currency, provider_tx_id, and integer amount_minor on both the local record and the inquiry). Graded specialist scenarios live in [evaluations.md](evaluations.md) (7 scenarios).

## Reference Guide

Load **only** the 1–2 modules matching the active subtask (never load all 4 at once):

| Task / Scenario | Tier | Load Reference |
| :--- | :--- | :--- |
| Official-first SDK verification, Anti-Corruption Port adapters, explicit timeouts & log redaction | CORE | [references/01-official-first-adapters-and-timeouts.md](references/01-official-first-adapters-and-timeouts.md) |
| Raw-body dual-secret HMAC/RSA webhooks, replay windows, durable inbox dedup & monotonic state | CORE | [references/02-hmac-webhooks-replay-and-ordering.md](references/02-hmac-webhooks-replay-and-ordering.md) |
| Full-Jitter transient retries, Circuit Breakers & `reconcile_unknown.py` timeout recovery | CORE | [references/03-retries-circuit-breakers-and-unknown-recovery.md](references/03-retries-circuit-breakers-and-unknown-recovery.md) |
| SNAP BI / Midtrans / Xendit / Stripe specifics, closed VA/QRIS & scheduled `T+1` reconciliation | SPECIALIST | [references/04-payment-gateways-snap-bi-and-reconciliation.md](references/04-payment-gateways-snap-bi-and-reconciliation.md) |

Do not load unrelated references unnecessarily.
