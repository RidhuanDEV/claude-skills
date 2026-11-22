---
name: shadow-eval
description: "AI, LLM, RAG & Agent Evaluation and Red-Teaming. Use when evaluating RAG pipelines (Context Recall, Faithfulness, Citation Integrity), calibrating LLM judges, grading agent tool traces, testing prompt/regex heuristics with precision/recall probes, or red-teaming OWASP LLM 2025 & NIST AI 600-1."
---

# `/shadow-eval` — AI/LLM Evaluation, RAG Quality & GenAI Red-Teaming Gate

Use this skill whenever the **Monarch** evaluates RAG pipelines, prompt classifiers, LLM-as-a-Judge rubrics, or autonomous tool-calling agents, or gates an AI feature for Staging/Pre-UAT release.

## 1. Core Evaluation Principles & Non-Negotiables

1. **Stratified Holdout Hygiene:** Separate `dev_tuning` from immutable `blind_holdout` snapshots (`dataset_vX.Y`). Cover 6 archetypes: normal, ambiguous, out-of-scope abstention, negative/topic-switch contrast probes (`>= 5` precision + `>= 3` recall probes on heuristics), adversarial security, and incident regressions.
2. **Decoupled RAG Attribution & Zero-Tolerance Gates:** Separate Retrieval (`/shadow-search`: `Recall@K`, `MRR`, `NDCG`, pre-top-K tenant ACL) from Generation (`/shadow-eval`: claim-level Faithfulness, citation support, abstention calibration). Enforce **100% Tenant ACL Isolation**, **100% valid Citation IDs**, and non-compensatory safety gates.
3. **Deterministic Graders First, Calibrated Judges Second:** Use code graders for objective invariants (`ai_eval_gate.py`, action-trace assertions); calibrate any LLM-as-a-Judge with atomic binary rubrics at `temp=0`, swapped-order pairwise checks, and Cohen's kappa + false-pass-rate validation against human anchors.
4. **OWASP LLM 2025 & NIST AI 600-1 Containment:** Never treat system prompts as security boundaries (`LLM07`); block unsafe sinks (`LLM05`), require HITL/RBAC on mutating tools (`LLM06`), enforce token/step caps (`LLM10`), and grade complete agent tool trajectories — not final text alone.
5. **Honest Measurement & `L1` vs `L3` Boundary:** Offline deterministic scoring is `L1_SAFE_VERIFICATION`; paid live LLM judge/red-team sweeps are **`L3_RESOURCE_INTENSIVE`** requiring explicit Monarch approval + budget cap. Report unexecuted live evals explicitly as **`NOT_RUN`**.

## 2. Deterministic Verification CLI & Scenario Benchmarks

Run offline checks (`L0`/`L1`) before claiming `VERIFIED-LOCAL`:
```powershell
python "shadow-eval/scripts/ai_eval_gate.py" --self-test
python "shadow-eval/scripts/ai_eval_gate.py" --score-rag path/to/rag_eval_dataset.json
python "shadow-eval/scripts/ai_eval_gate.py" --compare-rag path/to/baseline.json path/to/candidate.json
python "shadow-eval/scripts/ai_eval_gate.py" --redteam-check path/to/src_or_prompt.py
python -m unittest discover -s "shadow-eval/tests" -v
```
- **Local RAG Gate Notes:** Typed samples declare `answerable`/`abstain`/`isolation`, stable sample ID, tenant, and language; keep unlabeled denominators visible. For `--compare-rag`, freeze `corpus_snapshot_id`, revision, and dev-ID inventory across both runs; only an independent reviewer supplies claim-to-document support mappings. For combined ACL snapshot + per-segment retrieval ranking comparisons, run `evals/compare_search_indexes.py`.
- Graded specialist scenarios live in [evaluations.md](evaluations.md) (8 scenarios).

## Reference Guide

Load **only** the 1–2 modules matching the active subtask (never load all 6 at once):

| Task / Scenario | Tier | Load Reference |
| :--- | :--- | :--- |
| Golden dataset taxonomy, `dev` vs `blind_holdout` splits, precision/recall contrast probes | CORE | [references/01-evaluation-taxonomy-and-scenario-design.md](references/01-evaluation-taxonomy-and-scenario-design.md) |
| Retrieval (`/shadow-search`) vs Generation RAG Triad, claim-level Faithfulness & ACL isolation | CORE | [references/02-rag-retrieval-and-faithfulness-metrics.md](references/02-rag-retrieval-and-faithfulness-metrics.md) |
| Deterministic vs LLM-as-a-Judge, position/verbosity bias, Cohen's kappa & false-pass calibration | ADVANCED | [references/03-graders-llm-judge-and-calibration.md](references/03-graders-llm-judge-and-calibration.md) |
| Agent tool-use & action-trace grading, indirect injection stubs, HITL approval & step budgets | ADVANCED | [references/04-tool-use-and-agent-trace-evaluation.md](references/04-tool-use-and-agent-trace-evaluation.md) |
| OWASP Top 10 for LLM 2025 (`LLM01`–`LLM10`) red-teaming & NIST AI 600-1 GenAI Profile | CORE | [references/05-owasp-llm-2025-red-teaming-and-nist-ai-600-1.md](references/05-owasp-llm-2025-red-teaming-and-nist-ai-600-1.md) |
| Paired baseline-vs-candidate diffs (McNemar), PII/benchmark leakage & honest `NOT_RUN` reports | OPERATIONAL | [references/06-regression-baselines-leakage-and-reporting.md](references/06-regression-baselines-leakage-and-reporting.md) |

Do not load unrelated references unnecessarily.
