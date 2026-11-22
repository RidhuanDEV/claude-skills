# 15. Decision Science & Reporting

## 1. Purpose & Activation Conditions
Translate statistical outputs and product analyses into rigorous, auditable executive decisions (`SHIP`, `ITERATE`, `ROLLBACK`, `RE-RUN / FIX INSTRUMENTATION`) — covering decision records, uncertainty communication, guardrail overrides, novelty/primacy checks, post-launch holdouts, and feature-flag retirement. Load when writing experiment readouts, product review memos, or resolving disputed ship calls.

## 2. Prerequisites
- Verified telemetry (`07`), valid SRM & randomization (`11`), appropriate statistical estimator (`12–13`), or falsified quasi-experiment (`14`).

## 3. Technical Principles & Constraints
- **Mandatory 4-Gate Ship Decision Framework (Strict Precedence):**
  1. **Gate 1 — Data Integrity & SRM (HARD STOP):** Is `srm_p >= 0.001`, tracking clean, and exposure symmetric? If NO -> **`BLOCKED_SRM` / `RE-RUN`** immediately. Never ship on broken randomization even if lift is `+12%, p = 0.02`!
  2. **Gate 2 — Blocking Guardrails (HARD STOP):** Did latency, crash/error rate, refund/chargeback rate, or core trust/privacy metrics regress beyond threshold? If YES -> **`ROLLBACK / ITERATE`** unless engineering resolves the regression and re-validates.
  3. **Gate 3 — Statistical & Practical Significance:** Look at the **95% Confidence Interval** against the **Minimum Viable Business Effect (MDE / ROI threshold)** — NOT just whether `p < 0.05`!
     - Lower bound of CI `> 0` and clinically/financially worthwhile -> **`SHIP_CANDIDATE`**.
     - Point estimate positive, CI spans zero (`[-0.4%, +2.8%]`), experiment underpowered -> **`INCONCLUSIVE`** (do NOT declare `"no effect"` — distinguish *"evidence of no meaningful effect"* from *"insufficient power"*).
     - CI tightly bounded near zero (`[-0.2%, +0.3%]`) -> **Flat / Neutral** (ship ONLY if it simplifies architecture, cuts cost, or improves accessibility/UX with zero downside; otherwise **`DO NOT SHIP`** to avoid dead complexity).
  4. **Gate 4 — Durability (Novelty / Primacy & Seasonality):** Check lift trajectory across Day 1–3 vs Day 8–14. A `+8%` spike on Day 1 that decays to `+0.3%` by Day 12 is a **novelty effect** — extend or run a post-launch holdout before projecting annualized revenue!
- **Decision-First Executive Communication:** Start every readout with a 5-line **Executive Verdict Box** (`Recommendation | Primary OEC + 95% CI | SRM & Data Quality Status | Guardrails | Annualized Impact Range & Caveats`), followed by diagnostic breakdowns and raw evidence links. Never cherry-pick 1 lucky subgroup (`"overall was flat, but iOS users in Bali on Tuesday were +14%!"`) to rationalize shipping a failed hypothesis.
- **Post-Launch Discipline (Holdouts & Flag Cleanup):**
  - For major architectural or growth bets, keep a small **long-term holdout (`2%–5%` for 30–90 days)** to verify durable retention/LTV impact and detect cumulative interaction effects across shipped tests.
  - Within **14 days** of a `SHIP` or `ROLLBACK` decision, remove dead experiment branches and archive feature flags so technical debt never accumulates.

## 4. Architecture & Implementation
```typescript
export type ExperimentDecision =
  | 'BLOCKED_SRM_RERUN'
  | 'BLOCKED_GUARDRAIL_ITERATE'
  | 'SHIP_FULL_ROLLOUT'
  | 'SHIP_WITH_HOLDOUT'
  | 'ITERATE_HYPOTHESIS'
  | 'ROLLBACK_CLEANUP';

export interface ExperimentDecisionRecord {
  readonly experimentKey: string;
  readonly decisionDateIso: string;
  readonly decision: ExperimentDecision;
  readonly srmPValue: number;
  readonly primaryMetric: {
    readonly name: string;
    readonly relativeLiftPct: number;
    readonly ci95LowPct: number;
    readonly ci95HighPct: number;
    readonly pValue: number;
    readonly estimator: string;
  };
  readonly blockingGuardrailsPassed: boolean;
  readonly noveltyDecayObserved: boolean;
  readonly notMeasuredCaveats: readonly string[];
  readonly flagCleanupDueDateIso: string;
  readonly owners: readonly string[];
}

export function determineBaselineDecision(input: {
  readonly srmPValue: number;
  readonly blockingGuardrailsPassed: boolean;
  readonly ci95LowPct: number;
  readonly ci95HighPct: number;
  readonly minWorthwhileLiftPct: number;
  readonly noveltyDecayObserved: boolean;
}): ExperimentDecision {
  if (input.srmPValue < 0.001) return 'BLOCKED_SRM_RERUN';
  if (!input.blockingGuardrailsPassed) return 'BLOCKED_GUARDRAIL_ITERATE';
  if (input.ci95HighPct < 0) return 'ROLLBACK_CLEANUP';
  if (input.ci95LowPct >= input.minWorthwhileLiftPct) {
    return input.noveltyDecayObserved ? 'SHIP_WITH_HOLDOUT' : 'SHIP_FULL_ROLLOUT';
  }
  return 'ITERATE_HYPOTHESIS';
}
```

