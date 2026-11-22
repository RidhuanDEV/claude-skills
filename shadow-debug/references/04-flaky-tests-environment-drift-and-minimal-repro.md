# 04 — Flaky Tests, Environment Drift & Minimal Isolated Reproductions

## 1. Purpose & Activation Conditions
Diagnose "works on my machine" staging/CI-only failures by systematically auditing **environment drift** across runtimes, lockfiles, timezones, OS path/case sensitivity, proxies, and configs BEFORE editing application code — and convert noisy multi-service bug reports into tiny, deterministic, self-contained local reproductions. Activate whenever a bug reproduces in CI/staging/Windows/Linux only, or when intermittent test failures resist casual inspection.

## 2. Prerequisites
- Redacted environment metadata from BOTH the failing environment (CI/staging) and the passing environment (local dev).
- Read-only (`L0`) access to Dockerfiles, lockfiles, reverse proxy configs, and CI workflow YAML.

## 3. Technical Principles & Constraints
- **Diff the Environment Before Guessing Code:** When code passes locally and fails in staging/CI, the root cause almost always lives in ONE of **8 Concrete Drift Axes**:
  1. **Exact Runtime / Native Lib Patch Version:** Node `20.11` vs `22.9`, Python `3.11` vs `3.13`, OpenSSL 3 legacy ciphers, glibc vs musl Alpine (`ICU` timezone/collation data missing on Alpine!).
  2. **Lockfile & Transitive Dependency Drift:** Local `npm install` vs CI `npm ci`, stale `node_modules`, missing `package-lock.json` pin.
  3. **OS Case Sensitivity & Line Endings:** Windows/macOS case-insensitive filesystems silently resolve `import './UserCard'` when file is `userCard.tsx` -> crashes on Linux Docker (`MODULE_NOT_FOUND`)! Also `CRLF` (`\r\n`) inside bash scripts (`^M: bad interpreter`) and `\` vs `/` path joins.
  4. **Timezone & Locale Drift:** Local `Asia/Jakarta` (`UTC+7`) vs CI/Docker `UTC` -> date truncation, midnight rollover, and `toLocaleDateString()` mismatches.
  5. **Reverse Proxy / Ingress Limits:** Staging Nginx default `client_max_body_size 1m` (`413`), `proxy_read_timeout 60s` (`504`), buffered SSE (`X-Accel-Buffering`), or missing `X-Forwarded-Proto` breaking `Secure` cookies (`shadow-auth`).
  6. **Database Engine / Schema / Data Distribution:** Local empty 10-row DB vs staging 2M-row skewed DB, missing migration, MySQL `ONLY_FULL_GROUP_BY` / Postgres `search_path` / RLS role differences (local superuser bypasses RLS while staging app role enforces RLS!).
  7. **Memory / CPU / Pool Caps:** Local laptop 32GB RAM vs staging container `512Mi` RAM / `0.5` CPU / `pool_max: 5`.
  8. **Env Var Type / Whitespace Coercion:** Trailing newline/space in secret value (`"secret\n"`), string `"false"` evaluated as truthy in JS (`Boolean("false") === true`!!), or missing optional env fallback.
- **Minimal Reproducible Example (MRE) Standard:** Strip away UI, unrelated routes, and external services until you have the **smallest runnable command** (`<= 30` lines or 1 focused test case) that fails deterministically (`exit_code != 0`) with zero external network calls.
- **Secret Hygiene When Diffing Envs:** Compare **presence, type, length, and SHA-256 prefix** of env vars — NEVER print or paste raw secret values into tickets or logs!

## 4. Architecture & Implementation

### 8-Axis Environment Drift Audit Checklist (Read-Only `L0` Diff)

| Drift Axis | Safe Local vs Staging Check Command | Classic Hidden Bug Caught |
| :--- | :--- | :--- |
| **1. Runtime & OS** | `node -v`, `python --version`, `uname -a`, check Alpine `tzdata`/`icu-full` | Missing `Asia/Jakarta` timezone or musl native addon crash |
| **2. Lockfile Parity** | Compare `sha256` of `package-lock.json`/`uv.lock`/`go.sum` | Transitive dependency bump breaking serializer in CI only |
| **3. Case & Path** | `git ls-files` casing vs import paths; check `.gitattributes` `eol=lf` | Passes on Windows/macOS, fails `ERR_MODULE_NOT_FOUND` on Linux CI |
| **4. Timezone/Locale** | Re-run test with `TZ=UTC` AND `TZ=Asia/Jakarta` | Off-by-one day bug in invoice due-date calculations |
| **5. Proxy & Headers** | Inspect Nginx/Caddy `client_max_body_size`, `X-Forwarded-Proto`, `proxy_buffering` | `413` upload reject, SSE buffering hang, or login cookie loop |
| **6. DB Role & RLS** | Check `current_user`, `rolbypassrls`, `sql_mode`, row counts | Local `postgres` superuser bypassed RLS; staging app user got 0 rows! |
| **7. Container Limits** | `docker inspect` memory/CPU quotas, `pool_max` | OOMKill or connection-pool self-deadlock only under small pool |
| **8. Env Var Parsing** | Inspect keys + value types/lengths (NEVER raw secrets!) | `ENABLE_CACHE="false"` parsed as truthy `Boolean("false") === true`! |

```ts
// Strict Env Boolean & Integer Parser (Eliminates Classic Boolean("false") === true Drift Bug — 0 any, 0 casts)
export function parseStrictEnvBoolean(raw: string | undefined, defaultValue: boolean, name: string): boolean {
  if (raw === undefined) return defaultValue
  const normalized = raw.trim().toLowerCase()
  if (normalized === 'true' || normalized === '1') return true
  if (normalized === 'false' || normalized === '0') return false
  throw new Error(`Invalid boolean env var ${name}: expected 'true'|'false'|'1'|'0'`)
}

