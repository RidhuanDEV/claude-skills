# 13. Advanced Experimentation

## 1. Purpose & Activation Conditions
Handle real-world experimentation settings where standard fixed-horizon user-level A/B testing breaks down: continuous peeking (**mSPRT Always-Valid Inference** & **Group Sequential Testing**), **Cluster Randomization**, and **Marketplace / Network Interference (SUTVA violations)** via **Switchback** and **Geo-Cluster** designs. Load when stakeholders demand early stopping, or when testing pricing, ranking, logistics, social, or B2B collaboration features.

## 2. Prerequisites
- Mastery of core randomization (`11-experiment-design-and-randomization.md`) and statistical inference (`12-statistical-inference.md`).

## 3. Technical Principles & Constraints
- **The Peeking Problem:** Checking a fixed-horizon p-value daily for 14 days and stopping the first time $p < 0.05$ inflates the true false-positive rate from `5%` to **`20%–30%+`**. Solve it with one of two rigorous sequential frameworks (pre-registered BEFORE launch):
  1. **mSPRT (Mixture Sequential Probability Ratio Test — Johari, Pekelis & Walsh 2017/2022):** Produces **Always-Valid p-values** and **Always-Valid Confidence Sequences** that hold Type-I error `<= alpha` at **every** sample size $n = 1, 2, \dots, \infty$, allowing continuous real-time monitoring and immediate stopping for safety/guardrail regressions or huge wins. Trade-off: requires ~15%–25% more samples than fixed-horizon at the exact same MDE when the true effect is small.
  2. **Group Sequential Testing (GST — O'Brien-Fleming / Lan-DeMets Alpha Spending):** Defines a fixed schedule of interim looks (e.g., 25%, 50%, 75%, 100% of planned $N$). O'Brien-Fleming spends tiny alpha early (`p < 0.0005` at 25% look) and preserves nearly full power (`p < 0.044`) at the final look — minimal sample penalty (`~2%–4%`) while allowing early exit on huge effects or clear futility!
- **SUTVA (Stable Unit Treatment Value Assumption) & Network Interference:** Standard A/B testing assumes User A's treatment does not affect User B's outcome. This **fails catastrophically** in:
  - **Two-Sided Marketplaces / Capacity-Constrained Supply** (ride-hailing, food delivery, hotel inventory, ad auctions): Giving Treatment buyers a promo consumes scarce drivers/inventory, starving Control buyers and **double-counting the apparent lift** (cannibalization!).
  - **Social / Collaborative Networks** (chat, viral invites, shared B2B workspaces): Treatment features spill over directly onto Control teammates.
- **Interference-Resilient Designs:**
  - **Cluster Randomization (Geo / City / Workspace / Graph Clusters):** Randomize entire clusters (minimizing cross-cluster edges) and analyze with cluster-level or cluster-robust (`CR2`) inference. Notice effective sample size scales with **number of clusters $K$**, not total users — account for Intra-Cluster Correlation (ICC, $\rho_{\text{ICC}}$) via Design Effect $\text{DEFF} = 1 + (m - 1)\rho_{\text{ICC}}$.
  - **Time-Based Switchback Designs:** For single-market / single-city logistics, pricing, or matching algorithms, alternate the ENTIRE market between Control and Treatment across randomized time blocks (e.g., 2-hour or 1-day windows), inserting a **burn-in / washout buffer** at block boundaries to eliminate carryover bias!

## 4. Architecture & Implementation
```typescript
// Always-Valid mSPRT (Mixture Sequential Probability Ratio Test) for normal/difference-in-means summary
// Reference: Johari, Koomen, Pekelis & Walsh (Operations Research, 2022)
export interface MsprtInput {
  readonly nControl: number;
  readonly nTreatment: number;
  readonly meanControl: number;
  readonly meanTreatment: number;
  readonly varControl: number;
  readonly varTreatment: number;
  readonly tauSquared: number; // Mixing variance prior (calibrated to expected effect scale)
  readonly alpha?: number;
}

export interface MsprtResult {
  readonly likelihoodRatioLambda: number;
  readonly alwaysValidPValue: number;
  readonly canStopRejectNull: boolean;
}

export function evaluateMsprt(input: MsprtInput): MsprtResult {
  const alpha = input.alpha ?? 0.05;
  const v = input.varControl / input.nControl + input.varTreatment / input.nTreatment;
  if (v <= 0 || input.tauSquared <= 0) {
    throw new Error('Variance v and mixing prior tauSquared must be strictly positive');
  }
  const diff = input.meanTreatment - input.meanControl;
  const ratio = v / (v + input.tauSquared);
  const exponent = (diff * diff * input.tauSquared) / (2 * v * (v + input.tauSquared));
  const lambda = Math.sqrt(ratio) * Math.exp(exponent);
  const alwaysValidP = Math.min(1, 1 / Math.max(lambda, 1));
  return {
    likelihoodRatioLambda: lambda,
    alwaysValidPValue: alwaysValidP,
    canStopRejectNull: alwaysValidP < alpha,
  };
}
```
Switchback experiment design with washout exclusion in SQL:
```sql
-- Switchback analysis excluding first 15 minutes of each 2-hour block as carryover washout buffer
WITH blocks AS (
  SELECT
    block_id,
    city_id,
    variant_name,
    block_start_ts,
    block_end_ts
  FROM dim_switchback_schedule
  WHERE experiment_key = 'dispatch_algo_v4'
)
SELECT
  b.block_id,
  b.city_id,
  b.variant_name,
  COUNT(o.order_id) AS completed_orders,
  AVG(o.eta_seconds) AS mean_eta_sec
FROM blocks b
JOIN fct_dispatch_orders o
  ON o.city_id = b.city_id
 AND o.created_at >= b.block_start_ts + INTERVAL '15 minutes' -- Washout buffer removes boundary carryover
 AND o.created_at < b.block_end_ts
GROUP BY 1, 2, 3;
-- Next step: compute cluster-robust / randomization-inference p-value across (block_id, city_id) units!
```

## 5. Platform / Vendor Variations
| Platform / Method | Sequential Support | Interference / Switchback Support |
| --- | --- | --- |
| **Statsig / Optimizely / GrowthBook** | Native Sequential Testing (mSPRT or Group Sequential) | Supports cluster/org ID randomization; switchbacks typically orchestrated via server config + warehouse analysis |
| **DoorDash / Uber / Lyft Pattern** | Group Sequential + Randomization Inference (Permutation Tests) | Standard **Switchback** with washout buffers + regression adjustment for hour-of-day/city fixed effects |
| **Bayesian A/B (PostHog / Eppo)** | Outputs Probability to Beat Control + Expected Loss (still requires sensible prior & minimum horizon to avoid early noise traps!) | Standard user/group units |

## 6. Decision Matrix & Trade-Offs
| Challenge | Recommended Design | Primary Trade-Off |
| --- | --- | --- |
| **Stakeholders monitor dashboard daily** | **Group Sequential (O'Brien-Fleming)** or **mSPRT** | Slightly wider confidence intervals / larger $N$ than fixed horizon |
| **B2B Workspace / Team Feature** | **Cluster Randomization (`workspace_id`)** + Cluster-Robust SE | Lower statistical power when a few giant workspaces dominate (stratify by workspace size!) |
| **Shared-Supply Marketplace (Dispatch/Pricing)** | **Time Switchback** (or **Geo-Cluster** across cities) | Requires washout buffer & careful choice of block duration (`>=` order lifecycle length) |
| **Social / Viral Graph Feature** | **Graph-Cluster Randomization** (e.g., ego-clusters / community detection) | Residual cross-cluster leakage attenuates observed effect slightly |

## 7. Real Production Scenario
A food-delivery marketplace tests a new courier matching algorithm via 50/50 user-level randomization. Treatment users get priority assignment to the nearest idle driver, slashing Treatment ETA by `-2.1 minutes` (`p < 0.0001`). However, when shipped to 100% of users, city-wide ETA barely moves (`-0.1 minutes`) because Treatment had merely stolen nearby couriers away from Control orders (classic SUTVA cannibalization!). Re-running as a **2-hour city-level Switchback** with 20-minute washout buffers and randomization inference measures the true marketplace-wide net impact accurately.

## 8. Failure Modes & Edge Cases
- **WRONG:** Stopping a sequential test on Day 2 (`alwaysValidP = 0.03`) before completing a full 7-day cycle — sequential math controls *statistical peeking*, NOT *day-of-week seasonality* or *short-term novelty effects*!
- **RIGHT:** Enforce BOTH valid sequential boundaries AND a minimum calendar duration (typically `>= 7 days`) for non-safety ship decisions (immediate early stop is ALWAYS allowed for severe safety/guardrail regressions!).
- **WRONG:** Running a cluster-randomized test on 12 cities (`6 Control vs 6 Treatment`) and calculating a user-level Z-test over 500,000 users (produces bogus `p < 1e-12` purely from 1 city's local weather/holiday).
- **RIGHT:** Analyze at the cluster level (`N = 12` clusters) using paired/stratified cluster t-test, DiD/CUPED pre-period adjustment, or exact permutation/randomization inference.

## 9. Testing & Verification
- Simulate null data with repeated daily checks: confirm fixed-horizon peeking produces `~22%` false positives while `evaluateMsprt` holds empirical false positives `<= 5%`.
- In switchback designs, verify autocorrelation across consecutive blocks and test sensitivity to washout duration (`10m` vs `20m` vs `30m`).

## 10. Operational Considerations
- For cluster randomization with heterogeneous cluster sizes (e.g., enterprise workspaces with 500 seats vs SMBs with 3 seats), use **stratified / matched-pair randomization** on pre-experiment activity so giant whales balance evenly across Control and Treatment.
- For switchback schedules, randomize block assignments balanced across `(day_of_week, hour_of_day)` so Treatment never lands disproportionately on Friday dinner rush.

## 11. Authoritative References
- Ramesh Johari, Pete Koomen, Leonid Pekelis & David Walsh — *Always Valid Inference: Continuous Monitoring of A/B Tests* (Operations Research, 2022).
- Iavor Bojinov, David Simchi-Levi & Jinglong Zhao — *Design and Analysis of Switchback Experiments* (Management Science, 2023).
- DoorDash Engineering — *Switchback Tests and Randomized Experimentation Under Network Effects* (`https://careersatdoordash.com/blog/switchback-tests-and-randomized-experimentation-under-network-effects-at-doordash/`).

## 12. Limitations & When NOT to Use
- Do NOT use switchback experiments for features with **multi-day user learning or memory effects** (e.g., changing navigation menus every 2 hours confuses users and creates massive carryover); use geo/cluster randomization or quasi-experimental methods (`14-causal-inference.md`) instead.
- Multi-armed bandits (Thompson Sampling / UCB) optimize short-term regret (e.g., news headlines/ad creatives) but sacrifice clean statistical inference on secondary/guardrail metrics — prefer A/B/n or GST for core product decisions.
