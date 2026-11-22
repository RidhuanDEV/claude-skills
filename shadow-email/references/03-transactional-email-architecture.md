# 03 — Transactional Email Architecture (`CORE`)

## 1. Purpose & Activation Conditions
Load when designing application email abstractions (`EmailProviderPort`), separating transactional vs marketing streams, structuring template registries, or defining logical idempotency keys.

## 2. Prerequisites
Modules `01`–`02` and `/shadow-domain` / `/shadow-concurrency` outbox foundations.

## 3. Technical Principles & Constraints
- **Stream & Subdomain Isolation:** Never mix critical transactional emails (`OTP`, `password reset`, `payment receipt` on `tx.example.com`) with promotional/digest mail (`news.example.com`). One marketing spam spike must never degrade login OTP delivery.
- **Provider Abstraction Boundary:** Application business logic MUST call a narrow domain interface (`EmailProviderPort`), NEVER scatter vendor SDK calls (`resend.emails.send(...)`) inside controllers — enabling clean Mailpit local dev, deterministic unit tests, and zero-rewrite ESP failover.
- **Logical Idempotency Keys:** Generate idempotency keys per logical notification event (e.g., `invoice-paid:inv_901`, `otp-login:req_7f3a`), NOT solely per recipient email (so a user can legitimately request a second OTP after expiry while duplicate webhook retries still deduplicate!).

## 4. Architecture & Implementation
```ts
export type EmailStream = "TRANSACTIONAL_SECURITY" | "TRANSACTIONAL_RECEIPT" | "SUBSCRIBED_DIGEST" | "MARKETING_BULK";

export interface OutboundEmailMessage {
  readonly idempotencyKey: string;
  readonly stream: EmailStream;
  readonly from: string;
  readonly to: string;
  readonly replyTo?: string;
  readonly subject: string;
  readonly html: string;
  readonly text: string;
  readonly headers?: Readonly<Record<string, string>>;
}

export interface EmailSendReceipt {
  readonly provider: string;
  readonly providerMessageId: string;
  readonly acceptedAtIso: string;
}

export interface EmailProviderPort {
  send(message: OutboundEmailMessage, signal?: AbortSignal): Promise<EmailSendReceipt>;
}
```

## 5. Platform / Vendor Variations
- **Local Dev / CI:** Bind `EmailProviderPort` to a `MailpitSmtpAdapter` (`127.0.0.1:1025`) or in-memory test spy.
- **Staging:** Wrap `EmailProviderPort` with an `AllowlistGuardAdapter` that refuses or redirects any recipient outside `ALLOWED_STAGING_EMAIL_DOMAINS`.
- **Production:** Bind `EmailProviderPort` to `SesAdapter` / `ResendAdapter` / `PostmarkAdapter` configured with stream-specific `From:` addresses (`no-reply@tx.example.com` vs `updates@news.example.com`).

## 6. Decision Matrix & Trade-Offs
| Notification Category | Stream & Subdomain | Queue Priority | Unsubscribe Required? |
| :--- | :--- | :---: | :---: |
| OTP, MFA, Password Reset, Login Alert | `TRANSACTIONAL_SECURITY` (`tx.`) | Critical (`< 5s` SLA) | **NO** (never allow opt-out of security mail) |
| Invoice, Receipt, Shipping Update | `TRANSACTIONAL_RECEIPT` (`tx.`) | High (`< 30s` SLA) | No (contractual/operational record) |
| Weekly Activity Digest / Comment Alert | `SUBSCRIBED_DIGEST` (`news.`) | Normal (coalesced) | **YES** (preference center + RFC 8058) |
| Promotions / Product Launches | `MARKETING_BULK` (`news.`) | Low (throttled) | **YES** (mandatory DKIM-signed RFC 8058) |

## 7. Real Production Scenario
A startup sent password resets and weekly newsletters from the exact same `hello@company.com` address and synchronous Express controller. When a promo email triggered `0.5%` spam complaints, Gmail throttled `hello@company.com` — locking users out of password resets. Splitting into `tx.company.com` + `news.company.com` behind `EmailProviderPort` + Outbox isolated auth reliability completely.

## 8. Failure Modes & Edge Cases (`WRONG` vs `RIGHT`)
- **WRONG:** Sending email inside an HTTP `POST /checkout` handler with `await resend.emails.send(...)` before returning `200 OK` (ESP latency spikes break checkout!).
  **RIGHT:** Insert an `email_outbox` row inside the checkout DB transaction and dispatch asynchronously via worker.
- **WRONG:** Using `userId` alone as idempotency key for OTPs (blocks all future logins!) or omitting idempotency keys completely (sends 4 duplicate invoices on retry).
  **RIGHT:** Scope idempotency keys to the unique logical trigger (`otp:${requestId}`, `invoice-paid:${invoiceId}`).

## 9. Testing & Verification
Unit-test template rendering + stream policy (`email_deliverability_verifier.py --check-rfc8058` & `--check-artifact`), and verify staging `AllowlistGuardAdapter` blocks non-allowlisted addresses.

## 10. Operational Considerations
Version template IDs (`invoice-paid.v2`) so in-flight outbox rows rendered during rolling deployments deserialize cleanly against their exact payload schema.

## 11. Authoritative References
- Google Bulk Sender Guidelines (stream separation); `shadow-email/scripts/email_deliverability_verifier.py`.

## 12. Limitations & When NOT to Use
For simple internal ops alerts (disk full, CI build failed), prefer Slack/PagerDuty/monitoring alerts (`/shadow-observe`) rather than building a full multi-stream email architecture.
