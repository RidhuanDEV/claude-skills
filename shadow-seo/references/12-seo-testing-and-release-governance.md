# 12 — SEO Testing & Release Governance (`OPERATIONAL`)

## 1. Purpose & Activation Conditions
Load when wiring automated SEO checks into CI/CD pipelines, building pre-launch staging checklists, or defining post-release SEO monitoring gates for public web apps.

## 2. Prerequisites
Modules `01`–`11` and `shadow-seo/scripts/seo_audit_verifier.py`.

## 3. Technical Principles & Constraints
- **Shift-Left SEO Governance:** Catching an accidental `noindex`, relative canonical, broken `hreflang`, redirect chain, or unescaped JSON-LD in a Pull Request takes **3 seconds**; recovering from it after Googlebot de-indexes your site takes **2–6 weeks**.
- **Environment Symmetry Trap:** Staging MUST emit `X-Robots-Tag: noindex, nofollow`, while Production MUST NOT — enforce this strictly from an explicit production hostname allowlist, never hard-coded inside template files that get merged between branches.

## 4. Architecture & Implementation
### Automated CI SEO Gate Commands (`L1_SAFE_VERIFICATION`)
```powershell
# Run deterministic offline SEO verifier checks in CI before merge
python "shadow-seo/scripts/seo_audit_verifier.py" --self-test
python "shadow-seo/scripts/seo_audit_verifier.py" --check-redirects config/redirects.json
python "shadow-seo/scripts/seo_audit_verifier.py" --check-hreflang artifacts/hreflang-cluster.json
python "shadow-seo/scripts/seo_audit_verifier.py" --check-jsonld artifacts/product-jsonld.json
python "shadow-seo/scripts/seo_audit_verifier.py" --check-ssr-page artifacts/home-ssr-audit.json
```

### Pre-Launch & Post-Release Governance Checklist
1. **PR / CI Gate (Blocking):** Zero redirect chains/loops; valid reciprocal `hreflang`; XSS-safe valid JSON-LD; SSR raw HTML carries `<title>`, `canonical`, `<h1>`, and core body text; `robots.txt` diff reviewed explicitly.
2. **Staging Gate:** Confirm `X-Robots-Tag: noindex, nofollow` active on staging host AND zero leaked staging domains inside rendered `canonical` or `sitemap.xml` URLs.
3. **Post-Deploy Smoke (`T+5m`, `T+24h`, `T+7d`):** Confirm production `robots.txt` allows crawling, `sitemap.xml` returns `200` with production HTTPS URLs, top 10 organic landing pages return `200` with `0` `noindex`, and `Googlebot` `5xx` rate stays `< 0.5%`.

## 5. Platform / Vendor Variations
- **GitHub Actions / GitLab CI:** Require `CODEOWNERS` approval on `robots.txt`, `redirects.*`, `sitemap.*`, and `next.config.*` so routine feature PRs cannot silently alter crawl directives.
- **Playwright Integration (`/shadow-browser`):** Extract initial `curl`/fetch HTML vs Playwright DOM on key templates in staging E2E runs to enforce hydration parity automatically.

## 6. Decision Matrix & Trade-Offs
| Release Risk Tier | Required SEO Gate | Blocking? |
| :--- | :--- | :---: |
| Copy / CSS tweak (no routing/meta change) | Fast `seo_audit_verifier.py` JSON-LD & SSR smoke | Advisory / Fast CI |
| Template, metadata, i18n, or pagination change | Full SSR parity + `hreflang` + `canonical` + JSON-LD gate | **Blocking CI** |
| URL restructure, replatforming, or domain move | Full redirect map gate + staging dress rehearsal + 90-day monitor (Module `06`) | **Blocking CI + Release Sign-Off** |

## 7. Real Production Scenario
A CMS plugin update silently replaced `robots.txt` with `Disallow: /` during a Friday deploy. Adding a GitHub `CODEOWNERS` lock on `robots.txt` + a 15-minute synthetic check verifying `robots.txt` never disallows `/` on production prevented recurrence completely.

## 8. Failure Modes & Edge Cases (`WRONG` vs `RIGHT`)
- **WRONG:** Committing `<meta name="robots" content="noindex">` inside `layout.tsx` during staging testing and merging it into `main`.
  **RIGHT:** Drive `X-Robots-Tag: noindex` solely via runtime hostname allowlist (`enforcePreviewNoIndex`) and fail CI if production build emits `noindex`.
- **WRONG:** Running aggressive live crawlers (Screaming Frog at 50 threads) against production without `L3` approval (can DoS origin!).
  **RIGHT:** Keep CI checks bounded to representative template fixtures (`L1`), and request explicit `L3` approval before high-concurrency sitewide crawls.

## 9. Testing & Verification
Run `python -m unittest discover -s shadow-seo/tests` and verify every scenario in [`evaluations.md`](../evaluations.md) passes after skill or template updates.

## 10. Operational Considerations
Pair SEO release gates with `/shadow-release` `< 2 min` post-deploy smoke checks so SEO regressions trigger immediate rollback alongside HTTP `5xx` checks.

## 11. Authoritative References
- Google Search Central — *Launching a New Site Checklist*; `shadow-seo/scripts/seo_audit_verifier.py`.

## 12. Limitations & When NOT to Use
CI SEO gates verify deterministic technical invariants (headers, tags, links, JSON-LD, redirects) — they cannot predict search engine ranking algorithms or judge editorial depth, which require human and Search Console evaluation.
