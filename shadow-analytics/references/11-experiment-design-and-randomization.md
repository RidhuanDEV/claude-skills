# 11. Experiment Design & Randomization

## 1. Purpose & Activation Conditions
Design trustworthy online controlled experiments (A/B/n tests): deterministic salted bucketing, **Assignment vs Exposure separation**, randomization-unit selection, mutual-exclusion layers, A/A calibration, and Sample Ratio Mismatch (SRM) detection & root-cause diagnosis. Load before launching any feature experiment or diagnosing SRM/bucketing anomalies.

## 2. Prerequisites
- Agreed Primary OEC & Guardrails (`01-product-metrics-and-kpi-design.md`) and clean identity keys (`03-identity-resolution.md`).

## 3. Technical Principles & Constraints
- **Deterministic Salted Hash Bucketing:** Assign units deterministically via `hash(experiment_salt + ":" + randomization_unit_id) % 10000` (using MurmurHash3 / SHA-256). Always use a **unique salt per experiment** so Experiment B never correlates with Experiment A's bucket split, and never use `Math.random()` without sticky persistence.
- **Separate Assignment vs Exposure (CRITICAL):**
  - **Assignment (`Experiment_Assigned`):** Logged the moment a unit is eligible and bucketed into Control or Treatment. Defines the **Intent-to-Treat (ITT)** denominator — strictly unbiased under randomization.
  - **Exposure (`Experiment_Exposed`):** Logged ONLY when the unit actually reaches the code path / UI surface where the treatment differs from control (triggered at the **exact identical code point** for BOTH Control and Treatment — also known as *triggering* / *counterfactual logging*).
  - **Never conflate them:** Logging exposure only when Treatment renders a new banner (and not at the equivalent point in Control) creates massive selection bias and guarantees SRM! When non-compliance occurs, report **ITT** as primary (valid causal estimate of offering the feature) and **LATE / CACE** (Local Average Treatment Effect via Wald estimator = `ITT / exposure_rate_diff`) only with clear assumptions.
- **Randomization Unit Selection:** Match the randomization unit to the interference boundary:
  - Logged-in individual consumer feature -> `user_id`
  - Pre-signup landing/funnel -> `anonymous_id` (persist sticky cookie)
  - B2B collaborative workspace -> `workspace_id` (prevents teammates seeing different UIs)
  - Marketplace / shared supply -> `geo_region` or `time_cluster` (`13-advanced-experimentation.md`)
- **Sample Ratio Mismatch (SRM — Hard Invalidation Gate):** Run Pearson's chi-squared goodness-of-fit test on observed vs expected variant counts at $\alpha_{\text{SRM}} = 0.001$ (Fabijan et al., Microsoft KDD 2019 found ~6% of real experiments suffer SRM). **If $p_{\text{SRM}} < 0.001$, the experiment is INVALID and MUST BE BLOCKED (`BLOCKED_SRM`) regardless of how positive or statistically significant the primary metric looks!**
- **A/A Testing & Mutual Exclusion:** Run periodic A/A tests (identical experience in both buckets) to confirm uniform p-values, zero SRM, and empirical false-positive rate `~5%`. Place mutually exclusive UI changes (e.g., two checkout layout tests) inside one **Mutual Exclusion Layer**; orthogonal experiments run in independent layers with distinct salts.

## 4. Architecture & Implementation
```typescript
import { createHash } from 'node:crypto';

export interface ExperimentAllocation {
  readonly experimentKey: string;
  readonly salt: string;
  readonly variants: readonly { readonly name: string; readonly weightBps: number }[]; // Sums to 10000
}

export function assignDeterministicVariant(
  unitId: string,
  allocation: ExperimentAllocation
): string {
  const totalBps = allocation.variants.reduce((acc, v) => acc + v.weightBps, 0);
  if (totalBps !== 10000) {
    throw new Error(`Allocation weights for ${allocation.experimentKey} must sum to 10000 bps (got ${totalBps})`);
  }
  const digest = createHash('sha256').update(`${allocation.salt}:${unitId}`).digest();
  const bucket = digest.readUInt32BE(0) % 10000;

  let cumulative = 0;
  for (const variant of allocation.variants) {
    cumulative += variant.weightBps;
    if (bucket < cumulative) {
      return variant.name;
    }
  }
  return allocation.variants[allocation.variants.length - 1].name;
}
```
SRM chi-squared check in SQL (2-variant 50/50 or general ratios):
```sql
-- Daily Experiment SRM Health Check (Flag whenever chi2 > 10.828 for df=1 -> p < 0.001)
WITH counts AS (
  SELECT
    experiment_key,
    variant_name,
    COUNT(DISTINCT randomization_unit_id) AS observed_n,
    MAX(expected_ratio) AS expected_ratio
  FROM fct_experiment_assignments
  WHERE assigned_at >= NOW() - INTERVAL '14 days'
  GROUP BY 1, 2
),
totals AS (
  SELECT experiment_key, SUM(observed_n) AS total_n
  FROM counts
  GROUP BY 1
)
SELECT
  c.experiment_key,
  SUM(POWER(c.observed_n - (t.total_n * c.expected_ratio), 2) / NULLIF(t.total_n * c.expected_ratio, 0)) AS srm_chi2,
  CASE
    WHEN SUM(POWER(c.observed_n - (t.total_n * c.expected_ratio), 2) / NULLIF(t.total_n * c.expected_ratio, 0)) > 10.828
      THEN 'BLOCKED_SRM'
    ELSE 'OK'
  END AS srm_status
FROM counts c
JOIN totals t ON t.experiment_key = c.experiment_key
GROUP BY 1;
```

