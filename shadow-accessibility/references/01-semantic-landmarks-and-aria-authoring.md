# 01 — Semantic HTML Landmarks, Heading Hierarchy & WAI-ARIA Authoring Rules

## 1. Purpose & Activation Conditions
Build web interfaces whose underlying **Accessibility Tree** (exposed to NVDA, VoiceOver, JAWS, TalkBack, and voice control) is structurally sound from day one using **native HTML semantics**, **proper landmarks & skip links**, **sequential heading outlines**, and the **Five Rules of ARIA**. Activate when building or auditing page layouts, navigation bars, buttons, links, cards, tables, or custom widgets.

## 2. Prerequisites
- Target HTML/JSX/Vue/Svelte templates and understanding of the component's interactive purpose (navigation vs action vs disclosure vs status).

## 3. Technical Principles & Constraints
- **The First Rule of ARIA — Native HTML Beats Custom ARIA Every Time:**
  - Use `<button type="button">` for actions (NOT `<div onClick>` — native `<button>` gives you `Tab` focusability, `Enter` + `Space` activation, disabled semantics, and screen-reader role for free!).
  - Use `<a href="...">` for navigation (NOT `<button onClick={router.push}>` — native `<a>` supports middle-click new tab, right-click copy URL, and link-list navigation in screen readers!).
  - Use `<dialog>`, `<details>`/`<summary>`, `<select>`, and `<input>` before hand-rolling ARIA widgets (`modern-web-guidance`).
- **Complete Page Landmark Architecture + Skip Link:**
  - Every page MUST declare `<html lang="id">` (or accurate BCP 47 tag), a unique descriptive `<title>`, and clear landmark regions: `<header>`, `<nav aria-label="...">`, `<main id="main-content">`, optional `<aside>`, and `<footer>`.
  - Provide a visually hidden **"Skip to main content"** anchor (`<a href="#main-content" class="sr-only focus:not-sr-only">`) as the very first focusable element so keyboard users bypass 20 nav links on every page load!
- **Sequential Heading Outline (Zero Skipped Levels):** Exactly **one `<h1>`** describing the primary page purpose, followed sequentially by `<h2>` -> `<h3>` -> `<h4>` without jumping `<h1> -> <h3>` just to pick a smaller font size (style size with CSS classes, NEVER choose heading tags for typography!).
- **Accessible Names & Decorative Media Hygiene:**
  - Every icon-only button (`<button>` containing only an `<svg>`) MUST have an explicit accessible name (`aria-label="Close modal"` or `<span class="sr-only">Close modal</span>`) AND set `aria-hidden="true"` on the decorative `<svg>`.
  - Informative images require concise functional `alt="Sales growth chart showing Q3 +18%"`; purely decorative illustrations/dividers MUST set `alt=""` (empty string, NOT omitted — omitting `alt` makes screen readers announce the raw filename `hero-bg-v2-final.png`!).
- **Data Tables Need Real Semantics:** Use `<table>`, `<caption>`, `<thead>`, `<th scope="col">` / `<th scope="row">`, and `<tbody>` so screen readers announce row/column headers as users navigate cells.

## 4. Architecture & Implementation

```html
<!doctype html>
<html lang="id">
  <head>
    <meta charset="utf-8" />
    <title>Daftar Pesanan — Portal Operasional</title>
  </head>
  <body>
    <a href="#main-content" class="skip-link">Lewati ke konten utama</a>

    <header>
      <nav aria-label="Navigasi utama">
        <ul>
          <li><a href="/dashboard">Beranda</a></li>
          <li><a href="/orders" aria-current="page">Pesanan</a></li>
        </ul>
      </nav>
    </header>

    <main id="main-content" tabindex="-1">
      <h1>Daftar Pesanan</h1>
      <section aria-labelledby="orders-heading">
        <h2 id="orders-heading">Pesanan Aktif</h2>
        <table>
          <caption class="sr-only">Ringkasan pesanan aktif tenant saat ini</caption>
          <thead>
            <tr>
              <th scope="col">Kode Pesanan</th>
              <th scope="col">Status</th>
              <th scope="col">Aksi</th>
            </tr>
          </thead>
          <tbody>
            <tr>
              <th scope="row">ORD-2026-0042</th>
              <td><span>Menunggu Persetujuan</span></td>
              <td>
                <button type="button" aria-label="Lihat detail pesanan ORD-2026-0042">
                  Detail
                </button>
              </td>
            </tr>
          </tbody>
        </table>
      </section>
    </main>

    <footer>
      <p>Portal Operasional</p>
    </footer>
  </body>
</html>
```

### Native HTML vs Broken ARIA Quick Reference

