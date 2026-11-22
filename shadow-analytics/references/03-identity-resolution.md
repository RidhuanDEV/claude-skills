# 03. Identity Resolution

## 1. Purpose & Activation Conditions
Design deterministic, privacy-safe identity resolution across anonymous browsing, signup/login transitions, multi-device usage, session stitching, and shared-device logouts. Load when wiring `anonymous_id` / `user_id` / `identify()` / `reset()`, debugging fractured pre-signup-to-purchase funnels, or fixing merged user profiles on shared terminals.

## 2. Prerequisites
- Stable, immutable internal `user_id` (UUID/snowflake — NEVER mutable `email` or `phone` as primary identity key).
- Consent gate (`04-privacy-and-consent-architecture.md`) controlling whether persistent client identifiers (`cookie`/`localStorage`) may be stored.

## 3. Technical Principles & Constraints
- **Immutable Canonical Key:** Always identify users by an opaque immutable database `user_id` (e.g., `usr_01J9...`), never by `email` (users change emails, causing split histories, and emails leak PII into every vendor).
- **Clean Lifecycle State Machine:**
  1. **Pre-Auth:** Generate a random `anonymous_id` (stored in first-party cookie/storage only when permitted by consent; otherwise ephemeral in-memory session ID).
  2. **Authentication (`identify`):** Call `identify(user_id)` upon confirmed login/signup, emitting an explicit link `(anonymous_id, user_id, linked_at)` so pre-login funnel events stitch cleanly to the authenticated user.
  3. **Logout (`reset` — MANDATORY):** Immediately call `reset()` on logout (and session expiry on shared devices) to generate a **brand-new `anonymous_id`** and clear cached traits so the next person on that browser/kiosk NEVER merges into the previous user's profile.
- **Shared-Device / Kiosk Guard:** On shared terminals (POS tablets, hospital/clinic desks, school labs, admin impersonation sessions), **disable retroactive cross-user alias merging** and isolate staff/impersonated traffic (`is_impersonated: true`, excluded from customer metrics).
- **Session Definition Explicitness:** Define session boundaries deterministically (standard `30-minute` inactivity timeout, plus optional UTM campaign boundary if marketing attribution requires it) in the warehouse rather than relying solely on opaque client-side session timers.

## 4. Architecture & Implementation
```typescript
export interface IdentityClient {
  identify(userId: string, traits: Readonly<Record<string, string | number | boolean>>): void;
  reset(): void;
  setSuperProperties(props: Readonly<Record<string, string | boolean>>): void;
}

export interface AuthSessionContext {
  readonly userId: string;
  readonly workspaceId: string;
  readonly planTier: string;
  readonly isSharedKiosk: boolean;
  readonly isImpersonated: boolean;
}

export function onUserAuthenticated(client: IdentityClient, ctx: AuthSessionContext): void {
  if (ctx.isImpersonated) {
    // Never contaminate customer identity graph during support impersonation
    client.setSuperProperties({ is_impersonated: true });
    return;
  }
  if (ctx.isSharedKiosk) {
    // Rotate anonymous_id BEFORE identify so prior kiosk user's anonymous events do not bleed in
    client.reset();
  }
  client.identify(ctx.userId, {
    workspace_id: ctx.workspaceId,
    plan_tier: ctx.planTier,
  });
}

export function onUserLoggedOut(client: IdentityClient): void {
  // Always rotate anonymous_id & clear cached user traits on logout
  client.reset();
}
```
Warehouse retroactive stitching (bounded to a safe lookback window to avoid merging years-old shared-computer events):
```sql
-- Resolve canonical user_id for anonymous events within 30 days prior to first identify
WITH id_map AS (
  SELECT
    anonymous_id,
    user_id,
    MIN(event_ts) AS first_linked_at
  FROM analytics_identity_links
  WHERE is_shared_kiosk = FALSE
  GROUP BY anonymous_id, user_id
  -- Exclude polluted anonymous_ids linked to > 3 distinct users (shared devices/bots)
  HAVING COUNT(*) OVER (PARTITION BY anonymous_id) <= 3
)
SELECT
  e.event_id,
  COALESCE(e.user_id, m.user_id, e.anonymous_id) AS canonical_actor_id,
  e.event_name,
  e.event_ts
FROM raw_events e
LEFT JOIN id_map m
  ON e.user_id IS NULL
 AND e.anonymous_id = m.anonymous_id
 AND e.event_ts BETWEEN m.first_linked_at - INTERVAL '30 days' AND m.first_linked_at;
```

