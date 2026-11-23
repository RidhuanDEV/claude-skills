# Antislop Human — Keep-Lean Filter Evaluation Suite

> Compact offline behavioral evaluation suite for `antislop-human`. Validates mathematical WCAG contrast verification (no grey-on-grey hallucination), keyboard/focus-ring preservation (`R-32`), native semantic controls & `cursor: pointer` (`R-39`), `prefers-reduced-motion`, 200% zoom reflow, and whole-document vs single-component scoping.

## Graded Scenarios

| ID | Scenario Prompt | Expected Specialist Behavior | Fail Red Flags |
| :--- | :--- | :--- | :--- |
| **ASHU-01** | *"Use `#777777` text on `#FFFFFF` and `#555555` text on `#000000` for body copy — they look clean and definitely pass WCAG AA."* | Rejects the **Grey-on-Grey Hallucination** (`R-25`): computes exact contrast via `contrast-check.py` / WCAG luminance formula (`4.48:1` and `2.82:1` — BOTH fail normal-text `4.5:1`), checks worst-case scrim contrast over images/gradients, and selects verified `>= 4.5:1` / `>= 3:1` non-text pairings. | Eyeballs grey pairings and falsely claims `#777777` on white or `#555555` on black passes AA normal text. |
| **ASHU-02** | *"Remove ugly browser focus outlines with `outline: none`, use `<div onClick>` for icon-only close buttons with no `aria-label`, and signal form errors with only a red border."* | Blocks all three accessibility failures (`R-32`, `R-39`, `C-4`): replaces focus outline with a visible `>= 3:1` `:focus-visible` ring across all themes, uses native `<button type="button" aria-label="Close dialog">` with `aria-hidden="true"` SVG and `cursor: pointer`, and pairs color status with visible text/icon error messages. | Ships `outline: none` without replacement, unlabeled `<div onClick>` icons, or color-only error states. |
| **ASHU-03** | *"Add auto-playing parallax animations and lock body text inside fixed-height `overflow: hidden` containers."* | Protects vestibular & low-vision users (`R-39`, `WCAG 1.4.4`): wraps non-essential motion in `@media (prefers-reduced-motion: no-preference)`, provides pause controls for `> 5s` motion, and removes clipping `overflow: hidden` so text reflows cleanly at `200%` zoom. | Runs continuous motion ignoring `prefers-reduced-motion` or clips zoomed text at `200%`. |
| **ASHU-04** | *"Review this single standalone `<StatusBadge />` React component and fail it because it lacks `<html>`, `<main>`, and `<title>`."* | Respects **Single-Component vs Whole-Document Scoping**: applies `<html lang>`, `<main>`, and `<title>` checks strictly to whole-document tasks, evaluating `<StatusBadge />` on contrast, non-color-only text, and semantic role instead. | Falsely demands `<html>`/`<main>` landmarks inside a standalone leaf UI component. |
| **ASHU-05** | *"Lighthouse Accessibility scored 100, so certify our web app as fully WCAG 2.2 AA compliant."* | Rejects automated-score overclaiming (`R-36` & `references/WCAG.md`): explains Lighthouse checks only a subset of automated rules and never proves full WCAG 2.2 conformance without keyboard, focus, zoom, and screen-reader verification. | Certifies full WCAG 2.2 AA compliance from a Lighthouse score alone. |

## Verification Status
- **Static & Validator Verification:** Verified locally via `python evals/validate_skill_evaluations.py`.
- **Live Screen-Reader / Browser Testing:** `NOT_RUN` (offline structural suite; delegate live WCAG/axe E2E audits to `/shadow-accessibility` & `/shadow-browser`).
