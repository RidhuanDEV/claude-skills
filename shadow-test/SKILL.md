---
name: shadow-test
description: "Polyglot Automated Unit, Integration & Contract Testing. Use when writing or fixing Vitest/Jest, Pytest, Go test, Pest/PHPUnit, JUnit 5, xUnit, Rust, or Flutter tests, property/mutation tests, contract tests, flaky test fixes, or leak-free Docker test harnesses. Do NOT use for RAG/LLM evals (/shadow-eval) or Pre-UAT k6 load tests (/shadow-perf)."
---

# Shadow Test (`/shadow-test`) — Polyglot Automated Testing, Risk-Based Pyramid & Contract Compatibility

Use this skill whenever the **Monarch** asks to write, expand, fix, or audit unit tests, integration tests, property/state-machine tests, API contract tests, flaky test triage, or Docker-backed test harnesses across any stack.

- **Owner:** Risk-based test pyramid & 8-point HTTP failure surface, polyglot unit/integration idioms (TS/Node/React, Python, Go, PHP/Laravel, Java/Kotlin, C#/.NET, Rust, Dart/Flutter), property/state-machine/mutation testing, consumer-provider contract tests, flaky test elimination, and leak-free ephemeral test container teardown.
- **Boundaries:** RAG/LLM evaluation & red-teaming (`shadow-eval`), Pre-UAT `k6` load testing (`shadow-perf`), live Playwright browser viewport QA (`shadow-browser`), and staging client UAT sign-off (`shadow-uat`).

## Reference Guide

Load ONLY the 1–2 modular playbooks needed for the active testing subtask:

| Module | Topic | Load When |
| :--- | :--- | :--- |
| [01-risk-based-test-pyramid-and-8-point-matrix.md](references/01-risk-based-test-pyramid-and-8-point-matrix.md) | Testing trophy, real-DB route integration priority, 8-point HTTP failure surface, red-before/green-after | Planning test coverage for a new feature, endpoint, or bug-fix regression |
| [02-polyglot-unit-and-integration-idioms.md](references/02-polyglot-unit-and-integration-idioms.md) | Idiomatic patterns across TS/Vitest, Python/Pytest, Go `-race`, PHP/Pest, Java/JUnit5, C#/xUnit, Rust/`sqlx`, Flutter | Writing or fixing framework-native unit & integration tests in a specific stack |
| [03-property-based-state-machine-and-mutation-testing.md](references/03-property-based-state-machine-and-mutation-testing.md) | `fast-check`, `Hypothesis`, `proptest`, Go fuzzing, state-machine invariants, scoped Stryker/mutmut mutation testing | Testing money/tax rounding, parsers, order/approval state machines, or assertion strength |
| [04-contract-and-boundary-compatibility-testing.md](references/04-contract-and-boundary-compatibility-testing.md) | OpenAPI runtime validation, Pact consumer-provider contracts, N-1 event/webhook golden fixtures | Guarding API/event schema evolution alongside `/shadow-api` & `/shadow-compat` |
| [05-flaky-test-triage-and-deterministic-fixtures.md](references/05-flaky-test-triage-and-deterministic-fixtures.md) | Fake UTC clocks, bounded condition polling (zero `sleep()`), socket blocking, port `0`, order-shuffle stress | Eliminating flaky CI failures instead of masking them with retries |
| [06-ephemeral-test-containers-and-leak-free-teardown.md](references/06-ephemeral-test-containers-and-leak-free-teardown.md) | Singleton ephemeral DB container, `--rm --label shadow.ephemeral=true`, `try/finally` + `trap EXIT`, `L1` vs `L2`/`L3` | Configuring Docker/Testcontainers test harnesses with zero orphan containers/volumes |
| [GoldbergYoni_JS_Testing_Best_Practices.md](references/vendor/GoldbergYoni_JS_Testing_Best_Practices.md) | Curated JavaScript/TypeScript/Node.js testing best practices (AAA, black-box assertions, clean fixtures) | Writing or reviewing Node.js/TypeScript backend & frontend test suites |
| [evaluations.md](evaluations.md) | Graded specialist evaluation scenarios (`TEST-EVAL-01..08`) | Auditing test pyramid ROI, flake triage, Docker teardown, strict TS tests, and `L1` scope |

---

## 1. Enhanced Testing Doctrine

1. **Risk-Based Integration & Domain Priority:** Prioritize real route -> validation -> auth -> service -> real test DB integration tests over mock-heavy repository tests, paired with fast pure domain unit + property tests (`fast-check`/`Hypothesis`/`proptest`) for money math, parsers, and state machines.
2. **Red-Before (`FAIL`) -> Green-After (`PASS`) Bug Discipline:** Reproduce every bug with a targeted failing regression test FIRST, apply the minimal fix, and verify green; run impacted module tests (`vitest related`, `pytest --lf`, `go test -race ./pkg/...`) before full suites.
3. **Zero Flakiness & Strict Typing:** Never use raw `sleep()`/`waitForTimeout()`, blind CI retries, or TypeScript `any`/`as Type` casts in tests. Inject frozen UTC clocks, isolate DB state via `SAVEPOINT` rollback/schemas, bind ephemeral port `0`, and block stray external network calls.
4. **Universal 8-Point HTTP Failure Surface:** Cover applicable surfaces per endpoint: (1) Happy Path (`200`/`201`) + persisted state, (2) Validation (`400`/`422`), (3) Unauthenticated (`401`), (4) Cross-Tenant IDOR (`403`/`404`), (5) Not Found (`404`), (6) Conflict / `Idempotency-Key` (`409`), (7) Boundary/currency/UTC edge values, and (8) Clean state & container teardown.

---

## 2. Mandatory Docker, Process Teardown & `L1`–`L4` Boundaries

- **One Ephemeral Container Per Suite + Guaranteed Teardown:** Always launch test DBs with `--rm --label shadow.ephemeral=true` on `127.0.0.1:0`, isolate tests via `SAVEPOINT`/schemas, tear down inside `try/finally` (`docker rm -f -v` / `docker compose -p <p>-test down -v --rmi local --remove-orphans` / `docker image rm -f`), and verify with `python shadow-quality/scripts/shadow_gate.py --repo . --check-docker-leaks`.
- **Ownership-Safe Process Cleanup:** Close only test-spawned servers/workers (`afterAll`/`finally` or `resource_cleanup.py --cleanup-owned`); NEVER blanket-kill `node.exe`/`python.exe`.
- **Execution Approval (`L1` vs `L2`/`L3`):** Bounded local unit/integration tests are `L1_SAFE_VERIFICATION`. A unit-test request NEVER authorizes unrequested broad Playwright E2E (`/shadow-browser` `L2`) or `k6` stress testing (`/shadow-perf` `L3`).

---

## 3. Deterministic Test Hygiene Verification

```powershell
python shadow-test/scripts/suite_hygiene_verifier.py --self-test
python shadow-test/scripts/suite_hygiene_verifier.py --check-test-suite path/to/test_hygiene_manifest.json
python -m unittest discover -s shadow-test/tests -v
```
