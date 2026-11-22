# 11 — SEO Observability, Search Console & Incident Auditing (`OPERATIONAL`)

## 1. Purpose & Activation Conditions
Load when investigating sudden organic traffic/impression drops, diagnosing Google Search Console indexing errors, analyzing raw search-bot server logs, or setting up production SEO alerting.

## 2. Prerequisites
Modules `01`–`07` and read-only access to Google Search Console, CDN/origin access logs, and deployment history (`git log`).

## 3. Technical Principles & Constraints
- **Root-Cause Separation (4-Layer Fault Tree):** Every organic traffic drop belongs to one or more distinct layers — NEVER jump to content rewrites before isolating the failing layer:
  1. **Tracking / Analytics Breakage:** Organic traffic didn't actually drop — GA4/PostHog tag broke (cross-check Search Console clicks vs analytics!).
  2. **Technical / Crawling / Indexing Incident:** Accidental `noindex`, broken `robots.txt`, canonical flip, WAF blocking `Googlebot`, `5xx` spike, or broken JS rendering.
  3. **Seasonality / Demand Shift / Competitor:** Impressions drop across entire market queries even while average position stays flat.
  4. **Ranking / Algorithm / Manual Action:** Impressions stay stable or fall alongside sharp average-position drops on specific templates/intents.

## 4. Architecture & Implementation
### Structured Dropped-Page Incident Diagnosis Playbook
1. **Cross-Check Reality (`T+0`):** Compare Google Search Console *Clicks* against `/shadow-analytics` Organic Sessions (if GSC clicks are flat -> analytics tag bug, route to `/shadow-analytics`).
2. **Inspect Live HTTP & HTML (`T+5m`):** Run `curl -sI` + raw HTML inspection on affected URLs checking status code, redirect hops, `X-Robots-Tag`, `<meta name="robots">`, `<link rel="canonical">`, and `/robots.txt`.
3. **Correlate Deployments (`T+10m`):** Align traffic/crawl cliff timestamp against `git log`, CDN/WAF rule edits, and Search Console *Page Indexing* reason buckets (*Excluded by 'noindex'*, *Duplicate without user-selected canonical*, *Server error 5xx*, *Soft 404*).
4. **Analyze Bot Access Logs (`T+20m`):** Segment verified `Googlebot` hits by HTTP status (`200/301/404/403/5xx`), TTFB p95, and URL template to pinpoint exact affected routes.
5. **Remediate + Lock Regression (`T+30m+`):** Ship minimal surgical fix, add failing-then-passing CI test (`seo_audit_verifier.py`), and trigger Search Console URL Inspection / sitemap re-ping.

```bash
# Quick production incident triage: status, single-hop Location, X-Robots-Tag, and canonical
curl -sS -D - -o /tmp/page.html "https://example.com/products/flagship" | grep -iE "^(HTTP/|location:|x-robots-tag:|cache-control:)"
grep -iE "(meta name=\"robots\"|rel=\"canonical\")" /tmp/page.html
```

## 5. Platform / Vendor Variations
- **Google Search Console API / BigQuery Export:** Export daily GSC data to BigQuery/warehouse for `> 16 months` historical retention and template-level anomaly queries (Search Console UI caps rows at `1,000`).
- **CDN Logs (Cloudflare Logpush / Nginx / CloudFront):** Verify real `Googlebot` IP ranges (official JSON range list) rather than trusting spoofable `User-Agent` strings alone.

## 6. Decision Matrix & Trade-Offs
| Observed Signal | Probable Layer | First Verification Command / Check |
| :--- | :--- | :--- |
| Analytics organic down 80%, GSC clicks flat | Analytics Tag Bug | Inspect client tag firing & consent gate (`/shadow-analytics`) |
| Sharp cliff 24–72h after deploy + GSC `noindex` spike | Technical Release Bug | `curl -sI` headers, `<meta robots>`, `git diff` middleware |
| `Googlebot` hits drop to 0 or spike `403`/`5xx` | WAF / Origin Infra | Check WAF bot rules, TLS cert, origin `5xx` logs (`/shadow-ops`) |
| Gradual multi-week slide, 0 technical errors, position drop | Content / Algorithm / Competition | Compare query/template CTR, intent match, Core Web Vitals CrUX |

## 7. Real Production Scenario
Organic traffic dropped 58% over 5 days after a Next.js middleware upgrade. Engineers initially suspected a Google algorithm update. Running `curl -I` immediately revealed `X-Robots-Tag: noindex` leaking onto production because `VERCEL_ENV` check fell back to non-production on self-hosted Docker. Fixing the host allowlist + adding `seo_audit_verifier.py` to CI restored rankings in 12 days.

## 8. Failure Modes & Edge Cases (`WRONG` vs `RIGHT`)
- **WRONG:** Rewriting copy or changing URLs during an unverified traffic dip (compounds damage when root cause was a `robots.txt` or `canonical` bug!).
  **RIGHT:** Complete the 4-layer diagnostic fault tree (`Analytics -> Technical -> Demand -> Ranking`) before touching content or URLs.
- **WRONG:** Trusting Search Console's 2–3 day reporting lag as your only alert for broken production `robots.txt` or `noindex`.
  **RIGHT:** Run synthetic production monitors every 15 minutes checking `robots.txt` hash, `200` status, and zero `noindex` on top landing pages.

## 9. Testing & Verification
Verify alerting synthetic checks fire on simulated staging `noindex` or `robots.txt Disallow: /`, and confirm bot log parsers accurately flag `5xx > 1%`.

## 10. Operational Considerations
Maintain an **SEO Incident Log** recording deploy dates, migration dates, major template launches, and Google Core Update dates so future analysts never misattribute seasonal or deploy changes.

## 11. Authoritative References
- Google Search Central — *Debugging Drops in Google Search Traffic*, *Page Indexing Report*, *Verifying Googlebot*.

## 12. Limitations & When NOT to Use
Search Console reports lag by 24–72 hours and sample anonymized queries; never rely solely on GSC UI for real-time outage detection — combine GSC with real-time server/CDN logs and synthetic monitors.
