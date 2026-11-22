# 03. Graders, LLM-as-a-Judge & Calibration

## 1. Purpose & Activation Conditions
Select the right grading hierarchy (Deterministic Code Graders -> Calibrated LLM Judges -> Human Anchor Audits), eliminate judge bias, and measure inter-rater reliability before trusting automated eval scores. Load when designing evaluation rubrics, calibrating LLM-as-a-Judge prompts, or investigating noisy/inconsistent eval scores.

## 2. Prerequisites
- Stratified golden dataset with explicit rubrics (`01-evaluation-taxonomy-and-scenario-design.md`).

## 3. Technical Principles & Constraints
- **3-Tier Grader Hierarchy (Prefer Deterministic First):**
  1. **Code / Deterministic Graders (Primary for Objective Rules):** Schema validation, exact refusal/allow status, forbidden SQL/XSS/secret regexes, tool-call parameter bounds, tenant ID isolation. Zero variance, `$0` cost, instant CI feedback.
  2. **Calibrated LLM-as-a-Judge (Secondary for Semantic Rubric Criteria):** Faithfulness, tone, nuance, completeness — **ONLY** after validating agreement against human-labeled anchor samples!
  3. **Independent Human Expert Audit (Ground Truth Anchor):** Mandatory for safety-critical domains (medical, legal, fintech), rubric calibration (`>= 30–50` anchor items), and resolving judge disagreements.
- **Mandatory Judge Calibration & Bias Mitigations:**
  - **No Same-Model Self-Grading Without Calibration:** Models systematically favor their own phrasing and longer answers (*self-preference* & *verbosity bias*). Use a distinct judge model family or explicitly calibrate against human ground truth.
  - **Position-Bias Swap Test:** For pairwise comparisons (`A vs B`), run BOTH `(A, B)` and `(B, A)` orderings; flag inconsistent flips as ties or escalate to human audit.
  - **Binary / Structured Criteria > Arbitrary 1–10 Scales:** Break evaluation into concrete `PASS`/`FAIL` atomic criteria (e.g., `"Cites exact source clause"`, `"Does not leak PII"`, `"Offers rollback step"`) rather than noisy holistic `7/10` scores.
  - **Quantify Inter-Rater Agreement:** Compute **Cohen's kappa ($\kappa$)** (or Krippendorff's $\alpha$) between LLM Judge and Human Anchor labels before gating releases on the judge (target $\kappa \ge 0.75$ for general quality, $\ge 0.85$ for critical gates).

## 4. Architecture & Implementation
```typescript
export interface BinaryJudgmentPair {
  readonly sampleId: string;
  readonly humanPass: boolean;
  readonly judgePass: boolean;
}

export interface JudgeCalibrationReport {
  readonly n: number;
  readonly rawAgreement: number;
  readonly cohensKappa: number;
  readonly falsePassRate: number; // Judge passed when human failed (most dangerous error!)
  readonly calibrated: boolean;
}

export function evaluateJudgeCalibration(
  pairs: readonly BinaryJudgmentPair[],
  minKappa = 0.75,
  maxFalsePassRate = 0.05
): JudgeCalibrationReport {
  if (pairs.length === 0) {
    throw new Error('Calibration requires at least 1 human-labeled anchor pair');
  }
  let tp = 0;
  let tn = 0;
  let fp = 0; // Judge=PASS, Human=FAIL
  let fn = 0; // Judge=FAIL, Human=PASS
  for (const p of pairs) {
    if (p.humanPass && p.judgePass) tp += 1;
    else if (!p.humanPass && !p.judgePass) tn += 1;
    else if (!p.humanPass && p.judgePass) fp += 1;
    else fn += 1;
  }
  const n = pairs.length;
  const p0 = (tp + tn) / n;
  const pHumanPass = (tp + fn) / n;
  const pJudgePass = (tp + fp) / n;
  const pe = pHumanPass * pJudgePass + (1 - pHumanPass) * (1 - pJudgePass);
  const kappa = pe < 1 ? (p0 - pe) / (1 - pe) : 1;
  const humanFailCount = tn + fp;
  const falsePassRate = humanFailCount > 0 ? fp / humanFailCount : 0;

  return {
    n,
    rawAgreement: p0,
    cohensKappa: kappa,
    falsePassRate,
    calibrated: kappa >= minKappa && falsePassRate <= maxFalsePassRate,
  };
}
```

