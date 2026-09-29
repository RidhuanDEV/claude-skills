# AI-LLM — Building Features on Large Language Models

Use when building or reviewing features that call LLMs: chat, summarization, extraction, classification,
RAG ("chat with your documents"), agents/tool use, AI code features. Chat/AI UX lives in DESIGN.md §9.
Model names, context sizes, prices and SDK APIs change fast: check the provider's current docs and the SDK
version in the project instead of relying on memory, and never invent model IDs or parameters.

## 1. Treat the LLM as an unreliable, non-deterministic dependency

- It can be slow, rate-limited (429), overloaded (5xx), wrong, or confidently fabricate. Design for all of these.
- Timeouts on every call; bounded retries with exponential backoff + jitter on 429/5xx/timeouts only;
  honor `retry-after`; circuit breaker or fallback model/provider for critical paths; graceful degraded UX.
- Stream responses for anything user-facing and long; support cancellation when the user stops or leaves.
- Long or batch jobs go to a queue with idempotency (same as BACKEND.md §7), not inside a web request.
- Is an LLM even needed? Regex, rules, full-text search or a classical classifier is cheaper, faster and
  deterministic when the task is simple. Use the LLM where language understanding is the actual value.

## 2. Prompts are code

- Keep prompts in version-controlled files/templates, not scattered string concatenation. Review prompt changes like code
  and re-run evals (§6) when they change.
- Structure: system prompt for role, rules and context; clear task; relevant data delimited (XML tags or fenced sections);
  output format; a few examples when the format or judgment is subtle. Explain why a rule matters rather than shouting in caps.
- Put stable content first and variable content last so provider prompt caching can hit.
- Ask for structured output with the provider's JSON-schema / structured-output / tool-calling feature where available,
  then **validate** the result with a schema (Zod, Pydantic, etc.). Handle invalid output: repair-retry once, then fail clearly.
- Temperature low for extraction/classification; higher only for creative generation.
- Never rely on the prompt alone for security or business rules (see §4).

## 3. RAG (retrieval-augmented generation)

Pipeline: ingest → parse/clean → chunk → embed → store → retrieve → (rerank) → generate with citations.
- **Ingestion**: extract text reliably (PDF tables, OCR for scans), keep metadata (source, title, page, section, updated_at,
  tenant/owner, access level). Re-index on document change; delete vectors when documents are deleted.
- **Chunking**: follow document structure (headings, paragraphs) over fixed character splits; moderate size with some overlap;
  include the title/section path in each chunk's text so it stands alone.
- **Embeddings**: one embedding model per index (changing models means re-embedding everything); store model name/version.
- **Storage**: pgvector is often enough when you already run PostgreSQL; dedicated vector DBs when scale or features demand it.
  Index choice (HNSW/IVF) and filters must support metadata constraints.
- **Retrieval**: hybrid search (vector + keyword/BM25) usually beats either alone; filter by tenant and permissions **inside the
  query**, never after generation; rerank the top candidates; cap the context you send.
- **Generation**: instruct the model to answer only from provided sources, cite them, and say "not found in the documents"
  instead of guessing. Show citations in the UI so users can verify.
- **Evaluate retrieval separately** from generation (did the right chunks come back? recall@k) — most bad RAG answers are retrieval failures.

## 4. Security: prompt injection and output handling

- Any text the model reads from users, documents, web pages, emails or tool results can contain instructions.
  Treat it as **untrusted data**, clearly delimited, and never let it change permissions or goals.
- Authorization happens in your code, not in the prompt: the model can only reach data the current user may access
  (filter retrieval and tool calls by the user's identity).
- Tools/agents get **least privilege**: narrow, typed tools; server-side validation of every argument; allowlists;
  read-only by default; human confirmation for destructive, financial or externally visible actions (sending email, payments, deletes).
- Treat model output as untrusted input: escape before rendering (no raw HTML from the model), never `eval`/execute it,
  parameterize any SQL it influences, validate URLs before fetching (SSRF), sandbox generated code execution.
- Beware data exfiltration via rendered links/images that embed data in URLs.
- Secrets never go into prompts. Redact PII where the provider or logs should not see it.
- Rate-limit and budget per user to prevent cost abuse ("denial of wallet").

## 5. Agents and tool use

- Prefer a fixed workflow (explicit steps in code) over an autonomous agent when the steps are known; agents are for open-ended tasks.
- Clear tool names and descriptions, strict input schemas, informative error messages returned to the model.
- Bound loops: max steps, max tokens, wall-clock timeout, and a stop condition. Detect repetition.
- Keep state and side effects in your system (idempotent tool calls, audit log of actions taken on behalf of a user).
- Give the model only the context it needs; long, noisy context degrades quality and costs money.

## 6. Evaluation

- Build a **golden set** early: realistic inputs with expected outputs or grading criteria, including edge cases and
  adversarial inputs (injection attempts, empty/irrelevant documents, other languages such as Bahasa Indonesia).
- Automate: exact/schema checks where possible; LLM-as-judge with a clear rubric for fuzzy quality (validate the judge
  against human ratings); human review for high-stakes outputs.
- Run evals in CI on prompt, model or retrieval changes; compare against the previous version before shipping.
- Track production signals: user feedback, fallback/refusal rates, latency, cost per request, schema-validation failures.

## 7. Cost and latency

- Log tokens in/out and cost per feature/user/tenant; set budgets and alerts.
- Levers: smaller/cheaper model for easy steps (route by difficulty), prompt caching, response caching for identical requests,
  trimming context, batching APIs for offline jobs, streaming for perceived latency, parallel independent calls.
- Measure before optimizing; quality regressions from a cheaper model must show up in evals, not in production.

## 8. Observability, privacy, compliance

- Trace each request: prompt template version, model, parameters, retrieved chunk IDs, tool calls, tokens, latency, outcome.
  Redact or hash PII and secrets in logs; restrict access to prompt logs (they often contain user data).
- Know the provider's data retention and training policy; choose the region/contract appropriate for the data
  (government or personal data may be subject to Indonesia's PDP Law, GDPR, or sector rules).
- Disclose AI-generated content where appropriate; keep a human in the loop for consequential decisions.

## 9. Review checklist

Timeouts/retries/fallback · streaming + cancel for long outputs · prompts versioned · structured output validated ·
retrieval filtered by permissions in the query · citations shown · injection considered for every untrusted input ·
tools least-privilege with confirmation for risky actions · output escaped before rendering · loop/budget limits ·
golden-set evals in CI · token cost tracked · PII redacted in logs · model IDs and SDK usage verified against current docs.

## 10. Anti-patterns

LLM for a regex-sized problem · prompt-only authorization ("the model will only show the user's own data") ·
rendering model HTML/Markdown links unsanitized · unbounded agent loops · parsing free-text instead of structured output ·
filtering RAG results by permission after generation · no evals ("it looked good in the demo") · one giant prompt string
built by concatenation · secrets or full PII in prompts and logs · hardcoded, outdated model names with no config.
