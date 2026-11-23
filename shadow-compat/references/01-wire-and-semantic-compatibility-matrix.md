# 01 — Wire & Semantic Backward-Compatibility Matrix & Rolling Skew Survival

## 1. Purpose & Activation Conditions
Prevent silent breakage of mobile apps, partner webhooks, event consumers, and coexisting `N-1` servers when evolving APIs, schemas, and payloads — catching **both syntactic wire breaks AND hidden semantic regressions** (default flips, sort order shifts, `null` vs omitted semantics, strict enum exhaustiveness). Activate whenever modifying any existing HTTP API, GraphQL/gRPC schema, webhook payload, or async event DTO.

## 2. Prerequisites
- Authoritative API/event contract from the owning service (`/shadow-api`) and an inventory of active consumers by version, owner, and reachability (mobile app binaries, partner integrations, web SPAs, async workers).

## 3. Technical Principles & Constraints
- **Three Formal Compatibility Modes & Mandatory Deployment Order:**
  1. **Backward Compatible (New Reader Reads Old Data):** Adding an optional field with a safe reader default or relaxing validation. **Safe deploy order:** deploy **Consumer/Reader first**, then Producer.
  2. **Forward Compatible (Old Reader Ignores New Data):** Adding an optional response field while older tolerant readers ignore unknown keys (ZERO `additionalProperties: false` tightening on shared DTOs!). **Safe deploy order:** deploy **Producer first**, then Consumer.
  3. **Full Compatible (Simultaneous Bidirectional Skew):** Only adding/removing fields that BOTH old and new versions default safely -> survives rolling deploys & rollbacks in either order!
- **Syntactic Clean != Semantically Compatible!** Even when an OpenAPI schema diff prints `0 breaking changes`, these **6 Semantic Breaking Changes** crash real consumers:
  1. Changing default list sort order (`created_at DESC -> ASC`) or pagination cursor encoding (`test_consumer_replay.py`).
  2. Flipping a response property from omitted (`undefined`) to explicit `null` (or `null` -> omitted) when mobile Swift/Kotlin/Go decoders distinguish presence vs `null`!
  3. Changing default boolean/numeric behavior when an optional request parameter is omitted.
  4. Adding a **new enum value** in a response when older mobile apps switch exhaustively without an `UNKNOWN` fallback branch!
  5. Remapping error codes (`404 -> 403` or `INVALID_COUPON -> COUPON_EXPIRED`) that clients branch on programmatically.
  6. Lowering maximum pagination `limit` caps (e.g., `max=500 -> max=100` causing `400` on existing batch clients!).
- **Expand-Contract Dual-Write / Dual-Read Rule:** Never rename or retype a live field in-place — emit BOTH old and new fields during the deprecation window, verify telemetry shows legacy callers drained to `0`, and remove only after `Sunset` (`02`).

## 4. Architecture & Implementation

### Wire & Semantic Evolution Classification Table

| Change Type | Classification | Safe Evolution Rule |
| :--- | :--- | :--- |
| Adding an **optional** request field (with identical default) or **new** optional response field | **Non-Breaking (Additive)** | Safe in `MINOR` (`v1.x`) once verified consumers tolerate extra response fields |
| Adding a **required** request field | **BREAKING** | Make optional with safe server default, OR introduce `/api/v2/...` |
| Removing or renaming a response field | **BREAKING** | Dual-emit both old & new fields during RFC 9745/8594 sunset window |
| Mutating field type (`number -> string`, `object -> array`) | **BREAKING** | Never mutate in place; add sibling field or bump major `/v2` |
| Making a previously non-nullable response field `nullable` | **BREAKING** | Crashes Kotlin/Swift/TS non-null decoders; provide default or bump `/v2` |
| Adding a new **response enum** value | **Potentially Breaking** | Audit mobile/partner decoders for default/unknown fallback before emitting |
| Changing default sort order, cursor format, or error `code` | **SEMANTIC BREAK** | Keep default behavior on `v1`; opt-in via explicit query param or `/v2` |

