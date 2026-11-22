# 03 — Network Fault Injection (`page.route`), Console Oracles & Async UI States

## 1. Purpose & Activation Conditions
Prove that frontend applications survive real-world network hostility cleanly — **expired sessions (`401`)**, **rate limits (`429 Retry-After`)**, **server crashes (`500`/`503`)**, **asynchronous jobs (`202 Accepted`)**, **offline drops**, and **duplicate submit clicks** — while enforcing a strict zero-`pageerror`, zero-console-error, non-blank-UI oracle. Activate when verifying critical user forms, dashboards, or error recovery flows in Playwright.

## 2. Prerequisites
- Running local frontend app and Playwright test runner (`page.route()`) or Playwright MCP network/console inspection tools.
- Explicit separation between **expected negative-test HTTP statuses** (e.g., `401` on invalid login) and **unexpected network failures** (e.g., unrequested `500` on avatar/config API).

## 3. Technical Principles & Constraints
- **Zero-Crash Console & `pageerror` Oracle:** Attach `page.on('pageerror', ...)` and `page.on('console', msg => ...)` BEFORE `page.goto()`. Any uncaught JavaScript exception (`TypeError`, React hydration mismatch, unhandled promise rejection) or unexpected `5xx` fails the test immediately — even if the page returned HTTP `200`!
- **Mandatory 5 Fault Scenarios via Deterministic `page.route()` Injection:**
  1. **`401 Unauthorized` (Mid-Session Expiry):** Intercept an authenticated save/fetch with `401` -> verify UI redirects cleanly to login OR opens re-auth modal, clears stale session indicators, emits zero uncaught console errors, and (where supported) preserves unsaved form input.
  2. **`500 Internal Server Error`:** Intercept submit with `500` -> verify UI renders an accessible `role="alert"` message (displaying `Ref ID` if returned, NEVER raw stack trace!), keeps user input intact, re-enables the submit button for retry, and rolls back any optimistic UI state (`shadow-cache`).
  3. **`429 Too Many Requests` (`Retry-After: 5`):** Intercept with `429` -> verify UI displays clear rate-limit cooldown guidance rather than spamming infinite tight-loop retries!
  4. **`202 Accepted` (Async Background Job):** Intercept heavy export/settlement `POST` with `202` + `{ jobId, status: "QUEUED" }` -> verify UI displays an honest **Pending / Queued** tracker — NEVER falsely flashes "Completed!" before the job finishes!
  5. **Slow Response (`1500ms` Delay) + Double-Click Guard:** Delay `POST /orders` by `1500ms`, double-click the submit button rapidly -> verify the button enters a disabled/loading state immediately and ONLY **1** HTTP `POST` request leaves the browser!
- **Attribute Unrelated Traffic Separately:** When testing a real local backend, log any unexpected background `404`/`500` (e.g., missing `/favicon.ico` or broken analytics ping) separately so real defects aren't masked OR confused with the target endpoint's contract.

## 4. Architecture & Implementation

```ts
// Strict TypeScript Console, Pageerror & Network Fault Oracle Classifier (0 any, 0 casts)
export interface ObservedNetworkEvent {
  readonly url: string
  readonly method: string
  readonly status: number
}

export interface BrowserHealthOracleResult {
  readonly passed: boolean
  readonly failureReasons: readonly string[]
}

export function evaluateBrowserHealthOracle(opts: {
  readonly uncaughtPageErrors: readonly string[]
  readonly consoleErrors: readonly string[]
  readonly networkEvents: readonly ObservedNetworkEvent[]
  readonly allowedFailureStatusesByUrlSubstring?: Readonly<Record<string, readonly number[]>>
  readonly mainLandmarkVisible: boolean
}): BrowserHealthOracleResult {
  const reasons: string[] = []
  if (!opts.mainLandmarkVisible) {
    reasons.push('BLANK_OR_BROKEN_UI: expected <main> landmark or primary heading is missing')
  }
  if (opts.uncaughtPageErrors.length > 0) {
    reasons.push(`UNCAUGHT_PAGEERROR: ${opts.uncaughtPageErrors.join(' | ')}`)
  }
  if (opts.consoleErrors.length > 0) {
    reasons.push(`CONSOLE_ERROR: ${opts.consoleErrors.join(' | ')}`)
  }
  const allowMap = opts.allowedFailureStatusesByUrlSubstring ?? {}
  for (const ev of opts.networkEvents) {
    if (ev.status >= 400) {
      const explicitlyAllowed = Object.entries(allowMap).some(
        ([substr, statuses]) => ev.url.includes(substr) && statuses.includes(ev.status),
      )
      if (!explicitlyAllowed) {
        reasons.push(`UNEXPECTED_HTTP_${ev.status}: ${ev.method} ${ev.url}`)
      }
    }
  }
  return { passed: reasons.length === 0, failureReasons: reasons }
}
```

