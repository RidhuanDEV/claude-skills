---
name: shadow-browser
description: "Use when verifying real browser behavior with Playwright, screenshots, console, navigation, or mocked network errors."
---

# `/shadow-browser` — Live Web Browser E2E, Responsive QA & Fault-Injection Verification

Use this skill whenever the **Monarch** invokes `/shadow-browser` or wants live browser verification of a running Frontend web app via Playwright Test or the official **`playwright` MCP server** (`@playwright/mcp`) and `chrome-devtools-plugin`.

- **Owner:** Semantic Playwright locators & `storageState` auth reuse, pre-declared action oracles (`compare_action.py`), `375px`/`768px`/`1440px` responsive overflow & touch-target QA, deterministic `page.route()` network fault injection (`401`/`429`/`500`/`202`/offline), visual regression stability, cross-browser WebKit/Firefox parity, and leak-free `browser_close` / dev-server teardown.
- **Boundaries:** Native iOS/Android mobile builds & store gates (`shadow-mobile`), narrated product tutorial videos (`shadow-video`), unit/integration suites (`shadow-test`), and deep WCAG/i18n/RTL engineering (`shadow-accessibility`).

## Reference Guide

Load ONLY the 1–2 modular playbooks needed for the active browser QA subtask:

| Module | Topic | Load When |
| :--- | :--- | :--- |
| [01-playwright-semantic-locators-and-auth-state.md](references/01-playwright-semantic-locators-and-auth-state.md) | Semantic locators (`getByRole`/`getByLabel`), `storageState` auth reuse, host safety guard, `compare_action.py` action oracles | Writing Playwright E2E specs, verifying live flows, fixing brittle CSS selectors |
| [02-responsive-viewports-and-mobile-overflow-qa.md](references/02-responsive-viewports-and-mobile-overflow-qa.md) | `375px`/`768px`/`1440px` viewport matrix, `scrollWidth <= innerWidth` offender finder, `44x44px` touch targets, `100dvh` | Checking mobile/tablet layout overflow, clipped modals/tables, or touch-target compliance |
| [03-network-fault-injection-and-console-oracles.md](references/03-network-fault-injection-and-console-oracles.md) | `page.route()` fault injection (`401`/`429`/`500`/`202`/offline/double-submit), zero-`pageerror`/hydration console oracle | Verifying frontend error handling, session expiry, async queued states, and blank-screen defense |
| [04-visual-regression-cross-browser-and-teardown.md](references/04-visual-regression-cross-browser-and-teardown.md) | `document.fonts.ready`, clock/animation freezing, light/dark + WebKit/Firefox parity, CDP CLS, `browser_close` & PID cleanup | Stabilizing visual diffs, catching Safari/Firefox bugs, enforcing zero leaked Chromium/dev processes |
| [evaluations.md](evaluations.md) | Graded specialist evaluation scenarios (`BRW-EVAL-01..07`) | Auditing UI/console oracles, mobile overflow checks, fault injection, teardown, and `L1`/`L2` scope |

---

## 1. Live Verification Checklist

1. **Desktop, Tablet & Mobile Viewport Check (`375x812`, `768x1024`, `1440x900`)**:
   - Navigate to the running local URL (explicitly allowlisted loopback/sandbox host only).
   - Verify zero horizontal overflow (`document.documentElement.scrollWidth <= window.innerWidth`) both at rest and with interactive overlays open, plus `>= 44x44px` mobile touch targets in compliance with `antislop-layoutmobile`.
2. **Pre-Declared Action, Console & Network Error Oracle**:
   - Before acting, record `role`, `route`, expected HTTP outcome, visible state, focus, and persistence after reload where relevant.
   - For invalid credentials, a `401` with the expected accessible error and `sessionPresent: false` can pass; a `200` with a blank white page or uncaught `pageerror`/console error fails the UI oracle. Attribute unrelated traffic separately. If the target is unreachable, mark the scenario **`BLOCKED`** and record the attempted URL without credentials.
3. **Interactive Control & Fault Verification**:
   - Actually click buttons, modals, tabs, and forms (`antislop` R-26) using accessible semantic locators (`getByRole`/`getByLabel`), and verify fault states (`401`/`429`/`500`/`202`/double-click) via `page.route()`.
4. **Mandatory Browser & Dev Server Teardown (Zero Leftover Processes)**:
   - Always call Playwright **`browser_close`** as soon as browser verification finishes so headless Chromium processes (`~300–600 MB` RAM) are released immediately.
   - If this task started a local dev server (`vite`, `next dev`, etc.) solely for browser checks, stop ONLY that exact tracked PID (`shadow-monarch/scripts/resource_cleanup.py --cleanup-owned`) before completing — unless the Monarch explicitly asked to keep the preview server alive (report its `PID` & `port`). NEVER run blanket kills (`taskkill /IM node.exe`) or touch sibling project servers or active host/MCP sessions.

---

## 2. Execution Approval (`L1` vs `L2`) & Repeatable Action Comparison

- Targeted Playwright/browser checks for explicitly modified UI routes on local/sandbox are **`L1_SAFE_VERIFICATION`**. Unrequested broad full-repo E2E suite runs (`playwright test` full suite during unit-test or minor edits) are **`L2: SCOPE_EXPANSION`** and require explicit Monarch approval (`shadow-monarch/scripts/execution_approval_gate.py`). Mutating E2E against production hosts is strictly prohibited without explicit `L4` approval.
- For repeatable review of one action, run `compare_action.py` setting `role`, `route`, `action`, and `visibleState` before the run (adding `httpStatus`, `sessionPresent`, `focusedControl`, or `persistedState` where applicable) and capturing matching fields + `environment` (`"reachable"` or `"unreachable"`) from the real run with zero raw credentials/PII/tokens:

```powershell
python shadow-browser/scripts/compare_action.py expected.json observed.json
python -m unittest discover -s shadow-browser/tests -v
```
