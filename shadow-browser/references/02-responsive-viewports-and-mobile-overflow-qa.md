# 02 — Responsive Viewport Matrix, Mobile `375px` Overflow & Touch-Target QA

## 1. Purpose & Activation Conditions
Detect and eliminate real-browser layout defects that unit tests and JSDOM cannot see — including **horizontal overflow at `375px` mobile / `768px` tablet / `1440px` desktop**, **cramped touch targets (`< 44x44px`)**, **clipped sticky headers/drawers**, **text overlap at `200%` zoom**, and **missing pointer/focus craft states** (`antislop-layoutmobile` & `antislop-ui`). Activate on every UI feature verification, responsive bug fix, or mobile web QA pass.

## 2. Prerequisites
- Live rendered web page in a real browser engine (Playwright MCP / Playwright Test / Chrome DevTools) — JSDOM has zero CSS layout calculation and CANNOT measure `scrollWidth` or bounding boxes!

## 3. Technical Principles & Constraints
- **Mandatory 3-Breakpoint Viewport Matrix:** Verify every modified route at:
  - **Mobile Small:** `375 × 812` (iPhone SE/13 mini baseline — also spot-check `320px` for WCAG 2.2 Reflow).
  - **Tablet / Split-Screen:** `768 × 1024` (where desktop sidebars and mobile grids most often collide!).
  - **Desktop:** `1440 × 900` (check max-width container balance, table alignment, and modal centering).
- **Zero Horizontal Overflow Gate (`scrollWidth <= innerWidth`):** Never "fix" horizontal overflow by slapping `overflow-x: hidden` on `html`/`body` (which silently cuts off buttons and breaks `position: sticky`!). Instead, query the exact DOM elements whose `getBoundingClientRect().right > window.innerWidth` and fix the offending flex/grid `min-width: 0`, table scroll wrapper (`overflow-x: auto` strictly on the table container!), or long unbroken URL/code strings (`overflow-wrap: anywhere`).
- **Mobile Touch Target Floor (`>= 44×44px`) & Interactive Cursor Craft:** Verify primary buttons, icon triggers, checkboxes, and nav links meet `>= 44×44px` hit areas on mobile (`375px`) with `>= 8px` spacing between adjacent destructive/confirm actions, and verify enabled buttons exhibit `cursor: pointer` and visible `:focus-visible` rings (`3:1` contrast).
- **Interactive Real-State Verification (`antislop` R-26):** Do not stop at static screenshots! Actually open mobile hamburger drawers, switch tabs, trigger validation errors, open modals/popovers, and re-run the overflow check while overlays/accordions are open!

## 4. Architecture & Implementation

```ts
// Strict TypeScript Real-Browser Viewport Overflow & Touch-Target Evaluator (0 any, 0 casts)
export interface ElementBoundsSample {
  readonly label: string
  readonly rightPx: number
  readonly widthPx: number
  readonly heightPx: number
  readonly isInteractive: boolean
}

export interface ResponsiveAuditReport {
  readonly viewportWidth: number
  readonly scrollWidth: number
  readonly hasHorizontalOverflow: boolean
  readonly overflowingElements: readonly string[]
  readonly undersizedTouchTargets: readonly string[]
}

export function evaluateResponsiveSnapshot(
  viewportWidth: number,
  scrollWidth: number,
  elements: readonly ElementBoundsSample[],
  minTouchPx = 44,
): ResponsiveAuditReport {
  const overflowing: string[] = []
  const undersized: string[] = []
  const isMobile = viewportWidth <= 480

  for (const el of elements) {
    if (el.rightPx > viewportWidth + 1) {
      overflowing.push(`${el.label} (right=${Math.round(el.rightPx)}px > ${viewportWidth}px)`)
    }
    if (isMobile && el.isInteractive && (el.widthPx < minTouchPx || el.heightPx < minTouchPx)) {
      undersized.push(`${el.label} (${Math.round(el.widthPx)}x${Math.round(el.heightPx)}px < ${minTouchPx}px)`)
    }
  }

  return {
    viewportWidth,
    scrollWidth,
    hasHorizontalOverflow: scrollWidth > viewportWidth + 1,
    overflowingElements: overflowing,
    undersizedTouchTargets: undersized,
  }
}
```