## 5. Platform / Vendor Variations
| Platform | Identity Mechanism | Critical Gotcha |
| --- | --- | --- |
| **PostHog** | `posthog.identify(userId)` merges current `distinct_id` into `userId`; `posthog.reset()` rotates device ID | Calling `identify()` with an already-merged `anonymous_id` across >1 user creates irreversible person-merge collisions unless `reset()` runs on logout |
| **Mixpanel (Simplified ID Merge)** | Automatically merges `$device_id` + `$user_id` when both appear on same event | Hard cap of ~500 `$device_id`s per `$user_id`; shared kiosk without `reset()` hits cap and corrupts user |
| **GA4** | `user_id` + `client_id` (cookie `_ga`); Reporting Identity blends User-ID / Device / Modeling | Does NOT retroactively stitch pre-login hits in standard UI reports; requires BigQuery export stitching |
| **B2B Group Analytics** | `group('workspace', workspaceId)` alongside `user_id` | Essential for B2B SaaS retention where seats rotate inside one paying account |

## 6. Decision Matrix & Trade-Offs
| Resolution Strategy | Pre-Signup Funnel Accuracy | Shared-Device Safety | Complexity |
| --- | --- | --- | --- |
| **Device-Only (`anonymous_id`)** | Broken across devices | High | Low |
| **Deterministic `identify` + `reset` + Bounded Warehouse Stitch** | High (same device + cross-device post-login) | High (with `<= 3` users/device cap) | Medium (Recommended) |
| **Probabilistic IP + User-Agent Fingerprinting** | Unreliable (CGNAT/office Wi-Fi) | Poor + high UU PDP / GDPR legal risk | High (**Avoid**) |

## 7. Real Production Scenario
A clinic management SaaS notices that receptionists and doctors share a single Chrome browser at the front desk. Because the app never calls `analytics.reset()` on logout, 14 staff accounts get merged into one giant PostHog person profile, inflating "power user" counts and breaking role-based funnel metrics. Implementing `reset()` on logout, flagging `isSharedKiosk`, and capping warehouse `anonymous_id` fan-out (`<= 3` distinct `user_id`s) immediately isolates staff profiles and cleans downstream funnels.

## 8. Failure Modes & Edge Cases
- **WRONG:** Passing `email` as `distinct_id` / `user_id` or calling `identify()` on every page load with a string `"null"` / `"undefined"` when logged out (merges ALL anonymous visitors worldwide into one single user named `"undefined"`!).
- **RIGHT:** Guard `if (!userId || userId === 'undefined' || userId === 'null') return;` before calling `identify()`, and use opaque immutable `user_id` UUIDs.
- **WRONG:** Letting Safari ITP (7-day client-side JS cookie cap) wipe `anonymous_id` on returning visitors and misclassifying them as brand-new users every week.
- **RIGHT:** Set `anonymous_id` via a first-party **server-set `HttpOnly` cookie** from your own domain (subject to consent) to preserve legitimate continuity without third-party tracking.

## 9. Testing & Verification
- E2E test: Visit landing page (`anon_A`) -> sign up as `user_1` -> verify `identify(user_1)` links `anon_A` -> log out -> verify `anonymous_id` rotates to `anon_B != anon_A` -> log in as `user_2` -> assert `user_2` is NOT linked to `anon_A`.
- Warehouse quality query: Alert if any single `anonymous_id` links to `> 5` distinct `user_id`s in 30 days (indicates missing `reset()` or QA/kiosk pollution).

## 10. Operational Considerations
- Exclude internal QA accounts, synthetic health checks, and support impersonation sessions via explicit boolean properties (`is_internal`, `is_impersonated`) filtered in dbt staging models.
- For B2B products, ALWAYS attach `workspace_id` / `organization_id` to every authenticated event so account-level retention and seat expansion can be analyzed alongside user-level funnels.

## 11. Authoritative References
- PostHog Documentation — *Identifying Users & Merging Caveats* (`https://posthog.com/docs/product-analytics/identify`).
- Mixpanel Documentation — *Simplified ID Merge Architecture* (`https://docs.mixpanel.com/docs/tracking-methods/id-management/identifying-users-simplified`).
- WebKit Tracking Prevention (ITP) Policy (`https://webkit.org/tracking-prevention/`).

## 12. Limitations & When NOT to Use
- Do NOT attempt deterministic cross-device stitching before login (e.g., matching mobile visitor to desktop visitor without authentication) via invasive browser fingerprinting; accept pre-login cross-device breaks honestly as a measurement limit.
- Never reuse analytics `anonymous_id` as a security session token or CSRF secret.
