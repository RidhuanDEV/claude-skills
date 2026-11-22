# 08. Email Security & Abuse Prevention

## 1. Purpose & Activation Conditions
Harden email pipelines against SMTP/header injection, OTP/email bombing, webhook spoofing, credential leakage, and phishing/brand impersonation. Load when building public-facing forms that trigger emails, implementing ESP webhook endpoints, auditing auth email flows, or responding to abuse incidents.

## 2. Prerequisites
- Authenticated DNS stack (`02-authentication-and-domain-security.md`) and transactional sending architecture (`03-transactional-email-architecture.md`).
- Rate-limiter store (Redis token bucket or sliding window) accessible from API entry points.

## 3. Technical Principles & Constraints
- **Zero CRLF Header Injection:** Never interpolate untrusted user input (`name`, `subject`, `replyTo`, `tenantName`) into raw MIME headers without stripping `\r` (`0x0D`), `\n` (`0x0A`), and NUL (`0x00`) bytes and enforcing strict length/charset bounds.
- **Email Bombing & Amplification Defense:** Public endpoints (`POST /auth/forgot-password`, `POST /auth/otp`, `POST /invite`, `POST /contact`) are prime targets for email bombing and SMS/email wallet draining. Enforce layered rate limits: per normalized recipient email, per IP/subnet, per account/tenant, plus proof-of-work/Turnstile on anomalous bursts, and return uniform responses (`202 Accepted`) to prevent account enumeration.
- **Webhook Authenticity & Replay Protection:** ESP webhooks (`bounce`, `complaint`, `delivered`) mutate suppression tables and billing states. Always verify provider cryptographic signatures (`HMAC-SHA256`, `Svix`, or AWS SNS X.509 certificate verification) over the **raw request body**, enforce a tight timestamp window (`<= 5 minutes`), and deduplicate by `webhook_event_id`.
- **Zero Secrets or PII in Subjects & Logs:** Email subject lines are transmitted in cleartext metadata logs, push notifications, and lock-screen previews. NEVER place OTP codes, reset tokens, NIK, or full account numbers in `Subject:` or structured application logs (mask recipients as `r***@domain.com` in operational logs).
- **Safe Links & Redirects:** Never construct dynamic email CTA URLs from unvalidated `Host` or `Origin` request headers (Host Header Poisoning sends victims a password-reset link pointing to an attacker domain). Always bind base URLs from a static server-side allowlisted config (`APP_CANONICAL_ORIGIN`).

## 4. Architecture & Implementation
```typescript
import { createHmac, timingSafeEqual } from 'node:crypto';

const CRLF_OR_CONTROL = /[\r\n\0\u0000-\u001f\u007f]/g;

export function sanitizeHeaderValue(input: string, maxLen = 160): string {
  return input.replace(CRLF_OR_CONTROL, ' ').replace(/\s+/g, ' ').trim().slice(0, maxLen);
}

export function buildSafeActionUrl(
  canonicalOrigin: string,
  path: string,
  token: string
): string {
  const base = new URL(canonicalOrigin);
  if (base.protocol !== 'https:') {
    throw new Error('Canonical origin for email links must use HTTPS');
  }
  const url = new URL(path, base);
  url.searchParams.set('token', token);
  return url.toString();
}

export interface WebhookVerifyInput {
  readonly rawBody: Buffer;
  readonly timestampSec: number;
  readonly signatureHex: string;
  readonly secret: string;
  readonly nowSec?: number;
  readonly maxSkewSec?: number;
}

export function verifyWebhookSignature(input: WebhookVerifyInput): boolean {
  const now = input.nowSec ?? Math.floor(Date.now() / 1000);
  const maxSkew = input.maxSkewSec ?? 300;
  if (Math.abs(now - input.timestampSec) > maxSkew) {
    return false;
  }
  const signedPayload = `${input.timestampSec}.${input.rawBody.toString('utf8')}`;
  const expected = createHmac('sha256', input.secret).update(signedPayload).digest('hex');
  const a = Buffer.from(expected, 'hex');
  const b = Buffer.from(input.signatureHex, 'hex');
  return a.length === b.length && timingSafeEqual(a, b);
}
```

