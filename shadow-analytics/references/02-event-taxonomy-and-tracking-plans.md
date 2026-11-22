# 02. Event Taxonomy & Tracking Plans

## 1. Purpose & Activation Conditions
Design versioned, type-safe event schemas, naming conventions, and idempotent `event_id` strategies so product data stays clean, deduplicatable, and free of PII across web, mobile, and backend services. Load when creating a tracking plan, defining analytics events in TypeScript/JSON Schema, or fixing duplicate/malformed event ingestion.

## 2. Prerequisites
- Approved metric tree (`01-product-metrics-and-kpi-design.md`) defining which user and system behaviors actually drive decisions.
- Shared contract package or schema registry accessible by both producers (frontend/backend) and warehouse models.

## 3. Technical Principles & Constraints
- **Strict `Object_Action` Naming:** Use unambiguous past-tense `Object_Action` (`Checkout_Started`, `Order_Completed`, `Search_Queried`, `Invoice_Downloaded`). Never encode dynamic values inside event names (`Clicked_Red_Button_Home_V2` -> use `CTA_Clicked` with `variant: 'v2'`, `placement: 'home'`).
- **Occurrence-Unique, Retry-Stable `event_id` (CRITICAL):**
  - **Repeatable events** (`Search_Queried`, `Cart_Item_Added`, `Page_Viewed`, `Message_Sent`) MUST generate a **fresh unique ID per logical occurrence** (e.g., `UUIDv7` generated at the moment the user/system action occurs) and **reuse that exact `event_id` across network retries** so retries deduplicate cleanly while legitimate repeat actions are preserved.
  - **NEVER** use a static entity-only hash like `sha256(event + skuId)` or `sha256(event + userId)` for repeatable events — it silently destroys genuine repeat interactions!
  - Deterministic composite keys (`event:entityId:stateTransition`, e.g., `order_completed:ord_991`) are valid **ONLY** for strictly **once-per-entity domain state transitions** where a second occurrence is logically impossible.
- **Explicit Envelope & Schema Versioning:** Every event carries an immutable envelope: `event`, `event_id`, `schema_version`, `timestamp` (ISO-8601 UTC), `source` (`web` | `ios` | `android` | `server`), `anonymous_id` / `user_id`, and strongly typed `properties`.
- **Zero Raw PII by Contract:** Never put `email`, `phone`, `nik`, `npwp`, `password`, `token`, or `full_address` in event properties. Use opaque internal IDs (`user_id`, `workspace_id`, `order_id`).

## 4. Architecture & Implementation
```typescript
import { randomUUID } from 'node:crypto';

export type EventSource = 'web' | 'ios' | 'android' | 'server';

export interface EventEnvelope<TName extends string, TProps extends Readonly<Record<string, unknown>>> {
  readonly event: TName;
  readonly event_id: string;
  readonly schema_version: number;
  readonly timestamp: string;
  readonly source: EventSource;
  readonly anonymous_id?: string;
  readonly user_id?: string;
  readonly properties: TProps;
}

export type TrackedEvent =
  | EventEnvelope<'Search_Queried', { readonly query_length: number; readonly result_count: number; readonly filter_count: number }>
  | EventEnvelope<'Cart_Item_Added', { readonly sku_id: string; readonly quantity: number; readonly unit_price_minor: number; readonly currency: string }>
  | EventEnvelope<'Order_Completed', { readonly order_id: string; readonly subtotal_minor: number; readonly currency: string; readonly payment_method: string }>;

// Repeatable user action -> fresh per-occurrence UUID generated once and reused on retries
export function createCartItemAddedEvent(
  actor: { readonly anonymous_id?: string; readonly user_id?: string },
  props: { readonly sku_id: string; readonly quantity: number; readonly unit_price_minor: number; readonly currency: string }
): TrackedEvent {
  return {
    event: 'Cart_Item_Added',
    event_id: randomUUID(), // Unique per logical add action; caller preserves this exact ID on retry
    schema_version: 2,
    timestamp: new Date().toISOString(),
    source: 'web',
    ...actor,
    properties: props,
  };
}

// Once-per-entity state transition -> deterministic transition key prevents duplicate billing emits
export function createOrderCompletedEvent(
  userId: string,
  props: { readonly order_id: string; readonly subtotal_minor: number; readonly currency: string; readonly payment_method: string }
): TrackedEvent {
  return {
    event: 'Order_Completed',
    event_id: `order_completed:${props.order_id}`,
    schema_version: 2,
    timestamp: new Date().toISOString(),
    source: 'server',
    user_id: userId,
    properties: props,
  };
}
```

