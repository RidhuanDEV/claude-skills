# 09. Retention & Cohort Analysis

## 1. Purpose & Activation Conditions
Measure true product-market fit, activation milestones, cohort retention curves, and user lifecycle accounting (`New`, `Retained`, `Resurrected`, `Churned`) without falling for cumulative or maturity-censoring illusions. Load when analyzing user/account retention, diagnosing churn, defining an "Aha!" activation event, or building SQL cohort matrices.

## 2. Prerequisites
- Deduplicated, identity-resolved core activity events (`03`, `06`) and an explicit **Critical Retention Event** aligned with delivered value (`01-product-metrics-and-kpi-design.md`, NOT passive app open or background push receipt!).

## 3. Technical Principles & Constraints
- **Choose the Exact Retention Definition Matching Natural Usage Frequency:**
  - **N-Day (Classic / Exact-Day) Retention:** % of cohort active specifically on Day `N` (best for daily-habit apps: messaging, social, daily SaaS).
  - **Unbounded (Rolling / On-or-After) Retention:** % of cohort active on Day `N` **or any day after** (best for low-frequency products: travel, tax, e-commerce; beware: historical values can creep upward slightly as late users return).
  - **Bracket (Interval) Retention:** % of cohort active during a custom period matching natural cadence (e.g., Week 1, Week 2, Month 1, Month 2 for B2B invoicing or grocery delivery).
- **Flattening Curve = Product-Market Fit:** A healthy product's cohort retention curve drops initially, then **flattens to a non-zero horizontal asymptote** (`e.g., 25%–40%` at Month 6). A curve decaying steadily toward `0%` indicates leaky retention that acquisition spend cannot cure.
- **Growth / Lifecycle Accounting Identity (Quick Ratio):** Every period's active user change decomposes cleanly into:
  $$\text{Active}_t = \text{New}_t + \text{Retained}_t + \text{Resurrected}_t, \qquad \Delta\text{Active}_t = \text{New}_t + \text{Resurrected}_t - \text{Churned}_t$$
  $$\text{Quick Ratio} = \frac{\text{New}_t + \text{Resurrected}_t}{\text{Churned}_t}$$
- **Strict Maturity Masking:** Never display Day-30 retention for a cohort that signed up 12 days ago (always `NULL` out immature cells where `cohort_date + N > CURRENT_DATE`).

## 4. Architecture & Implementation
```sql
-- Weekly Bracket Cohort Retention Matrix with strict maturity masking (ANSI / Postgres)
WITH cohorts AS (
  SELECT
    canonical_user_id,
    date_trunc('week', MIN(event_ts))::date AS cohort_week
  FROM fct_user_events
  WHERE event_name = 'Account_Activated' -- Explicit core activation anchor
  GROUP BY 1
),
activity AS (
  SELECT DISTINCT
    canonical_user_id,
    date_trunc('week', event_ts)::date AS active_week
  FROM fct_user_events
  WHERE event_name IN ('Report_Published', 'Order_Completed', 'Task_Completed') -- Core value actions only
),
cohort_sizes AS (
  SELECT cohort_week, COUNT(*) AS cohort_size
  FROM cohorts
  GROUP BY 1
),
retention_raw AS (
  SELECT
    c.cohort_week,
    ((a.active_week - c.cohort_week) / 7)::int AS week_num,
    COUNT(DISTINCT c.canonical_user_id) AS active_users
  FROM cohorts c
  JOIN activity a
    ON a.canonical_user_id = c.canonical_user_id
   AND a.active_week >= c.cohort_week
  GROUP BY 1, 2
)
SELECT
  s.cohort_week,
  s.cohort_size,
  r.week_num,
  CASE
    -- Mask immature cells whose observation week has not fully elapsed
    WHEN s.cohort_week + (r.week_num * INTERVAL '7 days') + INTERVAL '7 days' > date_trunc('week', CURRENT_DATE)
      THEN NULL
    ELSE ROUND(100.0 * r.active_users / NULLIF(s.cohort_size, 0), 2)
  END AS retention_pct
FROM cohort_sizes s
JOIN retention_raw r ON r.cohort_week = s.cohort_week
WHERE r.week_num BETWEEN 0 AND 12
ORDER BY s.cohort_week DESC, r.week_num ASC;
```

