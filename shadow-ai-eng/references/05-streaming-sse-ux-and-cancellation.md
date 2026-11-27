# 05. Streaming SSE Token UX & Cancellation

## 1. Purpose & Activation Conditions
Deliver snappy, cancellable token-streaming UX over **Server-Sent Events (`text/event-stream`)** while protecting backend budgets from orphaned generations, reverse-proxy buffering bugs, and broken partial states. Load when implementing streaming chat/copilot APIs, frontend token renderers, or debugging buffered/cut-off AI streams.

## 2. Prerequisites
- Bounded LLM gateway (`01`) and reverse-proxy configuration awareness (`/shadow-ops`, `/shadow-realtime`).

## 3. Technical Principles & Constraints
- **Mandatory `AbortController` Disconnect Cancellation (`Zero Orphaned Token Burn!`):** Whenever a browser user clicks `"Stop"`, navigates away, or closes the tab mid-stream, the backend MUST catch `req.on('close')` / `request.signal` and immediately call `abortController.abort()` on the upstream LLM fetch! Otherwise your backend keeps streaming and paying for `2,000` output tokens nobody will ever read!
- **Reverse-Proxy Zero-Buffering Headers (Fixes `"Tokens Arrive All at Once After 12s"`):** Nginx, Cloudflare, and API gateways buffer chunked responses by default unless you emit:
  - `Content-Type: text/event-stream; charset=utf-8`
  - `Cache-Control: no-cache, no-transform` (`no-transform` stops proxies from gzip-buffering chunks!)
  - `X-Accel-Buffering: no` (disables Nginx proxy buffering!)
  - Periodic SSE heartbeat comments (`: keepalive\n\n` every `15s`) so idle reasoning pauses never trip `30s` load-balancer idle timeouts!
- **Typed Streaming Event Protocol (Never Stream Raw Unframed Text):** Emit explicit typed JSON frames (`event: status`, `event: token`, `event: citation`, `event: tool_preview`, `event: done`, `event: error`) with monotonic `seq` IDs so the frontend cleanly renders tool progress, citations, HITL approval buttons, and partial-failure recovery without corrupting Markdown!
- **Bounded Token & Thinking Ceilings (`OWASP LLM06:2026` Unbounded Consumption):** Cap BOTH `max_output_tokens` AND `thinking_budget` per request tier (remember: reasoning/thinking tokens bill at expensive output-token rates — `/shadow-finops`!).

## 4. Architecture & Implementation
```typescript
export type SseFrame =
  | { readonly type: 'status'; readonly stage: 'retrieving' | 'generating' | 'waiting_hitl' }
  | { readonly type: 'token'; readonly seq: number; readonly delta: string }
  | { readonly type: 'citation'; readonly docIds: readonly string[] }
  | { readonly type: 'done'; readonly finishReason: 'stop' | 'length' | 'cancelled' }
  | { readonly type: 'error'; readonly code: string; readonly retryable: boolean };

export function formatSseEvent(frame: SseFrame): string {
  return `event: ${frame.type}\ndata: ${JSON.stringify(frame)}\n\n`;
}

export const SSE_STREAM_HEADERS: Readonly<Record<string, string>> = {
  'Content-Type': 'text/event-stream; charset=utf-8',
  'Cache-Control': 'no-cache, no-transform',
  Connection: 'keep-alive',
  'X-Accel-Buffering': 'no',
};

export function linkClientDisconnectToUpstreamAbort(
  clientSignal: AbortSignal,
  maxStreamDurationMs = 90_000
): { readonly upstreamSignal: AbortSignal; readonly cleanup: () => void } {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(new Error('STREAM_DURATION_CAP')), maxStreamDurationMs);
  const onClientAbort = (): void => controller.abort(new Error('CLIENT_DISCONNECTED'));

  if (clientSignal.aborted) {
    onClientAbort();
  } else {
    clientSignal.addEventListener('abort', onClientAbort, { once: true });
  }

  return {
    upstreamSignal: controller.signal,
    cleanup: () => {
      clearTimeout(timer);
      clientSignal.removeEventListener('abort', onClientAbort);
    },
  };
}
```

