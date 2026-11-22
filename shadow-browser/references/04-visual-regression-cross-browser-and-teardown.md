# 04 — Visual Regression Stability, Cross-Browser Parity, CDP Diagnostics & Teardown

## 1. Purpose & Activation Conditions
Prevent flaky pixel diffs in visual regression tests, catch **WebKit (Safari) & Firefox rendering quirks**, measure **browser CLS/memory leaks via CDP**, and strictly enforce **zero leftover Chromium processes / dev servers** (`browser_close` + tracked PID cleanup) plus **`L1` vs `L2` scope approval**. Activate when configuring visual snapshots, investigating Safari/Firefox-only bugs, running CDP diagnostics, or wrapping up any Playwright session.

## 2. Prerequisites
- Local or CI Playwright browsers (`chromium`, `firefox`, `webkit`).
- Awareness of `shadow-monarch/scripts/resource_cleanup.py` and `L1` vs `L2` execution boundaries.

## 3. Technical Principles & Constraints
- **Deterministic Visual Regression Checklist (Zero False-Positive Diffs):** Before calling `expect(page).toHaveScreenshot()`:
  1. **Wait for Web Fonts:** `await page.evaluate(() => document.fonts.ready)` (prevents fallback Arial vs Inter/Plus Jakarta Sans jitter!).
  2. **Freeze Animations & Transitions:** Pass `animations: 'disabled'` (or inject `prefers-reduced-motion: reduce`) so blinking cursors and spinners never fail diffs.
  3. **Freeze Clock & Mask Dynamic Regions:** Use `page.clock.setFixedTime(new Date('2026-11-22T10:00:00Z'))` and pass `mask: [page.getByTestId('live-clock'), page.getByTestId('chart-canvas')]` for unavoidable dynamic sub-elements.
  4. **Pin OS / Docker Font Rendering:** Linux CI vs Windows/macOS subpixel font anti-aliasing ALWAYS differs — generate and compare golden snapshots inside the exact same OS/Docker container image (`mcr.microsoft.com/playwright:...`)!
  5. **Test Both Light & Dark Modes:** Set `colorScheme: 'dark'` alongside `'light'` so invisible dark-on-dark badges or broken custom selects are caught automatically.
- **Cross-Browser Parity (Chromium vs WebKit/Safari vs Firefox):**
  - **WebKit (Safari/iOS):** Stricter `new Date("2026-11-22 10:00:00")` parser (returns `Invalid Date` without `T` ISO separator!), stricter `SameSite` / ITP third-party cookie blocking, `:focus-visible` vs button click focus behavior, and `100dvh` toolbar sizing.
  - **Firefox:** Scrollbar width reservation differences (`scrollbar-gutter: stable`) and CSS subgrid / backdrop-filter edge cases.
- **Mandatory Browser & Dev-Server Teardown (Zero RAM Leaks!):**
  - Every interactive Playwright MCP session MUST invoke **`browser_close`** immediately upon finishing verification (`~300–600 MB` RAM freed immediately!).
  - If the task started a local dev server (`vite`, `next dev`, `uvicorn`) solely for browser verification, stop that exact tracked PID via `resource_cleanup.py --cleanup-owned` (or explicit `finally` child-process stop) before reporting completion — unless the Monarch explicitly requested keeping the live preview running (report exact `PID`, `port`, and stop command!).
  - **NEVER** run blanket `taskkill /IM node.exe /F` or `pkill -f node` (kills sibling project servers and active MCP hosts!).
- **Execution Approval Boundary (`L1` vs `L2`):**
  - Targeted Playwright verification of explicitly modified local/sandbox routes = **`L1_SAFE_VERIFICATION`**.
  - Running an unrequested full-repository E2E suite (`npx playwright test` across 100 unrelated specs) during a minor edit or unit-test task = **`L2_SCOPE_EXPANSION`** (requires explicit Monarch approval!).

## 4. Architecture & Implementation

```ts
// Strict TypeScript Visual Snapshot & CDP CLS Budget Config Helper (0 any, 0 casts)
export interface VisualSnapshotPolicy {
  readonly animations: 'disabled'
  readonly maxDiffPixelRatio: number
  readonly fullPage: boolean
  readonly colorSchemes: readonly ('light' | 'dark')[]
  readonly requiredFontReadyWait: boolean
  readonly fixedClockIsoUtc: string
}

export const PRODUCTION_VISUAL_POLICY: VisualSnapshotPolicy = {
  animations: 'disabled',
  maxDiffPixelRatio: 0.005, // 0.5% strict pixel budget (never 20–30%!)
  fullPage: false, // viewport-scoped avoids massive scroll stitching flake
  colorSchemes: ['light', 'dark'],
  requiredFontReadyWait: true,
  fixedClockIsoUtc: '2026-11-22T10:00:00Z',
}

export interface CdpLayoutShiftBudget {
  readonly cumulativeLayoutShift: number
  readonly maxAllowedCls: number // WCAG / Core Web Vitals Good threshold = 0.1
  readonly passed: boolean
}

export function evaluateClsBudget(observedCls: number, maxAllowedCls = 0.1): CdpLayoutShiftBudget {
  return {
    cumulativeLayoutShift: Number(observedCls.toFixed(4)),
    maxAllowedCls,
    passed: observedCls <= maxAllowedCls,
  }
}
```

