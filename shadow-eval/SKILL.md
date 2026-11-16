---
name: shadow-eval
description: "AI, LLM, RAG & Agent Evaluation and Red-Teaming. Use when evaluating RAG pipelines (Context Recall, Faithfulness, Citation Integrity), testing prompt/regex heuristics with precision/recall probes, or red-teaming OWASP Top 10 for LLM 2025 & NIST AI 600-1."
---

# `/shadow-eval` — AI/LLM Evaluation, RAG Quality & GenAI Red-Teaming Gate

Use this skill whenever the **Monarch** invokes `/shadow-eval`, builds or modifies RAG pipelines, prompt classifiers, LLM-as-a-Judge workflows, or autonomous tool-calling agents, or prepares an AI feature for Staging/Pre-UAT release.

Grounded in authoritative AI risk and security standards documented in [`references/NIST-AI-600-1-AND-OWASP-LLM-2025.md`](references/NIST-AI-600-1-AND-OWASP-LLM-2025.md):
1. **OWASP Top 10 for Large Language Model Applications (2025 Edition)** (`LLM01:2025` through `LLM10:2025`) — `https://genai.owasp.org/llm-top-10/`.
2. **NIST AI RMF 1.0 (`AI 100-1`) & Generative AI Profile (`NIST AI 600-1`, July 2024)** — `https://doi.org/10.6028/NIST.AI.600-1` (`Govern`, `Map`, `Measure`, `Manage`).

---

## 1. The 5-Pillar AI & RAG Evaluation Workflow

### Pillar 1: Golden Dataset & Adversarial Contrast Set
- Curate representative real-world queries **plus** out-of-scope queries ("must refuse / I don't know"), multilingual/code-switched phrasing, and **topic-switch negative probes** (so follow-up heuristics or query rewriters do not pollute new topics).
- Tag every dataset item with `tenant_id`, `expected_chunk_ids`, `expected_claims`, and `must_refuse` boolean.

### Pillar 2: Retrieval & RAG Triad Metrics (`NIST AI 600-1 Measure`)
Measure retrieval and generation separately so failures are attributable:
- **Retrieval Layer**: `Recall@K`, `MRR@K`, `NDCG@K`, and **Tenant ACL Isolation = 100%** (zero cross-tenant chunks allowed in context, enforcing `LLM08:2025`).
- **Generation Layer (RAG Triad)**:
  1. **Context Relevance / Precision**: retrieved chunks actually contain evidence for the query.
  2. **Faithfulness / Groundedness**: every factual claim and citation in the answer is directly supported by retrieved context (prevents `LLM09:2025` hallucinations).
  3. **Answer Relevance**: response directly resolves the user's question without evading or drifting.

### Pillar 3: Heuristic, Regex & Router Falsification
Whenever an AI pipeline includes deterministic pre-filters, follow-up detectors, or intent routers:
- Run **Precision Probes** (>= 5 realistic inputs that must NOT trigger, e.g., non-anaphoric root words like `hanya`/`punya`/`bertanya` in Indonesian `-nya` filters).
- Run **Recall Probes** (>= 3 differently phrased inputs that MUST trigger).
- Never treat positive tests alone as proof of safety.

### Pillar 4: OWASP Top 10 for LLM Applications (2025) Red-Teaming
Verify technical defenses across all 10 categories:
- **`LLM01:2025` Prompt Injection**: Delimit untrusted retrieved/user text, validate tool schemas, and separate system instructions from retrieved content.
- **`LLM02:2025` Sensitive Information Disclosure** & **`LLM07:2025` System Prompt Leakage**: Redact PII/secrets before prompt assembly; never embed API keys or sensitive business thresholds in system prompts.
- **`LLM05:2025` Improper Output Handling**: Never pass raw LLM output to `eval()`, `exec()`, `shell=True`, raw SQL interpolation, or unsanitized HTML (`dangerouslySetInnerHTML`).
- **`LLM06:2025` Excessive Agency**: Enforce least-privilege tool scopes and mandatory **Human-in-the-Loop (HITL)** confirmation for financial, destructive, or external communication tools.
- **`LLM10:2025` Unbounded Consumption**: Cap `max_output_tokens`, `thinking_budget`, per-user rate limits, and max agent loop iterations.

### Pillar 5: Automated Eval & Red-Team Gate Script

```powershell
python "shadow-eval/scripts/ai_eval_gate.py" --self-test
python "shadow-eval/scripts/ai_eval_gate.py" --score-rag path/to/rag_eval_dataset.json
python "shadow-eval/scripts/ai_eval_gate.py" --redteam-check path/to/src_or_prompt.py
```

Report metrics with explicit **Claim -> Measured Score -> Threshold -> Untested Surfaces** rather than subjective "model sounds good" claims.

### Pillar 6: Search Retrieval Handoff, Dataset Splits & Independent Judge Calibration
- **`/shadow-search` Retrieval Handoff**: Split RAG evaluation strictly into Retrieval (`/shadow-search`: Recall@k, MRR, NDCG@k, pre-generation ACL tenant leak rate) vs Generation (`/shadow-eval`: faithfulness, citation grounding, refusal accuracy). Never tune prompts to mask broken retrieval ranking or missing RBAC filters.
- **Dataset Versioning & Held-Out Split**: Version every golden evaluation dataset with an immutable version tag/SHA hash (`dataset_vX.Y`). Enforce a strict **Dev/Tuning Split** vs **Blind Held-Out Split** so prompt engineers cannot overfit system prompts against the acceptance gate set.
- **Independent Judge Calibration**: Never rely on the same model family/temperature that generated outputs as an uncalibrated sole judge. Calibrate LLM-as-a-judge rubrics against human-labeled anchor items, mitigate positional/verbosity bias via swapped-order trials, and measure inter-rater agreement (e.g., Cohen's kappa or accuracy >= threshold) before promoting judge thresholds.
- **Execution Approval Boundary (`L1` vs `L3`)**: Offline deterministic `ai_eval_gate.py` scoring is bounded `L1_SAFE_VERIFICATION`, whereas high-cost live LLM judge sweeps or `--agent` batches (`>= $` API budget) are **`L3: RESOURCE_INTENSIVE`** requiring explicit 7-part Monarch approval with estimated token cost (`shadow-monarch/scripts/execution_approval_gate.py`).
