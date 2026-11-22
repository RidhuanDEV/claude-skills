# 01. Evaluation Taxonomy & Scenario Design

## 1. Purpose & Activation Conditions
Design rigorous, leak-free evaluation suites for LLM features, RAG pipelines, prompt classifiers, and tool-calling agents. Load when defining golden datasets, structuring scenario coverage, or separating tuning sets from blind acceptance gates.

## 2. Prerequisites
- Clear product task definition, failure impact tier, and separation between Retrieval (`/shadow-search`) and Generation/Agent (`/shadow-eval`).

## 3. Technical Principles & Constraints
- **6 Mandatory Scenario Archetypes:** A trustworthy evaluation suite MUST NOT contain only happy-path examples. Every benchmark covers:
  1. **Normal / In-Distribution:** Representative production user queries and multi-turn flows.
  2. **Ambiguous / Underspecified:** Requests requiring clarification or safe assumption declaration.
  3. **Out-of-Scope / Abstention (`must_refuse: true`):** Queries where the correct behavior is `"Insufficient evidence"` or refusal rather than fabrication.
  4. **Negative / Contrast & Topic-Switch Probes:** Inputs that look lexically similar to triggers (e.g., Indonesian `hanya`/`punya`/`bertanya` in `-nya` follow-up heuristics) that **must NOT** fire.
  5. **Adversarial / Security (`OWASP LLM01–LLM10`):** Prompt injection, indirect retrieved-doc injection, cross-tenant probe, unauthorized tool call attempt.
  6. **Incident / Regression & Cross-Skill:** Reproduction fixtures from real production bugs locked permanently into CI.
- **Immutable Dataset Versioning & Split Hygiene:** Tag every dataset snapshot with a semantic version + SHA-256 hash (`dataset_v1.2_<sha>`). Enforce a strict **Dev/Tuning Split** vs **Blind Held-Out Acceptance Split** — engineers tuning prompts must NEVER overfit directly against held-out acceptance items!
- **Per-Category Non-Compensatory Reporting:** Report scores separately per category (`normal`, `abstention`, `tenant_isolation`, `adversarial`). A `95%` overall score MUST NOT mask a single `0%` cross-tenant ACL leak!

## 4. Architecture & Implementation
```typescript
export type EvalScenarioType =
  | 'normal'
  | 'ambiguous'
  | 'abstention'
  | 'negative_contrast'
  | 'adversarial_security'
  | 'regression';

export interface EvalDatasetItem {
  readonly sampleId: string;
  readonly datasetVersion: string;
  readonly split: 'dev_tuning' | 'blind_holdout';
  readonly scenarioType: EvalScenarioType;
  readonly language: 'en' | 'id' | 'mixed';
  readonly tenantId: string;
  readonly prompt: string;
  readonly expectedDocIds: readonly string[];
  readonly forbiddenDocIds: readonly string[];
  readonly mustAbstain: boolean;
  readonly mustNotActions: readonly string[];
}

export function assertSplitIsolation(
  devIds: ReadonlySet<string>,
  holdoutItems: readonly EvalDatasetItem[]
): { readonly clean: boolean; readonly leakedIds: readonly string[] } {
  const leakedIds = holdoutItems
    .filter((item) => devIds.has(item.sampleId))
    .map((item) => item.sampleId);
  return { clean: leakedIds.length === 0, leakedIds };
}
```

## 5. Platform / Vendor Variations
| Evaluation Scope | Recommended Harness | Cost / Execution Level |
| :--- | :--- | :--- |
| **Offline Deterministic Gate (Retrieval, Regex, Red-Team Sinks)** | `shadow-eval/scripts/ai_eval_gate.py` | `L1_SAFE_VERIFICATION` ($0, CI-fast) |
| **Skill / Repo Structural Eval** | `evals/validate_skill_evaluations.py` | `L0_READ_ONLY` ($0) |
| **Live Multi-Model Agent Eval Sweep** | `evals/run_evals.py --agent` / Promptfoo / Inspect AI | **`L3_RESOURCE_INTENSIVE`** (requires explicit Monarch approval + budget cap) |

## 6. Decision Matrix & Trade-Offs
| Dataset Size | Best Used For | Statistical Confidence Note |
| :--- | :--- | :--- |
| **15–30 Golden Items** | Rapid PR smoke gate & heuristic precision/recall probes | Wide CI (`±15–20%`); catches gross regressions only |
| **100–300 Stratified Items** | Pre-release RAG/agent gate across slices (lang, tenant, type) | Meaningful slice comparison (`±5–8%` CI) |
| **1,000+ Production-Sampled Items** | Model migration / fine-tuning benchmark | Tight CI; stratify rare safety & abstention tails explicitly |

## 7. Real Production Scenario
A support copilot achieved `94%` pass rate on 50 developer-written happy-path questions, then shipped to production and leaked Tenant B's contract pricing when prompted with an indirect injection embedded in a shared PDF, while Indonesian follow-up questions containing `"hanya"` stitched unrelated prior queries. Rebuilding the dataset with `dev_tuning` vs `blind_holdout` splits, Indonesian contrast probes, and cross-tenant negative fixtures caught both defects offline before re-release.

## 8. Failure Modes & Edge Cases
- **WRONG:** Iterating prompts 20 times directly against the sole 30-item test set until it hits `100%`, then declaring production readiness.
- **RIGHT:** Tune exclusively on `dev_tuning`, freeze prompt + model version, then measure once on `blind_holdout` with confidence bounds and zero-tolerance safety gates.
- **WRONG:** Testing only positive recall (`"it triggers on follow-ups"`) without negative precision probes.
- **RIGHT:** Pair every recall probe (`>= 3` phrasings) with precision probes (`>= 5` realistic lookalikes that MUST NOT trigger).

## 9. Testing & Verification
- Run `python shadow-eval/scripts/ai_eval_gate.py --self-test` and `python -m unittest discover -s shadow-eval/tests -v`.
- Verify `assertSplitIsolation` rejects overlapping sample IDs between dev and holdout snapshots.

## 10. Operational Considerations
- Refresh `blind_holdout` quarterly with newly anonymized production failure traces (removing PII before storing fixtures) so benchmarks never go stale as user language evolves.

## 11. Authoritative References
- NIST AI RMF 1.0 (`AI 100-1`) & Generative AI Profile (`NIST AI 600-1`, July 2024) — *Measure Function* (`https://doi.org/10.6028/NIST.AI.600-1`).
- Anthropic Engineering — *Demystifying Evals for AI Agents* (`https://www.anthropic.com/engineering`).

## 12. Limitations & When NOT to Use
- Synthetic LLM-generated eval questions miss messy real-world typos, domain jargon, and code-switching (`ID + EN`); anchor at least `60%` of holdout scenarios in sanitized real traffic or real incident postmortems.
