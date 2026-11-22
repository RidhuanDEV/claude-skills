# 01 — SEO Fundamentals & Search Architecture (`CORE`)

## 1. Purpose & Activation Conditions
Load when framing organic search requirements, explaining why pages fail to get discovered/indexed/ranked, or designing greenfield URL and site architecture.

## 2. Prerequisites
Understanding of HTTP status codes (`200/301/308/404/410/503`), HTML semantics, DNS/HTTPS, and basic server-rendered vs client-rendered web delivery.

## 3. Technical Principles & Constraints
Search engines operate a 5-stage funnel: **Discovery -> Crawling -> Rendering -> Indexing -> Ranking**. A breakdown at stage `k` makes optimizations at stage `k+1` invisible:
- **Canonicalization Hierarchy:** Google treats `<link rel="canonical">` as a **strong hint**, NOT a directive; it resolves canonicals by reconciling redirects (`301`/`308`), internal `<a href>` links, XML sitemaps, HTTPS preference, and `rel="canonical"`.
- **Single-URL Authority:** Every distinct piece of content needs one stable, lowercase, hyphenated canonical URL (`https://example.com/id/produk/rack-42u`) free of session IDs or tracking query strings.

## 4. Architecture & Implementation
```ts
export interface CanonicalUrlPolicy {
  readonly origin: string; // e.g., "https://example.com"
  readonly trailingSlash: boolean;
  readonly stripParams: ReadonlySet<string>;
}

export function normalizeCanonicalUrl(rawPathAndQuery: string, policy: CanonicalUrlPolicy): string {
  const url = new URL(rawPathAndQuery, policy.origin);
  for (const key of [...url.searchParams.keys()]) {
    if (policy.stripParams.has(key.toLowerCase()) || key.toLowerCase().startsWith("utm_")) {
      url.searchParams.delete(key);
    }
  }
  let pathname = url.pathname.replace(/\/{2,}/g, "/");
  if (pathname !== "/") {
    pathname = policy.trailingSlash ? (pathname.endsWith("/") ? pathname : `${pathname}/`) : pathname.replace(/\/+$/, "");
  }
  url.pathname = pathname;
  url.hash = "";
  return url.toString();
}
```

## 5. Platform / Vendor Variations
- **Next.js App Router:** Configure `metadataBase` in root `layout.tsx` and `trailingSlash` consistently in `next.config.*` so relative alternates resolve to exact production HTTPS canonicals.
- **Nginx / Cloudflare Edge:** Enforce single-hop HTTP->HTTPS + `www` vs apex canonical redirect at the edge BEFORE requests hit origin SSR.

## 6. Decision Matrix & Trade-Offs
| Signal / Requirement | Mechanism | Strength & Trade-Off |
| :--- | :--- | :--- |
| Duplicate host (`http://`, `www.`) | Edge `301`/`308` redirect | Hard directive; preserves link equity cleanly |
| Tracking params (`?utm_*`, `?fbclid`) | Self-referencing `<link rel="canonical">` | Keeps analytics intact while consolidating index |
| Private/Admin/Staging routes | Auth gate + `X-Robots-Tag: noindex` | Prevents index leakage (stronger than `robots.txt`) |
| Discontinued URL with no replacement | `410 Gone` / `404` | Releases crawl budget cleanly; avoids Soft 404 |

## 7. Real Production Scenario
A SaaS site served both `https://example.com/pricing` and `https://www.example.com/pricing/` with `200 OK` and relative canonicals. Search Console split impressions across 4 URL variants. Enforcing one edge `308` to apex without trailing slash + absolute canonicals consolidated signals within 3 weeks.

## 8. Failure Modes & Edge Cases (`WRONG` vs `RIGHT`)
- **WRONG:** Conflicting signals (sitemap lists `/produk/`, internal links point to `/produk`, canonical points to `/en/products`).
  **RIGHT:** Unify edge redirects, internal `<a href>`, XML sitemap, and `<link rel="canonical">` onto the exact same absolute URL string.
- **WRONG:** Blocking CSS/JS in `robots.txt` or hiding navigation links behind `<div onClick={() => router.push(...)}>`.
  **RIGHT:** Allow crawler access to rendering assets and use semantic `<a href="...">` elements for all crawlable navigation.

## 9. Testing & Verification
Inspect raw `curl -I` redirect chains (must be `<= 1` hop to `200`), verify `<link rel="canonical">` in initial HTML, and run `python shadow-seo/scripts/seo_audit_verifier.py --check-ssr-page page.json`.

## 10. Operational Considerations
Treat URL architecture as a long-term public API contract; changing URL patterns after launch requires permanent redirects (`>= 12 months`) and risks temporary ranking volatility.

## 11. Authoritative References
- Google Search Central — *How Google Search Works*, *Consolidate Duplicate URLs* (`developers.google.com/search/docs`).

## 12. Limitations & When NOT to Use
Do not apply public SEO indexing work to authenticated B2B back-office dashboards or private customer portals — those MUST enforce authentication + `X-Robots-Tag: noindex, nofollow`.