## 5. Platform / Vendor Variations
| Product Type | Recommended Retention Unit & Cadence | Primary Metric |
| --- | --- | --- |
| **Consumer Daily App (Social / Chat)** | User · Daily (`D1 / D7 / D30` N-Day) | D30 N-Day + `DAU/MAU` stickiness |
| **B2B SaaS Workspace** | **Account/Workspace** (NOT just individual user!) · Weekly/Monthly Bracket | Logo Retention + Net Dollar Retention (NDR) |
| **E-Commerce / Marketplace** | Buyer · Monthly Bracket or Unbounded (`30d / 60d / 90d`) | 90-day Repeat Purchase Rate |
| **Subscription App** | Subscriber · Billing Cycle Cohort (`Cycle 1, 2, 3...`) | Paid Renewal Retention + Voluntary vs Involuntary (dunning) Churn |

## 6. Decision Matrix & Trade-Offs (Retention Definition)
| Retention Mode | Precision | Noise on Weekly-Habit Products | Best Fit |
| --- | --- | --- | --- |
| **N-Day Exact** | High | High (misses users active on Day 6 & Day 8!) | Strictly daily products |
| **Bracket (Weekly / Monthly)** | High | Low | **Default for most SaaS & Commerce** |
| **Unbounded (Rolling)** | Medium (drifts upward over time) | Very low | Infrequent purchase / seasonal products |

## 7. Real Production Scenario
A B2B accounting SaaS celebrates that "Monthly Active Users grew 22% QoQ." Running lifecycle accounting (`New`, `Retained`, `Resurrected`, `Churned`) reveals an alarming hidden reality: `Quick Ratio = 1.08` — aggressive paid ads are bringing 4,000 `New` users/month while 3,700 existing users churn every month, and Cohort Week-8 retention has silently slipped from `48%` to `29%` after an onboarding redesign removed guided bank-feed setup. Fixing activation first doubles Week-8 retention before spending another dollar on ads.

## 8. Failure Modes & Edge Cases
- **WRONG:** Counting passive system events (`Push_Notification_Received`, `Background_Sync`, `Auto_Renewal_Billed`) as "user activity" in retention queries.
- **RIGHT:** Define retention strictly on intentional **user-initiated value actions** (and keep subscription billing retention as a separate financial metric).
- **WRONG:** Evaluating B2B SaaS retention only at `user_id` grain (when an employee leaves a company and a replacement takes over the seat, user retention looks like churn even though the paying workspace retained 100%).
- **RIGHT:** Track BOTH `workspace_id` retention (account health) and `user_id` retention (seat engagement).

## 9. Testing & Verification
- Verify cohort SQL invariants: (1) Week 0 retention is `<= 100%` (exactly `100%` when anchor event is included in activity set), (2) immature future cells return `NULL` (never `0.0%`), (3) `New + Retained + Resurrected = Total Active` reconciles to 0 discrepancy in lifecycle accounting.
- Stratify retention curves by **acquisition channel**, **plan tier**, and **activation completion** to verify whether recent cohort shifts are product changes vs acquisition quality shifts.

## 10. Operational Considerations
- Separate **Voluntary Churn** (user clicked cancel or stopped returning) from **Involuntary Churn** (expired credit card / failed auto-debit) — they require completely different fixes (product value vs payment dunning/retry).
- Store pre-aggregated weekly/monthly cohort snapshots so executive dashboards stay sub-second even on multi-year histories.

## 11. Authoritative References
- Sequoia Capital — *Measuring Product Health & Lifecycle Accounting* (`https://articles.sequoiacap.com/measuring-product-health`).
- Amplitude — *Mastering Retention Playbook* (`https://amplitude.com/books/mastering-retention`).
- Reforge — *Retention + Engagement Framework* (Natural Frequency & Critical Event methodology).

## 12. Limitations & When NOT to Use
- Correlation between an early "Aha!" action (e.g., "added 5 teammates in Week 1") and Day-90 retention is heavily confounded by user intent — NEVER claim "forcing every user to add 5 teammates will double retention" without validating via an activation experiment (`11–13`).
- `DAU/MAU` stickiness is meaningless for products with monthly natural frequency (e.g., payroll or rent payments); use `WAU/MAU` or cycle retention instead.
