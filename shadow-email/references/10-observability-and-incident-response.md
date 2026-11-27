# 10. Observability & Incident Response

## 1. Purpose & Activation Conditions
Instrument end-to-end email delivery telemetry, configure actionable SLO alerts, and execute root-cause incident runbooks when emails vanish, bounce, land in spam, or back up in queues. Load when setting up email monitoring dashboards, diagnosing `"250 OK but not in inbox"` tickets, or handling deliverability incidents.

## 2. Prerequisites
- Normalized webhook ingestion from all active ESPs (`09-esp-integration-and-failover.md`) and queue metrics (`05-queue-and-reliability-engineering.md`).
- Access to Google Postmaster Tools, Microsoft SNDS, and DMARC aggregate (`rua`) reports.

## 3. Technical Principles & Constraints
- **Full Delivery Funnel Visibility:** HTTP `200 OK` from an ESP API only proves **acceptance**, not **delivery** or **inbox placement**. Track every stage per `(stream, template, esp, recipient_domain_group)`:
  `outbox_created -> enqueued -> esp_accepted -> smtp_delivered | smtp_deferred | bounced_soft | bounced_hard | complained | suppressed_pre_send`.
- **Two Orthogonal Health Axes:**
  1. **Latency & Queue Health (SRE):** OTP p95 end-to-end delivery latency (`outbox_created` to `smtp_delivered`), queue lag, DLQ growth, worker error rate.
  2. **Reputation & Inbox Health (Deliverability):** Hard-bounce rate, spam-complaint rate, deferral rate by mailbox provider (`gmail.com`, `outlook.com`, `yahoo.com`, `corporate`), and DMARC alignment pass rate (`>= 99%`).
- **Privacy-Safe Telemetry:** Never emit raw email addresses, OTP codes, or message bodies into Prometheus labels, Sentry breadcrumbs, or Loki logs. Use `message_id`, `template_name`, `recipient_domain` (cardinality-capped top domains + `other`), and `smtp_enhanced_code`.

## 4. Architecture & Implementation
```sql
-- Daily deliverability & latency SLI query segmented by stream and recipient domain group
SELECT
  date_trunc('hour', created_at) AS hour_bucket,
  stream,
  CASE
    WHEN recipient_domain IN ('gmail.com', 'googlemail.com') THEN 'gmail'
    WHEN recipient_domain IN ('outlook.com', 'hotmail.com', 'live.com') THEN 'microsoft'
    WHEN recipient_domain IN ('yahoo.com', 'ymail.com') THEN 'yahoo'
    ELSE 'other'
  END AS provider_group,
  COUNT(*) AS total_attempted,
  COUNT(*) FILTER (WHERE status = 'delivered') AS delivered,
  COUNT(*) FILTER (WHERE status = 'bounced_hard') AS hard_bounces,
  COUNT(*) FILTER (WHERE status = 'complained') AS complaints,
  ROUND(100.0 * COUNT(*) FILTER (WHERE status = 'bounced_hard') / NULLIF(COUNT(*), 0), 3) AS hard_bounce_pct,
  ROUND(100.0 * COUNT(*) FILTER (WHERE status = 'complained') / NULLIF(COUNT(*), 0), 4) AS complaint_pct,
  PERCENTILE_CONT(0.95) WITHIN GROUP (
    ORDER BY EXTRACT(EPOCH FROM (delivered_at - created_at))
  ) FILTER (WHERE status = 'delivered') AS p95_delivery_sec
FROM email_delivery_events
WHERE created_at >= NOW() - INTERVAL '24 hours'
GROUP BY 1, 2, 3
ORDER BY 1 DESC, total_attempted DESC;
```

## 5. Platform / Vendor Variations
| Signal Source | What It Reveals | Cadence / Lag |
| --- | --- | --- |
| **ESP Webhooks** | Exact `4.x.x` / `5.x.x` SMTP codes, delivery latency, bounces, FBL complaints | Real-time (seconds) |
| **Google Postmaster Tools** | v2 Compliance Status + user-reported spam rate (`< 0.10%` target); the v1 IP/domain reputation dashboards were retired in 2025 | Daily (~24–48h lag) |
| **Microsoft SNDS / JMRP** | Outlook/Hotmail IP filter status (green/yellow/red), trap hits, complaint feedback | Daily |
| **DMARC `rua` XML Reports** | Unauthorized senders spoofing your domain + legitimate services missing DKIM/SPF alignment | Daily XML digests |

