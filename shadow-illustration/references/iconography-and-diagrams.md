# Iconography Systems, Technical Diagrams & Data-Driven Visuals

> Use this playbook for UI icon families, brand pictograms, custom architecture/isometric diagrams, annotated screenshots, or custom SVG/D3 infographics.

## 1. Core Concepts
Iconography and technical diagrams communicate structure at glance speed only when optical weight, stroke geometry, semantic color inheritance, and directional localization obey one coherent system. Ad-hoc SVGs break dark mode contrast, misalign baselines, and invert universal symbols in RTL locales.

## 2. Technical Rules & Decision Matrix

| Need | Pattern to Pick | Core Technical Constraint |
| :--- | :--- | :--- |
| Dense App UI Icons (`16–24px`) | SVG `<symbol>` sprite or tree-shakeable SVG component | Uniform `24x24` `viewBox`, `2px` live padding (`20x20` keyline), `currentColor`, consistent `1.5px`/`2px` stroke |
| Directional Navigation Icons | CSS `[dir="rtl"] .icon-directional` mirror class | Flip arrows/chevrons/reply/logout; NEVER flip clocks, checkmarks, search, or media play/pause |
| Architecture & Pitch Diagrams | Hand-crafted SVG or custom D3 layout (when Mermaid auto-layout clips) | Okabe-Ito color-blind safe palette + redundant shape/dash encoding + min `11–12px` effective text |
| Product Walkthrough Screenshots | Annotated PNG/WebP with masked PII & numbered callouts | Redact live secrets/customer names first; keep legend outside controls with `>= 3:1` badge ring |

### Okabe-Ito Color-Blind Safe Diagram Palette
- Use perceptually separable colors paired with distinct line styles: Blue `#0072B2`, Orange `#E69F00`, Sky `#56B4E9`, Bluish-Green `#009E73`, Vermilion `#D55E00`, Purple `#CC79A7`.

## 3. Implementation Examples

### Strict-TS Accessible Theme-Aware Icon + RTL Rule
```tsx
export interface IconProps {
  readonly title?: string;
  readonly directional?: boolean;
  readonly className?: string;
}

export function ArrowRightIcon({ title, directional = true, className = "" }: IconProps): JSX.Element {
  const dirClass = directional ? "icon-directional" : "";
  return (
    <svg
      viewBox="0 0 24 24"
      width={24}
      height={24}
      fill="none"
      stroke="currentColor"
      strokeWidth={2}
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden={title ? undefined : true}
      role={title ? "img" : undefined}
      className={`${dirClass} ${className}`.trim()}
    >
      {title ? <title>{title}</title> : null}
      <path d="M5 12h14" />
      <path d="m13 6 6 6-6 6" />
    </svg>
  );
}
```
```css
[dir="rtl"] .icon-directional {
  transform: scaleX(-1);
}
```

## 4. Best Practices
- Balance optical mass inside a `24x24` grid (`18x18` squares, `20x20` circles, `20x16` landscape rectangles) so mixed icons look equally heavy next to labels.
- Group custom diagrams into background zones (low-contrast fill, dashed border), primary nodes (`1.5px` stroke), and non-crossing directional connectors.
- Embed or explicitly set cross-platform sans/mono font stacks on standalone `.svg` diagrams so headless rasterizers (`resvg`, Chromium) compute accurate label widths.

## 5. Anti-Patterns (`WRONG` vs `RIGHT`)
- **WRONG (Icon fonts & hardcoded dark ink):** Loading `.woff` icon fonts (FOUT tofu boxes on slow networks) or hardcoding `stroke="#111827"` inside SVGs (invisible on dark themes).
  **RIGHT:** Inline `<svg>` / `<symbol>` sprite using `stroke="currentColor"` / `fill="currentColor"` so light, dark, and high-contrast themes adapt automatically.
- **WRONG (Global SVG flip in RTL & red/green status-only diagrams):** Applying `[dir="rtl"] svg { transform: scaleX(-1); }` (mirrors clocks, locks, checkmarks, and charts!) or coding pass/fail solely in `#16A34A` vs `#DC2626`.
  **RIGHT:** Opt-in `.icon-directional` only on directional glyphs, and pair Okabe-Ito colors with solid vs dashed strokes + text labels.

## 6. Production Considerations
- **Accessibility:** Decorative icons paired with visible button text MUST set `aria-hidden="true"`; standalone icon-only actions MUST provide an accessible label on the parent `<button>` or `<title>` inside `role="img"`.
- **PII & Security Hygiene:** Scrub customer emails, JWTs, API keys, and internal URLs with synthetic fixtures before screenshotting or annotating.