### Live Playwright `browser_evaluate` Diagnostic Snippet (Finds Exact Overflow Culprit)
```js
// Run read-only in Playwright browser_evaluate to pinpoint exact overflowing nodes at 375px:
() => {
  const vw = window.innerWidth;
  const sw = document.documentElement.scrollWidth;
  const offenders = Array.from(document.querySelectorAll('*'))
    .map((el) => {
      const r = el.getBoundingClientRect();
      return { tag: el.tagName, cls: String(el.className || '').slice(0, 60), right: Math.round(r.right), width: Math.round(r.width) };
    })
    .filter((item) => item.right > vw + 1 && item.width > 0)
    .slice(0, 10);
  return { viewportWidth: vw, scrollWidth: sw, hasHorizontalOverflow: sw > vw + 1, offenders };
}
```

## 5. Platform/Vendor Variations
- **iOS Safari Dynamic Viewport (`100dvh` vs `100vh`) & Safe Areas:** `height: 100vh` on mobile Safari gets hidden behind the bottom browser toolbar; prefer `min-height: 100dvh` and `padding-bottom: env(safe-area-inset-bottom)` on fixed bottom action bars (`modern-web-guidance`).
- **Wide Data Tables on `375px`:** Wrap data tables inside a dedicated scrollable container (`<div class="overflow-x-auto" tabindex="0" role="region" aria-label="Orders table">`) or transform rows into stacked cards on narrow screens — never let `<table>` push the entire document `scrollWidth` past `375px`!
- **Flex/Grid Child Shrink Bug:** CSS Flexbox/Grid children default to `min-width: auto`, causing long emails, UUIDs, or `<pre>` blocks to blow out mobile cards unless the flex/grid child sets `min-w-0` (`min-width: 0`).

## 6. Decision Matrix & Trade-Offs

| Layout Defect | Bad Band-Aid | Proper Engineering Fix |
| :--- | :--- | :--- |
| **Long invoice ID overflows `375px` card** | `body { overflow-x: hidden }` | `min-width: 0` on flex/grid item + `overflow-wrap: anywhere` |
| **10-column admin table overflows mobile** | Shrinking text to `9px` | Dedicated horizontal scroll region (`overflow-x-auto`) or mobile card stack |
| **Icon button is `24×24px` on mobile** | Making SVG giant & ugly | Keep `20px` icon inside `min-w-[44px] min-h-[44px]` button hit box |
| **Fixed footer covers submit button on iOS** | Hardcoding `bottom: 60px` | Use `100dvh` + `env(safe-area-inset-bottom)` + content bottom padding |

## 7. Real Production Scenario
A B2B procurement portal passed desktop QA (`1440px`), yet field supervisors on Android phones (`375px`) could not tap "Approve PO" because a wide status pill row pushed the flex header to `462px`, shifting the button off-screen. Running the `375x812` + `768x1024` + `1440x900` Playwright matrix with the `scrollWidth > innerWidth` diagnostic script pinpointed the exact offending header flex container (`missing flex-wrap & min-w-0`) and 4 undersized `28x28px` icon buttons in under 15 seconds.

## 8. Failure Modes & Edge Cases
- **WRONG:** Only checking `scrollWidth <= innerWidth` on initial page load before opening modals, dropdowns, or tabs (a drawer or popover often triggers horizontal scroll only when opened!).
  **RIGHT:** Re-run viewport overflow checks both at rest AND while interactive modals/drawers/tabs/error alerts are open.
- **WRONG:** Applying `overflow-x: hidden` on `<body>` to silence a Playwright overflow assertion while leaving clipped buttons inaccessible off-screen.
  **RIGHT:** Fix the underlying flex/grid/table container width so all interactive elements stay cleanly inside `[0, innerWidth]`.

## 9. Testing & Verification
- Add a fast Playwright responsive smoke test running across `[375, 768, 1440]` widths asserting `scrollWidth <= innerWidth`, zero clipped interactive buttons, and `>= 44x44px` hit areas at `375px`.
- Pair with `/shadow-accessibility` for `200%` zoom reflow and `+35%` pseudo-localization text-expansion checks.

## 10. Operational Considerations
- Combine responsive viewport verification with dark-mode/high-contrast toggle checks when the application supports themes.

## 11. Authoritative References
- W3C WCAG 2.2 — *Success Criterion 1.4.10 (Reflow at 320px)* & *2.5.8 (Target Size)*.
- MDN Web Docs — *CSS Grid/Flexbox `min-width: 0` & Dynamic Viewport Units (`dvh`)*.
- Shadow Army `antislop-layoutmobile` rules.

## 12. Limitations & When NOT to Use
- Do NOT use `shadow-browser` Playwright desktop emulation as a substitute for native iOS/Android gesture, WebView, or App Store compliance QA (`/shadow-mobile`).
