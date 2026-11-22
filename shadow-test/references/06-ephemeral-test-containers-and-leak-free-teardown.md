# 06 — Ephemeral Test Containers, Leak-Free Teardown & Execution Approval Boundaries

## 1. Purpose & Activation Conditions
Run realistic database/Redis/broker integration suites with **singleton ephemeral Docker containers**, guaranteed **`try / finally` (`trap EXIT`) teardown** leaving zero orphan containers/volumes/images/processes, and strict adherence to **`L1` vs `L2`/`L3` execution approval boundaries**. Activate whenever configuring DB-backed test harnesses, Testcontainers, Docker Compose test stacks, or local mock/dev servers for tests.

## 2. Prerequisites
- Docker engine available locally or in CI for real-engine integration testing.
- Awareness of `shadow-quality/scripts/shadow_gate.py --check-docker-leaks` and `shadow-monarch/scripts/resource_cleanup.py`.

## 3. Technical Principles & Constraints
- **One Ephemeral Container Per Suite — NEVER One Container Per Test File:** Booting 18 separate Postgres/MariaDB containers across 18 test files wastes gigabytes of RAM, slows suites by 10x, and multiplies teardown leak risk. Start **1** shared ephemeral DB container per test run (on a dynamically allocated loopback port `127.0.0.1:0`), run migrations once, and isolate individual tests via `BEGIN ... SAVEPOINT ... ROLLBACK` or fast per-worker schemas (`test_worker_1`, `test_worker_2`).
- **Mandatory Ephemeral Container Metadata & Cleanup:**
  - Always pass **`--rm`** AND **`--label shadow.ephemeral=true`** on every `docker run` test/migration container.
  - Always wrap execution in **`try / finally`** (PowerShell / Python / JS `afterAll`) or **`trap '...' EXIT`** (Bash/POSIX) calling `docker rm -f -v <name>` (or `docker compose -p <project>-test down -v --rmi local --remove-orphans`).
  - If a suite builds a temporary test image (`docker build -t <app>-test:temp`), explicitly delete it in `finally` (`docker image rm -f <app>-test:temp`).
- **Ownership-Safe Process Teardown (Zero Blanket Kills!):** If a test harness starts an HTTP server, worker, or mock server, capture its exact spawned child `PID` / `server.close()` handle and close it in `finally`/`afterAll`. **NEVER** run blanket kills (`taskkill /IM node.exe /F`, `pkill -f python`) that destroy sibling projects' dev servers or active host/MCP sessions!
- **Intent & Approval Boundaries (`L1` vs `L2`/`L3`):**
  - Scoped unit/integration tests on local/sandbox targets = **`L1_SAFE_VERIFICATION`** (auto-allowed in task scope).
  - Unrequested broad repo E2E suites (`/shadow-browser`) or extra dependency installations = **`L2_SCOPE_EXPANSION`** (requires explicit approval).
  - Load/stress/soak testing (`/shadow-perf`) or unbounded fuzzing = **`L3_RESOURCE_INTENSIVE`** (requires explicit approval).
  - Touching staging/production databases or shared non-ephemeral infrastructure = **`L4_HIGH_IMPACT`** (strictly prohibited during unit/integration tests!).

## 4. Architecture & Implementation

### PowerShell Leak-Proof Ephemeral DB Test Harness (Windows Native)
```powershell
$ErrorActionPreference = "Stop"
$ContainerName = "app-test-pg-$PID"
try {
    docker run -d --rm --label shadow.ephemeral=true `
        --name $ContainerName `
        -p 127.0.0.1:0:5432 `
        -e POSTGRES_PASSWORD=test_only_local_pw `
        -e POSTGRES_DB=app_test `
        postgres:16-alpine | Out-Null
    if ($LASTEXITCODE -ne 0) { throw "Failed to launch ephemeral Postgres test container" }

    $HostPort = (docker port $ContainerName 5432/tcp).Split(":")[-1].Trim()
    $env:TEST_DATABASE_URL = "postgresql://postgres:test_only_local_pw@127.0.0.1:$HostPort/app_test"

    # Wait until pg_isready succeeds (bounded 30s loop, then migrate & run tests)
    for ($i = 0; $i -lt 30; $i++) {
        docker exec $ContainerName pg_isready -U postgres -d app_test *> $null
        if ($LASTEXITCODE -eq 0) { break }
        Start-Sleep -Seconds 1
    }

    npm run test:integration
} finally {
    docker rm -f -v $ContainerName 2>$null | Out-Null
}
```

### Bash / POSIX Equivalent (`trap EXIT`)
```bash
#!/usr/bin/env bash
set -euo pipefail
CONTAINER_NAME="app-test-pg-$$"
cleanup() {
  docker rm -f -v "$CONTAINER_NAME" >/dev/null 2>&1 || true
}
trap cleanup EXIT

docker run -d --rm --label shadow.ephemeral=true \
  --name "$CONTAINER_NAME" \
  -p 127.0.0.1:0:5432 \
  -e POSTGRES_PASSWORD=test_only_local_pw \
  -e POSTGRES_DB=app_test \
  postgres:16-alpine >/dev/null

