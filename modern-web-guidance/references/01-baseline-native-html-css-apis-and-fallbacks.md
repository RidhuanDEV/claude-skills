# 01 — Baseline Native HTML/CSS Platform APIs, `@supports` Fallbacks & Interactive Craft

## 1. Purpose & Activation Conditions
Replace obsolete polyfills, brittle `z-index: 9999` portals, and unnecessary npm UI packages with **Baseline Widely Available** native browser APIs (`<dialog>`, Popover API, `@container`, `:has()`, `:user-valid`, `oklch()`/`color-mix()`, `inert`), while gating Newly Available features cleanly behind `@supports` progressive enhancement and upholding the **Hard UI Craft Floor**. Activate at the start of any HTML, CSS, React, Vue, Angular, or Svelte UI build.

## 2. Prerequisites
- Target browser support tier (default: **Baseline Widely Available** = supported cleanly across Chrome, Edge, Safari, and Firefox for 30+ months).
- Optional live official lookup when online (`npx.cmd -y modern-web-guidance@1.0.1 search "<query>"` — never invent unverified guide IDs when offline!).

## 3. Technical Principles & Constraints
- **Native Top-Layer & Semantic Primitives First:**
  - **Modals & Drawers -> `<dialog>` (`showModal()`):** Native top-layer stacking (zero `z-index` wars!), built-in `::backdrop`, automatic `Escape` dismissal, and background `inert` interaction blocking! Always return keyboard focus to the trigger element on close (`/shadow-accessibility`).
  - **Popovers, Menus & Tooltips -> Popover API (`popover="auto"`, `popovertarget`):** Native top-layer + light-dismiss + `Escape` close with `0 KB` JS! Combine with **CSS Anchor Positioning (`anchor-name`, `position-anchor`)** ONLY inside `@supports (anchor-name: --a)` with a clean fallback for older Safari/Firefox!
  - **Component-Scoped Layouts -> Container Queries (`container-type: inline-size`, `@container`) & `:has()`:** Make cards, widgets, and form rows adapt to their *actual container* rather than brittle viewport media queries; use `:has()` for pure-CSS parent styling (e.g., `.field:has(:user-invalid)`).
  - **Native Form States -> `:user-valid` / `:user-invalid` + `autocomplete` + `inputmode`:** Style invalid states ONLY after user interaction (no premature red error borders on initial load!), paired with accessible `aria-invalid` + `aria-describedby`.
- **Semantic Design Tokens & Modern Color Math:** Bind custom components strictly to semantic theme variables (`@theme` / `:root`) using `oklch()`, `color-mix(in oklch, ...)`, and `light-dark()` — NEVER scatter ad-hoc hardcoded hex values that clash across light/dark themes!
- **Tailwind v4 Cursor & 5-State Hard UI Craft Floor:** Tailwind v4 preflight resets `<button>` to `cursor: default`. Always restore `cursor: pointer` on enabled interactive controls (`button:not(:disabled)`, `[role="button"]:not([aria-disabled="true"])`, `summary`, `select:not(:disabled)`, `label[for]`) and `cursor: not-allowed` on disabled controls, shipping all **5 interactive states** (`default`, `hover`, `active`, `:focus-visible` `3:1` ring, `disabled`)!

## 4. Architecture & Implementation

```css
/* Baseline Modern CSS: Interactive Craft Floor + Container Query + :user-invalid + Anchor Fallback */
@layer base {
  button:not(:disabled),
  [role="button"]:not([aria-disabled="true"]),
  summary,
  select:not(:disabled),
  label[for] {
    cursor: pointer;
  }

  button:disabled,
  select:disabled,
  input:disabled,
  [aria-disabled="true"] {
    cursor: not-allowed;
  }

  :where(a[href], button, input, select, textarea, summary, [tabindex]):focus-visible {
    outline: 2px solid var(--color-focus-ring);
    outline-offset: 2px;
  }
}

.product-card-shell {
  container-type: inline-size;
  container-name: card;
}

@container card (min-width: 28rem) {
  .product-card {
    display: grid;
    grid-template-columns: 12rem 1fr;
    gap: 1.25rem;
  }
}

.form-field:has(input:user-invalid) .field-error {
  display: block;
  color: var(--color-danger-text);
}

/* Progressive enhancement for Newly Available CSS Anchor Positioning */
.menu-popover {
  margin: 0.5rem auto; /* Clean centered fallback for non-supporting browsers */
}

@supports (anchor-name: --trigger) {
  .menu-trigger {
    anchor-name: --menu-btn;
  }
  .menu-popover {
    position-anchor: --menu-btn;
    inset: auto;
    top: anchor(bottom);
    left: anchor(left);
    margin-top: 0.375rem;
  }
}
```

