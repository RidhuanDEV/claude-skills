# TypeScript / JavaScript / Node.js / NestJS / Express / React / Next.js

Prefer TypeScript for anything non-trivial. Match the project's module system (ESM vs CommonJS), package manager
(npm/pnpm/yarn — use the one whose lockfile exists) and Node version (`.nvmrc`/`engines`).

## 1. TypeScript rules

- `strict: true` (plus `noUncheckedIndexedAccess` for new projects). No `any`; use `unknown` and narrow.
- Types are design: domain types, discriminated unions (`{ status: 'success'; data } | { status: 'error'; error }`),
  type guards, `satisfies` for config objects, branded types for IDs/money when mix-ups are costly.
- **Validate at runtime at boundaries** — TypeScript types vanish at runtime. Parse request bodies, env vars, API responses
  and messages with Zod/Valibot/class-validator. Never `as User` on external data.
- Avoid non-null `!` as a habit, enums with surprising runtime behavior (prefer `as const` objects or string unions unless
  the codebase uses enums), and unreadable type gymnastics.

## 2. Async and error handling

- `async/await`; never mix with unhandled `.then` chains. Every promise is awaited, returned, or explicitly handled —
  no floating promises (lint `@typescript-eslint/no-floating-promises`).
- Parallel independent work: `Promise.all` (fail-fast) or `Promise.allSettled`; bound concurrency for large lists (`p-limit`).
- Timeouts and cancellation: `AbortController` / `AbortSignal.timeout(ms)` for `fetch` and cancellable APIs.
- Never `catch (e) {}`. `catch (e: unknown)` and narrow. Throw `Error` subclasses with `cause` (`new AppError('…', { cause: err })`).
- Process-level: handle `unhandledRejection`/`uncaughtException` by logging and exiting (let the supervisor restart) — do not continue in an unknown state.
- Never block the event loop: no sync FS/crypto (`readFileSync`, `pbkdf2Sync`) on request paths; offload CPU-heavy work to worker threads or a queue.
- Streams for large data (`pipeline` from `node:stream/promises`) — handles backpressure and errors.

## 3. NestJS

- Module per feature; controllers thin; providers (services) hold use cases; repositories/data layer separate.
- Global `ValidationPipe({ whitelist: true, forbidNonWhitelisted: true, transform: true })` with class-validator DTOs
  (or a Zod pipe) — prevents mass assignment.
- **Guards** for authN/authZ (`@UseGuards(JwtAuthGuard, RolesGuard)`), object-level checks in services.
  **Pipes** for validation/transformation, **Interceptors** for logging/mapping/timeouts, **Exception filters** to map domain errors to the
  error contract. Use built-in `HttpException` subclasses (`NotFoundException`, `ConflictException`…).
- Config via `@nestjs/config` with schema validation at startup. Avoid circular dependencies instead of papering over them with `forwardRef`.
- Provider scope defaults to singleton — do not store request state in providers; request-scoped providers have a performance cost.
- `app.enableShutdownHooks()` for graceful shutdown; `@nestjs/terminus` for health checks; `@nestjs/throttler` for rate limiting;
  `helmet` for headers; queues via BullMQ (`@nestjs/bullmq`).
- Testing: `Test.createTestingModule` with overridden providers; Supertest e2e against `app.getHttpServer()`.

## 4. Express (and similar)

- Express 4 does not catch rejected promises in handlers — wrap async handlers or use Express 5 (async errors forwarded).
- Central error-handling middleware `(err, req, res, next)` last. `helmet`, body size limits (`express.json({ limit: '1mb' })`),
  CORS allowlist, rate limiting, `app.set('trust proxy', …)` correctly behind proxies.
- Validate with Zod/Joi middleware; never pass `req.body` straight into ORM create/update.

## 5. Data access

- Prisma: use `select`/`include` deliberately (N+1 via loops of `findUnique`), `$transaction` for atomic multi-step writes,
  `$queryRaw` tagged templates are parameterized — **never `$queryRawUnsafe` with user input**. One `PrismaClient` instance per process.
  Migrations via `prisma migrate deploy` in the pipeline; review generated SQL.
- TypeORM/Drizzle/Knex/Mongoose: parameterized queries only; Mongoose — sanitize query objects (reject `$` operators from input), set `strictQuery`.
- Pool sizes respect DB limits × instance count. Money as integer minor units or decimal library (`decimal.js`), never `number` math on floats.

## 6. React

- Function components and hooks; follow Rules of Hooks. Effects only for external synchronization, always with cleanup and abort of stale fetches.
- Server state with TanStack Query/SWR; forms with React Hook Form + Zod; derive state instead of syncing copies.
- Stable keys from IDs; memoize only when profiling shows need (React Compiler may make manual memo unnecessary — follow the project).
- Accessibility via semantic elements; Testing Library queries by role/label.

## 7. Next.js (App Router)

- Server Components by default; `"use client"` only where interactivity is needed; keep server-only code/secrets out of client
  components (`import 'server-only'`). Only `NEXT_PUBLIC_*` vars reach the browser — never secrets there.
- Server Actions and Route Handlers are public endpoints: validate input and authorize every call.
- Know the caching model of the version in use (fetch cache, `revalidate`, `revalidatePath/Tag`, dynamic rendering) — it changed
  between Next 14 and 15; check the project's version before advising.
- Middleware runs on every matched request — keep it light; do not rely on it as the only authorization layer.
- Auth libraries (Auth.js/NextAuth): set `AUTH_SECRET`/`NEXTAUTH_SECRET`, correct `AUTH_URL`/`NEXTAUTH_URL` and `trustHost` behind proxies,
  and forward `X-Forwarded-Proto` — common source of 500s and redirect loops in Docker.
- `output: 'standalone'` for Docker images.

## 8. Logging, config, security

- Structured logger (pino) with request IDs; no `console.log` in production paths; redact auth headers/cookies.
- Validate `process.env` at startup with a schema; fail fast.
- `npm ci`/`pnpm install --frozen-lockfile` in CI; `npm audit`/Dependabot/Snyk; beware typosquatting and install scripts.
- XSS: avoid `dangerouslySetInnerHTML`/`innerHTML`; sanitize with DOMPurify when unavoidable. Prototype pollution: never deep-merge untrusted objects.
- Passwords: `argon2` or `bcrypt` packages; tokens: `crypto.randomBytes`/`randomUUID`, compare with `crypto.timingSafeEqual`.
- JWT (`jose`/`jsonwebtoken`): pin `algorithms`, verify `iss`/`aud`/`exp`.

## 9. Testing

Vitest (or Jest) for unit; Supertest for HTTP; Testcontainers for DB; MSW to mock HTTP at the network level;
Playwright for E2E. Fake timers for time-dependent logic.

## 10. Tooling

ESLint (typescript-eslint, `no-floating-promises`, `no-misused-promises`) · Prettier · `tsc --noEmit` in CI ·
lockfile committed · Node LTS · multi-stage Docker with `npm ci --omit=dev` and non-root `node` user.

## 11. Common mistakes to catch

Floating promises · `await` in loops where parallel is intended (or unbounded `Promise.all` over thousands) · unhandled async errors in Express 4 ·
sync I/O on hot paths · `any` and `as` casts on API data · unvalidated env vars · `==` comparisons · mutating shared module state across requests ·
`$queryRawUnsafe` / string-built SQL · secrets in `NEXT_PUBLIC_*` · missing effect cleanup · index as React key ·
float money · `JSON.parse` without try/validation · large dependencies for trivial helpers.
