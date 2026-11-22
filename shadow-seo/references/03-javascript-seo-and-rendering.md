# 03 — JavaScript SEO & Rendering Architecture (`CORE`)

## 1. Purpose & Activation Conditions
Load when diagnosing empty/partial indexing on React/Vue/Angular SPAs, choosing between CSR/SSR/SSG/ISR/Streaming SSR, or auditing hydration parity for search crawlers.

## 2. Prerequisites
Modules `01`–`02` and familiarity with React/Next.js/Nuxt/Astro rendering modes.

## 3. Technical Principles & Constraints
- **Googlebot Web Rendering Service (WRS) Two-Wave Indexing:** Googlebot first crawls raw HTML (`Wave 1`) and later queues JavaScript execution in a headless evergreen Chromium renderer (`Wave 2`). Under heavy load, Wave 2 can lag hours/days or drop slow/failing async API calls.
- **Stateless Crawler Constraints:** Googlebot WRS does NOT preserve cookies/localStorage across page loads, does NOT click UI tabs/accordions to load hidden AJAX content, and ignores URL hash fragments (`#/products/123`).
- **Hydration Parity:** If SSR renders one `<title>`/`canonical`/`<h1>` and client hydration mutates it to another (or swaps content to an error boundary), search engines receive contradictory indexing signals.

## 4. Architecture & Implementation
```ts
// CI Hydration Parity Check: verify raw SSR HTML already carries core SEO signals
export interface ParitySnapshot {
  readonly rawTitle: string;
  readonly renderedTitle: string;
  readonly rawCanonical: string;
  readonly renderedCanonical: string;
  readonly rawWordCount: number;
  readonly renderedWordCount: number;
}

export function detectJsRenderingDependency(snap: ParitySnapshot): readonly string[] {
  const warnings: string[] = [];
  if (!snap.rawTitle || snap.rawTitle !== snap.renderedTitle) {
    warnings.push(`TITLE_HYDRATION_DRIFT: raw='${snap.rawTitle}' vs rendered='${snap.renderedTitle}'`);
  }
  if (!snap.rawCanonical || snap.rawCanonical !== snap.renderedCanonical) {
    warnings.push(`CANONICAL_HYDRATION_DRIFT: raw='${snap.rawCanonical}' vs rendered='${snap.renderedCanonical}'`);
  }
  if (snap.renderedWordCount > 0 && snap.rawWordCount / snap.renderedWordCount < 0.7) {
    warnings.push("HIGH_JS_CONTENT_DEPENDENCY: >30% of primary body copy absent from initial SSR HTML");
  }
  return warnings;
}
```

## 5. Platform / Vendor Variations
- **Next.js / Nuxt / SvelteKit / Astro:** Default public SEO pages to Server Components (SSR/SSG/ISR); avoid wrapping critical copy or links inside `"use client"` `useEffect` fetchers.
- **Legacy React Vite SPA (when full SSR migration is deferred):** Pre-render static marketing/landing routes at build time or migrate high-value organic templates incrementally via Strangler Fig (`/shadow-modernize`); note Google officially treats legacy "dynamic rendering" (user-agent cloaking middleware) strictly as a temporary workaround, NOT a long-term architecture.

## 6. Decision Matrix & Trade-Offs
| Rendering Mode | TTFB & Crawl Reliability | Best Fit |
| :--- | :--- | :--- |
| **SSG (Static)** | Fastest TTFB; 100% HTML in Wave 1 | Docs, blogs, marketing pages (`< 10k` pages) |
| **ISR / On-Demand Revalidate** | Fast cached HTML + fresh inventory/prices | Large catalogs (`10k–500k` SKUs), news portals |
| **Full SSR (+ Edge Cache)** | Always fresh; higher origin CPU cost | Real-time pricing, search-indexable dynamic directories |
| **Streaming SSR (`<Suspense>`)** | Fast hero; ensure `<head>` metadata resolves BEFORE stream flush | Complex dashboards / product pages with slow secondary widgets |
| **Pure CSR (SPA)** | Weakest SEO (Wave 2 risk, slow LCP, empty social OG tags) | Authenticated private apps (`noindex`) ONLY |

## 7. Real Production Scenario
A Vue SPA loaded product descriptions and `canonical` tags via `/api/products/:id` after mount; social shares showed blank previews and 35% of SKUs stayed "Discovered - currently not indexed". Moving route data fetching to Nuxt SSR with Redis/CDN caching raised indexed SKUs from 65% to 98% within 4 weeks.

## 8. Failure Modes & Edge Cases (`WRONG` vs `RIGHT`)
- **WRONG:** Lazy-loading below-the-fold images via JS scroll listeners (`onScroll`) without native `<img loading="lazy">` or keeping critical text inside `if (typeof window !== "undefined")` branches.
  **RIGHT:** Use native `<img loading="lazy" src="...">` for offscreen images (never for hero LCP!), and render primary copy, links, and metadata in server HTML.
- **WRONG:** Returning HTTP `200 OK` with `<div id="root">Loading...</div>` when an API returns `404` on client fetch (creates massive Soft 404s!).
  **RIGHT:** Resolve missing entities on the server and return a genuine HTTP `404` or `410` status code.

## 9. Testing & Verification
Compare raw `curl -s https://staging.../page` against Playwright rendered DOM (`shadow-browser`), run `detectJsRenderingDependency`, and inspect Google Search Console *URL Inspection -> View Tested Page -> Screenshot & HTML*.

## 10. Operational Considerations
Watch CDN cache headers (`Cache-Control: public, s-maxage=300, stale-while-revalidate=3600`) on SSR pages so Googlebot bursts do not overwhelm origin databases.

## 11. Authoritative References
- Google Search Central — *Understand the JavaScript SEO Basics*, *Fix Search-Related JavaScript Problems*, *Lazy-Loading Content*.

## 12. Limitations & When NOT to Use
Do not force SSR onto authenticated user-only dashboards or internal admin panels where search indexing is unwanted and CSR simplifies state management.
