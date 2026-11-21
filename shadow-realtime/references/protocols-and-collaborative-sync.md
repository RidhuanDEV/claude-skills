# Realtime Protocols (SSE, WebSocket, WebRTC, MQTT) & Collaborative Sync

## 1. Core Concepts
Realtime systems balance **transport directionality (unidirectional SSE vs full-duplex WebSocket/WebTransport vs P2P/SFU WebRTC vs brokered MQTT)**, **horizontal pub/sub fan-out**, **conflict-free state convergence (CRDT/OT)**, **mid-session auth revocation**, and **slow-consumer backpressure**.

## 2. Technical Rules & Protocol Selection Matrix

| Use Case | Choose Protocol | Mandatory Production Rule |
| :--- | :--- | :--- |
| Live feeds, notifications, LLM token streaming | **SSE (`EventSource`)** | Send monotonic `id: <seq>`, support `Last-Event-ID` resume, emit `event: snapshot_required` if cursor expired, set `X-Accel-Buffering: no`. |
| Bidirectional chat, live cursors, trading books | **WebSocket** | App-level ping/pong heartbeat (20–30s), Redis/NATS multi-node fan-out, mid-session token revocation check, bounded per-socket outbound queue. |
| Low-latency voice/video calls, screen sharing | **WebRTC (STUN + TURN + SFU)** | Deploy authenticated **TURN** relay (15–20% of users behind symmetric NAT fail P2P) and an **SFU** (LiveKit/mediasoup) for `> 3` participants. |
| IoT telemetry over flaky mobile/embedded links | **MQTT (QoS 0/1/2)** | Configure **LWT (Last Will & Testament)** for disconnect detection, per-device mTLS/ACL topics, and consumer dedup on QoS 1. |
| Multi-user offline-capable document/canvas editing | **CRDT (Yjs / Automerge)** | Periodic state-vector snapshot compaction to bound tombstone memory; never use CRDTs for financial balances/inventory. |

## 3. Implementation Examples
```ts
// 1. Full-Jitter Exponential Backoff Reconnect Delay (Prevents Reconnect Thundering Herd)
export function computeJitteredReconnectMs(attempt: number, baseMs = 500, maxMs = 30_000, rand = Math.random): number {
  const expCeiling = Math.min(maxMs, baseMs * Math.pow(2, Math.min(attempt, 10)))
  return Math.round(rand() * expCeiling)
}

// 2. Bounded Slow-Consumer Socket Queue with Coalescing / Eviction
export function enqueueRealtimeFrame<T extends { readonly seq: number; readonly droppable: boolean }>(
  queue: T[],
  incoming: T,
  maxBufferSize = 128,
): 'ENQUEUED' | 'COALESCED_DROPPED' | 'DISCONNECT_SLOW_CONSUMER' {
  if (queue.length < maxBufferSize) {
    queue.push(incoming)
    return 'ENQUEUED'
  }
  const dropIdx = queue.findIndex((item) => item.droppable)
  if (dropIdx !== -1) {
    queue.splice(dropIdx, 1)
    queue.push(incoming)
    return 'COALESCED_DROPPED'
  }
  return 'DISCONNECT_SLOW_CONSUMER'
}
```

## 4. Best Practices
- Terminate or block active WebSocket/SSE streams immediately when an admin revokes the user's session or removes tenant membership (push a revocation control event over Redis Pub/Sub to all gateway nodes).
- Mark presence states (`online` / `lastSeen`) with an explicit server TTL lease so crashed clients transition to `offline` deterministically.

## 5. Anti-patterns (WRONG vs RIGHT)
- **WRONG:** Reconnecting disconnected WebSockets on a fixed `setInterval(..., 2000)` across 50,000 clients after a deploy (creates a synchronized reconnection DDoS storm).
- **RIGHT:** Use exponential backoff with **full jitter** (`rand(0, min(30s, 500ms * 2^attempt))`).
- **WRONG:** Buffering unbounded outbound messages in RAM for a client on a stalled 2G connection (causes Node/Go process OOM).
- **RIGHT:** Cap per-connection send queues, drop coalescable frames (cursor/typing), or close with a `1008`/`snapshot_required` resync code.

## 6. Production Considerations
- Tune OS & reverse-proxy file descriptor limits (`ulimit -n`, Nginx `worker_connections`, `proxy_read_timeout`) and test multi-node fan-out + mid-session revocation before production rollout.
