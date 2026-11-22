# 03. Agent Planning, State, Compaction & Memory Privacy

## 1. Purpose & Activation Conditions
Architect bounded, predictable multi-step agent loops with deterministic context compaction, tool-output truncation, resumable state persistence, and strict multi-tenant memory isolation. Load when building multi-turn copilots, long-running agents, or conversational memory stores.

## 2. Prerequisites
- Bounded tool boundaries (`02`), database persistence for conversation state (`shadow-db`), and privacy retention rules (`shadow-privacy`).

## 3. Technical Principles & Constraints
- **Bounded Execution Loops (`MAX_STEPS` & Token Budgets):** Never write `while (response.hasToolCalls)` with no hard ceiling! Enforce strict `MAX_STEPS` (typically `<= 6–10`), `MAX_WALL_CLOCK_MS`, duplicate-call loop detection (if the agent calls the exact same `(tool, args)` twice consecutively -> break and return best partial explanation!), and cumulative token caps (`OWASP LLM10:2025`).
- **Deterministic Context Compaction (Never Blindly Drop Index `0`!):** Long sessions degrade reasoning ("lost in the middle") and multiply input token costs quadratically! Partition the prompt window cleanly into 4 ordered zones:
  1. **Pinned Static System Prefix + Tool Schemas** (NEVER truncated; kept byte-identical for prefix caching!),
  2. **Structured Rolling State Summary** (explicit factual state: confirmed goals, decisions, resolved IDs, open constraints — updated when history exceeds threshold),
  3. **Bounded Tool Outputs** (cap each raw tool output to e.g. `4–8 KB` or top `N` rows with a clear `[TRUNCATED: 482 more rows omitted]` hint instead of dumping a 100 KB JSON blob into context!),
  4. **Recent Sliding Turns** (`last K` verbatim user/assistant turns).
- **Multi-Tenant & Privacy-Safe Memory Isolation (`UU PDP` / `OWASP LLM02`):**
  - Scope ALL conversation histories, summaries, and semantic long-term memories strictly by **`(tenant_id, user_id)`** (never shared global memory across tenants!).
  - Exclude raw secrets, passwords, OTPs, and high-risk PII from persistent long-term memory extraction, enforce explicit retention TTLs (`30–90d`), and wire memory tables into DSAR erasure (`shadow-privacy` Module `03`)!

## 4. Architecture & Implementation
```typescript
export interface ChatMessage {
  readonly role: 'user' | 'assistant' | 'tool';
  readonly content: string;
  readonly estimatedTokens: number;
}

export interface CompactedContextWindow {
  readonly systemPrefix: string; // Always preserved intact at position 0 for prefix caching
  readonly summaryBlock: string | null;
  readonly recentMessages: readonly ChatMessage[];
  readonly totalEstimatedTokens: number;
}

export function truncateToolOutputSafely(rawText: string, maxChars = 6000): string {
  if (rawText.length <= maxChars) return rawText;
  const omitted = rawText.length - maxChars;
  return `${rawText.slice(0, maxChars)}\n...[TRUNCATED: ${omitted} characters omitted; refine query/filters]`;
}

export function compactConversationWindow(opts: {
  readonly systemPrefix: string;
  readonly systemPrefixTokens: number;
  readonly existingSummary: string | null;
  readonly summaryTokens: number;
  readonly history: readonly ChatMessage[];
  readonly maxContextTokens: number;
  readonly keepRecentTurns: number;
}): CompactedContextWindow {
  const budgetForHistory = Math.max(
    512,
    opts.maxContextTokens - opts.systemPrefixTokens - opts.summaryTokens
  );
  const kept: ChatMessage[] = [];
  let used = 0;

  // Preserve most recent turns from newest to oldest within token ceiling
  for (let i = opts.history.length - 1; i >= 0; i -= 1) {
    const msg = opts.history[i];
    if (!msg) continue;
    if (kept.length >= opts.keepRecentTurns && used + msg.estimatedTokens > budgetForHistory) {
      break;
    }
    if (used + msg.estimatedTokens > budgetForHistory && kept.length > 0) {
      break;
    }
    kept.unshift(msg);
    used += msg.estimatedTokens;
  }

  return {
    systemPrefix: opts.systemPrefix,
    summaryBlock: opts.existingSummary,
    recentMessages: kept,
    totalEstimatedTokens: opts.systemPrefixTokens + opts.summaryTokens + used,
  };
}
```

