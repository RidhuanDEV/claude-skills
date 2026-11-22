# 05 — International SEO & Multi-Locale Architecture (`ADVANCED`)

## 1. Purpose & Activation Conditions
Load when designing or debugging multi-language/multi-region websites (`id-ID`, `en`, `en-SG`, `ms-MY`), validating reciprocal `hreflang` clusters, or resolving wrong-country pages ranking in regional search results.

## 2. Prerequisites
Modules `01`–`04` and `/shadow-accessibility` (`04-i18n-rtl-and-cognitive-accessibility.md`).

## 3. Technical Principles & Constraints
- **Reciprocity Invariant:** Every page in an `hreflang` cluster MUST reference itself AND every sibling locale, AND every sibling MUST link back, plus an `x-default` fallback. One missing return link breaks reciprocity.
- **Self-Canonical Invariant:** `/id/harga` MUST canonicalize to `/id/harga` (NEVER to `/en/pricing`). Cross-locale canonicalization tells Google to drop the localized URL from the index.
- **Valid BCP-47 / ISO Codes Only:** Use ISO 639-1 language (`id`, `en`) + optional ISO 3166-1 Alpha-2 region (`id-ID`, `en-GB`). Invalid codes like `en-UK` or `in-ID` are silently ignored.
- **No Geo-IP Auto-Redirects:** Googlebot predominantly crawls from US IPs; forcing IP-based `302` redirects away from `/id/` prevents indexing of Indonesian pages.

## 4. Architecture & Implementation
```ts
export interface LocaleAlternate {
  readonly hreflang: string; // e.g., "id-ID", "en", "x-default"
  readonly href: string;     // Absolute https:// canonical URL
}

export function buildHreflangLinkHeader(alternates: readonly LocaleAlternate[]): string {
  // Useful for non-HTML localized assets (PDF manuals, brochures)
  return alternates.map((a) => `<${a.href}>; rel="alternate"; hreflang="${a.hreflang}"`).join(", ");
}
```
Validate full clusters deterministically in CI using `python shadow-seo/scripts/seo_audit_verifier.py --check-hreflang cluster.json`.

## 5. Platform / Vendor Variations
- **HTML `<head>` `<link rel="alternate">`:** Best for `<= 10` locales (simple SSR testability).
- **XML Sitemap `<xhtml:link>`:** Best for `> 10` regional/language variants to avoid bloating HTML `<head>` bytes on every page.
- **Next.js / Cloudflare Workers:** Detect `Accept-Language` strictly to display a non-blocking dismissible locale banner — never return `302` redirecting crawlers away from requested locale paths.

## 6. Decision Matrix & Trade-Offs
| URL Topology | Authority Consolidation | Ops Complexity | Pick When |
| :--- | :---: | :---: | :--- |
| **Subdirectories (`/id/`, `/en/`)** *(Default)* | Highest (single host) | Lowest | Most SaaS, docs, e-commerce expanding regionally |
| **Subdomains (`id.example.com`)** | Medium | Medium | Separate regional stacks/hosting teams |
| **ccTLDs (`example.co.id`, `example.sg`)** | Split per domain | Highest (separate DNS/SEO) | Distinct local legal entities with strong regional brand equity |

## 7. Real Production Scenario
An Indonesian fintech launched `/en/` alongside `/id/` and deployed Cloudflare IP geolocation redirecting US visitors from `/id/` to `/en/`. Within 3 weeks, 70% of `/id/` pages dropped from Google Indonesia because US-origin Googlebot was redirected to `/en/`. Replacing the IP redirect with a client-side suggestion banner + reciprocal `hreflang` restored `/id/` visibility cleanly.

## 8. Failure Modes & Edge Cases (`WRONG` vs `RIGHT`)
- **WRONG:** Using `hreflang="in-ID"` or `hreflang="en-UK"`, omitting self-referencing `hreflang`, or canonicalizing `/id/` to `/en/`.
  **RIGHT:** Validate BCP-47 codes (`id-ID`, `en-GB`), self-canonicalize every locale, and verify reciprocity via `seo_audit_verifier.py --check-hreflang`.
- **WRONG:** Serving different languages at the exact same URL based solely on cookies or `Accept-Language` headers.
  **RIGHT:** Give every locale its own distinct, crawlable canonical URL.

## 9. Testing & Verification
Run `python shadow-seo/scripts/seo_audit_verifier.py --check-hreflang cluster.json`, test `curl` from a US IP/User-Agent against `/id/` confirming HTTP `200` (zero forced redirect), and verify `<html lang>` matches page language.

## 10. Operational Considerations
Whenever a localized page is temporarily unpublished (`404`/`410`) or marked `noindex`, remove it from ALL sibling pages' `hreflang` lists simultaneously so no live page points `hreflang` to a dead URL.

## 11. Authoritative References
- Google Search Central — *Managing Multi-Regional and Multilingual Sites*; IETF BCP 47 (RFC 5646).

## 12. Limitations & When NOT to Use
Do not auto-generate thin machine-translated pages across 20 languages merely to chase international traffic — unedited machine translations degrade sitewide quality signals.
