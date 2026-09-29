# TESTING — Strategy, Required Cases & Quality of Tests

## 1. Layers

- **Unit** — pure logic, fast, many. Domain rules, calculations, validators, state machines.
- **Integration** — real interactions with DB, queue, cache, filesystem, framework wiring. Prefer real dependencies in
  containers (Testcontainers or Docker Compose) over mocking the database.
- **API/contract** — endpoint status codes, shapes, errors, auth; consumer-driven contracts between services where useful.
- **End-to-end** — a few critical user journeys (login, checkout, submit/approve). Do not try to prove everything with E2E.

Default pyramid: many unit → fewer integration → few E2E. Adjust for the system (a thin CRUD API may be mostly integration tests).

## 2. Test behavior, not implementation

Assert observable outcomes: "given valid input, the order is created, stock decremented and the response is 201",
not "method X was called once". Mock only at true boundaries (external HTTP APIs, clock, randomness, email/SMS providers).
Excessive mocking produces tests that pass while the real system fails.

## 3. Required cases for business logic

Happy path · invalid input · boundary values (0, 1, max, max+1, empty, very large) · not found · permission denied
and cross-user/tenant access · dependency failure and timeout · retry and duplicate request (idempotency) ·
concurrency/race for shared resources · regression test for every fixed bug (write it failing first).

Edge-case catalog to mine: null/undefined, zero, negatives, duplicates, huge payloads, invalid encoding/Unicode,
expired sessions, concurrent updates, partial DB state, timezone boundaries (UTC vs local midnight, DST, month end,
leap day), inclusive/exclusive ranges, pagination boundaries, floating-point money, integer overflow.

## 4. Test quality rules

- Deterministic: no dependence on execution order, real time (inject a clock), randomness (seed it), or external network.
- Isolated: each test sets up and cleans its own data (transactions rolled back, unique IDs, or fresh containers).
- Names describe behavior: `should_reject_order_when_total_is_negative`, `returns 403 when user edits another user's post`.
- Arrange–Act–Assert structure; one behavior per test; meaningful assertions (no `expect(result).toBeTruthy()` on complex objects).
- Avoid snapshot abuse, testing private internals, sleeping to wait (poll with timeout or use fakes), and coverage-chasing tests.
- Coverage is a signal, not a goal; critical paths need meaningful coverage, not 100% of trivial code.
- Flaky tests are bugs: quarantine, find the cause (shared state, time, async ordering, network), fix.

## 5. Tools by stack

| Stack | Unit / integration | HTTP / E2E | Mocks / fakes |
|---|---|---|---|
| Go | `testing`, table-driven tests, `testify` (optional), `-race` | `httptest`, Testcontainers-go | interfaces + fakes, `gomock` |
| .NET | xUnit (or NUnit), FluentAssertions/Shouldly | `WebApplicationFactory`, Testcontainers, Playwright | NSubstitute / Moq |
| TS/Node/NestJS | Vitest or Jest, `@nestjs/testing` | Supertest, Playwright/Cypress | `vi.fn`/`jest.fn`, MSW for HTTP |
| Python | pytest, fixtures, `pytest-asyncio`, hypothesis | FastAPI `TestClient`/httpx, Django test client, Playwright | `unittest.mock`, `respx`/`responses` |
| Java/Kotlin | JUnit 5, AssertJ, Kotest | Spring Boot Test, MockMvc/WebTestClient, Testcontainers | Mockito / MockK |
| PHP/Laravel | Pest or PHPUnit | Laravel HTTP tests, Dusk | Laravel fakes (`Queue::fake`, `Http::fake`), Mockery |
| Rust | `#[test]`, `#[tokio::test]`, `proptest` | `axum` + `tower::ServiceExt::oneshot`, `sqlx::test` | trait-based fakes, `mockall` |
| Dart/Flutter | `test`, `flutter_test` widget tests | `integration_test`, golden tests with care | `mocktail` |
| Frontend (React) | Vitest + Testing Library (query by role/label) | Playwright | MSW |

## 6. What to include when delivering code

For non-trivial implementations include tests (or at minimum a concrete test plan): test file paths, the cases above that apply,
how to run them, and any fixtures/containers needed. For bug fixes always include the regression test.

## 7. Testing checklist

Meaningful tests for critical behavior · edge and failure paths covered · authorization tested · concurrency/idempotency
tested where relevant · deterministic and isolated · realistic integration tests for DB/queue boundaries ·
regression test for the bug · runs in CI.