## 6. Decision Matrix & Trade-Offs (Alert Thresholds & Runbook Triggers)
| Metric | Warning Alert | Critical Page | Immediate First Action |
| --- | --- | --- | --- |
| **OTP p95 Delivery Latency** | `> 15s` (5m) | `> 45s` (5m) | Check queue depth, worker saturation, and ESP API latency / `4.x.x` deferrals |
| **Hard Bounce Rate (1h rolling)** | `> 1.5%` | `> 3.0%` | Pause marketing/bulk stream; inspect newly imported lists or bot signups |
| **Spam Complaint Rate (Postmaster / FBL)** | `>= 0.08%` | `>= 0.25%` | Halt offending campaign immediately; audit opt-in source & RFC 8058 unsubscribe |
| **DMARC Alignment Pass Rate** | `< 99.0%` | `< 95.0%` | Inspect `rua` report for misconfigured subdomain, rotated DKIM key, or SPF `> 10` lookups |
| **DLQ Depth (Transactional)** | `> 10` msgs | `> 50` msgs | Inspect top error codes (`401` expired key vs `422` template bug); fix before replay |

## 7. Real Production Scenario
Customer support escalates: `"Users on @outlook.com and @company.co.id are not receiving invoice emails, though our dashboard shows Sent."`
**Structured RCA Runbook (`250 OK` Missing in Inbox):**
1. Query `email_delivery_events` segmented by `provider_group`: Gmail shows `99.4% delivered`, Microsoft shows `72% deferred (4.7.650)` and `18% bounced (5.7.1)`.
2. Inspect raw SMTP diagnostic string from ESP webhook: `550 5.7.1 Service unavailable, Client host [x.x.x.x] blocked using Spamhaus` (or DMARC fail).
3. Check recent DNS/DMARC `rua` + `email_deliverability_verifier.py`: discover a newly added CRM tool pushed SPF to 12 DNS lookups (`permerror`), breaking SPF alignment on a shared IP.
4. Mitigation: flatten/trim SPF back to `<= 8` lookups, verify DKIM alignment on invoice subdomain, pause non-essential marketing on that IP, and request Microsoft delisting once metrics stabilize.

## 8. Failure Modes & Edge Cases
- **WRONG:** Alerting only on HTTP `5xx` from the ESP API while ignoring webhook delivery/bounce/deferral telemetry (blind to silent spam-foldering and async `5.7.1` rejections).
- **RIGHT:** Pair API health alerts with asynchronous webhook funnel alerts segmented by recipient provider (`gmail`, `microsoft`, `yahoo`, `other`).
- **WRONG:** Putting full `recipient_email` as a Prometheus metric label (explodes TSDB cardinality and leaks PII into monitoring).
- **RIGHT:** Bound labels strictly to low-cardinality enums (`stream`, `template`, `esp`, `provider_group`, `outcome`).

## 9. Testing & Verification
- Simulate synthetic `hard_bounce` and `complaint` webhook events in staging; verify Prometheus/SQL counters increment, suppression writes succeed, and alert rules fire cleanly.
- Run a quarterly tabletop drill of the `"ESP API key expired"` and `"SPF permerror"` runbooks to confirm MTTR `< 15 minutes`.

## 10. Operational Considerations
- Retain detailed delivery event rows (with masked or hashed recipient reference) for 30–90 days to answer support tickets (`"Was my invoice sent on Nov 12?"`) without keeping raw email body PII indefinitely.
- Link every email support ticket directly to `internal_message_id` and `provider_message_id` so engineers trace the exact SMTP transcript in `< 30 seconds`.

## 11. Authoritative References
- Google Postmaster Tools Help — *Dashboards & Compliance Status* (`https://support.google.com/mail/answer/16594218`).
- Microsoft SNDS — *Smart Network Data Services* (`https://sendersupport.olc.protection.outlook.com/snds/`).
- IETF RFC 9989 — *DMARC* (obsoletes RFC 7489; `pct` tag removed) and RFC 9990 — *DMARC Aggregate Reporting (`rua`)* (`https://www.rfc-editor.org/rfc/rfc9989.html`).

## 12. Limitations & When NOT to Use
- Google Postmaster Tools requires a minimum daily Gmail volume (typically several hundred messages/day) before displaying spam-rate data; low-volume domains must supplement with seed-list inbox placement tests and strict webhook bounce/deferral tracking.
- Do not infer inbox placement from open-tracking pixels (Apple MPP inflates opens artificially); rely on Postmaster Compliance Status and user-reported spam rate, bounce/deferral codes, and seed-list placement instead.
