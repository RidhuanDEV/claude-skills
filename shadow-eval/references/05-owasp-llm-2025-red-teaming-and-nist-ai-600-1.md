# 05. OWASP LLM 2026 & Agentic Top 10 Red-Teaming & NIST AI 600-1 Controls

## 1. Purpose & Activation Conditions
Red-team GenAI applications, RAG systems, and tool-calling agents against **OWASP Top 10 for LLM Applications (2026 edition, published 2026-08-04)**, the **OWASP Top 10 for Agentic Applications (for 2026)** (§4.1), and **NIST AI 600-1 (GenAI Profile, July 2024)**. IDs below use the 2026 numbering; the 2025 edition is superseded and its numbers differ (for example 2025 `LLM05` Improper Output Handling is now `LLM10`). Load when auditing AI security posture, designing adversarial probes, or validating pre-release GenAI safety controls.

## 2. Prerequisites
- Inventory of all model providers, prompts, RAG data sources, MCP/tool scopes, and output sinks (`SQL`, `HTML`, `shell`, external HTTP).

## 3. Technical Principles & Constraints
- **System Prompts Are NOT Security Boundaries (`LLM08:2026` Hidden Context Exposure — nearest 2026 entry to the superseded 2025 System Prompt Leakage; confirm against the 2026 document):** Never store secrets, API keys, tenant checks, or pricing/authorization logic inside system prompts — enforce them deterministically in server code.
- **Zero Unsafe Output Sinks (`LLM10:2026` Improper Output Handling):** Treat EVERY LLM token as untrusted user input. Never pass model output directly into `eval()`, `exec()`, `shell=True`, raw SQL string interpolation, or unsanitized `dangerouslySetInnerHTML`.
- **Mandatory Separation of Instructions vs Untrusted Data (`LLM01:2026`):** Wrap retrieved RAG chunks and external tool outputs in explicit structural delimiters and enforce schema validation + least-privilege tool scopes (`LLM03:2026` Excessive Agency) with HITL approval for financial/destructive actions.
- **NIST AI 600-1 Lifecycle Mapping (`Govern`, `Map`, `Measure`, `Manage`):** Address all 12 GenAI risk domains — especially Confabulation (`LLM07` Misinformation), Data Privacy (`LLM02`), Information Security (`LLM01`, `LLM03`, `LLM05`, `LLM08`–`LLM10`), Value-Chain / MCP Provenance (`LLM04` Supply Chain), and Unbounded Consumption (`LLM06`).

## 4. Architecture & Implementation
| ID | OWASP LLM 2026 Category | Core Attack / Failure Mode | Mandatory Technical Defense & Red-Team Probe |
| :--- | :--- | :--- | :--- |
| `LLM01:2026` | **Prompt Injection** | Direct jailbreaks or indirect directives inside PDFs/webpages/emails hijack agent behavior | Delimit untrusted context; validate structured JSON schema; test indirect injection inside retrieved docs |
| `LLM02:2026` | **Sensitive Info Disclosure** | PII, secrets, or cross-tenant records leak in prompt/output/memorization | Pre-prompt PII redaction/tokenization; output DLP scanner; zero training on raw customer PII |
| `LLM03:2026` | **Excessive Agency** | Unrestricted write/delete/payment/email tools executed without confirmation | Read/write tool split, server-side RBAC per tool, idempotency keys, mandatory HITL confirmation |
| `LLM04:2026` | **Supply Chain** | Compromised model weights (`pickle`), LoRA adapters, or untrusted MCP servers | Pin model revisions/digests, require `safetensors`, verify MCP provenance & SBOM (`/shadow-supplychain`) |
| `LLM05:2026` | **Data & Model Poisoning** | Tampered corpus docs or feedback loops poison retrieval/fine-tuning | Corpus ingestion provenance checks, moderation filters, post-ingest golden regression suite |
| `LLM06:2026` | **Unbounded Consumption** | Denial of Wallet via giant prompts, recursive agent loops, or uncapped reasoning tokens | Cap `max_output_tokens`, `thinking_budget`, max agent turns, per-tenant quotas & timeouts (`/shadow-finops`) |
| `LLM07:2026` | **Misinformation** | Confident hallucination or fabricated document citations | Quote-anchored grounding, claim-level verification, calibrated `"Insufficient evidence"` abstention |
| `LLM08:2026` | **Hidden Context Exposure** (nearest to superseded 2025 System Prompt Leakage; confirm against the 2026 document) | Adversarial extraction reveals internal instructions or hidden thresholds | Keep secrets/auth strictly in backend code; assume system prompt text can be read by users |
| `LLM09:2026` | **Vector & Embedding Weaknesses** | Cross-tenant retrieval leak or adversarial nearest-neighbor poisoning | Mandatory pre-top-K `tenant_id` & ACL filter inside vector query; `100%` isolation gate |
| `LLM10:2026` | **Improper Output Handling** | Model output reaches SQL, shell, `eval`, or DOM -> `SQLi`/`RCE`/`XSS` | Parameterized SQL, `execFile` (`shell: false`), strict Zod/Pydantic parsing, HTML sanitization |