### Cross-Browser & Visual Flake Elimination Matrix

| Flake / Engine Divergence | Cause | Deterministic Fix |
| :--- | :--- | :--- |
| **Font shift pixel diff** | Screenshot fired before WOFF2 webfont finished loading | `await page.evaluate(() => document.fonts.ready)` before capture |
| **Windows vs Linux CI pixel diff** | ClearType vs FreeType font subpixel hinting | Generate/update golden PNGs inside pinned Playwright Docker image |
| **WebKit `NaN` date crash** | `new Date("2026-11-22 10:00:00")` fails in Safari | Always parse strict ISO-8601 (`"2026-11-22T10:00:00Z"`) |
| **CLS jump (`CLS > 0.1`)** | Images/skeletons missing explicit `width`/`height` or `aspect-ratio` | Set explicit dimensions + inspect via CDP `PerformanceObserver('layout-shift')` |
| **Leaked Chromium RAM after QA** | Forgot `browser_close` / `browser.close()` on failure | Always call `browser_close` / `try { ... } finally { await browser.close() }` |

## 5. Platform/Vendor Variations
- **Chromium CDP Performance Diagnostics:** On Chromium, create a CDP session (`context.newCDPSession(page)`) to sample `Performance.getMetrics` (`JSHeapUsedSize`, `Nodes`, `LayoutCount`) across repeated navigation cycles to catch SPA DOM-node / detached-element leaks directly during E2E flows.
- **GitHub Actions / CI Matrix:** Run fast Chromium smoke/functional E2E on every PR (`< 3m`), and run full Chromium + WebKit + Firefox visual matrix on release branches or nightly builds to balance cost and confidence.

## 6. Decision Matrix & Trade-Offs

| QA Scope | Approval Level | Typical Runtime | Best Trigger |
| :--- | :--- | :--- | :--- |
| **Targeted Route Live Check (`375px`/`1440px`, Console, Clicks)** | `L1` (auto on UI task) | `15–45s` | Every modified UI route/component |
| **Targeted Component/Page Visual Diff (Light + Dark)** | `L1` | `10–30s` | Design-system, CSS token, or layout edits |
| **Full-Repo Cross-Browser E2E Suite (100+ specs)** | **`L2`** (explicit approval if unrequested) | `5–15m` | Pre-release / Staging gate or explicit Monarch request |
| **Production Live Mutating Browser Automation** | **`L4`** (FORBIDDEN without explicit approval) | High risk | Never for test writes; read-only synthetic uptime belongs in `/shadow-observe` |

## 7. Real Production Scenario
A booking dashboard worked perfectly in Chrome on Windows, yet Safari iOS users saw `Invalid Date` on every reservation card and a blank modal backdrop! Running a cross-browser Playwright WebKit pass caught both `new Date("2026-05-10 09:00")` (rejected by WebKit's strict ISO parser) and a missing `-webkit-backdrop-filter` fallback in 40 seconds — before release. Enforcing `browser_close` + tracked dev-server cleanup also eliminated the `2.4 GB` of stale Chromium/Vite processes that previously accumulated during long coding sessions.

## 8. Failure Modes & Edge Cases
- **WRONG:** Setting `maxDiffPixelRatio: 0.25` (25%!) so visual tests stop failing on CI (a broken red error banner or missing CTA button covers `< 5%` of pixels and slips right through!).
  **RIGHT:** Stabilize fonts/animations/clock/OS image first and keep pixel tolerance tight (`<= 0.005`–`0.01`).
- **WRONG:** Exiting a Playwright MCP verification turn without calling `browser_close` or leaving a task-started `vite` dev server orphaned.
  **RIGHT:** Call `browser_close` immediately when finished and stop ONLY task-owned dev servers via tracked PID / `resource_cleanup.py --cleanup-owned`.

## 9. Testing & Verification
- Verify `python -m unittest discover -s shadow-browser/tests -v` passes (`test_auth_and_host_boundaries.py` & `test_compare_action.py`).
- After live browser verification, confirm `browser_close` was invoked and no task-spawned dev server remains running (unless explicitly requested for live preview).

## 10. Operational Considerations
- Store Playwright Docker image version in lockstep with `@playwright/test` package version in `package.json` so browser binary versions never mismatch.
- Keep `shadow-browser` focused on QA/verification; if the Monarch wants narrated MP4/SRT product tutorials or scripted motion demo videos, route to `/shadow-video`.

## 11. Authoritative References
- Playwright Official Documentation — *Visual Comparisons (`toHaveScreenshot`), Clock API & Cross-Browser Projects*.
- Chrome DevTools Protocol (CDP) — *Performance & LayoutShift Diagnostics*.
- Shadow Monarch Resource Cleanup Protocol (`shadow-monarch/scripts/resource_cleanup.py`).

## 12. Limitations & When NOT to Use
- Do NOT use visual pixel-diff snapshots as the primary test for business logic or backend persistence — pair thin visual checks with semantic functional E2E (`01`) and backend integration suites (`/shadow-test`).
- Do NOT trigger `/shadow-browser` on pure backend/SQL/CLI tasks that have no web UI surface.
