# 08 — Content & Information Architecture (`CORE`)

## 1. Purpose & Activation Conditions
Load when designing site navigation, internal link graphs, topical hub-and-spoke clusters, eliminating orphan pages, or resolving keyword cannibalization across competing URLs.

## 2. Prerequisites
Modules `01`–`02` and stakeholder product/domain taxonomy.

## 3. Technical Principles & Constraints
- **Search Intent Alignment:** Every target page maps to one clear dominant intent: **Informational** (guides/docs), **Commercial Investigation** (comparisons/categories), **Transactional** (product/pricing/signup), or **Navigational** (brand/login).
- **Crawl Depth & Internal Link Graph:** Important revenue/pillar pages should sit within `<= 3` clicks from the homepage via descriptive `<a href>` anchor text (not generic *"klik di sini"*). Pages with `0` internal inbound links (**orphan pages**) lose crawl demand and ranking signals even if listed in XML sitemaps.
- **Keyword Cannibalization:** When 2+ pages on the same domain target identical search intent, search engines split internal links, backlinks, and click signals — causing both URLs to oscillate below page 1.

## 4. Architecture & Implementation
```ts
export interface InternalLinkNode {
  readonly url: string;
  readonly outboundLinks: readonly string[];
  readonly primaryIntentKey: string;
}

export function auditInformationArchitecture(nodes: readonly InternalLinkNode[]): {
  readonly orphanUrls: readonly string[];
  readonly cannibalizedIntents: Readonly<Record<string, readonly string[]>>;
} {
  const inboundCount = new Map<string, number>(nodes.map((n) => [n.url, 0]));
  const byIntent = new Map<string, string[]>();

  for (const node of nodes) {
    byIntent.set(node.primaryIntentKey, [...(byIntent.get(node.primaryIntentKey) ?? []), node.url]);
    for (const target of node.outboundLinks) {
      if (inboundCount.has(target) && target !== node.url) {
        inboundCount.set(target, (inboundCount.get(target) ?? 0) + 1);
      }
    }
  }
  const orphanUrls = [...inboundCount.entries()].filter(([u, c]) => u !== "/" && c === 0).map(([u]) => u);
  const cannibalizedIntents: Record<string, readonly string[]> = {};
  for (const [intent, urls] of byIntent.entries()) {
    if (urls.length > 1) cannibalizedIntents[intent] = urls;
  }
  return { orphanUrls, cannibalizedIntents };
}
```

## 5. Platform / Vendor Variations
- **Breadcrumbs + Related Clusters:** Pair visible HTML breadcrumb navigation with `BreadcrumbList` JSON-LD so both users and crawlers see exact category hierarchy.
- **Docs Portals & Blogs:** Build explicit hub pages (`/panduan/pajak-umkm`) linking bi-directionally to sub-topic spokes (`/panduan/pajak-umkm/tarif-pph-final`) rather than flat chronological blog archives where older posts sink 15 pages deep.

## 6. Decision Matrix & Trade-Offs
| IA Defect | Diagnostic Signal | Resolution Strategy |
| :--- | :--- | :--- |
| **Orphan Pages** | `inboundLinks == 0` yet present in sitemap | Link from parent category/hub/related modules, OR prune/de-index if obsolete |
| **Keyword Cannibalization** | 2+ URLs swap positions in GSC for same query | Merge into 1 stronger canonical page + `301` redirect weaker URL, OR differentiate intent sharply |
| **Deep Pagination / Archive Burial** | Core pages `> 4` clicks from `/` | Add topical hub pages, HTML category index, and contextual cross-links |
| **Thin Tag/Author Archives** | 1-post tag pages indexed with duplicate excerpts | Set `noindex, follow` on low-value tag/search-result pages |

## 7. Real Production Scenario
A SaaS company published 4 separate blog posts all targeting *"aplikasi absensi online"* alongside its main landing page `/fitur/absensi`. Google rotated URLs weekly at position #11–#18. Consolidating 3 overlapping posts into one comprehensive guide linking with descriptive anchor text to `/fitur/absensi` (plus `301` redirects) lifted the landing page to Top 3.

## 8. Failure Modes & Edge Cases (`WRONG` vs `RIGHT`)
- **WRONG:** Indexing internal site search result pages (`/search?q=...`) or auto-creating thin tag pages for every keyword.
  **RIGHT:** Block/noindex internal search results (`/search`) and curate intentional, substantial hub pages.
- **WRONG:** Mega-menus stuffing 400 links into every `<header>` (dilutes link equity & hurts mobile UX/DOM size).
  **RIGHT:** Keep global navigation focused on primary hubs (`<= 30–50` links) and link deeper spokes contextually from category/hub pages.

## 9. Testing & Verification
Run `auditInformationArchitecture` over crawled internal link exports, check click depth distribution (`>= 95%` revenue pages `<= 3` clicks), and inspect Google Search Console query-to-URL mapping for cannibalization.

## 10. Operational Considerations
Review new editorial/category slugs against existing intent registry before publishing so content teams do not accidentally spawn duplicate competing landing pages.

## 11. Authoritative References
- Google Search Central — *SEO Starter Guide (Organize Your Site)*, *Link Best Practices for Google*.

## 12. Limitations & When NOT to Use
Do not force artificial keyword-stuffed anchor text or rigid silo walls when natural cross-linking genuinely helps users complete their task.
