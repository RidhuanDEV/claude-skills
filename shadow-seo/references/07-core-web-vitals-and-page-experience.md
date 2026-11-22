# 07 — Core Web Vitals & Page Experience (`CORE`)

## 1. Purpose & Activation Conditions
Load when diagnosing Search Console Core Web Vitals failures (`LCP`, `INP`, `CLS`), bridging lab Lighthouse vs CrUX 28-day field data, or instrumenting Real User Monitoring (RUM) for organic templates.

## 2. Prerequisites
Module `03` (rendering architecture) and `/modern-web-guidance` (frontend/RSC/image implementation patterns).

## 3. Technical Principles & Constraints
- **Field Data (CrUX p75) Governs Search:** Google evaluates Core Web Vitals using real Chrome users over a **rolling 28-day window at the 75th percentile (p75)**, split by Mobile vs Desktop — synthetic laptop Lighthouse scores do NOT dictate Search Console status.
- **Official Good Thresholds (p75):**
  - **LCP (Largest Contentful Paint):** `<= 2.5s` (*Poor* `> 4.0s`) — decompose into **TTFB + Resource Load Delay + Resource Load Duration + Element Render Delay**.
  - **INP (Interaction to Next Paint — replaced FID):** `<= 200ms` (*Poor* `> 500ms`) — decompose into **Input Delay + Processing Duration + Presentation Delay**.
  - **CLS (Cumulative Layout Shift):** `<= 0.1` (*Poor* `> 0.25`) — driven by unsized media, late banners/ads, and webfont swap shifts.

## 4. Architecture & Implementation
```ts
export interface WebVitalSample {
  readonly metric: "LCP" | "INP" | "CLS";
  readonly value: number;
  readonly routeTemplate: string; // e.g., "/id/produk/[slug]" (low cardinality!)
  readonly deviceClass: "mobile" | "desktop";
}

export function classifyCoreWebVital(sample: WebVitalSample): "GOOD" | "NEEDS_IMPROVEMENT" | "POOR" {
  if (sample.metric === "LCP") return sample.value <= 2500 ? "GOOD" : sample.value <= 4000 ? "NEEDS_IMPROVEMENT" : "POOR";
  if (sample.metric === "INP") return sample.value <= 200 ? "GOOD" : sample.value <= 500 ? "NEEDS_IMPROVEMENT" : "POOR";
  return sample.value <= 0.1 ? "GOOD" : sample.value <= 0.25 ? "NEEDS_IMPROVEMENT" : "POOR";
}
```
Pair with the official `web-vitals` RUM library (`onLCP`, `onINP`, `onCLS` + attribution build) to capture the exact offending DOM selector (`lcp.attribution.element`, `inp.attribution.interactionTarget`) per route template.

## 5. Platform / Vendor Variations
- **Mobile 4G / Mid-Tier Android Reality:** Indonesian organic traffic is heavily mobile; profile INP & LCP under `4x CPU slowdown` + throttled 4G rather than desktop M-series laptops.
- **Implementation Hand-Off:** Delegate React waterfall elimination, barrel import removal, `<img fetchpriority="high">`, and `content-visibility: auto` execution to `/modern-web-guidance` (`react-nextjs-performance.md`).

## 6. Decision Matrix & Trade-Offs
| Bottleneck Sub-Part | Root Cause Signal | Primary Fix |
| :--- | :--- | :--- |
| LCP — High **TTFB** (`> 800ms`) | Slow origin SSR / uncached DB query | Edge CDN caching (`s-maxage`), ISR, parallel `Promise.all` |
| LCP — **Resource Load Delay** | Hero image discovered late via CSS/JS or `loading="lazy"` | Inline `<img fetchpriority="high">` in SSR HTML; NEVER lazy-load LCP hero |
| INP — High **Processing / Input Delay** | Heavy hydration, synchronous click handlers, 3rd-party tag bloat | Defer third-party scripts, code-split heavy widgets, yield with `scheduler.yield()` |
| CLS — Unexpected Layout Shift | Images/ads/banners injected without reserved box | Explicit `width`/`height` or `aspect-ratio`, fixed-height ad slots, `font-display: swap` + `size-adjust` |

## 7. Real Production Scenario
A news portal scored 92 in desktop Lighthouse yet failed Search Console mobile CWV (`LCP 3.9s`, `CLS 0.28`). RUM attribution exposed (1) hero image had `loading="lazy"` + client JS swap, and (2) top ad slot expanded dynamically from `0px` to `250px`. Removing `loading="lazy"`, adding `fetchpriority="high"`, and reserving `min-height: 250px` dropped mobile p75 LCP to `2.1s` and CLS to `0.03` over the next 28-day CrUX cycle.

## 8. Failure Modes & Edge Cases (`WRONG` vs `RIGHT`)
- **WRONG:** Reporting "CWV fixed!" immediately after a laptop Lighthouse run or sending raw URLs with query strings to RUM metrics (high-cardinality explosion).
  **RIGHT:** Track p75 RUM segmented by `routeTemplate` + `deviceClass` and verify CrUX recovery across the 28-day rolling window.
- **WRONG:** Adding `loading="lazy"` globally to every `<Image>` component including the above-the-fold hero.
  **RIGHT:** Apply `fetchpriority="high"` + eager loading to the single hero LCP element and `loading="lazy"` strictly below the fold.

## 9. Testing & Verification
Inspect PageSpeed Insights (both CrUX Field + Lab sections), capture `web-vitals` RUM attribution p75 per route template, and verify `0` layout shifts during Playwright throttled loads (`/shadow-browser`).

## 10. Operational Considerations
Alert when p75 mobile LCP exceeds `2.5s`, INP exceeds `200ms`, or CLS exceeds `0.1` for 48 consecutive hours on high-traffic organic templates — catching third-party marketing script regressions early.

## 11. Authoritative References
- Google Search Central — *Understanding Core Web Vitals and Google Search Results*; web.dev — *Optimize LCP / INP / CLS* (`web.dev/articles/vitals`).

## 12. Limitations & When NOT to Use
Passing Core Web Vitals does NOT override weak content relevance or broken indexation; treat CWV as a hygiene & conversion multiplier, not a substitute for search intent alignment.