### Baseline Browser Status & Fallback Decision Table

| Platform Feature | Baseline Tier | Safe Without Fallback? | Fallback / Guardrail |
| :--- | :--- | :---: | :--- |
| **`<dialog>` (`showModal()`), `inert`, `:focus-visible`** | **Widely Available** | **Yes** | Restore trigger focus on close (`/shadow-accessibility`) |
| **Container Queries (`@container`), `:has()`, `subgrid`, `100dvh`** | **Widely Available** | **Yes** | Set `min-width: 0` on flex/grid children |
| **Popover API (`popover`), `:user-valid`/`:user-invalid`** | **Widely Available / Newly** | High (Baseline 2024+) | Mirror server validation with `aria-invalid="true"` |
| **CSS Anchor Positioning, View Transitions, Scroll Animations** | **Newly / Limited** | **No** | Gate with `@supports` & `@media (prefers-reduced-motion: no-preference)` |

## 5. Platform/Vendor Variations
- **React 18/19 + Native `<dialog>`:** Invoke `dialogRef.current?.showModal()` inside controlled open effects (never render `<dialog open>` attribute alone — the `open` attribute skips top-layer modal behavior and `::backdrop`!).
- **Dark Mode & `color-scheme: light dark`:** Set `color-scheme: light dark` on `:root` so native scrollbars, date pickers, and form controls automatically match the active theme!

## 6. Decision Matrix & Trade-Offs

| Need | Prefer Native Platform | Pick Headless Primitive (Radix / React Aria) When |
| :--- | :--- | :--- |
| **Confirmation modal / drawer** | Native `<dialog>` (`0 KB`) | Complex nested modal stacks + animated exit transitions |
| **Disclosure / FAQ accordion** | Native `<details>` + `<summary>` | Animated height accordion with roving keyboard toolbar |
| **Card adapting to sidebar vs grid** | Native `@container` queries (`0 KB`) | Never use JS `ResizeObserver` solely for layout breakpoints! |

## 7. Real Production Scenario
A React admin app bundled 4 UI libraries (`react-modal`, `body-scroll-lock`, `react-resize-detector`, `@popperjs/core` = `+64 KB` gzipped) causing Safari scroll locks and `z-index` overlap bugs between tables and modals. Migrating modals to native `<dialog>`, responsive cards to `@container`, and form borders to `:user-invalid` removed 4 npm dependencies, cut client JS by `64 KB`, and resolved every `z-index` collision permanently.

## 8. Failure Modes & Edge Cases
- **WRONG:** Rendering `<dialog open>` instead of calling `dialog.showModal()`, or relying on CSS Anchor Positioning without an `@supports` fallback (floating menus land at `(0, 0)` top-left in older browsers!).
  **RIGHT:** Always open modal dialogs via `showModal()` and wrap Anchor Positioning inside `@supports (anchor-name: --a)` with a usable fallback position.
- **WRONG:** Leaving Tailwind v4's `button { cursor: default }` untouched or hardcoding `#3b82f6` in one component while the design system uses `--color-primary`.
  **RIGHT:** Restore interactive pointer cursors in `@layer base` and bind 100% of colors/radii/shadows to semantic theme tokens.

## 9. Testing & Verification
- Verify native `<dialog>`, Popover, `@container`, and fallback styling live across Chromium & WebKit in `/shadow-browser` (`375px`, `768px`, `1440px`).
- Run `python shadow-accessibility/scripts/a11y_html_verifier.py` on rendered HTML.

## 10. Operational Considerations
- Check Baseline status (`webstatus.dev` / MDN Baseline badge) before shipping Newly Available CSS/JS APIs to wide public Indonesian mobile audiences.

## 11. Authoritative References
- GoogleChrome `modern-web-guidance` (`modern-web-guidance@1.0.1`).
- W3C WebDX Community Group — *Web Platform Baseline Definitions*.
- MDN Web Docs — `<dialog>`, Popover API, CSS Containment Level 3 (`@container`), `:has()`, `:user-invalid`.

## 12. Limitations & When NOT to Use
- Do NOT trigger `modern-web-guidance` for backend SQL, ORM migrations, Dockerfiles, CI pipelines, or Python/Go CLI scripts.
