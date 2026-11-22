# 10. Behavioral & Segmentation Analytics

## 1. Purpose & Activation Conditions
Uncover actionable user segments, power-user distributions (`L7/L28`), product journey paths, and behavioral cohorts (including RFM when applicable) to guide personalization, onboarding, and lifecycle interventions. Load when analyzing user journeys, engagement depth, power-user curves, or customer segmentation.

## 2. Prerequisites
- Clean identity-resolved activity marts (`03`, `06`) and established retention baselines (`09-retention-and-cohort-analysis.md`).

## 3. Technical Principles & Constraints
- **Behavioral > Demographic Segmentation:** Segmenting users by *what they do* (feature adoption, workflow depth, session frequency, time-to-value) consistently predicts retention and monetization far better than static demographics alone.
- **Power-User Curve (`L7/L28` or `L30` Histogram):** Plot the distribution of how many days in the last 28/30 days each active user performed the core action (`1` through `28`). Look for the **Right-Side Smile**: a growing right-hand tail (`20+` days/month) proves a hardcore habit-forming segment exists, whereas a purely left-skewed curve (`1–2` days) signals shallow/one-off utility.
- **RFM (Recency, Frequency, Monetary) — Know When Applicable vs NOT Applicable:**
  - **Applicable:** Repeat-purchase e-commerce, B2C marketplaces, QSR/delivery, and usage-based transactional platforms where customers repurchase at variable intervals and basket sizes.
  - **NOT Applicable:** Flat-rate B2B SaaS subscriptions with fixed monthly seats (monetary variance reflects contract tier, not purchasing cadence; use **Feature Adoption + Seat Utilization + Account Health Score** instead).
- **Avoid Over-Fragmentation & Cherry-Picking:** Creating 40 micro-segments guarantees spurious patterns by random chance. Keep operational segments to **4–6 mutually exclusive, collectively exhaustive (MECE)** cohorts tied to concrete product or lifecycle actions.

## 4. Architecture & Implementation
```sql
-- L28 Power-User Distribution + Behavioral Engagement Tiers (Postgres / ANSI SQL)
WITH user_active_days AS (
  SELECT
    canonical_user_id,
    COUNT(DISTINCT DATE(event_ts)) AS active_days_28d,
    COUNT(*) FILTER (WHERE event_name = 'Report_Published') AS core_actions_28d
  FROM fct_user_events
  WHERE event_ts >= CURRENT_DATE - INTERVAL '28 days'
    AND event_ts < CURRENT_DATE
    AND event_name IN ('Report_Published', 'Dashboard_Shared', 'Query_Executed')
  GROUP BY 1
)
SELECT
  active_days_28d,
  COUNT(*) AS users_count,
  ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER (), 2) AS pct_of_active_users,
  CASE
    WHEN active_days_28d >= 16 THEN 'power_user'
    WHEN active_days_28d >= 5 THEN 'core_regular'
    WHEN active_days_28d >= 2 THEN 'casual'
    ELSE 'one_day_visitor'
  END AS engagement_tier
FROM user_active_days
GROUP BY 1
ORDER BY active_days_28d ASC;
```
Journey / Path next-step transition query (identifying dead-ends and loops):
```sql
-- Top 3-step user paths starting from Onboarding_Started
WITH ordered AS (
  SELECT
    canonical_user_id,
    session_id,
    event_name,
    ROW_NUMBER() OVER (PARTITION BY canonical_user_id, session_id ORDER BY event_ts ASC) AS step_no
  FROM fct_user_events
  WHERE event_ts >= CURRENT_DATE - INTERVAL '14 days'
    AND event_name NOT IN ('Page_Heartbeat', 'Tooltip_Hovered') -- Filter noisy telemetry
),
pivoted AS (
  SELECT
    canonical_user_id,
    session_id,
    MAX(CASE WHEN step_no = 1 THEN event_name END) AS step_1,
    MAX(CASE WHEN step_no = 2 THEN event_name END) AS step_2,
    MAX(CASE WHEN step_no = 3 THEN event_name END) AS step_3
  FROM ordered
  WHERE step_no <= 3
  GROUP BY 1, 2
)
SELECT
  step_1,
  COALESCE(step_2, '[EXIT]') AS step_2,
  COALESCE(step_3, '[EXIT]') AS step_3,
  COUNT(*) AS sessions
FROM pivoted
WHERE step_1 = 'Onboarding_Started'
GROUP BY 1, 2, 3
ORDER BY sessions DESC
LIMIT 20;
```

