# Advanced Browser E2E, Visual Regression, Fault Injection & CDP Diagnostics

## 1. Core Concepts
Senior browser verification goes beyond happy-path clicking: it validates **accessible locator resilience**, **network fault tolerance (`page.route` 500/429/401/202/offline)**, **deterministic visual regression stability**, **cross-browser rendering parity (Chromium, Firefox, WebKit/Safari)**, and **zero console/pageerror/CLS regressions**.

## 2. Technical Rules & Scenario Matrix

| Verification Target | Technique | Mandatory Pass Oracle |
| :--- | :--- | :--- |
| **Responsive Layout (`375px`, `768px`, `1440px`)** | Viewport resize + `scrollWidth <= innerWidth` check | Zero horizontal overflow, touch targets `>= 44×44px`, readable contrast. |
| **Session Expiry (`401`) & Recovery** | Intercept API with `401` via `page.route()` | Redirects or prompts re-auth cleanly without uncaught console exception or blank white screen. |
| **Async Job (`202 Accepted`)** | Stub `POST` returning `202` + `{ status: 'QUEUED' }` | UI displays pending/queued tracker honestly — never claims "Completed" prematurely. |
| **Server Fault (`500`) & Rate Limit (`429`)** | Stub route with `500` / `429 Retry-After: 5` | Renders accessible `role="alert"` message + retry affordance; submit button prevents double-submit. |
| **Visual Regression Snapshot** | Wait for `document.fonts.ready`, freeze animations & clock, mask timestamps | Pixel diff `< threshold` across light and dark themes. |

## 3. Implementation Examples
```ts
// Playwright Resilient Fault-Injection & Zero-Overflow Verification Pattern
export interface PageOverflowCheckResult {
  readonly viewportWidth: number
  readonly scrollWidth: number
  readonly hasHorizontalOverflow: boolean
}

export function evaluateViewportOverflow(innerWidth: number, scrollWidth: number): PageOverflowCheckResult {
  return {
    viewportWidth: innerWidth,
    scrollWidth,
    hasHorizontalOverflow: scrollWidth > innerWidth,
  }
}

export function classifyConsoleAndNetworkHealth(
  consoleErrors: ReadonlyArray<string>,
  uncaughtPageErrors: ReadonlyArray<string>,
  unexpected5xxUrls: ReadonlyArray<string>,
): { readonly passed: boolean; readonly failureReasons: ReadonlyArray<string> } {
  const reasons: string[] = []
  if (uncaughtPageErrors.length > 0) reasons.push(`Uncaught pageerror: ${uncaughtPageErrors.join('; ')}`)
  if (consoleErrors.length > 0) reasons.push(`Console errors: ${consoleErrors.join('; ')}`)
  if (unexpected5xxUrls.length > 0) reasons.push(`Unexpected 5xx responses: ${unexpected5xxUrls.join(', ')}`)
  return { passed: reasons.length === 0, failureReasons: reasons }
}
```

## 4. Best Practices
- Reuse existing brownfield E2E runners (**Playwright**, **Cypress**, **Puppeteer**) and prefer semantic locators (`getByRole`, `getByLabel`, `getByText`) over CSS class selectors.
- Authenticate once in a setup fixture (`storageState`) for feature suites, keeping a dedicated test file for login, invalid-credential `401`, and logout flows.

## 5. Anti-patterns (WRONG vs RIGHT)
- **WRONG:** Asserting `expect(res.status()).toBe(200)` while ignoring a blank white React crash screen or uncaught `TypeError` in the browser console.
- **RIGHT:** Fail the E2E oracle on any uncaught `pageerror`, unexpected console error, or missing visible landmark/heading.
- **WRONG:** Using `page.waitForTimeout(3000)` or brittle `.div > button:nth-child(3)` selectors.
- **RIGHT:** Wait on explicit accessible UI state (`expect(page.getByRole('status')).toHaveText(...)`) and semantic roles.

## 6. Production Considerations
- Never run mutating browser E2E suites against production hosts; enforce `L1` (targeted local route verification) vs `L2` (full repo E2E suite approval) boundaries strictly.
