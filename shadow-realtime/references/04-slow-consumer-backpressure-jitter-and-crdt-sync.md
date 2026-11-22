# 04 — Slow-Consumer Backpressure, Reconnect Storm Jitter & Collaborative Sync (CRDT vs OT)

## 1. Purpose & Activation Conditions
Protect realtime servers from **OOM crashes caused by slow 2G/3G consumers**, prevent **synchronized reconnect DDoS storms after deploys**, and choose accurately between **CRDTs (`Yjs`/`Automerge`)**, **Operational Transformation (OT)**, and **Server-Authoritative Transactions** for collaborative state. Activate when scaling realtime fleets, hardening WebSocket/SSE memory limits, or designing multi-user live editing.

## 2. Prerequisites
- Active connection lifecycle management (`02`, `03`) and observability tracking per-pod RAM, queue depth, and reconnect rates (`/shadow-observe`).

## 3. Technical Principles & Constraints
- **Bounded Slow-Consumer Backpressure (Zero Unbounded Per-Socket RAM!):**
  - When a client on a congested 2G network stops reading TCP packets while a chat/ticker room emits `50 msg/sec`, calling `ws.send(frame)` blindly buffers megabytes inside the server's kernel/Node `ws.bufferedAmount` RAM until the pod hits `OOMKilled` and kills 5,000 healthy users!
  - Enforce explicit **per-connection queue caps** (`maxBufferSize` / `maxBufferedBytes`, e.g., `128` frames or `256 KB`):
    1. **Droppable / Coalescable Frames** (typing indicators, mouse cursors, live price ticks): drop oldest or coalesce to **latest state only**!
    2. **Non-Droppable Ordered State Frames** (chat messages, document ops): once the bounded cap overflows, **disconnect the slow consumer cleanly** (`WS close 1008/4008 SLOW_CONSUMER` or SSE `event: snapshot_required` + end) so the client recovers via authorized full snapshot when its network clears!
- **Full-Jitter Exponential Backoff Against Reconnect Storms:**
  - When a deploy restarts a node holding `20,000` connections, naive `setTimeout(reconnect, 2000)` slams your auth/DB tier with `20,000` simultaneous handshakes every 2 seconds!
  - Always combine: (1) **Client Exponential Backoff + Full Jitter** (`delay = rand(0, min(maxMs, baseMs * 2^attempt))`), (2) **Staggered Server Drain** (close existing sockets in gradual waves during `SIGTERM` graceful shutdown over `15–30s`), and (3) **Token-Bucket Handshake Admission Rate Limits** at ingress.
- **CRDT (`Yjs`/`Automerge`) vs OT vs Server-Authoritative State:**
  - **CRDT (Conflict-Free Replicated Data Types):** Strong eventual consistency with offline-first editing and peer-independent merging — ideal for collaborative docs, sticky notes, whiteboards, checklists. **Mandatory ops rule:** run periodic **state-vector snapshot compaction** so deleted-character **tombstones** do not grow document payloads unboundedly!
  - **OT (Operational Transformation):** Requires a central ordering server; lower historical memory footprint for gigantic text docs (Google Docs model), much harder to implement correctly from scratch.
  - **NEVER Use CRDTs for Financial Balances, Finite Inventory, or Authorization:** Eventual conflict-free convergence allows two offline devices to spend the same `Rp 500,000` balance simultaneously (double-spend!). Money, stock locks, and permissions MUST stay **server-authoritative transactional** (`/shadow-domain`, `/shadow-concurrency`)!

## 4. Architecture & Implementation

```ts
// Strict TypeScript Full-Jitter Reconnect Backoff + Bounded Slow-Consumer Queue (0 any, 0 casts)
export function computeJitteredReconnectMs(
  attempt: number,
  baseMs = 500,
  maxMs = 30_000,
  rand: () => number = Math.random,
): number {
  const safeAttempt = Math.max(0, Math.min(10, Math.floor(attempt)))
  const expCeiling = Math.min(maxMs, baseMs * Math.pow(2, safeAttempt))
  return Math.max(100, Math.round(rand() * expCeiling))
}

export interface QueuedRealtimeFrame {
  readonly seq: number
  readonly droppable: boolean
  readonly payloadBytes: number
}

export type BackpressureDecision = 'ENQUEUED' | 'COALESCED_DROPPED' | 'DISCONNECT_SLOW_CONSUMER'

export function enqueueBoundedRealtimeFrame(
  queue: QueuedRealtimeFrame[],
  incoming: QueuedRealtimeFrame,
  limits: { readonly maxFrames: number; readonly maxTotalBytes: number },
): BackpressureDecision {
  const currentBytes = queue.reduce((acc, item) => acc + item.payloadBytes, 0)
  if (queue.length < limits.maxFrames && currentBytes + incoming.payloadBytes <= limits.maxTotalBytes) {
    queue.push(incoming)
    return 'ENQUEUED'
  }
  const droppableIdx = queue.findIndex((item) => item.droppable)
  if (droppableIdx !== -1) {
    queue.splice(droppableIdx, 1)
    queue.push(incoming)
    return 'COALESCED_DROPPED'
  }
  if (incoming.droppable) {
    return 'COALESCED_DROPPED'
  }
  return 'DISCONNECT_SLOW_CONSUMER'
}
```

### Collaborative Sync & Conflict Resolution Decision Matrix