## 5. Platform / Vendor Variations
| Vendor / Pipeline | Deduplication Field | Schema Enforcement Support |
| --- | --- | --- |
| **PostHog** | `$insert_id` (dedups within rolling window in ClickHouse/ingest) | Data Management event/property definitions + custom TS/Zod validation |
| **Mixpanel** | `$insert_id` (exact dedup per `(event, time, distinct_id, $insert_id)`) | Lexicon schema + Data Pipelines |
| **Segment / RudderStack** | `messageId` | Protocols / Tracking Plans (blocks or flags violations at edge) |
| **GA4 (Measurement Protocol)** | No native global `event_id` dedup (only `transaction_id` on `purchase`) | Custom BigQuery `QUALIFY ROW_NUMBER() OVER (PARTITION BY event_id)` |

## 6. Decision Matrix & Trade-Offs (`event_id` Strategy)
| Event Kind | Example | Recommended `event_id` | Why |
| --- | --- | --- | --- |
| **Repeatable UI / Search / Cart Action** | `Cart_Item_Added`, `Search_Queried` | Fresh `UUIDv7` per occurrence (persisted across retry queue) | Preserves 5 distinct adds while deduplicating network retries |
| **Once-Per-Entity Domain Transition** | `Order_Completed`, `Account_Verified` | `order_completed:<order_id>` | Guarantees at-most-once warehouse counting even across webhook replays |
| **Periodic Heartbeat / Session Ping** | `Video_Heartbeat` | `heartbeat:<session_id>:<bucket_ts>` | Deduplicates jitter within the same time bucket |

## 7. Real Production Scenario
An engineer "hardens" deduplication by setting `event_id = sha256(event + userId + skuId)` globally for all events. One month later, merchandising reports repeat-purchase cart velocity dropped 40%. Investigation reveals that whenever a shopper adds the same SKU twice (or removes and re-adds it), the warehouse dedup job silently drops every subsequent `Cart_Item_Added` because the static hash collided with the first occurrence. Switching repeatable events to occurrence-unique UUIDs generated at action creation (persisted in the retry queue) restores accurate funnel counts while keeping retry deduplication intact.

## 8. Failure Modes & Edge Cases
- **WRONG:** Changing a property's data type in place (`price: 50000` -> `price: "Rp 50.000"`) without bumping `schema_version`.
- **RIGHT:** Store money in integer minor units (`amount_minor: 50000`, `currency: "IDR"`), treat property types as append-only immutable contracts, and bump `schema_version` on breaking schema changes.
- **WRONG:** Tracking "everything" via uncurated autocapture with zero explicit domain events (breaks whenever CSS classes or DOM hierarchy change).
- **RIGHT:** Use explicit, typed domain events for every funnel, KPI, and experiment metric; keep autocapture strictly for exploratory UX diagnostics.

## 9. Testing & Verification
- Validate sample event payloads in CI using `python shadow-analytics/scripts/analytics_experiment_verifier.py --check-event <event.json>`.
- Add unit tests verifying that retrying a failed `analytics.track(event)` call sends the **exact same `event_id`**, while two distinct user clicks emit **two distinct `event_id`s**.

## 10. Operational Considerations
- Maintain a single `tracking-plan.json` or TypeScript union in source control; require PR review from Analytics/Data Engineering whenever adding, renaming, or deprecating an event.
- Never rename an active event in place during a running A/B test — emit dual events during migration or wait for experiment conclusion.

## 11. Authoritative References
- Segment Documentation — *Tracking Plan & Schema Best Practices* (`https://segment.com/docs/protocols/tracking-plan/best-practices/`).
- PostHog Documentation — *Event Naming & Best Practices* (`https://posthog.com/docs/product-analytics/best-practices`).
- Snowplow Documentation — *Self-Describing JSON Schemas & Versioning* (`https://docs.snowplow.io/docs/understanding-tracking-design/`).

## 12. Limitations & When NOT to Use
- Do NOT use client-side analytics event schemas as an accounting/billing ledger or security audit log; emit authoritative financial records from transactional backend tables (`/shadow-data`, `/shadow-observe`).
- Avoid over-engineering 100+ micro-events before defining your core funnel (`01-product-metrics-and-kpi-design.md`) — start with 10–20 high-signal domain events.