# Run migrations & tests...
```

### Docker Compose Test Stack Teardown
```powershell
$Project = "orders-test-$PID"
try {
    docker compose -p $Project -f docker-compose.test.yml up -d --wait
    if ($LASTEXITCODE -ne 0) { throw "Compose test stack startup failed" }
    npm run test:integration
} finally {
    docker compose -p $Project -f docker-compose.test.yml down -v --rmi local --remove-orphans
}
```

## 5. Platform/Vendor Variations
- **Testcontainers (Node / Python / Java / Go / .NET):** Uses Ryuk reaper sidecar to clean up containers automatically, AND still bind containers to a single suite lifecycle (`globalSetup` / `conftest` session-scoped fixture) + explicit `container.stop({ removeVolumes: true })` in `globalTeardown` because Windows/restricted CI environments sometimes disable Ryuk!
- **PostgreSQL Speed Boost for Ephemeral Test Containers ONLY:** Mount `tmpfs` (`--tmpfs /var/lib/postgresql/data:rw,size=512m`) and pass `-c fsync=off -c synchronous_commit=off -c full_page_writes=off` **strictly on ephemeral disposable test containers** (NEVER in production!) — speeds up integration tests 3–5x and prevents SSD wear.
- **Database Safety Guardrail:** Always assert in test bootstrap that `DATABASE_URL` points to `127.0.0.1`/`localhost` AND database name ends with `_test` (abort immediately with non-zero exit if pointed at a staging/prod hostname!).

## 6. Decision Matrix & Trade-Offs

| Isolation Pattern | Speed | Parallel Worker Safety | Leak Risk If Crashed | Recommendation |
| :--- | :--- | :--- | :--- | :--- |
| **1 Container Per Test File** | Slow (`30–90s`) | High | **High** (18x containers) | Avoid |
| **1 Ephemeral Container + `SAVEPOINT` Rollback** | Very Fast (`< 3s` boot) | High (1 TX/test) | **Zero** with `--rm` + `finally` | **Default** for single-connection suites |
| **1 Ephemeral Container + Per-Worker Schema** | Fast | **Highest** (supports multi-TX tests!) | **Zero** with `--rm` + `finally` | Best when testing real `COMMIT` + concurrent pool locks |
| **Shared Persistent Dev DB** | Fast | **BROKEN** (pollutes dev data) | High data corruption | **NEVER** |

## 7. Real Production Scenario
A developer's CI runner ran out of disk space every 3 days with `No space left on device`. Investigation showed `docker ps -a` and `docker volume ls` held 140 exited `app-test-mariadb-*` containers and 65GB of anonymous volumes because test failures exited before reaching the final `docker rm` line (no `try/finally` or `--rm`). Moving to a single suite-scoped container with `--rm --label shadow.ephemeral=true`, `try/finally` (`docker rm -f -v`), and gating with `shadow_gate.py --check-docker-leaks` dropped leftover containers/volumes permanently to `0` and cut test wall time from 115s to 18s.

## 8. Failure Modes & Edge Cases
- **WRONG:** Placing `docker rm -f test-db` at the bottom of a script without `try / finally` or `trap EXIT` (whenever any test fails, cleanup is skipped!).
  **RIGHT:** Always wrap container & server teardown in `finally` / `trap EXIT` / `afterAll` AND pass `--rm --label shadow.ephemeral=true`.
- **WRONG:** Binding an ephemeral test container to `0.0.0.0:5432` (conflicts with developer's local Postgres and exposes test DB on LAN!).
  **RIGHT:** Always bind strictly to `127.0.0.1:0:5432` (random ephemeral loopback port).
- **WRONG:** Running `taskkill /IM node.exe /F` inside a test cleanup script to kill a lingering mock server.
  **RIGHT:** Store the spawned server reference or exact child PID (`server.close()` / `resource_cleanup.py --cleanup-owned`) and close ONLY owned resources.

## 9. Testing & Verification
- Run `python shadow-test/scripts/suite_hygiene_verifier.py --check-test-suite manifest.json` to audit Docker harness scripts for `--rm`, `shadow.ephemeral=true`, and guaranteed teardown.
- After running any Docker-backed test suite, run `python shadow-quality/scripts/shadow_gate.py --repo . --check-docker-leaks` to prove zero leftover containers, volumes, or temporary images remain.

## 10. Operational Considerations
- Verify safety guardrails reject non-local `TEST_DATABASE_URL` hosts before running `DROP SCHEMA` or `TRUNCATE` (defense in depth against accidental staging/prod wipes).
- Document exact test environment requirements and teardown commands in the repository `README.md` / `AGENTS.md`.

## 11. Authoritative References
- Docker Official Documentation — *Container Cleanup (`--rm`, `--volumes`), Compose `--rmi local --remove-orphans`*.
- Testcontainers Documentation — *Singleton Container Pattern & Reusable Ryuk Cleanup*.
- Shadow Quality Gate — `shadow-quality/scripts/shadow_gate.py --check-docker-leaks`.

## 12. Limitations & When NOT to Use
- Do NOT spin up Docker containers for pure domain logic unit tests (pricing math, parsers, validators) — keep pure unit tests sub-second with zero container overhead!
- Do NOT use `fsync=off` or `tmpfs` tuning on any persistent or staging database — strictly disposable local/CI test containers only.
