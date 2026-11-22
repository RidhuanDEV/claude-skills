---
name: shadow-realtime
description: "Realtime Transport & Client Synchronization Engineering. Use when designing WebSockets, Server-Sent Events (SSE), WebRTC/MQTT, long-lived streams, Last-Event-ID resumption cursors, mid-connection auth revocation, presence TTL leases, slow-consumer backpressure, multi-node pub/sub fan-out, or CRDT sync. Do NOT use for durable queue semantics (shadow-concurrency), stateless HTTP APIs (shadow-api), or third-party webhooks (shadow-integrate)."
---

# `/shadow-realtime` — Realtime Transport, Resumption, Revocation & Client Synchronization

- **Owner:** Live client connections, protocol selection ADR (`SSE` vs `WebSocket` vs `WebRTC` vs `MQTT` vs `Polling`), mid-connection auth revocation, `Last-Event-ID` resumption cursors, deduplication, multi-node pub/sub fan-out, slow-consumer backpressure, jittered reconnect storms, and CRDT vs transactional sync boundaries.
- **Boundaries:** Durable business job outbox/DLQ (`shadow-concurrency`), stateless REST/GraphQL (`shadow-api`), outbound payment/SMTP webhook adapters (`shadow-integrate`), and caching tiers (`shadow-cache`).

## Reference Guide

Load ONLY the 1–2 modular playbooks needed for the active realtime subtask:

| Module | Topic | Load When |
| :--- | :--- | :--- |
| [01-protocol-selection-sse-websocket-webrtc-mqtt.md](references/01-protocol-selection-sse-websocket-webrtc-mqtt.md) | Polling vs HTTP/2 SSE (`X-Accel-Buffering: no`) vs WebSocket vs WebRTC (TURN/SFU) vs MQTT (QoS/LWT), safe handshake tickets | Choosing a realtime protocol via ADR or fixing proxy buffering / handshake token leaks |
| [02-resumption-cursors-dedup-and-multi-node-fanout.md](references/02-resumption-cursors-dedup-and-multi-node-fanout.md) | Monotonic `Last-Event-ID` cursors, `snapshot_required` expired-cursor fallback, client dedup, Redis Streams/NATS multi-node fan-out | Preventing dropped/duplicate updates across reconnects or scaling beyond 1 replica |
| [03-mid-connection-auth-revocation-and-presence.md](references/03-mid-connection-auth-revocation-and-presence.md) | Push-driven revocation channels (`4403`), periodic lease re-checks, honest TTL presence bounds, zombie ping/pong sweeping | Closing stale unauthorized sockets on logout/revoke or fixing ghost online counts |
| [04-slow-consumer-backpressure-jitter-and-crdt-sync.md](references/04-slow-consumer-backpressure-jitter-and-crdt-sync.md) | Bounded outbound queues (`bufferedAmount`), coalescing vs `1008` eviction, full-jitter reconnect backoff, CRDT (`Yjs`) vs ACID boundaries | Preventing slow-consumer OOMs, deploy reconnect storms, or choosing CRDT vs server TX |
| [methodologies/WEBSOCKET-SSE-RESUMPTION-AND-BACKPRESSURE.md](methodologies/WEBSOCKET-SSE-RESUMPTION-AND-BACKPRESSURE.md) | Core resumption & backpressure methodology | Reviewing formal resumption & overflow mechanics |
| [playbooks/REALTIME-PROTOCOL-ADR-AND-RUNBOOK.md](playbooks/REALTIME-PROTOCOL-ADR-AND-RUNBOOK.md) | Realtime Protocol ADR & operations runbook template | Documenting protocol choice and operational thresholds |
| [evaluations.md](evaluations.md) | Graded specialist evaluation scenarios (`RT-EVAL-01..07`) | Auditing SSE vs WS judgment, revocation, backpressure, multi-node fan-out, and CRDT boundaries |

---

## 1. Preconditions, Security & Accuracy Rules
- **Revocation Gate:** A mid-session permission downgrade, logout, or token expiration MUST terminate or pause unauthorized event streams immediately — never continue pushing events on a stale open socket, and never pass long-lived JWTs in `?token=` URL query strings.
- **Presence Honesty:** Document explicit TTL-lease staleness bounds (`heartbeat_interval + grace_window`) rather than claiming exact real-time online counts across flaky mobile networks.

