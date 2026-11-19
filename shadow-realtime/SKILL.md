---
name: shadow-realtime
description: "Realtime Transport & Client Synchronization Engineering. Use when designing WebSockets, Server-Sent Events (SSE), long-lived streams, Last-Event-ID resumption cursors, mid-connection auth revocation, presence accuracy, slow-consumer backpressure, or multi-node pub/sub fan-out. Do NOT use for durable queue semantics (shadow-concurrency), stateless HTTP APIs (shadow-api), or third-party webhooks (shadow-integrate)."
---

# `/shadow-realtime` — Realtime Transport & Client Synchronization

- **Owner:** Live client connections, protocol choice (`WebSocket` vs `SSE` vs `Polling`), auth renewal/revocation, resumption cursors, deduplication, and backpressure.
- **Boundaries:** Durable business job outbox/DLQ (`shadow-concurrency`), stateless REST (`shadow-api`), outbound payment/SMTP adapters (`shadow-integrate`).

## 1. Preconditions, Security & Accuracy Rules
- **Revocation Gate:** A mid-session permission downgrade or token expiration MUST terminate or pause unauthorized event streams immediately — never continue pushing events on a stale socket.
- **Presence Honesty:** Document explicit staleness bounds (e.g., `heartbeat_interval + grace_window`) rather than claiming exact real-time online counts across mobile networks.

## 2. 6-Step Realtime Engineering Playbook
Read [`methodologies/WEBSOCKET-SSE-RESUMPTION-AND-BACKPRESSURE.md`](methodologies/WEBSOCKET-SSE-RESUMPTION-AND-BACKPRESSURE.md) and [`playbooks/REALTIME-PROTOCOL-ADR-AND-RUNBOOK.md`](playbooks/REALTIME-PROTOCOL-ADR-AND-RUNBOOK.md):
1. **Select Transport via ADR:** Prefer **SSE (`EventSource` + `Last-Event-ID`)** for server->client feeds behind standard HTTP proxies; use **WebSocket** when bidirectional low-latency frames are required; use **Polling** for low-frequency status updates.
2. **Design Resumption & Deduplication:** Attach monotonic sequence/cursor IDs; replay missed bounded history on reconnect or trigger full state resync (`snapshot_required`) if cursor fell behind retention window.
3. **Enforce Auth & Tenant ACL Per-Subscription:** Validate token & tenant ACL at handshake AND on periodic refresh / revocation channel events.
4. **Configure Multi-Node Fan-Out & Backpressure:** For multi-node subscribers, trace the producer and receiving node across the existing fan-out mechanism. A single-node service can use its local stream. Choose queue capacity and overflow behavior from the service contract; a slow consumer must have a bounded recovery path.
5. **Simulate Adversarial Disconnects:** Test 30-minute offline reconnect, duplicate frame delivery, token revocation mid-stream, and reverse-proxy idle timeout (`proxy_read_timeout` vs heartbeat ping).
6. **Verify Observability & Runbook:** Track active connections, disconnect reasons, drop rates, and reconnect storms with jittered exponential backoff.

```powershell
python "shadow-realtime/scripts/realtime_transport_verifier.py" --self-test
python "shadow-realtime/scripts/realtime_transport_verifier.py" --verify-session path/to/session_spec.json
```

## Reading an observed session

Capture redacted events at broker, authorization and client boundaries. Give each logical subscription a stable connection ID across transport reconnects, and give each scope its tenant and stream. The v2 verifier consumes an ordered trace in that service's sequence space. It expects contiguous, monotonically increasing integers per stream; for sparse/global offsets, supply a service-aware adapter or classify continuity as unmeasured.

- Start with `trace_version: 2`, `topology: single_node|multi_node`, `queue_capacity` and an ordered `events` array. A connect records node, tenant, stream and the last applied cursor. Authorize records the same tenant/stream. Emit records tenant, stream, seq and publisher node. Deliver records the scope, seq and actual boolean client `applied`. The verifier checks that a replayed frame did not reapply its effect.
- During disconnect/resume, compare the client's cursor with the acknowledged cursor and the server's earliest retained sequence. After resume, observe a fresh grant. An expired cursor requires an authorized scoped snapshot with a new cursor before stream delivery. Validate overflow behavior separately under the selected transport contract.
- To check revocation, record a valid grant and delivery, effective revoke, a new emission, and the dispatcher's observed block or delivery. Require a measured queue depth. For multi-node topology, at least one applied frame must have crossed a node boundary. The fixture in [recovery tests](tests/test_session_cli.py) shows the fields and transitions.
- Distinguish a behavioral violation (`FAIL`) from an absent observation (`INCOMPLETE`). The former flat session format remains readable as incomplete evidence. A passing trace is evidence for the supplied sequence only. Window duration, load, connection fairness, jitter distribution, graph-wide propagation and recovery latency require their own measurements.

When handing off, attach the trace revision, service contract, emitter/consumer instrumentation, selected topology, recovery decision and uncovered conditions. Never reconstruct observed `applied` or `blocked` values from design intentions.
