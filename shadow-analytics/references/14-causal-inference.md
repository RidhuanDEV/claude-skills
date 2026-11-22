# 14. Causal Inference

## 1. Purpose & Activation Conditions
Estimate credible causal impact when randomized A/B experiments are impossible, unethical, illegal, or already shipped to 100% of users — using **Difference-in-Differences (DiD)**, **Propensity Score Matching / IPW**, **Synthetic Control**, and **Regression Discontinuity Design (RDD)**, with mandatory assumption checks and honest caveats. Load when evaluating market-wide launches, regulatory changes, TV/brand campaigns, B2B opt-in features, or retroactive launches.

## 2. Prerequisites
- Historical pre-treatment panel data (`>= 4–8` pre-periods for DiD/Synthetic Control) and clean non-leaking covariates (`06-analytics-data-architecture.md`).

## 3. Technical Principles & Constraints
- **Correlation Is NOT Causation (Selection Bias Rule):** Comparing users who *chose* to adopt a feature vs users who didn't (or simply comparing *After* vs *Before* a launch) confounds true causal lift with **Self-Selection** (power users adopt new features first) and **Secular Trends / Seasonality** (holidays, macro shifts, marketing campaigns).
- **Four Core Quasi-Experimental Designs & Their Identifying Assumptions:**
  1. **Difference-in-Differences (DiD):** Compares change `(Post - Pre)` in a Treated group (e.g., Jakarta rollout) against `(Post - Pre)` in an Untreated control group (e.g., Surabaya + Bandung).
     $$\hat{\tau}_{\text{DiD}} = (\bar{Y}_{\text{T,post}} - \bar{Y}_{\text{T,pre}}) - (\bar{Y}_{\text{C,post}} - \bar{Y}_{\text{C,pre}})$$
     **Critical Assumption — Parallel Trends:** Absent treatment, Treated and Control would have evolved along parallel trajectories. **MUST test pre-treatment parallel trends (event-study plot) AND run placebo-date tests!** When rollouts are staggered across time, avoid naive Two-Way Fixed Effects (TWFE) with heterogeneous effects; use modern staggered estimators (**Callaway & Sant'Anna** or **Sun & Abraham**).
  2. **Synthetic Control Method (SCM):** When only 1 treated unit exists (e.g., 1 country or 1 flagship city) and no single control city matches it, construct a convex weighted combination of donor cities matching pre-treatment outcomes and covariates tightly; evaluate inference via **in-space placebo permutation tests**.
  3. **Propensity Score Matching (PSM) / Inverse Probability Weighting (IPW) / Doubly Robust (AIPW):** Re-weights or matches treated and untreated observational units on rich **pre-treatment** covariates $X$ (`P(T=1 | X)`). **Critical Assumptions:** Conditional Ignorability (no unobserved confounders!) + Positivity/Overlap (`0 < e(X) < 1`). MUST report post-weighting **Standardized Mean Difference (`SMD < 0.10`)** covariate balance table!
  4. **Regression Discontinuity Design (RDD):** Exploits a sharp eligibility cutoff (e.g., free shipping for carts `>= Rp 100.000`, loyalty tier at `>= 1,000 points`) by comparing units just above vs just below the threshold. **Critical Assumption:** Zero gaming/manipulation of the running variable around the cutoff (check McCrary density test).
- **Honest Non-Causal Caveats:** If parallel pre-trends fail, covariate overlap collapses, or unobserved confounding is severe (e.g., viral press coverage hit ONLY the treated city on launch day), explicitly state: *"Causal identification assumptions are violated; this estimate is descriptive/associational, not proven causal impact."*

## 4. Architecture & Implementation
```sql
-- Difference-in-Differences (DiD) Pre-Trend Check + 2x2 Estimate (City Rollout Example)
WITH panel AS (
  SELECT
    city_id,
    CASE WHEN city_id = 'jakarta' THEN 1 ELSE 0 END AS is_treated,
    week_start,
    CASE WHEN week_start >= DATE '2026-10-05' THEN 1 ELSE 0 END AS is_post,
    SUM(completed_orders)::double precision / NULLIF(COUNT(DISTINCT active_user_id), 0) AS orders_per_user
  FROM fct_city_weekly_kpis
  WHERE city_id IN ('jakarta', 'surabaya', 'bandung', 'medan')
    AND week_start BETWEEN DATE '2026-08-10' AND DATE '2026-11-16'
  GROUP BY 1, 2, 3, 4
),
cell_means AS (
  SELECT
    is_treated,
    is_post,
    AVG(orders_per_user) AS mean_y
  FROM panel
  GROUP BY 1, 2
)
SELECT
  MAX(CASE WHEN is_treated = 1 AND is_post = 1 THEN mean_y END) -
  MAX(CASE WHEN is_treated = 1 AND is_post = 0 THEN mean_y END) AS treated_delta,
  MAX(CASE WHEN is_treated = 0 AND is_post = 1 THEN mean_y END) -
  MAX(CASE WHEN is_treated = 0 AND is_post = 0 THEN mean_y END) AS control_delta,
  (
    (MAX(CASE WHEN is_treated = 1 AND is_post = 1 THEN mean_y END) - MAX(CASE WHEN is_treated = 1 AND is_post = 0 THEN mean_y END))
    -
    (MAX(CASE WHEN is_treated = 0 AND is_post = 1 THEN mean_y END) - MAX(CASE WHEN is_treated = 0 AND is_post = 0 THEN mean_y END))
  ) AS did_estimate
FROM cell_means;
-- Note: Compute standard errors clustered at city_id (or Wild Cluster Bootstrap / Placebo inference when clusters < 30)!
```

## 5. Platform / Vendor Variations
| Python / R Ecosystem | Recommended Library | Use Case |
| --- | --- | --- |
| **Python** | `pyfixest` / `linearmodels` / `statsmodels` | DiD, Event-Study plots, Cluster-Robust SE, Callaway-Sant'Anna |
| **Python** | `CausalPy` / `tfp-causalimpact` / `SparseSC` | Bayesian Structural Time Series (CausalImpact) & Synthetic Control |
| **Python / Microsoft** | `DoWhy` / `EconML` | Explicit Causal DAGs, IPW/Doubly Robust AIPW, sensitivity refuters |
| **R** | `fixest`, `did`, `Synth`, `rdrobust`, `MatchIt` | Gold-standard econometric implementations (especially `did` & `rdrobust`) |

## 6. Decision Matrix & Trade-Offs
| Real-World Situation | Best Quasi-Experimental Method | Must-Pass Validation Check |
| --- | --- | --- |
| **Phased Regional / City Launch** | **DiD** (or **Synthetic Control** if 1 treated geo) | Parallel pre-trends (`p > 0.10` on pre-period leads) + placebo date test |
| **Threshold / Tier Eligibility Rule** | **Regression Discontinuity (RDD)** | Zero bunching/manipulation around cutoff + bandwidth sensitivity check |
| **Voluntary Feature Opt-In (No RCT)** | **Doubly Robust (AIPW) / PSM + DiD** | Post-weighting `SMD < 0.10` on all pre-period covariates + Rosenbaum sensitivity |
| **100% Global Launch (No Control Group)** | Interrupted Time Series / CausalImpact (using unaffected proxy series) | **Lowest causal strength** — must explicitly warn of concurrent confounders |

## 7. Real Production Scenario
Due to an OJK / local regulatory mandate, a fintech company must roll out a new KYC verification flow in Jakarta on Oct 5 while deferring other provinces until Dec 1. Leadership asks for the causal impact on 7-day activation. A naive Before-vs-After comparison in Jakarta shows `-9%` activation — but an analyst applies **Difference-in-Differences** against Surabaya, Bandung, and Medan (after verifying flat parallel pre-trends over the prior 8 weeks and passing a Sep 7 placebo date test with `-0.3%` null effect). Control cities also dropped `-5%` due to a seasonal pay-cycle trough, revealing the true causal impact of the KYC friction is **`-4.0%` (95% CI: `-6.2%` to `-1.8%`)**, preventing mis-sizing the engineering fix.

## 8. Failure Modes & Edge Cases
- **WRONG:** Reporting a simple `"Before vs After"` percentage change (or `"Feature Users vs Non-Users"` comparison) as `"Feature X caused +35% retention"`.
- **RIGHT:** Draw the causal DAG, identify confounders/selection bias, apply DiD/SCM/RDD/AIPW with explicit falsification checks, and report confidence bounds + remaining threats to validity.
- **WRONG:** Including **post-treatment** variables (mediators/colliders) in a Propensity Score or DiD regression (introduces post-treatment/collider bias that can even flip the sign of the estimate!).
- **RIGHT:** Condition strictly on **pre-treatment** covariates measured prior to intervention.

## 9. Testing & Verification
- **Mandatory 3-Check Falsification Suite** for every quasi-experiment:
  1. **Pre-Trends / Event-Study Check:** Verify treated vs control differences in `t = -4, -3, -2, -1` hover around `0`.
  2. **Placebo-in-Time Test:** Re-run estimator pretending the launch occurred 4 weeks earlier inside the pre-period -> MUST yield null (`~0`).
  3. **Negative-Control Outcome Test:** Run the same estimator on an outcome the feature could NOT plausibly affect (e.g., legacy desktop invoices during a mobile-only rollout) -> MUST yield null.

## 10. Operational Considerations
- Whenever a non-randomized phased rollout is unavoidable (regulatory, B2B enterprise, brand marketing), involve Product Analytics **before** rollout starts to select matched control regions or staggered rollout waves that dramatically strengthen causal identification.
- Keep causal analysis notebooks reproducible in git with frozen dataset snapshots and explicit assumption audit tables.

## 11. Authoritative References
- Scott Cunningham — *Causal Inference: The Mixtape* (`https://mixtape.scunning.com/`).
- Nick Huntington-Klein — *The Effect: An Introduction to Research Design and Causality* (`https://theeffectbook.net/`).
- Brantly Callaway & Pedro H. C. Sant'Anna — *Difference-in-Differences with Multiple Time Periods* (Journal of Econometrics, 2021).
- Alberto Abadie — *Using Synthetic Controls: Feasibility, Data Requirements, and Methodological Aspects* (Journal of Economic Literature, 2021).

## 12. Limitations & When NOT to Use
- Quasi-experiments NEVER fully match the internal validity of a clean randomized controlled trial (RCT); whenever an A/B test is feasible and ethical, prefer randomization (`11–13`).
- Do NOT use observational PSM/IPW when the primary driver of adoption is an **unobserved variable** (e.g., private sales outreach or sudden user intent spike) with no reliable pre-period proxy — matching on weak demographics gives false mathematical precision to a biased answer.