## 5. Platform / Vendor Variations
| Platform | Assignment Mechanism | Trigger / Exposure Nuance |
| --- | --- | --- |
| **PostHog Experiments** | SHA-1 hash of `flag_key + distinct_id` | Automatically emits `$feature_flag_called` on evaluation — evaluate flag **only at the trigger point**, not globally on app boot! |
| **Statsig / GrowthBook** | Deterministic hash + Warehouse-native SQL exposure table | Supports explicit exposure queries, automated SRM alerts, and mutual exclusion layers |
| **LaunchDarkly** | Deterministic murmur/sha bucketing + Experimentation SDK | Requires calling `variation()` at identical trigger point for Control and Treatment |
| **Custom In-House** | `assignDeterministicVariant` + dedicated `Experiment_Assigned` / `Experiment_Exposed` events | Must build SRM monitor & A/A calibration yourself |

## 6. Decision Matrix & Trade-Offs (SRM Root-Cause Taxonomy — Fabijan et al. KDD 2019)
| Stage Where SRM Occurs | Common Engineering Cause | Diagnostic Query |
| --- | --- | --- |
| **Assignment / Bucketing** | Broken hash modulo bias, CDN/edge cache serving Treatment HTML to Control users | Compare raw edge assignment logs vs app-level logs by cache status (`HIT`/`MISS`) |
| **Execution / Redirect** | Treatment uses client-side redirect (slower -> users bounce before exposure fires!) | Check `assigned -> exposed` drop rate by variant & device latency |
| **Telemetry / Logging** | Treatment crashes JS bundle or triggers ad-blocker -> loses exposure events | Segment SRM by `browser`, `app_version`, `js_error_count` |
| **Analysis / Filtering** | Bot filter or post-assignment eligibility filter drops one variant asymmetrically | Re-run SRM on unfiltered raw assignments before bot/eligibility filters |

## 7. Real Production Scenario
A checkout redesign experiment runs 50/50 for 10 days. The dashboard shows **+12% checkout conversion lift (`p = 0.02`)**, and the PM asks to ship immediately. Before approving, the engineer inspects variant counts: Control has `10,200` users and Treatment has `9,680` users — `srm_chi2 = 13.60, p = 0.00022 < 0.001` (`BLOCKED_SRM`). Root-cause triage reveals Treatment's new heavy JS bundle crashed on older Android WebViews before `Experiment_Exposed` fired, dropping ~520 low-converting mobile users from Treatment's denominator and creating an **entirely illusory +12% lift**. Blocking the ship prevents a conversion-destroying rollout!

## 8. Failure Modes & Edge Cases
- **WRONG:** "Re-weighting" or randomly subsampling Control down to match Treatment's count to "fix" SRM.
- **RIGHT:** NEVER sub-sample or post-hoc re-weight away SRM — the missing users are **not missing at random** (they are systematically slower devices, crash victims, or impatient bounces). Fix the root cause and re-run cleanly.
- **WRONG:** Changing variant traffic split mid-experiment (`10/90 -> 50/50`) and analyzing the entire date range pooled together (introduces Simpson's paradox from day-of-week shifts AND triggers false SRM).
- **RIGHT:** Analyze only post-ramp stable-allocation periods (or stratify strictly by allocation period with Mantel-Haenszel / inverse-variance weighting).

## 9. Testing & Verification
- Run `python shadow-analytics/scripts/analytics_experiment_verifier.py --check-experiment <exp.json>` on every experiment readout; confirm `srm_detected == false` BEFORE interpreting any p-value.
- Run a 7-day A/A test whenever onboarding a new experimentation SDK, reverse proxy, or mobile release channel; assert uniform split (`p_SRM > 0.01`) and zero systematic metric drift.

## 10. Operational Considerations
- Run every experiment for at least **1–2 full weekly cycles** (7 or 14 days) to capture weekday vs weekend behavioral differences and allow short-term novelty effects to decay.
- Document a concise 1-page **Experiment Pre-Registration Spec** before launch: Hypothesis, Randomization Unit, Trigger Point, Primary OEC, Guardrails, MDE, Required Sample Size, and Stopping Rule.

## 11. Authoritative References
- Aleksander Fabijan, Jayant Gupchup, Somit Gupta, Jeff Omhover, Wen Qin, Lukas Vermeer & Pavel Dmitriev — *Diagnosing Sample Ratio Mismatch in Online Controlled Experiments: A Taxonomy and Rules of Thumb for Practitioners* (KDD 2019, `https://www.microsoft.com/en-us/research/publication/diagnosing-sample-ratio-mismatch-in-online-controlled-experiments/`).
- Ron Kohavi, Diane Tang & Ya Xu — *Trustworthy Online Controlled Experiments* (Ch. 3, 13, 19–21).
- PostHog Documentation — *Experiment Exposures & Feature Flag Triggering* (`https://posthog.com/docs/experiments/exposures`).

## 12. Limitations & When NOT to Use
- Do NOT run randomized user-level A/B tests when traffic is tiny (`< 500` conversions/month -> MDE would need to be `> 30%` to detect) or when ethical/legal rules prohibit unequal treatment — use qualitative usability testing, staged rollouts, or quasi-experimental causal inference (`14-causal-inference.md`).
- Never launch an experiment without verifying the rollback kill-switch works in `< 1 minute`.
