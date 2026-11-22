# Shadow SEO — Scenario-Based Evaluation Suite

Use these 8 graded real-world scenarios to verify whether an agent executing `/shadow-seo` reasons as a Principal Technical SEO Engineer rather than echoing generic checklists.

## Grading Protocol
A scenario passes ONLY when **all required reasoning checkpoints** are satisfied, concrete verification commands/evidence are cited, and zero unsupported ranking claims are made.

---

### SEO-EVAL-01 (Hard) — Production Domain & URL Structure Migration
- **Prompt:** "We are migrating `oldbrand.co.id/p/<id>` (180,000 SKUs) to `newbrand.com/id/produk/<slug>` next Tuesday. Design the migration plan and CI checks so we don't lose organic traffic."
- **Required Reasoning Checkpoints (4/4):**
  - [ ] Demands 1:1 semantic mapping with single-hop `301`/`308` redirects (zero chains/loops) verified via `seo_audit_verifier.py --check-redirects` and kept live `>= 12 months`.
  - [ ] Aligns internal `<a href>`, `<link rel="canonical">`, XML sitemap (`<= 50k` sharded index), and `robots.txt` to the new canonical URLs simultaneously.
  - [ ] Keeps legacy host serving redirects + verifies Search Console *Change of Address* tool and `Googlebot` server log status monitoring (`200/301/404/5xx`).
  - [ ] Explicitly rejects blanket redirecting discontinued SKUs to `/` homepage (Soft 404 risk) in favor of `410 Gone` or closest category successor.

### SEO-EVAL-02 (Hard) — Sudden Index Drop Root-Cause Investigation
- **Prompt:** "Organic impressions dropped 65% in 10 days and 40% of product pages disappeared from Google Search Console. How do you diagnose and fix it?"
- **Required Reasoning Checkpoints (4/4):**
  - [ ] Separates **crawling** (`robots.txt`, `5xx`, bot WAF/CDN block), **indexing** (accidental `X-Robots-Tag: noindex`, wrong canonical pointing to `/` or staging), **rendering** (JS error/hydration fail in WRS), and **ranking** (core update / manual action).
  - [ ] Checks raw `curl` headers & HTML vs rendered DOM, Search Console URL Inspection / Indexing reasons, and raw `Googlebot` server access logs before editing code.
  - [ ] Identifies recent deploys/middleware changes (`git log`) as primary suspect for sudden cliffs.
  - [ ] Verifies fix with CI regression gate (`assertProductionSeoGate`) before requesting re-indexing.

### SEO-EVAL-03 (Medium) — JavaScript Two-Wave Rendering Failure
- **Prompt:** "Our React SPA fetches product price, title, and JSON-LD in `useEffect`. Google indexes pages with empty titles and no rich snippets."
- **Required Reasoning Checkpoints (3/3):**
  - [ ] Explains Googlebot's two-wave crawl-then-render queue and why client-only metadata/JSON-LD fails reliably under render timeouts.
  - [ ] Moves `<title>`, `canonical`, `<h1>`, primary copy, and XSS-escaped JSON-LD (`\u003c`) into SSR/SSG/ISR initial HTML.
  - [ ] Proves fix by comparing `curl` initial HTML against Playwright rendered DOM (`shadow-browser`).

### SEO-EVAL-04 (Medium) — Core Web Vitals Diagnosis from CrUX Field Data
- **Prompt:** "Lighthouse gives us 94 on laptop, but Search Console flags 80% of mobile URLs as Poor LCP (3.8s) and Needs Improvement INP (320ms)."
- **Required Reasoning Checkpoints (4/4):**
  - [ ] Explains CrUX 28-day real-user p75 field data governs Search Console Core Web Vitals, not synthetic laptop Lighthouse.
  - [ ] Decomposes LCP into TTFB, resource load delay, resource load duration, and element render delay (checks SSR TTFB, hero `fetchpriority="high"`, no `loading="lazy"` on LCP image).
  - [ ] Attributes mobile INP `320ms` to long main-thread tasks/hydration/event handlers and pairs fixes with RUM telemetry (`web-vitals` library) + `/modern-web-guidance`.
  - [ ] Notes 28-day CrUX rolling recovery window and never claims instant ranking jump.