## 5. Platform / Vendor Variations
| Bias / Failure Mode | Root Cause | Concrete Mitigation |
| :--- | :--- | :--- |
| **Position Bias** | Judge prefers first (`A`) or second (`B`) candidate | Run swapped-order trials `(A,B)` + `(B,A)` and require order agreement |
| **Verbosity Bias** | Judge rewards longer bullet lists even when padded | Use atomic binary checklist criteria + penalize unsupported fluff explicitly |
| **Self-Enhancement Bias** | Same model family grades its own outputs leniently | Cross-family judge + human anchor calibration (`evaluateJudgeCalibration`) |
| **Score Drift Across Runs** | High temperature (`0.7–1.0`) makes judge non-deterministic | Set `temperature = 0`, pin exact judge model snapshot ID, log prompt hash |

## 6. Decision Matrix & Trade-Offs
| Grader Type | Repeatability | Cost | Captures Semantic Nuance | Best Role |
| :--- | :---: | :---: | :---: | :--- |
| **Deterministic Code / Regex / AST** | 100% | Zero | Low | Schema, ACL, security sinks, tool args, negative probes |
| **Calibrated Binary LLM Judge** | High (`temp=0`) | Medium (`L3`) | High | Groundedness, helpfulness, tone, rubric scoring |
| **Human Domain Expert** | High (with rubric) | High | Highest | Calibration anchors, safety sign-off, edge disputes |

## 7. Real Production Scenario
Two prompt revisions for a customer-support agent return conflicting judge scores (`82%` vs `91%`, then `89%` vs `84%` on re-run). Investigation reveals the team used an uncalibrated holistic `1–10` judge prompt at `temperature = 0.7` with the same model that generated the answers, and the judge had a `28%` false-pass rate on subtle policy violations (`kappa = 0.41`). Converting the rubric to 5 atomic binary checks at `temperature = 0`, pinning an independent judge model, and validating `kappa = 0.84` on 40 human-labeled anchors stabilized score variance to `< 1.5%`.

## 8. Failure Modes & Edge Cases
- **WRONG:** Reporting raw agreement (`90%`) on an imbalanced dataset where `92%` of samples pass (a broken judge that ALWAYS outputs `PASS` gets `92%` raw agreement while missing `100%` of failures!).
- **RIGHT:** Always inspect **Cohen's kappa** AND **False-Pass Rate** (`judge=PASS` when `human=FAIL`) alongside raw agreement.
- **WRONG:** Running large-scale LLM-as-a-Judge sweeps (`500+` calls) automatically without `L3` approval and token budget cap.
- **RIGHT:** Run deterministic offline checks freely (`L1`), and request explicit Monarch `L3` approval with estimated cost before batch LLM judge runs.

## 9. Testing & Verification
- Test your judge prompt against 5 known-bad adversarial fixtures (subtle hallucination, verbose wrong answer, hidden PII leak) and assert `0%` false passes before running it on real candidates.

## 10. Operational Considerations
- Version judge prompts alongside evaluation results (`judge_model`, `judge_prompt_sha`, `calibration_kappa`) so a sudden score jump isn't misattributed to your app when the judge changed.

## 11. Authoritative References
- Zheng et al. (NeurIPS 2023) — *Judging LLM-as-a-Judge with MT-Bench and Chatbot Arena* (`https://arxiv.org/abs/2306.05685`) `[PREPRINT/NEURIPS]`.
- Cohen, J. (1960) — *A Coefficient of Agreement for Nominal Scales* (Educational and Psychological Measurement).

## 12. Limitations & When NOT to Use
- Never delegate final legal, medical, or high-impact security sign-off solely to an LLM judge; use judges to triage and scale coverage while humans own critical acceptance decisions.
