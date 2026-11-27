# 01. LLM Application Architecture & Multi-Provider Gateways

## 1. Purpose & Activation Conditions
Design resilient, version-pinned LLM application architectures and multi-provider AI gateways with bounded timeouts, circuit breakers, fallback tiers, and per-tenant quotas. Load when integrating OpenAI/Anthropic/Gemini/local vLLM endpoints or hardening LLM reliability in production.

## 2. Prerequisites
- Clear separation of concerns: `/shadow-ai-eng` owns LLM runtime/gateway; `/shadow-search` owns retrieval ranking; `/shadow-eval` owns quality/red-team gates; `/shadow-finops` owns token cost accounting.

## 3. Technical Principles & Constraints
- **Treat Every LLM Provider as an Untrusted, Variable-Latency External Service:** Never call provider SDKs scattered across UI routes with unbounded timeouts or default retries. Centralize calls behind an internal **`AiGatewayPort`** enforcing:
  1. **Pinned Model Snapshots:** Pin exact immutable version IDs (never floating `latest` aliases in regulated/tested production paths — silent model swaps break structured outputs and evals!).
  2. **Explicit Timeouts & Bounded Retries:** Set TTFT/total timeouts (`<= 30s` non-streaming, `<= 15s` TTFT streaming), retry ONLY `408`/`429` (honoring `Retry-After`)/`502`/`503`/`504` max `2` times with Full Jitter, and NEVER retry `400`/`401`/`403`!
  3. **Circuit Breaker & Verified Fallback Tiers:** Trip provider circuit breaker on sustained `5xx`/`429` bursts and route ONLY to an **eval-verified** fallback model (confirming structured-output & safety parity via `/shadow-eval` beforehand!).
  4. **Per-Tenant Token & Cost Quotas (`OWASP LLM06:2026` Unbounded Consumption):** Enforce per-tenant rate limits, `max_output_tokens`, and `thinking_budget` caps at the gateway before forwarding upstream.
- **Prompt & Model Version Governance:** Store prompt templates as versioned code in Git (`prompt_id`, `prompt_version`, `model_id`, `temperature`, `schema_hash`) and log these exact coordinates on every trace (`shadow-observe`) so quality regressions bisect cleanly!

## 4. Architecture & Implementation
```typescript
export interface LlmModelTier {
  readonly provider: 'anthropic' | 'google' | 'openai' | 'local_vllm';
  readonly pinnedModelId: string;
  readonly maxOutputTokens: number;
  readonly timeoutMs: number;
}

export interface GatewayCallResult {
  readonly text: string;
  readonly providerUsed: string;
  readonly modelUsed: string;
  readonly inputTokens: number;
  readonly outputTokens: number;
  readonly cachedInputTokens: number;
  readonly ttftMs: number;
}

export async function executeWithVerifiedFallback(
  tiers: readonly LlmModelTier[],
  isCircuitOpen: (provider: string) => boolean,
  invokeTier: (tier: LlmModelTier, signal: AbortSignal) => Promise<GatewayCallResult>,
  onTransientFailure: (provider: string) => void
): Promise<GatewayCallResult> {
  let lastErr: unknown = new Error('NO_HEALTHY_LLM_TIER');
  for (const tier of tiers) {
    if (isCircuitOpen(tier.provider)) continue;
    try {
      return await invokeTier(tier, AbortSignal.timeout(tier.timeoutMs));
    } catch (err: unknown) {
      lastErr = err;
      onTransientFailure(tier.provider);
    }
  }
  throw lastErr;
}
```

## 5. Platform / Vendor Variations
| Gateway Strategy | Pros | Cons / Watch-Out |
| :--- | :--- | :--- |
| **Thin Internal `AiGatewayPort` (App-Owned)** | Zero extra network hop, full control over tenant quotas, PII redaction & OTel spans | You maintain provider SDK adapters |
| **Dedicated Proxy (LiteLLM / Portkey / Cloudflare AI Gateway)** | Unified logging, rate limits, fallback UI across teams | Extra operational hop; lock down proxy auth & verify zero unintended prompt logging! |

## 6. Decision Matrix & Trade-Offs (Model Routing)
| Task Profile | Recommended Tier | Why |
| :--- | :--- | :--- |
| **Classification, Extraction, Simple Summarization** | Fast/Small Model + Structured Output | 5x–15x cheaper & `< 500ms` TTFT |
| **Complex Reasoning, Code, Multi-Tool Planning** | Frontier Model + Bounded `thinking_budget` | Higher accuracy; cap reasoning tokens (`shadow-finops`) |
| **Regulated Specific PII (Healthcare/Gov)** | In-Country VPC / Private Endpoint / Self-Hosted vLLM | Satisfies `UU PDP Pasal 56` localization (`shadow-privacy`) |

## 7. Real Production Scenario
During a regional primary-model `503` spike, a copilot app with no circuit breaker or fallback retries 10 times synchronously per user request, piling up 600 pending HTTP connections and crashing the API server. Adding `executeWithVerifiedFallback` (primary -> pre-evaluated secondary provider, `20s` timeout, circuit breaker `OPEN` after 5 consecutive `5xx`, and `max_output_tokens = 1500`) keeps chat availability at `99.95%` through the entire upstream outage.

## 8. Failure Modes & Edge Cases
- **WRONG:** Silently falling back from a frontier model to a tiny weak model on a complex financial tool-calling agent without running `/shadow-eval` on the fallback (fallback hallucinates tool arguments!).
- **RIGHT:** Only register fallback tiers whose safety/schema pass rates have been explicitly verified on your `/shadow-eval` golden set.
- **WRONG:** Leaving `temperature = 1.0` on deterministic extraction/routing tasks or omitting `max_output_tokens`.
- **RIGHT:** Set low temperature (`0.0–0.2`) for extraction/tool routing and ALWAYS set explicit `max_output_tokens`.

## 9. Testing & Verification
- Test gateway failover offline with mocked primary `503` -> assert secondary tier invoked within timeout and telemetry records `providerUsed`, `inputTokens`, `outputTokens`, `cachedInputTokens`, and `ttftMs`.

## 10. Operational Considerations
- Emit per-stage latency histograms (`gateway_ttft_ms`, `gateway_total_ms`) and token counters segmented by `(tenant_tier, feature_name, model_id)` for `/shadow-observe` and `/shadow-finops`.

## 11. Authoritative References
- NIST AI RMF (`AI 100-1` & `AI 600-1`) — *Manage & Govern* (`https://www.nist.gov/itl/ai-risk-management-framework`).
- OWASP Top 10 for LLM Applications 2026 — `LLM06:2026` Unbounded Consumption (`https://raw.githubusercontent.com/GenAI-Security-Project/GenAI-LLM-Top10/main/README.md`).

## 12. Limitations & When NOT to Use
- Do NOT use an LLM at all for deterministic tasks that pure code, SQL, regex, or a lightweight classical classifier solves faster, cheaper, and with 100% repeatability!
