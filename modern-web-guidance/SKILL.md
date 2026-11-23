---
name: modern-web-guidance
description: "Modern Web Platform & Baseline Guidance (GoogleChrome modern-web-guidance). Use when building or styling HTML, CSS, React/Vue/Angular/Svelte components, native dialogs/popovers, container queries, `:has()`, `:user-valid`, animations, scroll effects, or Core Web Vitals (LCP/INP/CLS) & React/Next.js performance optimizations. Do NOT use for backend SQL/ORMs, Docker/CI pipelines, or local Python/Go CLI scripts."
---

# Modern Web Guidance (`/modern-web-guidance`) — Baseline Web Platform & Frontend Performance

Use this skill at the start of any HTML, CSS, UI component, or client-side web task so the Shadow Army uses **Baseline Widely Available** native web platform capabilities instead of obsolete polyfills or bloated third-party libraries.

- **Owner:** Baseline native HTML/CSS platform APIs (`<dialog>`, Popover, `@container`, `:has()`, `:user-valid`, `oklch()`), graceful `@supports` fallbacks, Tailwind v4 cursor/craft restoration, Core Web Vitals (`LCP`/`INP`/`CLS`) asset/yielding mechanics, and React/Next.js waterfall & bundle optimization.
- **Boundaries:** Deep WCAG screen-reader/RTL audits (`shadow-accessibility`), live Playwright E2E/viewport runs (`shadow-browser`), SEO CrUX search architecture (`shadow-seo`), backend SQL/ORMs (`shadow-db`), and Docker/CI pipelines (`shadow-ops`).

## Reference Guide

Load ONLY the 1–2 playbooks needed for the active frontend platform subtask:

| Module | Topic | Load When |
| :--- | :--- | :--- |
| [01-baseline-native-html-css-apis-and-fallbacks.md](references/01-baseline-native-html-css-apis-and-fallbacks.md) | `<dialog>` (`showModal()`), Popover API + Anchor `@supports` fallback, `@container`, `:has()`, `:user-valid`, `oklch()`, Tailwind v4 cursor restoration | Building modals, popovers, responsive cards, forms, themes, or replacing legacy UI npm libs |
| [02-core-web-vitals-assets-and-main-thread-yielding.md](references/02-core-web-vitals-assets-and-main-thread-yielding.md) | `LCP` (`fetchpriority="high"`, AVIF/WebP), `CLS` (`aspect-ratio`, `content-visibility: auto`), `INP` (`scheduler.yield()` chunking), reduced-motion View Transitions | Fixing slow hero loads, layout jumps, sluggish click/filter INP, or scroll animations |
| [react-nextjs-performance.md](references/react-nextjs-performance.md) | Eliminating async waterfalls, barrel/bundle splitting, RSC `React.cache()`, Server Actions & avoiding needless re-renders | Optimizing React or Next.js App Router rendering, bundles, and data fetching |
| [evaluations.md](evaluations.md) | Graded specialist evaluation scenarios (`MWG-EVAL-01..06`) | Auditing native-first platform choices, Tailwind v4 craft, CWV honesty, and backend non-triggering |

---

## 1. Live Official Guide Lookup (`GoogleChrome/modern-web-guidance`)

When network access is available, query the verified official CLI (`modern-web-guidance@1.0.1`, `GoogleChrome/modern-web-guidance-src`) first:

- **Windows (PowerShell):**
  ```powershell
  npx.cmd -y modern-web-guidance@1.0.1 search "<query>"
  npx.cmd -y modern-web-guidance@1.0.1 retrieve "<guide-id>"
  ```
- **macOS / Linux:**
  ```sh
  npx -y modern-web-guidance@1.0.1 search "<query>"
  npx -y modern-web-guidance@1.0.1 retrieve "<guide-id>"
  ```
- **Offline / Sandboxed Fallback:** If `npx` is unavailable or offline, try `npx --offline ...` or apply the self-contained Baseline Web Platform Matrix below without inventing unverified guide IDs.

---

## 2. Self-Contained Baseline Modern Web Platform Matrix

Prefer native platform primitives before adding npm dependencies:

| Use Case | Modern Native Standard | Guardrail / Fallback Policy |
| :--- | :--- | :--- |
| **Modals & Drawers** | Native `<dialog>` (`showModal()`, `::backdrop`, Escape, `inert`) | Return keyboard focus to trigger element on close (`/shadow-accessibility`). |
| **Popovers, Menus & Tooltips** | Popover API (`popover`, `popovertarget`) + CSS Anchor Positioning | Gate Anchor Positioning behind `@supports (anchor-name: --a)` with clean fallback. |
| **Component-Scoped Layout** | Container Queries (`container-type: inline-size`, `@container`), `subgrid`, `:has()` | Prefer `@container` over viewport-only `@media` for reusable widgets. |
| **Form Validation & UX** | `:user-valid` / `:user-invalid`, `autocomplete`, `inputmode` | Mirror server validation with `aria-invalid` + `aria-describedby` + visible `<label for>`. |
| **Theme Tokens & Color Math** | CSS Custom Properties (`@theme` / `:root`), `oklch()`, `color-mix()`, `light-dark()` | Bind 100% of custom UI to semantic theme tokens — zero ad-hoc hex values. |
| **Motion & Scroll** | View Transitions API, Scroll-driven animations (`animation-timeline`) | **Mandatory:** gate inside `@media (prefers-reduced-motion: no-preference)` with static fallback. |
| **Core Web Vitals (LCP/INP/CLS)** | Hero `<img>` with `width`/`height` + `fetchpriority="high"` (never `loading="lazy"`); `content-visibility: auto`; `scheduler.yield()` chunking | Never claim CWV pass numbers without real measurement (`antislop-ui` R-36 / R-40). |
| **Interactive Affordances (Tailwind v4)** | Restore `cursor: pointer` on enabled controls & `cursor: not-allowed` on `:disabled` | Always ship all 5 states (`default`, `hover`, `active`, `:focus-visible` 3:1, `disabled`). |

---

## 3. Browser Support & Fallback Policy
- **Default:** Features marked **Baseline Widely Available** ship cleanly without polyfills.
- **Newly / Limited Availability:** Feature-detect with `@supports` or runtime checks and degrade gracefully — never silently break Safari/Firefox users or add bloated polyfills without checking bundle impact.
