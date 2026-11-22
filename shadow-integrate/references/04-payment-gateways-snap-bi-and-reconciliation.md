# 04. Payment Gateways, SNAP BI & Scheduled Reconciliation

## 1. Purpose & Activation Conditions
Integrate Indonesian and global payment rails (**SNAP BI**, **Midtrans**, **Xendit**, **Stripe**) and close the loop on dropped webhooks or partial network failures via deterministic **Scheduled Reconciliation Jobs** and Transactional Outbox handoffs. Load when integrating payment/QRIS/VA/payout APIs or designing financial ledger reconciliation.

## 2. Prerequisites
- Bounded adapters (`01`), verified HMAC/asymmetric webhooks (`02`), `UNKNOWN` inquiry recovery (`03`), and ACID ledger precision (`shadow-data` Module `04`).

## 3. Technical Principles & Constraints
- **Indonesia Payment & Banking Integration Specifics (`SNAP BI` / `Midtrans` / `Xendit`):**
  - **SNAP BI (Standar Nasional Open API Pembayaran — Bank Indonesia):** Asymmetric RSA-SHA256 `X-SIGNATURE` for B2B Access Token (`POST /v1.0/access-token/b2b`), symmetric HMAC-SHA512 `X-SIGNATURE` on transactional calls (`HTTPMethod:EndpointUrl:AccessToken:Lowercase(HexEncode(SHA-256(minify(body)))):TimeStamp`), ISO-8601 `X-TIMESTAMP` (`+07:00` WIB or UTC strictly per bank spec), and strictly **unique daily `X-EXTERNAL-ID`** (reusing `X-EXTERNAL-ID` on the same calendar day causes immediate `409 Conflict`!).
  - **QRIS / Virtual Account (VA) Lifecycle:** Expect asynchronous settlement minutes to hours after invoice creation, partial/over-payment edge cases on open VA (prefer closed fixed-amount VA whenever possible!), and exact expiry timestamp synchronization (`expired_at`).
  - **Zero Trust in Browser Return URLs (`finish_redirect_url`):** NEVER mark an order `PAID` purely because the browser landed on `/checkout/success?order_id=...`! Settle ONLY from a cryptographically verified **server-to-server webhook** (`02`) OR an **authenticated server status inquiry** (`03`)!
- **Scheduled Reconciliation Cron (The Mandatory Safety Net):** Webhooks get dropped by firewalls, DNS blips, and partner outages. Run a scheduled reconciliation worker every `5–15 minutes` (plus daily `T+1` settlement-file matching against bank/gateway reports!):
  1. Select local transactions stuck in `PENDING` or `UNKNOWN_PENDING_RECONCILE` beyond SLA (e.g., `> 5 min` old, `< 48h` old),
  2. Call the provider's authenticated Status Inquiry API (bounded rate & circuit breaker),
  3. Reconcile exact `(order_id, amount_minor, currency, terminal_status)` inside an atomic DB transaction with optimistic lock / monotonic transition guard,
  4. Emit alerts on any **Ledger Discrepancy** (provider `SETTLED` but local `CANCELLED`/`EXPIRED` -> escalate immediately to Finance Ops for refund or manual fulfillment!).

## 4. Architecture & Implementation
```typescript
export interface LocalTxSnapshot {
  readonly orderId: string;
  readonly status: 'PENDING' | 'UNKNOWN_PENDING_RECONCILE' | 'SETTLED' | 'EXPIRED' | 'CANCELLED';
  readonly amountMinor: number;
  readonly currency: string;
}

export interface ProviderInquirySnapshot {
  readonly orderId: string;
  readonly providerRef: string;
  readonly terminalStatus: 'PENDING' | 'SETTLED' | 'FAILED' | 'EXPIRED';
  readonly amountMinor: number;
  readonly currency: string;
}

export type ReconAction =
  | { readonly action: 'SETTLE_LOCAL'; readonly providerRef: string }
  | { readonly action: 'MARK_EXPIRED_OR_FAILED' }
  | { readonly action: 'KEEP_PENDING' }
  | { readonly action: 'ESCALATE_FINANCE_DISCREPANCY'; readonly reason: string };

export function evaluatePaymentReconciliation(
  local: LocalTxSnapshot,
  remote: ProviderInquirySnapshot
): ReconAction {
  if (local.orderId !== remote.orderId || local.currency !== remote.currency || local.amountMinor !== remote.amountMinor) {
    return { action: 'ESCALATE_FINANCE_DISCREPANCY', reason: 'IDENTITY_OR_AMOUNT_MISMATCH' };
  }
  if (remote.terminalStatus === 'PENDING') return { action: 'KEEP_PENDING' };
  if (remote.terminalStatus === 'SETTLED') {
    if (local.status === 'EXPIRED' || local.status === 'CANCELLED') {
      // Late settlement after local timeout -> NEVER silently ignore real customer money!
      return { action: 'ESCALATE_FINANCE_DISCREPANCY', reason: 'LATE_SETTLEMENT_ON_EXPIRED_ORDER' };
    }
    return { action: 'SETTLE_LOCAL', providerRef: remote.providerRef };
  }
  if (local.status === 'SETTLED') {
    return { action: 'ESCALATE_FINANCE_DISCREPANCY', reason: 'REMOTE_FAILED_BUT_LOCAL_SETTLED' };
  }
  return { action: 'MARK_EXPIRED_OR_FAILED' };
}
```
Daily `T+1` reconciliation summary query:
```sql
SELECT
  provider,
  currency,
  COUNT(*) FILTER (WHERE status = 'SETTLED') AS settled_count,
  COALESCE(SUM(amount_minor) FILTER (WHERE status = 'SETTLED'), 0) AS settled_total_minor,
  COUNT(*) FILTER (WHERE status = 'UNKNOWN_PENDING_RECONCILE') AS unresolved_unknown_count
FROM payment_transactions
WHERE created_at >= CURRENT_DATE - INTERVAL '1 day'
  AND created_at < CURRENT_DATE
GROUP BY 1, 2;
```

