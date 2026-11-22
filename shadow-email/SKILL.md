---
name: shadow-email
description: "Email Infrastructure & Deliverability Engineering Specialist. Use when designing SMTP/MIME pipelines, SPF/DKIM/DMARC/MTA-STS authentication, React Email/MJML Outlook & dark-mode templates, transactional outbox queues, DSN bounce handling, RFC 8058 bulk unsubscribe, abuse/header-injection defense, multi-ESP failover (SES/Resend/Postmark/SendGrid), Postmaster incident response, or Mailpit testing. Do NOT use for generic REST/payment webhooks (/shadow-integrate)."
---

# Shadow Email (`/shadow-email`) — Email Infrastructure & Deliverability Engineering

Use this skill whenever the **Monarch** designs, builds, hardens, tests, or troubleshoots transactional email pipelines (OTP, password reset, invoices, receipts), subscribed/marketing campaigns, DNS authentication, deliverability incidents, or ESP migrations.

## 1. Core Engineering Principles & Non-Negotiables

1. **Stream & Reputation Isolation:** Separate critical transactional mail (`auth.example.com` / `tx.example.com`) from marketing/digest streams (`news.example.com`) with distinct subdomains, DKIM keys, and IP pools so marketing complaints never block OTPs.
2. **End-to-End Authentication & Alignment:** Enforce **SPF (`<= 10` DNS lookups)**, **2048-bit DKIM**, **DMARC** (`p=none -> quarantine -> reject` + `rua`), valid **PTR/rDNS**, and **TLS / MTA-STS** with `From:` alignment.
3. **Contextual RFC 8058 Unsubscribe:** Include DKIM-signed `List-Unsubscribe` + `List-Unsubscribe-Post: List-Unsubscribe=One-Click` (honored `<= 2 days`) for **bulk marketing and subscribed messages** — do **NOT** attach marketing one-click unsubscribe headers to essential security transactional mail (`OTP`, `password reset`, `fraud alerts`).
4. **Durable Outbox, Safe Failover & Erasure-Safe Suppression:** Persist email intents in a transactional outbox with idempotency keys, suppress hard bounces (`5.x.x`) and FBL complaints using keyed `HMAC-SHA256` tombstones compatible with UU PDP/GDPR erasure, and never blindly fail over after an ambiguous post-submit timeout.
5. **Security & Zero Staging Leakage:** Strip `\r\n\0` from headers, build action links strictly from static `APP_CANONICAL_ORIGIN`, verify webhook HMAC/RSA signatures over raw bytes, and enforce a hard recipient allowlist/Mailpit sink in non-production environments.

## 2. Deterministic Verification CLI & Scenario Benchmarks

Run offline checks (`L0`/`L1`) before claiming `VERIFIED-LOCAL`:
```powershell
python "shadow-email/scripts/email_deliverability_verifier.py" --self-test
python "shadow-email/scripts/email_deliverability_verifier.py" --check-dns path/to/dns.json
python "shadow-email/scripts/email_deliverability_verifier.py" --check-headers path/to/headers.json
python "shadow-email/scripts/email_deliverability_verifier.py" --check-template path/to/template.html
python -m unittest discover -s "shadow-email/tests" -v
```
Graded specialist scenarios live in [evaluations.md](evaluations.md) (9 scenarios covering DNS alignment, RFC 8058 transactional vs bulk distinction, Outlook VML/dark mode, DSN `4.x.x`/`5.x.x`, CRLF injection, failover safety, and `250 OK` missing-in-inbox RCA).

## Reference Guide

Load **only** the 1–2 modules matching the active subtask (never load all 11 at once):

| Task / Scenario | Tier | Load Reference |
| :--- | :--- | :--- |
| SMTP/ESMTP handshake, MIME multipart/alternative, RFC 5321/5322 headers, DSN codes (`2.x`/`4.x`/`5.x`) | CORE | [references/01-email-protocol-fundamentals.md](references/01-email-protocol-fundamentals.md) |
| SPF (`<= 10` lookups), 2048-bit DKIM, DMARC alignment & rollout, PTR/rDNS, MTA-STS, TLS-RPT, BIMI | CORE | [references/02-authentication-and-domain-security.md](references/02-authentication-and-domain-security.md) |
| `EmailProviderPort`, React Email/MJML architecture, idempotency keys, stream isolation, template versioning | CORE | [references/03-transactional-email-architecture.md](references/03-transactional-email-architecture.md) |
| Outlook Classic Word/VML buttons, Gmail `102 KB` clipping, dark-mode CSS contrast, email accessibility | CORE | [references/04-rendering-and-client-compatibility.md](references/04-rendering-and-client-compatibility.md) |
| Transactional outbox, BullMQ/SQS priority queues, exponential backoff, DLQ replay, per-domain rate limits | CORE | [references/05-queue-and-reliability-engineering.md](references/05-queue-and-reliability-engineering.md) |
| IP/domain reputation, warm-up schedules, hard/soft bounce & complaint thresholds (`< 0.1%`), throttling | ADVANCED | [references/06-deliverability-engineering.md](references/06-deliverability-engineering.md) |
| Consent ledger, RFC 8058 marketing vs OTP exception, `GET`/`POST` unsubscribe safety, HMAC suppression | CORE | [references/07-consent-and-subscription-management.md](references/07-consent-and-subscription-management.md) |
| CRLF header injection, OTP bombing rate limits, Host header poisoning, signed webhook replay protection | ADVANCED | [references/08-email-security-and-abuse-prevention.md](references/08-email-security-and-abuse-prevention.md) |
| Amazon SES vs Resend vs Postmark vs SendGrid, safe multi-ESP circuit-breaker failover, suppression sync | SPECIALIST | [references/09-esp-integration-and-failover.md](references/09-esp-integration-and-failover.md) |
| Delivery funnel SLIs, Google Postmaster/SNDS/DMARC `rua` alerts, `250 OK` inbox-missing incident runbooks | OPERATIONAL | [references/10-observability-and-incident-response.md](references/10-observability-and-incident-response.md) |
| Mailpit local E2E, staging recipient allowlist sink, CI gates, SES simulator & production launch checklist | OPERATIONAL | [references/11-testing-and-production-readiness.md](references/11-testing-and-production-readiness.md) |

Do not load unrelated references unnecessarily.
