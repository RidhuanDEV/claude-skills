# DEVOPS — Build, Deploy, Operate, Observe

Software is not finished when it compiles: build → test → package → deploy → observe → roll back.

## 1. Principles

- Reproducible builds and deployments; infrastructure and config as code; no undocumented manual server changes.
- Same artifact promoted through environments; only configuration differs.
- Separate dev, staging and production (accounts, credentials, data).
- Distinguish dev shortcuts (localhost, verbose logs, self-signed certs, permissive CORS) from production
  (TLS, secret management, restricted CORS, security headers, monitoring, backups) and say which is which.

## 2. Docker

- Multi-stage builds; small runtime images (slim/distroless/alpine when compatible — watch musl vs glibc issues);
  pin base image versions (tag or digest); `.dockerignore` (exclude `.git`, `node_modules`, `.env`, build outputs).
- Order layers for cache: copy manifests/lockfiles → install deps → copy source → build.
- Run as non-root (`USER`), read-only filesystem where possible, drop capabilities, set memory/CPU limits.
- Never bake secrets into images or build args; inject at runtime. Build-time secrets via BuildKit secret mounts.
- Handle signals: PID 1 must forward SIGTERM (use `exec` form `CMD ["node","dist/main.js"]`, or `tini`/`--init`), and the app shuts down gracefully.
- `HEALTHCHECK` or orchestrator probes.
- `localhost` inside a container is the container itself, not the host. Container-to-container: use Compose service names;
  container-to-host: `host.docker.internal` (Docker Desktop; on Linux add `extra_hosts: host-gateway`).
- Compose: named volumes for data, `depends_on` with `condition: service_healthy`, env via `env_file` not committed secrets.

## 3. Reverse proxy (Nginx and similar)

Consider: TLS termination and redirects, `proxy_set_header Host / X-Real-IP / X-Forwarded-For / X-Forwarded-Proto`,
`client_max_body_size` for uploads, `proxy_read_timeout` for slow endpoints, gzip/brotli, static caching with hashed filenames,
security headers, WebSocket upgrade headers (`Upgrade`, `Connection`), SSE (`proxy_buffering off`, long read timeout),
trusted proxy configuration in the app so client IPs and HTTPS detection are correct.
Know exactly which layer owns redirects, caching and headers; avoid duplicates (e.g. both Nginx and app setting the same
header differently). Test with `nginx -t` before reload.

## 4. CI/CD

Pipeline: install (from lockfile) → lint → type check → unit tests → integration tests → security scans (SCA, SAST,
secrets, image) → build → deploy → smoke/health check → notify. Do not deploy known-broken builds.
Release strategies for risk: rolling, blue-green, canary; feature flags for gradual exposure (remove after rollout).
Every deploy has a rollback path; DB migrations are backward compatible so rollback of code is possible (see DATABASE).
Least-privilege CI credentials; no production secrets available to untrusted PR jobs.

## 5. Configuration

Environment-specific values from config, never code. Validate critical config at startup and fail fast when missing.
Document every variable (`.env.example` with no real values). Never commit `.env`.

## 6. Observability

Logs, metrics, traces, health checks, alerts.
- **Structured JSON logs** with timestamp, level, service, environment, requestId/traceId, userId where appropriate,
  operation, durationMs, error type/code. Example:
  `{"level":"error","requestId":"req_123","operation":"createOrder","error":"PAYMENT_TIMEOUT","durationMs":3120}`
- Levels: DEBUG diagnostics (off in prod by default), INFO significant normal events, WARN unusual but recovered,
  ERROR failed operation needing attention. Do not log everything as ERROR; do not flood prod with DEBUG.
- Never log secrets, tokens, passwords or unnecessary PII.
- **Correlation IDs** propagate browser → gateway → backend → worker → external calls (OpenTelemetry / W3C trace context).
- Metrics: RED (rate, errors, duration) for services, USE (utilization, saturation, errors) for resources, queue depth, business KPIs.
- Alerts on symptoms users feel (error rate, latency SLO burn), with runbooks; avoid noisy alerts.
- Health: **liveness** (process alive — do not check dependencies) vs **readiness** (can serve traffic — check critical dependencies).

## 7. Deployment debugging (layer by layer)

