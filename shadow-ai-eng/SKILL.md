---
name: shadow-ai-eng
description: "Production AI, LLM & Agent Systems Engineering Specialist. Use when building multi-provider LLM gateways, JSON Schema structured outputs, safe tool-calling agents with HITL, context compaction, hybrid RAG runtime & prefix caching, cancellable SSE streaming UX, or hardened MCP servers. Do NOT use for RAG evaluation/red-teaming (/shadow-eval), search index tuning (/shadow-search), or token billing audits (/shadow-finops)."
---

# Shadow AI Engineering (`/shadow-ai-eng`) — Production LLM, Agents & MCP Systems

Use this skill whenever the **Monarch** builds or troubleshoots production LLM features, multi-provider AI gateways, structured outputs, tool-calling agents, context compaction, hybrid RAG runtimes, streaming SSE chat UX, or hardened MCP servers.

## 1. Core Production AI Engineering Non-Negotiables

1. **Zero-Trust Structured Outputs & Tool Boundaries:** Use provider native Structured Outputs + runtime `Zod`/`Pydantic` validation (zero regex JSON parsing or `as Type` casts). **NEVER** expose `tenantId`, `userId`, `rawSql`, or `shellCommand` as LLM tool args — inject `session.tenantId` server-side, wrap untrusted RAG/tool outputs as passive data, and require **HITL confirmation** + `idempotency_key` on mutating/financial tools.
2. **Bounded Gateways, Loops & Token Caps:** Pin immutable model snapshots behind an `AiGatewayPort` with explicit timeouts, bounded Full-Jitter retries, circuit breakers, eval-verified fallbacks, `MAX_STEPS <= 8–10` loop guards, and hard `max_output_tokens` + `thinking_budget` ceilings.
3. **Static Prefix Prompt Caching & Context Compaction:** Keep `[Static System + Tool Schemas]` strictly byte-identical at the prefix (never inject timestamps/UUIDs at line 1!), truncate giant tool outputs, compact long histories without dropping position 0, and scope memory strictly by `(tenantId, userId)`.
4. **Cancellable SSE Streaming & Stdio-Clean MCP:** Emit `X-Accel-Buffering: no` + `Cache-Control: no-cache, no-transform` + `AbortController` linked to client disconnect. For `stdio` MCP servers: keep `stdout` 100% JSON-RPC only (redacted logs strictly to `stderr`), enforce canonical `realpathSync` path jails, and exit cleanly on `stdin` EOF (`Rule #29`).
5. **Cross-Skill Ownership:** Delegate retrieval indexing/ranking to `/shadow-search`, RAG/agent evals & OWASP LLM red-teaming to `/shadow-eval`, and FOCUS token-cost governance to `/shadow-finops`.

## 2. Deterministic Verification CLI & Scenario Benchmarks

Run offline checks (`L0`/`L1`, zero LLM API calls) before claiming `VERIFIED-LOCAL`:
```powershell
python "shadow-ai-eng/scripts/ai_runtime_verifier.py" --self-test
python "shadow-ai-eng/scripts/ai_runtime_verifier.py" --check-tool-spec path/to/tools.json
python "shadow-ai-eng/scripts/ai_runtime_verifier.py" --check-prompt-layout path/to/prompt_cfg.json
python "shadow-ai-eng/scripts/ai_runtime_verifier.py" --check-mcp-config path/to/mcp_cfg.json
python -m unittest discover -s "shadow-ai-eng/tests" -v
```
Graded specialist scenarios live in [evaluations.md](evaluations.md) (8 scenarios covering slow RAG TTFT + indirect tool injection, LLM-supplied `tenantId`/`rawSql`, broken prefix caching, uncancelled SSE streams, context compaction, and stdio MCP stdout corruption).

## Reference Guide

Load **only** the 1–2 modules matching the active subtask (never load all 6 at once):

| Task / Scenario | Tier | Load Reference |
| :--- | :--- | :--- |
| Multi-provider AI gateways, pinned models, circuit breakers, eval-verified fallbacks & quotas | CORE | [references/01-llm-app-architecture-and-gateways.md](references/01-llm-app-architecture-and-gateways.md) |
| Structured Outputs, Zod/Pydantic validation, server-injected `tenantId`, HITL & untrusted tool outputs | CORE | [references/02-structured-outputs-and-tool-trust-boundaries.md](references/02-structured-outputs-and-tool-trust-boundaries.md) |
| Bounded agent step loops (`MAX_STEPS`), context compaction, tool truncation & tenant memory privacy | CORE | [references/03-agent-state-compaction-and-memory-privacy.md](references/03-agent-state-compaction-and-memory-privacy.md) |
| Hybrid RAG runtime, static prefix prompt caching, `<retrieved_context>` delimiters & 5-stage TTFT | ADVANCED | [references/04-hybrid-rag-runtime-and-prompt-caching.md](references/04-hybrid-rag-runtime-and-prompt-caching.md) |
| Cancellable SSE streaming (`AbortController`), Nginx zero-buffering headers & typed stream frames | ADVANCED | [references/05-streaming-sse-ux-and-cancellation.md](references/05-streaming-sse-ux-and-cancellation.md) |
| Hardened stdio/HTTP MCP servers (`stderr` logs, `realpathSync` jail, EOF exit) & incident triage | SPECIALIST | [references/06-mcp-server-engineering-and-troubleshooting.md](references/06-mcp-server-engineering-and-troubleshooting.md) |

Do not load unrelated references unnecessarily.
