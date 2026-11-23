# 03 — Fail-Fast Startup Config, Structured JSON Logging, Health Probes & Graceful Shutdown

## 1. Purpose & Activation Conditions
Wire the **4 day-one production operability foundations** into every greenfield HTTP service and async worker — **fail-fast startup environment validation**, **non-blocking redacted structured JSON logging with `X-Request-Id` propagation**, **clean `/healthz` vs `/readyz` separation**, and **bounded `SIGTERM`/`SIGINT` graceful shutdown** — so the very first commit is observable, leak-free, and safe to deploy. Activate on every `http` and `worker` bootstrap.

## 2. Prerequisites
- Scaffolded `http` or `worker` vertical slice (`01`, `02`).
- Zero duplicate logger check: if extending a brownfield service, reuse and harden the existing logger instead of adding a second one!

## 3. Technical Principles & Constraints
- **1. Fail-Fast Startup Configuration Validation:**
  - Parse and validate ALL required environment variables (`PORT`, `NODE_ENV`, `DATABASE_URL`, `LOG_LEVEL`, secrets) **once at process boot BEFORE binding any TCP socket**.
  - **NEVER** scatter `process.env.SECRET!` non-null assertions or `Boolean(process.env.FLAG)` bugs inside runtime request handlers — if a required env var is missing or malformed (`PORT="abc"`), fail immediately at startup with a clear non-secret diagnostic message (`exit 1`)!
  - Always ship a synchronized `.env.example` containing safe dummy placeholders (NEVER real secrets!).
- **2. Non-Blocking Structured JSON Logger + `X-Request-Id` + Fail-Closed Redaction (`BACKEND.md §12`):**
  - Wire the stack-idiomatic JSON logger from day one: **`pino`** (`AsyncLocalStorage` in Node/TS), **`structlog`** (`contextvars` in Python), **`log/slog`** (`NewJSONHandler` in Go), or **Monolog `JsonFormatter`** (PHP/Laravel).
  - Emit one canonical wide-event JSON log per completed HTTP request (`method`, `routeTemplate`, `statusCode`, `durationMs`, `requestId`, `errorCode`).
  - Redact `authorization`, `cookie`, `password`, `token`, `secret`, `apiKey`, `nik`, `otp` fail-closed (`[REDACTED]`), strip `\r\n` log injection, and emit **ZERO raw `console.log`** in production routes!
- **3. Clean Liveness (`/healthz`) vs Readiness (`/readyz`) Separation:**
  - Add health endpoints ONLY when the runtime serves HTTP and a consumer/orchestrator needs them.
  - `/healthz` (Liveness): checks ONLY that the process/event loop is alive -> returns `200`. NEVER pings external APIs or optional caches!
  - `/readyz` (Readiness): checks mandatory local/DB dependencies with short timeouts (`<= 1500ms`) and returns `releaseSha`. An optional cache outage MUST NOT mark a healthy degradable service `503` if it can safely degrade (`/shadow-resilience`)!
- **4. Bounded Graceful Shutdown (`SIGTERM` / `SIGINT`):**
  - Stop accepting new HTTP requests / queue polls -> allow in-flight requests to drain cleanly -> close DB/Redis pools -> exit `0` — guarded by a hard fallback deadline timer (`10–15s`, `.unref()`ed) so a stuck socket cannot hang container stop forever!

## 4. Architecture & Implementation

