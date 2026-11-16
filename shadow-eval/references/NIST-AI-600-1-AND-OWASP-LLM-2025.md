# NIST AI 600-1 & OWASP Top 10 for LLM Applications (2025) Reference

> **Normative Sources**:
> - **OWASP Top 10 for Large Language Model Applications (2025 Edition)**: [genai.owasp.org/llm-top-10](https://genai.owasp.org/llm-top-10/)
> - **NIST AI 600-1 (AI RMF Generative AI Profile, July 2024)**: [doi.org/10.6028/NIST.AI.600-1](https://doi.org/10.6028/NIST.AI.600-1)

---

## 1. OWASP Top 10 for LLM Applications (2025) — Engineering Controls & Red-Team Probes

| ID | Category (2025) | Core Attack / Failure Mode | Required Engineering Defense & Eval Probe |
|---|---|---|---|
| `LLM01:2025` | **Prompt Injection** | Direct jailbreaks or indirect instructions hidden inside RAG documents, emails, or web pages override system directives | Separate instructions from untrusted data blocks; run indirect injection probes inside retrieved chunks; validate structured outputs against strict JSON Schema |
| `LLM02:2025` | **Sensitive Information Disclosure** | Model reveals PII, API keys, or confidential tenant records from training/fine-tuning data or context | Pre-prompt PII redaction/tokenization; output DLP scanner; zero training on unredacted customer PII |
| `LLM03:2025` | **Supply Chain Vulnerabilities** | Compromised base weights, LoRA adapters, datasets, embeddings, or third-party MCP servers | Pin model hashes/revisions, use `safetensors` (never untrusted `pickle`), verify MCP server provenance and SBOM |
| `LLM04:2025` | **Data and Model Poisoning** | Tampered RAG corpus documents or training sets introduce backdoors or biased answers | Document ingestion provenance checks, moderation/integrity filters before indexing, Golden Dataset regression runs after corpus updates |
| `LLM05:2025` | **Improper Output Handling** | Unvalidated LLM output passed to SQL, shell, `eval()`, `exec()`, or DOM (`XSS`/`SQLi`/`SSRF`/`RCE`) | Parameterized DB queries, schema validation (`Zod`/`Pydantic`), strict HTML sanitization, zero `eval`/`exec`/`shell=True` on model strings |
| `LLM06:2025` | **Excessive Agency** | Agent holds unrestricted write/delete/payment/email tools without confirmation or scope checks | Read/write tool split, server-side RBAC on every tool call, idempotency keys, mandatory Human-in-the-Loop (HITL) approval on high-impact mutations |
| `LLM07:2025` | **System Prompt Leakage** | Adversarial prompts extract hidden instructions, internal APIs, or policy thresholds | Never treat system prompts as security boundaries; keep secrets/auth/business logic in code, not prompt text |
| `LLM08:2025` | **Vector and Embedding Weaknesses** | Cross-tenant retrieval leakage, missing ACL pre-filtering, or poisoned vector neighbors | Enforce mandatory `tenant_id` & ACL pre-filtering inside vector query (`WHERE tenant_id = ?`), test 100% cross-tenant isolation |
| `LLM09:2025` | **Misinformation** | Confabulation / hallucination presented confidently or fabricated document citations | Grounding/Faithfulness scoring against retrieved chunks, exact citation ID verification, explicit `"Insufficient evidence"` fallback |
| `LLM10:2025` | **Unbounded Consumption** | Denial of Wallet via massive prompts, recursive agent loops, or uncapped reasoning/output tokens | Enforce `max_output_tokens`, bounded `thinking_budget`, per-tenant token quotas, max agent steps, and request timeouts |

---

## 2. NIST AI 600-1 (GenAI Profile) — 12 Risk Categories & Measure/Manage Mapping

NIST AI 600-1 extends **NIST AI RMF 1.0 (`AI 100-1`)** functions (`Govern`, `Map`, `Measure`, `Manage`) across 12 GenAI risk domains:
1. **CBRN Information or Capabilities** — pre-deployment safety filters and refusal evals.
2. **Confabulation / Hallucination** — RAG Faithfulness, citation checks, abstention calibration.
3. **Dangerous, Violent, or Hateful Content** — input/output guardrails and adversarial testing.
4. **Data Privacy** — PII scrubbing, memorization audits, cross-tenant ACLs (pairs with `/shadow-privacy`).
5. **Environmental Impacts** — model right-sizing and caching efficiency (pairs with `/shadow-finops`).
6. **Harmful Bias & Homogenization** — demographic parity / contrast probes on decision outputs.
7. **Human-AI Configuration** — clear AI disclosure, HITL oversight, and avoiding automation bias.
8. **Information Integrity** — provenance watermarking and source-grounded citations.
9. **Information Security** — `LLM01`–`LLM08` adversarial red-teaming.
10. **Intellectual Property** — training/retrieval license attribution and verbatim regurgitation checks.
11. **Obscene, Degrading, and/or Abusive Content** — safety classifiers.
12. **Value Chain and Component Integration** — third-party API/model/MCP dependency governance.

---

## 3. Quantitative RAG & Agent Release Gate Thresholds

| Metric | Formula / Definition | Typical Production Gate |
|---|---|---|
| **Tenant ACL Isolation** | `1 - (cross_tenant_chunks / total_retrieved_chunks)` | **100.0%** (Zero tolerance) |
| **Citation Integrity** | `valid_citations_in_retrieved_ids / total_citations_emitted` | **100.0%** (Zero fabricated IDs) |
| **Faithfulness / Groundedness** | `supported_claims / total_claims_in_answer` | **>= 0.90** (Critical domains: >= 0.95) |
| **Context Recall@K** | `retrieved_expected_chunks / total_expected_chunks` | **>= 0.85** |
| **Out-of-Scope Abstention Accuracy** | `correct_refusals / total_unanswerable_probes` | **>= 0.95** |
| **Red-Team Block Rate (`LLM01`/`LLM05`/`LLM06`)** | `blocked_or_safe_adversarial_probes / total_adversarial_probes` | **>= 0.95** (100% on RCE/SQLi/unapproved financial sinks) |
