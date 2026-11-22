# 08. Versioning, Deprecation & Contract Testing

## 1. Purpose & Activation Conditions
Evolve live production APIs (`v1 -> v2`) without breaking mobile or partner consumers — combining additive-first evolution, RFC 9745 `Deprecation` / RFC 8594 `Sunset` signaling, consumer telemetry, and automated consumer-driven contract tests. Load before modifying existing request/response shapes, deprecating routes, or planning an API version migration.

## 2. Prerequisites
- Authoritative OpenAPI baseline (`01`), telemetry segmented by `api_version` & `client_version` (`07`), and collaboration with `/shadow-compat`.

## 3. Technical Principles & Constraints
- **Additive-First Evolution Rule (Avoid Unnecessary Major Versions):**
  - **Safe (Non-Breaking):** Adding new endpoints, adding **optional** request fields with safe defaults, adding new optional response fields (consumers MUST be tolerant readers!), relaxing validation constraints.
  - **Breaking (FORBIDDEN in-place on live `v1`):** Removing/renaming paths or response fields, adding **new required** request fields, tightening validation/enum subsets, changing field data types (`integer -> string`), changing auth/error semantics.
- **RFC 9745 `Deprecation` & RFC 8594 `Sunset` Lifecycle:** When a breaking change truly requires `v2` (or sunsetting an old route):
  1. Ship `v2` side-by-side (or Expand-Contract dual fields on `v1`) while keeping `v1` 100% functional.
  2. Emit standard headers on deprecated `v1` responses:
     - `Deprecation: @<unix_timestamp>` (RFC 9745 exact Unix timestamp format, e.g., `Deprecation: @1795219200`),
     - `Sunset: <HTTP-date>` (RFC 8594 planned removal date, e.g., `Sunset: Tue, 01 Jun 2027 00:00:00 GMT`),
     - `Link: <https://docs.example.com/migrations/v1-to-v2>; rel="sunset"`.
  3. Monitor active `v1` traffic by `consumer_id` / `mobile_app_version`; notify remaining integrators proactively BEFORE the sunset date.
  4. Only decommission (`410 Gone` with RFC 9457 migration link) once active consumer volume reaches zero or contractual notice expires!
- **Automated Contract & Breaking-Diff Gates:** Run `api_contract_verifier.py --check-breaking-diff` (and `oasdiff` / `buf breaking` / Pact consumer contracts) in CI on every PR modifying routes/DTOs.

## 4. Architecture & Implementation
```typescript
export interface DeprecationNoticeConfig {
  readonly deprecatedAtUnixSec: number;
  readonly sunsetHttpDate: string; // RFC 9110 IMF-fixdate e.g. 'Tue, 01 Jun 2027 00:00:00 GMT'
  readonly migrationGuideUrl: string;
}

export function buildDeprecationHeaders(cfg: DeprecationNoticeConfig): Readonly<Record<string, string>> {
  return {
    Deprecation: `@${Math.floor(cfg.deprecatedAtUnixSec)}`,
    Sunset: cfg.sunsetHttpDate,
    Link: `<${cfg.migrationGuideUrl}>; rel="sunset"`,
  };
}

// Expand-Contract adapter keeping v1 clients working cleanly while v2 uses integer minor units
export interface InternalOrderDomain {
  readonly id: string;
  readonly totalMinor: number;
  readonly currency: string;
}

export function serializeOrderV1(order: InternalOrderDomain): {
  readonly id: string;
  readonly total_amount: number; // Legacy major-unit compatibility field preserved for v1
  readonly total_minor: number;  // Additive forward-compatible field
  readonly currency: string;
} {
  return {
    id: order.id,
    total_amount: order.totalMinor / 100,
    total_minor: order.totalMinor,
    currency: order.currency,
  };
}
```
CI breaking-diff verification:
```powershell
python "shadow-api/scripts/api_contract_verifier.py" --check-breaking-diff baseline_v1.json candidate_v1.json
```

