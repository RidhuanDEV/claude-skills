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
4. **Configure Multi-Node Fan-Out & Backpressure:** Use Redis Pub/Sub / NATS / Kafka fan-out (never in-memory-only arrays behind load balancers); bound per-client send queues so one slow consumer drops/resyncs instead of OOMing the server.
5. **Simulate Adversarial Disconnects:** Test 30-minute offline reconnect, duplicate frame delivery, token revocation mid-stream, and reverse-proxy idle timeout (`proxy_read_timeout` vs heartbeat ping).
6. **Verify Observability & Runbook:** Track active connections, disconnect reasons, drop rates, and reconnect storms with jittered exponential backoff.

```powershell
python "shadow-realtime/scripts/realtime_transport_verifier.py" --self-test
python "shadow-realtime/scripts/realtime_transport_verifier.py" --verify-session path/to/session_spec.json
```
