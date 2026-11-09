---
name: shadow-browser
description: "Run automated browser E2E verification, mobile viewport (375px) overflow checks, console error inspection, and interactive UI testing using the official Playwright MCP. Trigger with /shadow-browser."
---

# /shadow-browser — Automated Browser E2E & Responsive UI Verification (Shadow Army)

Use this skill whenever the **Monarch** invokes `/shadow-browser` or wants live browser verification of a running Frontend web app.
Connects to the official **`playwright` MCP server** (`@playwright/mcp`) and `chrome-devtools-plugin`.

## Verification Checklist

1. **Desktop & Mobile Viewport Check (`375x812` & `1440x900`)**:
   - Navigate to the running local URL.
   - Verify zero horizontal overflow (`document.documentElement.scrollWidth <= window.innerWidth`) at mobile (`375px`), tablet (`768px`), and desktop (`1440px`) widths in compliance with `antislop-layoutmobile`.
2. **Console & Network Error Gate**:
   - Inspect browser console logs and network requests; report any unhandled JS exceptions, React hydration errors, CORS failures, or 4xx/5xx API responses.
3. **Interactive Control Verification**:
   - Click interactive buttons, modals, tabs, and forms to verify real behavior (`antislop` R-26).
