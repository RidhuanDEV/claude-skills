# 02. AI/LLM Token Economics, Prefix Prompt Caching & Thinking/Output Token Caps

## 1. Purpose & Activation Conditions
Use this playbook when estimating, auditing, or optimizing production **LLM, RAG, and AI Agent token costs**. Unbounded reasoning/thinking tokens and cache-busting dynamic prompt prefixes routinely inflate production AI bills by **`5x–15x`** without improving answer quality—and violate **`OWASP LLM06:2026` (Unbounded Consumption)**.

Activate this playbook when:
- Calculating monthly LLM API spend across input tokens, cached prefix discounts, visible output tokens, and hidden reasoning/thinking tokens (`finops_cost_auditor.py --estimate-llm`).
- Diagnosing why prompt cache hit rates collapsed to `0%` despite identical system instructions.
- Designing multi-tier model routing, Batch API offloading, and strict per-route token budgets alongside `/shadow-ai-eng`.

## 2. Prerequisites
- Target provider pricing table (`R_in` input rate per 1M tokens, `R_out` output/thinking rate per 1M tokens, cached input discount `d_cache`), expected daily calls, and average token distribution (`T_in`, `T_out`, `T_think`).
- Deterministic calculator & static prompt auditor: [`../scripts/finops_cost_auditor.py`](../scripts/finops_cost_auditor.py).
- Note: A standalone LLM token-cost estimate needs **ZERO** Kubernetes cluster audit — keep scope right-sized!

## 3. Technical Principles & Constraints
1. **Billing Reality: Thinking / Reasoning Tokens Are Billed at the Output Rate**:
   On frontier reasoning models (Gemini thinking, Claude extended thinking, OpenAI o-series/GPT-5), hidden internal thinking tokens ($T_{\text{think}}$) are billed at the **Output Token rate** ($R_{\text{out}}$, typically `3x–6x` higher than $R_{\text{in}}$):
   $$\text{Monthly Cost} = 30 \times N_{\text{calls/day}} \times \left[ \frac{T_{\text{in}}(1 - h)R_{\text{in}} + T_{\text{in}} h R_{\text{in}}(1 - d_{\text{cache}}) + (T_{\text{out}} + T_{\text{think}})R_{\text{out}}}{10^6} \right]$$
   Omitting $T_{\text{think}}$ from FinOps models causes `2x–5x` invoice shocks on launch week!
2. **Prefix Prompt Caching Discipline (`75%–95%` Input Discount)**:
   - Place **100% static content FIRST** in every request: `[System Prompt] -> [Stable Tool Definitions] -> [Shared Few-Shot / Reference Docs]`.
   - Place **all dynamic per-request variables LAST** (inside the user turn): `current_timestamp`, `request_id`, `user_id`, random UUIDs, or live RAG chunks.
   - Injecting `datetime.now()` or `Date.now()` into the system prompt prefix invalidates the KV/prefix cache on **100% of calls**, immediately destroying `75%–95%` cached input savings!
3. **Mandatory Output & Thinking Token Caps (`OWASP LLM06:2026` Unbounded Consumption)**:
   - Every production LLM route MUST set explicit `max_output_tokens` / `max_completion_tokens` AND bounded `thinking_budget` (or `reasoning_effort`) matched to route complexity, plus hard loop-iteration caps on tool-calling agents (`max_steps <= 6–10`).
4. **5 High-Leverage Token Cost Levers**:
   1. **Prefix Prompt Caching** (static prefix -> `75%–95%` off cached input).
   2. **Output & Thinking Caps** (prevents runaway reasoning loops).
   3. **Complexity-Based Model Routing** (frontier reasoning for planning/RCA; fast workhorse/flash models for extraction, classification, and formatting — often `5x–20x` cheaper).
   4. **Deterministic Short-Circuiting** (regex, SQL, BM25, schema validators run FIRST at `$0.00`; invoke an LLM only when deterministic logic cannot resolve the query).
   5. **Asynchronous Batch APIs** (nightly evals, document indexing, bulk summarization -> `~50%` discount).

## 4. Architecture & Implementation
### Deterministic Monthly Token Cost Estimator (`finops_cost_auditor.py`)
```powershell
python "shadow-finops/scripts/finops_cost_auditor.py" --estimate-llm `
  --calls-per-day 50000 --input-tokens 8000 --output-tokens 600 `
  --thinking-tokens 1200 --cache-hit-rate 0.80 `
  --input-rate 1.50 --output-rate 7.50 --cached-discount 0.90
```

### Strict TypeScript Cache-Safe Prompt Builder & Route Budget Guard
```typescript
export type LlmRouteTier = 'FAST_EXTRACTION' | 'STANDARD_CHAT' | 'DEEP_REASONING';

export interface LlmBudgetPolicy {
  readonly maxOutputTokens: number;
  readonly maxThinkingTokens: number;
  readonly maxAgentSteps: number;
}

export const ROUTE_TOKEN_BUDGETS: Readonly<Record<LlmRouteTier, LlmBudgetPolicy>> = {
  FAST_EXTRACTION: { maxOutputTokens: 512, maxThinkingTokens: 0, maxAgentSteps: 1 },
  STANDARD_CHAT: { maxOutputTokens: 1500, maxThinkingTokens: 1024, maxAgentSteps: 4 },
  DEEP_REASONING: { maxOutputTokens: 4096, maxThinkingTokens: 4096, maxAgentSteps: 8 },
};

export interface CacheSafePromptMessages {
  readonly staticSystemPrefix: string;
  readonly dynamicUserMessage: string;
}

