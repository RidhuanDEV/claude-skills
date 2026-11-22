# 03 — Graceful Degradation, Stale Fallbacks & Feature Kill-Switches

## 1. Purpose & Activation Conditions
Architect applications so partial failures of non-critical dependencies (Redis cache outage, SMTP/WhatsApp gateway downtime, recommendation/search service lag, or third-party enrichment failure) degrade smoothly into a **bounded, honest, usable experience** instead of returning blanket `500 Internal Server Error` pages. Activate when hardening critical user journeys, designing fallback tiers, or implementing emergency feature kill-switches.

## 2. Prerequisites
- Dependency map classifying every subsystem as **Hard Dependency** (cannot complete core invariant without it, e.g., primary ledger DB for payment commit) vs **Soft/Degradable Dependency** (Redis cache, email/WhatsApp dispatch, personalized recommendations, avatar CDN, analytics).

## 3. Technical Principles & Constraints
- **Explicit Degradation Matrix (No Unhandled Cascade):** Every soft dependency MUST declare its exact fallback behavior before production launch:
  1. **Redis Cache Down:** Bound Redis command timeout (`50–150ms`), trip circuit breaker, bypass Redis to PostgreSQL for **Tier 0** requests (with strict DB concurrency bulkhead!), serve bounded in-process stale L1 snapshot tagged `degraded: true` for read-heavy catalogs, and shed non-essential analytics queries.
  2. **SMTP / WhatsApp / Push Gateway Down:** NEVER block synchronous checkout/registration HTTP handlers waiting on email/WA delivery! Commit the authoritative DB row + insert an `outbox_events` row in the same SQL transaction (`/shadow-concurrency`), return `200`/`201` immediately, and let async workers retry with backoff once the gateway recovers.
  3. **Search / Recommendation / AI Assistant Down:** Fall back to deterministic SQL prefix/category browsing or curated popular catalog items, and hide/disable optional AI widgets cleanly via kill-switch while checkout continues 100% uninterrupted!
  4. **Primary DB Read-Only Maintenance / Failover:** Serve static/cached public catalog (`stale-if-error=3600`) and render an honest, accessible maintenance banner (`503 Retry-After`) on mutating actions while preserving user-typed form drafts in `sessionStorage` so users don't lose work!
- **Never Fake Financial or Security Success:** Graceful degradation applies strictly to **optional/read/deferrable** capabilities — NEVER silently accept an unverified auth token ("fail-open" security breach!) or fake a confirmed payment when the payment ledger is unreachable! Security and money MUST **fail-closed**!
- **Pre-Wired Runtime Feature Kill-Switches:** Non-critical high-cost features (live search autocomplete, AI summaries, real-time recommendation carousels, heavy PDF previews) should be toggleable via fast cached runtime flags (with safe local default if the flag provider itself is unreachable!) so ops can shed 40% DB load in 5 seconds during an incident without redeploying code.

## 4. Architecture & Implementation

### Dependency Degradation Blueprint Matrix

| Dependency Outage | Fragile Behavior (Bad) | Resilient Degradation (`/shadow-resilience`) | Fail-Closed or Degrade? |
| :--- | :--- | :--- | :--- |
| **Redis Cache Down** | Every route throws `500 ECONNREFUSED` | Fast timeout (`100ms`) + circuit open -> bypass to bulkheaded DB or serve L1 stale snapshot | **Degrade** (keep auth & checkout alive) |
| **SMTP / WhatsApp API Down** | Registration / order approval hangs 60s -> `500` | Commit DB TX + `outbox_events`; async worker retries when gateway recovers | **Degrade** (defer notification cleanly) |
| **Recommendations / Search Down** | Entire product page crashes `500` | Omit recommendation carousel or render curated fallback; SQL category listing stays live | **Degrade** (shed optional widget) |
| **JWKS / Auth IdP Unreachable** | Allow all requests through without verifying JWT | Serve cached valid JWKS within signature expiry; **REJECT** unknown/unverifiable tokens (`503`/`401`) | **FAIL-CLOSED** (zero auth bypass!) |
| **Payment Ledger DB Down** | Return `200 Paid` optimistically in RAM | Reject payment commit cleanly (`503 Retry-After`) preserving cart & `Idempotency-Key` | **FAIL-CLOSED** (zero phantom money!) |

```ts
// Strict TypeScript Stale-If-Error Fallback Wrapper with Explicit Degraded Signal (0 any, 0 casts)
export interface FallbackResult<T> {
  readonly data: T
  readonly source: 'fresh' | 'stale_fallback' | 'static_default'
  readonly degraded: boolean
  readonly reason?: string
}

export async function resolveWithGracefulFallback<T>(opts: {
  readonly fetchFresh: () => Promise<T>
  readonly readStaleSnapshot: () => Promise<T | undefined>
  readonly staticDefault?: T
  readonly onDegraded: (reason: string) => void
}): Promise<FallbackResult<T>> {
  try {
    const fresh = await opts.fetchFresh()
    return { data: fresh, source: 'fresh', degraded: false }
  } catch (err: unknown) {
    const reason = err instanceof Error ? err.message : 'dependency_unavailable'
    opts.onDegraded(reason)
    const stale = await opts.readStaleSnapshot().catch(() => undefined)
    if (stale !== undefined) {
      return { data: stale, source: 'stale_fallback', degraded: true, reason }
    }
    if (opts.staticDefault !== undefined) {
      return { data: opts.staticDefault, source: 'static_default', degraded: true, reason }
    }
    throw err
  }
}
```

