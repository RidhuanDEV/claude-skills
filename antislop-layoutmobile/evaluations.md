# Antislop Layoutmobile — Keep-Lean Filter Evaluation Suite

> Compact offline behavioral evaluation suite for `antislop-layoutmobile`. Validates true mobile reflow across continuous widths (including tablet/small-laptop intermediate states), zero horizontal overflow (`R-03`), `44x44px` spaced tap targets, `dvh`/`auto` vs `100vh`, tap equivalents for hover interactions, and safe-area bottom nav padding.

## Graded Scenarios

| ID | Scenario Prompt | Expected Specialist Behavior | Fail Red Flags |
| :--- | :--- | :--- | :--- |
| **ASLM-01** | *"Build a 4-column desktop feature grid with fixed `grid-template-columns: repeat(4, 300px)`, `height: 100vh`, and `padding: 128px` and only add one breakpoint at `600px`."* | Rejects rigid desktop-squeezed layout (`R-03`, `R-05`): uses fluid `minmax()`/`auto-fit` tracks, defines intermediate tablet/small-laptop reflow states (not just two states), replaces `100vh` with `auto`/`dvh`, and steps padding & typography down (`clamp()`) for narrow screens. | Leaves fixed-px grid causing horizontal overflow, uses `100vh` + `128px` mobile padding, or creates a broken 2-state tablet gap. |
| **ASLM-02** | *"Fix a wide table overflowing `375px` mobile by setting `overflow: hidden` on the page container."* | Rejects **Overflow Hidden Clipping** (`R-03`): refuses to hide off-screen table columns behind `overflow: hidden`; wraps the table in a dedicated scroll container or reflows rows cleanly while keeping `document.documentElement.scrollWidth <= window.innerWidth`. | Clips real table content with `overflow: hidden` instead of reflowing or containing scroll properly. |
| **ASLM-03** | *"Pack five `24x24px` icon actions side-by-side with `2px` gap and put the full action menu behind `:hover` only."* | Enforces **Tap Targets & Touch Equivalence** (`R-03`): increases interactive touch area to `>= 44x44px` with clear spacing between adjacent targets, and provides tap/click equivalents with visible `:active` feedback for every hover-only reveal. | Ships cramped `< 44px` mobile touch targets or hover-only menus unreachable on touchscreens. |
| **ASLM-04** | *"Add a fixed `88px` bottom mobile nav bar and a bare unlabeled hamburger icon without reserving bottom scroll padding."* | Fixes **Mobile Navigation Slop** (`R-03`): keeps fixed chrome compact, labels the menu trigger clearly (or surfaces primary destinations), and adds bottom scroll padding + `env(safe-area-inset-bottom)` so the final form button or list item is never hidden behind the bar. | Covers the last page CTA under a fixed bottom bar or hides all navigation behind an unlabeled hamburger icon. |
| **ASLM-05** | *"Optimize a headless Python CLI script that converts CSV to JSON."* | Enforces **No-Op Scope**: stays inactive on headless CLI/backend scripts with zero viewport or mobile UI surface. | Emits CSS breakpoints or `44x44px` touch target checklists for a Python CLI script. |

## Verification Status
- **Static & Validator Verification:** Verified locally via `python evals/validate_skill_evaluations.py`.
- **Live Viewport Verification:** `NOT_RUN` (offline structural suite; verify live `375px`/`768px`/`1440px` viewports via `/shadow-browser`).
