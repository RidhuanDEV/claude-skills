# 01 — Realtime Protocol Selection ADR: Polling vs SSE vs WebSocket vs WebRTC vs MQTT

## 1. Purpose & Activation Conditions
Choose the simplest, most operationally reliable realtime transport matching directionality, latency budget, network constraints, and proxy infrastructure — avoiding unnecessary WebSocket clusters where HTTP **SSE (`EventSource`)** or **Smart Polling** is superior, and knowing exactly when **WebSocket**, **WebTransport**, **WebRTC (STUN/TURN/SFU)**, or **MQTT** is mandatory. Activate before writing any live-update, streaming, chat, call, or IoT ingestion architecture.

## 2. Prerequisites
- Defined message directionality (server -> client only vs full duplex), message frequency (`msg/sec`), payload size, concurrent connection count, and client network profile (corporate HTTP proxies, mobile 3G/4G NAT, embedded IoT).

## 3. Technical Principles & Constraints
- **Transport Simplicity Ladder (Pick the Lowest Rung That Meets SLA):**
  1. **Short / Conditional Polling (`ETag` / `If-None-Match`):** Best when updates occur every `10–60s` (dashboards, build status, background job progress). Zero persistent sockets, effortless CDN/load-balancer scaling!
  2. **Server-Sent Events (`SSE` / `EventSource` or `fetch` stream):** Default choice for **unidirectional server -> client** feeds (live notifications, order status updates, stock tickers, LLM token streaming). Works natively over HTTP/2 multiplexing (no 6-connection browser limit under HTTP/2!), traverses strict corporate firewalls, includes built-in `Last-Event-ID` resumption, and uses standard HTTP auth headers/cookies. **Mandatory proxy header:** `X-Accel-Buffering: no` + `Cache-Control: no-cache, no-transform` + `Content-Type: text/event-stream`.
  3. **WebSocket (`wss://`):** Use ONLY when genuine **low-latency bidirectional** client <-> server frames are needed (multiplayer collaboration, live chat typing + messages, interactive trading order books). Requires explicit app-level ping/pong heartbeats (`20–30s`), reverse-proxy `Upgrade` + `proxy_read_timeout`, and custom resumption protocol.
  4. **WebRTC (STUN + TURN + SFU):** Mandatory for **real-time audio/video calls & screen sharing** (UDP SRTP media). Always provision an authenticated **TURN relay** (`15–20%` of corporate/mobile users sit behind symmetric NAT where P2P STUN fails!) and use an **SFU** (LiveKit, mediasoup) once rooms exceed `3–4` participants (P2P mesh collapses at $N(N-1)/2$ upload streams!).
  5. **MQTT (`QoS 0/1/2` + `LWT`):** Purpose-built for **flaky mobile/embedded IoT telemetry** (tiny 2-byte header, native Last Will & Testament disconnect alerts, persistent sessions, per-device mTLS/ACL topics). Note: MQTT `QoS 1` is at-least-once -> consumers MUST deduplicate!
- **Reverse-Proxy Timeout & Buffering Traps:** Default Nginx `proxy_read_timeout 60s` silently drops idle WebSocket/SSE connections every 60 seconds unless either heartbeat frames/comments (`: ping\n\n`) fire every `20–25s` OR `proxy_read_timeout` is tuned cleanly alongside OS `ulimit -n` / `worker_connections`.

## 4. Architecture & Implementation

### Transport Selection Decision Matrix

| Use Case | Recommended Protocol | Why Not Alternatives? | Mandatory Production Config |
| :--- | :--- | :--- | :--- |
| **Status updates every `15–60s`** | Conditional Polling (`ETag`) | Zero persistent socket RAM/FD cost | `Cache-Control: private, no-cache`, backoff on idle tab |
| **Live notifications, order progress, LLM streaming** | **SSE (`EventSource` / `fetch` SSE)** | Simpler than WS; HTTP/2 multiplexed; native `Last-Event-ID` | `X-Accel-Buffering: no`, monotonic `id:`, `: keepalive\n\n` every `20s` |
| **Bidirectional chat, live cursors, trading books** | **WebSocket (`wss://`)** | True full-duplex binary/text frames with low framing overhead | Ping/pong heartbeat (`25s`), Redis/NATS fan-out, bounded outbound queue |
| **Voice / Video / Screen Share (`> 3` users)** | **WebRTC + TURN + SFU** | TCP/WebSocket suffers head-of-line blocking on video packets | Authenticated TURN (coturn/managed) + SFU (LiveKit/mediasoup) |
| **IoT sensors / GPS trackers on flaky cellular** | **MQTT (QoS 1 + LWT)** | Ultra-low bandwidth; native LWT offline alert | Per-device mTLS + topic ACL + idempotent QoS 1 consumer |

```ts
// Strict TypeScript SSE Frame Encoder & Proxy-Safe Response Header Builder (0 any, 0 casts)
export interface SseEventFrame {
  readonly id: number
  readonly event: string
  readonly data: Record<string, unknown>
  readonly retryMs?: number
}

export const SSE_SAFE_HEADERS: Readonly<Record<string, string>> = {
  'Content-Type': 'text/event-stream; charset=utf-8',
  'Cache-Control': 'no-cache, no-transform',
  Connection: 'keep-alive',
  'X-Accel-Buffering': 'no', // Critical: prevents Nginx from buffering SSE chunks!
}

export function encodeSseFrame(frame: SseEventFrame): string {
  const lines: string[] = [`id: ${frame.id}`, `event: ${frame.event}`]
  if (frame.retryMs !== undefined && frame.retryMs > 0) {
    lines.push(`retry: ${frame.retryMs}`)
  }
  const serialized = JSON.stringify(frame.data).replace(/[\r\n]+/g, ' ')
  lines.push(`data: ${serialized}`)
  return `${lines.join('\n')}\n\n`
}

export function encodeSseKeepaliveComment(): string {
  return ': keepalive\n\n'
}
```

