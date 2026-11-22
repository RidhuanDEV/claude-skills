# 03 — Structured JSON Logging, Canonical Wide Events & PII Redaction

## 1. Purpose & Activation Conditions
Design production-grade, non-blocking **structured JSON logging** with automatic request/trace context propagation, **canonical wide-event** emission (one rich event per completed request), fail-closed PII/secret redaction, anti-CRLF sanitization, and strict separation from immutable audit trails. Activate when setting up backend logging, replacing scattered `console.log` calls, or remediating secret/PII log leaks under UU PDP / OWASP ASVS.

## 2. Prerequisites
- For brownfield codebases: inspect the existing logger first and harden it in-place (NEVER install a second duplicate logging library).
- Inventory of sensitive fields regulated by security policy and UU No. 27/2022 (`authorization`, `cookie`, `password`, `token`, `secret`, `apiKey`, `nik`, `otp`, `creditCard`, health/biometric fields).

## 3. Technical Principles & Constraints
- **Canonical Wide Event (1 Request = 1 Rich Structured Log):** Emit one `http.request.completed` JSON line at response finish carrying `ts`, `level`, `event`, `requestId`, `traceId`, `tenantId`, `actorSub`, `method`, `routeTemplate`, `statusCode`, `durationMs`, `dbQueryCount`, and `errorCode`. Avoid printing 15 fragmented `"entering controller"`, `"got user"`, `"calling db"` lines per request.
- **Automatic Context Propagation:** Bind `requestId` and `traceId` at the HTTP/queue boundary (`AsyncLocalStorage` in Node, `contextvars` in Python, `context.Context` in Go, `Context` facade in Laravel) so deep service logs inherit correlation automatically without polluting function signatures.
- **Fail-Closed Redaction + Anti-CRLF Sanitization:** Redact sensitive keys recursively (replace with `"[REDACTED]"`), scrub raw `Bearer <token>` / JWT patterns in free-text strings, and replace `\r`/`\n` with spaces so attackers cannot forge fake JSON log lines via user inputs (e.g., `username`).
- **4xx vs 5xx Level Hygiene:** Log expected client errors (`400`, `404`, `422`) at `info` or `warn` (never `error` with scary stack traces) and unexpected server faults (`5xx`) at `error` with full structured cause + stack. Keep `/health` and `/ready` at `debug` (or suppress on `200`).
- **Operational Logs != Immutable Audit Logs:** Ephemeral Loki/CloudWatch logs rotate in 14–30 days and are mutable/sampled; compliance audit trails (login, RBAC change, data export, payment approval) MUST live in an append-only database audit table (`/shadow-auth`, `/shadow-privacy`).

## 4. Architecture & Implementation

### Polyglot Logger & Context Propagation Blueprint Matrix

| Stack | Standard Logger | Context Propagation | Mandatory Redaction & Hygiene |
| :--- | :--- | :--- | :--- |
| **Node.js / TypeScript** | `pino` (+ `pino-http`) | `AsyncLocalStorage` (`node:async_hooks`) injected via `mixin()` | Redact `req.headers.authorization`, `cookie`, `*.password`, `*.token`, `*.secret`, `*.nik`, `*.otp`; zero raw `console.log` in prod routes. |
| **Python** | `structlog` (`JSONRenderer`) | `structlog.contextvars.bind_contextvars(request_id=..., trace_id=...)` | Custom processor redacting sensitive keys + stripping `\r\n` log-forging characters. |
| **Go** | `log/slog` (`NewJSONHandler`) | `context.Context` + custom `slog.Handler` extracting trace/request IDs | `ReplaceAttr` masking secret/PII attributes before JSON serialization. |
| **PHP / Laravel** | Monolog (`JsonFormatter`) | `Context::add('request_id', ...)` + middleware wide-event emitter | Monolog processor redacting auth headers & sensitive form fields before write. |

```ts
// Production-Ready Node/TS Context-Propagated Structured Logger + Wide-Event Emitter (0 any, 0 casts)
import { AsyncLocalStorage } from 'node:async_hooks'

export interface RequestLogContext {
  readonly requestId: string
  readonly traceId: string
  readonly traceparent: string
  readonly tenantId?: string
  readonly actorSub?: string
}

export const logContextStore = new AsyncLocalStorage<RequestLogContext>()

const SENSITIVE_KEY_RE =
  /^(?:authorization|cookie|set-cookie|password|passwd|token|access_token|refresh_token|secret|api_?key|nik|otp|credit_?card|cvv)$/i
const BEARER_OR_JWT_RE =
  /(?:Bearer\s+[A-Za-z0-9._\-~+/]+=*|eyJ[A-Za-z0-9_\-]{10,}\.[A-Za-z0-9_\-]{10,}\.[A-Za-z0-9_\-]{5,})/g

function sanitizeString(input: string): string {
  return input.replace(/[\r\n]+/g, ' ').replace(BEARER_OR_JWT_RE, '[REDACTED_TOKEN]')
}

function redactValue(value: unknown): unknown {
  if (typeof value === 'string') return sanitizeString(value)
  if (value === null || typeof value !== 'object') return value
  if (Array.isArray(value)) return value.map(redactValue)
  const out: Record<string, unknown> = {}
  for (const [k, v] of Object.entries(value)) {
    out[k] = SENSITIVE_KEY_RE.test(k) ? '[REDACTED]' : redactValue(v)
  }
  return out
}

export function logStructured(
  level: 'debug' | 'info' | 'warn' | 'error',
  event: string,
  fields: Record<string, unknown> = {},
): void {
  const ctx = logContextStore.getStore()
  const sanitizedFields: Record<string, unknown> = {}
  for (const [k, v] of Object.entries(fields)) {
    sanitizedFields[k] = SENSITIVE_KEY_RE.test(k) ? '[REDACTED]' : redactValue(v)
  }
  const payload = {
    ts: new Date().toISOString(),
    level,
    event: sanitizeString(event),
    ...(ctx ?? {}),
    ...sanitizedFields,
  }
  process.stdout.write(JSON.stringify(payload) + '\n')
}
```

