# AI-LLM — Building Production Features on Large Language Models

Use when building or reviewing features that call LLMs: chat, summarization, extraction, classification,
structured outputs, streaming UI, prompt architecture, and model routing.
For specialized depth, load the companion modules:
- **Advanced RAG, Hybrid Search, Reranking, Vector DBs & GraphRAG**: `reference/sub-RAG-VECTOR-KNOWLEDGE.md`
- **AI Agents, Subagents, Tool Design & MCP Servers**: `reference/AGENTS-MCP.md`
- **AI/GPU Infrastructure, vLLM/TGI/Ollama Serving, VRAM Sizing & LLM Gateways**: `reference/sub-AI-INFRA-SERVING.md`
- **Fine-Tuning (LoRA/QLoRA/DPO), Dataset Curation, Guardrails & LLMOps Tracing**: `reference/sub-LLM-FINETUNING-LLMOps.md`
- **Computer Vision, OCR, Whisper Speech & Media**: `reference/sub-VISION-OCR-MEDIA.md`

Model names, context sizes, prices, and SDK APIs evolve rapidly: verify the provider's current documentation and the
installed SDK version in the repository instead of relying on memory, and never invent model IDs or parameters.

## 1. Treat the LLM as an unreliable, non-deterministic dependency

- **Failure modes**: high latency, rate limits (`429`), overloaded servers (`503`/`529`), malformed JSON, refusal,
  context-window overflow, or confident hallucination. Design for every single one.
- **Resilience pattern**:
  - Explicit per-call timeouts (`AbortSignal.timeout(ms)` / `httpx.Timeout`). Distinguish **Time-To-First-Token (TTFT)**
    timeout from total stream completion timeout.
  - Bounded retries (max 2–3) with exponential backoff + jitter on `429`/`5xx`/network timeouts only; honor `Retry-After` headers.
  - Automatic fallback to a secondary model or provider (e.g., primary frontier model → fallback regional endpoint or alternate provider) on sustained failure.
- **Right-sized tool**: if regex, deterministic rules, SQL/BM25 search, or a lightweight classifier solves the problem,
  do not call an LLM. Use LLMs where natural-language understanding, synthesis, or fuzzy extraction provides real value.

## 2. Prompt architecture & prefix caching

- **Prompts are versioned code**: store prompts in dedicated, version-controlled template files/modules — never scattered
  string concatenations inside controllers. Review prompt diffs and run evals whenever prompts change.
- **Prompt structure (ordered for Prefix Caching)**:
  Providers (OpenAI, Anthropic, Google Gemini, DeepSeek, vLLM Prefix Caching) cache the **static prefix** of prompts
  (50%–90% input token discount and lower TTFT). Always order prompt segments from **most static to most dynamic**:
  1. **System Instructions**: role, domain rules, tone, output schema instructions, security boundaries (100% static).
  2. **Tool Definitions**: static JSON schemas for available tools.
  3. **Few-Shot Examples**: canonical input/output examples demonstrating edge cases and judgment criteria (static).
  4. **Domain / Reference Context**: retrieved documents or project metadata (semi-static; place cache breakpoints here if supported).
  5. **Conversation History & Current User Input**: clearly delimited in XML tags (`<user_query>...</user_query>`,
     `<retrieved_documents>...</retrieved_documents>`) at the very end (dynamic).
- **Never put dynamic timestamps (`Current time: 2026-10-18T21:45:03Z`) or random request IDs at the top of the system prompt** — doing so invalidates the entire prefix cache on every request!

## 3. Structured outputs & runtime schema validation

- **Enforce constrained decoding**: use the provider's native **Structured Outputs** (`response_format: { type: "json_schema", strict: true }`,
  `responseSchema`, or tool-calling) rather than asking in prose *"please reply only in valid JSON"*.
- **Keep schemas flat and explicit**:
  - Use clear property names, descriptions, and string `enum` unions.
  - Put reasoning/explanation fields **before** final decision/classification fields in the JSON schema (chain-of-thought
    ordering improves accuracy because tokens are generated left-to-right).
- **Mandatory runtime validation**: parse every model response through **Zod / Valibot / Pydantic** at the boundary:
  - Check `finish_reason` / `stop_reason` first (`length` / `max_tokens` means the JSON was truncated mid-stream; `content_filter` / `safety` means refusal).
  - If validation fails, run at most **1 repair retry** feeding the exact validation error back to the model, then fail gracefully with a typed error.

## 4. Streaming, cancellation & backpressure

- **Stream any user-facing generation > 1–2 seconds**: use **Server-Sent Events (SSE)** or the framework's typed stream
  protocol (Vercel AI SDK Data Stream, FastAPI `StreamingResponse` with `text/event-stream`).
- **End-to-end cancellation**: wire client disconnect (`req.signal` / `AbortController`) directly into the upstream LLM SDK
  call so when a user clicks "Stop" or closes the tab, token generation stops immediately and stops billing.
- **Async background jobs**: batch summarization, document ingestion, and multi-minute reports belong in an idempotent
  job queue (BullMQ / Celery / Temporal), never inside a synchronous HTTP request.

## 5. Security: prompt injection, authorization & data privacy

- **Untrusted data vs instructions**: any text from users, uploaded PDFs, web pages, emails, or tool outputs can contain
  adversarial prompt injections. Delimit untrusted text inside data tags and instruct the model to treat tag contents strictly as passive data.
- **Code-enforced authorization (zero trust in prompt rules)**:
  - Never put multi-tenant data in context and ask the model *"only answer for user_id 123"*. Enforce tenant and RBAC
    permissions in SQL/Vector DB queries and tool handlers **before** data ever reaches the prompt.
- **Output sanitization**: treat LLM output as untrusted user input. Sanitize Markdown/HTML (DOMPurify, block `javascript:`
  and unauthorized external image URLs that exfiltrate context data via query strings), parameterize any SQL/queries, and
  sandbox any generated code execution.
- **PII & secret redaction**: never pass `.env` secrets or raw credentials in prompts; mask/redact sensitive PII (NIK, credit card, tokens) before logging or sending to external providers, in compliance with **UU PDP Indonesia / GDPR**.

## 6. Cost, token budgeting & model routing

- **Token & cost telemetry**: record `input_tokens`, `cached_input_tokens`, `output_tokens`, `reasoning_tokens`, `latency_ms`,
  `ttft_ms`, and `estimated_cost_usd` per request, tagged by `tenant_id`, `user_id`, and `feature_name`.
- **Tiered model routing**:
  - **Tier 1 (Flash / Mini / 8B local)**: classification, intent routing, query rewriting, simple extraction, guardrails.
  - **Tier 2 (Standard Frontier / 70B)**: general RAG synthesis, code generation, multi-turn chat.
  - **Tier 3 (Reasoning / Pro)**: complex architecture, deep debugging, multi-constraint planning, high-stakes auditing.
- **Denial-of-Wallet protection**: enforce per-user and per-tenant token/cost budgets (daily/monthly quotas + RPM/TPM rate limits) and max input length caps.

## 7. Review checklist

Prefix cache order preserved (static first, dynamic last) · native structured outputs + Zod/Pydantic validation ·
`finish_reason` checked · timeouts + bounded retry + provider fallback · streaming with `AbortSignal` cancellation ·
RBAC/tenant filtering enforced in code/DB · untrusted inputs delimited · output sanitized before render · token cost and
latency logged · per-user rate/budget limits active · companion `sub-*` modules loaded for RAG, Agents, Infra, or Fine-Tuning.
