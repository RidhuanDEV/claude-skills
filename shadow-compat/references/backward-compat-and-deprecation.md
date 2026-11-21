# Backward Compatibility, RFC 9745/8594 Deprecation & Evolution Playbook

> Use this playbook when evolving APIs, webhooks, schemas, or dependencies without breaking existing consumers, implementing RFC 9745 `Deprecation` + RFC 8594 `Sunset` headers, or building consumer-driven compatibility checks.

## 1. Core Concepts
Compatibility failures rarely look like syntax errors—they happen silently when field defaults flip, `null` vs omitted semantics shift, sort keys change, or strict JSON decoders reject unannounced fields:
- **Rolling Skew Survival:** During deploys, old and new producers/consumers run concurrently (`N` and `N-1`). Schema and API changes MUST support both simultaneously via additive fields or Expand-Contract adapters.
- **Standardized Retirement Signaling:** Use **RFC 9745 (`Deprecation: @<unix_sec>`, March 2025)** paired with **RFC 8594 (`Sunset: <IMF-fixdate>`, May 2019)** and `Link` headers so clients parse machine-readable sunset timelines rather than scraping changelog prose.

## 2. Technical Rules & Decision Matrix

| Evolution Need | Pattern to Pick | Rollout Order & Constraints |
| :--- | :--- | :--- |
| Adding non-required response metadata | **Additive Optional Field** (Forward Compatible) | Deploy Producer first; confirm consumers use tolerant decoders |
| Renaming/retyping field or column in use | **Expand-Contract Dual-Write / Dual-Read** | Populate both -> backfill -> migrate callers -> verify telemetry `0` -> drop legacy |
| Incompatible semantics or auth contract | **URI Major Version (`/v2/...`) + RFC 9745/8594 Headers** | Keep `/v1` active through `Sunset`; emit `@unix` `Deprecation` + IMF-fixdate `Sunset` |
| Unreachable external/partner webhook clients | **Sanitized Historical Payload Replay + Decoder Capture** | Capture real client decoder strictness; clearly report what replay cannot measure |

## 3. Implementation Examples

### Strict-TS RFC 9745 (`Deprecation`) + RFC 8594 (`Sunset`) Middleware & `410 Gone`
```ts
export interface DeprecationPolicy {
  readonly deprecatedSince: Date;
  readonly sunsetAt: Date; // MUST be >= deprecatedSince per RFC 8594
  readonly successorUrl: string;
  readonly docsUrl: string;
  readonly enforceGoneAfterSunset: boolean;
}

export interface HttpResponseLike {
  status(code: number): HttpResponseLike;
  setHeader(name: string, value: string): void;
  json(body: Readonly<Record<string, unknown>>): void;
}

export function applyDeprecationMiddleware(
  policy: DeprecationPolicy,
  now: Date = new Date(),
): (res: HttpResponseLike, next: () => void) => void {
  if (policy.sunsetAt.getTime() < policy.deprecatedSince.getTime()) {
    throw new RangeError("INVALID_SUNSET: Sunset MUST NOT precede Deprecation (RFC 8594)");
  }
  const depUnix = Math.floor(policy.deprecatedSince.getTime() / 1000);
  const sunsetImf = policy.sunsetAt.toUTCString(); // Valid IMF-fixdate in GMT

  return (res: HttpResponseLike, next: () => void): void => {
    res.setHeader("Deprecation", `@${depUnix}`);
    res.setHeader("Sunset", sunsetImf);
    res.setHeader(
      "Link",
      `<${policy.successorUrl}>; rel="alternate", <${policy.docsUrl}>; rel="deprecation"`,
    );

    if (policy.enforceGoneAfterSunset && now.getTime() >= policy.sunsetAt.getTime()) {
      res.status(410).json({
        type: policy.docsUrl,
        title: "Endpoint Retired",
        status: 410,
        detail: `This resource reached sunset at ${sunsetImf}. Migrate to ${policy.successorUrl}.`,
      });
      return;
    }
    next();
  };
}
```

## 4. Best Practices
- Audit **semantic regressions** beyond OpenAPI diffs: check pagination sort order stability, default boolean flips, currency rounding rules, enum exhaustion on old clients, and HTTP error code consistency.
- Check downstream runtime `engines` and peer dependencies before upgrading packages; pin exact versions in lockfiles and production manifests.
- Run `python -m unittest discover -s tests` inside `shadow-compat` whenever testing strict decoders or omitted cursors.

## 5. Anti-Patterns (`WRONG` vs `RIGHT`)
- **WRONG (Draft header syntax or premature removal):** Emitting `Deprecation: true`, formatting `Sunset` earlier than `Deprecation`, or returning `404 Not Found` on a newly deleted legacy route.
  **RIGHT:** Emit RFC 9745 `Deprecation: @<unix_timestamp>`, RFC 8594 `Sunset: <IMF-fixdate>`, migration `Link` headers, and `410 Gone` once sunset expires and telemetry confirms legacy traffic is drained.
- **WRONG (Breaking tolerant readers with strict schema tightening):** Adding `additionalProperties: false` to a shared response DTO consumed by older clients, or reusing a deleted enum string for a new meaning.
  **RIGHT:** Keep responses additive and backwards-compatible; introduce `/v2` when breaking contract semantics is unavoidable.

## 6. Production Considerations
- **Telemetry Drain Gate:** Instrument a metric (`legacy_route_hits{route, consumer_id}`) before scheduling removal so contract owners see exact lagging integrators prior to enabling `410 Gone`.
- **Replay Integrity:** When replaying sanitized historical payloads against candidate upgrades, treat `replay_only` honestly as partial evidence when strict client decoders or retries are unrepresented.