## 5. Platform / Vendor Variations
| Agent State Complexity | Recommended Architecture | When to Upgrade |
| :--- | :--- | :--- |
| **Simple Chat + 2–4 Tools** | Explicit TypeScript/Python bounded `for (step = 0; step < MAX_STEPS)` loop + Postgres `messages` table | Covers 85% of production copilots cleanly without framework magic |
| **Pause-for-HITL / Multi-Hour Workflows** | Durable checkpoint state machine in Postgres (or Temporal / LangGraph checkpoint store) | When workflows pause waiting for human approval or async webhooks |

## 6. Decision Matrix & Trade-Offs
| Context Strategy | Input Token Cost | Fact Retention | Prefix Cache Friendly? |
| :--- | :---: | :---: | :---: |
| **Send Full Unbounded History** | Quadratic explosion | High (until overflow!) | Moderate |
| **Naive `slice(-10)` (Drops System/Early Facts)** | Low | Poor (forgets early rules!) | Broken if prefix shifts |
| **Pinned Prefix + Structured Summary + Recent Window** | **Bounded & Low** | **High** | **YES (Prefix stays static!)** |

## 7. Real Production Scenario
A support agent lets users inspect order logs via a tool that returns raw 90 KB JSON arrays. By turn 4, a single user prompt carries 85,000 input tokens (`$0.40/turn`, `9s` TTFT), and on turn 7 a naive trimmer slices off the system prompt so the agent stops refusing out-of-scope requests. Adding `truncateToolOutputSafely(raw, 6000)` + `compactConversationWindow` keeping the static prefix pinned cuts average cost per session by 78% and stabilizes TTFT under `1.1s`.

## 8. Failure Modes & Edge Cases
- **WRONG:** Storing an agent's "learned user preferences" in a shared vector index keyed only by `organization_name` string instead of `(tenant_id, user_id)` (leaks private HR/finance preferences across coworkers or tenants!).
- **RIGHT:** Partition every memory table and vector index strictly by `(tenant_id, user_id)` with pre-filter enforcement (`shadow-search`).
- **WRONG:** Letting a tool loop retry an identical failing call 15 times until `429` or OOM.
- **RIGHT:** Detect identical consecutive `(toolName, argsHash)` loops and abort cleanly with an honest explanation to the user.

## 9. Testing & Verification
- Unit-test `compactConversationWindow`: assert `systemPrefix` is ALWAYS intact at index 0, total tokens stay `<= maxContextTokens`, and newest turns survive.
- Test loop breaker: feed stubbed identical tool call twice -> assert loop terminates `<= MAX_STEPS` without infinite recursion.

## 10. Operational Considerations
- Track `agent_steps_per_turn` (`p50`/`p95`), `compaction_trigger_rate`, and `loop_abort_count` in `/shadow-observe` — rising step counts are an early indicator of confusing tool descriptions or broken upstream tools!

## 11. Authoritative References
- Anthropic Engineering — *Building Effective Agents* & *Effective Context Engineering for AI Agents* (`https://www.anthropic.com/engineering`).
- OWASP Top 10 for LLM Applications 2025 — `LLM02` & `LLM10`.

## 12. Limitations & When NOT to Use
- Avoid complex multi-agent swarms ("Manager -> Researcher -> Critic -> Writer") when a single well-structured prompt + 3 clean tools solves the workflow deterministically — extra agent hops multiply latency, token spend, and failure surface!