export function buildRedactedEnvFingerprint(
  env: Readonly<Record<string, string | undefined>>,
  keysToInspect: readonly string[],
): ReadonlyArray<{ readonly key: string; readonly present: boolean; readonly length: number; readonly hasTrailingWhitespace: boolean }> {
  return keysToInspect.map((key) => {
    const val = env[key]
    return {
      key,
      present: val !== undefined && val.length > 0,
      length: val ? val.length : 0,
      hasTrailingWhitespace: val !== undefined && val !== val.trim(),
    }
  })
}
```

## 5. Platform/Vendor Variations
- **Windows Dev -> Linux Docker CI:** Always set `*.sh text eol=lf` in `.gitattributes` and run `tsc --noEmit` with `"forceConsistentCasingInFileNames": true` in `tsconfig.json` so casing bugs fail immediately on Windows before pushing!
- **PostgreSQL Superuser vs Non-Superuser RLS Testing:** Local Docker Postgres often connects as `postgres` (which has `BYPASSRLS`!). Always create a non-superuser `app_role` in local integration tests (`shadow-db`) so RLS policy bugs surface locally instead of staging!
- **Docker Build Cache Drift:** Stale Docker layers (`COPY . .` caching old build output or outdated `apt` indexes) can cause staging to run yesterday's bundle; check exact `git sha` stamped into `/health/ready` (`releaseSha`).

## 6. Decision Matrix & Trade-Offs

| Mystery Failure Mode | Fast Discriminating Test | Expected Proof |
| :--- | :--- | :--- |
| **Passes local, fails Linux CI** | Run inside exact CI Docker image locally (`docker run --rm ...`) | Reproduces exact OS/casing/tz/Alpine failure locally |
| **Passes as admin/local DB, returns `[]` in staging** | Query `SELECT current_user, rolbypassrls` + test as non-superuser role | Exposes missing RLS policy or `SET LOCAL app.tenant_id` |
| **Fails randomly 1 in 15 CI runs** | Run `20x` with shuffled order, `TZ=UTC`, and small DB pool | Exposes clock, shared state, or concurrency race (`shadow-test`) |
| **Fails only behind staging HTTPS** | Inspect `X-Forwarded-Proto`, `trust proxy`, `Secure`/`SameSite` cookie flags | Exposes Express/Fastify missing `trust proxy` setting |

## 7. Real Production Scenario
Login worked 100% locally (`http://localhost:3000`) and passed all 90 unit tests, yet looped endlessly back to `/login` on staging (`https://staging.example.com`). Instead of rewriting the JWT middleware, running the 8-axis drift check immediately caught two staging-only facts: (1) Nginx terminated TLS and forwarded HTTP to Express without `app.set('trust proxy', 1)`, so Express refused to issue `Secure` session cookies, and (2) `COOKIE_SECURE="false"` in `.env.staging` was evaluated via `Boolean(process.env.COOKIE_SECURE)` which returned `true`! Fixing `trust proxy` + `parseStrictEnvBoolean` with a local `X-Forwarded-Proto` integration test resolved the issue in 15 minutes.

## 8. Failure Modes & Edge Cases
- **WRONG:** Dumping `printenv` or `console.log(process.env)` into CI logs or Slack to compare local vs staging configs (immediately leaks every DB password, JWT secret, and API key!).
  **RIGHT:** Use `buildRedactedEnvFingerprint()` logging ONLY key presence, length, trailing-whitespace flag, and safe non-secret values (`NODE_ENV`, `TZ`, `POOL_MAX`).
- **WRONG:** Pushing 10 "try-fix-ci" commits blindly to staging to see what happens.
  **RIGHT:** Reproduce locally inside the exact target runtime/timezone/container environment (`L1`) with a minimal failing test first!

## 9. Testing & Verification
- Once drift is isolated, lock it down with a deterministic regression test (e.g., testing with `TZ=UTC`, non-superuser DB role, `X-Forwarded-Proto: https`, and `parseStrictEnvBoolean("false") === false`) and run `debug_hypothesis_gate.py --validate-report`.

## 10. Operational Considerations
- Pin exact runtime versions (`.nvmrc`/`.python-version`/`Dockerfile` digest) and enforce `forceConsistentCasingInFileNames: true` + `.gitattributes` `eol=lf` so environment drift stops at commit time.

## 11. Authoritative References
- Twelve-Factor App — *Dev/Prod Parity & Config*.
- TypeScript `tsconfig.json` — `forceConsistentCasingInFileNames` & Strict Compiler Flags.
- PostgreSQL Documentation — *Row Security Policies (`BYPASSRLS` vs Application Roles)*.

## 12. Limitations & When NOT to Use
- Once a flaky test or missing parity check is diagnosed and minimally patched, hand broader test-suite hardening to `/shadow-test` and CI/Dockerfile hardening to `/shadow-ops`.
