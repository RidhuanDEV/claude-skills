---
name: shadow-seo
description: "Use when checking crawl/indexing, hreflang, canonical URLs, JSON-LD, sitemaps, CrUX, or search visibility."
---

# Shadow SEO (`/shadow-seo`) — Technical SEO Engineering & Organic Growth

Use this skill whenever the **Monarch** plans, implements, audits, migrates, diagnoses, or governs search visibility for public web applications, docs portals, blogs, or e-commerce catalogs.

## 1. Core Engineering Principles & Non-Negotiables

1. **5-Stage Funnel Discipline:** Diagnose and build across **Discovery -> Crawling -> Rendering -> Indexing -> Ranking**; never optimize downstream copy/markup while upstream crawling, rendering, or canonical signals are broken.
2. **Crawlable HTML & Signal Unanimity:** Render `<title>`, `meta description`, `<h1>`, primary copy, `<a href>` links, and XSS-escaped JSON-LD (`<` -> `\u003c`) in initial SSR/SSG/ISR HTML. Keep edge redirects, internal links, XML sitemaps, and self-referencing `<link rel="canonical">` 100% aligned.
3. **Environment & International Isolation:** Enforce `X-Robots-Tag: noindex, nofollow` on non-production hosts via runtime hostname allowlists (never hardcoded in merged templates). Never force Geo-IP auto-redirects on bots, and always validate reciprocal BCP-47 `hreflang` clusters.
4. **Honest Evidence & Experimental Tagging:** Measure Core Web Vitals against 28-day **CrUX field p75** (not laptop Lighthouse alone). Treat **`/llms.txt`** and GEO tactics explicitly as **experimental** with empirical citation/referral measurement — never promise guaranteed ranking or AI citation lifts.
5. **Cross-Skill Boundaries:** Delegate React/CSS/bundle performance implementation to `/modern-web-guidance`, `1200x630` OG artwork rendering to `/shadow-illustration`, browser DOM/CWV capture to `/shadow-browser`, and referral/funnel tracking to `/shadow-analytics`.

## 2. Deterministic Verification CLI & Scenario Benchmarks

Run offline checks (`L0`/`L1`) before claiming `VERIFIED-LOCAL`:
```powershell
python "shadow-seo/scripts/seo_audit_verifier.py" --self-test
python "shadow-seo/scripts/seo_audit_verifier.py" --check-redirects path/to/redirects.json
python "shadow-seo/scripts/seo_audit_verifier.py" --check-hreflang path/to/hreflang.json
python "shadow-seo/scripts/seo_audit_verifier.py" --check-jsonld path/to/jsonld.json
python "shadow-seo/scripts/seo_audit_verifier.py" --check-ssr-page path/to/page.json
```
Scenario evaluation benchmarks: [`evaluations.md`](evaluations.md) (8 graded real-world production scenarios).

## Reference Guide

Load ONLY the 1–2 modules matching the active task or incident symptom:

| Task / Symptom | Tier | Load Reference |
| :--- | :---: | :--- |
| Search architecture, canonicalization hierarchy & URL normalization | `CORE` | [01-seo-fundamentals-and-search-architecture.md](references/01-seo-fundamentals-and-search-architecture.md) |
| `<title>`/meta, XSS-safe JSON-LD `@graph` (`Schema.org`), rich results & OG tags | `CORE` | [02-technical-seo-and-structured-data.md](references/02-technical-seo-and-structured-data.md) |
| SPA/CSR vs SSR/SSG/ISR, Googlebot WRS two-wave rendering & hydration parity | `CORE` | [03-javascript-seo-and-rendering.md](references/03-javascript-seo-and-rendering.md) |
| Crawl budget, `robots.txt` vs `noindex`, sharded sitemaps (`<=50k`) & bot log efficiency | `ADVANCED` | [04-crawl-budget-and-indexation.md](references/04-crawl-budget-and-indexation.md) |
| Multi-locale URL structure, reciprocal `hreflang`, BCP-47 & anti-Geo-IP redirect | `ADVANCED` | [05-international-seo.md](references/05-international-seo.md) |
| Domain/URL/CMS migrations, single-hop `301`/`308`, Search Console Change of Address | `OPERATIONAL` | [06-seo-migration-engineering.md](references/06-seo-migration-engineering.md) |
| Core Web Vitals (`LCP`/`INP`/`CLS`), CrUX p75 field diagnosis & RUM attribution | `CORE` | [07-core-web-vitals-and-page-experience.md](references/07-core-web-vitals-and-page-experience.md) |
| Search intent, topical clusters, internal link graph, orphan pages & cannibalization | `CORE` | [08-content-and-information-architecture.md](references/08-content-and-information-architecture.md) |
| E-commerce variants, out-of-stock lifecycle, pagination & faceted crawl traps | `SPECIALIST` | [09-ecommerce-and-programmatic-seo.md](references/09-ecommerce-and-programmatic-seo.md) |
| AI search / GEO, AI crawler `robots.txt` split & experimental `/llms.txt` evaluation | `SPECIALIST` | [10-geo-and-ai-search-visibility.md](references/10-geo-and-ai-search-visibility.md) |
| Sudden index/traffic drop RCA, Search Console triage & bot log alerting | `OPERATIONAL` | [11-seo-observability-and-auditing.md](references/11-seo-observability-and-auditing.md) |
| Automated CI SEO release gates, `CODEOWNERS`, staging checks & post-deploy smoke | `OPERATIONAL` | [12-seo-testing-and-release-governance.md](references/12-seo-testing-and-release-governance.md) |

Do not load unrelated references unnecessarily.
