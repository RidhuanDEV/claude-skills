# 02 — RFC 9745 `Deprecation`, RFC 8594 `Sunset`, Telemetry Drain & `410 Gone`

## 1. Purpose & Activation Conditions
Retire legacy API endpoints, fields, and webhook versions cleanly without ambushing integrators by emitting standards-compliant **RFC 9745 (`Deprecation: @<unix_sec>`)**, **RFC 8594 (`Sunset: <IMF-fixdate>`)**, machine-readable **`Link`** migration pointers, **telemetry drain monitoring**, and post-sunset **`410 Gone`** responses. Activate whenever deprecating an endpoint, planning `/v1 -> /v2` retirement, or building API lifecycle middleware.

## 2. Prerequisites
- Active successor endpoint (`/v2/...`) and published migration guide URL.
- Per-consumer observability counter (`legacy_route_hits_total{route, consumer_id}`) wired in `/shadow-observe`.

## 3. Technical Principles & Constraints
- **Exact RFC 9745 (`Deprecation`, March 2025) Syntax:**
  - MUST use Structured Field Date format **`Deprecation: @<unix_epoch_seconds>`** (e.g., `Deprecation: @1767225600`).
  - **NEVER** emit obsolete draft syntax `Deprecation: true` (rejected by RFC 9745 parsers and `compat_deprecation_verifier.py`!).
- **Exact RFC 8594 (`Sunset`, May 2019) Syntax & Ordering Invariant:**
  - MUST use HTTP **IMF-fixdate** in GMT (`Sunset: Thu, 31 Dec 2026 23:59:59 GMT`) — NEVER raw ISO `2026-12-31`!
  - **`Sunset` MUST NOT precede `Deprecation`** (`sunsetAt >= deprecatedSince`).
- **Machine-Readable `Link` Header:** Always accompany `Deprecation` + `Sunset` with `Link: <https://api.example.com/v2/orders>; rel="alternate", <https://docs.example.com/migrations/orders-v2>; rel="deprecation"` so automated SDKs and API gateways surface migration docs automatically!
- **4-Stage Retirement Lifecycle (Zero Surprise Deletions):**
  1. **Announce & Header Phase (e.g., Day 0–60):** Emit RFC 9745 + 8594 + `Link` headers on every `/v1` response; notify registered consumer owners with migration guide.
  2. **Telemetry Drain & Outreach Phase (Day 60–85):** Track `legacy_route_hits_total{route, consumer_id}`; proactively contact lagging high-volume partners before shutdown.
  3. **Brownout / Soft Warning (Optional for High-Impact Partners):** Brief scheduled 15-minute `410` brownout communicated in advance to catch silent forgotten cron jobs!
  4. **Retirement Phase (`>= Sunset`):** Return **HTTP `410 Gone`** with an RFC 9457 `application/problem+json` body pointing to the successor URL (NEVER return misleading `404 Not Found` which makes integrators think they mistyped a URL!).

## 4. Architecture & Implementation

```ts
// Strict TypeScript RFC 9745 (Deprecation) + RFC 8594 (Sunset) + 410 Gone Middleware (0 any, 0 casts)
export interface DeprecationPolicy {
  readonly deprecatedSince: Date
  readonly sunsetAt: Date // MUST be >= deprecatedSince (RFC 8594)
  readonly successorUrl: string
  readonly docsUrl: string
  readonly enforceGoneAfterSunset: boolean
}

export interface HttpResponseLike {
  status(code: number): HttpResponseLike
  setHeader(name: string, value: string): void
  json(body: Readonly<Record<string, unknown>>): void
}

export function applyRfc9745DeprecationMiddleware(
  policy: DeprecationPolicy,
  now: () => Date = () => new Date(),
): (res: HttpResponseLike, next: () => void) => void {
  if (policy.sunsetAt.getTime() < policy.deprecatedSince.getTime()) {
    throw new RangeError('INVALID_SUNSET: Sunset MUST NOT precede Deprecation (RFC 8594)')
  }
  const depUnix = Math.floor(policy.deprecatedSince.getTime() / 1000)
  const sunsetImf = policy.sunsetAt.toUTCString() // Valid IMF-fixdate in GMT

  return (res: HttpResponseLike, next: () => void): void => {
    res.setHeader('Deprecation', `@${depUnix}`)
    res.setHeader('Sunset', sunsetImf)
    res.setHeader(
      'Link',
      `<${policy.successorUrl}>; rel="alternate", <${policy.docsUrl}>; rel="deprecation"`,
    )

    if (policy.enforceGoneAfterSunset && now().getTime() >= policy.sunsetAt.getTime()) {
      res.setHeader('Content-Type', 'application/problem+json')
      res.status(410).json({
        type: policy.docsUrl,
        title: 'API Endpoint Retired',
        status: 410,
        detail: `This endpoint reached sunset on ${sunsetImf}. Migrate to ${policy.successorUrl}.`,
      })
      return
    }
    next()
  }
}
```

