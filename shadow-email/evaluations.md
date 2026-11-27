# Shadow Email — Scenario-Based Evaluation Suite

Use these 9 graded real-world scenarios to evaluate whether an agent executing `/shadow-email` reasons as a Principal Email Infrastructure & Deliverability Engineer.

---

### EMAIL-EVAL-01 (Hard) — `250 OK` Accepted by SMTP Yet Missing in Recipient Inbox
- **Prompt:** "Our app logs show SMTP `250 OK` from SES, yet 40% of corporate customers report never receiving invoices. How do you diagnose and resolve this?"
- **Required Reasoning Checkpoints (4/4):**
  - [ ] Explains that SMTP `250 OK` from the relay/ESP only confirms queue acceptance — NOT inbox placement.
  - [ ] Inspects full `Authentication-Results` headers (`SPF`, `DKIM`, `DMARC` alignment), ESP delivery/bounce/deferral webhook logs, Google Postmaster v2 Compliance Status / user-reported spam rate, and Microsoft SNDS reputation.
  - [ ] Checks for `5.7.x` policy rejections, missing custom-domain alignment, or spam-folder filtering on shared/new IPs.
  - [ ] Verifies DNS alignment via `email_deliverability_verifier.py --check-dns` before recommending code changes.

### EMAIL-EVAL-02 (Medium) — SPF/DKIM/DMARC Misalignment & SPF 10-Lookup Overflow
- **Prompt:** "Our DMARC `rua` reports show 60% failure after adding HubSpot, Zendesk, and SES to SPF, and our `From:` is `billing@company.com` while DKIM signs `amazonses.com`."
- **Required Reasoning Checkpoints (4/4):**
  - [ ] Identifies BOTH root causes: (1) SPF exceeds RFC 7208's 10-DNS-lookup limit (`PermError`), and (2) unaligned ESP DKIM (`amazonses.com` != `company.com`).
  - [ ] Splits streams onto dedicated subdomains (`tx.company.com`, `news.company.com`, `support.company.com`) so each subdomain stays well below 10 SPF lookups and isolates reputation.
  - [ ] Enables custom-domain 2048-bit DKIM signing & custom `MAIL FROM` return-path alignment.
  - [ ] Stages DMARC safely (`p=none` + `rua` audit -> `p=quarantine` -> `p=reject`).

### EMAIL-EVAL-03 (Medium) — Duplicate OTP & Invoice Emails on Queue Retries
- **Prompt:** "Users received 4 identical invoice emails whenever our payment webhook timed out and retried."
- **Required Reasoning Checkpoints (3/3):**
  - [ ] Decouples email sending from synchronous HTTP controller into an atomic `email_outbox` table inside the DB commit transaction.
  - [ ] Enforces a `UNIQUE` logical `idempotency_key` (e.g., `invoice-issued:<invoiceId>`) so webhook retries cannot enqueue duplicates.
  - [ ] Guards worker delivery against duplicate sends after ambiguous provider timeouts (check provider message state or idempotency header where supported).

### EMAIL-EVAL-04 (Hard) — Primary ESP Outage & Safe Multi-Provider Failover
- **Prompt:** "Our primary ESP is returning 503s for 20 minutes and login OTPs are failing. Design failover to Postmark without double-sending."
- **Required Reasoning Checkpoints (4/4):**
  - [ ] Abstracts ESPs behind one `EmailProviderPort` adapter + per-provider Circuit Breaker (`/shadow-integrate`).
  - [ ] Fails over automatically ONLY on deterministic pre-accept errors (`503`, `ECONNREFUSED`, `OPEN` breaker) — NEVER blindly resends on ambiguous post-POST read timeouts without reconciliation.
  - [ ] Pre-verifies DNS SPF/DKIM/DMARC alignment for BOTH primary and secondary ESPs on the `tx.` subdomain before an incident happens.
  - [ ] Keeps transactional OTPs on a separate high-priority queue lane from bulk newsletters.

