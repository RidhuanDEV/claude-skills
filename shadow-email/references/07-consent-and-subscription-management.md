# 07. Consent & Subscription Management

## 1. Purpose & Activation Conditions
Design legally compliant, deliverability-safe email consent, preference centers, one-click unsubscribe workflows, and suppression tombstones. Load when implementing marketing/newsletter opt-in, RFC 8058 one-click unsubscribe headers, unsubscribe landing pages, or UU PDP / GDPR erasure interactions with email suppression.

## 2. Prerequisites
- Clear separation of email streams (`security_transactional`, `operational_transactional`, `product_notification`, `marketing_subscribed`).
- Authenticated sending domain with DKIM covering `List-Unsubscribe` and `List-Unsubscribe-Post` headers (`02-authentication-and-domain-security.md`).

## 3. Technical Principles & Constraints
- **Mandatory Distinction — Bulk Marketing vs Security Transactional:** Under Gmail and Yahoo bulk-sender requirements and RFC 8058, **one-click unsubscribe (`List-Unsubscribe` + `List-Unsubscribe-Post: List-Unsubscribe=One-Click`) is required for marketing, newsletter, and subscribed messages**, NOT for essential security/legal transactional emails (`OTP`, `password reset`, `fraud alert`, `payment receipt`). Adding an unsubscribe link to an OTP email risks accidental user opt-out from account recovery.
- **Honor SLA (`<= 48 hours`):** Gmail requires bulk senders to honor one-click unsubscribe requests within 2 days; best practice is synchronous suppression (`< 1 second`) before returning `200 OK`.
- **Two-Mode Unsubscribe Safety:** Mail scanners pre-fetch `GET` URLs automatically. Therefore:
  - `POST` to the signed `List-Unsubscribe` endpoint (with `List-Unsubscribe=One-Click` body) MUST unsubscribe immediately without login.
  - `GET` to the browser unsubscribe link MUST render a confirmation button (which triggers `POST`), NEVER mutate subscription state on `GET`.
- **Erasure-Compatible Suppression Tombstones:** When a user exercises UU PDP (UU No. 27/2022) or GDPR Right to Erasure, deleting the user record without retaining a keyed hash (`HMAC-SHA256(normalized_email, pepper)`) risks re-emailing an unsubscribed/bounced address on future imports. Store only the keyed digest + reason + timestamp in `email_suppressions`.

## 4. Architecture & Implementation
```typescript
import { createHmac, timingSafeEqual } from 'node:crypto';

export type EmailCategory =
  | 'security_transactional'
  | 'operational_transactional'
  | 'product_notification'
  | 'marketing_subscribed';

export interface UnsubscribeHeaders {
  readonly 'List-Unsubscribe'?: string;
  readonly 'List-Unsubscribe-Post'?: string;
}

export function buildUnsubscribeHeaders(
  category: EmailCategory,
  signedUnsubscribeUrl: string,
  mailtoFallback: string
): UnsubscribeHeaders {
  // Security & legal transactional mail MUST NOT carry marketing one-click unsubscribe headers
  if (category === 'security_transactional' || category === 'operational_transactional') {
    return {};
  }
  return {
    'List-Unsubscribe': `<${signedUnsubscribeUrl}>, <mailto:${mailtoFallback}?subject=unsubscribe>`,
    'List-Unsubscribe-Post': 'List-Unsubscribe=One-Click',
  };
}

export function hashRecipientForSuppression(rawEmail: string, serverPepper: string): string {
  const normalized = rawEmail.trim().toLowerCase();
  return createHmac('sha256', serverPepper).update(normalized).digest('hex');
}

export function verifyUnsubscribeSignature(
  payload: string,
  providedHex: string,
  secret: string
): boolean {
  const expected = createHmac('sha256', secret).update(payload).digest('hex');
  const a = Buffer.from(expected, 'hex');
  const b = Buffer.from(providedHex, 'hex');
  return a.length === b.length && timingSafeEqual(a, b);
}
```

