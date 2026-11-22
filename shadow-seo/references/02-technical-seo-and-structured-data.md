# 02 — Technical SEO & Structured Data (`CORE`)

## 1. Purpose & Activation Conditions
Load when implementing HTML `<head>` metadata (`<title>`, meta description, OpenGraph/Twitter), `Schema.org` JSON-LD structured data, rich-result eligibility, or preventing JSON-LD XSS injection.

## 2. Prerequisites
Module `01` (canonical URLs) and server-side HTML rendering awareness.

## 3. Technical Principles & Constraints
- **Visible Parity Policy (Google Structured Data Guidelines):** Structured data MUST describe content actually visible on the rendered page. Marking up hidden reviews, fake ratings, or unrendered FAQs violates spam policy and risks manual action.
- **XSS Breakout Hazard:** Putting unescaped `JSON.stringify(obj)` inside `<script type="application/ld+json">` lets a user-supplied string containing `</script><script>...` execute arbitrary JavaScript. Always escape `<`, `>`, `&`, `U+2028`, `U+2029`.
- **Linked `@graph` Entities:** Connect `Organization`, `WebSite`, `WebPage`, `BreadcrumbList`, and `Product`/`Article` via stable `@id` URIs so search engines build one coherent entity graph.

## 4. Architecture & Implementation
```ts
export function serializeSafeJsonLd(payload: Readonly<Record<string, unknown>>): string {
  return JSON.stringify(payload)
    .replace(/</g, "\\u003c")
    .replace(/>/g, "\\u003e")
    .replace(/&/g, "\\u0026")
    .replace(/\u2028/g, "\\u2028")
    .replace(/\u2029/g, "\\u2029");
}

export interface ProductGraphInput {
  readonly url: string;
  readonly orgName: string;
  readonly orgUrl: string;
  readonly name: string;
  readonly description: string;
  readonly sku: string;
  readonly imageUrl: string;
  readonly priceIdr: number;
  readonly availability: "InStock" | "OutOfStock" | "PreOrder";
}

export function buildProductGraphJsonLd(input: ProductGraphInput): string {
  return serializeSafeJsonLd({
    "@context": "https://schema.org",
    "@graph": [
      { "@type": "Organization", "@id": `${input.orgUrl}#org`, name: input.orgName, url: input.orgUrl },
      {
        "@type": "WebPage",
        "@id": `${input.url}#webpage`,
        url: input.url,
        name: input.name,
        publisher: { "@id": `${input.orgUrl}#org` },
        mainEntity: { "@id": `${input.url}#product` },
      },
      {
        "@type": "Product",
        "@id": `${input.url}#product`,
        name: input.name,
        description: input.description,
        sku: input.sku,
        image: [input.imageUrl],
        offers: {
          "@type": "Offer",
          url: input.url,
          priceCurrency: "IDR",
          price: input.priceIdr,
          availability: `https://schema.org/${input.availability}`,
        },
      },
    ],
  });
}
```

## 5. Platform / Vendor Variations
- **Next.js App Router:** Use `generateMetadata()` for `<title>`, `description`, `alternates.canonical`, and `openGraph`; render `<script type="application/ld+json">` inside the Server Component with `serializeSafeJsonLd`.
- **Social Cards (OG/Twitter):** Pair metadata tags (`og:image` absolute `https://`, `1200x630`, `<= 250 KB`) with `/shadow-illustration` for deterministic Satori/Sharp image generation.

## 6. Decision Matrix & Trade-Offs
| Page Type | Primary Schema.org Types | Key Mandatory Fields |
| :--- | :--- | :--- |
| Product Detail | `Product` + `Offer` (+ `MerchantReturnPolicy`) | `name`, `image`, `offers.price`, `priceCurrency`, `availability` |
| Editorial / Docs Article | `Article` / `TechArticle` + `BreadcrumbList` | `headline`, `datePublished`, `dateModified`, `author.name`, `image` |
| Homepage / Brand | `Organization` + `WebSite` | `name`, `url`, `logo`, `sameAs` |
| Local Branch / Clinic | `LocalBusiness` | `name`, `address`, `geo`, `openingHoursSpecification`, `telephone` |

## 7. Real Production Scenario
An e-commerce marketplace rendered raw `JSON.stringify(product)` in SSR templates; a merchant entered `"</script><img src=x onerror=...>"` in a SKU title, causing stored XSS across product pages. Replacing raw serialization with `serializeSafeJsonLd` + CI verifier (`seo_audit_verifier.py --check-jsonld`) eliminated the vulnerability permanently.

## 8. Failure Modes & Edge Cases (`WRONG` vs `RIGHT`)
- **WRONG:** Duplicating identical `<title>` and `<meta description>` across 500 category pages or injecting `AggregateRating` markup when no visible reviews exist on the page.
  **RIGHT:** Generate unique, intent-specific titles (`50–60` chars) and emit `AggregateRating` strictly from verified visible reviews.
- **WRONG:** Using Microdata scattered across brittle DOM templates or relative `og:image="/og.png"` paths.
  **RIGHT:** Use JSON-LD `@graph` cleanly decoupled from CSS/DOM layout and absolute `https://` URLs for every image/canonical.

## 9. Testing & Verification
Run `python shadow-seo/scripts/seo_audit_verifier.py --check-jsonld payload.json`, verify Schema.org syntax in Google Rich Results Test / Schema Markup Validator, and inspect rendered social previews.

## 10. Operational Considerations
Monitor Google Search Console *Enhancements / Structured Data* reports weekly after template releases so broken `priceCurrency` or missing `image` regressions are caught immediately.

## 11. Authoritative References
- Google Search Central — *Intro to Structured Data*, *General Structured Data Guidelines*; Schema.org Vocabulary.

## 12. Limitations & When NOT to Use
Valid structured data enables *eligibility* for rich results; it never guarantees Google will display rich snippets (Google decides dynamically based on query intent and site trust).
