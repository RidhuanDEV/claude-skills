# BACKEND — APIs, Services, Jobs & Integrations

## 1. Layer responsibilities

- **Controller/handler**: parse request → validate → call use case → map domain errors to HTTP → consistent response →
  log with request ID. No complex business logic, no direct DB queries when the codebase uses services/repositories,
  never return raw exceptions, never ignore the auth context.
- **Service/use case**: business workflows, orchestration, transaction boundaries.
- **Repository**: persistence only.
- **Validator/schema/DTO**: input validation; external contracts separate from internal models.
Do not put the whole application in controllers, and do not create pass-through services with no purpose.

## 2. API design

- Resource-oriented REST with correct HTTP semantics:
  `GET /users`, `GET /users/:id`, `POST /users`, `PATCH /users/:id`, `DELETE /users/:id`.
- Status codes: 200, 201 (+Location), 204, 400 malformed, 401 unauthenticated, 403 forbidden, 404, 409 conflict,
  422 validation, 429 rate limited, 500 unexpected, 502/503/504 dependency issues.
  Never return 200 for a failed operation.
- Version public APIs from the start (`/v1`, or header-based). Additive changes first; never silently change field
  meaning, request/response shape or auth behavior for existing consumers; deprecate with a migration window.
- Collections are always paginated. Offset for small/admin lists; cursor for large or fast-changing data.
  Ordering must be deterministic (add a unique tiebreaker such as `id`). Enforce a max page size.
- Critical mutations (payments, orders, anything clients retry) accept an `Idempotency-Key`.
- Propagate a request/correlation ID (`X-Request-Id` or W3C `traceparent`) and return it in errors.

Response envelope (keep it predictable across endpoints):
```json
{ "data": {}, "meta": { "page": 1, "pageSize": 20, "total": 125 } }
```
Error shape (or RFC 9457 Problem Details where the stack standardizes on it):
```json
{ "error": { "code": "VALIDATION_ERROR", "message": "Email is invalid", "details": [], "requestId": "req_123" } }
```
Never leak stack traces, SQL errors, internal paths, hostnames, secrets or library versions.

## 3. Validation

Validate at every system boundary, server-side, regardless of frontend validation: required fields, types, lengths,
numeric ranges, formats (dates, emails, UUIDs), enums/allowlists, nested depth, array sizes, payload size, encoding,
file size/type, and **ownership** of referenced resources. Reject unknown fields for sensitive DTOs (mass assignment).
Client-side validation is UX; server-side validation is protection.

## 4. Error model

Map domain errors to a small taxonomy: `ValidationError`, `AuthenticationError`, `AuthorizationError`, `NotFoundError`,
`ConflictError`, `RateLimitError`, `DependencyError`, `InternalError`. One global error handler/filter/middleware converts
them to the error shape. Log unexpected errors once, with context, at the boundary — not at every layer.

## 5. Idempotency, retries, timeouts

- Anything retryable (payments, webhooks, jobs, order creation, external calls) must not produce duplicate side effects:
  idempotency keys stored with the result, unique constraints, or state checks.
- Retry only transient failures (timeouts, 429, 502/503/504, connection resets), bounded attempts, exponential backoff
  with jitter (e.g. 1s, 2s, 4s, 8s ± random). Never retry validation or authorization failures. Never retry forever.
- Every outbound call has an explicit timeout matched to the operation and user experience; never rely on library defaults.
- Propagate cancellation (context, AbortSignal, CancellationToken) so abandoned requests stop work.

## 6. External APIs and webhooks

Treat third parties as unreliable: timeouts, rate limits, auth expiry, retries, fallback, schema drift, partial failure.
Validate their responses; do not assume they honor their docs.

Webhook consumers: (1) verify signature/authenticity with constant-time compare and timestamp tolerance,
(2) validate payload, (3) dedupe by event ID, (4) acknowledge fast (2xx), (5) process asynchronously when heavy,
(6) record processing status. Providers will retry and may deliver out of order.

## 7. Queues and background jobs

Use for slow, retryable, bursty work that should not block the request. Each worker defines: max concurrency,
retry policy, DLQ, poison-message handling, ack/visibility timeout, idempotency key, graceful shutdown, and metrics
(processed, failed, retried, latency, queue depth). Queues and in-memory buffers are bounded.
Use the **outbox pattern** when a DB change and a published message must both happen.
Never fire-and-forget critical work inside a request.

## 8. Concurrency and consistency

Where multiple requests can touch the same resource (stock, counters, balances, bookings, duplicate submits),
protect the invariant with the simplest correct tool: atomic update (`UPDATE … SET qty = qty - 1 WHERE qty > 0`),
unique constraint, transaction with the right isolation, row lock (`SELECT … FOR UPDATE`), optimistic locking (version
column), idempotency key, or a distributed lock only when the above cannot work. Never do check-then-act without protection.

## 9. Realtime

- **SSE** (server → client, one-way): notifications, progress, live dashboards. Handle reconnection and `Last-Event-ID`,
  heartbeats, proxy buffering/timeouts (disable buffering in Nginx), per-connection auth, connection limits, cleanup on disconnect.
- **WebSockets** only for genuine bidirectional needs: auth on connect, heartbeat, reconnection with backoff,
  backpressure, room membership, message ordering, and shared pub/sub (e.g. Redis) when running multiple instances.
- Prefer polling when updates are rare.

## 10. Rate limiting & abuse

Protect login, OTP, password reset, search, export, upload and expensive endpoints. Dimensions: IP, user, API key,
tenant, endpoint. Return 429 with `Retry-After`. Derive client IP only from trusted proxy headers.

## 11. Money, time, search, i18n

- Money: never binary floating point. Integer minor units or decimal types; explicit currency and rounding rules
  (e.g. IDR Rp10.000 → `10000`). Financial correctness beats convenience. Never trust client-reported payment status;
  verify with the provider, verify webhook signatures, persist provider references, handle duplicate notifications.
- Time: store UTC (`timestamptz`), convert at the presentation edge, be explicit about business timezone (e.g. Asia/Jakarta),
  compare datetime values not formatted strings, define inclusive/exclusive ranges, beware DST where relevant.
- Search: case sensitivity, index use, partial match, tokenization, ranking, language, typos. Move to a search engine
  when relational `LIKE` stops meeting requirements.
- i18n: do not hardcode date/number/currency formats or user-facing strings when multiple locales are possible.

## 12. Configuration

Configuration is separate from code, comes from env/secret manager, is validated at startup (fail fast on missing
critical values), and never ships secrets to clients. Feature flags for risky rollouts are removed after rollout.

## 13. Backend checklist

Validation at boundary · authorization per resource · consistent errors · pagination with max size · timeouts on all
outbound calls · bounded retries · idempotency on critical mutations · transactions sized correctly (no network calls
inside) · no N+1 · structured logs with request ID · metrics on critical flows · rate limits on sensitive endpoints ·
graceful shutdown · health/readiness endpoints.