### 4.1 OWASP Top 10 for Agentic Applications (for 2026) — Probe & Control Map
Source: `https://genai.owasp.org/resource/owasp-top-10-for-agentic-applications-for-2026/` (published 2025-12-09). Each item maps to an existing probe or control in this skill; none adds a new detector.

| ID | Agentic Risk | Existing Probe / Control in `/shadow-eval` |
| :--- | :--- | :--- |
| `ASI01` | **Agent Goal Hijack** | `ai_eval_gate.py` `LLM01_IGNORE_INSTRUCTIONS` / `LLM01_SYSTEM_OVERRIDE` probes + indirect-injection fixture inside retrieved docs (`LLM01` row above) |
| `ASI02` | **Tool Misuse and Exploitation** | Action-trace grading of argument schema & injection safety ([04](04-tool-use-and-agent-trace-evaluation.md)) + `LLM10_*` unsafe-sink rules (`LLM10` row) |
| `ASI03` | **Identity and Privilege Abuse** | Server-side RBAC per tool and `LLM03_EXCESSIVE_AGENCY` HITL rule (`LLM03` row); cross-tenant negative probes (`LLM09` row) |
| `ASI04` | **Agentic Supply Chain** | Model digest pinning, `safetensors`-only, MCP provenance & SBOM (`LLM04` row, `/shadow-supplychain`) |
| `ASI05` | **Unexpected Code Execution** | `LLM10_CODE_EXEC_SINK` / `LLM10_SHELL_EXEC_SINK` static sink probes (`LLM10` row) |
| `ASI06` | **Memory and Context Poisoning** | Corpus ingestion provenance + post-ingest golden regression suite (`LLM05` row); delimited untrusted context (`LLM01` row) |
| `ASI07` | **Insecure Inter-Agent Communication** | Treat every peer-agent message as untrusted tool output: structural delimiting + schema validation (§3); trace-grade the receiving agent's actions ([04](04-tool-use-and-agent-trace-evaluation.md)) |
| `ASI08` | **Cascading Failures** | Bounded `max_steps` / token / latency budgets in trace grading ([04](04-tool-use-and-agent-trace-evaluation.md)) + `LLM06` unbounded-consumption caps |
| `ASI09` | **Human-Agent Trust Exploitation** | HITL approval gate compliance in trace grading ([04](04-tool-use-and-agent-trace-evaluation.md)) + quote-anchored grounding and `"Insufficient evidence"` abstention (`LLM07` row) |
| `ASI10` | **Rogue Agents** | Deterministic tool RBAC + HITL + safe sinks (§6 containment layer) and blocked-trigger telemetry (§10) |

Offline static red-team & sink check command:
```powershell
python "shadow-eval/scripts/ai_eval_gate.py" --redteam-check path/to/ai_service.py
python "shadow-eval/scripts/ai_eval_gate.py" --self-test
```