## 5. Platform / Vendor Variations
| Provider / Jurisdiction | Specific Requirement | Implementation Impact |
| --- | --- | --- |
| **Gmail / Yahoo Bulk Senders** | RFC 8058 `List-Unsubscribe-Post` on marketing/subscribed mail; DKIM must sign both headers; honor `<= 2 days` | Include headers in DKIM `h=` tag; expose unauthenticated HMAC-signed `POST` endpoint |
| **Apple Mail (iOS / macOS)** | Displays native banner from `List-Unsubscribe`; supports `mailto:` and HTTPS `POST` | Provide both HTTPS URL and `mailto:` fallback |
| **UU PDP (Indonesia) & GDPR (EU)** | Explicit, granular, withdrawable opt-in consent with proof (`consent_timestamp`, `source`, `policy_version`); erasure compatibility | Log immutable consent ledger; use keyed HMAC suppression tombstone after PII erasure |
| **CAN-SPAM (US)** | Physical postal address + clear opt-out honored within 10 business days | Include legal footer on commercial mail; unify around stricter 48-hour SLA |

## 6. Decision Matrix & Trade-Offs
| Mechanism | User Friction | Bot / Scanner Safety | Compliance Coverage | Best Used For |
| --- | --- | --- | --- | --- |
| **RFC 8058 HTTPS `POST`** | Zero (1 click in inbox UI) | High (scanners rarely send signed `POST`) | Mandatory for bulk marketing | Gmail, Yahoo, Apple Mail native banner |
| **`GET` Page + `POST` Button** | Low (1 confirmation click) | High (immune to link pre-fetchers) | Universal fallback | In-body "Manage preferences / Unsubscribe" link |
| **Granular Preference Center** | Low–Medium | High | Reduces full opt-outs | Multi-topic newsletters & product digests |
| **Login-Gated Unsubscribe** | Very High (causes spam clicks) | High | Violates best practice / CAN-SPAM friction | **NEVER use** for unsubscribe |

## 7. Real Production Scenario
A SaaS platform puts an unsubscribe link in the footer that executes `UPDATE users SET marketing_opt_in = false` on `GET /unsubscribe?token=...`. Enterprise customers behind Microsoft Defender Safe Links report being mysteriously unsubscribed minutes after receiving weekly digests because the security gateway pre-fetches every `GET` URL. Fixing the route to render a confirmation page on `GET` and mutate only on `POST` (while keeping `POST` immediate for RFC 8058 `List-Unsubscribe-Post`) eliminates false opt-outs completely.

## 8. Failure Modes & Edge Cases
- **WRONG:** Adding `List-Unsubscribe-Post` to password-reset or OTP emails because a linter demanded it on "all emails".
- **RIGHT:** Enforce category-aware headers: omit one-click unsubscribe on `security_transactional` and `operational_transactional`, require it on `marketing_subscribed` and `product_notification`.
- **WRONG:** Checking only `users.marketing_opt_in = true` while ignoring the global `email_suppressions` table (or re-enabling a hard-bounced user when they re-subscribe).
- **RIGHT:** Always intersect `consent_granted AND NOT suppressed(hmac(email))` at enqueue AND worker dispatch time.

## 9. Testing & Verification
- Run `python shadow-email/scripts/email_deliverability_verifier.py --check-headers <headers.json>` for both a marketing fixture (must pass with RFC 8058 headers) and an OTP fixture (must fail if one-click unsubscribe is accidentally attached).
- Verify `GET /unsubscribe/:token` returns `200` with zero DB writes, while `POST /unsubscribe/:token` with `List-Unsubscribe=One-Click` writes suppression synchronously and is idempotent on repeat calls.

## 10. Operational Considerations
- Track unsubscribe rate per campaign (`> 0.5%` signals audience mismatch or over-frequency).
- Rotate signing secrets with dual-key verification (`current` + `previous`) so 30-day-old emails in user inboxes remain unsubscribable without signature failure.

## 11. Authoritative References
- IETF RFC 8058 — *Signaling One-Click Functionality for List Email Headers* (`https://datatracker.ietf.org/doc/html/rfc8058`).
- Google Email Sender Guidelines — *Unsubscribe Requirements* (`https://support.google.com/a/answer/81126`).
- UU No. 27 Tahun 2022 tentang Pelindungan Data Pribadi (UU PDP) — Consent & Erasure provisions.

## 12. Limitations & When NOT to Use
- Preference centers do not override hard-bounce or spam-complaint suppressions; a user who previously complained should require explicit double opt-in re-verification before removal from suppression.
- Do not manage SMS/WhatsApp consent in an email-only boolean column; model channel-scoped consent records.
