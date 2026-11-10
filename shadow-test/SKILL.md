---
name: shadow-test
description: Polyglot Automated Unit, Integration, and API Contract Test Generator supporting TypeScript/JS (Vitest/Jest), Python (Pytest), Go (testing), PHP/Laravel (Pest/PHPUnit), Java/Kotlin (JUnit 5), .NET (xUnit), Rust, and Flutter. Enforces Risk-Based Test Pyramid, Deterministic Fixtures, Regression Selection, and Contract Compatibility. Trigger with /shadow-test.
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
3. **Consumer/Provider Contract Tests (Paired with `/shadow-api` & `/shadow-compat`)**: Verify HTTP status codes, response envelopes, required fields, and nullability match `openapi.yaml` so frontend/mobile consumers never break.

### B. Regression Selection for Bug Fixes
- Whenever fixing a bug or production incident (`/shadow-maintain`), write a targeted regression test that reproduces the exact failure first, then verify the fix turns it green.
- Run affected module tests first (`vitest related`, `pytest --lf`, `go test ./pkg/...`) for fast feedback before running the full test suite.

### C. Deterministic Fixtures & Zero Flakiness
- Inject or freeze clocks (`vi.useFakeTimers()`, `freezegun`) when testing token expiration, SLA deadlines, or date boundaries.
- Seed any random generators and use unique per-test identifiers (`randomUUID()`) or automatic transaction rollback (`BEGIN ... ROLLBACK` / `RefreshDatabase`) so tests pass in any execution order and in parallel CI runs.

---

## 3. Mandatory 8-Point Test Coverage Matrix

For every module, service, or endpoint under test, cover:
1. **Happy Path (`200`/`201`)**: Assert observable output and persisted database/queue state.
2. **Validation & Schema Failure (`400`/`422`)**: Missing required fields, invalid types, negative numbers.
3. **Unauthenticated (`401`)**: Missing, malformed, or expired token.
4. **Forbidden / Cross-Tenant IDOR (`403`/`404`)**: User from Tenant A attempting to access or mutate Tenant B's resource (`/shadow-auth`).
5. **Not Found (`404`)**: Valid UUID/ID not present in DB.
6. **Idempotency / Conflict (`409`)**: Duplicate unique key or repeated `Idempotency-Key` request (`/shadow-cache`).
7. **Boundary Values**: `0`, `-1`, empty list `[]`, `max + 1`, timezone/midnight edge cases, decimal/currency rounding.
8. **State Isolation**: Verify zero leftover test records in development databases.
