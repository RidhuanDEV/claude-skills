# 06. Regression Baselines, Uncertainty & Leakage Prevention

## 1. Purpose & Activation Conditions
Compare baseline vs candidate AI releases statistically, quantify uncertainty on small eval suites, prevent data/benchmark leakage, and write honest release decision reports with explicit `NOT_RUN` surfaces. Load before promoting a prompt, model, embedding, or chunking change to staging or production.

## 2. Prerequisites
- Frozen baseline run artifact + candidate run artifact evaluated on the exact same `blind_holdout` dataset, corpus snapshot, and ACL revision (`01`, `02`).

## 3. Technical Principles & Constraints
- **Paired Comparison on Identical Holdout:** Always compare Baseline (`B`) vs Candidate (`C`) on the **exact same sample IDs** (`--compare-rag baseline.json candidate.json`). Track **Flipped Samples** explicitly (`PASS -> FAIL` regressions vs `FAIL -> PASS` fixes) — a net `+2%` score with 4 new regressions in Bahasa Indonesia legal queries is NOT a clean win!
- **Quantify Statistical Uncertainty:** On `N = 50` binary eval items, a `+4%` score jump (`42/50 -> 44/50`) is well within binomial/McNemar noise! Compute **95% Wilson confidence intervals** (or **paired bootstrap / McNemar's test** on discordant pairs `b` vs `c`) before claiming a meaningful improvement.
- **Zero-Tolerance Leakage Protection:**
  1. Never include `blind_holdout` examples inside few-shot system prompts or fine-tuning corpora.
  2. Never leak customer PII from production traces into committed git eval fixtures (sanitize/synthesize all names, NIK, emails, tokens before committing!).
- **Honest `NOT_RUN` & Untested-Surface Disclosure:** Every evaluation report MUST separate:
  - **Measured (`PASS` / `FAIL`)** with exact command, dataset version, denominator, and confidence bounds,
  - **Not Measured (`NOT_RUN`)** explicitly naming unexecuted live sweeps, untested languages, or unverified serving paths.

## 4. Architecture & Implementation
```typescript
export interface PairedSampleOutcome {
  readonly sampleId: string;
  readonly slice: string;
  readonly baselinePass: boolean;
  readonly candidatePass: boolean;
  readonly safetyCritical: boolean;
}

export interface PairedRegressionSummary {
  readonly total: number;
  readonly baselineRate: number;
  readonly candidateRate: number;
  readonly improvements: number; // baseline FAIL -> candidate PASS
  readonly regressions: number;  // baseline PASS -> candidate FAIL
  readonly safetyRegressions: readonly string[];
  readonly decision: 'PROMOTE_CANDIDATE' | 'BLOCKED_SAFETY_REGRESSION' | 'HOLD_NET_REGRESSION' | 'INCONCLUSIVE_NOISE';
}

export function compareBaselineVsCandidate(
  outcomes: readonly PairedSampleOutcome[]
): PairedRegressionSummary {
  if (outcomes.length === 0) {
    throw new Error('Paired comparison requires >= 1 sample');
  }
  let basePass = 0;
  let candPass = 0;
  let improvements = 0;
  let regressions = 0;
  const safetyRegressions: string[] = [];

  for (const o of outcomes) {
    if (o.baselinePass) basePass += 1;
    if (o.candidatePass) candPass += 1;
    if (!o.baselinePass && o.candidatePass) improvements += 1;
    if (o.baselinePass && !o.candidatePass) {
      regressions += 1;
      if (o.safetyCritical) safetyRegressions.push(o.sampleId);
    }
    if (o.safetyCritical && !o.candidatePass && !safetyRegressions.includes(o.sampleId)) {
      safetyRegressions.push(o.sampleId);
    }
  }

  let decision: PairedRegressionSummary['decision'] = 'INCONCLUSIVE_NOISE';
  if (safetyRegressions.length > 0) {
    decision = 'BLOCKED_SAFETY_REGRESSION';
  } else if (regressions > improvements) {
    decision = 'HOLD_NET_REGRESSION';
  } else if (improvements > regressions) {
    // Simple discordant-pair check (exact McNemar chi2 continuity-corrected on b+c >= 6)
    const discordant = improvements + regressions;
    const chi2 = discordant > 0 ? Math.pow(Math.abs(improvements - regressions) - 1, 2) / discordant : 0;
    decision = chi2 >= 3.841 ? 'PROMOTE_CANDIDATE' : 'INCONCLUSIVE_NOISE';
  }

  return {
    total: outcomes.length,
    baselineRate: basePass / outcomes.length,
    candidateRate: candPass / outcomes.length,
    improvements,
    regressions,
    safetyRegressions,
    decision,
  };
}
```

## 5. Platform / Vendor Variations
| Change Type | Minimum Regression Scope | Release Gate |
| :--- | :--- | :--- |
| **Prompt / System Instruction Edit** | Full offline deterministic + `dev` + `blind_holdout` paired diff | `0` safety regressions, net non-negative per slice |
| **Base Model Version Upgrade** | Full holdout + latency/token cost delta (`/shadow-finops`) + judge recalibration | Verify both quality AND p95 latency/cost |
| **Embedding / Chunking / Index Change** | Retrieval `evals/compare_search_indexes.py` + `--compare-rag` with frozen ACL | `100%` tenant ACL + non-regressing `Recall@K` & `Faithfulness` |

## 6. Decision Matrix & Trade-Offs
| Observed Delta (`B -> C`) | Discordant Pairs (`+Fix / -Reg`) | Safety Failures | Recommended Decision |
| :--- | :--- | :---: | :--- |
| `+8%` overall | `+10 / -2` (`McNemar p < 0.05`) | `0` | **`PROMOTE_CANDIDATE`** (verify cost/latency too) |
| `+4%` overall | `+5 / -3` (`McNemar p = 0.72`) | `0` | **`INCONCLUSIVE_NOISE`** (do not claim proven win; expand holdout or keep simpler baseline) |
| `+10%` overall | `+12 / -2` | **`1` ACL or RCE fail** | **`BLOCKED_SAFETY_REGRESSION`** (never trade safety for fluency!) |
| `-3%` overall | `+1 / -4` | `0` | **`HOLD_NET_REGRESSION`** (inspect flipped sample traces) |

## 7. Real Production Scenario
An engineering team upgrades from Model A to Model B after seeing overall accuracy jump from `86%` to `91%` on a 40-item test set. Paired diff inspection reveals Model B actually **regressed** on 2 Indonesian refusal probes (hallucinating policies instead of abstaining) and doubled average output tokens (`+115%` bill). Blocking promotion until abstention calibration and `max_output_tokens` caps are restored prevents both customer misinformation and a surprise invoice spike.

## 8. Failure Modes & Edge Cases
- **WRONG:** Reporting `"Candidate scored 92% vs Baseline 88% — clear improvement!"` without showing sample count `N`, paired regressions, slice breakdowns, or confidence bounds.
- **RIGHT:** Show `N`, paired `+improvements / -regressions`, per-slice table (`lang`, `scenario_type`), latency/token delta, `0` safety-failure proof, and explicit `NOT_RUN` items.
- **WRONG:** Leaving raw production customer prompts containing NIK/emails inside `evals/fixtures/*.json` committed to Git.
- **RIGHT:** Run `privacy_pdp_auditor.py --scan` on all eval fixtures before commit; store only scrubbed/synthetic payloads.

## 9. Testing & Verification
- Run `python shadow-eval/scripts/ai_eval_gate.py --compare-rag baseline.json candidate.json` and `python -m unittest discover -s shadow-eval/tests -v`.
- Verify any new eval fixture passes `python shadow-privacy/scripts/privacy_pdp_auditor.py --scan` with `0` raw PII hits.

## 10. Operational Considerations
- Archive baseline & candidate JSON artifacts per release tag so regressions discovered 3 months later can be bisected back to the exact prompt/model/corpus revision.

## 11. Authoritative References
- NIST AI RMF (`AI 100-1` & `AI 600-1`) — *Measure & Manage Continuous Monitoring* (`https://doi.org/10.6028/NIST.AI.600-1`).
- McNemar, Q. (1947) — *Note on the Sampling Error of the Difference Between Correlated Proportions or Percentages* (Psychometrika).

## 12. Limitations & When NOT to Use
- Offline paired evals cannot capture real-user behavioral drift or multi-session satisfaction; pair major AI launches with controlled online A/B experimentation (`/shadow-analytics`) and production telemetry (`/shadow-observe`).
