---
name: shadow-test
description: "Polyglot Automated Unit, Integration & Contract Testing. Use when writing or fixing Vitest/Jest, Pytest, Go test, Pest/PHPUnit, JUnit 5, xUnit, Rust, or Flutter tests. Do NOT use for RAG/LLM evals (/shadow-eval) or Pre-UAT k6 load tests (/shadow-perf)."
---

# Shadow Test (`/shadow-test`) — Polyglot Automated Testing, Risk-Based Pyramid & Contract Compatibility

Use this skill whenever the **Monarch** asks to write, expand, fix, or audit unit tests, integration tests, or API contract tests in any programming language or framework.

---

## 1. Local Knowledge Base Routing

1. Read [`references/POLYGLOT-TESTING-MATRIX.md`](references/POLYGLOT-TESTING-MATRIX.md) for idiomatic test structures across TypeScript/Node/React, Python, Go, PHP/Laravel, Java/Kotlin, C#/.NET, Rust, and Dart/Flutter.
2. For JavaScript/TypeScript/Node.js backend & frontend testing, consult [`references/vendor/GoldbergYoni_JS_Testing_Best_Practices.md`](references/vendor/GoldbergYoni_JS_Testing_Best_Practices.md).

---

## 2. Enhanced Testing Doctrine

### A. Risk-Based Test Pyramid
Prioritize testing effort where business and financial risk is highest:
1. **Integration / Component Tests (Highest ROI for Backend APIs)**: Test the full route -> validation -> service -> database/transaction boundary using real test DB transactions or Testcontainers rather than brittle mocks of internal repositories.
2. **Pure Domain Unit Tests**: Fast, exhaustive table-driven/parameterized tests for pricing formulas, tax/discount calculations, state machine transitions, and permission evaluators.
3. **Consumer/Provider Contract Tests (Paired with `/shadow-api` & `/shadow-compat`)**: Verify HTTP status codes, response envelopes, required fields, and nullability match the verified contract in its owning service so frontend/mobile consumers never break.

### B. Regression Selection for Bug Fixes
- Whenever fixing a bug or production incident (`/shadow-maintain`), write a targeted regression test that reproduces the exact failure first, then verify the fix turns it green.
- Run affected module tests first (`vitest related`, `pytest --lf`, `go test ./pkg/...`) for fast feedback before running the full test suite.

### C. Deterministic Fixtures, Advanced Techniques & Zero Flakiness
- **Property-Based & State-Machine Testing**: For monetary math, parsers, serializers, and order/approval workflows, pair example tests with property-based checks (`fast-check`, `Hypothesis`, `proptest`) and randomized state-transition sequences verifying core invariants hold across arbitrary inputs.
- **Mutation & Fault/Race Injection**: Verify critical business tests catch seeded bugs (mutation mindset); inject concurrent duplicate requests, DB deadlocks, or simulated ack timeouts when testing async/transactional code (`/shadow-concurrency`).
- **Flaky-Test Triage**: Never ignore intermittent CI failures or blindly wrap with retries; isolate shared mutable globals, wall-clock timers (`vi.useFakeTimers()`, `freezegun`), seeded RNGs, and per-test DB transaction rollback (`BEGIN ... ROLLBACK`) before reporting `PASS`.

### D. Mandatory Docker & Test Database Teardown (Zero Orphan Containers/Volumes/Images)
Never leave exited test or migration-verification containers (`*-test-<timestamp>`, `*-migration-verification*`), anonymous volumes, or temporary test-built images behind in Docker:
1. **Reuse One Container Per Suite (Never One Container Per Test)**:
   - Start at most **one** ephemeral DB container per test suite run and isolate individual tests via transactions (`BEGIN ... ROLLBACK` / `SAVEPOINT`) or disposable schemas (`CREATE DATABASE test_<id>; ... DROP DATABASE test_<id>;`). Never spawn a new `postgres`/`mariadb`/`mysql` container per test file.
2. **Always Pass `--rm` & `--label shadow.ephemeral=true` + Guaranteed `try / finally` Teardown**:
   - **Single Container (`docker run`)**:
     - PowerShell:
       ```powershell
       $ContainerName = "app-test-db-$PID"
       try {
           docker run -d --rm --label shadow.ephemeral=true --name $ContainerName -e MYSQL_ROOT_PASSWORD=test mariadb:10
           # run migrations & tests...
       } finally {
           docker rm -f -v $ContainerName 2>$null | Out-Null
       }
       ```
     - Bash / POSIX:
       ```bash
       CONTAINER_NAME="app-test-db-$$"
       trap 'docker rm -f -v "$CONTAINER_NAME" >/dev/null 2>&1 || true' EXIT
       docker run -d --rm --label shadow.ephemeral=true --name "$CONTAINER_NAME" -e MYSQL_ROOT_PASSWORD=test mariadb:10
       ```
   - **Docker Compose Test Stack**:
     - Always run with an explicit project name (`-p <project>-test`) and tear down containers, anonymous volumes, AND locally built test images in `finally` / `trap EXIT`:
       ```powershell
       docker compose -p "$Project-test" -f docker-compose.test.yml down -v --rmi local --remove-orphans
       ```
   - **Temporary Test Images (`docker build`)**:
     - If a test builds a temporary image (`docker build -t <app>-test:temp`), always remove it in `finally` (`docker image rm -f <app>-test:temp`).
3. **Post-Test Leak & Process Teardown Verification**:
   - Tear down any test-spawned HTTP/dev/mock servers, background workers, or child processes in `finally` / `afterAll` (track owned PIDs via `shadow-monarch/scripts/resource_cleanup.py` when running shell harnesses; NEVER blanket-kill `node.exe`/`python.exe` or touch other projects' dev servers or active host/MCP sessions).
   - Before reporting tests as `VERIFIED-LOCAL`, run `python "shadow-quality/scripts/shadow_gate.py" --repo . --check-docker-leaks` (for Docker-backed suites) to verify zero leftover test containers or images remain.

---

## 3. Select coverage by failure surface

For a pure function, select representative inputs, boundary values and invariants. A discount calculation needs currency rounding and threshold cases. For a worker, exercise duplicate delivery, partial completion and retries where its contract requires them. For HTTP services, select applicable cases below using the actual status and authentication contract. Verify cleanup only for resources created by this run.
1. **Happy Path (`200`/`201`)**: Assert observable output and persisted database/queue state.
2. **Validation & Schema Failure (`400`/`422`)**: Missing required fields, invalid types, negative numbers.
3. **Unauthenticated (`401`)**: Missing, malformed, or expired token.
4. **Forbidden / Cross-Tenant IDOR (`403`/`404`)**: User from Tenant A attempting to access or mutate Tenant B's resource (`/shadow-auth`).
5. **Not Found (`404`)**: Valid UUID/ID not present in DB.
6. **Idempotency / Conflict (`409`)**: Duplicate unique key or repeated `Idempotency-Key` request (`/shadow-cache`).
7. **Boundary Values**: `0`, `-1`, empty list `[]`, `max + 1`, timezone/midnight edge cases, decimal/currency rounding.
8. **State & Container Isolation**: Verify zero leftover test records in development databases AND zero leftover Docker test containers, anonymous volumes, or temporary test-built images after suite teardown.

---

## 4. Execution Approval & Intent Boundary (`L0`–`L4`)
- Bounded unit/integration tests on verified local/sandbox environments are `L1_SAFE_VERIFICATION`. A unit-test request NEVER automatically authorizes `L2` broad E2E suites (`/shadow-browser`) or `L3` load/stress testing (`/shadow-perf`); require explicit approval (`execution_approval_gate.py`).
