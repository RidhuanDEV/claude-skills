---
name: shadow-browser
description: "Live Web Browser E2E Verification. Use when running real Playwright browser tests, inspecting 375px mobile viewport overflow, checking browser console/network errors, or clicking through live web UI flows. Do NOT use for native mobile store gates (/shadow-mobile)."
---

# /shadow-browser — Automated Browser E2E & Responsive UI Verification (Shadow Army)

Use this skill whenever the **Monarch** invokes `/shadow-browser` or wants live browser verification of a running Frontend web app.
Connects to the official **`playwright` MCP server** (`@playwright/mcp`) and `chrome-devtools-plugin`.

## Verification Checklist

1. **Desktop & Mobile Viewport Check (`375x812` & `1440x900`)**:
   - Navigate to the running local URL.
   - Verify zero horizontal overflow (`document.documentElement.scrollWidth <= window.innerWidth`) at mobile (`375px`), tablet (`768px`), and desktop (`1440px`) widths in compliance with `antislop-layoutmobile`.
2. **Console & Network Error Gate**:
   - Before acting, record role, route, expected HTTP outcome, visible state, focus and persistence after reload where relevant. For invalid credentials, a 401 with the expected accessible error and no session can pass. A 200 with a blank page fails the UI oracle. Attribute unrelated traffic separately. If the target is unreachable, mark the scenario BLOCKED and record the attempted URL without credentials.
3. **Interactive Control Verification**:
   - Click interactive buttons, modals, tabs, and forms to verify real behavior (`antislop` R-26).

## Execution Approval & Intent Boundary (`L1` vs `L2`)
- Targeted Playwright/browser checks for explicitly modified UI routes on local/sandbox are `L1_SAFE_VERIFICATION`. Unrequested broad E2E suite runs (`playwright test` full repo suite during unit-test or minor edits) are **`L2: SCOPE_EXPANSION`** and require explicit Monarch approval (`shadow-monarch/scripts/execution_approval_gate.py`).

For repeatable review of one action, run `python scripts/compare_action.py expected.json observed.json` from the skill directory. Set the expected role, route, action and visibleState before the run. Add httpStatus, sessionPresent, focusedControl or persistedState where applicable. Capture matching fields and environment ("reachable" or "unreachable") from the real run. Keep raw credentials, personal data and tokens out of the evidence. The comparison validates supplied observations only.

## Deep Browser QA Reference (Load On-Demand)
- For brownfield Playwright/Cypress/Puppeteer reuse, `storageState` auth reuse, `page.route()` network fault injection (500/429/401/202/offline), visual regression masking & font wait, WebKit/Firefox quirks, and CDP CLS/memory traces -> read [Advanced E2E & visual QA playbook](references/advanced-e2e-and-visual-qa.md).