## 5. Platform/Vendor Variations
- **HTTP/1.1 vs HTTP/2 for Browser `EventSource`:** Over legacy HTTP/1.1, browsers allow at most **6 concurrent connections per origin** (opening 6 browser tabs with SSE starves normal API `fetch` calls!). Always serve SSE over **HTTP/2 (TLS)** (supports `100+` concurrent multiplexed streams over 1 TCP connection) or use a shared `BroadcastChannel` across browser tabs!
- **Browser `EventSource` Auth Header Limitation:** Native `new EventSource(url)` cannot set custom `Authorization: Bearer ...` headers — use either `HttpOnly; Secure; SameSite=Lax` session cookies, short-lived opaque stream ticket exchanged via `POST /stream-ticket` (NEVER put long-lived JWTs in `?token=` URL query strings that leak into proxy logs!), or `@microsoft/fetch-event-source` / `fetch` streaming reader!
- **Nginx Reverse Proxy Config:** Set `proxy_http_version 1.1`, `proxy_buffering off`, `proxy_cache off`, `chunked_transfer_encoding on` for SSE, and `proxy_set_header Upgrade $http_upgrade; proxy_set_header Connection "upgrade";` for WebSocket.

## 6. Decision Matrix & Trade-Offs

| Protocol | Proxy / Firewall Survival | Bidirectional | Built-In Resume Cursor | Connection Overhead |
| :--- | :--- | :--- | :--- | :--- |
| **Polling (`ETag`)** | `100%` | Request/Response | Client query param | Stateless (lowest) |
| **SSE over HTTP/2** | `99%` (with `X-Accel-Buffering: no`) | Server -> Client | Native `Last-Event-ID` | Low (shared H2 TCP) |
| **WebSocket (`wss://`)** | `95%` (some corporate proxies strip Upgrade) | Full-Duplex | Custom (app protocol) | Medium (1 TCP/socket) |
| **WebTransport (HTTP/3)** | Growing (UDP/QUIC blocked in some enterprises) | Multiplexed streams + datagrams | Custom | Low (needs WS fallback) |

## 7. Real Production Scenario
A logistics dashboard built a custom WebSocket server to push shipment status changes (`~1` event per minute per user). Enterprise customers behind corporate HTTP inspection proxies reported disconnected feeds, and developers spent 3 weeks debugging custom reconnect/auth-refresh logic. Replacing WebSocket with **HTTP/2 SSE (`Last-Event-ID` + `X-Accel-Buffering: no`)** cut server code by 65%, worked immediately behind every enterprise proxy, and made missed-event replay deterministic via standard HTTP headers.

## 8. Failure Modes & Edge Cases
- **WRONG:** Passing a long-lived JWT in the WebSocket/SSE query string (`wss://api.example.com/ws?token=eyJhbG...`) where Nginx access logs, CDN logs, and browser history record the secret token!
  **RIGHT:** Use `HttpOnly` secure cookies on same-site origins, `fetch` streaming with `Authorization` header (for SSE), or a single-use short-lived (`15s` TTL) opaque handshake ticket exchanged via `POST /api/v1/realtime/ticket`!
- **WRONG:** Deploying WebRTC peer-to-peer calls with only Google public STUN and zero TURN relay (fails silently for 15–20% of cellular/corporate users!).
  **RIGHT:** Provision authenticated TURN relay credentials (short-lived HMAC time-limited credentials) and an SFU for multi-party calls.
- **WRONG:** Forgetting `X-Accel-Buffering: no` behind Nginx on SSE endpoints (events sit buffered in Nginx's 4KB buffer until 4KB accumulates or the stream closes!).
  **RIGHT:** Always emit `X-Accel-Buffering: no` and `Cache-Control: no-cache, no-transform` on every SSE response.

## 9. Testing & Verification
- Test SSE behind the real local/staging reverse proxy (not just raw `localhost:3000`) to confirm chunks flush immediately (`< 100ms`) rather than buffering in Nginx.
- Record protocol decision trade-offs in `playbooks/REALTIME-PROTOCOL-ADR-AND-RUNBOOK.md`.

## 10. Operational Considerations
- Tune Linux kernel `fs.file-max`, process `ulimit -n`, and Nginx `worker_connections` when planning `> 10,000` concurrent persistent connections.

## 11. Authoritative References
- WHATWG HTML Living Standard — *Server-Sent Events (`EventSource` & `Last-Event-ID`)*.
- RFC 6455 — *The WebSocket Protocol* & RFC 8441 (*Bootstrapping WebSockets with HTTP/2*).
- OASIS MQTT v5.0 Specification (`QoS`, `LWT`, Session Expiry).

## 12. Limitations & When NOT to Use
- Do NOT use `shadow-realtime` to guarantee durable multi-hour background job execution or payment webhook processing — durable delivery belongs in transactional queues/outboxes (`/shadow-concurrency`) and third-party webhook adapters (`/shadow-integrate`).
