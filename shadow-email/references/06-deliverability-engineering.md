# 06 — Deliverability Engineering (`ADVANCED`)

## 1. Purpose & Activation Conditions
Load when diagnosing spam-folder placement, managing IP/domain reputation, planning IP warm-up ramps, handling bounces/complaints, or monitoring Google Postmaster Tools (v2 Compliance Status) & Microsoft SNDS.

## 2. Prerequisites
Modules `01`–`05` (authentication, stream separation, queue pacing).

## 3. Technical Principles & Constraints
- **Sender Reputation Thresholds (Gmail / Yahoo Bulk Sender Baseline):**
  - **Spam Complaint Rate:** Target **`< 0.1%`**; hard danger threshold **`>= 0.3%`** (triggers aggressive spam foldering and `4.7.28` throttling).
  - **Hard Bounce Rate:** Target **`< 1%`** (alert `>= 2%`, freeze campaign `>= 5%`).
- **Shared Pool vs Dedicated IP:** Below `~100,000` steady emails/month, a **reputable shared IP pool** with custom-aligned DKIM/SPF outperforms a cold dedicated IP (which lacks consistent volume to sustain ISP trust).
- **Zero List Buying & Spam Trap Avoidance:** Purchased or stale unengaged lists contain recycled/pristine spam traps; a single trap hit can blocklist an entire sending domain.

## 4. Architecture & Implementation
### 4-Week Dedicated IP / New Subdomain Warm-Up Ramp
| Week | Target Cohort | Daily Volume Cap (Guideline) | Abort / Pause Signal |
| :--- | :--- | :--- | :--- |
| Week 1 | Most engaged users (opened/active `<= 14d`) | `500 -> 2,500 -> 5,000` | Pause immediately if complaint `>= 0.15%` or bounce `>= 2%` |
| Week 2 | Engaged users (`<= 30d`) | `10,000 -> 25,000` | Watch Gmail `4.7.28` deferral rate `< 2%` |
| Week 3 | Active users (`<= 60d`) | `50,000 -> 75,000` | Verify Postmaster v2 Compliance Status passes and user-reported spam rate `< 0.1%` |
| Week 4+ | Full opted-in active base | Ramp `<= +25%/day` to target | Sunset unengaged marketing contacts (`> 180d` 0 opens/clicks) |

Use `python shadow-email/scripts/email_deliverability_verifier.py --classify-dsn <code>` to enforce exact bounce handling (`5.1.1` suppress permanently, `5.7.1` reputation/policy alert, `4.2.2` bounded retry).

```sql
-- Select Week-1 IP warm-up cohort (engaged via real clicks/app activity, NOT Apple MPP opens, excluding suppressed)
SELECT u.user_id, u.email_hash
FROM users u
LEFT JOIN email_suppressions s ON s.email_hmac = u.email_hmac
WHERE u.marketing_opt_in = TRUE
  AND s.email_hmac IS NULL
  AND (u.last_clicked_at >= NOW() - INTERVAL '14 days' OR u.last_app_active_at >= NOW() - INTERVAL '14 days')
ORDER BY GREATEST(COALESCE(u.last_clicked_at, '1970-01-01'), COALESCE(u.last_app_active_at, '1970-01-01')) DESC
LIMIT 2500;
```

## 5. Platform / Vendor Variations
- **Google Postmaster Tools (GPT):** Authoritative source for Gmail sender compliance (v2 Compliance Status; the v1 domain/IP reputation dashboards were retired in 2025), user-reported spam rate, DMARC/SPF/DKIM pass rates, and delivery error taxonomy (`4.7.28` vs `5.7.26`).
- **Microsoft SNDS & JMRP:** Authoritative source for Outlook.com/Hotmail IP reputation and complaint feedback loops.
- **Apple Mail Privacy Protection (MPP):** Pre-fetches tracking pixels — **never treat raw Open Rate alone as proof of human engagement**; combine clicks, app logins, and purchases when defining active warm-up cohorts!

## 6. Decision Matrix & Trade-Offs
| Deliverability Signal | Diagnosis | Corrective Action |
| :--- | :--- | :--- |
| Complaint rate `>= 0.3%` on `news.` | Unwanted frequency, bad list import, or hidden unsubscribe | Pause campaign; scrub unengaged contacts; verify DKIM-signed RFC 8058 |
| `5.7.26` Gmail rejection | Missing SPF/DKIM/DMARC alignment | Fix DNS auth alignment (Module `02`) |
| `4.7.28` Gmail throttling | Sudden volume spike or low IP/domain reputation | Cut concurrency/rate per domain; warm up with engaged cohort |
| Hard bounce `>= 3%` on signup verification | Bot signup spam or missing email typo/MX check | Add CAPTCHA/Turnstile, rate-limit signup, suppress `5.1.1` |

## 7. Real Production Scenario
A SaaS team imported 45,000 two-year-old CRM leads and sent a product announcement on Day 1 from a brand-new domain. Hard bounces hit `8.4%`, complaints hit `0.7%`, and Gmail routed all domain mail to Spam. Recovery required: (1) pausing bulk sends, (2) suppressing all bounces/complaints & purging unverified leads, (3) verifying strict SPF/DKIM/DMARC/RFC 8058, and (4) executing a 3-week re-warm strictly to active logged-in users.

## 8. Failure Modes & Edge Cases (`WRONG` vs `RIGHT`)
- **WRONG:** Provisioning a dedicated IP for 8,000 emails/month, or relying solely on Open Rate (skewed by Apple MPP) to select warm-up cohorts.
  **RIGHT:** Use shared reputation pools under `100k/mo` and base engagement cohorts on clicks + verified in-app activity.
- **WRONG:** Keeping unsubscribed or hard-bounced addresses in marketing exports.
  **RIGHT:** Enforce a central `email_suppressions` check before every outbound send across every worker and ESP.

## 9. Testing & Verification
Verify DNS auth (`--check-dns`), verify bounce webhook suppression writes (`5.1.1` -> suppressed, `4.2.2` -> retry), and audit Postmaster/SNDS metrics weekly during warm-up.

## 10. Operational Considerations
Configure automated circuit-breakers that auto-pause a marketing campaign if its observed bounce rate exceeds `3%` or complaint rate exceeds `0.2%` within the first `1,000` deliveries.

## 11. Authoritative References
- Google Email Sender Guidelines (`support.google.com/a/answer/81126`), Yahoo Sender Best Practices (`senders.yahooinc.com`), Google Postmaster Tools Documentation.

## 12. Limitations & When NOT to Use
Reputation recovery takes 2–6 weeks of clean sending — do not spin up throwaway "burn domains" to evade spam filters (major ISPs fingerprint domain age, content hashes, and shared links, making evasion worse).
