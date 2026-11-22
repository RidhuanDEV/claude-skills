# 02. RAG Retrieval & Faithfulness Metrics

## 1. Purpose & Activation Conditions
Measure RAG pipelines with strict attribution between Retrieval quality (`/shadow-search`) and Generation groundedness (`/shadow-eval`), enforcing 100% tenant ACL isolation and citation integrity. Load when benchmarking RAG changes, diagnosing hallucinations, or gating RAG releases.

## 2. Prerequisites
- Versioned golden dataset (`01-evaluation-taxonomy-and-scenario-design.md`) with frozen corpus snapshot ID and independent policy-owner ACL revision (`/shadow-auth`).

## 3. Technical Principles & Constraints
- **Decouple Retrieval vs Generation (Root-Cause Attribution):**
  - If `Context Recall@K` is low (`< 0.85`), the right document never reached the prompt — **tuning system prompts will NOT fix broken retrieval**; hand off to `/shadow-search` (chunking, Indonesian morphology/BM25, hybrid RRF, reranker).
  - If `Context Recall@K` is high (`>= 0.90`) but `Faithfulness` is low (`< 0.90`), the model is hallucinating beyond provided evidence — fix prompt grounding, structured citations, or model choice.
- **Zero-Tolerance Isolation & Citation Invariants:**
  - **Tenant ACL Isolation = `100.0%`:** Verify forbidden cross-tenant chunks are absent from BOTH ranked top-K results AND the actual serialized generation context (including below-cutoff metadata).
  - **Citation Integrity = `100.0%`:** Every emitted citation ID MUST exist in the retrieved context set AND genuinely support the attached claim (verified by an independent reviewer/calibrated judge, not mere ID membership!).
- **Abstention Calibration:** Measure BOTH **False Acceptance** (answering when `must_abstain: true` -> hallucination) and **False Rejection** (refusing an answerable question -> poor UX), sliced by language (`id`, `en`, `mixed`).

## 4. Architecture & Implementation
```powershell
# Run single-snapshot offline RAG gate and baseline-vs-candidate holdout comparison
python "shadow-eval/scripts/ai_eval_gate.py" --score-rag path/to/rag_eval_dataset.json
python "shadow-eval/scripts/ai_eval_gate.py" --compare-rag path/to/baseline.json path/to/candidate.json
```
Typed Claim-Support Verification Contract:
```typescript
export interface LabeledClaim {
  readonly claimId: string;
  readonly citedDocIds: readonly string[];
  readonly independentSupportVerdict: 'supported' | 'unsupported' | 'contradicted' | 'unlabeled';
}

export interface RagSampleEvaluation {
  readonly sampleId: string;
  readonly retrievedDocIds: readonly string[];
  readonly forbiddenDocIds: readonly string[];
  readonly claims: readonly LabeledClaim[];
}

export function computeSampleGrounding(sample: RagSampleEvaluation): {
  readonly tenantLeakCount: number;
  readonly fabricatedCitationCount: number;
  readonly labeledFaithfulness: number | null;
} {
  const retrievedSet = new Set(sample.retrievedDocIds);
  const forbiddenSet = new Set(sample.forbiddenDocIds);
  const tenantLeakCount = sample.retrievedDocIds.filter((id) => forbiddenSet.has(id)).length;

  let fabricatedCitationCount = 0;
  let labeledTotal = 0;
  let supported = 0;

  for (const claim of sample.claims) {
    for (const cid of claim.citedDocIds) {
      if (!retrievedSet.has(cid)) fabricatedCitationCount += 1;
    }
    if (claim.independentSupportVerdict !== 'unlabeled') {
      labeledTotal += 1;
      if (claim.independentSupportVerdict === 'supported') supported += 1;
    }
  }

  return {
    tenantLeakCount,
    fabricatedCitationCount,
    labeledFaithfulness: labeledTotal > 0 ? supported / labeledTotal : null,
  };
}
```

