# 11. Testing & Production Readiness

## 1. Purpose & Activation Conditions
Verify email infrastructure end-to-end across local development, staging, CI gates, and production rollout without ever leaking test emails to real customers. Load when setting up local SMTP capture (Mailpit), staging email sinks, CI deliverability/template tests, or pre-launch production checklists.

## 2. Prerequisites
- Local Docker/binary tooling for Mailpit (`localhost:1025` SMTP / `localhost:8025` HTTP API) and `shadow-email/scripts/email_deliverability_verifier.py`.
- All upstream contracts (`02-authentication`, `03-architecture`, `04-rendering`, `07-consent`, `08-security`) implemented.

## 3. Technical Principles & Constraints
- **Staging Sink Guarantee (Zero Customer Leakage):** Staging and QA environments MUST NEVER be able to deliver email to real customer addresses, even if seeded with anonymized/snapshot data. Enforce a **hard recipient allowlist guard** (`ALLOWED_TEST_RECIPIENT_DOMAINS` such as `@company.internal` or rerouting all non-allowlisted recipients to a Mailpit/sink inbox) inside the lowest-level `EmailProviderPort` wrapper — not just in UI config.
- **Automated 4-Layer Test Pyramid for Email:**
  1. **Unit / Static Gates (CI, ms):** DNS SPF/DKIM/DMARC validator, RFC 8058 category-header validator, HTML rendering/dark-mode/size/accessibility linter (`email_deliverability_verifier.py`), CRLF header-injection fuzz tests.
  2. **Contract / Integration Tests (CI, seconds):** Outbox transaction + worker dispatch into local **Mailpit** (`http://127.0.0.1:8025/api/v1/messages`), asserting exact MIME structure (`multipart/alternative` with both `text/html` and `text/plain`), idempotency under duplicate jobs, and webhook signature verification + suppression write.
  3. **Client Rendering Visual QA (Pre-release):** Inspect Outlook Classic (Word), Gmail Web/App dark mode, and Apple Mail via Litmus / Email on Acid or physical test devices.
  4. **Production Canary & Seed-List Check (Post-deploy):** Send one real canary email per stream to owned Gmail, Outlook, and Yahoo seed accounts and inspect raw `Authentication-Results` (`spf=pass`, `dkim=pass`, `dmarc=pass`) and folder placement (`Inbox` vs `Spam`).
- **Ephemeral Test Container Hygiene:** When running Mailpit via Docker in automated tests, always pass `--rm --label shadow.ephemeral=true` and tear it down in `try/finally`.

## 4. Architecture & Implementation
```typescript
export interface StagingGuardConfig {
  readonly environment: 'development' | 'staging' | 'production';
  readonly allowedDomains: readonly string[];
  readonly sinkAddress: string;
}

export function enforceNonProdRecipientGuard(
  recipients: readonly string[],
  config: StagingGuardConfig
): readonly string[] {
  if (config.environment === 'production') {
    return recipients;
  }
  const allowSet = new Set(config.allowedDomains.map((d) => d.toLowerCase()));
  return recipients.map((addr) => {
    const domain = addr.split('@')[1]?.toLowerCase() ?? '';
    return allowSet.has(domain) ? addr : config.sinkAddress;
  });
}

// Integration assertion against local Mailpit HTTP API
export interface MailpitMessageSummary {
  readonly ID: string;
  readonly Subject: string;
  readonly To: readonly { readonly Address: string }[];
}

function parseMailpitSummary(item: unknown): MailpitMessageSummary | null {
  if (typeof item !== 'object' || item === null) return null;
  const id = 'ID' in item && typeof item.ID === 'string' ? item.ID : null;
  const subject = 'Subject' in item && typeof item.Subject === 'string' ? item.Subject : null;
  const rawTo = 'To' in item && Array.isArray(item.To) ? item.To : null;
  if (!id || !subject || !rawTo) return null;
  const toList: { readonly Address: string }[] = [];
  for (const entry of rawTo) {
    if (typeof entry === 'object' && entry !== null && 'Address' in entry && typeof entry.Address === 'string') {
      toList.push({ Address: entry.Address });
    }
  }
  return { ID: id, Subject: subject, To: toList };
}

export async function waitForMailpitMessage(
  apiBaseUrl: string,
  recipientEmail: string,
  timeoutMs = 5000
): Promise<MailpitMessageSummary> {
  const deadline = Date.now() + timeoutMs;
  while (Date.now() < deadline) {
    const res = await fetch(`${apiBaseUrl}/api/v1/search?query=to:${encodeURIComponent(recipientEmail)}`);
    if (res.ok) {
      const data: unknown = await res.json();
      if (
        typeof data === 'object' &&
        data !== null &&
        'messages' in data &&
        Array.isArray(data.messages) &&
        data.messages.length > 0
      ) {
        const parsed = parseMailpitSummary(data.messages[0]);
        if (parsed !== null) {
          return parsed;
        }
      }
    }
    await new Promise((resolve) => setTimeout(resolve, 150));
  }
  throw new Error(`Timed out waiting for email to ${recipientEmail} in Mailpit`);
}
```

