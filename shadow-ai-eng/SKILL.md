---
name: shadow-ai-eng
description: "Production AI, LLM & Agent Systems Engineering. Use when building LLM features, structured outputs, tool-calling agents, streaming token UX, multi-provider AI gateways, prompt versioning, context compaction, or MCP servers. Do NOT use for RAG evaluation/red-teaming (/shadow-eval), search index tuning (/shadow-search), or token billing audits (/shadow-finops)."
---

# Shadow AI Engineering (`/shadow-ai-eng`) — Production LLM & Agent Systems

Use this skill when **building** production AI/LLM features, agent workflows, tool-calling pipelines, streaming chat/copilot UIs, or MCP servers. Pair with `/shadow-eval` for evaluation & OWASP LLM red-teaming, `/shadow-search` for hybrid retrieval/ACL, and `/shadow-finops` for token cost governance.

## 1. Core Production AI Engineering Non-Negotiables

1. **Structured Output & Schema Boundary Validation:** Never parse LLM JSON with brittle regexes or trust raw model output. Use provider native Structured Outputs / JSON Schema constrained decoding + validate every response and tool argument with a strict runtime schema (`Zod` / `Pydantic`) at the boundary before passing into application logic.
2. **Safe Tool-Calling & Human-in-the-Loop (HITL) Boundaries:**
   - Every tool MUST declare narrow typed arguments, explicit timeouts, idempotency keys (for mutating tools), and server-derived `tenantId`/`actorSub` (NEVER let the LLM choose or override `tenantId` or `userId`!).
   - High-impact tools (financial transfers, deletes, external emails, DB writes) MUST pause for explicit human confirmation before execution.
3. **Resilient Multi-Provider & Streaming Architecture:**
   - Stream user-facing generations over SSE/WebSocket with `AbortController` cancellation, bounded output ceilings (`max_output_tokens`, `thinking_budget`), and graceful partial-state recovery if the stream drops mid-response.
   - Protect outbound LLM calls with per-request timeouts, bounded exponential backoff on `429`/`503`, circuit breakers, and explicit model fallback tiers (never infinite retry loops!).
4. **Prompt Engineering as Versioned Code:**
   - Keep system instructions **strictly static at the prefix** to maximize provider prefix prompt caching (never inject volatile timestamps/UUIDs at line 1 of the system prompt!).
   - Separate untrusted user/retrieved content with explicit structural delimiters (treat retrieved documents and tool outputs strictly as **data, never instructions**).
   - Version prompts alongside code/fixtures and gate prompt changes through `/shadow-eval` before rollout.
5. **Context Window Hygiene & MCP Server Craft:**
   - Enforce deterministic context budgets (sliding window + structured summary compaction + bounded tool-output truncation) so long sessions never silently truncate critical instructions or blow up latency/cost.
   - For MCP servers: keep tool schemas narrow, validate every input fail-closed, never log secrets/PII to `stdout` (breaks JSON-RPC stdio transport — log diagnostics strictly to `stderr`!), and separate read-only vs mutating tools clearly.

## 2. Deep Architecture Reference (Load On-Demand)

- For concrete patterns covering **Structured Outputs & Tool-Calling Loops, Streaming SSE/UX Cancellation, Multi-Provider Gateways & Semantic Caching, Context Compaction, and MCP Server Engineering** -> read [Production AI & Agent Architecture](references/agent-and-llm-architecture.md).
- For evaluation metrics (`Faithfulness`, `Context Recall`, OWASP LLM 2025 red-team) -> hand off to `/shadow-eval`.
- For hybrid retrieval & tenant ACL pre-filtering -> hand off to `/shadow-search`.
- For FOCUS token cost & caching telemetry -> hand off to `/shadow-finops`.