| Domain State | Sync Strategy | Offline Edit Safe? | Tombstone / Ops Concern |
| :--- | :--- | :--- | :--- |
| **Rich Text / Notes / Canvas / Whiteboard** | **CRDT (`Yjs` / `Automerge`)** | **Yes** (merges automatically) | Compact snapshots periodically to prune tombstones |
| **Form / Settings / Ticket Fields** | **Server Optimistic Locking (`version` / `ETag`)** | Partial (conflict UI on sync) | Simple, zero CRDT bloat; shows merge diff on `409` |
| **Chat Messages / Activity Feeds** | **Append-Only Server Sequence (`02`)** | Queue locally with `client_msg_id` dedup | Bounded history retention + `snapshot_required` |
| **Wallet Balance / Stock / Seat Booking** | **Server-Authoritative ACID TX** | **NO** (online commit required) | **NEVER** use CRDTs (prevents double-spend/oversell) |

## 5. Platform/Vendor Variations
- **Node.js `ws` Library `bufferedAmount` Guard:** Check `ws.bufferedAmount > 262_144` (`256KB`) BEFORE calling `ws.send()` — `ws.send()` alone does not enforce backpressure automatically and will happily queue gigabytes into C++/V8 memory!
- **SSE (`res.write()`) Node Stream Backpressure:** Respect the boolean return value of `res.write(chunk)` — if `false`, the OS TCP send buffer is full! Track pending overflow per client and close slow SSE consumers cleanly instead of ignoring `res.write() === false`.
- **Yjs Production Persistence (`y-websocket` / Hocuspocus / Liveblocks):** Persist incremental binary updates in Postgres/S3 and schedule compaction merging updates into a fresh encoded state snapshot (`Y.encodeStateAsUpdate`) every `N` edits so cold-loading a 6-month-old document stays `< 50ms`.

## 6. Decision Matrix & Trade-Offs

| Overflow Strategy | Memory Safety | Client Experience | Right For |
| :--- | :--- | :--- | :--- |
| **Unbounded RAM Queue** | **CRASHES POD (OOM)** | All users go down | **NEVER** |
| **Drop / Coalesce Latest Frame** | **100% Bounded** | Skips intermediate cursor/price ticks smoothly | Telemetry, cursors, typing indicators, live prices |
| **Disconnect (`1008`) + `snapshot_required`** | **100% Bounded** | Brief reconnect -> clean authoritative state | Ordered feeds, chat, collaborative state streams |

## 7. Real Production Scenario
During a live auction event with 18,000 concurrent viewers, a backend deploy restarted all 6 WebSocket pods simultaneously. All 18,000 mobile clients executed `setTimeout(connect, 1000)`, slamming the auth database with 18,000 JWT/session queries in 1 second, while ~300 users on stalled 3G connections caused `ws.bufferedAmount` to balloon to `2.1 GB` per pod and trigger cascading `OOMKilled` loops. Implementing staggered 25-second graceful drain on `SIGTERM`, client full-jitter exponential backoff (`computeJitteredReconnectMs`), and strict `256KB` `bufferedAmount` slow-consumer eviction + `snapshot_required` dropped reconnect peak auth RPS by 92% and capped per-pod RAM flat at `380 MB`.

## 8. Failure Modes & Edge Cases
- **WRONG:** Adding identical deterministic backoff (`1s, 2s, 4s, 8s` with NO random jitter!) on reconnect — all 20,000 disconnected clients STILL fire in lockstep waves at `t=1s`, `t=3s`, `t=7s`!
  **RIGHT:** Always apply **Full Jitter** (`rand() * expCeiling`) so reconnects spread uniformly across the backoff window.
- **WRONG:** Ignoring `res.write() === false` on SSE or `ws.bufferedAmount` on WebSocket while streaming high-frequency ticks.
  **RIGHT:** Measure queue depth explicitly (`realtime_transport_verifier.py` requires measured queue depth!), coalesce droppable frames, and disconnect overflowed non-droppable slow consumers cleanly.

## 9. Testing & Verification
- Unit-test `enqueueBoundedRealtimeFrame` verifying: (1) normal enqueue under limits, (2) droppable frame eviction/coalescing when full, and (3) `DISCONNECT_SLOW_CONSUMER` when queue holds only non-droppable frames.
- Run `python shadow-realtime/scripts/realtime_transport_verifier.py --self-test` and `python -m unittest discover -s shadow-realtime/tests -v`.

## 10. Operational Considerations
- Track `realtime_slow_consumer_disconnects_total`, `realtime_dropped_coalesced_frames_total`, and `realtime_reconnect_rate` in Grafana (`/shadow-observe`).
- Configure Kubernetes `terminationGracePeriodSeconds: 45` so pods have enough time to drain WebSocket connections in staggered waves on rolling deploys (`/shadow-ops`, `/shadow-release`).

## 11. Authoritative References
- AWS Architecture Blog — *Exponential Backoff and Jitter (Full Jitter)*.
- Martin Kleppmann — *Local-First Software & CRDTs* / Yjs Documentation (`Y.encodeStateAsUpdate` compaction).
- `shadow-realtime/methodologies/WEBSOCKET-SSE-RESUMPTION-AND-BACKPRESSURE.md`.

## 12. Limitations & When NOT to Use
- Do NOT adopt CRDT libraries (`Yjs`/`Automerge`) for ordinary single-user CRUD forms where simple optimistic locking (`version`/`If-Match`) is 10x simpler and easier to audit.
- Do NOT run synthetic `50,000`-socket load tests locally without explicit `L3` approval and dedicated load-generator infrastructure (`/shadow-perf`).