## 5. Platform / Vendor Variations
| Tool / Environment | Best For | Limitation |
| --- | --- | --- |
| **Mailpit** (Go binary / Docker) | Local dev & CI SMTP capture + HTML/link/spam-score inspection API | Does not test real ISP spam filters or DNS auth |
| **Amazon SES Mailbox Simulator** | Testing real SES bounce (`bounce@simulator.amazonses.com`), complaint (`complaint@simulator.amazonses.com`), and OOTO webhooks safely without harming reputation | SES-specific addresses |
| **Litmus / Email on Acid** | Cross-client screenshot rendering (Outlook Classic Word, Gmail dark mode, iOS Mail) | Paid SaaS; run on template PRs, not every backend commit |
| **Owned Seed Accounts (Gmail/Outlook/Yahoo)** | End-to-end production DNS auth (`Authentication-Results`) & real inbox placement | Manual or scheduled canary; keep volume tiny |

## 6. Decision Matrix & Trade-Offs (Production Go-Live Gate)
| Gate Check | Mandatory for Launch? | Verification Method |
| --- | --- | --- |
| **SPF `<= 10` lookups, DKIM 2048-bit aligned, DMARC published** | YES (Blocking) | `email_deliverability_verifier.py --check-dns` + live `dig TXT` |
| **RFC 8058 headers present on marketing, absent on security OTP** | YES (Blocking) | `email_deliverability_verifier.py --check-headers` |
| **Template `< 102 KB`, table-safe, `text/plain` companion, no scripts** | YES (Blocking) | `email_deliverability_verifier.py --check-template` |
| **Staging recipient guard active in non-prod** | YES (Blocking) | Automated integration test asserting non-allowlist reroutes to sink |
| **Signed webhooks writing to `email_suppressions`** | YES (Blocking) | SES simulator / signed test webhook E2E |
| **Google Postmaster Tools verified + DMARC `rua` ingesting** | YES (Blocking for bulk) | Postmaster domain verification DNS TXT + first `rua` receipt |

## 7. Real Production Scenario
A developer runs a billing backfill script on staging that uses a production-like database dump. Because staging shares the production Resend API key with no recipient allowlist guard, 14,000 real customers receive fake `"Payment Overdue"` emails with broken staging links, triggering 190 spam complaints and cratering production domain reputation overnight. Enforcing separate environment credentials + `enforceNonProdRecipientGuard` inside the adapter + Mailpit sink in staging makes this failure mode structurally impossible.

## 8. Failure Modes & Edge Cases
- **WRONG:** Mocking `emailProvider.send = vi.fn()` in every test and never verifying real MIME headers, `text/plain` fallback, or HTML template size.
- **RIGHT:** Keep unit tests fast with fakes, AND run CI integration tests against Mailpit + `email_deliverability_verifier.py` on every template/pipeline PR.
- **WRONG:** Testing bounces in production by sending to intentionally fake addresses (`asdasd@gmail.com`), which inflates your real hard-bounce rate and trips ISP spam traps.
- **RIGHT:** Use official provider simulators (`bounce@simulator.amazonses.com`, Resend `bounced@resend.dev`) or local Mailpit.

## 9. Testing & Verification
- Run full offline suite:
  - `python shadow-email/scripts/email_deliverability_verifier.py --self-test`
  - `python -m unittest discover -s shadow-email/tests -v`
- Inspect a real production canary email's raw source (`Show original` in Gmail) and confirm `SPF: PASS`, `DKIM: PASS`, `DMARC: PASS`, aligned `d=` domain, and `Inbox` placement.

## 10. Operational Considerations
- Run weekly automated canary probes on every active sending stream (`auth`, `billing`, `marketing`) to detect silent DNS edits, expired DKIM keys, or broken webhook certs before customers notice.
- Clean up temporary Mailpit containers and staging test emails after CI runs (`Rule #29`).

## 11. Authoritative References
- Mailpit Documentation — *SMTP & REST API Testing* (`https://mailpit.axllent.org/docs/`).
- Amazon SES Developer Guide — *Testing Sending with the Mailbox Simulator* (`https://docs.aws.amazon.com/ses/latest/dg/send-email-simulator.html`).
- Google Workspace Admin Help — *Check Email Authentication Headers* (`https://support.google.com/mail/answer/180707`).

## 12. Limitations & When NOT to Use
- Mailpit and unit checks cannot predict spam-filter ML classification caused by sudden sending volume spikes or poor list acquisition; always pair CI gates with gradual IP warm-up (`06-deliverability-engineering.md`) and live Postmaster monitoring (`10-observability-and-incident-response.md`).
- Do not run heavy visual screenshot matrix builds on backend-only commits; scope Litmus/Email-on-Acid triggers to changes under `emails/` or `templates/`.
