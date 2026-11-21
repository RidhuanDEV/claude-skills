# Programmatic Image Synthesis, Responsive Raster & Icon Pipelines

> Use this playbook when generating, compositing, converting, or batch-exporting images via code (`Sharp`, `Pillow`, `Satori`/`@vercel/og`, `resvg`, `Cairo`/`Skia`, `ImageMagick`) for web, mobile, social cards, or print.

## 1. Core Concepts
Code-driven image pipelines turn design templates, vectors, and raw bitmaps into deterministic, multi-resolution delivery assets during build or on demand. Key invariants:
- **Bundled Typography:** Programmatic text-to-image engines (`satori`, headless Chromium, `Pillow`) must resolve explicit `.woff2`/`.ttf` font binaries checked into the repository rather than host OS fonts, which drift across CI runners and containers.
- **Pixel-Grid Integrity & Alpha Hygiene:** Crisp UI icons, spritesheets, and maskable app icons require integer geometry alignment and clean alpha edges tested against both light and dark surfaces.

## 2. Technical Rules & Decision Matrix

| Deliverable | Node.js / TS Standard | Python Standard | Mandatory Constraints |
| :--- | :--- | :--- | :--- |
| Dynamic OG Cards / Social Banners | `satori` + `@resvg/resvg-js` or `@vercel/og` | `Pillow` + `cairosvg` / Playwright | Bundle explicit `.ttf`/`.woff2` fonts; cap 1200x630 export `<= 250 KB` |
| Fast Resize, Format Convert, Watermark | `sharp` (libvips) | `Pillow` (PIL) | Stream pipelines; strip EXIF GPS/camera PII unless explicitly required |
| Deterministic SVG to PNG/PDF | `@resvg/resvg-js` | `resvg` / `cairosvg` | Verify `<clipPath>` / `<filter>` and font fallback fidelity visually |
| Spritesheets & Pixel Art | `sharp` composite + JSON atlas | `Pillow` composite + JSON manifest | Use nearest-neighbor resampling; never apply lossy chroma subsampling |

### Responsive Delivery & App Icon Set
- **Modern `<picture>` Cascade:** Serve **AVIF** (Q 45–60) -> **WebP** (Q 75–82) -> **PNG** (alpha/line art) or progressive **JPEG** (opaque photos, Q 80–85), exporting `400w`, `800w`, `1200w`, and `1600w` variants with explicit `width`/`height` attributes.
- **Complete Brand Icon Set (from one verified square vector/1024px master):** `favicon.svg` (scalable, dark-mode CSS aware), `favicon.ico` (32x32), `apple-touch-icon.png` (180x180 opaque backdrop), `icon-192.png`, `icon-512.png`, and `icon-maskable-512.png` (all key logo shapes inside central 80% safe zone circle).

## 3. Implementation Examples

### Strict-TS Deterministic `sharp` Responsive Exporter
```ts
import sharp from "sharp";

export interface ExportSpec {
  readonly inputPath: string;
  readonly outDir: string;
  readonly baseName: string;
  readonly widths: readonly number[];
  readonly flattenOpaqueHex?: string;
}

export async function exportResponsiveRaster(spec: ExportSpec): Promise<readonly string[]> {
  const written: string[] = [];
  for (const width of spec.widths) {
    let pipeline = sharp(spec.inputPath).resize({ width, withoutEnlargement: true });
    if (spec.flattenOpaqueHex) {
      pipeline = pipeline.flatten({ background: spec.flattenOpaqueHex });
    }
    const avifOut = `${spec.outDir}/${spec.baseName}-${width}w.avif`;
    const webpOut = `${spec.outDir}/${spec.baseName}-${width}w.webp`;
    // Note: without .withMetadata(), sharp strips EXIF/IPTC/XMP PII by default.
    await pipeline.clone().avif({ quality: 52, effort: 4 }).toFile(avifOut);
    await pipeline.clone().webp({ quality: 80 }).toFile(webpOut);
    written.push(avifOut, webpOut);
  }
  return written;
}
```

### Zero-CLS Responsive `<picture>` Delivery
```html
<picture>
  <source type="image/avif" srcset="/img/hero-800w.avif 800w, /img/hero-1600w.avif 1600w" sizes="100vw" />
  <source type="image/webp" srcset="/img/hero-800w.webp 800w, /img/hero-1600w.webp 1600w" sizes="100vw" />
  <img src="/img/hero-1600w.webp" alt="Product architecture overview" width="1600" height="900" decoding="async" fetchpriority="high" />
</picture>
```

## 4. Best Practices
- Keep asset build scripts deterministic and idempotent (`npm run assets:build` / `python scripts/build_assets.py`) with vector masters committed and generated permutations tracked cleanly.
- Enforce placement byte budgets in CI (`hero <= 180 KB`, `thumbnail <= 45 KB`, `OG card <= 250 KB`).

## 5. Anti-Patterns (`WRONG` vs `RIGHT`)
- **WRONG (Host font drift & bloated GPS metadata):** Calling `satori(..., { fonts: [] })` or copying camera uploads verbatim via `.withMetadata()` (leaks photographer GPS/EXIF and breaks layout across Linux CI vs Windows).
  **RIGHT:** Read checked-in `.woff2` buffers via `fs/promises` and strip EXIF metadata by default before publishing.
- **WRONG (Transparent `apple-touch-icon.png` or edge-bleeding maskable icon):** Exporting `apple-touch-icon.png` with transparent corners (iOS fills alpha with solid black) or stretching a full-bleed logo to 100% of `icon-maskable-512.png`.
  **RIGHT:** Call `.flatten({ background: brandSurfaceHex })` for Apple icons and constrain maskable artwork inside the inner `409px` diameter (`80%` safe zone).

## 6. Production Considerations
- **Verification Gate:** Assert every generated file exists, has `size > 0`, matches target pixel dimensions via `sharp(file).metadata()`, and visually inspect transparent PNG/WebP variants over `#FFFFFF` and `#0F172A`.
- **DoS Protection:** Bound maximum input pixel dimensions (`limitInputPixels`) when processing untrusted uploads so decompression bombs cannot exhaust worker memory.
