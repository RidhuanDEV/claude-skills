# 05. OWASP LLM 2025 Red-Teaming & NIST AI 600-1 Controls

## 1. Purpose & Activation Conditions
Red-team GenAI applications, RAG systems, and tool-calling agents against **OWASP Top 10 for Large Language Model Applications (2025 Edition)** and **NIST AI 600-1 (GenAI Profile, July 2024)**. Load when auditing AI security posture, designing adversarial probes, or validating pre-release GenAI safety controls.

## 2. Prerequisites
- Inventory of all model providers, prompts, RAG data sources, MCP/tool scopes, and output sinks (`SQL`, `HTML`, `shell`, external HTTP).

## 3. Technical Principles & Constraints
- **System Prompts Are NOT Security Boundaries (`LLM07:2025`):** Never store secrets, API keys, tenant checks, or pricing/authorization logic inside system prompts — enforce them deterministically in server code.
- **Zero Unsafe Output Sinks (`LLM05:2025`):** Treat EVERY LLM token as untrusted user input. Never pass model output directly into `eval()`, `exec()`, `shell=True`, raw SQL string interpolation, or unsanitized `dangerouslySetInnerHTML`.
- **Mandatory Separation of Instructions vs Untrusted Data (`LLM01:2025`):** Wrap retrieved RAG chunks and external tool outputs in explicit structural delimiters and enforce schema validation + least-privilege tool scopes (`LLM06:2025`) with HITL approval for financial/destructive actions.
- **NIST AI 600-1 Lifecycle Mapping (`Govern`, `Map`, `Measure`, `Manage`):** Address all 12 GenAI risk domains — especially Confabulation (`LLM09`), Data Privacy (`LLM02`), Information Security (`LLM01–LLM08`), Value-Chain / MCP Provenance (`LLM03`), and Unbounded Consumption (`LLM10`).

## 4. Architecture & Implementation
| ID | OWASP LLM 2025 Category | Core Attack / Failure Mode | Mandatory Technical Defense & Red-Team Probe |
| :--- | :--- | :--- | :--- |
| `LLM01:2025` | **Prompt Injection** | Direct jailbreaks or indirect directives inside PDFs/webpages/emails hijack agent behavior | Delimit untrusted context; validate structured JSON schema; test indirect injection inside retrieved docs |
| `LLM02:2025` | **Sensitive Info Disclosure** | PII, secrets, or cross-tenant records leak in prompt/output/memorization | Pre-prompt PII redaction/tokenization; output DLP scanner; zero training on raw customer PII |
| `LLM03:2025` | **Supply Chain** | Compromised model weights (`pickle`), LoRA adapters, or untrusted MCP servers | Pin model revisions/digests, require `safetensors`, verify MCP provenance & SBOM (`/shadow-supplychain`) |
| `LLM04:2025` | **Data & Model Poisoning** | Tampered corpus docs or feedback loops poison retrieval/fine-tuning | Corpus ingestion provenance checks, moderation filters, post-ingest golden regression suite |
| `LLM05:2025` | **Improper Output Handling** | Model output reaches SQL, shell, `eval`, or DOM -> `SQLi`/`RCE`/`XSS` | Parameterized SQL, `execFile` (`shell: false`), strict Zod/Pydantic parsing, HTML sanitization |
| `LLM06:2025` | **Excessive Agency** | Unrestricted write/delete/payment/email tools executed without confirmation | Read/write tool split, server-side RBAC per tool, idempotency keys, mandatory HITL confirmation |
| `LLM07:2025` | **System Prompt Leakage** | Adversarial extraction reveals internal instructions or hidden thresholds | Keep secrets/auth strictly in backend code; assume system prompt text can be read by users |
| `LLM08:2025` | **Vector & Embedding Weaknesses** | Cross-tenant retrieval leak or adversarial nearest-neighbor poisoning | Mandatory pre-top-K `tenant_id` & ACL filter inside vector query; `100%` isolation gate |
| `LLM09:2025` | **Misinformation** | Confident hallucination or fabricated document citations | Quote-anchored grounding, claim-level verification, calibrated `"Insufficient evidence"` abstention |
| `LLM10:2025` | **Unbounded Consumption** | Denial of Wallet via giant prompts, recursive agent loops, or uncapped reasoning tokens | Cap `max_output_tokens`, `thinking_budget`, max agent turns, per-tenant quotas & timeouts (`/shadow-finops`) |