## 5. Platform / Vendor Variations
| Organization Maturity | Readout Format | Governance Cadence |
| --- | --- | --- |
| **Startup / Lean Squad** | 1-page Markdown Decision Record attached to PR / ticket + verifier JSON | Weekly product review |
| **Scale-Up (PostHog / Statsig / Eppo)** | Auto-generated scorecard + human Decision Record memo (never ship from automated green badge alone!) | Bi-weekly Experiment Review Board |
| **Enterprise / Regulated Fintech** | Versioned Experiment Registry + quarterly cumulative Holdout audit vs Finance ledger | Change Advisory + Product Science sign-off |

## 6. Decision Matrix & Trade-Offs (Reading Confidence Intervals Correctly)
| Observed 95% CI (Relative Lift) | Business Threshold (`+1.0%`) | Correct Interpretation | Recommended Action |
| --- | --- | --- | --- |
| `[+2.1%, +5.4%]` (Clean SRM & Guardrails) | Entire CI above `+1.0%` | Clear, practically meaningful win | **SHIP** (+ optional 5% holdout if major change) |
| `[+0.1%, +0.4%]` (`p = 0.01`) | Stat-sig, below ROI threshold | Statistically real but trivially small | **DO NOT SHIP** unless zero maintenance cost |
| `[-0.5%, +4.2%]` (`p = 0.14`) | Spans zero & includes big upside | **Inconclusive / Underpowered** (not proven flat!) | Extend runtime, apply CUPED, or iterate stronger treatment |
| `[-0.3%, +0.4%]` (`p = 0.78`) | Tightly bounded around zero | **Precise Null** (meaningful lift ruled out) | **ROLLBACK / MOVE ON** — don't waste more traffic |
| `[+6.0%, +18.0%]` (**SRM `p = 0.0002`**) | **INVALID** | Randomization/logging corrupted | **`BLOCKED_SRM`** — diagnose, fix bug, re-run |

## 7. Real Production Scenario
A PM brings an A/B readout to the weekly launch review: `"Treatment boosted checkout conversion by +12% (p = 0.02). Let's ship today so we hit Q4 targets!"` The Staff Analyst runs `analytics_experiment_verifier.py --check-experiment` and presents a calm, evidence-backed Decision Record:
1. **Verdict:** **`BLOCKED_SRM_RERUN`** (SRM `p = 0.0002`, Control `10,200` vs Treatment `9,680`).
2. **Why `p = 0.02` cannot be trusted:** A `5.1%` missing-user asymmetry easily explains a fake `+12%` lift if slow/failing mobile sessions dropped out of Treatment before logging.
3. **Actionable Path Forward (not just "No"):** Isolate the missing `520` Treatment users by `device_os`, `js_error`, and `redirect_latency` today, fix the broken Android WebView bundle, verify zero SRM in a 24-hour canary, and re-run a clean 7-day test with pre-experiment CUPED (`rho = 0.55` cuts runtime by ~30%).

## 8. Failure Modes & Edge Cases
- **WRONG:** Summing up the estimated lifts of 10 shipped experiments (`+3% + 2% + 4% + ... = +32%`) and promising Finance `+32%` annual revenue (Winner's Curse + interaction overlap + novelty decay routinely deflate naive sums by 40%–70%).
- **RIGHT:** Apply empirical shrinkage (or validate cumulative impact via a quarterly `5%` Global Holdout) before booking projected revenue into financial forecasts.
- **WRONG:** Declaring a failed test `"wasted engineering time"` and hiding the readout (breeds p-hacking and repeats dead ideas 6 months later).
- **RIGHT:** Archive EVERY experiment Decision Record — wins, neutrals, and losses — in a searchable Experiment Knowledge Base (`60%–80%` of well-designed ideas in mature tech orgs are neutral or negative; learning fast is the win!).

## 9. Testing & Verification
- Before publishing any readout, run `python shadow-analytics/scripts/analytics_experiment_verifier.py --check-experiment <readout.json>` and attach its JSON output verbatim to the Decision Record.
- Peer-review any high-stakes (`> $100k` revenue impact or pricing/auth change) Decision Record with an independent analyst checking SRM, estimator choice, CUPED covariate timing, and guardrail sensitivity.

## 10. Operational Considerations
- Track **Experimentation Program Health Metrics** quarterly: experiments launched/month, SRM incident rate (target `< 2%`), median time-to-decision, and stale feature-flag count (`> 30 days` post-decision -> alert owning squad).
- Always document a `"Not Measured"` section explicitly listing long-term effects (e.g., 90-day renewal churn, brand sentiment, offline cannibalization) that a 14-day test could not observe.

## 11. Authoritative References
- Ron Kohavi, Diane Tang & Ya Xu — *Trustworthy Online Controlled Experiments* (Ch. 22–23: Institutional Memory & Decision Making).
- Evan Miller — *How Not To Run an A/B Test* (`https://www.evanmiller.org/how-not-to-run-an-ab-test.html`).
- Gelman & Carlin — *Beyond Power Calculations: Assessing Type S (Sign) and Type M (Magnitude) Errors* (Perspectives on Psychological Science, 2014).

## 12. Limitations & When NOT to Use
- Do NOT require a formal 2-week A/B Decision Record for obvious P0 bug fixes, security patches, legal compliance mandates, or WCAG accessibility fixes — ship fixes immediately and verify via operational monitoring and guardrails.
- Statistical evidence informs product strategy; it does not replace product vision or ethical judgment (never ship a dark pattern that lifts short-term clicks while eroding user trust).