| UI Pattern | Accessible Native Pattern | Broken Anti-Pattern |
| :--- | :--- | :--- |
| **Trigger an action** | `<button type="button">Simpan</button>` | `<div onClick={save}>Simpan</div>` |
| **Navigate to another route** | `<a href="/invoices/42">Lihat Invoice</a>` | `<span onClick={() => navigate('/invoices/42')}>` |
| **Icon-only close button** | `<button type="button" aria-label="Tutup dialog"><svg aria-hidden="true">...</svg></button>` | `<button><svg>...</svg></button>` (announced as "button" with no name!) |
| **Expandable accordion** | `<details><summary>FAQ</summary>...</details>` or `<button aria-expanded="false" aria-controls="panel-1">` | `<div onClick={toggle}>FAQ</div>` |
| **Decorative icon/divider** | `<img src="/wave.svg" alt="" />` / `<svg aria-hidden="true">` | `<img src="/wave.svg" />` (missing `alt`) |

## 5. Platform/Vendor Variations
- **Single-Page Applications (React Router / Next.js App Router / Vue Router):** Because client-side route transitions do not reload the full browser document, screen readers do NOT automatically announce page changes! Update `document.title` on every route change AND move focus (or announce via a polite route announcer) to the new `<main>` / `<h1>`.
- **Radix UI / React Aria / Headless UI / Ark UI:** When building complex ARIA composite widgets (Combobox, Menu, Tabs, Treeview, Popover), prefer battle-tested accessible headless primitives over hand-writing complex `aria-activedescendant` and roving-tabindex state machines from scratch!
- **Multiple `<nav>` Landmarks:** Whenever a page has more than one `<nav>` (e.g., top header nav + sidebar nav + pagination nav), give EVERY `<nav>` a unique `aria-label` (without repeating the word "navigation", e.g., `aria-label="Utama"`, `aria-label="Pagination"`).

## 6. Decision Matrix & Trade-Offs

| Component Complexity | Recommended Implementation | Verification Required |
| :--- | :--- | :--- |
| **Buttons, links, forms, disclosures, modals** | Native HTML (`<button>`, `<a>`, `<details>`, `<dialog>`) | `a11y_html_verifier.py` + keyboard tab check |
| **Tabs, Combobox, Dropdown Menu, Tooltip, Select** | Audited headless primitive (Radix / React Aria) styled with design tokens | Keyboard arrow/Escape matrix + screen-reader name/state audit |
| **Custom `<div role="grid">` hand-coded from scratch** | Avoid unless building spreadsheet-class canvas | Full APG keyboard & AT testing (NVDA + VoiceOver) |

## 7. Real Production Scenario
A government procurement portal failed its SPBE accessibility audit on 14 findings in 10 minutes: all 9 table action buttons were `<span onClick>` icons with no labels, heading levels jumped from `<h1>` to `<h4>`, and `<html lang>` was missing (causing NVDA to read Bahasa Indonesia text with English pronunciation!). Swapping `<span onClick>` to `<button type="button" aria-label="...">`, setting `<html lang="id">`, fixing heading order, and gating PRs with `a11y_html_verifier.py` resolved all 14 findings in one afternoon.

## 8. Failure Modes & Edge Cases
- **WRONG:** Nesting an interactive element inside another interactive element (`<a href="/item"><button>Favorite</button></a>` or `<button><a href="...">Details</a></button>`) — completely breaks screen readers and keyboard activation!
  **RIGHT:** Keep interactive controls as siblings (use CSS stretched-link `::after` pseudo-element on the primary link while elevating sibling buttons with `position: relative; z-index: 1`).
- **WRONG:** Putting `aria-hidden="true"` on a container that still holds focusable `<button>` or `<a>` children (screen-reader users tab into invisible unnamed ghost controls!).
  **RIGHT:** Use the native HTML `inert` attribute (supported across all modern Baseline browsers!) on background/closed off-canvas panels instead of `aria-hidden="true"` alone.

## 9. Testing & Verification
- Run `python shadow-accessibility/scripts/a11y_html_verifier.py --check-html path/to/page.html` to verify `<html lang>`, programmatic labels, semantic buttons, `alt` attributes, heading hierarchy, and focus indicators.
- Inspect the rendered Accessibility Tree in Chrome DevTools / Playwright `browser_snapshot` (`shadow-browser`) and record which assistive tech (NVDA/VoiceOver/TalkBack) was actually tested.

## 10. Operational Considerations
- Pair structural checks with `@axe-core/playwright` in CI, remembering that automated tools catch only `~35–45%` of WCAG issues — keyboard walkthroughs (`02`) and screen-reader checks remain essential!

## 11. Authoritative References
- W3C WCAG 2.2 Recommendation (w3.org/TR/WCAG22/) — Guidelines 1.1, 1.3, 2.4, 4.1.
- W3C WAI-ARIA Authoring Practices Guide (APG) — *Landmarks & Five Rules of ARIA*.
- `shadow-design/references/external-upstreams/ghaida-intent/skills/include/SKILL.md` (local `T1` audited reference).

## 12. Limitations & When NOT to Use
- Do NOT claim "100% WCAG compliant" solely from static HTML linters (`a11y_html_verifier.py` / `axe-core`) without manual keyboard navigation and rendered contrast/reflow verification.