Offline static red-team & sink check command:
```powershell
python "shadow-eval/scripts/ai_eval_gate.py" --redteam-check path/to/ai_service.py
python "shadow-eval/scripts/ai_eval_gate.py" --self-test
```

## 5. Platform / Vendor Variations
| Deployment Model | Highest-Risk OWASP Vectors | Priority Verification |
| :--- | :--- | :--- |
| **Internal Multi-Tenant RAG Copilot** | `LLM01` (indirect doc injection), `LLM08` (tenant leak), `LLM09` (confabulation) | Cross-tenant negative probes + indirect injection fixture inside indexed doc |
| **Customer-Facing Agent with MCP Tools** | `LLM05` (output sinks), `LLM06` (excessive agency), `LLM10` (wallet drain) | Action-trace HITL gate tests + per-user token/step budget caps |
| **Fine-Tuned / Self-Hosted Weights** | `LLM02` (memorization), `LLM03` (`pickle` RCE), `LLM04` (poisoning) | `safetensors`-only policy + dataset PII scrubbing + weight SHA pinning |

## 6. Decision Matrix & Trade-Offs
| Defense Layer | Stops Prompt Injection Alone? | Required in Production? | Why |
| :--- | :---: | :---: | :--- |
| **Prompt Hardening ("Ignore attacks")** | No (probabilistic only) | Helpful baseline | Easily bypassed by novel phrasing — never sole control |
| **Deterministic Tool RBAC + HITL + Safe Sinks** | **YES (blast-radius containment)** | **MANDATORY** | Prevents injection from causing unauthorized mutation or RCE even if model is tricked |
| **Input/Output Guardrail Classifier** | Partial (adds defense-in-depth) | Recommended for public apps | Monitor latency and false-positive refusal rate |

## 7. Real Production Scenario
An enterprise assistant executes `cursor.execute(f"SELECT * FROM invoices WHERE {llm_where_clause}")` generated by an LLM after adding `"Never write DROP TABLE"` to the system prompt. Red-teaming trivially bypasses the prompt with a `UNION SELECT` query leaking another tenant's invoices (`LLM01` + `LLM05`). Replacing free-form SQL with a typed structured filter DTO (`Zod`/`Pydantic` enum fields -> parameterized SQL + mandatory server `tenant_id` binding) eliminates the vulnerability structurally.

## 8. Failure Modes & Edge Cases
- **WRONG:** Relying solely on `"Do not reveal confidential info or call admin tools"` inside the system prompt to prevent `LLM02`/`LLM06`.
- **RIGHT:** Enforce tenant ACL pre-filtering in retrieval (`LLM08`), strip secrets before prompt assembly (`LLM02`), and enforce server-side tool authorization + HITL outside the LLM (`LLM06`).
- **WRONG:** Running aggressive live automated jailbreak fuzzing against a shared staging/production LLM endpoint without `L3` approval.
- **RIGHT:** Run static sink/red-team checks (`ai_eval_gate.py --redteam-check`) locally (`L1`) and obtain explicit Monarch `L3` approval with cost cap before live red-team sweeps.

## 9. Testing & Verification
- Execute `python shadow-eval/scripts/ai_eval_gate.py --self-test` and `--redteam-check` on every PR modifying prompts, tool schemas, or LLM output handlers.
- Maintain a versioned red-team probe pack covering `LLM01`, `LLM02`, `LLM05`, `LLM06`, `LLM08`, and `LLM10` with `100%` block rate on RCE/SQLi/cross-tenant/unapproved-financial sinks.

## 10. Operational Considerations
- Log blocked red-team/guardrail triggers (`rule_id`, `tenant_id`, `request_id` — NEVER raw sensitive PII) to security telemetry (`/shadow-observe`, `/shadow-sec`) to detect active probing campaigns.

## 11. Authoritative References
- OWASP GenAI Security Project — *OWASP Top 10 for Large Language Model Applications 2025* (`https://genai.owasp.org/llm-top-10/`).
- NIST — *Artificial Intelligence Risk Management Framework: Generative AI Profile (`NIST AI 600-1`, July 2024)* (`https://doi.org/10.6028/NIST.AI.600-1`).

## 12. Limitations & When NOT to Use
- Static sink scanning (`--redteam-check`) cannot detect subtle semantic prompt injections or novel jailbreaks in live model weights; pair with deterministic architectural containment (`LLM05`/`LLM06`/`LLM08`) and periodic authorized adversarial evaluations.
