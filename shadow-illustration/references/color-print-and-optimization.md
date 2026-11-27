# Color Management, Print vs Screen & Asset Optimization

> Use this playbook to prevent washed-out colors, white/dark alpha halos, clipped print margins, or broken SVG optimizations.

## 1. Core Concepts
Digital screens emit additive light (`sRGB` / `Display P3`), whereas physical presses deposit subtractive ink (`CMYK`) across trimmed paper with mechanical cutting tolerances. Treating them identically causes muddy print purples, clipped bleed edges, broken dark-mode transparency halos, or broken CSS-animated inline SVGs when naive optimizers strip structural attributes.

## 2. Technical Rules & Decision Matrix

| Target Medium | Color Space | Resolution / Sizing | Structural & Margin Rules |
| :--- | :--- | :--- | :--- |
| **Web / Mobile UI** | `sRGB` baseline + optional `@media (color-gamut: p3)` | `1x` CSS px + `2x` HiDPI backing | Explicit `width`/`height` or `aspect-ratio`; preserve SVG `viewBox` |
| **Print (Posters, Roll-ups, PDFs)** | **CMYK** (`ISO Coated v2` / `GRACoL`) or vector `PDF/X-4` | **300 DPI** (`150 DPI` banners > 1.5m) | **3–5 mm bleed** beyond trim + **5–10 mm inner safe zone**; subset/outline fonts |
| **Transparent Web Art** | Straight/unpremultiplied `RGBA` PNG/WebP | Match container max `2x` | Verify matte-free edges against BOTH `#FFFFFF` and `#0F172A` |
| **Inline Multi-SVG Pages** | `currentColor` + semantic tokens | Optimized via SVGO | Keep `viewBox`, `<title>`/`<desc>`, and **unique prefixed IDs** (`prefixIds`) |

## 3. Implementation Examples

### Safe Production `svgo.config.mjs` (SVGO v4; Zero Broken `viewBox` / ID Collisions)
SVGO v4's `preset-default` no longer includes `removeViewBox` or `removeTitle`, so `viewBox` and `<title>` are kept unless a config enables those plugins. Do not add either plugin.
```js
/** @type {import('svgo').Config} */
export default {
  multipass: true,
  plugins: [
    {
      name: "preset-default",
      params: {
        overrides: {
          cleanupIds: false, // Keep IDs referenced by gradients/clips/JS
        },
      },
    },
    "prefixIds", // Rewrites #grad-1 -> #filename_grad-1 to avoid DOM collisions
    "removeDimensions",
  ],
};
```

### Progressive Display P3 with Safe sRGB Fallback
```css
:root {
  --brand-accent: #0b5fff;
}
@media (color-gamut: p3) {
  :root {
    --brand-accent: color(display-p3 0.04 0.37 1);
  }
}
```

## 4. Best Practices
- Export semi-transparent glows and feathered drop shadows using **straight alpha** — never render over a white canvas and magic-wand the background out.
- Strip Figma/Illustrator editor metadata (`inkscape:*`, `sodipodi:*`, comments, hidden layers, `data-name`) and forbid huge embedded base64 bitmaps pretending to be SVGs.
- Require printer proof PDFs (`PDF/X-4`) to embed crop marks and verify rich black (`C60 M40 Y40 K100`) on large fills while keeping body text pure `K100` to avoid ink registration blur.

## 5. Anti-Patterns (`WRONG` vs `RIGHT`)
- **WRONG (Minifier configs stripping `viewBox` & global `#clip0` IDs):** Running generic minifiers that delete `viewBox` or share `id="clip0_1_2"` across two inline hero SVGs (hiding the second SVG breaks `<defs>` across the whole DOM!).
  **RIGHT:** On SVGO v4 keep `removeViewBox` and `removeTitle` out of the config (they are no longer in `preset-default`; on older SVGO, disable them explicitly), preserve accessibility tags, and run `prefixIds` (plus `aria-hidden` cleanup only when decorative).
- **WRONG (Sending 72 DPI RGB PNGs to commercial offset print):** Exporting a web hero PNG directly for a roll-up banner or booklet without bleed.
  **RIGHT:** Export CMYK vector `PDF/X-4` (or `300 DPI` flattened CMYK TIFF/PDF) with `3–5 mm` bleed and `5–10 mm` safe text margins.

## 6. Production Considerations
- **Pre-Flight QA:** Inspect transparent assets composited over `#FFFFFF` and `#0F172A`, verify total SVG path node counts, and in CI re-run SVGO with the committed config and fail when the output differs from the committed file (deterministic asset hashing), so visual diffs remain auditable.
