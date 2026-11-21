---
name: shadow-bootstrap
description: "Greenfield Project Scaffolder. Use when initializing a CLI, static site, worker, service or library in a new target using the chosen stack and verified generator."
---

# Shadow Bootstrap — first runnable product slice

Read the requested deliverable, runtime, platform and team constraints. In a monorepo inspect workspace manifests, sibling projects, package manager, SDKs, generator presets and CI at the parent before deciding whether the target is new. An explicit choice of stack or output settles that decision. If the product type or an architectural choice is still material and unresolved, use the host question tool before generating files.

1. **Preview.** From this skill directory run `python scripts/preview_scaffold.py TARGET --profile cli` (choices: cli, static, worker, http, library). Add one `--capability` for each requirement established by the brief or repository. The command reads target names and prints deliverables. A nonempty destination returns REVIEW_EXISTING. Inspect its contents and provenance; handle a requested addition through the owning project's conventions. On a retry after a partial generator run, preserve all existing work, compare against the preview and resume only attributable missing steps.
2. **Select the generator.** Inspect official version-specific documentation, package identity and compatibility, and local trusted alternatives. Use the existing [official-first policy](../shadow-monarch/reference/OFFICIAL-FIRST-DEPENDENCY-POLICY.md) and [decision verifier](../shadow-monarch/scripts/official_first_verifier.py). Preview records product capabilities. Also capture exact generator version, arguments, package manager, expected files and installation side effects before invoking it. Check target again immediately before execution; isolate into a new sibling staging directory when a generator can overwrite or install implicitly. Adopt the result only after inspecting its diff against the current destination.
3. **Build one vertical slice.** An offline CLI needs a command, documented input/exit status and one executable example. A static site needs a page and reproducible build. A worker needs one job, failure semantics and a duplicate-delivery test. An HTTP service needs one request/response contract, its matching smoke test, and a stack-idiomatic non-blocking JSON structured logger (`pino`, `structlog`/JSON `logging`, `log/slog`, Monolog) with `X-Request-Id` context propagation, centralized secret/PII redaction, and zero raw `console.log` in production routes (reuse existing logger if brownfield). A library needs one importable export exercised by a consumer. Use idiomatic compiler, lint and test settings available for the chosen language.
4. **Add conditional infrastructure.** Persistence calls for an established migration path, isolated test data and replay verification. A queue needs acknowledgment and retry ownership; a cache needs invalidation and isolation. Add a health endpoint only when the service/runtime can serve it and a consumer requires it. A DB dependency may affect readiness; an independent optional cache outage need not make a healthy service unavailable. Create Compose, client collections, OpenAPI, cloud CI or telemetry only when selected or established. Send an unsettled docs choice to shadow-api before writing a persistent spec.
5. **Verify and hand off.** Run the selected build, test and smoke commands from a clean working directory. Compare actual created and modified paths to the preview; document prerequisites and unresolved side effects. On a failure, record last successful action and proposed retry. Shared infrastructure, remote publication and cleanup of user files require separate authority.

## Reference Guide

| Task / Scenario | Load Reference |
| :--- | :--- |
| Choosing `cli`/`static`/`worker`/`http`/`library` Vertical Slice, Official CLI Generators, Startup Env Validation & Graceful Shutdown | [references/greenfield-profiles-and-wiring.md](references/greenfield-profiles-and-wiring.md) |

Do not load unrelated references unnecessarily.
