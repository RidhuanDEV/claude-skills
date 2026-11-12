---
name: shadow-accessibility
description: Advanced Accessibility QA & Engineering (WCAG 2.2 AA/AAA): Semantic HTML landmarks, ARIA roles & live regions, full keyboard navigation & focus management, screen reader compatibility, color-blindness safety, and reduced-motion support. Trigger with /shadow-accessibility.
---

# Shadow Accessibility (`/shadow-accessibility`) — Deep WCAG 2.2 AA/AAA & Assistive Tech QA

Works alongside `antislop-human` to provide deep, verifiable accessibility engineering and regression testing for public, enterprise, and government web/mobile applications.

---

## 1. The 6 Core WCAG 2.2 AA Compliance Pillars

### 1. Semantic HTML & Landmark Structure
- Use native interactive elements (`<button>`, `<a href>`, `<input>`, `<select>`, `<dialog>`) instead of `<div onClick>`.
- Every page must have a logical heading hierarchy (`<h1>` once per page, followed by `<h2>` -> `<h3>` without skipping levels) and proper landmarks (`<header>`, `<nav>`, `<main id="main-content">`, `<footer>`) plus a **"Skip to main content"** link for keyboard users.

### 2. Complete Keyboard Navigation & Focus Management
- Every interactive control must be reachable via `Tab` / `Shift+Tab` in visual reading order (`tabIndex={0}` or native focusable; never use positive `tabIndex > 0`).
- **Visible Focus Ring**: Always use `:focus-visible` with at least a `2px` high-contrast outline (`3:1` contrast against adjacent surface). Never write `outline: none` without a clear replacement.
- **Modals / Drawers / Dialogs**:
  - Trap focus inside the open modal (`Tab` cycles within modal controls).
  - Close on `Escape`.
  - Return focus to the exact trigger button when the modal closes.

### 3. Form Labels, Instructions & Error Announcements
- Every form input MUST have a programmatic `<label htmlFor="...">` (placeholder text is NOT a label replacement).
- Required fields and format constraints (e.g., password rules, date format) must be associated via `aria-describedby`.
- On validation failure:
  - Set `aria-invalid="true"` on the invalid input.
  - Link the error message element via `aria-describedby`.
  - Move focus to the first invalid field (or error summary banner with `role="alert"`).

### 4. Dynamic Updates & ARIA Live Regions
- Toast notifications, async form submission results, and filter result counts ("Showing 12 of 48 results") must use `aria-live="polite"` (or `role="alert"` / `aria-live="assertive"` for critical errors) so screen readers (NVDA, VoiceOver, TalkBack) announce changes without losing focus.

### 5. Contrast, Color Independence & Target Size (WCAG 2.2)
- Normal text contrast $\ge 4.5:1$; large text ($\ge 18\text{pt}$ or $14\text{pt}$ bold) and UI components/icons $\ge 3.0:1$.
- Never convey status by color alone (pair green/yellow/red badges with explicit text labels and icons).
- Interactive target size: minimum `24x24px` (WCAG 2.2 AA) and `44x44px` on mobile touch viewports.

### 6. Motion & Zoom Resilience
- Respect `@media (prefers-reduced-motion: reduce)` by disabling parallax, auto-playing animations, and non-essential transitions.
- Layout must remain readable and functional without horizontal scrolling when browser zoom is set to `200%` and down to `320px` CSS width.

### 7. Cognitive, Neurodivergent & Motor Accessibility (Beyond Bare Checklists)
- **Zero Memory-Burden Transitions**: Never force users to remember or manually re-type codes, IDs, or error details from a previous screen or dismissed toast. Keep reference context visible inline.
- **Forgiving Interactions (Undo Over Confirm)**: Support 1-click Undo for reversible actions, preserve all typed form inputs across validation failures or auth timeouts, and provide a warning with 1-click extension before any session timeout expires.
- **Plain, Non-Blaming Microcopy**: Error and empty-state copy must explain what happened and how to recover in plain language (`06-accessibility-responsive-content.md`). Never use "weaponized accessibility" or confusing double-negative consent toggles.

### 8. Localization (I18n), RTL & Text Expansion Resilience
- Layouts, badges, and buttons must accommodate `+30–40%` text length expansion (e.g., translating terse English UI labels into Bahasa Indonesia or German) without clipping or overlapping controls.
- Use CSS logical properties (`margin-inline`, `padding-inline`, `inset-inline`, `text-align: start`) and locale-aware date, number, and currency formatters (`Intl.DateTimeFormat`, `Intl.NumberFormat`).

---

## 2. Foreign-Key Reference Routing (`T1` Audited Packs)
- **Inclusive Design & Screen Reader Flow Architecture**: [`ghaida-intent/skills/include/SKILL.md`](file:///d:/Ridhuan%20Ngoding%20Moment/SKILL/shadow-design/references/external-upstreams/ghaida-intent/skills/include/SKILL.md) & [`accessibility-foundations.md`](file:///d:/Ridhuan%20Ngoding%20Moment/SKILL/shadow-design/references/external-upstreams/ghaida-intent/skills/intent/references/accessibility-foundations.md)
- **Cultural, Linguistic & RTL/LTR Localization**: [`ghaida-intent/skills/localize/SKILL.md`](file:///d:/Ridhuan%20Ngoding%20Moment/SKILL/shadow-design/references/external-upstreams/ghaida-intent/skills/localize/SKILL.md)
- **Accessibility, Responsive & Microcopy Rules**: [`06-accessibility-responsive-content.md`](file:///d:/Ridhuan%20Ngoding%20Moment/SKILL/shadow-design/references/ai-product-designer-skill-pack/06-accessibility-responsive-content.md)