## 5. Platform / Vendor Variations
| Technique | Best Tooling | Pitfall to Watch |
| --- | --- | --- |
| **User Journey / Sankey Paths** | PostHog Paths, Mixpanel Flows, SQL `LEAD()` | Noisy micro-events (`Page_Scrolled`) turn paths into unreadable spaghetti — collapse consecutive duplicate events first |
| **Power-User Curves (`L7/L28`)** | Warehouse SQL / dbt + BI histogram | Mixing first-week signups with tenured users skews Day 1–3 bar artificially high; filter to users registered `>= 28 days` ago! |
| **Behavioral Cohorts & Reverse ETL** | Census / Hightouch / PostHog Cohorts | Avoid syncing stale cohorts to marketing/CRM without opt-in consent check (`04`) |
| **RFM Quintiles (`NTILE(5)`)** | Warehouse SQL | `NTILE(5)` forces arbitrary cutoffs when ties are huge (e.g., 80% of users have `frequency = 1`); prefer explicit business thresholds over blind `NTILE` |

## 6. Decision Matrix & Trade-Offs
| Segmentation Method | Interpretability | Actionability | When to Use |
| --- | --- | --- | --- |
| **Rule-Based Behavioral Cohorts** | Very High | Very High | Default for product, CRM, and onboarding flows |
| **RFM (Explicit Thresholds)** | High | High | Repeat-purchase e-commerce & transactional marketplaces |
| **Unsupervised Clustering (K-Means / GMM)** | Low–Medium | Low unless validated | Exploratory research ONLY; never deploy opaque clusters straight into product rules without human-readable labels |

## 7. Real Production Scenario
A marketplace runs blind `NTILE(5)` RFM scoring and sends a 25% discount voucher to `"At-Risk High-Value"` users. Post-campaign review shows `60%` of recipients had already placed an order only 10 days earlier because `NTILE` bucketed skewed recency poorly, wasting \$45k in margin on organic repeat buyers. Replacing blind `NTILE` with explicit domain-calibrated recency thresholds (based on the 75th percentile inter-purchase interval of 21 days) and validating the voucher via a 10% holdout group proves true incremental lift and saves 68% of promo burn.

## 8. Failure Modes & Edge Cases
- **WRONG:** Including brand-new signups from the last 7 days inside an `L28` power-user curve (they physically cannot have `> 7` active days, artificially inflating the left tail).
- **RIGHT:** Filter `L28` curves strictly to users whose `signup_ts <= CURRENT_DATE - INTERVAL '28 days'`.
- **WRONG:** Leaving consecutive repeated clicks (`Search_Queried -> Search_Queried -> Search_Queried`) uncollapsed in path analysis, hiding real navigation loops and exits.
- **RIGHT:** Collapse adjacent duplicate events (`event_name != LAG(event_name)`) when analyzing journeys unless measuring retry loops explicitly.

## 9. Testing & Verification
- Check MECE property of operational segments: `SUM(segment_users) == total_active_users` with zero overlaps and zero unclassified `NULL` leaks.
- Validate that any segment used for targeting or experimentation is computed strictly from **pre-period** behavior (never leak future behavior into segment assignment!).

## 10. Operational Considerations
- Refresh behavioral segments on a documented cadence (daily batch for CRM/lifecycle; real-time only when sub-minute in-app nudges justify streaming cost).
- Audit segment drift quarterly: as pricing or user mix evolves, static monetary or frequency cutoffs become outdated.

## 11. Authoritative References
- Andrew Chen / a16z — *The Power User Curve: The Best Way to Understand Your Most Engaged Users* (`https://a16z.com/the-power-user-curve/`).
- PostHog Documentation — *User Paths & Cohorts* (`https://posthog.com/docs/product-analytics/paths`).
- Fader, Hardie & Lee — *RFM & Customer Lifetime Value Modeling (BG/NBD)* (Marketing Science).

## 12. Limitations & When NOT to Use
- Segmentation is **descriptive**, not causal: finding that `"Power Users"` adopt Feature Z does not prove pushing Feature Z turns casual users into power users.
- Avoid K-means clustering on raw unscaled, heavy-tailed count variables (`orders`, `revenue`) without log-scaling and outlier inspection — otherwise 1 cluster just isolates 3 extreme whales.
