# sub-QA-AUTOMATION — Authoring Rules for Playwright, Cypress, k6 Load Tests, Bruno & UAT Docs

Use when writing E2E browser tests, API contract tests, performance/load test scripts, Test Case Matrices (TCM),
or User Acceptance Testing (UAT) documents. Pair with `TESTING.md` for overall test strategy.

## 1. Playwright & Cypress (TypeScript) authoring rules

- **Locator priority (resilient to UI refactors)**:
  1. `page.getByRole('button', { name: 'Submit order' })`
  2. `page.getByLabel('Email address')` / `page.getByPlaceholder(...)`
  3. `page.getByText(...)` (for non-interactive content assertions)
  4. `page.getByTestId('order-summary-total')` (fallback when semantics are ambiguous)
  - **Forbidden**: brittle CSS class chains (`.div > .btn-primary:nth-child(2)`) or XPath expressions.
- **Zero arbitrary sleeps**:
  - **NEVER** write `await page.waitForTimeout(3000)` or `cy.wait(3000)`.
  - Always rely on web-first auto-retrying assertions (`await expect(locator).toBeVisible()`, `toHaveText()`, `toHaveURL()`)
    or explicit network/response waits (`page.waitForResponse(...)`).
- **Page Object Model (POM) & Typed Fixtures**:
  - Encapsulate locators and page actions inside typed Page/Component classes (`LoginPage`, `CheckoutModal`), keeping
    `expect(...)` assertions inside the test spec file so test intent remains explicit.
  - Strictly type all test data builders and fixtures (zero `any`, zero `as Type` casting).
- **Fast authentication & test isolation**:
  - Authenticate once via API in a setup project and save `storageState` (`playwright/.auth/user.json`) rather than
    repeating UI login in every test (except in `auth.spec.ts`).
  - Seed and clean up isolated test data per test/worker (unique email/tenant prefix) so parallel runs never collide.

## 2. Performance & Load Testing (`k6` / `Locust`) authoring rules

Every `k6` script (`load-test.js` / `.ts`) must include:
- **Explicit stages & workload profile**:
  - **Smoke** (1–5 VUs, 1 min) → **Average Load** (ramp to expected peak RPS, hold 10–15m) → **Stress / Spike** (ramp to
    2x–3x peak) → **Soak** (sustained load over hours to catch memory/connection leaks).
- **Mandatory pass/fail thresholds** (so CI fails automatically on regression):
  ```js
  export const options = {
    thresholds: {
      http_req_failed: ['rate<0.01'],              // < 1% errors
      http_req_duration: ['p(95)<400', 'p(99)<900'], // p95 < 400ms, p99 < 900ms
    },
  };
  ```
- **Realistic virtual user behavior**:
  - Parameterize test data from a shared array (`SharedArray`) so VUs do not all query the exact same cached DB row.
  - Include realistic think time (`sleep(Math.random() * 2 + 1)`) for user-journey tests, or use `constant-arrival-rate`
    executors when testing strict backend RPS targets.
  - Assert both `res.status === 200` and response body contract (`check(res, { 'has order id': (r) => ... })`) — a fast
    `200 OK` returning an HTML error page is a failed test.

## 3. API Contract Testing (Bruno `.bru` / Supertest / Schemathesis)

- **Bruno `.bru` collection rules**:
  - Store secrets and host URLs in environment files (`environments/local.bru`, `staging.bru`), never hardcoded in requests.
  - Include `assert` and `tests` blocks in every `.bru` file checking status code, required fields, types, and error envelopes.
  - Chain dependent requests cleanly using `bru.setVar("orderId", res.body.data.id)` with cleanup teardown requests.
- Verify negative contract cases for every endpoint: `400/422` schema validation failure, `401` missing/expired token,
  `403` cross-role/cross-tenant access, `404` non-existent ID, and `409` duplicate/idempotency conflict.

## 4. Test Case Matrix (TCM) & UAT Document authoring rules

When generating QA Test Cases or UAT Sign-off documents:
- **Standard TCM columns**:
  `Test ID (TC-MOD-001) | Feature / Story ID | Priority (P0/P1/P2) | Type (Positive/Negative/Edge/Security) | Preconditions & Role | Test Steps & Input Data | Expected Result (UI + DB/API state) | Actual Result | Status (Pass/Fail/Blocked)`.
- **Bug Report template**:
  `Title | Severity & Priority | Environment & Build Version | Preconditions & User Role | Exact Steps to Reproduce | Expected Behavior | Observed Behavior | Evidence (Logs, Request ID, Screenshot/HAR, DB State) | Suspected Layer`.