export function buildCacheSafeMessages(
  staticPolicyText: string,
  requestIsoTimestamp: string,
  requestId: string,
  userQuestion: string,
): CacheSafePromptMessages {
  // Dynamic metadata stays STRICTLY in the trailing user message so system prefix stays cache-hot
  return {
    staticSystemPrefix: staticPolicyText,
    dynamicUserMessage: `[meta timestamp=${requestIsoTimestamp} requestId=${requestId}]\n${userQuestion}`,
  };
}
```

## 5. Platform / Vendor Variations
- **Anthropic Claude (`cache_control: { type: "ephemeral" }`)**: Explicit cache breakpoints on system + tools + static context; minimum prefix size threshold (`1,024`–`2,048` tokens depending on model) and 5m/1h TTL write premium vs `90%` read discount.
- **Google Gemini (Implicit & Explicit Context Caching)**: Stable prefix benefits from implicit caching automatically, while high-reuse shared knowledge bases (`>= 32k` tokens) can pin explicit `CachedContent` TTLs (account for storage-hour cost vs read savings!).
- **OpenAI / Azure OpenAI**: Automatic prefix caching on `>= 1,024` identical leading tokens (stepped in 128-token increments); keep tool JSON schema key ordering 100% deterministic across deploys!

## 6. Decision Matrix & Trade-Offs
| Optimization Lever | Typical Savings | Latency / Quality Trade-Off | Recommendation |
| :--- | :--- | :--- | :--- |
| **Static Prefix Prompt Caching** | `50%–90%` on input tokens | **Faster TTFT**, zero quality loss | **Always Enable First** |
| **Thinking Token Cap + Model Tier Routing** | `40%–80%` on output spend | Must validate quality on golden eval set (`/shadow-eval`) | High-ROI production standard |
| **Async Batch API (`24h` SLA)** | `50%` across input & output | Non-interactive latency | Mandatory for offline indexing/evals/bulk tags |
| **Deterministic Pre-Filter** | `100%` on bypassed calls | Zero latency, deterministic | Always short-circuit trivial lookups before LLM |

## 7. Real Production Scenario
**Context:** A customer-support RAG copilot burned `$14,800/mo` at `40,000` calls/day despite enabling prompt caching and routing simple FAQ lookups to a frontier reasoning model with unbounded thinking tokens.
**FinOps Audit (`finops_cost_auditor.py --audit .`):** Detected `f"Current time: {datetime.now().isoformat()}"` inside line 1 of `SYSTEM_PROMPT` (crushing cache hit rate to `0%`) and missing `max_output_tokens`/`thinking_budget` (averaging `3,400` hidden thinking tokens per trivial FAQ!).
**Impact:** Moving the timestamp to the user message (`84%` cache hit rate), capping thinking tokens (`0` for FAQ tier, `1,500` for escalations), and routing 75% of queries to a fast workhorse model slashed spend from **`$14,800/mo` -> `$2,650/mo` (`-82%`)** while cutting `p95` latency by `1.9s` with zero drop in `/shadow-eval` faithfulness score.

## 8. Failure Modes & Edge Cases
- **WRONG (Injecting `Date.now()`, `uuid()`, or per-user memory into the top of `system_prompt` and leaving `max_output_tokens` unset):** Permanently busts prefix KV caching (`0%` hit rate) and invites `OWASP LLM06:2026` Unbounded Consumption runaway token exhaustion attacks.
  **RIGHT:** Freeze static instructions/tools at the top of the prompt, append dynamic timestamps/user state at the end, and enforce strict `max_output_tokens`, `maxThinkingTokens`, and `maxAgentSteps` per route.
- **WRONG (Re-ordering tool JSON keys dynamically on every request via unsorted dict iteration):** Silently changes prefix byte hash and invalidates prompt caching across worker replicas.
  **RIGHT:** Serialize tool schemas deterministically (`sort_keys=True`) at process startup.

## 9. Testing & Verification
- Run `python shadow-finops/scripts/finops_cost_auditor.py --audit .` and `--self-test` (`9/9` probes catching cache-busting dynamic prefixes & unbounded LLM outputs).
- Verify any model-tier downgrade or thinking-budget reduction against an offline golden dataset (`/shadow-eval`) before rolling out to 100% of users.

## 10. Operational Considerations
- Log `prompt_tokens`, `cached_input_tokens`, `output_tokens`, `thinking_tokens`, `model_id`, and `route_tier` as structured metrics (`/shadow-observe`) so cache-hit-rate drops (`< 60%`) trigger immediate FinOps alerts before month-end billing surprises!

## 11. Authoritative References
- **OWASP Top 10 for LLM Applications 2026** — *LLM06:2026 Unbounded Consumption* (`https://raw.githubusercontent.com/GenAI-Security-Project/GenAI-LLM-Top10/main/README.md`).
- **FinOps Foundation** — *FinOps for AI* (`https://www.finops.org/`).
- **Shadow FinOps Auditor** — [`../scripts/finops_cost_auditor.py`](../scripts/finops_cost_auditor.py).

## 12. Limitations & When NOT to Use
- **Do NOT use** `/shadow-finops` to build RAG hybrid search or LLM gateway retry plumbing — implement architecture in `/shadow-ai-eng` and quality benchmarks in `/shadow-eval`.
- **Do NOT claim** exact provider savings without plugging verified current provider rates (`R_in`, `R_out`, `d_cache`) into `--estimate-llm` (rates evolve frequently).
