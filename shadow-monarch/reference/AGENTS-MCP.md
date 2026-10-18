# AGENTS-MCP — Agentic Workflows, Subagents & Model Context Protocol

Use when designing, building, orchestrating, or operating AI agents, multi-agent systems, subagents,
tool-calling runtimes, or Model Context Protocol (MCP) servers and clients. Pair with `AI-LLM.md` for
underlying model calls, prompts, RAG, and evaluation.

## 1. When to use an agent vs a deterministic workflow

- **Fixed workflow (code-driven DAG/pipeline)**: steps and branches are known ahead of time. Use explicit code
  orchestration with structured LLM calls at specific nodes. Faster, cheaper, predictable, easier to test.
- **Autonomous / semi-autonomous agent**: the sequence of tools and decisions depends dynamically on intermediate
  observations (e.g., debugging an unknown failure, exploring a repository, multi-step research).
- **Hybrid pattern (preferred in production)**: deterministic outer state machine with bounded agentic loops inside
  specific steps.

## 2. Subagent orchestration & context isolation

When operating as a coding/research agent or designing a multi-agent runtime:
- **Context window is a scarce resource**: do not pollute the primary orchestrator's context with raw file dumps,
  long search logs, or noisy intermediate outputs.
- **Delegate to subagents** when:
  1. Broad codebase exploration or literature/web research requires many read steps — let a read-only research
     subagent return a concise, source-linked synthesis.
  2. Independent workstreams can run in parallel across isolated modules or branched workspaces.
  3. A specialized persona/toolset is needed (e.g., security auditor, test runner, UI/image generator).
- **Subagent contract**: every subagent invocation must specify a clear **Role**, **Bounded Goal**, **Input Context**
  (relevant file paths, contracts, constraints), **Allowed Scope** (read-only vs write, target directories), and
  **Expected Output Schema/Summary**.
- **Verify subagent output**: the parent agent owns correctness. Cross-check subagent claims against actual source
  files and run verification checks before integrating changes.

## 3. MCP (Model Context Protocol) & tool engineering

Tools are the API contract between the model and the outside world:
- **Clear, unambiguous schemas**: descriptive tool names (`search_orders_by_customer`, not `do_query`), strict JSON
  Schema / Zod / Pydantic parameter definitions, explicit enums, format constraints, and defaults.
- **Token-safe responses**:
  - Paginate or cap list results (e.g., default `limit: 25`, max `100`) and return `total_count` + `next_cursor`.
  - Truncate oversized payloads (logs, large files, DOM trees) with explicit byte/line offsets so the agent can fetch
    slices on demand instead of overflowing context.
- **Actionable error messages**: when a tool call fails validation or hits a business rule, return a structured,
  self-correcting error message to the model explaining *what* was invalid and *how* to fix the arguments — never
  raw stack traces or database internals.
- **Idempotency & side-effect classification**:
  - Tag tools clearly: **Read-Only** (safe to retry/parallelize), **Mutating-Reversible**, or **Destructive/External**.
  - Mutating tools accept an idempotency key or check state before applying changes so duplicate tool calls from
    model retries do not duplicate records or charges.

## 4. State, checkpointing & durable execution

- **Persist agent state outside the prompt**: store conversation turns, tool call inputs/outputs, step counter, and
  workflow state in durable storage (DB/Redis) keyed by `thread_id` / `run_id`.
- **Checkpointing**: save state after every completed tool step so interrupted runs, server restarts, or human
  approval pauses can resume without re-executing completed side effects.
- **Context compaction / memory management**:
  - Trim or summarize old tool outputs (e.g., replace a 500-line file read from 15 turns ago with a short summary
    and file reference once the edit is complete).
  - Keep system instructions, active task plan, and verified contracts pinned in the active window.

## 5. Guardrails, budgets & human-in-the-loop (HITL)

- **Hard loop bounds**: enforce `max_steps` / `max_iterations`, `max_tokens_per_run`, `max_cost_usd`, and a
  wall-clock timeout. Detect repetitive tool calls (same tool + same arguments >= 2 times) and break the loop.
- **Human-in-the-loop (HITL) gates**: pause execution and require explicit user confirmation before:
  - Destructive file/data deletions or production infrastructure mutations.
  - External communications (sending emails, posting to webhooks/chat, publishing packages).
  - Financial transactions or permission/role escalations.
- **Workspace & filesystem sandboxing**: restrict file-system and shell tools to authorized workspace directories;
  block path traversal (`..`), secret files (`.env`, private keys), and unauthorized network egress.

## 6. Observability & agent evaluation

- **Trace the full trajectory**: log each step with `run_id`, `step_index`, `agent_role`, `model`, `thinking_summary`,
  `tool_name`, `tool_args`, `tool_status`, `latency_ms`, and `tokens_used`.
- **Evaluate trajectories, not just final text**:
  - Did the agent call the right tools with valid arguments?
  - Did it take redundant steps or hallucinate tool names/parameters?
  - Did it respect authorization boundaries and stop conditions?

## 7. Checklist

Workflow vs agent justified · subagents given bounded prompts and verified on return · MCP/tool schemas strict and
documented · tool outputs paginated/truncated for token safety · mutating tools idempotent · hard step/token/time
budgets enforced · repetition detection active · HITL gate on destructive/external actions · state checkpointed ·
full trajectory traced.

## 8. Anti-patterns

Unbounded `while (true)` agent loops · dumping megabytes of raw JSON/logs into tool responses · giving an agent a
raw SQL or unrestricted root shell tool in production · subagents spawning subagents recursively without depth limits ·
relying on system prompt text alone to prevent destructive tool calls · losing entire multi-step run progress on a
single transient network timeout.
