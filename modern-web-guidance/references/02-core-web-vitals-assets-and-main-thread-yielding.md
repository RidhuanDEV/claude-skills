# 02 — Core Web Vitals (LCP, INP, CLS), Asset Loading & Main-Thread Yielding

## 1. Purpose & Activation Conditions
Achieve measurably fast, jank-free web experiences across **Largest Contentful Paint (`LCP <= 2.5s`)**, **Interaction to Next Paint (`INP <= 200ms`)**, and **Cumulative Layout Shift (`CLS <= 0.1`)** using native browser scheduling, priority hints, aspect-ratio reservations, `content-visibility`, and reduced-motion-safe View Transitions. Activate when optimizing frontend load speed, fixing sluggish clicks/filters, eliminating layout jumps, or auditing page experience alongside [references/react-nextjs-performance.md](react-nextjs-performance.md).

## 2. Prerequisites
- Real measurement plan (Chrome DevTools Performance panel, Lighthouse lab trace, or CrUX/RUM field telemetry — NEVER fabricate or guess CWV pass numbers without measurement!).

## 3. Technical Principles & Constraints
- **LCP (`<= 2.5s`) — Make the Hero Discoverable Immediately in Initial HTML:**
  - **NEVER** put `loading="lazy"` on the above-the-fold hero `<img>`! Always set **`fetchpriority="high"`** + `decoding="async"` + explicit `width` & `height` (and `<link rel="preload" as="image" fetchpriority="high" href="...">` if the hero image is referenced via CSS or delayed JS).
  - Serve responsive modern formats (`AVIF` / `WebP`) with accurate `srcset` and `sizes` so a `375px` phone doesn't download a `2400px` desktop banner!
  - Preload critical primary webfont WOFF2 (`crossorigin`) with `font-display: swap` (or `optional` for zero layout jump) and match fallback metrics (`size-adjust`) to minimize text reflow.
- **CLS (`<= 0.1`) — Reserve Every Box Before Pixels Arrive:**
  - Always declare explicit `width`/`height` or CSS `aspect-ratio` on every `<img>`, `<video>`, `<iframe>`, skeleton loader, and ad/embed slot.
  - Never dynamically inject top banners, cookie bars, or async notices *above* already-rendered content without reserving space or overlaying cleanly.
  - Reserve scrollbar gutter (`scrollbar-gutter: stable`) where modal/page scrollbars toggle abruptly.
- **INP (`<= 200ms`) — Keep Event Handlers Short & Yield Long Tasks (`> 50ms`):**
  - Long synchronous JavaScript loops (`> 50ms` filtering 10,000 rows, complex JSON transforms, heavy DOM updates inside `onClick`/`onInput`) block browser painting and spike `INP`!
  - Break heavy client tasks into chunks yielding back to the main thread using **`scheduler.yield()`** (with a graceful `setTimeout(0)` fallback for browsers without `scheduler.yield`), debounce non-urgent search filters cleanly, and keep heavy transforms on the server (`react-nextjs-performance.md`).
  - Use **`content-visibility: auto; contain-intrinsic-size: auto 600px;`** on long below-the-fold sections (huge comment lists, long documentation tables) so the browser skips offscreen layout & paint work!
- **Motion & View Transitions Restraint:** Wrap View Transitions (`document.startViewTransition`) and CSS scroll-driven animations (`animation-timeline: view()`) strictly inside **`@media (prefers-reduced-motion: no-preference)`** (and `matchMedia('(prefers-reduced-motion: reduce)').matches` check in JS) — animate ONLY compositor-friendly properties (`transform`, `opacity`), NEVER `top`/`left`/`width`/`height`!

## 4. Architecture & Implementation

```html
<!-- LCP-Optimized Hero + Zero-CLS Responsive Image + Offscreen content-visibility -->
<head>
  <link rel="preload" as="image" href="/images/hero-800.avif" fetchpriority="high" />
</head>
<body>
  <section class="hero">
    <picture>
      <source type="image/avif" srcset="/images/hero-480.avif 480w, /images/hero-960.avif 960w, /images/hero-1440.avif 1440w" sizes="(max-width: 768px) 100vw, 1200px" />
      <img
        src="/images/hero-960.webp"
        alt="Dashboard operasional ringkasan pesanan harian"
        width="1200"
        height="675"
        fetchpriority="high"
        decoding="async"
      />
    </picture>
  </section>

  <section class="below-fold-catalog">
    <!-- Deferred layout/paint for long below-the-fold sections -->
  </section>
</body>
```

```ts
// Strict TypeScript Main-Thread Yielding Helper for Responsive INP (scheduler.yield + fallback, 0 any, 0 casts)
interface SchedulerWithYield {
  readonly yield?: () => Promise<void>
}

export async function yieldToMainThread(): Promise<void> {
  const globalObj: { readonly scheduler?: SchedulerWithYield } = globalThis
  if (typeof globalObj.scheduler?.yield === 'function') {
    await globalObj.scheduler.yield()
    return
  }
  await new Promise<void>((resolve) => {
    setTimeout(resolve, 0)
  })
}

export async function processChunkedForLowInp<T, R>(
  items: readonly T[],
  mapper: (item: T) => R,
  chunkSize = 100,
): Promise<readonly R[]> {
  const results: R[] = []
  for (let i = 0; i < items.length; i += chunkSize) {
    const slice = items.slice(i, i + chunkSize)
    for (const item of slice) {
      results.push(mapper(item))
    }
    if (i + chunkSize < items.length) {
      await yieldToMainThread()
    }
  }
  return results
}
```