## 5. Platform / Vendor Variations
| ESP | Webhook Verification Mechanism | Security Pitfall to Avoid |
| --- | --- | --- |
| **Amazon SES (via SNS)** | RSA-SHA1/SHA256 signature verified against `SigningCertURL` | Must verify `SigningCertURL` hostname is strictly `sns.<region>.amazonaws.com` over HTTPS before fetching cert |
| **Resend (Svix)** | `svix-id`, `svix-timestamp`, `svix-signature` HMAC-SHA256 | Re-serializing JSON body instead of verifying raw bytes breaks signature |
| **Postmark** | Dedicated Basic Auth / custom header token + IP allowlist or signed webhook secret | Never expose unauthenticated `/webhooks/email` endpoints |
| **SendGrid** | Signed Event Webhook (`X-Twilio-Email-Event-Webhook-Signature` ECDSA) | Must verify ECDSA signature AND timestamp header (`X-Twilio-Email-Event-Webhook-Timestamp`) |

## 6. Decision Matrix & Trade-Offs
| Abuse Vector | Primary Control | Secondary Control | UX Trade-Off |
| --- | --- | --- | --- |
| **Password-reset Host Poisoning** | Static `APP_CANONICAL_ORIGIN` allowlist | Reverse-proxy strict `Host` validation | Zero UX cost |
| **OTP / Reset Bombing** | Per-recipient cooldown (`60s`) + hourly cap (`5/hr`) | Per-IP / ASN rate limit + challenge on burst | Legitimate retry waits 60s (clear UI countdown) |
| **SMTP Header Injection** | Strip `[\r\n\0]` + strict email parser + API ESP | Unit test fuzzing with `\r\nBcc: evil@attacker` | Zero UX cost |
| **Webhook Forgery / Replay** | Constant-time HMAC/ECDSA + `<= 5m` timestamp skew | `webhook_event_id` unique DB constraint | Requires raw-body middleware on webhook route |

## 7. Real Production Scenario
An attacker exploits `POST /api/v1/auth/forgot-password` by injecting `Host: evil-reset.example` in the HTTP request. Because the backend builds the reset link using `req.headers.host`, the legitimate ESP sends a DKIM-signed email from the company's own domain containing a link to `https://evil-reset.example/reset?token=...`. Simultaneously, another bot floods 40,000 password-reset emails to a competitor's inbox, triggering spam complaints that damage domain reputation. Remediation: lock link generation to `APP_CANONICAL_ORIGIN`, enforce per-email (`3/15m`) + per-IP rate limits, and rotate leaked tokens.

## 8. Failure Modes & Edge Cases
- **WRONG:** Constructing password-reset links from `req.headers.origin` or `req.headers.host` and logging the full reset URL in server logs.
- **RIGHT:** Read `APP_CANONICAL_ORIGIN` from verified server config, hash tokens at rest (SHA-256), and never log token query strings.
- **WRONG:** Accepting unverified webhook JSON payloads to auto-suppress addresses — an attacker can POST forged `hard_bounce` webhooks for admin emails to lock them out of OTP recovery.
- **RIGHT:** Reject any webhook failing cryptographic signature + timestamp skew validation with `401 Unauthorized` before touching suppression state.

## 9. Testing & Verification
- Add unit tests injecting `foo@example.com\r\nBcc: victim@example.com` into display names, subjects, and reply-to fields; assert sanitized output contains zero `\r` or `\n`.
- Run negative security tests on webhook handlers: mutated body byte -> `401`, stale timestamp (`> 5m`) -> `401`, duplicate `event_id` -> `200` no-op.
- Verify OTP rate limiter returns `429` (or uniform silent throttle) on rapid burst to the same normalized email (`user+1@gmail.com` canonicalization aware where appropriate).

## 10. Operational Considerations
- Alert on anomalous spikes in `forgot_password` or `otp_request` volume (`> 5x` rolling 15-minute baseline) — early indicator of credential stuffing or email-bombing distraction attacks.
- Store ESP API keys in a secrets manager with least-privilege scopes (e.g., AWS IAM `ses:SendEmail` restricted to verified domain ARN and specific configuration set).

## 11. Authoritative References
- OWASP Cheat Sheet Series — *Forgot Password* & *Input Validation* (`https://cheatsheetseries.owasp.org/`).
- AWS SNS Documentation — *Verifying the Signatures of Amazon SNS Messages* (`https://docs.aws.amazon.com/sns/latest/dg/sns-verify-signature-of-message.html`).
- IETF RFC 5322 — *Internet Message Format* header syntax constraints.

## 12. Limitations & When NOT to Use
- Email security controls do not substitute for MFA or phishing-resistant Passkeys (`shadow-auth`); treat email magic links/OTPs as time-bound (`<= 10 min`), single-use, and never as long-lived credentials.
- Email-level anti-phishing (DMARC/BIMI) protects your exact domain, not lookalike domains (`examp1e.com`); register defensive domains and monitor Certificate Transparency logs for high-value brands.