```ts
// Strict TypeScript Tolerant Reader & Unknown-Enum Fallback Pattern (0 any, 0 casts)
export type KnownOrderStatus = 'PENDING' | 'PAID' | 'SHIPPED' | 'CANCELLED'
export type SafeOrderStatus = KnownOrderStatus | 'UNKNOWN_FUTURE_STATUS'

const KNOWN_STATUSES: ReadonlySet<string> = new Set(['PENDING', 'PAID', 'SHIPPED', 'CANCELLED'])

export function parseTolerantOrderStatus(raw: unknown): SafeOrderStatus {
  if (typeof raw === 'string' && KNOWN_STATUSES.has(raw)) {
    switch (raw) {
      case 'PENDING': return 'PENDING'
      case 'PAID': return 'PAID'
      case 'SHIPPED': return 'SHIPPED'
      case 'CANCELLED': return 'CANCELLED'
    }
  }
  return 'UNKNOWN_FUTURE_STATUS'
}
```

## 5. Platform/Vendor Variations
- **Protobuf / gRPC (`buf breaking`):** NEVER reuse deleted numeric field tags (`reserved 4, 5;`) — reusing tag `4` with a different wire type silently corrupts deserialization across old clients!
- **GraphQL:** Never delete or change argument/field nullability directly; annotate fields with `@deprecated(reason: "Use totalMinor; sunsets 2026-12-31")` and track field usage telemetry before removal.
- **Mobile Clients (Android/iOS/Flutter):** Unlike web SPAs refreshed on reload, `10–30%` of mobile users remain on `N-2` / `N-3` versions for 6+ months — maintain explicit minimum-supported-app-version telemetry alongside API versions (`/shadow-mobile`).

## 6. Decision Matrix & Trade-Offs

| Scenario | Right Choice | Why |
| :--- | :--- | :--- |
| **Adding metadata field to `/v1/orders`** | Additive optional field | Zero client churn; check strict decoders first |
| **Renaming `total` -> `totalMinor`** | Dual-emit `total` + `totalMinor` + deprecation headers | Protects mobile & external webhook consumers |
| **Restructuring core payload & auth semantics** | New major route `/api/v2/...` | Clean break without corrupting `/v1` traffic |

## 7. Real Production Scenario
A backend team cleaned up `/api/v1/invoices` by renaming `total_price` to `totalMinor` and adding `additionalProperties: false` to incoming request schemas. Web worked because frontend deployed simultaneously, yet 4 B2B partner ERP integrations and 18,000 un-updated iOS devices immediately broke with `400` and blank totals! Reverting to dual-emission (`total_price` + `totalMinor`), dropping `additionalProperties: false` on existing endpoints, and gating PRs with `compat_deprecation_verifier.py` restored partners within 15 minutes and gave them a clean 90-day RFC 9745/8594 migration window.

## 8. Failure Modes & Edge Cases
- **WRONG:** Assuming "our own frontend is the only caller" without checking mobile apps, cron scripts, partner webhooks, or analytics ETL readers.
  **RIGHT:** Inventory ALL consumers by version, owner, and reachability before altering any contract.
- **WRONG:** Reusing a deleted enum value or status string for a different business meaning later.
  **RIGHT:** Retire old enum symbols permanently and introduce new distinct identifiers.

## 9. Testing & Verification
- Run `python shadow-compat/scripts/compat_deprecation_verifier.py --check-compat diff.json` in CI to catch field removal, type flips, nullability regressions, new required inputs, and strict schema tightening.
- Run `python -m unittest discover -s shadow-compat/tests -v` (`test_consumer_replay.py` + `test_compat_deprecation_verifier.py`).

## 10. Operational Considerations
- Pair semantic compatibility checks with `/shadow-test` (`04-contract-and-boundary-compatibility-testing.md`) and `/shadow-api` `compare_openapi_drift`.

## 11. Authoritative References
- Martin Fowler — *Tolerant Reader* & *Expand-Contract Pattern*.
- OpenAPI `oasdiff` Breaking Rules & Protobuf `buf breaking` Wire Compatibility Guide.

## 12. Limitations & When NOT to Use
- Do NOT freeze internal private helper functions inside a single unexposed module under public API compatibility ceremony — reserve full Expand-Contract & versioning for externally consumed APIs, shared events, and persisted schemas.