```ts
// Strict TypeScript Greenfield HTTP Wiring: Fail-Fast Env + Redacted Logger + Graceful Shutdown (0 any, 0 casts, 0 !)
import { AsyncLocalStorage } from 'node:async_hooks'

export interface AppConfig {
  readonly port: number
  readonly nodeEnv: 'development' | 'test' | 'production'
  readonly logLevel: 'debug' | 'info' | 'warn' | 'error'
  readonly releaseSha: string
}

export function parseStartupConfig(raw: Readonly<Record<string, string | undefined>>): AppConfig {
  const portStr = raw['PORT'] ?? '3000'
  const port = Number.parseInt(portStr, 10)
  if (!Number.isInteger(port) || port < 1 || port > 65535) {
    throw new Error(`INVALID_CONFIG: PORT must be integer 1..65535, got '${portStr}'`)
  }
  const env = raw['NODE_ENV'] ?? 'development'
  if (env !== 'development' && env !== 'test' && env !== 'production') {
    throw new Error(`INVALID_CONFIG: Unsupported NODE_ENV '${env}'`)
  }
  const lvl = raw['LOG_LEVEL'] ?? 'info'
  if (lvl !== 'debug' && lvl !== 'info' && lvl !== 'warn' && lvl !== 'error') {
    throw new Error(`INVALID_CONFIG: Unsupported LOG_LEVEL '${lvl}'`)
  }
  return {
    port,
    nodeEnv: env,
    logLevel: lvl,
    releaseSha: raw['RELEASE_SHA'] ?? 'local-dev',
  }
}

export interface RequestCorrelation {
  readonly requestId: string
  readonly traceId?: string
}

export const correlationStore = new AsyncLocalStorage<RequestCorrelation>()

const REDACT_KEY_RE = /^(?:authorization|cookie|password|token|secret|apikey|nik|otp)$/i

export function writeJsonLog(
  level: 'debug' | 'info' | 'warn' | 'error',
  event: string,
  fields: Readonly<Record<string, unknown>> = {},
): void {
  const ctx = correlationStore.getStore()
  const safeFields: Record<string, unknown> = {}
  for (const [k, v] of Object.entries(fields)) {
    safeFields[k] = REDACT_KEY_RE.test(k)
      ? '[REDACTED]'
      : typeof v === 'string'
        ? v.replace(/[\r\n]+/g, ' ')
        : v
  }
  const line = JSON.stringify({
    ts: new Date().toISOString(),
    level,
    event,
    ...(ctx ?? {}),
    ...safeFields,
  })
  process.stdout.write(`${line}\n`)
}

export function registerGracefulShutdown(
  stopAccepting: () => Promise<void>,
  closeResources: () => Promise<void>,
  hardTimeoutMs = 10_000,
): void {
  let active = false
  const handleSignal = async (signal: string): Promise<void> => {
    if (active) return
    active = true
    writeJsonLog('info', 'process.shutdown.started', { signal })
    const timer = setTimeout(() => {
      writeJsonLog('error', 'process.shutdown.forced_timeout', { hardTimeoutMs })
      process.exit(1)
    }, hardTimeoutMs)
    timer.unref()
    try {
      await stopAccepting()
      await closeResources()
      clearTimeout(timer)
      writeJsonLog('info', 'process.shutdown.completed', { signal })
      process.exit(0)
    } catch (err: unknown) {
      writeJsonLog('error', 'process.shutdown.failed', {
        signal,
        reason: err instanceof Error ? err.message : 'unknown_shutdown_error',
      })
      process.exit(1)
    }
  }
  process.on('SIGTERM', () => void handleSignal('SIGTERM'))
  process.on('SIGINT', () => void handleSignal('SIGINT'))
}
```

### Stack-Idiomatic Day-One Wiring Summary

| Stack | Startup Env Validator | Structured JSON Logger | Graceful Shutdown Signal |
| :--- | :--- | :--- | :--- |
| **Node.js / TS** | `zod` / strict `parseStartupConfig()` | `pino` + `AsyncLocalStorage` | `process.on('SIGTERM'/'SIGINT')` + `server.close()` |
| **Python (FastAPI)** | `pydantic-settings` (`BaseSettings`) | `structlog` (`JSONRenderer`) + `contextvars` | ASGI `lifespan` async context manager |
| **Go** | Explicit startup struct validator | `log/slog.NewJSONHandler` + `context.Context` | `signal.NotifyContext` + `srv.Shutdown(ctx)` |
| **PHP / Laravel** | Typed `config/*.php` + boot check | Monolog `JsonFormatter` + `Context::add` | Octane / PHP-FPM graceful reload |