### Core Web Vitals Root-Cause & Fix Matrix

| Metric | Good Threshold (p75) | Top Real-World Culprit | Primary Platform Fix |
| :--- | :---: | :--- | :--- |
| **LCP** | `<= 2.5s` | Hero `<img>` with `loading="lazy"`, client-only JS fetch before hero render, unoptimized 3MB PNG | Remove `loading="lazy"`, add `fetchpriority="high"` + AVIF/WebP + SSR HTML hero |
| **INP** | `<= 200ms` | Long `> 100ms` JS handler on click/input, huge DOM (`> 1,500` nodes), re-rendering whole table on 1 keystroke | `yieldToMainThread()` chunking, `content-visibility: auto`, memoize/virtualize list (`react-nextjs-performance.md`) |
| **CLS** | `<= 0.1` | Images without `width`/`height`, late-inserted top promo banner, webfont fallback width jump | Explicit `width`/`height` or `aspect-ratio`, reserve space, `font-display: swap` + fallback metrics |

## 5. Platform/Vendor Variations
- **Next.js (`next/image`) & React Frameworks:** Set `priority` (or `preload` in newer Next versions) ONLY on the single primary above-the-fold LCP image — NEVER put `priority` on 12 grid cards (competes for bandwidth with the hero!). Pair with [references/react-nextjs-performance.md](react-nextjs-performance.md) for eliminating RSC/client async waterfalls and barrel-file bundle bloat!
- **View Transitions API (`document.startViewTransition`):** Always feature-detect `if (typeof document.startViewTransition === 'function' && !prefersReducedMotion)` so Safari/Firefox versions or reduced-motion users execute the DOM update instantaneously with zero error!

## 6. Decision Matrix & Trade-Offs

| Optimization | Impact | Complexity | Watch-Out |
| :--- | :---: | :---: | :--- |
| **`fetchpriority="high"` on Hero `<img>`** | Huge LCP win (`-300..900ms`) | Trivial | Apply strictly to 1–2 above-the-fold hero assets |
| **`width`/`height` + `aspect-ratio` everywhere** | Eliminates CLS | Trivial | Never omit on dynamically loaded media |
| **`content-visibility: auto` on below-fold** | Huge render & INP win | Low | Always pair with `contain-intrinsic-size` so scrollbars don't jump! |
| **`yieldToMainThread()` chunking** | Fixes INP stalls | Low | Better yet: move heavy filtering/sorting to server/Web Worker |

## 7. Real Production Scenario
An e-commerce storefront scored `LCP = 4.9s`, `CLS = 0.31`, `INP = 420ms` on 4G Android devices. Profiling revealed three simple platform bugs: the hero carousel had `loading="lazy"` without dimensions, clicking a category checkbox ran synchronous sorting over 4,000 items on the main thread, and 60 product cards rendered offscreen eagerly. Removing `loading="lazy"` + adding `fetchpriority="high"` + explicit `width/height`, adding `content-visibility: auto; contain-intrinsic-size: auto 340px`, and chunking filter transforms with `yieldToMainThread()` improved real field telemetry to `LCP = 1.9s`, `CLS = 0.02`, `INP = 95ms`.

## 8. Failure Modes & Edge Cases
- **WRONG:** Adding `loading="lazy"` to EVERY `<img>` component globally (including the above-the-fold hero banner — delays LCP until layout & JS finish!).
  **RIGHT:** Above-the-fold hero gets eager load + `fetchpriority="high"`; below-the-fold gallery images get `loading="lazy"`.
- **WRONG:** Claiming `"LCP 1.4s / CLS 0.00 / INP 60ms PASS"` from reading code without actually running Lighthouse, Chrome DevTools Performance, or Playwright CDP telemetry (`antislop-ui` R-36 / R-40)!
  **RIGHT:** Mark CWV measurements `NOT_RUN` unless genuinely measured in a browser or RUM dataset!

## 9. Testing & Verification
- Measure real lab `LCP`, `CLS`, and `INP` via Chrome DevTools Performance trace (4x CPU throttling + Fast 4G) or Playwright CDP `PerformanceObserver` (`/shadow-browser`).
- Coordinate search-ranking CrUX field diagnostics with `/shadow-seo` (`shadow-seo/references/07-core-web-vitals-and-page-experience.md`).

## 10. Operational Considerations
- Monitor real-user field CWV via `web-vitals` library (`onLCP`, `onINP`, `onCLS`) shipped to `/shadow-analytics` or `/shadow-observe` because lab runs on fast developer laptops hide slow mid-tier mobile Android INP bottlenecks!

## 11. Authoritative References
- Google web.dev — *Optimize LCP (`fetchpriority`), Optimize INP (`scheduler.yield`), Optimize CLS (`content-visibility`)*.
- `modern-web-guidance/references/react-nextjs-performance.md` (local React/Next.js waterfall & bundle guide).

## 12. Limitations & When NOT to Use
- Do NOT put `content-visibility: auto` on the above-the-fold hero section or on elements needing immediate anchor-scroll measurements without `contain-intrinsic-size`.
- Do NOT use `modern-web-guidance` for backend API latency or SQL profiling — route backend bottlenecks to `/shadow-perf` or `/shadow-db`.
