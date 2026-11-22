# 02. HMAC Webhooks, Replay Protection & Ordering Guards

## 1. Purpose & Activation Conditions
Receive inbound webhooks from payment gateways, couriers, and SaaS platforms (`Midtrans`, `Xendit`, `Stripe`, `SNAP BI`, `GitHub`) securely and idempotently — blocking forged payloads, replay attacks, duplicate deliveries, and out-of-order state regressions. Load whenever implementing or auditing any inbound webhook endpoint.

## 2. Prerequisites
- Raw-body HTTP middleware (preserving exact unparsed bytes before `JSON.parse`), persistent `webhook_events` dedup table, and durable async queue (`/shadow-concurrency`).

## 3. Technical Principles & Constraints
- **5-Step Inbound Webhook Hardening Protocol (Non-Negotiable):**
  1. **Raw-Body Cryptographic Verification:** Compute HMAC-SHA256 (or provider RSA/SHA-512 signature per exact versioned vendor spec) strictly over the **exact unparsed raw request bytes** — NEVER re-serialize `JSON.stringify(req.body)`! Compare signatures with **`crypto.timingSafeEqual`** (constant-time) supporting **dual active secrets (`[current, previous]`)** for zero-downtime secret rotation!
  2. **Replay-Attack Protection:** Verify provider timestamp field/unit against a bounded skew window (e.g., `<= 300s` where signed timestamps exist, matching the provider's documented retry/skew spec!). Where a provider lacks signed timestamps (e.g., Midtrans SHA-512), pair signature checks with unique `(provider, provider_event_id)` deduplication + amount/status cross-check!
  3. **Durable Atomic Accept Before `200 OK`:** Persist `(provider, provider_event_id, payload, status='ACCEPTED')` with a `UNIQUE (provider, provider_event_id)` constraint **BEFORE returning `200 OK`**!
     - If duplicate `provider_event_id` arrives: distinguish whether effect is already `APPLIED` (return `200 OK` idempotent no-op!) vs `PENDING` (ensure enqueued, return `200 OK`).
     - If DB write fails: intentionally return **`500`** so the provider retries safely! NEVER return `200 OK` and drop the event in memory!
  4. **Out-of-Order & Monotonic State Protection (CRITICAL):** Providers frequently deliver `PENDING` *after* `SETTLED` due to retries! NEVER allow a stale/reordered notification to revert an already-`SETTLED`/`PAID` transaction back to `PENDING` or `EXPIRED` unless a distinct verified reversal/refund/chargeback event explicitly permits it!
  5. **Amount & Identity Cross-Verification:** Before settling any invoice/order from a webhook, assert `webhook.orderId === dbOrder.id`, `webhook.currency === dbOrder.currency`, AND `webhook.amountMinor === dbOrder.totalMinor`!

## 4. Architecture & Implementation
```typescript
import { createHmac, timingSafeEqual } from 'node:crypto';

export function verifyWebhookHmacDualSecret(
  rawBody: Buffer,
  headerSignatureHex: string,
  timestampSec: number,
  activeSecrets: readonly string[],
  maxSkewSec = 300,
  nowSec: number = Math.floor(Date.now() / 1000)
): boolean {
  if (!Number.isFinite(timestampSec) || Math.abs(nowSec - timestampSec) > maxSkewSec) {
    return false;
  }
  const provided = Buffer.from(headerSignatureHex.trim(), 'hex');
  if (provided.length === 0) return false;
  const signedPayload = Buffer.concat([Buffer.from(`${timestampSec}.`, 'utf8'), rawBody]);

  for (const secret of activeSecrets) {
    const expected = createHmac('sha256', secret).update(signedPayload).digest();
    if (provided.length === expected.length && timingSafeEqual(provided, expected)) {
      return true;
    }
  }
  return false;
}

export type PaymentLedgerState = 'PENDING' | 'SETTLED' | 'FAILED' | 'REFUNDED';

// Prevents out-of-order delayed webhooks from regressing settled financial state
export function isValidPaymentWebhookTransition(
  current: PaymentLedgerState,
  incomingEvent: 'PAYMENT_PENDING' | 'PAYMENT_SETTLED' | 'PAYMENT_FAILED' | 'PAYMENT_REFUNDED'
): boolean {
  if (current === 'SETTLED') {
    // Only an explicit verified refund/reversal event may transition out of SETTLED
    return incomingEvent === 'PAYMENT_REFUNDED';
  }
  if (current === 'REFUNDED') return false;
  if (current === 'FAILED') return incomingEvent === 'PAYMENT_SETTLED'; // Late settlement recovery requires audit
  return incomingEvent === 'PAYMENT_SETTLED' || incomingEvent === 'PAYMENT_FAILED' || incomingEvent === 'PAYMENT_PENDING';
}
```
Durable webhook inbox deduplication table:
```sql
CREATE TABLE webhook_inbox_events (
  id                 UUID PRIMARY KEY,
  provider           TEXT NOT NULL,
  provider_event_id  TEXT NOT NULL,
  order_ref          TEXT,
  status             TEXT NOT NULL DEFAULT 'PENDING' CHECK (status IN ('PENDING', 'APPLIED', 'IGNORED_STALE', 'DEAD_LETTER')),
  raw_payload        JSONB NOT NULL,
  received_at        TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  applied_at         TIMESTAMPTZ,
  UNIQUE (provider, provider_event_id)
);
```

## 5. Platform / Vendor Variations
| Provider | Signature Specification | Specific Nuance |
| :--- | :--- | :--- |
| **Stripe** | `Stripe-Signature: t=...,v1=...` (`HMAC-SHA256` over `${t}.${rawBody}`) | `5-min` replay skew default; use `stripe.webhooks.constructEvent(rawBody, sig, secret)` |
| **Midtrans** | `SHA-512(order_id + status_code + gross_amount + server_key)` | No signed timestamp header — MUST cross-check `gross_amount` + deduplicate + protect monotonic state! |
| **Xendit** | `x-callback-token` verification token (constant-time compare!) + optional IP allowlist | Verify `timingSafeEqual` on token & cross-verify via Inquiry API for high-value payouts |
| **SNAP BI (Indonesia)** | Asymmetric RSA-SHA256 (`X-SIGNATURE`) + `X-TIMESTAMP` (ISO-8601 WIB/UTC) + `X-EXTERNAL-ID` | Strict timestamp skew + `X-EXTERNAL-ID` daily uniqueness per BI SNAP spec |

## 6. Decision Matrix & Trade-Offs
| Processing Mode Inside Webhook HTTP Handler | Timeout Risk | Reliability | Verdict |
| :--- | :---: | :---: | :--- |
| **Verify -> Persist `webhook_inbox_events` + Enqueue -> Return `200` (< 200ms)** | Very Low | **Highest** | **Recommended default** |
| **Run heavy PDF + Email + ERP sync inline before `200`** | High (`> 5–10s` triggers provider retry storm!) | Poor | **Avoid** |

## 7. Real Production Scenario
A payment webhook times out at 8s on the first attempt (because the handler synchronously generated a PDF invoice and sent SMTP email inside the HTTP request). The payment gateway retries the exact same webhook twice; without `UNIQUE (provider, provider_event_id)`, the system ships 3 digital gift cards for 1 payment — AND an earlier delayed `PENDING` retry overwrites the order back to `PENDING`! Switching to raw-body HMAC verification -> atomic `webhook_inbox_events` insert -> fast `200` -> async worker with `isValidPaymentWebhookTransition` stops duplicate fulfillment and stale overwrites completely.

## 8. Failure Modes & Edge Cases
- **WRONG:** Comparing webhook signatures with `sig === expected` (timing side-channel) or running `express.json()` globally BEFORE capturing `rawBody` (re-stringifying alters whitespace/key order and breaks HMAC!).
- **RIGHT:** Capture raw `Buffer` on webhook routes, verify with `timingSafeEqual`, and support dual-secret rotation arrays.
- **WRONG:** Trusting `req.body.status === 'PAID'` from an unverified endpoint without checking cryptographic signature AND matching `amountMinor`/`currency` against the local order!
- **RIGHT:** Reject unsigned/invalid signatures with `401` and reject amount/currency mismatches loudly (`ALERT_AMOUNT_MISMATCH`).

## 9. Testing & Verification
- Test 5 webhook fixtures offline: (1) valid signature -> `200` & persisted, (2) 1-byte mutated body -> `401`, (3) stale timestamp `> 300s` -> `401`, (4) duplicate `provider_event_id` -> `200` with `0` duplicate side effects, (5) delayed `PAYMENT_PENDING` arriving after `SETTLED` -> ignored (`IGNORED_STALE`, order stays `SETTLED`)!

## 10. Operational Considerations
- Alert immediately on unexpected spikes in `401 invalid_signature` (expired/rotated webhook secret OR spoofing attack) and `ALERT_AMOUNT_MISMATCH`.

## 11. Authoritative References
- Standard Webhooks Specification (`https://www.standardwebhooks.com/`).
- Stripe / Midtrans / Xendit / Bank Indonesia SNAP Official Webhook Verification Guides.

## 12. Limitations & When NOT to Use
- Inbound webhooks can always be delayed or silently dropped during partner outages — ALWAYS pair webhooks with a scheduled **Reconciliation Cron** querying provider status APIs for stale `PENDING` rows (`04`).