## 5. Platform / Vendor Variations
| Deployment Model | Highest-Risk OWASP Vectors | Priority Verification |
| :--- | :--- | :--- |
| **Internal Multi-Tenant RAG Copilot** | `LLM01` (indirect doc injection), `LLM09` (tenant leak), `LLM07` (confabulation) | Cross-tenant negative probes + indirect injection fixture inside indexed doc |
| **Customer-Facing Agent with MCP Tools** | `LLM10` (output sinks), `LLM03` (excessive agency), `LLM06` (wallet drain) | Action-trace HITL gate tests + per-user token/step budget caps |
| **Fine-Tuned / Self-Hosted Weights** | `LLM02` (memorization), `LLM04` (`pickle` RCE), `LLM05` (poisoning) | `safetensors`-only policy + dataset PII scrubbing + weight SHA pinning |

## 6. Decision Matrix & Trade-Offs
| Defense Layer | Stops Prompt Injection Alone? | Required in Production? | Why |
| :--- | :---: | :---: | :--- |
| **Prompt Hardening ("Ignore attacks")** | No (probabilistic only) | Helpful baseline | Easily bypassed by novel phrasing — never sole control |
| **Deterministic Tool RBAC + HITL + Safe Sinks** | **YES (blast-radius containment)** | **MANDATORY** | Prevents injection from causing unauthorized mutation or RCE even if model is tricked |
| **Input/Output Guardrail Classifier** | Partial (adds defense-in-depth) | Recommended for public apps | Monitor latency and false-positive refusal rate |

## 7. Real Production Scenario
An enterprise assistant executes `cursor.execute(f"SELECT * FROM invoices WHERE {llm_where_clause}")` generated by an LLM after adding `"Never write DROP TABLE"` to the system prompt. Red-teaming trivially bypasses the prompt with a `UNION SELECT` query leaking another tenant's invoices (`LLM01` + `LLM10`). Replacing free-form SQL with a typed structured filter DTO (`Zod`/`Pydantic` enum fields -> parameterized SQL + mandatory server `tenant_id` binding) eliminates the vulnerability structurally.

## 8. Failure Modes & Edge Cases
- **WRONG:** Relying solely on `"Do not reveal confidential info or call admin tools"` inside the system prompt to prevent `LLM02`/`LLM03`.
- **RIGHT:** Enforce tenant ACL pre-filtering in retrieval (`LLM09`), strip secrets before prompt assembly (`LLM02`), and enforce server-side tool authorization + HITL outside the LLM (`LLM03`).
- **WRONG:** Running aggressive live automated jailbreak fuzzing against a shared staging/production LLM endpoint without `L3` approval.
- **RIGHT:** Run static sink/red-team checks (`ai_eval_gate.py --redteam-check`) locally (`L1`) and obtain explicit Monarch `L3` approval with cost cap before live red-team sweeps.

## 9. Testing & Verification
- Execute `python shadow-eval/scripts/ai_eval_gate.py --self-test` and `--redteam-check` on every PR modifying prompts, tool schemas, or LLM output handlers.
- Maintain a versioned red-team probe pack covering `LLM01`, `LLM02`, `LLM03`, `LLM06`, `LLM09`, and `LLM10` with `100%` block rate on RCE/SQLi/cross-tenant/unapproved-financial sinks.

## 10. Operational Considerations
- Log blocked red-team/guardrail triggers (`rule_id`, `tenant_id`, `request_id` — NEVER raw sensitive PII) to security telemetry (`/shadow-observe`, `/shadow-sec`) to detect active probing campaigns.

## 11. Authoritative References
- OWASP GenAI Security Project — *OWASP Top 10 for LLM Applications, 2026 edition* (`https://raw.githubusercontent.com/GenAI-Security-Project/GenAI-LLM-Top10/main/README.md`).
- OWASP GenAI Security Project — *OWASP Top 10 for Agentic Applications for 2026* (`https://genai.owasp.org/resource/owasp-top-10-for-agentic-applications-for-2026/`).
- NIST — *Artificial Intelligence Risk Management Framework: Generative AI Profile (`NIST AI 600-1`, July 2024)* (`https://doi.org/10.6028/NIST.AI.600-1`).

## 12. Limitations & When NOT to Use
- Static sink scanning (`--redteam-check`) cannot detect subtle semantic prompt injections or novel jailbreaks in live model weights; pair with deterministic architectural containment (`LLM10`/`LLM03`/`LLM09`) and periodic authorized adversarial evaluations.