---

## 2. 6-Step Realtime Engineering Playbook
Read [`methodologies/WEBSOCKET-SSE-RESUMPTION-AND-BACKPRESSURE.md`](methodologies/WEBSOCKET-SSE-RESUMPTION-AND-BACKPRESSURE.md) and [`playbooks/REALTIME-PROTOCOL-ADR-AND-RUNBOOK.md`](playbooks/REALTIME-PROTOCOL-ADR-AND-RUNBOOK.md):
1. **Select Transport via ADR:** Prefer **SSE (`EventSource` + `Last-Event-ID` + `X-Accel-Buffering: no`)** for server -> client feeds behind standard HTTP/2 proxies; use **WebSocket** when bidirectional low-latency frames are required; use **Polling** for low-frequency status updates.
2. **Design Resumption & Deduplication:** Attach monotonic sequence/cursor IDs; replay missed bounded history on reconnect, skip duplicate `seq <= lastAppliedSeq` (`applied: false`), or trigger authorized full state resync (`snapshot_required`) if the cursor fell behind retention.
3. **Enforce Auth & Tenant ACL Per-Subscription:** Validate token & tenant ACL at handshake AND on push revocation channel events + periodic lease checks.
4. **Configure Multi-Node Fan-Out & Backpressure:** For multi-node subscribers, route tenant-scoped pub/sub fan-out across nodes (Redis Streams/PubSub or NATS). Enforce bounded per-socket outbound queues (`bufferedAmount` / `maxFrames`) with coalescing or clean slow-consumer eviction (`1008`/`snapshot_required`).
5. **Simulate Adversarial Disconnects:** Test 30-minute offline reconnect, duplicate frame delivery, token revocation mid-stream, and reverse-proxy idle timeout (`proxy_read_timeout` vs heartbeat ping).
6. **Verify Observability & Runbook:** Track active connections, disconnect reasons, drop rates, zombie prunes, and reconnect storms with full-jitter exponential backoff + staggered shutdown drains.

```powershell
python "shadow-realtime/scripts/realtime_transport_verifier.py" --self-test
python "shadow-realtime/scripts/realtime_transport_verifier.py" --verify-session path/to/session_spec.json
python -m unittest discover -s shadow-realtime/tests -v
```

---

## 3. Reading an Observed Session (`trace_version: 2`)

Capture redacted events at broker, authorization, and client boundaries. Give each logical subscription a stable connection ID across transport reconnects, and give each scope its tenant and stream. The v2 verifier consumes an ordered trace in that service's sequence space. It expects contiguous, monotonically increasing integers per stream; for sparse/global offsets, supply a service-aware adapter or classify continuity as unmeasured.

- Start with `trace_version: 2`, `topology: single_node|multi_node`, `queue_capacity`, and an ordered `events` array. A `connect` records node, tenant, stream, and the last applied cursor. `authorize` records the same tenant/stream. `emit` records tenant, stream, `seq`, and publisher node. `deliver` records the scope, `seq`, and actual boolean client `applied`. The verifier checks that a replayed frame did not reapply its effect.
- During disconnect/resume, compare the client's cursor with the acknowledged cursor and the server's earliest retained sequence. After resume, observe a fresh grant. An expired cursor requires an authorized scoped snapshot with a new cursor before stream delivery. Validate overflow behavior separately under the selected transport contract.
- To check revocation, record a valid grant and delivery, effective revoke, a new emission, and the dispatcher's observed block or delivery. Require a measured queue depth. For multi-node topology, at least one applied frame must have crossed a node boundary. The fixture in [recovery tests](tests/test_session_cli.py) shows the fields and transitions.
- Distinguish a behavioral violation (`FAIL`) from an absent observation (`INCOMPLETE`). The former flat session format remains readable as incomplete evidence. A passing trace is evidence for the supplied sequence only. Window duration, load, connection fairness, jitter distribution, graph-wide propagation, and recovery latency require their own measurements.

When handing off, attach the trace revision, service contract, emitter/consumer instrumentation, selected topology, recovery decision, and uncovered conditions. Never reconstruct observed `applied` or `blocked` values from design intentions.
