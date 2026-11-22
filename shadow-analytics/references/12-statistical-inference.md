# 12. Statistical Inference

## 1. Purpose & Activation Conditions
Select and execute the mathematically correct statistical estimator for every metric type (proportions, continuous skewed metrics, ratio metrics via **Delta Method**, cluster metrics), compute realistic power/MDE, apply **valid CUPED** variance reduction without post-assignment leakage, and control multiple-testing error rates (`FWER` vs `FDR`). Load when sizing or analyzing any A/B/n experiment.

## 2. Prerequisites
- Clean SRM check (`srm_p >= 0.001`) and proper Assignment/Exposure separation (`11-experiment-design-and-randomization.md`).

## 3. Technical Principles & Constraints
- **Z-Test & Bonferroni Are NOT Universal — Match the Estimator to the Metric Structure:**
  1. **User-Level Binary Conversion (`converted in {0, 1}`):** Two-proportion Z-test (or Fisher's exact for small counts).
  2. **User-Level Continuous / Skewed Metric (Revenue per User, Latency, Session Count):** **Welch's t-test** (unequal variances; robust via CLT for large $N$; pair with pre-registered 99th-percentile winsorization or Mann-Whitney U / quantile bootstrap if extreme whales dominate).
  3. **Ratio Metrics Where Analysis Unit != Randomization Unit (e.g., CTR = `clicks / impressions`, Revenue per Session = `revenue / sessions` under user randomization):** Observations within the same user are correlated — naive event-level Z-tests severely underestimate standard error and inflate false positives! MUST use the **Delta Method** (or **User-Level Cluster Bootstrap**):
     $$\operatorname{Var}\!\left(\frac{\bar{Y}}{\bar{X}}\right) \approx \frac{1}{n\,\mu_X^2}\left(\sigma_Y^2 - 2\frac{\mu_Y}{\mu_X}\operatorname{Cov}(X,Y) + \frac{\mu_Y^2}{\mu_X^2}\sigma_X^2\right)$$
     where $(Y_i, X_i)$ are aggregated **per randomization unit $i$** (e.g., total clicks and total impressions for user $i$).
  4. **Cluster-Randomized Experiments (Workspace / Geo / Store):** Compute **Cluster-Robust Standard Errors** (Liang-Zeger / CR2) or aggregate to cluster-level means (`13-advanced-experimentation.md`).
- **Valid CUPED (Controlled-Experiment Using Pre-Experiment Data — Deng et al., WSDM 2013):**
  $$Y_i^{\text{CUPED}} = Y_i - \theta (X_i - \bar{X}), \qquad \theta = \frac{\widehat{\operatorname{Cov}}(Y, X)}{\widehat{\operatorname{Var}}(X)}, \qquad \operatorname{Var}(Y^{\text{CUPED}}) = \operatorname{Var}(Y)(1 - \rho_{X,Y}^2)$$
  **NON-NEGOTIABLE VALIDITY RULE:** The covariate $X_i$ **MUST be measured strictly BEFORE randomization** and be **100% independent of treatment assignment** (e.g., user's 14-day pre-experiment spend or session count; for brand-new users with no history, impute with cohort mean $\bar{X}$ + missingness indicator computed globally, never per-variant). Using an **in-experiment** covariate affected by treatment biases the Average Treatment Effect (ATE) and invalidates inference!
- **Multiple Testing Control (`FWER` vs `FDR`):**
  - **1 Pre-Registered Primary OEC (2 variants):** No adjustment required ($\alpha = 0.05$).
  - **Multi-Arm A/B/C/D or Multiple Primary Decision Metrics (Strict Ship Gate):** Control Family-Wise Error Rate (**Holm-Bonferroni** — uniformly more powerful than raw Bonferroni, or **Dunnett's test** against shared control).
  - **Exploratory Analysis Across 20+ Diagnostic Metrics / Segments:** Control False Discovery Rate via **Benjamini-Hochberg (BH)** — avoids crushing statistical power while bounding expected proportion of false discoveries.
- **Confidence Intervals > Bare p-Values:** Always report Point Estimate + **95% Confidence Interval** (both absolute and relative) + p-value + sample size + MDE. A statistically significant `+0.05%` lift (`p = 0.01`) can still be **practically insignificant** if engineering maintenance costs exceed the value!

## 4. Architecture & Implementation
```typescript
export interface RatioUnitSummary {
  readonly nUsers: number;
  readonly meanNumerator: number;
  readonly meanDenominator: number;
  readonly varNumerator: number;
  readonly varDenominator: number;
  readonly covNumDen: number;
}

export interface RatioComparisonResult {
  readonly controlRatio: number;
  readonly treatmentRatio: number;
  readonly absoluteLift: number;
  readonly relativeLift: number;
  readonly standardError: number;
  readonly zScore: number;
  readonly ci95Low: number;
  readonly ci95High: number;
}

// Delta Method variance for ratio metrics aggregated at the randomization-unit (user) level
export function compareRatioMetricsDeltaMethod(
  control: RatioUnitSummary,
  treatment: RatioUnitSummary
): RatioComparisonResult {
  const ratioAndVar = (s: RatioUnitSummary): { readonly r: number; readonly v: number } => {
    const r = s.meanNumerator / s.meanDenominator;
    const v =
      (s.varNumerator - 2 * r * s.covNumDen + r * r * s.varDenominator) /
      (s.nUsers * s.meanDenominator * s.meanDenominator);
    return { r, v: Math.max(0, v) };
  };

  const c = ratioAndVar(control);
  const t = ratioAndVar(treatment);
  const diff = t.r - c.r;
  const se = Math.sqrt(c.v + t.v);
  const z = se > 0 ? diff / se : 0;
  const z95 = 1.959963984540054;
  return {
    controlRatio: c.r,
    treatmentRatio: t.r,
    absoluteLift: diff,
    relativeLift: c.r !== 0 ? diff / c.r : 0,
    standardError: se,
    zScore: z,
    ci95Low: diff - z95 * se,
    ci95High: diff + z95 * se,
  };
}
```
Warehouse SQL for user-level pre-experiment CUPED adjustment:
```sql
-- Compute strictly pre-experiment covariate X (14 days BEFORE assignment_ts) and post-assignment outcome Y
WITH base AS (
  SELECT
    a.variant_name,
    a.user_id,
    COALESCE(pre.orders_14d_pre, 0) AS x_pre,
    COALESCE(post.orders_14d_post, 0) AS y_post
  FROM fct_experiment_assignments a
  LEFT JOIN fct_user_pre_experiment_14d pre ON pre.user_id = a.user_id AND pre.experiment_key = a.experiment_key
  LEFT JOIN fct_user_post_experiment_14d post ON post.user_id = a.user_id AND post.experiment_key = a.experiment_key
  WHERE a.experiment_key = 'checkout_v2'
),
theta_calc AS (
  SELECT
    COVAR_SAMP(y_post, x_pre) / NULLIF(VAR_SAMP(x_pre), 0) AS theta,
    AVG(x_pre) AS x_mean
  FROM base
)
SELECT
  b.variant_name,
  COUNT(*) AS n_users,
  AVG(b.y_post) AS raw_mean,
  AVG(b.y_post - COALESCE(t.theta, 0) * (b.x_pre - t.x_mean)) AS cuped_mean,
  VAR_SAMP(b.y_post) AS raw_var,
  VAR_SAMP(b.y_post - COALESCE(t.theta, 0) * (b.x_pre - t.x_mean)) AS cuped_var
FROM base b
CROSS JOIN theta_calc t
GROUP BY 1;
```

## 5. Platform / Vendor Variations
| Platform | Ratio Metric Handling | CUPED / Variance Reduction |
| --- | --- | --- |
| **Statsig / Eppo / GrowthBook** | Native Delta Method for ratio metrics | Built-in pre-experiment CUPED (with automatic fallback for new users) |
| **PostHog Experiments** | Bayesian & Frequentist engines (check ratio vs user-level metric definition carefully) | Supports CUPED/covariates on warehouse-linked metrics; verify pre-experiment window |
| **Custom Python / SQL (`scipy`/`statsmodels`)** | Implement `compareRatioMetricsDeltaMethod` or user-level bootstrap (`B >= 2000`) | Explicit SQL join strictly `< assignment_ts` |

## 6. Decision Matrix & Trade-Offs (Estimator Selection Matrix)
| Metric Type | Randomization Unit | Correct Estimator | Why Naive Z-Test Fails |
| --- | --- | --- | --- |
| **User Conversion (`0/1`)** | User | Two-Proportion Z-test (or CUPED Welch t-test) | Valid here! |
| **Revenue / Spend per User** | User | Welch's t-test + CUPED (optional pre-registered 99% cap) | Z-test for proportions doesn't apply to continuous skewed data |
| **CTR (`clicks / impressions`), Rev/Session** | User | **Delta Method** or User-Level Bootstrap | Naive event-level Z-test ignores intra-user correlation -> false positives `2x–5x` too high |
| **Workspace / Geo KPI** | Workspace / Geo | Cluster-Robust SE (`CR2`) or Cluster-Level t-test | User-level SE pretends correlated cluster members are independent |
| **Multi-Arm (4 variants) or 15 Segments** | User | **Holm-Bonferroni** (ship decisions) / **Benjamini-Hochberg FDR** (exploration) | Unadjusted $\alpha = 0.05$ across 15 tests gives `54%` chance of >= 1 false positive |

## 7. Real Production Scenario
A search team runs a user-randomized experiment testing a new autocomplete UI and evaluates `CTR = total_clicks / total_queries` using a naive two-proportion Z-test over `1,200,000` queries. It reports `p = 0.008` ("ship it!"). When re-analyzed with the **Delta Method** aggregated at the `user_id` level (`85,000` users, where power users fire 60 queries each), the true standard error is `2.3x` larger and `p = 0.19` (noise!). Using the right ratio estimator prevents shipping a zero-value complexity increase.

## 8. Failure Modes & Edge Cases
- **WRONG:** Using `in_experiment_sessions` or `post_assignment_pageviews` as a CUPED covariate because it correlates strongly with revenue.
- **RIGHT:** Strictly forbid ANY post-assignment variable in CUPED; compute `X_i` exclusively from timestamps `< assignment_ts`.
- **WRONG:** Computing `theta` separately for Control and Treatment (leaks treatment noise into variance adjustment and introduces finite-sample bias).
- **RIGHT:** Estimate a single pooled `theta` across combined groups (or cross-fit/OLS with centered covariate interaction, Lin 2013).

## 9. Testing & Verification
- Verify ratio metrics, power/MDE, and CUPED pre-experiment validity via `python shadow-analytics/scripts/analytics_experiment_verifier.py --check-experiment <exp.json>`.
- Run Monte Carlo A/A simulation (1,000 simulated null splits on historical skewed user data) to verify your chosen estimator keeps empirical Type-I error near `5%` (not `18%`).

## 10. Operational Considerations
- Calculate required sample size and runtime (`required_n / daily_eligible_users`) BEFORE launch — if detecting a realistic `2%` relative lift requires 9 months of traffic, don't run an underpowered 2-week fixed-horizon test hoping for luck!
- Keep `mde_relative` grounded in business ROI (the smallest lift worth the ongoing maintenance cost).

## 11. Authoritative References
- Alex Deng, Ya Xu, Ron Kohavi & Toby Walker — *Improving the Sensitivity of Online Controlled Experiments by Utilizing Pre-Experiment Data* (WSDM 2013 — CUPED).
- Alex Deng, Ulf Knoblich & Jiannan Lu — *Applying the Delta Method in Metric Analytics: A Practical Guide with Novel Ideas* (KDD 2018).
- Winston Lin — *Agnostic Notes on Regression Adjustments to Experimental Data* (Annals of Applied Statistics, 2013).
- Benjamini & Hochberg (1995) — *Controlling the False Discovery Rate* (JRSS-B).

## 12. Limitations & When NOT to Use
- Fixed-horizon Z/t-tests assume a **single pre-committed sample size** — if stakeholders will peek daily and stop early, switch to **Sequential Testing (`mSPRT` / Group Sequential)** (`13-advanced-experimentation.md`).
- CUPED yields minimal variance reduction (`1 - rho^2`) for brand-new users with zero pre-experiment history; for new-user onboarding tests, rely on stratification or pre-trigger covariates (e.g., landing channel, device class) rather than expecting 50% CUPED gains.