### Playwright `page.route()` Fault-Injection Pattern (500 + Double-Submit + 202)
```ts
// Playwright test snippet (Strict TS: 0 any, 0 casts)
// 1. Intercept POST /api/v1/exports with 202 Accepted and verify honest Queued state:
// await page.route('**/api/v1/exports', async (route) => {
//   await route.fulfill({
//     status: 202,
//     contentType: 'application/json',
//     body: JSON.stringify({ jobId: 'job_99', status: 'QUEUED' }),
//   })
// })
// await page.getByRole('button', { name: 'Export CSV' }).click()
// await expect(page.getByRole('status')).toContainText(/queued|diproses/i)
// await expect(page.getByRole('status')).not.toContainText(/completed|selesai/i)
```

## 5. Platform/Vendor Variations
- **React 18/19 & Next.js App Router Hydration Mismatches:** Console warnings matching `Hydration failed` or `did not match` indicate server/client HTML divergence (often caused by `Date.now()`, `Math.random()`, or `window` checks during render) — treat hydration errors as **FAIL** in the console oracle!
- **Service Workers / Offline Mode (`context.setOffline(true)`):** Toggle `await context.setOffline(true)` during form submission to verify offline banner feedback, then `setOffline(false)` to verify clean recovery without refreshing the entire page.
- **Playwright MCP Live Inspection:** Call `browser_console_messages` and `browser_network_requests` after every critical click/navigation step to enforce the exact same oracle during interactive agent verification.

## 6. Decision Matrix & Trade-Offs

| Fault Test Target | Method | Needs Broken Backend? | Catches What? |
| :--- | :--- | :--- | :--- |
| **`401` Session Expiry** | `page.route()` returning `401` | No | White screen on expired JWT, missing re-auth flow |
| **`500` / `429` Server Fault** | `page.route()` returning `500`/`429` | No | Silent swallowed error, lost form draft, missing `role="alert"` |
| **`202 Accepted` Async Job** | `page.route()` returning `202` | No | Dishonest "Success!" toast before background worker finishes |
| **Slow API + Double-Click** | `page.route()` delayed + 2 rapid clicks | No | Duplicate form submission, missing pending button lock |
| **Real End-to-End Persistence** | Live local backend + `page.reload()` | Uses real local DB | Broken API payload mapping, unpersisted writes |

## 7. Real Production Scenario
Users reported clicking "Submit Expense" on slow mobile connections and either seeing "Success!" when the server returned `500` or accidentally creating 3 duplicate expenses. A 25-line Playwright `page.route()` test injecting a `1.5s` delay + `500` error immediately exposed both bugs: the React `useMutation` hook showed the success toast inside `onClick` instead of `onSuccess` AND never disabled the submit button while `isPending === true`. Moving toast emission to `onSuccess`, adding `role="alert"` on `onError`, and locking the button during `isPending` fixed both defects with zero regression.

## 8. Failure Modes & Edge Cases
- **WRONG:** Mocking 100% of API routes in every E2E test with `page.route()` so the real backend is never tested end-to-end!
  **RIGHT:** Use real local backend integration for happy-path & reload-persistence tests (`01`), and reserve `page.route()` specifically for deterministic fault injection (`401`/`429`/`500`/`202`/latency/offline) that is awkward to force reliably against a live server.
- **WRONG:** Failing a negative invalid-login test because `POST /api/v1/login` returned `401` (when `401` WAS the exact expected outcome!).
  **RIGHT:** Explicitly register expected negative status codes in `allowedFailureStatusesByUrlSubstring` (and `expected.json` `httpStatus: 401` for `compare_action.py`).

## 9. Testing & Verification
- Validate fault-injection test suites verify BOTH the error state (`role="alert"` visible, input preserved) AND recovery (removing the `page.route` fault and clicking Retry succeeds cleanly!).

## 10. Operational Considerations
- Pair frontend error boundaries with backend `X-Request-Id` echoing (`shadow-observe`) so `500` fault tests also assert that `Ref ID: <requestId>` renders cleanly for customer support triage.

## 11. Authoritative References
- Playwright Official Documentation — *Network Interception (`page.route`) & Emulating Offline Mode*.
- WAI-ARIA Authoring Practices — *Alert & Status Live Regions*.

## 12. Limitations & When NOT to Use
- Do NOT use `page.route()` to bypass testing real backend authorization/IDOR enforcement — test server-side `401`/`403` security directly in `/shadow-test` and `/shadow-auth`.