### Frontend `Ref ID` Correlation Loop
Always echo `X-Request-Id` on every HTTP response header (including `4xx` and `5xx` error middleware). Frontend error boundaries and toast banners display `Ref ID: req_01J9X2K...` (never raw stack traces or SQL messages), enabling instant 1:1 lookup in Loki/OpenSearch from customer support screenshots.

## 5. Platform/Vendor Variations
- **Grafana Loki / Promtail / Alloy:** Keep Loki **stream labels** ultra-low cardinality (`service`, `env`, `level`) — NEVER turn `requestId`, `traceId`, or `tenantId` into Loki stream labels! Query them via LogQL structured metadata or JSON parser (`{service="checkout"} | json | requestId="req_01J9..."`).
- **AWS CloudWatch Logs / GCP Cloud Logging:** Emit single-line JSON to `stdout` (`severity` field for GCP, `level` for CloudWatch); avoid multi-line pretty-printed logs that split one stack trace into 30 disconnected log events.
- **Nginx / Caddy Reverse Proxy:** Configure JSON access logs capturing `$http_x_request_id` (falling back to generated `$request_id`), `$upstream_response_time`, `$status`, and `$uri` (stripped of query strings so `?token=...` never lands in proxy logs).

## 6. Decision Matrix & Trade-Offs

| Logging Pattern | Storage Volume | Query Speed | Diagnostic Power | When to Use |
| :--- | :--- | :--- | :--- | :--- |
| **Canonical Wide Event (`1/req`)** | Low–Medium | Fast | Very High | Default for all production HTTP APIs & queue workers |
| **Verbose Step-by-Step `info` Logs** | Very High (5–15x cost) | Slow | Noisy | Avoid in prod; restrict to local dev or scoped `debug` sampling |
| **Append-Only DB Audit Table** | Low (write-only business events) | Transactional | Compliance-grade | Mandatory for auth, RBAC, finance, UU PDP DSAR events |
| **Raw `console.log(req)`** | Unbounded | Broken | Dangerous (PII leak) | **NEVER** in production services |

## 7. Real Production Scenario
During a financial compliance audit, auditors discovered `Authorization: Bearer eyJ...` and 16-digit customer `nik` values stored in plain text across 14 days of Loki logs because an exception middleware logged `JSON.stringify(req)` on validation failures. Switching to a single wide-event `pino` logger with `AsyncLocalStorage`, recursive key redaction + JWT scrubbing, and removing raw `req.body` logging cut monthly log ingestion by 68% and passed re-audit with zero PII findings.

## 8. Failure Modes & Edge Cases
- **WRONG:** Logging `req.originalUrl` verbatim when external OAuth callbacks or magic-link routes carry `?code=...` or `?token=...`.
  **RIGHT:** Log parameterized `routeTemplate` (`/api/v1/auth/callback`) and explicitly allowlist safe query parameters instead of dumping raw query strings.
- **WRONG:** Passing `userId` or `requestId` as Loki **index/stream labels** instead of JSON body fields or structured metadata.
  **RIGHT:** Keep Loki stream labels to `<= 4` static dimensions (`app`, `env`, `namespace`, `level`).
- **WRONG:** Writing logs synchronously to local container disk files without rotation (fills root volume -> crashes DB/app).
  **RIGHT:** Write non-blocking JSON to `stdout`/`stderr` and let the container runtime / log collector ship and rotate with bounded disk buffers.

## 9. Testing & Verification
- Run `python shadow-observe/scripts/telemetry_hygiene_verifier.py --check-log-sample sample.json` in CI against captured integration-test log output to verify schema, `requestId`/`traceId` presence, parameterized `routeTemplate`, zero secret leaks, and zero CRLF injection.
- Write unit tests feeding hostile inputs (`"admin\n{\"level\":\"info\"}"`, `"Bearer secret123"`, `{ nik: "3174..." }`) into the logger wrapper and asserting `[REDACTED]` output.

## 10. Operational Considerations
- Support dynamic log-level overrides (e.g., temporarily raising one service replica to `debug` via env/flag for 10 minutes) without requiring a full redeploy.
- Retain operational logs for `14–30` days (hot) and archive compliance audit tables separately per regulatory retention schedules (`/shadow-privacy`).

## 11. Authoritative References
- OWASP Logging Cheat Sheet — *Sanitization, CRLF Prevention & Sensitive Data Exclusion*.
- UU No. 27 Tahun 2022 (UU PDP) Pasal 4 & 35 — Protection of specific & general personal data in operational telemetry.
- Pino / Structlog / Go `log/slog` Official Documentation — High-throughput non-blocking JSON serialization & redaction.

## 12. Limitations & When NOT to Use
- Do NOT store multi-megabyte request/response payloads or base64 uploads in application logs; log `payloadBytes` and `sha256` hash only.
- Do NOT use Loki/CloudWatch logs as an analytics event warehouse — use `/shadow-analytics` pipelines for product funnels and cohorts.
