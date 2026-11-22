# 02 — Authentication & Domain Security (`CORE`)

## 1. Purpose & Activation Conditions
Load when configuring or auditing `SPF`, `DKIM`, `DMARC`, custom domain alignment, `PTR/rDNS`, `MTA-STS`, `TLS-RPT`, or `BIMI` on sending domains/subdomains.

## 2. Prerequisites
Module `01` (envelope `MAIL FROM` vs header `From:`) and DNS management access.

## 3. Technical Principles & Constraints
- **SPF (`RFC 7208`) Hard 10-Lookup Ceiling:** Exceeding **10 DNS lookup mechanisms** (`include:`, `a`, `mx`, `ptr`, `exists:`, `redirect=`) causes `PermError` and fails SPF silently across receivers! Isolating streams onto dedicated subdomains (`tx.`, `news.`, `support.`) prevents lookup bloat.
- **DKIM (`RFC 6376`):** Use **2048-bit RSA** (1024-bit minimum legacy) with custom domain signing (`d=tx.example.com`) and periodic selector rotation (`s2026a -> s2026b`). Sign critical headers (`From`, `To`, `Subject`, `Date`, `Message-ID`, plus `List-Unsubscribe` & `List-Unsubscribe-Post` on bulk/subscribed mail).
- **DMARC (`RFC 7489` / Standards Track Updates):** Requires SPF **or** DKIM to pass **AND align** with the `RFC 5322 From:` domain (`adkim=s/r`, `aspf=s/r`). Roll out safely: `p=none` + `rua` monitoring (`2–4 weeks`) -> `p=quarantine; pct=25 -> 100` -> `p=reject`.
- **Transport Encryption Enforcement:** Publish **MTA-STS (`RFC 8461`)** (`_mta-sts` TXT + `https://mta-sts.<domain>/.well-known/mta-sts.txt`) + **TLS-RPT (`RFC 8460`)** (`_smtp._tls`) to block SMTP STARTTLS downgrade attacks.

## 4. Architecture & Implementation
```dns
; Dedicated transactional subdomain (keeps SPF lookups tiny & isolates reputation)
tx.example.com.                   IN TXT "v=spf1 include:amazonses.com -all"
s2026a._domainkey.tx.example.com. IN TXT "v=DKIM1; k=rsa; p=<2048BIT_PUBLIC_KEY>"
_dmarc.tx.example.com.            IN TXT "v=DMARC1; p=reject; adkim=s; aspf=s; rua=mailto:dmarc-rua@example.com"
_mta-sts.tx.example.com.          IN TXT "v=STSv1; id=2026112201"
_smtp._tls.tx.example.com.        IN TXT "v=TLSRPTv1; rua=mailto:tls-rpt@example.com"
```
Validate DNS configuration offline before cutover via `python shadow-email/scripts/email_deliverability_verifier.py --check-dns dns_spec.json`.

## 5. Platform / Vendor Variations
- **Amazon SES / Resend / Postmark / SendGrid:** Always configure a **Custom `MAIL FROM` / Return-Path** subdomain (e.g., `bounces.tx.example.com`) AND CNAME-delegated DKIM selectors so BOTH SPF and DKIM align cleanly with `tx.example.com`.
- **Apex Domain Defense:** Even if `example.com` sends zero mail (all mail uses subdomains), publish `v=spf1 -all` + `_dmarc.example.com "v=DMARC1; p=reject; ..."` on parked/non-sending domains to block spoofing!

## 6. Decision Matrix & Trade-Offs
| Security Stage | Policy Configuration | Objective |
| :--- | :--- | :--- |
| New Sending Subdomain (Week 1–3) | SPF `~all` + 2048-bit DKIM + DMARC `p=none; rua=...` | Inventory every legitimate sender via aggregate XML reports |
| Verified Alignment (Week 4–6) | SPF `-all` + DMARC `p=quarantine; pct=100` | Route spoofed/unaligned mail to spam safely |
| Hardened Production | DMARC `p=reject` + MTA-STS `enforce` + TLS-RPT (+ optional BIMI VMC) | Maximum anti-spoofing, TLS integrity & brand trust |

## 7. Real Production Scenario
A company added 5 SaaS tools (`Zendesk`, `HubSpot`, `Mailchimp`, `SES`, `Google Workspace`) into the root domain SPF record, hitting 14 DNS lookups -> SPF `PermError` broke delivery across corporate Exchange servers. Moving each tool onto its own subdomain (`tx.`, `news.`, `support.`) dropped every SPF record to `<= 4` lookups and raised DMARC pass rate to `99.8%`.

## 8. Failure Modes & Edge Cases (`WRONG` vs `RIGHT`)
- **WRONG:** Publishing `p=reject` on Day 1 without auditing `rua` reports (blocks legitimate invoices sent by finance/ERP SaaS!) or publishing two separate `v=spf1` TXT records on the same host (invalidates SPF completely!).
  **RIGHT:** Keep strictly ONE `v=spf1` record per host (`<= 10` lookups), monitor `rua` reports under `p=none` first, then tighten incrementally.
- **WRONG:** Using `+all` in SPF or leaving DKIM on the ESP's default domain (`d=sendgrid.net`).
  **RIGHT:** Terminate SPF with `~all`/`-all` and configure custom aligned 2048-bit DKIM.

## 9. Testing & Verification
Run `email_deliverability_verifier.py --check-dns dns.json`, inspect live TXT records (`Resolve-DnsName -Type TXT` / `dig TXT`), and send a test email to inspect `Authentication-Results: spf=pass dkim=pass dmarc=pass`.

## 10. Operational Considerations
Rotate DKIM selectors every 6–12 months using **dual-selector overlap** (publish new `s2027a`, switch signing, keep old `s2026a` live for 7 days for in-flight mail before removing).

## 11. Authoritative References
- IETF **RFC 7208** (SPF), **RFC 6376** (DKIM), **RFC 7489** (DMARC), **RFC 8461** (MTA-STS), **RFC 8460** (TLS-RPT); Google & Yahoo Bulk Sender Guidelines.

## 12. Limitations & When NOT to Use
SPF breaks on traditional email forwarding (envelope IP changes); therefore **DKIM alignment** is essential so forwarded mail continues passing DMARC cleanly.
