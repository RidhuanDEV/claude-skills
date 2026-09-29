# DEBUGGING — Evidence-Based Root-Cause Analysis

Do not change code randomly. Follow evidence.

```text
Symptom → observed behavior → possible causes → evidence → root cause → fix → regression verification
```

## 1. Separate what the user sees from why

- **Symptom**: what the user observes ("image is broken").
- **Root cause**: why the system behaves that way.
- **Contributing factors**: conditions that made it possible or worse.

Bad: "The image is broken, so change the frontend component."
Senior: "First determine whether the URL is wrong, the file is missing in storage, access is blocked (CSP, CORS, auth, ACL),
the proxy rewrites the path, a cache serves a stale version, or the component renders it incorrectly."

## 2. Workflow

1. **Reproduce** reliably; note environment (local/staging/prod, OS, browser, version, data).
2. **Define** expected vs actual behavior precisely. When did it start? What changed (deploy, config, dependency, data, traffic)?
3. **Locate the layer**: UI → client state → API client → network/proxy → controller → service → domain → DB/cache/queue →
   infrastructure/config. Bisect the path: check the request in DevTools, then the server log for the same request ID,
   then the query.
4. **Hypothesize** several causes and rank by likelihood and cost to check. Don't lock onto the first theory.
5. **Gather evidence**: logs, stack traces, network requests, DB queries and plans, configs, env vars, metrics, traces,
   `git log`/`git bisect` for regressions. Prefer instrumentation (targeted logging, breakpoints) over guessing.
6. **Confirm root cause** — the explanation must account for all observations.
7. **Smallest correct fix**, plus regression test.
8. **Verify** the fix and check nearby behavior for regressions; explain why it happened and how to prevent recurrence.

Give **diagnostic commands before destructive ones**. Change one thing at a time.

## 3. Reading error output

Read the whole thing, not just the last line. Identify the primary error (often the first or the deepest "caused by"),
secondary errors, warnings that give context, the likely layer, and probable causes. For stack traces find the first
frame in our code. For build errors, the first error usually causes the rest.

## 4. Classic cause catalog

- **Works locally, fails in prod/Docker**: missing/different env vars, `localhost` inside containers, file paths and case
  sensitivity (Windows vs Linux), missing build step or asset, different Node/runtime version, proxy headers
  (`X-Forwarded-Proto` → wrong redirects, insecure cookies), CORS/CSP differences, timeouts at the proxy, permissions,
  DNS, time zone, memory limits (OOM kill: exit code 137).
- **Intermittent**: race conditions, connection pool exhaustion, timeouts, retries causing duplicates, caching layers,
  load-balancer stickiness, clock skew, resource leaks growing over time.
- **Auth issues**: cookie `Secure`/`SameSite`/domain mismatch, missing `credentials: 'include'`, CORS with credentials,
  wrong callback URL, secret/key mismatch between instances, expired tokens, clock skew on JWT validation.
- **Slow**: N+1 queries, missing index, unbounded queries, synchronous work that should be async, chatty APIs,
  large payloads, blocking event loop / thread pool starvation, lock contention, GC pressure.
- **Stale after deploy**: browser/service worker/CDN/proxy/framework/Redis cache (see DEVOPS cache debugging).
- **Memory growth**: listeners never removed, timers not cleared, unbounded caches/maps/queues, retained large objects,
  unclosed connections/streams, unresolved subscriptions, goroutine/task leaks.
- **500 with no log**: error swallowed, logged at wrong level, crash before logger init, proxy returning the 500 (check
  proxy logs), health check killing the container.

## 5. Deployment debugging order

DNS → TLS → reverse proxy → app process → environment variables → database → storage → application logic.
One controlled change at a time.

## 6. Production incidents

Stabilize first (rollback, disable flag, scale, failover), reduce user impact, then investigate with evidence.
No broad speculative refactors mid-incident. Write a blameless postmortem afterwards (see DEVOPS §11).

## 7. Answer format for bugs

```md
## Symptom
## Most likely layer & hypotheses (ranked, with why)
## Evidence to collect (exact commands, log queries, DevTools checks)
## Root cause (once confirmed, or the most likely with confidence level)
## Fix (minimal diff)
## Regression check & test
## Prevention (optional)
```
When evidence is incomplete, say so: "The most likely cause is X because Y; confirm by running Z."
Never invent log lines, stack traces or system state.
