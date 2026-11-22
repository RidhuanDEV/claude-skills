# 06 — SEO Migration Engineering (`OPERATIONAL`)

## 1. Purpose & Activation Conditions
Load before executing any domain rename, protocol change (`HTTP -> HTTPS`), CMS/framework replatforming, site consolidation, or URL-slug restructure on a live site with organic traffic.

## 2. Prerequisites
Modules `01`–`05` and access to current crawl exports, Google Search Console, analytics landing-page revenue data, and backlink profiles.

## 3. Technical Principles & Constraints
- **Single-Hop Permanent Redirect Invariant:** Every legacy URL MUST resolve in **exactly 1 hop** (`301` or `308`) to its closest semantic equivalent on the destination host. Zero redirect chains (`A -> B -> C`) and zero loops.
- **Full Signal Alignment:** Redirects alone are insufficient — internal links, `<link rel="canonical">`, `hreflang`, XML sitemaps, and `robots.txt` MUST all point directly to the new URLs on launch day.
- **Retention Window:** Keep legacy domain DNS, TLS certificates, and redirect rules active for **at least 12 months** (indefinitely if backlink equity is material).

## 4. Architecture & Implementation
### Migration Phases & Automated Gate
1. **Pre-Migration Baseline (`T-14d`):** Export top 100% indexed URLs, top organic traffic/revenue landing pages, top backlink targets, and current `<title>`/JSON-LD snapshots.
2. **1:1 Redirect Map & CI Verification (`T-7d`):** Validate complete map offline with `python shadow-seo/scripts/seo_audit_verifier.py --check-redirects redirects.json` (must report `0` chains, `0` loops, `0` invalid paths).
3. **Staging Dress Rehearsal (`T-3d`):** Test redirect rules against staging host (protected with `X-Robots-Tag: noindex` + Auth); verify HTTP `200` final destinations and SSR parity.
4. **Launch Cutover (`T0`):** Deploy redirects + new canonicals + new sharded sitemaps; lift `noindex` ONLY on production host; submit **Change of Address** in Google Search Console (for domain moves); keep old sitemap submitted temporarily to accelerate redirect discovery.
5. **Post-Launch Monitoring (`T+1h` to `T+90d`):** Watch `Googlebot` logs (`404`/`5xx` spikes), Search Console indexing transition, and top-50 landing page organic clicks daily.

```nginx
# O(1) Edge/Nginx single-hop permanent redirect map (scales to 100k+ legacy URLs cleanly)
map $uri $legacy_redirect_target {
    default "";
    /old-products/widget-a  https://new.example.com/products/widget-a;
    /blog/2024/launch-post  https://new.example.com/articles/launch-post;
}

server {
    listen 443 ssl http2;
    server_name legacy.example.com;
    if ($legacy_redirect_target != "") {
        return 301 $legacy_redirect_target;
    }
    return 410;
}
```

## 5. Platform / Vendor Variations
- **Edge Redirects (Cloudflare Bulk Redirects / Nginx `map` / AWS CloudFront Functions):** Always execute large redirect tables (`10k–500k` rules) at the edge/Nginx `map` (O(1) hash lookup) rather than slow regex loops inside app middleware.
- **Next.js `redirects()`:** Suitable for `< 1,000` static rules; offload massive SKU maps to edge KV or reverse proxy.

## 6. Decision Matrix & Trade-Offs
| Legacy URL State | Target Action | Rationale |
| :--- | :--- | :--- |
| Exact or close semantic equivalent exists | `301`/`308` direct single-hop redirect | Transfers ranking & backlink equity cleanly |
| Product discontinued, category still exists | `301` to parent category OR keep `200` out-of-stock with alternatives | Preserves UX and category relevance |
| Permanently deleted thin/spam URL with no match | `410 Gone` (or `404`) | Avoids Soft 404 penalty from homepage redirects |
| Simultaneous Domain + Complete Redesign | **Split into 2 separate launches (`>= 60d` apart)** | Isolates root cause if traffic dips |

## 7. Real Production Scenario
A B2B site moved domains AND redesigned templates simultaneously while accidentally leaving `302` redirects and old `canonical` tags pointing to the legacy domain. Traffic dropped 52%. Switching `302 -> 301`, fixing self-canonicals to the new domain, and updating internal links recovered 95% of organic traffic over 6 weeks.

## 8. Failure Modes & Edge Cases (`WRONG` vs `RIGHT`)
- **WRONG:** Redirecting all 20,000 unmapped legacy URLs indiscriminately to `/` homepage, or letting the old domain's SSL certificate expire 30 days after launch (breaks HTTPS redirects!).
  **RIGHT:** Map all revenue/backlink URLs 1:1, return `410` for truly obsolete pages, and keep legacy TLS + `301` active `>= 12 months`.
- **WRONG:** Changing domain, URL taxonomy, and page copy all on the same day.
  **RIGHT:** Separate infrastructure/domain moves from content/IA overhauls whenever business timelines allow.

## 9. Testing & Verification
Run `seo_audit_verifier.py --check-redirects redirects.json`, run bounded HTTP smoke checks sampling top 100 legacy URLs post-launch (assert `301`/`308` -> single hop -> `200` + matching `canonical`), and monitor `Googlebot` status logs.

## 10. Operational Considerations
Prepare a documented **rollback trigger** before cutover (e.g., `> 2%` `5xx` on canonical URLs or broken checkout/SSR on launch) and keep legacy DNS/origin warm for at least 72 hours.

## 11. Authoritative References
- Google Search Central — *Site Moves and Changes*, *Redirects and Google Search*, *Change of Address Tool*.

## 12. Limitations & When NOT to Use
Even flawlessly executed domain migrations commonly experience 2–6 weeks of temporary ranking fluctuation while Google re-crawls and transfers signals; warn stakeholders upfront with realistic timelines.
