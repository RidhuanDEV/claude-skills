---
name: shadow-accessibility
description: "Use when auditing WCAG, screen readers, ARIA, focus traps, accessible forms, or live regions. Not for visual refinement (/antislop-ui)."
---

# Shadow Accessibility (`/shadow-accessibility`) — Deep WCAG 2.2 AA/AAA, Assistive Tech, Cognitive UX & i18n/RTL

Works alongside `antislop-human` to provide deep, verifiable accessibility, inclusive UX, and internationalization/RTL engineering for public, enterprise, and government web/mobile applications.

- **Owner:** Semantic HTML landmarks & WAI-ARIA authoring, keyboard navigation & modal focus management, accessible forms & ARIA live regions, WCAG 2.2 contrast/color-independence/motion/target-size compliance, cognitive/neurodivergent accessibility, and i18n/ICU/`Intl.*`/CSS-logical RTL engineering.
- **Boundaries:** Design system brand identity & Figma tokens (`shadow-design`), live multi-viewport Playwright runs (`shadow-browser`), international `hreflang` SEO indexing (`shadow-seo`), and mobile native store gates (`shadow-mobile`).

## Reference Guide

Load ONLY the 1–2 modular playbooks needed for the active accessibility subtask:

| Module | Topic | Load When |
| :--- | :--- | :--- |
| [01-semantic-landmarks-and-aria-authoring.md](references/01-semantic-landmarks-and-aria-authoring.md) | Native HTML over ARIA, `<html lang>`, landmarks & skip links, sequential headings, accessible names, `inert`, tables | Auditing or building semantic page structure, navigation, icons, or data tables |
| [02-keyboard-focus-management-and-dialogs.md](references/02-keyboard-focus-management-and-dialogs.md) | Natural tab order (`0`/`-1`, zero positive `tabindex`), `:focus-visible` + `scroll-margin-block`, native `<dialog>` trap & trigger restore, roving tabindex | Fixing keyboard navigation, sticky-header obscured focus, modals/drawers, tabs, or dropdown menus |
| [03-forms-live-regions-contrast-and-motion.md](references/03-forms-live-regions-contrast-and-motion.md) | Programmatic labels (never placeholder-only), `aria-invalid`/`aria-describedby`, pre-mounted `aria-live`, WCAG `4.5:1`/`3.0:1` contrast, color-blind safety, `prefers-reduced-motion`, `200%` zoom | Hardening forms, error announcements, badges/charts, dark-mode contrast, or motion/zoom accessibility |
| [04-i18n-rtl-and-cognitive-accessibility.md](references/04-i18n-rtl-and-cognitive-accessibility.md) | ICU MessageFormat, `Intl.*` currency/timezone safety, CSS logical RTL, `<bdi>`, `+35%` pseudo-localization, Undo/session-extend/paste-friendly cognitive UX | Supporting Bahasa Indonesia/English/Arabic RTL, preventing clipped translations, or lowering cognitive load |
| [evaluations.md](evaluations.md) | Graded specialist evaluation scenarios (`A11Y-EVAL-01..08`) | Auditing WCAG 2.2 AA compliance, dialog focus restoration, contrast math, live regions, and RTL/i18n |

---

## 1. Core WCAG 2.2 AA, Cognitive & i18n Invariants

1. **Semantic HTML & Landmarks:** Use native `<button>`, `<a href>`, `<input>`, `<select>`, `<dialog>` over `<div onClick>`. Declare `<html lang>`, one `<h1>` with sequential headings, `<header>`/`<nav>`/`<main id="main-content">`/`<footer>`, and a **"Skip to main content"** link.
2. **Keyboard & Focus Management:** Maintain visual tab order (zero positive `tabindex > 0`), visible `>= 2px` `:focus-visible` ring (`>= 3:1` contrast), `scroll-margin-block` so sticky headers never obscure focus, and strict modal trapping + `Escape` close + exact trigger focus restoration.
3. **Forms & Pre-Mounted ARIA Live Regions:** Inspect rendered accessible name, role, and state (accept `<label for>`, wrapping `<label>`, or valid ARIA naming; reject placeholder-only). Link constraints/errors via `aria-describedby` + `aria-invalid="true"`, focus first invalid field or `role="alert"` summary, pre-mount `aria-live="polite"` containers, and record which assistive tech was actually exercised.
4. **Contrast, Color Independence, Target Size & Motion:** Enforce `>= 4.5:1` normal text, `>= 3.0:1` large text and UI borders/icons, pair status colors with explicit text + icons, enforce `>= 24×24px` desktop / `44×44px` mobile touch targets, honor `prefers-reduced-motion: reduce`, and guarantee zero horizontal scroll at `200%` zoom / `320px` width.
5. **Cognitive & i18n/RTL Resilience:** Zero memory-burden auto-dismissing error codes, allow password paste (`SC 3.3.8`), warn with 1-click extension before session expiry, support `+35–40%` text expansion, use CSS Logical Properties (`margin-inline`, `text-align: start`), `<bdi>` on codes/phones, ICU plurals, and `Intl.*` tied strictly to authoritative ISO-4217 currency & IANA timezones.

---

## 2. Deterministic Accessibility HTML & Contrast Verification

```powershell
python shadow-accessibility/scripts/a11y_html_verifier.py --self-test
python shadow-accessibility/scripts/a11y_html_verifier.py --check-html path/to/page.html
python shadow-accessibility/scripts/a11y_html_verifier.py --check-contrast "#4B5563" "#FFFFFF"
python -m unittest discover -s shadow-accessibility/tests -v
```

---

## 3. Foreign-Key Reference Routing (`T1` Audited Packs)
- **Inclusive Design & Screen Reader Flow Architecture:** [`ghaida-intent/skills/include/SKILL.md`](../shadow-design/references/external-upstreams/ghaida-intent/skills/include/SKILL.md) & [`accessibility-foundations.md`](../shadow-design/references/external-upstreams/ghaida-intent/skills/intent/references/accessibility-foundations.md)
- **Cultural, Linguistic & RTL/LTR Localization:** [`ghaida-intent/skills/localize/SKILL.md`](../shadow-design/references/external-upstreams/ghaida-intent/skills/localize/SKILL.md)
- **Accessibility, Responsive & Microcopy Rules:** [`06-accessibility-responsive-content.md`](../shadow-design/references/ai-product-designer-skill-pack/06-accessibility-responsive-content.md)
