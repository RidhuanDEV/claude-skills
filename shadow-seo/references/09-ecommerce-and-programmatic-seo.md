# 09 — E-Commerce & Programmatic SEO (`SPECIALIST`)

## 1. Purpose & Activation Conditions
Load when engineering large product catalogs, SKU color/size variants, out-of-stock lifecycles, faceted navigation filters, pagination, or template-driven programmatic landing pages.

## 2. Prerequisites
Modules `02`, `04`, and `08` (structured data, crawl budget, information architecture).

## 3. Technical Principles & Constraints
- **Faceted Navigation Combinatorial Explosion:** `10 categories × 20 brands × 15 colors × 10 sizes × 5 sorts = 150,000+` URLs from only `1,000` products. Without strict indexation rules, facets destroy crawl budget and create massive thin-duplicate content.
- **Programmatic SEO Quality Bar:** Template-generated pages (e.g., `/jasa-kirim/jakarta-ke-surabaya`) MUST carry **unique, genuinely useful structured data, pricing/SLA differences, or local proof** — swapping only a city name in boilerplate copy violates Google's *Scaled Content Abuse* spam policy.
- **Pagination Self-Canonical Rule:** Page 2 (`/kategori?page=2`) MUST canonicalize to **itself** (`?page=2`), NEVER to Page 1 (`?page=1`) — canonicalizing Page 2..N to Page 1 causes crawlers to drop products listed only on deeper pages!

## 4. Architecture & Implementation
```ts
export interface FacetPolicy {
  readonly indexableFacetKeys: ReadonlySet<string>; // e.g., new Set(["brand", "subcategory"])
  readonly maxIndexableFacets: number;              // typically 1 or 2
  readonly minMatchingProducts: number;             // e.g., >= 3 items to justify indexing
}

export function decideFacetDirectives(
  activeFacets: Readonly<Record<string, string>>,
  productCount: number,
  baseCategoryUrl: string,
  currentUrl: string,
  policy: FacetPolicy,
): { readonly indexable: boolean; readonly canonical: string; readonly robots: string } {
  const keys = Object.keys(activeFacets);
  const allAllowed = keys.every((k) => policy.indexableFacetKeys.has(k));
  const indexable = keys.length <= policy.maxIndexableFacets && allAllowed && productCount >= policy.minMatchingProducts;
  return indexable
    ? { indexable: true, canonical: currentUrl, robots: "index, follow" }
    : { indexable: false, canonical: baseCategoryUrl, robots: "noindex, follow" };
}
```

## 5. Platform / Vendor Variations
- **Out-of-Stock Lifecycle:**
  - *Temporarily out of stock:* Keep HTTP `200`, mark `OutOfStock` in JSON-LD `Offer`, show restock ETA + in-stock alternatives.
  - *Permanently discontinued with clear successor:* `301` redirect to the successor model or parent category.
  - *Permanently removed with no successor & minimal backlinks:* Return `410 Gone` so Google drops it rapidly.
- **Product Variants (`color`/`size`):** If users search specifically for variants (*"iPhone 16 Pro 256GB"*), give each variant a clean indexable URL + `ProductGroup` / `hasVariant` JSON-LD; if variants have zero distinct search demand (e.g., S/M/L shirt sizes), consolidate via canonical to the parent SKU URL.

## 6. Decision Matrix & Trade-Offs
| E-Com / Programmatic Pattern | Index / Canonical Strategy | Risk Prevented |
| :--- | :--- | :--- |
| Sort / View / Price Slider (`?sort=asc`, `?min=`) | `noindex, follow` + canonical to base + block crawl via `robots.txt` or button state | Infinite crawl trap |
| High-Demand 1-Facet Landing (`/sepatu/lari`) | Clean static path, `index, follow`, unique intro/H1/title, in sitemap | Captures commercial long-tail |
| Pagination (`?page=2..N`) | Self-referencing canonical + crawlable `<a href="?page=2">` (no infinite-scroll-only) | Keeps deep SKUs discoverable |
| Low-Inventory Facet (`productCount < 3`) | `noindex, follow`, omitted from sitemap | Prevents thin-content dilution |

## 7. Real Production Scenario
A marketplace allowed Googlebot to index 1.8 million empty/1-item multi-filter URLs while canonicalizing `?page=2..50` to `?page=1`. Result: deep SKUs vanished from Google and origin DB load spiked from bot queries. Implementing `decideFacetDirectives` (max 1 curated facet, `>= 3` SKUs), fixing pagination self-canonicals, and switching sort controls to non-crawlable state cut bot CPU by 74% and increased indexed active SKUs by 41%.

## 8. Failure Modes & Edge Cases (`WRONG` vs `RIGHT`)
- **WRONG:** Canonicalizing `?page=2` to `?page=1`, or using infinite scroll without paginated `<a href="?page=N">` links.
  **RIGHT:** Self-canonicalize each paginated page and provide crawlable pagination links alongside optional infinite scroll enhancement.
- **WRONG:** Spinning 50,000 thin programmatic city pages with identical 2-sentence templates and 0 local listings.
  **RIGHT:** Gate programmatic indexability strictly on real data uniqueness + non-zero inventory thresholds (`productCount >= minMatchingProducts`).

## 9. Testing & Verification
Unit-test `decideFacetDirectives` across allowed/disallowed/empty facets, verify paginated pages (`page=2`) self-canonicalize, and audit `Googlebot` hit-ratio on non-canonical query strings.

## 10. Operational Considerations
Sync product `availability` and `price` between visible HTML, JSON-LD `Offer`, and Google Merchant Center feed — mismatches trigger Merchant Center disapprovals.

## 11. Authoritative References
- Google Search Central — *Ecommerce SEO Best Practices*, *Product Variants Structured Data (`ProductGroup`)*, *Pagination & Incremental Page Loading*, *Spam Policies (Scaled Content Abuse)*.

## 12. Limitations & When NOT to Use
Do not use `robots.txt Disallow` alone to remove facet URLs that are ALREADY indexed (Google keeps blocked URLs indexed without snippets); de-index first with `noindex`, or let `robots.txt` prevent *new* crawl traps while canonicalizing existing ones.