## 5. Platform/Vendor Variations
- **CDN Edge `stale-if-error=3600` (`shadow-cache`):** Cloudflare, Fastly, and Varnish automatically serve the last cached public HTML/JSON for up to 1 hour if origin returns `500`/`502`/`503`/`504` — one header turns an origin outage into zero visible disruption for public browsing!
- **Feature Flag Providers (Unleash / LaunchDarkly / OpenFeature / DB-backed):** Always configure a local in-memory fallback snapshot + hardcoded safe code defaults so a flag-service outage never disables checkout or crashes boot.
- **UI Graceful Partial Rendering (React Error Boundaries):** Wrap non-critical dashboard cards (recommendations, activity feeds, AI chat sidebar) in isolated Error Boundaries so one crashed widget displays a compact retry card instead of unmounting the whole page into a blank white screen!

## 6. Decision Matrix & Trade-Offs

| Degradation Tactic | Implementation Cost | User Experience During Outage | Consistency Risk |
| :--- | :--- | :--- | :--- |
| **Transactional Outbox for Notifications** | Low | Seamless (`201` immediate, email arrives later) | Zero (durable delivery) |
| **Stale-If-Error Read Fallback** | Low | Smooth (read-only browsing continues) | Slightly stale prices/views (re-verified at checkout!) |
| **Kill-Switch Shedding Tier-2 Features** | Low | Core workflow fast; optional widgets hidden | Zero |
| **Fail-Open Auth / Payment** | **FORBIDDEN** | Catastrophic security/financial breach | **UNACCEPTABLE** |

## 7. Real Production Scenario
During a Ramadan traffic surge, a third-party WhatsApp OTP/receipt API suffered 45 minutes of `504 Gateway Timeout`. Because order confirmation called the WhatsApp API synchronously inside `POST /api/v1/orders`, checkout conversion dropped to `0%` and DB connections hit 100% waiting on 30-second HTTP timeouts. Refactoring notifications to write `outbox_events` in the order DB transaction + adding a runtime kill-switch for the non-critical "Related Products" recommendation engine kept checkout conversion at `99.8%` during the next gateway outage while 18,000 queued WhatsApp receipts drained automatically 20 minutes later.

## 8. Failure Modes & Edge Cases
- **WRONG:** Falling back from a crashed Redis cluster directly to PostgreSQL for 100% of traffic **without** a DB bulkhead or load shedding (instantly kills PostgreSQL too — turning a cache blip into a total DB meltdown!).
  **RIGHT:** Pair Redis bypass with a strict DB concurrency bulkhead (`02`) and shed Tier-2 read traffic (`503 Retry-After`) or serve bounded L1 stale cache.
- **WRONG:** Silently serving a `stale_fallback` catalog price without re-verifying the authoritative DB price during checkout submission.
  **RIGHT:** Tag stale reads honestly (`degraded: true`) and ALWAYS re-validate authoritative prices, stock, and permissions against the primary datastore on write/checkout!
- **WRONG:** Failing open on authentication/RBAC checks when Redis session store or IdP times out.
  **RIGHT:** Security and authorization ALWAYS fail-closed (`401`/`503`).

## 9. Testing & Verification
- Add integration tests injecting `ECONNREFUSED` on Redis and `504` on SMTP/WhatsApp stubs: verify core endpoints stay `200`/`201`, outbox rows persist cleanly, and auth routes fail-closed (`503`/`401`) when token verification cannot be established.
- Verify frontend Error Boundaries isolate widget failures in `/shadow-browser` fault-injection checks.

## 10. Operational Considerations
- Alert ops whenever `degraded: true` fallback rates stay elevated `> 5 minutes` (`/shadow-observe`) — graceful degradation buys calm recovery time, it must NEVER become silently permanent!
- Document every runtime kill-switch in the incident runbook with exact toggle commands and expected blast radius.

## 11. Authoritative References
- AWS Builders' Library — *Static Stability Using Availability Zones* & *Avoiding Fallback in Distributed Systems* (note: test your fallback path continuously so it actually works during an outage!).
- RFC 5861 — `stale-if-error` HTTP Resilience Extension.

## 12. Limitations & When NOT to Use
- **Untested Fallbacks Often Fail Worse:** Avoid complex rarely-executed fallback code paths that require massive extra DB load; prefer static stability (pre-computed defaults, `stale-if-error`, async outbox, simple widget hiding).
- Do NOT use graceful degradation to hide data corruption or bypass compliance/audit logging requirements (`/shadow-sec`, `/shadow-privacy`).