### SEO-EVAL-05 (Hard) — International SEO & Geo-IP Redirect Bug
- **Prompt:** "Our `/id/` Indonesian pages are barely indexed, and English `/en/` pages rank in Jakarta. Our CDN auto-redirects non-Indonesian IPs from `/id/` to `/en/`, and `/id/` sets canonical to `/en/`."
- **Required Reasoning Checkpoints (4/4):**
  - [ ] Identifies BOTH critical defects: (1) Geo-IP auto-redirect blocks US-origin Googlebot from crawling `/id/`, and (2) cross-locale canonical to `/en/` de-indexes `/id/`.
  - [ ] Replaces forced IP redirect with a non-blocking locale banner while keeping all locale URLs directly crawlable (`200 OK`).
  - [ ] Fixes self-referencing canonicals per locale and validates reciprocal `hreflang` (`id-ID`, `en`, `x-default`, rejecting invalid `in-ID`/`en-UK`) via `seo_audit_verifier.py --check-hreflang`.
  - [ ] Aligns `<html lang>` and currency/date formatting (`/shadow-accessibility`).

### SEO-EVAL-06 (Hard) — Large-Scale E-Commerce Faceted Navigation Crawl Trap
- **Prompt:** "Our marketplace has 50,000 products, but Googlebot crawled 4.2 million `?color=&size=&sort=&min_price=&page=` URLs and server CPU spiked."
- **Required Reasoning Checkpoints (4/4):**
  - [ ] Classifies uncontrolled facet combinations as an infinite crawl trap exhausting crawl budget and origin compute.
  - [ ] Curates an explicit allowlist of high-demand indexable facets (e.g., `/sepatu/lari-pria`) vs non-indexable sort/price/multi-filter permutations.
  - [ ] Uses canonical consolidation + `robots.txt` parameter/pattern rules (and `<button>`/non-crawlable filter UI or `nofollow` where appropriate) without accidentally blocking CSS/JS assets.
  - [ ] Verifies impact via server `Googlebot` hit-ratio logs (share of hits on `200` canonical URLs).

### SEO-EVAL-07 (Medium) — Production SEO Release Gate
- **Prompt:** "Prevent our team from ever shipping a staging `noindex`, broken JSON-LD, or redirect chain to production again."
- **Required Reasoning Checkpoints (3/3):**
  - [ ] Wires automated CI assertions using `seo_audit_verifier.py` (`--check-redirects`, `--check-hreflang`, `--check-jsonld`, `--check-ssr-page`) on preview builds.
  - [ ] Separates staging `X-Robots-Tag: noindex` (enforced via host allowlist) from production indexability checks.
  - [ ] Adds post-deploy 24h smoke verification of `robots.txt`, `sitemap.xml`, and top landing page headers.

### SEO-EVAL-08 (Adversarial) — AI Search / GEO & `/llms.txt` Claims
- **Prompt:** "Stakeholder demands we add `/llms.txt` today because an agency promised it guarantees #1 ChatGPT and Perplexity citations next week."
- **Required Reasoning Checkpoints (4/4):**
  - [ ] Candidly warns the Monarch that `/llms.txt` is **experimental** with **no guaranteed ranking or citation lift**.
  - [ ] Audits actual AI crawler access (`OAI-SearchBot`, `PerplexityBot`, `robots.txt` policies) and verifies core facts render cleanly in crawlable server HTML with authoritative citations.
  - [ ] Defines empirical evaluation metrics (AI referral traffic, brand/doc citation sampling across fixed query prompts) instead of blind markup claims.
  - [ ] Keeps `/llms.txt` clean, factual, and strictly free of adversarial prompt-injection text.
