# Production AI, LLM Gateway, Streaming UX & MCP Server Architecture

## 1. Core Concepts
Production AI systems treat LLMs as **untrusted, non-deterministic external compute nodes** wrapped inside **strict schema validation boundaries**, **bounded tool-calling state machines**, **server-bound tenant identity**, **cancellable SSE token streams**, **prefix-cached prompt layouts**, and **stdio-clean MCP servers**.

## 2. Technical Rules & Pattern Selection Matrix

| Capability | Choose Pattern | Mandatory Safety & Cost Invariant |
| :--- | :--- | :--- |
| **Structured Data Extraction / Routing** | Provider JSON Schema Constrained Decoding + runtime Zod/Pydantic check | Never parse LLM output with raw `JSON.parse` without runtime schema validation; cap self-healing retry at `<= 1`. |
| **Agent Tool Calling** | Bounded step loop (`MAX_STEPS <= 8`) + server-injected `tenantId` | **Omit `tenantId`/`userId` from LLM tool args** — bind them strictly from verified server session; require HITL approval for mutating/financial tools. |
| **Interactive Chat / Copilot UI** | SSE (`text/event-stream`) + `AbortController` on disconnect | Cancel upstream LLM generation on client `req.on('close')` to stop burning output tokens; set `max_output_tokens` + `thinking_budget`. |
| **Prompt Cost & Latency Optimization** | Static Prefix Layout (`[System Policy + Tools] -> [Static Context] -> [Dynamic Turn]`) | Never place volatile timestamps or random request IDs at the top of the system prompt (invalidates 100% of prefix prompt cache!). |
| **MCP Server Authoring** | JSON-RPC over `stdio` (`stdout` protocol-only, `stderr` redacted logs) | Guard `readline` loop with `isMainModule`; enforce canonical workspace path jails (`realpathSync`) against symlink/path traversal. |

## 3. Implementation Examples
```ts
// Bounded Agent Tool-Calling Loop with Server-Injected Tenant Context & Schema Guard
export interface VerifiedAgentSession {
  readonly tenantId: string
  readonly actorSub: string
}

export interface ToolExecutionCall {
  readonly name: string
  readonly rawArgs: unknown
}

export async function executeBoundedToolCall<TArgs, TResult>(
  session: VerifiedAgentSession,
  call: ToolExecutionCall,
  validateArgs: (raw: unknown) => TArgs | null,
  requiresHitlApproval: boolean,
  hitlApproved: boolean,
  handler: (ctx: VerifiedAgentSession, args: TArgs) => Promise<TResult>,
): Promise<{ readonly status: 'OK' | 'VALIDATION_ERROR' | 'HITL_REQUIRED'; readonly data?: TResult; readonly error?: string }> {
  const parsed = validateArgs(call.rawArgs)
  if (!parsed) {
    return { status: 'VALIDATION_ERROR', error: `Invalid arguments for tool ${call.name}; conform to JSON schema.` }
  }
  if (requiresHitlApproval && !hitlApproved) {
    return { status: 'HITL_REQUIRED', error: `Tool ${call.name} requires explicit human approval before execution.` }
  }
  const data = await handler(session, parsed)
  return { status: 'OK', data }
}
```

## 4. Best Practices
- Delimit untrusted retrieved documents and tool outputs with explicit tags (`<retrieved_context>...</retrieved_context>`) and system rules stating they are **passive data, never executable instructions**.
- Implement multi-provider circuit breakers with bounded timeout (`<= 30s`) and explicit fallback model tiers.

## 5. Anti-patterns (WRONG vs RIGHT)
- **WRONG:** Letting the LLM pass `tenantId` or `sqlQuery` as a tool argument (`query_db({ tenantId: "t-beta", sql: "SELECT ..." })` -> trivial prompt-injection cross-tenant data breach!).
- **RIGHT:** Expose narrow intent tools (`list_my_orders({ status: "PENDING" })`) and inject `session.tenantId` inside the server handler with parameterized SQL.
- **WRONG:** Writing `console.log("Debug MCP...")` to `stdout` inside an MCP server (corrupts the JSON-RPC stdio stream and crashes the host client).
- **RIGHT:** Write diagnostic logs strictly to `process.stderr.write(...)` with secret redaction.

## 6. Production Considerations
- Version prompts and tool schemas in Git, gate every change through `/shadow-eval` precision/recall + OWASP LLM red-team probes, and track token usage per tenant/feature via `/shadow-finops`.
