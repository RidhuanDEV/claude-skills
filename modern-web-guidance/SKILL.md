---
name: modern-web-guidance
description: "Modern Web Platform & Baseline Guidance (GoogleChrome modern-web-guidance). Use when building or styling HTML, CSS, React/Vue/Angular/Svelte components, modals, popovers, forms, animations, scroll effects, or Core Web Vitals optimizations. Do NOT use for backend SQL/ORMs, Docker/CI pipelines, or local Python/Go CLI scripts."
---

# Modern Web Guidance (`/modern-web-guidance`)

Use this skill at the start of any HTML, CSS, UI component, or client-side web task so the Shadow Army uses **Baseline Widely Available** native web platform capabilities instead of obsolete polyfills or heavy third-party libraries.

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

## 2. Self-Contained Baseline Modern Web Platform Matrix

Prefer native platform primitives before adding npm dependencies:

| Use Case | Modern Native Standard | Guardrail / Fallback Policy |
| :--- | :--- | :--- |
| **Modals & Drawers** | Native `<dialog>` (`showModal()`, `::backdrop`, Escape handling, `inert` on background) | Always return keyboard focus to the trigger element on close; pair with `shadow-accessibility` & `antislop-human`. |
| **Popovers, Menus & Tooltips** | Popover API (`popover`, `popovertarget`) + CSS Anchor Positioning (`anchor-name`, `position-anchor`) | Anchor Positioning is Newly Available: include a lightweight CSS/JS fallback or feature check (`@supports (anchor-name: --a)`) when supporting older Safari/Firefox. |
| **Component-Scoped Layout** | Container Queries (`container-type: inline-size`, `@container`), CSS Grid `subgrid`, `:has()` | Prefer `@container` over viewport-only media queries for reusable cards/widgets. |
| **Form Validation & UX** | `:user-valid` / `:user-invalid`, `autocomplete` tokens, `inputmode`, native constraints (`min`/`max`/`step`) | Always mirror server validation errors with `aria-invalid` + `aria-describedby` and visible `<label htmlFor>`. |
| **Theme Tokens & Color Math** | CSS Custom Properties (`@theme` / `:root`), `oklch()`, `color-mix()`, `light-dark()` | Bind every custom component to semantic theme tokens — never scatter hardcoded hex values. |
| **Motion & Scroll** | View Transitions API, Scroll-driven animations (`animation-timeline`) | **Mandatory:** wrap all non-essential motion in `@media (prefers-reduced-motion: no-preference)` and provide clean static rendering when reduced motion is active. |
| **Core Web Vitals (LCP/INP/CLS)** | Hero `<img>` with explicit `width`/`height` or `aspect-ratio` + `fetchpriority="high"` (never `loading="lazy"`); `content-visibility: auto` for long offscreen sections; yield heavy main-thread work (`scheduler.yield()` / chunking) for INP | Never claim CWV pass numbers without real measurement (`antislop-ui` R-36 / R-40). |
| **Interactive Affordances (Tailwind v4 Safe)** | Base-layer CSS `button:not(:disabled), [role="button"]:not([aria-disabled="true"]), summary, select:not(:disabled) { cursor: pointer; }` and `:disabled { cursor: not-allowed; }` | Tailwind v4 preflight resets buttons to `cursor: default`; always restore pointer cursor + explicit `hover`, `active`, `:focus-visible` (3:1), and `disabled` states. |

## 3. Browser Support & Fallback Policy

- **Default:** Features marked **Baseline Widely Available** can ship without fallbacks.
- **Newly / Limited Availability:** Feature-detect with `@supports` or runtime checks and provide graceful progressive enhancement — never silently break Safari/Firefox users or add bloated polyfills without checking bundle impact.
