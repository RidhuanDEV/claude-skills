# 01 — Email Protocol Fundamentals (`CORE`)

## 1. Purpose & Activation Conditions
Load when debugging low-level SMTP/MIME delivery failures, understanding why `250 OK` does not guarantee inbox placement, parsing enhanced DSN bounce codes, or inspecting raw email headers (`Return-Path`, `Received`, `Authentication-Results`).

## 2. Prerequisites
Basic networking (TCP/TLS, DNS MX/TXT/PTR records) and HTTP/API concepts.

## 3. Technical Principles & Constraints
- **Envelope (`RFC 5321`) vs Header (`RFC 5322`):**
  - **SMTP Envelope (`MAIL FROM:` / `Return-Path`, `RCPT TO:`):** Governs routing, bounce destination, and **SPF** verification.
  - **Internet Message Format Header (`From:`, `To:`, `Reply-To:`, `Subject:`, `Message-ID:`):** Governs what the human sees in the inbox and what **DMARC** aligns against.
- **MIME (`RFC 2045–2049`):** Always construct `multipart/alternative` with `text/plain; charset=utf-8` first and `text/html; charset=utf-8` second (highest-fidelity part last per RFC 2046).
- **Enhanced Status Codes (`RFC 3463`):** `2.x.x` = accepted by next hop (NOT guaranteed delivered to inbox!), `4.x.x` = persistent transient deferral (retryable with backoff), `5.x.x` = permanent failure (`5.1.1` bad mailbox -> suppress; `5.7.x` policy/security rejection -> fix auth/reputation).

## 4. Architecture & Implementation
```ts
export interface ParsedSmtpReply {
  readonly basicCode: number;       // e.g., 250, 421, 550
  readonly enhancedCode: string;    // e.g., "5.1.1", "4.7.28"
  readonly category: "ACCEPTED_BY_HOP" | "TRANSIENT_DEFER" | "PERMANENT_MAILBOX" | "POLICY_SECURITY_REJECT";
}

export function classifySmtpReply(basicCode: number, enhancedCode: string): ParsedSmtpReply {
  const clean = enhancedCode.trim();
  if (basicCode >= 200 && basicCode < 300) {
    return { basicCode, enhancedCode: clean, category: "ACCEPTED_BY_HOP" };
  }
  if (clean.startsWith("5.7.") || basicCode === 554) {
    return { basicCode, enhancedCode: clean, category: "POLICY_SECURITY_REJECT" };
  }
  if (basicCode >= 500 || clean.startsWith("5.")) {
    return { basicCode, enhancedCode: clean, category: "PERMANENT_MAILBOX" };
  }
  return { basicCode, enhancedCode: clean, category: "TRANSIENT_DEFER" };
}
```

## 5. Platform / Vendor Variations
- **HTTP API vs SMTP Submission (`587`/`465`):** Prefer provider HTTPS APIs (`SES v2`, `Resend`, `Postmark`) over raw SMTP connections in cloud/serverless apps — HTTPS APIs return structured JSON message IDs immediately and avoid multi-RTT SMTP handshakes and blocked port `25`.
- **STARTTLS (`587`) vs Implicit TLS (`465`):** RFC 8314 prefers implicit TLS on port `465` for mail submission when SMTP must be used.

## 6. Decision Matrix & Trade-Offs
| Signal / Header | Governing RFC | Diagnostic Meaning |
| :--- | :--- | :--- |
| `Return-Path` vs `From:` | `RFC 5321` vs `RFC 5322` | SPF checks `Return-Path`; DMARC requires SPF/DKIM alignment with `From:` |
| `Message-ID` (`<uuid@tx.example.com>`) | `RFC 5322` | Required unique message identifier; aids threading & ESP support tracing |
| `Authentication-Results` | `RFC 8601` | Shows exact receiving-server SPF/DKIM/DMARC verdicts |
| `4.7.28` vs `5.1.1` | `RFC 3463` | `4.7.28` = Gmail rate/reputation throttle; `5.1.1` = nonexistent mailbox |

## 7. Real Production Scenario
An app logged `"Email sent: 250 2.0.0 Ok"` for every invoice, yet clients received nothing. Inspecting raw headers on a test inbox showed `Authentication-Results: dmarc=fail (p=quarantine)` because the ESP sent `Return-Path` on an unaligned shared domain while DKIM was unsigned. `250 OK` merely meant the relay queued the message.

## 8. Failure Modes & Edge Cases (`WRONG` vs `RIGHT`)
- **WRONG:** Assuming SMTP `250 OK` proves inbox delivery, or connecting over unencrypted port `25` from app containers.
  **RIGHT:** Track asynchronous provider delivery/bounce/complaint webhooks and send via authenticated HTTPS ESP APIs (or TLS port `465`/`587`).
- **WRONG:** Omitting `Message-ID` or `Date` headers, or sending HTML-only MIME without `text/plain`.
  **RIGHT:** Emit compliant `RFC 5322` headers and `multipart/alternative` (`text/plain` + `text/html`).

## 9. Testing & Verification
Inspect raw MIME source (headers + boundary parts) in local **Mailpit** (`:8025` Raw tab) and validate DSN handling with `python shadow-email/scripts/email_deliverability_verifier.py --classify-dsn 5.1.1`.

## 10. Operational Considerations
Log provider `message_id` and `smtp_enhanced_code` (never recipient secrets/OTP) so support can trace any missing email end-to-end across ESP logs.

## 11. Authoritative References
- IETF **RFC 5321** (SMTP), **RFC 5322** (Internet Message Format), **RFC 2046** (MIME), **RFC 3463** (Enhanced Mail Status Codes), **RFC 8314** (Cleartext Considered Obsolete for Email).

## 12. Limitations & When NOT to Use
Do not run custom self-hosted Postfix/Exim outbound MTAs for standard web apps unless you have dedicated deliverability operations — managed ESPs handle IP reputation, TLS, feedback loops, and bounce parsing far more reliably.
