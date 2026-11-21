# OpenTelemetry Instrumentation, Golden Signals & Structured Logging Blueprints

## 1. Core Concepts
Production observability links **RED/USE Golden Signals**, **W3C `traceparent` distributed traces**, and **context-propagated structured JSON logs** (`requestId`, `traceId`, `tenantId`, `actorSub`) so any user-reported error Reference ID resolves to an exact trace and log timeline within seconds — without leaking secrets or blowing up ingestion costs.

## 2. Technical Rules & Stack Blueprint Matrix

| Stack | Standard Logger | Context Propagation | Mandatory Redaction & Hygiene |
| :--- | :--- | :--- | :--- |
| **Node.js / TypeScript** | `pino` (+ `pino-http`) | `AsyncLocalStorage` (`node:async_hooks`) injected via `mixin()` | Redact `req.headers.authorization`, `cookie`, `*.password`, `*.token`, `*.secret`, `*.nik`, `*.otp`; 0 raw `console.log`. |
| **Python** | `structlog` (`JSONRenderer`) | `structlog.contextvars.bind_contextvars(request_id=...)` | Processor redacting sensitive keys + stripping `\r\n` log-forging characters. |
| **Go** | `log/slog` (`NewJSONHandler`) | `context.Context` + custom `slog.Handler` extracting trace/request IDs | `ReplaceAttr` masking secret/PII attributes before serialization. |
| **PHP / Laravel** | Monolog (`JsonFormatter`) | `Context::add('request_id', ...)` + middleware wide-event | Monolog processor redacting auth headers & sensitive form fields. |

## 3. Implementation Examples
```ts
// Production-Ready Node/TS Context-Propagated Structured Logger + Wide-Event Middleware (Zero External Deps Demo)
import { AsyncLocalStorage } from 'node:async_hooks'
import crypto from 'node:crypto'

export interface RequestLogContext {
  readonly requestId: string
  readonly traceparent: string
  readonly tenantId?: string
  readonly actorSub?: string
}

export const logContextStore = new AsyncLocalStorage<RequestLogContext>()
const SENSITIVE_KEY_RE = /^(?:authorization|cookie|password|token|secret|apikey|nik|otp|creditcard)$/i

function redactValue(value: unknown): unknown {
  if (typeof value === 'string') return value.replace(/[\r\n]+/g, ' ')
  if (!value || typeof value !== 'object') return value
  if (Array.isArray(value)) return value.map(redactValue)
  const out: Record<string, unknown> = {}
  for (const [k, v] of Object.entries(value)) {
    out[k] = SENSITIVE_KEY_RE.test(k) ? '[REDACTED]' : redactValue(v)
  }
  return out
}

function redactRecord(fields: Record<string, unknown>): Record<string, unknown> {
  const out: Record<string, unknown> = {}
  for (const [k, v] of Object.entries(fields)) {
    out[k] = SENSITIVE_KEY_RE.test(k) ? '[REDACTED]' : redactValue(v)
  }
  return out
}

export function logStructured(level: 'info' | 'warn' | 'error', event: string, fields: Record<string, unknown> = {}): void {
  const ctx = logContextStore.getStore()
  const payload = {
    ts: new Date().toISOString(),
    level,
    event,
    ...(ctx ?? {}),
    ...redactRecord(fields),
  }
  process.stdout.write(JSON.stringify(payload) + '\n')
}
```

## 4. Best Practices
- Emit **one canonical wide-event JSON log** per completed HTTP request (`http.request.completed`) with `method`, `routeTemplate` (`/api/v1/orders/:id` — NEVER raw UUID path), `statusCode`, `durationMs`, and `errorCode`.
- Use **Tail-Based OTel Sampling** (keep 100% of `5xx` errors and `> p95` slow traces; sample 5–10% of fast healthy `2xx` traces) and log `/health` probes at `debug` only.

## 5. Anti-patterns (WRONG vs RIGHT)
- **WRONG:** Scattering `console.log("User paid:", req.headers, body)` in backend controllers (leaks Bearer tokens/PII, lacks `requestId`, and blocks stdout formatting) or attaching `userId`/`requestId` as Prometheus metric labels (causes cardinality explosion).
- **RIGHT:** Put high-cardinality IDs (`requestId`, `userId`, `tenantId`) inside **structured JSON logs and OTel spans**, keep Prometheus labels low-cardinality (`route_template`, `status_class`, `method`), and keep immutable business/security audit logs in an append-only database table.

## 6. Production Considerations
- Always return `X-Request-Id` in HTTP response headers and display `Ref ID: <requestId>` in frontend error banners so support tickets correlate 1:1 with backend logs.