## 5. Platform / Vendor Variations
| Gateway | Auth & Key Hygiene | Reconciliation Mechanism |
| :--- | :--- | :--- |
| **SNAP BI (BCA/Mandiri/BRI/BNI)** | OAuth2 B2B token (`15m` TTL cached!) + RSA-SHA256 + HMAC-SHA512 + unique daily `X-EXTERNAL-ID` | Mandatory Inquiry API (`POST /v1.0/transfer-va/status` / QRIS query) + `T+1` bank statement |
| **Midtrans** | Basic Auth (`ServerKey:`) + SHA-512 webhook check | `GET /v2/{order_id}/status` inquiry + closed VA amounts |
| **Xendit** | Basic Auth (`SecretKey:`) + `x-callback-token` | `GET /v2/invoices/{id}` inquiry + webhook replay |
| **Stripe** | Bearer restricted key + `Idempotency-Key` + `Stripe-Signature` | `GET /v1/payment_intents/{id}` + Stripe Balance Transactions `T+1` report |

## 6. Decision Matrix & Trade-Offs
| Settlement Trigger | Trustworthy for Fulfillment? | Why |
| :--- | :---: | :--- |
| **Browser `/checkout/success` Redirect** | **NO (UX Only!)** | Trivially spoofable by user editing URL, and fails if mobile tab closes |
| **Verified Server Webhook (`02`)** | **YES (Primary fast path)** | Cryptographically signed server-to-server notification |
| **Authenticated Status Inquiry Cron (`03`/`04`)** | **YES (Mandatory fallback)** | Recovers 100% of dropped/delayed webhooks automatically |

## 7. Real Production Scenario
A customer pays a QRIS invoice 2 seconds before the 15-minute checkout timer expires. The local expiry cron marks the order `EXPIRED`, while the bank settles the QRIS payment and delivers a delayed webhook 40 seconds later. Without `evaluatePaymentReconciliation`, the webhook is silently ignored, leaving the customer debited with an `EXPIRED` order! Detecting `LATE_SETTLEMENT_ON_EXPIRED_ORDER` and immediately flagging a structured Finance Ops discrepancy ticket (triggering automated refund or verified late fulfillment per business policy) protects both customer trust and accounting integrity.

## 8. Failure Modes & Edge Cases
- **WRONG:** Reusing the same SNAP BI `X-EXTERNAL-ID` across two different API calls on the same day, or caching B2B tokens past their 15-minute expiry without preemptive refresh (`expiry - 60s`).
- **RIGHT:** Generate a unique per-request `X-EXTERNAL-ID` (numeric/UUID per bank length limit), cache B2B access tokens with a 60s safety margin, and refresh cleanly on `401` once.
- **WRONG:** Relying 100% on webhooks with zero scheduled reconciliation job (any 5-minute webhook outage creates permanent silent accounting drift!).
- **RIGHT:** Pair webhooks with a 5–15 minute inquiry cron for stuck `PENDING`/`UNKNOWN` rows AND daily `T+1` settlement sum checks.

## 9. Testing & Verification
- Test `evaluatePaymentReconciliation` with all 5 edge fixtures: exact match settle, amount mismatch escalate, late settlement on expired order escalate, remote failed vs local settled escalate, and still-pending no-op.
- Run `python -m unittest discover -s shadow-integrate/tests -v` (`test_idempotency_recovery.py`).

## 10. Operational Considerations
- Keep sandbox test mode strictly isolated (`L1` mocked/sandbox fixtures only); NEVER fire synthetic test payment charges or refunds against live production gateway keys (`L4` financial impact!).

## 11. Authoritative References
- Bank Indonesia — *Standar Nasional Open API Pembayaran (SNAP BI)* Technical Specification (`https://apidevportal.aspi-indonesia.or.id/`).
- Midtrans / Xendit / Stripe Official Integration & Reconciliation Docs.

## 12. Limitations & When NOT to Use
- Automated reconciliation detects and heals technical delivery gaps (`PENDING -> SETTLED`), NOT contested chargebacks, fraud disputes, or manual bank-statement fee adjustments — route `ESCALATE_FINANCE_DISCREPANCY` items straight to Finance Ops with complete correlation IDs.