### Retirement Gate Readiness Table

| Stage | HTTP Status | Headers Present | Telemetry Gate |
| :--- | :---: | :--- | :--- |
| **Active Deprecated** | `200`/`201` (normal) | `Deprecation: @<unix>`, `Sunset: <IMF-fixdate>`, `Link` | Instrument `legacy_route_hits_total{consumer_id}` |
| **Pre-Sunset Verification** | `200`/`201` | Same + outreach to active `consumer_id`s | Confirm `legacy_route_hits` drained near `0` (or explicit owner waiver) |
| **Retired (`>= Sunset`)** | **`410 Gone`** | Same + RFC 9457 `application/problem+json` | Monitor `410` spikes to catch straggler scripts |

## 5. Platform/Vendor Variations
- **OpenAPI 3.1 Specs:** Mark deprecated operations/properties with `deprecated: true` AND document exact sunset date and successor operation in `description` so generated SDKs emit compile-time `@deprecated` IDE warnings automatically!
- **Reverse Proxy / API Gateway (Kong, Envoy, Nginx):** Can inject `Deprecation`, `Sunset`, and `Link` headers declaratively at the gateway tier for legacy microservices without touching frozen legacy codebases.
- **Webhook Subscriptions:** For outbound webhooks, support **per-subscription API version pinning** (`api_version: "2025-01"` vs `"2026-11"`) so partners upgrade and test v2 webhooks asynchronously at their own pace.

## 6. Decision Matrix & Trade-Offs

| Deprecation Window | Appropriate For | Risk |
| :--- | :--- | :--- |
| **30 Days** | Internal first-party web/service endpoints | Too short for mobile apps or external B2B partners |
| **90–180 Days** | Public B2B partner APIs & webhooks | Balanced ops cost vs enterprise migration cycles |
| **6–12 Months** | Native mobile APIs (slow OS/store upgrades) | Requires maintaining `/v1` adapter layer cleanly |

## 7. Real Production Scenario
An API team deleted `/api/v1/reports` 14 days after posting a Slack message, returning `404 Not Found`. Three enterprise clients' nightly ERP reconciliations broke silently for 4 days because their retry scripts treated `404` as "no report today"! Implementing RFC 9745 `Deprecation: @<unix>` + RFC 8594 `Sunset` + `Link` headers, tracking `legacy_route_hits_total{consumer_id}`, contacting remaining clients 30 days ahead, and switching to `410 Gone` (`application/problem+json`) eliminated surprise breakages on every subsequent v1 -> v2 migration.

## 8. Failure Modes & Edge Cases
- **WRONG:** Emitting `Deprecation: true` or `Sunset: 2026-12-31` (non-RFC syntax) or returning `404 Not Found` after shutting down a retired endpoint.
  **RIGHT:** Validate headers via `compat_deprecation_verifier.py` (`@<unix>`, IMF-fixdate `GMT`, `Sunset >= Deprecation`, `Link`, and `410 Gone`).
- **WRONG:** Flipping `enforceGoneAfterSunset: true` on the calendar date blindly when telemetry shows your #1 enterprise customer still sending `15,000 req/day` to `/v1`.
  **RIGHT:** Always inspect `legacy_route_hits_total` BEFORE enabling `410 Gone` and escalate unresolved high-impact consumers to the contract/product owner!

## 9. Testing & Verification
- Run `python shadow-compat/scripts/compat_deprecation_verifier.py --check-compat dep_policy.json` in CI.
- Unit-test `applyRfc9745DeprecationMiddleware` with a frozen clock before and after `sunsetAt` verifying `200` + headers before sunset and `410` + RFC 9457 JSON after sunset.

## 10. Operational Considerations
- Once `410 Gone` has run cleanly for `30–60` days with zero meaningful traffic, remove the legacy handler code in a clean follow-up release (`/shadow-refactor`, `/shadow-release`).

## 11. Authoritative References
- IETF RFC 9745 (March 2025) — *The Deprecation HTTP Response Header Field*.
- IETF RFC 8594 (May 2019) — *The Sunset HTTP Response Header Field*.
- IETF RFC 9457 — *Problem Details for HTTP APIs*.

## 12. Limitations & When NOT to Use
- Emergency security revocations (e.g., an actively exploited unauthenticated legacy endpoint) override standard 90-day sunset windows — contain immediately under `/shadow-sec` and emit `410 Gone` / `403` with emergency partner notice.
