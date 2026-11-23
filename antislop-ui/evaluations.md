# Antislop UI — Keep-Lean Filter Evaluation Suite

> Compact offline behavioral evaluation suite for `antislop-ui`. Validates semantic token binding & 5 interactive states, rejection of default AI visual slop clusters, truthful dashboard data & empty/loading/error states, Core Web Vitals (`R-40`) honesty, and non-activation on backend tasks.

## Graded Scenarios

| ID | Scenario Prompt | Expected Specialist Behavior | Fail Red Flags |
| :--- | :--- | :--- | :--- |
| **ASUI-01** | *"Style our admin dashboard with blue-to-purple gradients, glassmorphism on navbar + cards + modal + sidebar, glowing pulsing dots next to every heading, and emoji rockets on every button."* | Rejects the stacked AI slop cluster (`R-01`, `R-04`, `R-10`, `R-13`, `R-19`, `R-31`): binds colors to the project's semantic design tokens, caps glass/glow strictly to purposeful focal elements (`<= 1–2`), removes decorative pulsing dots and UI emojis, and states a 1-line reason per visual decision. | Ships stacked purple gradients, 4-surface glassmorphism, decorative pulsing status dots, or rocket emojis on buttons. |
| **ASUI-02** | *"Build an invoice dashboard shell with 4 stat cards showing `12,483 / 94.2% / $48.2K / 1,204 (+12% this week)` and a fake activity feed (`Sarah Chen updated a document`)."* | Rejects fabricated dashboard filler (`R-17`, `R-18`, `R-38`, `C-3`): designs layout around the real primary user job, wires only real data (or clearly labeled placeholders in prototypes), and ships an informative empty state naming cause & next action instead of a fake feed. | Ships invented stat cards, fake deltas, or fictional activity feeds disguised as real product data. |
| **ASUI-03** | *"Add Tailwind v4 buttons to our settings form without setting cursor or focus styles, and use hardcoded `#1a1a1a` on cards that break light mode."* | Enforces the **UI Craft Floor** (`R-25`, `R-32`, `R-34`, `R-39`): binds cards to semantic theme tokens working across light & dark themes, restores `cursor: pointer` on enabled controls (`cursor: not-allowed` on disabled), and ships all 5 states (`default`, `hover`, `active`, `:focus-visible` 3:1, `disabled`). | Leaves Tailwind v4 buttons with default arrow cursor, breaks light/dark mode with hardcoded hex, or omits focus/active states. |
| **ASUI-04** | *"Lazy-load the hero image (`loading="lazy"`), omit image `width`/`height`, put a synchronous analytics script in `<head>`, and claim '99/100 Lighthouse LCP 0.8s' without measuring."* | Enforces `R-40` & `R-36`: puts hero `<img>` in HTML with `fetchpriority="high"` (never lazy), adds explicit intrinsic dimensions/`aspect-ratio`, defers/asyncs third-party scripts, and refuses to report unmeasured Core Web Vitals numbers. | Ships lazy hero image, unsized CLS-shifting media, render-blocking head scripts, or unmeasured performance claims. |
| **ASUI-05** | *"Configure an Express Postgres migration script with zero UI files."* | Enforces **No-Op Scope**: stays inactive on pure backend SQL/migration tasks without adding visual/CSS commentary. | Injects frontend color/motion checklists into a pure backend database migration task. |

## Verification Status
- **Static & Validator Verification:** Verified locally via `python evals/validate_skill_evaluations.py`.
- **Live Browser Rendering Check:** `NOT_RUN` (offline structural suite).
