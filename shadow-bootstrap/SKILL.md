---
name: shadow-bootstrap
description: "Use when scaffolding a new app, worker, CLI, or service with a verified official generator. Not for incremental features (/shadow-plan)."
---

# Shadow Bootstrap (`/shadow-bootstrap`) — First Runnable Vertical Product Slice

Initialize a clean, reproducible greenfield target (`cli`, `static`, `worker`, `http`, or `library`) using verified **official CLI generators**, zero unrequested infrastructure bloat, and day-one production operability.

- **Owner:** Target safety preview (`preview_scaffold.py` / `REVIEW_EXISTING`), official CLI generator execution & sibling-staging adoption, single runnable vertical slices, fail-fast startup env validation, redacted JSON structured logging (`X-Request-Id`), `/healthz` vs `/readyz` separation, and graceful `SIGTERM` shutdown.
- **Boundaries:** Brownfield system architecture & convention extension (`shadow-architect`), production Docker/K8s/Nginx hardening (`shadow-ops`), OpenAPI spec governance (`shadow-api`), and full CI/CD release pipelines (`shadow-release`).

## Reference Guide

Load ONLY the 1–2 modular playbooks needed for the active bootstrapping subtask:

| Module | Topic | Load When |
| :--- | :--- | :--- |
| [01-vertical-slice-profiles-and-preview-gate.md](references/01-vertical-slice-profiles-and-preview-gate.md) | `cli`/`static`/`worker`/`http`/`library` profiles, `preview_scaffold.py` (`REVIEW_EXISTING`), conditional infra discipline | Choosing a project profile, previewing target safety, or scoping day-1 deliverables |
| [02-official-cli-generators-and-staging-adoption.md](references/02-official-cli-generators-and-staging-adoption.md) | Verified official CLI generators (`vite`, `create-next-app`, `uv`, `go mod`, `cargo`, `composer`), sibling staging isolation, 8-field Decision Record | Running official generators safely inside empty folders or monorepos |
| [03-startup-config-logging-health-and-shutdown.md](references/03-startup-config-logging-health-and-shutdown.md) | Fail-fast `parseStartupConfig()`, `pino`/`structlog`/`slog`/Monolog JSON logger + redaction, `/healthz` vs `/readyz`, `SIGTERM` shutdown | Wiring day-one production operability into new `http` services or `worker`s |
| [evaluations.md](evaluations.md) | Graded specialist evaluation scenarios (`BOOT-EVAL-01..06`) | Auditing `REVIEW_EXISTING` safety, official-first generators, zero bloat, and startup hygiene |

---

## 1. 5-Step Greenfield Bootstrap Workflow

Read the requested deliverable, runtime, platform, and team constraints. In a monorepo inspect workspace manifests, sibling projects, package manager, local SDKs, generator presets, and CI at the parent before deciding whether the target is new. If the product type or a material architectural/stack choice is still unresolved, ask the Monarch via the host interactive question tool BEFORE generating files.

1. **Preview (`L0` Safety Gate):** Run `python shadow-bootstrap/scripts/preview_scaffold.py TARGET --profile <cli|static|worker|http|library> [--capability ...]`. A non-empty destination returns **`REVIEW_EXISTING`** — inspect provenance and handle additions through the owning project's brownfield conventions rather than overwriting. On retry after a partial run, preserve existing work and resume only missing steps.
2. **Select & Stage the Official Generator:** Verify official version-specific docs (`/context7`), package identity, and local trusted alternatives ([official-first policy](../shadow-monarch/reference/OFFICIAL-FIRST-DEPENDENCY-POLICY.md) & [decision verifier](../shadow-monarch/scripts/official_first_verifier.py)). Record exact generator version, arguments, package manager, and side effects before running; isolate into a sibling staging directory whenever a generator might overwrite or drop a nested `.git`, and adopt only after inspecting the diff.
3. **Build One Vertical Slice:**
   - **`cli`:** 1 command, strict arg parsing, `0`/`1` exit status, executable example + unit test.
   - **`static`:** 1 semantic responsive accessible page (`antislop`), reproducible build.
   - **`worker`:** 1 idempotent job handler, retry/DLQ semantics, structured logger, duplicate-delivery test.
   - **`http`:** 1 validated endpoint + smoke test, fail-fast startup env parsing, stack-idiomatic non-blocking JSON structured logger (`pino`/`structlog`/`log/slog`/Monolog) with `X-Request-Id` context propagation + centralized secret/PII redaction + zero raw `console.log`, and bounded `SIGTERM` graceful shutdown.
   - **`library`:** 1 typed public export exercised by a consumer smoke test.
4. **Add Conditional Infrastructure Strictly On Need:** Persistence -> migration path + isolated test DB; queue -> ack/retry ownership; cache -> tenant isolation & invalidation; `/healthz` vs `/readyz` -> only for HTTP runtimes where needed (optional cache outage must not falsely kill healthy replicas). Route unsettled API docs choices to `/shadow-api`.
5. **Verify & Hand Off:** Run build, lint, test, and smoke commands from a clean working directory; compare created paths against the preview; stop any smoke-test server before returning; require separate authority for remote publication, shared infra, or deleting user files.

```powershell
python shadow-bootstrap/scripts/preview_scaffold.py ./target-app --profile http
python -m unittest discover -s shadow-bootstrap/tests -v
```
