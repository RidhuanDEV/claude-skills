# 04 — Crawl Budget & Indexation Engineering (`ADVANCED`)

## 1. Purpose & Activation Conditions
Load when managing medium-to-large sites (`> 10,000` URLs or frequent daily updates), diagnosing *"Crawled - currently not indexed"* / *"Discovered - currently not indexed"*, building sharded XML sitemaps, or analyzing server bot logs.

## 2. Prerequisites
Modules `01`–`03` and access to HTTP server/CDN access logs or Search Console Crawl Stats.

## 3. Technical Principles & Constraints
Google defines **Crawl Budget** as `min(Crawl Capacity Limit, Crawl Demand)`:
- **Crawl Capacity Limit:** Throttles automatically if your origin responds with slow TTFB (`> 1s`) or elevated `5xx`/`429` error rates.
- **`robots.txt` vs `noindex` Fundamental Trap:** `robots.txt` blocks **crawling**, NOT **indexing**. If a URL is blocked in `robots.txt`, Googlebot never reads `<meta name="robots" content="noindex">` on that page — and may still index the bare URL from external links!
- **XML Sitemap Hard Limits:** Max **`50,000` URLs** and **`50 MB` uncompressed** per sitemap file; larger catalogs MUST use a `<sitemapindex>` referencing sharded sub-sitemaps containing ONLY HTTP `200` canonical indexable URLs.

## 4. Architecture & Implementation
```ts
export interface SitemapEntry {
  readonly loc: string;
  readonly lastmodIso: string; // Genuine content modification timestamp (ISO-8601)
}

export function shardSitemapEntries(
  entries: readonly SitemapEntry[],
  maxUrlsPerFile = 50_000,
): readonly (readonly SitemapEntry[])[] {
  const shards: SitemapEntry[][] = [];
  for (let i = 0; i < entries.length; i += maxUrlsPerFile) {
    shards.push(entries.slice(i, i + maxUrlsPerFile));
  }
  return shards;
}

export interface BotLogLine {
  readonly path: string;
  readonly status: number;
  readonly isCanonicalTarget: boolean;
}

export function computeCrawlEfficiency(logs: readonly BotLogLine[]): {
  readonly totalHits: number;
  readonly canonical200Ratio: number;
  readonly error5xxRatio: number;
} {
  const totalHits = logs.length;
  if (totalHits === 0) return { totalHits: 0, canonical200Ratio: 0, error5xxRatio: 0 };
  const good = logs.filter((l) => l.status === 200 && l.isCanonicalTarget).length;
  const err5xx = logs.filter((l) => l.status >= 500).length;
  return {
    totalHits,
    canonical200Ratio: Number((good / totalHits).toFixed(4)),
    error5xxRatio: Number((err5xx / totalHits).toFixed(4)),
  };
}
```

## 5. Platform / Vendor Variations
- **Cloudflare / WAF Bot Fight Mode:** Verify verified `Googlebot` / `Bingbot` ASN/reverse-DNS allowlists so aggressive WAF rules never return `403`/`429` challenges to search crawlers.
- **Staging / Preview Subdomains:** Enforce HTTP `X-Robots-Tag: noindex, nofollow` (plus HTTP Basic Auth/SSO) instead of relying solely on `robots.txt`.

## 6. Decision Matrix & Trade-Offs
| Indexation Symptom | Most Likely Root Cause | Remediation |
| :--- | :--- | :--- |
| Millions of `?sort=&filter=` bot hits | Infinite faceted crawl trap | Allowlist indexable facets; block/canonicalize noisy params (Module `09`) |
| Pages stuck *"Discovered - currently not indexed"* | Crawl capacity limit (slow TTFB/`5xx`) OR low perceived uniqueness | Cut origin TTFB `< 400ms`, prune thin/duplicate URLs, improve internal linking |
| Staging URLs appearing in Google | `robots.txt` blocked crawl of `<meta noindex>` | Require Auth on staging OR allow crawl temporarily with `X-Robots-Tag: noindex` |
| High `3xx`/`404` share in bot logs (`> 15%`) | Stale internal links & sitemap URLs | Fix internal links to final canonicals; purge non-`200` URLs from sitemaps |

## 7. Real Production Scenario
A job portal had 25,000 active jobs but 600,000 expired job URLs returning `200 OK` ("Job expired — see similar jobs"). Googlebot spent 88% of crawl budget on dead pages (`canonical200Ratio = 0.12`). Switching expired jobs past 30 days to `410 Gone` and removing them from sitemaps tripled crawl speed on fresh listings within 2 weeks.

## 8. Failure Modes & Edge Cases (`WRONG` vs `RIGHT`)
- **WRONG:** Setting `lastmod` to `new Date().toISOString()` on every build or placing `Disallow: /` + `<meta noindex>` simultaneously on pages you want removed from the index.
  **RIGHT:** Emit `lastmod` strictly from real DB `content_updated_at`, and allow Googlebot to fetch `X-Robots-Tag: noindex` (or return `404`/`410`) to de-index URLs cleanly.
- **WRONG:** Blocking `/_next/static/` or `/assets/` in `robots.txt`.
  **RIGHT:** Keep JS/CSS/image bundles crawlable so WRS renders pages identically to users.

## 9. Testing & Verification
Inspect Google Search Console *Crawl Stats* + raw access logs filtered by verified `Googlebot` (`canonical200Ratio >= 0.80`, `error5xxRatio < 0.01`), validate XML sitemap well-formedness and HTTP `200` status on sampled `<loc>` URLs.

## 10. Operational Considerations
Alert SRE/SEO whenever `Googlebot` `5xx` rate exceeds `1%` over 15 minutes — prolonged `5xx` errors shrink crawl capacity rapidly and trigger de-indexing after ~24–48 hours.

## 11. Authoritative References
- Google Search Central — *Large Site Owner's Guide to Managing Your Crawl Budget*, *Build and Submit a Sitemap*, *Robots Meta Tag & X-Robots-Tag*.

## 12. Limitations & When NOT to Use
For small sites (`< 5,000` URLs) with fast TTFB (`< 300ms`) and clean URLs, crawl budget is rarely a bottleneck — prioritize content quality, internal linking, and rendering hygiene first.
