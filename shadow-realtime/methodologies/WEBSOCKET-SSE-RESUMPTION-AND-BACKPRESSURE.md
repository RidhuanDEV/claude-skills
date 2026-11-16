# WebSocket vs SSE, Resumption Cursors, Auth Revocation & Backpressure Methodology

## 1. Protocol Trade-Off Matrix
| Protocol | Best Fit | Built-In Resume | Proxy / LB Behavior | Limitations |
|---|---|---|---|---|
| **Server-Sent Events (SSE)** | Unidirectional live feeds, notifications, AI token streaming | Yes (`Last-Event-ID` header per WHATWG spec) | Standard HTTP/1.1–2; watch proxy buffering (`X-Accel-Buffering: no`) | Text-only UTF-8; browser 6-conn HTTP/1.1 limit (fine on HTTP/2) |
| **WebSocket (RFC 6455)** | Bidirectional chat, collaborative cursors, gaming, interactive telemetry | Manual (`seq` / `cursor` in app frames) | Needs `Upgrade` header & idle timeout tuning; sticky or pub/sub broker | No native HTTP header per frame after handshake |
| **Short/Long Polling** | Low-frequency status dashboards | Client fetches `since_ts` / `cursor` | Stateless horizontal scaling | Higher latency/overhead at high frequency |

## 2. Adversarial Scenarios & Mitigations
1. **Token Expiry or Permission Revocation Mid-Connection:** Subscribe socket gateway to auth-revocation events (`user_revoked:{id}`) + re-check session TTL on every heartbeat; close with `4401`/`4403` and flush zero queued tenant events after revocation timestamp.
2. **Offline 30 Minutes & Reconnect Storm:** Server retains bounded replay buffer (e.g. last 5 min / N events). If `client_cursor < oldest_retained_cursor`, emit explicit `RESYNC_SNAPSHOT` frame instead of silent gap; clients use full jittered exponential backoff (`min 1s..max 30s`).
3. **Slow Consumer:** Bounded outbound buffer per socket (`max_queue_frames`); drop/disconnect slow client cleanly so healthy peers are unaffected.
4. **Duplicate Events:** Assign deterministic `(stream_id, sequence_id)` so client cache (`TanStack Query` / local store) deduplicates idempotently.