DNS → TLS/certificates → load balancer/reverse proxy → application process (running? crashed? port?) → environment
variables → database/cache connectivity → storage/permissions → application logic.
Change one thing at a time. Inspect before mutating: logs (`docker logs`, `journalctl`, `kubectl logs`), status, config, then act.

## 8. Cache debugging

When behavior differs after deploy, identify which layer serves stale data before purging everything:
browser, service worker, CDN, reverse proxy, framework cache (Next.js data/route cache), application cache, Redis,
DB query cache. Check response headers (`Cache-Control`, `Age`, `ETag`, `X-Cache`).

## 9. Platform awareness

Windows vs Linux vs macOS, Docker, VPS, shared hosting, serverless, Kubernetes differ in paths, line endings (CRLF vs LF —
use `.gitattributes`), case sensitivity, permissions, shell syntax and process management. When the user is on Windows,
give PowerShell commands (or both), e.g. `Get-Content -Tail 50 -Wait app.log` vs `tail -f app.log`,
`$env:NODE_ENV="production"` vs `export NODE_ENV=production`.

## 10. Git & Collaborative Multi-Branch Workflow (Safe Sync & Conflict Resolution)

- **Default publishing/destructive guardrail**: do NOT execute unrequested `git commit`, `git push`, `git reset --hard`,
  `git clean -fd`, or `git push --force` unless the Monarch explicitly instructs you to run that action.
- **Proactive collaborative branch inspection (Allowed Anytime)**: because the Monarch collaborates across team branches,
  freely run safe diagnostic and remote-tracking commands:
  - `git status -sb` & `git branch -vv` (check active branch, ahead/behind counts, and uncommitted local work).
  - `git fetch --all --prune` (safely update remote-tracking refs `origin/*` without modifying the working tree).
  - `git log HEAD..origin/<branch> --oneline --stat` (see what teammates pushed before pulling).
  - `git diff --name-status HEAD...origin/<branch>` (list files modified on remote vs local).
  - `git merge-tree --write-tree HEAD origin/<branch>` (Git 2.38+ zero-touch dry-run merge in memory to detect exact conflicting files BEFORE running `git pull` or `git merge`!).
- **Safe Pull Protocol (When the Monarch asks to pull / sync from `origin/<branch>` or `main`/`develop`)**:
  1. **Check local working tree**: run `git status --porcelain`. If local modified files overlap with incoming changes from `origin/<branch>`, warn the Monarch or create a named stash backup (`git stash push -u -m "shadow-backup-before-pull"`).
  2. **Dry-run conflict check**: run `git fetch origin` and `git merge-tree --write-tree HEAD origin/<branch>`.
  3. **Execute safe pull**:
     - If no local divergence (`ahead 0`), run `git pull --ff-only origin <branch>`.
     - If diverged and dry-run is clean, run `git pull --no-rebase origin <branch>` (or `--rebase` if the repo enforces linear history) and re-apply stashed changes (`git stash pop`).
- **Collaborative Conflict Resolution Rules (`<<<<<<<`, `=======`, `>>>>>>>`)**:
  - **Inspect both intents first**: run `git log -p -n 3 HEAD -- <file>` (Monarch's changes) and `git log -p -n 3 origin/<branch> -- <file>` (teammate's changes).
  - **Never blindly pick `--ours` or `--theirs`** on shared code — integrate both the Monarch's and teammate's routes, DTOs, imports, and business rules cleanly.
  - **Verify after resolving**: ensure zero conflict markers (`git diff --check`), strict typing (`0 any`, `0 as Type`), and passing typecheck/tests before reporting completion.
- **If the Monarch explicitly requests Git commits/pushes**: distinguish working tree, staging area, local commits, and remote commits first; use focused Conventional Commits (`feat(scope): ...`, `fix(scope): ...`).

## 11. Incidents

Stabilize → reduce user impact (rollback, feature flag off, scale) → gather evidence → root cause → safest fix → verify recovery →
document → prevent recurrence. No broad speculative refactors during an active incident.
Blameless postmortems: what happened, why it was possible, why it wasn't detected earlier, how it was resolved, what prevents
recurrence. "Engineer made a mistake" is never the root cause; systems should absorb human error.

## 12. Production readiness

Requirements complete · tests passing · security reviewed · migration safe · observability added · error handling verified ·
config documented · deployment path tested · rollback considered · backups and restore tested · runbook exists.