## 5. Platform / Vendor Variations
| API Versioning Style | Pros | Cons / Watch-Out |
| :--- | :--- | :--- |
| **URI Path (`/api/v1/`, `/api/v2/`)** | Unambiguous in logs, CDN caches, browser dev tools & OpenAPI | Keep only major versions in URL (never `/v1.2.3/`) |
| **Date-Version Header (`API-Version: 2026-11-01`, Stripe style)** | Granular pinned partner upgrades | High server-side transformer maintenance; justify only for large public API platforms |
| **Unversioned Additive + RFC 9745 Field Deprecation** | Zero URL churn | Requires strict discipline & CI breaking-diff enforcement |

## 6. Decision Matrix & Trade-Offs
| Change Requested | Breaking? | Safe Migration Strategy |
| :--- | :---: | :--- |
| Add optional `currency` to response | No | Deploy directly on `v1` |
| Rename `price` -> `total_minor` | **YES** | Expand: return BOTH `price` + `total_minor`; deprecate `price` with `Sunset`; remove only in `v2` or after `0` callers |
| Add new mandatory `tax_id` on `POST /orders` | **YES** | Keep optional with default on `v1`, enforce required ONLY on `POST /v2/orders` |
| Fix security vulnerability / IDOR | Security Override | Patch immediately; communicate cleanly to affected clients |

## 7. Real Production Scenario
During a `v1 -> v2` order API rollout, a backend team changes `POST /api/v1/orders` in-place to require a new `tax_id` field and drops `total_amount` from the response. iOS/Android users who haven't updated their app in the App Store immediately hit `422` errors and blank checkout screens for 48 hours. Enforcing `api_contract_verifier.py --check-breaking-diff` in CI + serving `v1` via `serializeOrderV1` alongside `POST /api/v2/orders` with RFC 9745 `Deprecation`/`Sunset` headers keeps legacy mobile builds working smoothly until adoption drops below `0.1%`.

## 8. Failure Modes & Edge Cases
- **WRONG:** Emitting `Deprecation: true` (legacy draft boolean format obsoleted by RFC 9745) or removing a deprecated endpoint silently with `404 Not Found` while partners still call it.
- **RIGHT:** Emit RFC 9745 `Deprecation: @<unix_timestamp>` + RFC 8594 `Sunset: <IMF-fixdate>` + `Link: <guide>; rel="sunset"`, track live callers, and return `410 Gone` + migration URL after sunset.
- **WRONG:** Testing only server unit tests without running consumer contract tests (unit tests stay green while a renamed response property breaks the frontend/mobile parser!).
- **RIGHT:** Run OpenAPI breaking-diff (`compare_openapi_drift` / `api_contract_verifier.py`) + consumer-driven contract tests (`Pact` or typed client fixture tests) on every API PR.

## 9. Testing & Verification
- Run `python shadow-api/scripts/api_contract_verifier.py --self-test` and `python -m unittest discover -s shadow-api/tests -v`.
- Verify that every PR touching a live `v1` contract runs `--check-breaking-diff` against the `main` branch snapshot and fails CI if any breaking change is introduced without version isolation.

## 10. Operational Considerations
- Track `v1` vs `v2` request share and top remaining `v1` `consumer_id`/`User-Agent` versions on an API Migration Dashboard so sunset dates are driven by observed consumer telemetry, not guesswork.

## 11. Authoritative References
- IETF RFC 9745 — *The `Deprecation` HTTP Response Header Field* (`https://www.rfc-editor.org/rfc/rfc9745.html`).
- IETF RFC 8594 — *The `Sunset` HTTP Response Header Field* (`https://www.rfc-editor.org/rfc/rfc8594.html`).
- Pact Consumer-Driven Contract Testing (`https://docs.pact.io/`).

## 12. Limitations & When NOT to Use
- Maintaining `>= 3` simultaneous major API versions indefinitely creates severe testing and security-patching drag; keep at most 2 active major versions (`current` + `previous` with an explicit contractual `Sunset` schedule).