## 5. Platform / Vendor Variations
| Metric Layer | Primary Metric | Typical Production Gate | Owner Skill |
| :--- | :--- | :--- | :--- |
| **Retrieval Security** | Cross-tenant chunk leak rate | **`0.0%`** (Blocking) | `/shadow-search` + `/shadow-auth` |
| **Retrieval Quality** | `Recall@K`, `MRR@K`, `NDCG@K` | `Recall@K >= 0.85` | `/shadow-search` |
| **Generation Grounding** | Claim Faithfulness (`supported / labeled`) | `>= 0.90` (`>= 0.95` regulated) | `/shadow-eval` |
| **Citation Integrity** | Valid retrieved IDs + supported claims | **`100.0%`** IDs valid | `/shadow-eval` |
| **Abstention** | False Acceptance Rate on unanswerables | `<= 5%` (`0%` medical/legal) | `/shadow-eval` |

## 6. Decision Matrix & Trade-Offs
| Observed Failure Pattern | Root Cause Layer | Right Action |
| :--- | :--- | :--- |
| Low `Recall@K`, high `Faithfulness` | Retrieval / Indexing | Optimize chunking, BM25/Indonesian analyzer, hybrid RRF (`/shadow-search`) |
| High `Recall@K`, low `Faithfulness` | Generation / Prompting | Enforce quote-first grounding, strict abstention prompt, or stronger model |
| High `Citation ID Membership`, low `Claim Support` | Decorative Citations | Require claim-level NLI / independent reviewer verification, not regex `[1]` checks |
| Cross-tenant doc appears in context | Missing Pre-Filter ACL | Block release immediately; enforce pre-top-K `WHERE tenant_id = ?` in vector store |

## 7. Real Production Scenario
A legal-doc RAG system passed a legacy regex check showing `"100% of answers include [doc-id] citations"`. When upgraded to claim-level evaluation (`--compare-rag` with independent reviewer support labels), 24% of cited `[doc-id]` references actually discussed a different clause and did not support the generated legal conclusion. Switching to quote-anchored claim verification eliminated decorative citations and caught subtle confabulations before client UAT.

## 8. Failure Modes & Edge Cases
- **WRONG:** Treating `citation_id in retrieved_ids` as proof that the claim is faithful (models frequently attach real retrieved IDs to fabricated statements!).
- **RIGHT:** Separate deterministic `citation_membership` from independently verified `claim_support`, and keep `unlabeled` denominators explicitly visible.
- **WRONG:** Comparing baseline vs candidate RAG runs across different corpus snapshots or unpinned ACL policy revisions.
- **RIGHT:** Freeze `corpus_snapshot_id`, `label_revision`, and `acl_policy_revision` identically across both compared runs.

## 9. Testing & Verification
- Run `python -m unittest discover -s shadow-eval/tests -v` (`test_rag_gate.py` verifies typed samples, unlabeled denominator transparency, holdout checks, and isolation enforcement).
- Run `python evals/compare_search_indexes.py` when comparing retrieval index/ranking changes alongside ACL snapshots.

## 10. Operational Considerations
- Slice all RAG metrics by language (`id` vs `en` vs mixed) — multilingual embeddings often score `0.92` on English while silently dropping to `0.68` on Bahasa Indonesia queries.

## 11. Authoritative References
- NIST AI 600-1 (2024) — *Confabulation & Information Integrity* (`https://doi.org/10.6028/NIST.AI.600-1`).
- OWASP Top 10 for LLM Applications 2025 — `LLM08:2025` (Vector/Embedding Weaknesses) & `LLM09:2025` (Misinformation).
- RAGAS / TruLens RAG Triad Evaluation Methodology.

## 12. Limitations & When NOT to Use
- Offline RAG evaluation with static retrieved chunks does NOT verify end-to-end production serving ACL enforcement; verify pre-top-K tenant filtering independently in the serving database/vector store integration tests (`/shadow-auth`, `/shadow-search`).