### EMAIL-EVAL-05 (Medium) — Backlog Growth During Promo Surge Blocking OTPs
- **Prompt:** "Marketing queued 80,000 promo emails at 09:00 and now login OTPs take 18 minutes to arrive."
- **Required Reasoning Checkpoints (3/3):**
  - [ ] Isolates `TRANSACTIONAL` (priority lane + dedicated worker concurrency + `tx.` subdomain) from `MARKETING` (rate-limited bulk lane + `news.` subdomain).
  - [ ] Applies per-destination MX rate throttling (`gmail.com`, `yahoo.com`, `outlook.com`) and backpressure rather than blasting all 80k simultaneously.
  - [ ] Monitors queue depth & p95 time-to-first-attempt SLA (`< 5s` for OTPs).

### EMAIL-EVAL-06 (Hard) — Spam Complaint Spike (`0.6%`) & Reputation Recovery
- **Prompt:** "Google Postmaster shows spam complaint rate jumped to 0.6% after importing an old CRM list, and Gmail is throttling our mail with `4.7.28`."
- **Required Reasoning Checkpoints (4/4):**
  - [ ] Immediately pauses the offending bulk campaign/list on the `news.` subdomain (verifying `tx.` subdomain reputation remains isolated).
  - [ ] Enforces permanent suppression on complaints & `5.1.1` hard bounces using privacy-safe HMAC tombstones (`email_suppressions`), and stops retrying unengaged/unverified imported addresses.
  - [ ] Audits RFC 8058 one-click unsubscribe DKIM signing & confirms `< 0.1%` complaint target (`< 0.3%` hard ceiling).
  - [ ] Executes a gradual re-warm ramp targeting only recently engaged opted-in recipients first.

### EMAIL-EVAL-07 (Medium) — Broken Outlook Layout, Invisible Dark-Mode Logo & Gmail Clipping
- **Prompt:** "Customers complain our Tailwind email looks broken in Outlook desktop, our black logo disappears in iOS Dark Mode, and Gmail hides the unsubscribe footer."
- **Required Reasoning Checkpoints (4/4):**
  - [ ] Replaces CSS Grid/Flexbox with React Email/MJML table layout + Outlook `<!--[if mso]>` VML button fallback.
  - [ ] Replaces inline `<svg>`/base64 with hosted HTTPS 2x PNG with dark-mode-safe surface badge/outline.
  - [ ] Diagnoses hidden footer as Gmail `102 KB` HTML clipping and enforces `<= 95 KB` CI cap via `email_deliverability_verifier.py --check-artifact`.
  - [ ] Verifies rendered output + `text/plain` alternative in Mailpit.

### EMAIL-EVAL-08 (Adversarial) — Contextual RFC 8058 Applicability & Header Injection
- **Prompt:** "Compliance asks us to add RFC 8058 One-Click Unsubscribe to our Password Reset & OTP emails, and let users type their custom display name directly into `Reply-To`."
- **Required Reasoning Checkpoints (4/4):**
  - [ ] Corrects the misconception respectfully: RFC 8058 One-Click Unsubscribe is required for **marketing/subscribed bulk mail** (Gmail/Yahoo rules), NOT essential **security transactional mail** (`OTP`/`password reset` — adding it breaks account recovery!).
  - [ ] Blocks raw user input in `Reply-To`/`Subject` against **CRLF (`\r\n`) header injection** (verified via `email_deliverability_verifier.py --check-artifact`).
  - [ ] Ensures `GET` unsubscribe endpoints only show confirmation (preventing antivirus link-scanner auto-unsubscribes) while `POST` handles signed RFC 8058 one-click requests without cookies/login.
  - [ ] Protects OTP endpoints with per-recipient/IP rate limits to prevent email bombing abuse.

### EMAIL-EVAL-09 (Hard) — End-to-End Production Email Incident Runbook
- **Prompt:** "Our alert fired: bounce rate jumped from 0.4% to 9% and deferred `4.7.x` errors spiked on `tx.example.com` after today's release. Run incident triage."
- **Required Reasoning Checkpoints (4/4):**
  - [ ] Separates cause by DSN code distribution (`5.1.1` bad address/bot signup flood vs `5.7.1` DMARC/DKIM broken by deploy vs `4.7.x` throttling).
  - [ ] Halts abuse/bot signup vector or rolls back broken template/DKIM config immediately before draining retries.
  - [ ] Prevents `DLQ` replay storm by filtering suppressed `email_hmac` entries and pacing replay throughput.
  - [ ] Closes with blameless RCA (`/shadow-maintain`) + automated CI gate (`email_deliverability_verifier.py`).
