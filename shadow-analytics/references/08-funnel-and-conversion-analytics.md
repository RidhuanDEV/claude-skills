# 08. Funnel & Conversion Analytics

## 1. Purpose & Activation Conditions
Design accurate conversion funnels, drop-off diagnostics, conversion windows, and attribution analyses while avoiding timestamp-ordering bugs, denominator mismatches, and Simpson's paradox. Load when building SQL/BI funnels, diagnosing checkout or onboarding drop-offs, or reconciling funnel numbers across tools.

## 2. Prerequisites
- Deduplicated, identity-resolved event table (`03-identity-resolution.md`, `06-analytics-data-architecture.md`) with reliable timestamps (`event_ts`).

## 3. Technical Principles & Constraints
- **Explicit Funnel Semantics (State Every Parameter Upfront):** Two analysts will get wildly different conversion rates on the exact same data unless 5 parameters are explicitly locked:
  1. **Counting Unit:** Unique Users (`canonical_user_id`), Unique Accounts/Workspaces (B2B), or Unique Sessions/Orders.
  2. **Order Mode:** **Strict Ordered** (`A -> B -> C` in sequence), **Exact Adjacent** (no intermediate steps), or **Unordered** (did all steps within window regardless of order).
  3. **Conversion Window:** Maximum elapsed time from Step 1 to final step (e.g., `1 hour` for e-commerce checkout, `7 days` for B2B onboarding, `30 days` for enterprise trial-to-paid).
  4. **Property Hold-Constant:** Whether steps must share the same `checkout_id`, `cart_id`, or `product_id` (prevents User buying Product B from being falsely credited to viewing Product A!).
  5. **Maturity Censoring:** Never include users who entered Step 1 inside the last `conversion_window` (e.g., today's signups in a 7-day onboarding funnel) — right-censored cohorts artificially depress conversion!
- **Timestamp Ordering Resilience:** On high-speed client+server flows, Step 2 (server event) can arrive 50ms before Step 1 (buffered client event) due to minor clock skew. Understand when to apply a tiny sequence tolerance or unify step timestamps on the server.
- **Simpson's Paradox Guard:** Aggregate conversion can fall even while conversion **rises** in every single segment (e.g., if low-converting mobile traffic surged from 30% to 70% of total traffic). Always decompose funnel shifts into **Within-Segment Rate Change** vs **Mix Shift** (device, channel, new vs returning, geo).

## 4. Architecture & Implementation
```sql
-- Right-censored, strict-ordered, hold-constant (session_id) 3-step checkout funnel with 2-hour window
WITH params AS (
  SELECT
    NOW() - INTERVAL '30 days' AS start_ts,
    NOW() - INTERVAL '2 hours' AS cutoff_entry_ts -- Exclude immature cohorts still inside 2h window
),
step1 AS (
  SELECT
    canonical_user_id,
    session_id,
    MIN(event_ts) AS s1_ts
  FROM fct_user_events, params
  WHERE event_name = 'Checkout_Started'
    AND event_ts >= params.start_ts
    AND event_ts <= params.cutoff_entry_ts
  GROUP BY 1, 2
),
step2 AS (
  SELECT
    s1.canonical_user_id,
    s1.session_id,
    s1.s1_ts,
    MIN(e.event_ts) AS s2_ts
  FROM step1 s1
  LEFT JOIN fct_user_events e
    ON e.canonical_user_id = s1.canonical_user_id
   AND e.session_id = s1.session_id
   AND e.event_name = 'Payment_Method_Selected'
   AND e.event_ts >= s1.s1_ts
   AND e.event_ts <= s1.s1_ts + INTERVAL '2 hours'
  GROUP BY 1, 2, 3
),
step3 AS (
  SELECT
    s2.canonical_user_id,
    s2.session_id,
    s2.s1_ts,
    s2.s2_ts,
    MIN(e.event_ts) AS s3_ts
  FROM step2 s2
  LEFT JOIN fct_user_events e
    ON e.canonical_user_id = s2.canonical_user_id
   AND e.session_id = s2.session_id
   AND e.event_name = 'Order_Completed'
   AND s2.s2_ts IS NOT NULL
   AND e.event_ts >= s2.s2_ts
   AND e.event_ts <= s2.s1_ts + INTERVAL '2 hours'
  GROUP BY 1, 2, 3, 4
)
SELECT
  COUNT(*) AS step1_checkout_started,
  COUNT(s2_ts) AS step2_payment_selected,
  COUNT(s3_ts) AS step3_order_completed,
  ROUND(100.0 * COUNT(s2_ts) / NULLIF(COUNT(*), 0), 2) AS s1_to_s2_pct,
  ROUND(100.0 * COUNT(s3_ts) / NULLIF(COUNT(s2_ts), 0), 2) AS s2_to_s3_pct,
  ROUND(100.0 * COUNT(s3_ts) / NULLIF(COUNT(*), 0), 2) AS overall_conv_pct,
  PERCENTILE_CONT(0.50) WITHIN GROUP (ORDER BY EXTRACT(EPOCH FROM (s3_ts - s1_ts))) FILTER (WHERE s3_ts IS NOT NULL) AS median_time_to_convert_sec
FROM step3;
```

## 5. Platform / Vendor Variations
| Tool | Default Funnel Mode | Watch-Out |
| --- | --- | --- |
| **PostHog Funnels** | Sequential ordered, 14-day default window, unique users | Explicitly toggle `Hold property constant` (e.g., `order_id`) and check window length |
| **Mixpanel Funnels** | Sequential ordered, 30-day default window | Supports Exclusion Steps (`did NOT see Payment_Error between Step 2 and Step 3`) — very useful for root-cause sizing |
| **GA4 Funnel Exploration** | Closed vs Open funnel toggle | Open funnel lets users enter at Step 2, which breaks classic step-over-step conversion ratios unless explained |
| **Warehouse SQL (ClickHouse/BigQuery)** | ClickHouse `windowFunnel(7200)(event_ts, ...)` native function | Fastest on billions of rows; still enforce right-censoring cutoff on entry cohort |

## 6. Decision Matrix & Trade-Offs
| Funnel Type | Best Question Answered | Trap to Avoid |
| --- | --- | --- |
| **Strict Ordered (Closed)** | "Of users who start checkout, where do they drop off step-by-step?" | Missing alternative paths (e.g., Apple Pay Express bypasses Step 2) |
| **Unordered Within Window** | "Did a new user complete all 3 setup tasks in their first 7 days?" | Hides sequence friction when order matters |
| **Time-to-Convert Distribution** | "How long do users stall on KYC/payment verification?" | Using mean instead of median/p90 (outliers distort mean) |

## 7. Real Production Scenario
Leadership panics because overall `Signup -> Paid` conversion fell from `8.4%` to `6.9%` week-over-week. Instead of blaming the checkout UI, the analyst runs a Mix-Shift vs Rate-Change decomposition: Web conversion actually **improved** (`11.2% -> 11.8%`) and Mobile App conversion **improved** (`4.5% -> 4.9%`), but a viral TikTok campaign tripled low-intent mobile traffic share from `35%` to `72%` (**Simpson's Paradox**). Showing the segmented funnel + contribution waterfall prevents an unnecessary checkout rollback.

## 8. Failure Modes & Edge Cases
- **WRONG:** Computing funnel steps as independent `COUNT(DISTINCT user_id)` ratios (`Total Orders / Total Checkouts` in last 7 days) without tying users or enforcing ordering (`Order` could belong to a user who started checkout 8 days ago!).
- **RIGHT:** Join per actor (and optional hold-constant entity ID) enforcing `s1_ts <= s2_ts <= s3_ts <= s1_ts + window` and excluding right-censored cohorts.
- **WRONG:** Forgetting express shortcuts (e.g., "Buy Now" skips `Cart_Viewed`), causing Step 2 to look artificially catastrophic while Step 3 is higher than Step 2 in open queries.
- **RIGHT:** Model distinct funnel variants per entry path (`Standard Cart` vs `Express Buy Now`) or group equivalent step actions.

## 9. Testing & Verification
- Unit-test funnel SQL with 4 edge-case fixtures: (1) valid `A -> B -> C` inside window (counts all 3), (2) out-of-order `B -> A -> C` (counts Step 1 only in strict ordered), (3) `A -> B -> C` where `C` is outside window (counts Steps 1–2 only), (4) entry within right-censoring cutoff (excluded from denominator).
- Cross-check Step 3 completed orders against `fct_orders` to confirm no silent event loss.

## 10. Operational Considerations
- Pair every drop-off step with a **Breakdown by Top Exit Event / Error Code** (`Payment_Failed.error_code`, `Validation_Error.field`) so the funnel points directly to an actionable engineering fix.
- Re-evaluate conversion windows annually as user behavior changes (e.g., introducing "Save Cart" extends checkout latency).

## 11. Authoritative References
- PostHog Documentation — *Funnels Methodology & Conversion Windows* (`https://posthog.com/docs/product-analytics/funnels`).
- ClickHouse Documentation — *`windowFunnel` Aggregate Function* (`https://clickhouse.com/docs/en/sql-reference/aggregate-functions/parametric-functions#windowfunnel`).
- Pearl, J. — *Understanding Simpson's Paradox* (American Statistician, 2014).

## 12. Limitations & When NOT to Use
- Funnels only measure linear/staged progression; they are poorly suited for cyclical, non-linear workflows (e.g., collaborative document editing or social feeds) — use retention (`09`) and journey/path analysis (`10`) instead.
- Never claim a funnel correlation ("users who use feature X convert at 40%") proves causality (selection bias: high-intent users naturally use feature X); validate with experiments (`11–13`) or causal methods (`14`).