## 5. Platform/Vendor Variations
- **Docker Container PID 1 Trap:** Running `node dist/server.js` directly as PID 1 inside Docker ignores default `SIGTERM` behavior unless your process registers an explicit `SIGTERM` handler AND/OR Compose sets `init: true` (`tini`) — otherwise `docker stop` stalls 10 seconds then sends brutal `SIGKILL` dropping active user requests!
- **Bind Address (`127.0.0.1` vs `0.0.0.0`):** Bind local CLI/dev preview servers to `127.0.0.1` by default; bind containerized services to `0.0.0.0` ONLY inside container networks while keeping host exposure behind reverse proxy (`/shadow-ops`).

## 6. Decision Matrix & Trade-Offs

| Day-One Foundation | Implementation Time | Prevents Which Production Failure? |
| :--- | :--- | :--- |
| **Fail-Fast Startup Env Validation** | `5 min` | Silent mid-request `undefined` crashes hours after deploy |
| **Redacted JSON Wide-Event Logger** | `10 min` | PII/token leaks in Loki & uncorrelatable `console.log` spam |
| **Liveness vs Readiness Probes** | `5 min` | Kubernetes kill-loops during transient DB/cache blips |
| **Bounded `SIGTERM` Shutdown** | `5 min` | Dropped in-flight payments & corrupted DB connections during rolling deploys |

## 7. Real Production Scenario
A greenfield Fastify service launched using `console.log` and lazy `process.env.WEBHOOK_SECRET!` inside the webhook route. During its first rolling deploy, Kubernetes killed pods mid-request (dropping 12 checkout confirmations because no `SIGTERM` handler drained active connections), and 3 days later the webhook route crashed with `500` because `WEBHOOK_SECRET` had been misspelled in staging secrets! Wiring `parseStartupConfig`, `pino` with redaction, `/readyz`, and `registerGracefulShutdown` on day one of every greenfield bootstrap prevents all three failures before the first feature ships.

## 8. Failure Modes & Edge Cases
- **WRONG:** Leaving `process.env.DB_PASSWORD!` lazily read inside a helper function and logging `console.log("Boot config:", config)` at startup (leaks every secret into container logs immediately!).
  **RIGHT:** Validate all env vars at boot with zero `!` assertions and log ONLY non-secret metadata (`port`, `nodeEnv`, `releaseSha`).
- **WRONG:** Calling an external third-party payment gateway inside `/healthz` (when the third party slows down, Kubernetes restarts all your healthy pods in a crash loop!).
  **RIGHT:** Keep `/healthz` purely process-local; check only core DB readiness in `/readyz`.

## 9. Testing & Verification
- Unit-test `parseStartupConfig`: verify valid config passes, invalid `PORT="99999"` or bad `NODE_ENV` throws immediately, and verify `writeJsonLog` replaces `authorization`/`nik`/`token` with `"[REDACTED]"` and strips `\r\n`.
- Run a real clean-directory smoke test exercising the vertical slice endpoint + `/healthz` (`exit 0`) and cleanly stop the spawned test server in `finally`!

## 10. Operational Considerations
- Hand deeper SLO/OTel tracing setups to `/shadow-observe` and production container hardening to `/shadow-ops` once the first vertical slice is proven locally.

## 11. Authoritative References
- Twelve-Factor App — *III. Config, IX. Disposability, XI. Logs*.
- `shadow-monarch/reference/BACKEND.md` §12 (Production Backend Structured Logging & Audit Separation).
- `shadow-observe/references/03-structured-logging-and-pii-redaction.md`.

## 12. Limitations & When NOT to Use
- Do NOT wire HTTP `/healthz` servers or `SIGTERM` HTTP drainers into pure offline `cli` or `library` profiles — match wiring strictly to the selected vertical-slice profile (`01`).