## 5. Platform / Vendor Variations
| Transport / Proxy | Streaming Requirement | Common Failure Mode |
| :--- | :--- | :--- |
| **Nginx Reverse Proxy** | `proxy_buffering off; proxy_http_version 1.1; proxy_read_timeout 120s;` + `X-Accel-Buffering: no` | Nginx buffers 4–8 KB before flushing -> user stares at spinner for 10s then gets text dump |
| **Next.js App Router / Edge / Node Runtime** | Return `new Response(ReadableStream, { headers: SSE_STREAM_HEADERS })`, wire `request.signal` | Forgetting `export const dynamic = 'force-dynamic'` or hitting serverless 10–30s function timeout |
| **Frontend React Streaming Renderer** | Throttle DOM Markdown re-parses via `requestAnimationFrame` (~60fps) + explicit Stop button calling `abort()` | Re-parsing full 4,000-word Markdown AST on every single token chunk freezes low-end mobile browsers! |

## 6. Decision Matrix & Trade-Offs
| Transport | Best For | Complexity |
| :--- | :--- | :---: |
| **SSE (`POST` fetch + `ReadableStream` or `EventSource`)** | One-way LLM token streaming + citations + Stop button | **Lowest & HTTP-proxy friendly (Recommended)** |
| **WebSockets (`/shadow-realtime`)** | Full-duplex voice/audio/collaborative live editing | High (stateful LB sticky/pubsub needed) |

## 7. Real Production Scenario
A copilot chat works smoothly on `localhost:3000`, yet in production behind Nginx users see a blank loading spinner for 14 seconds followed by the entire answer popping in at once — and when impatient users refresh the tab 3 times, the backend finishes all 4 parallel 2,000-token generations (`4x` LLM bill!). Setting `X-Accel-Buffering: no`, `Cache-Control: no-cache, no-transform`, periodic `: keepalive` comments, and wiring `linkClientDisconnectToUpstreamAbort` fixes real-time streaming and cuts wasted aborted-stream spend to zero.

## 8. Failure Modes & Edge Cases
- **WRONG:** Saving a chat message to Postgres ONLY inside `onStreamComplete` without handling `cancelled` or mid-stream network drops (user loses a half-generated answer or sees duplicate messages on retry).
- **RIGHT:** Persist partial output cleanly with explicit status (`COMPLETED` vs `PARTIAL_CANCELLED` vs `FAILED`) + message `idempotency_key` so retries replace or resume cleanly.
- **WRONG:** Passing raw `err.stack` or provider API key error text inside the SSE `event: error` frame to the browser.
- **RIGHT:** Send only safe typed error codes (`{ type: 'error', code: 'UPSTREAM_TIMEOUT', retryable: true }`) and log full diagnostics privately with `requestId`.

## 9. Testing & Verification
- Run `python shadow-ai-eng/scripts/ai_runtime_verifier.py --check-prompt-layout <cfg.json>` confirming `abort_controller_on_disconnect: true`.
- Integration test: open SSE stream -> abort client fetch after 3 chunks -> assert upstream mock generator's `AbortSignal.aborted === true` within `< 100ms`!

## 10. Operational Considerations
- Measure BOTH **TTFT (Time-to-First-Token)** and **TPOT (Time-Per-Output-Token)** + **Stream Abort/Disconnect Rate** (`> 15%` early user aborts signal slow TTFT or irrelevant answers!).

## 11. Authoritative References
- WHATWG HTML Living Standard — *Server-Sent Events (`text/event-stream`)* (`https://html.spec.whatwg.org/multipage/server-sent-events.html`).
- MDN Web Docs — *AbortController & Streams API* (`https://developer.mozilla.org/en-US/docs/Web/API/AbortController`).

## 12. Limitations & When NOT to Use
- Do NOT stream structured machine-only background tasks (e.g., async invoice classification or batch document extraction) — use standard non-streaming constrained JSON calls with queue retries instead!
