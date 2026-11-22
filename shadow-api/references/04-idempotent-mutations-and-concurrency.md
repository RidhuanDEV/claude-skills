# 04. Idempotent Mutations & Concurrency Safety

## 1. Purpose & Activation Conditions
Guarantee safe client retries on non-idempotent `POST` mutations (orders, payments, refunds, transfers, invites) using **`Idempotency-Key`** semantics, payload fingerprinting, concurrent in-flight locks, and optimistic concurrency control (`ETag` / `If-Match`). Load when designing write endpoints that can be retried after mobile/network timeouts.

## 2. Prerequisites
- Relational database with ACID unique constraints (or transactional Redis + DB outbox `/shadow-concurrency`) and tenant-scoped authentication (`shadow-auth`).

## 3. Technical Principles & Constraints
- **Why Network Retries Create Duplicate Charges:** When a client sends `POST /api/v1/orders` and the TCP connection drops AFTER the server committed the DB transaction but BEFORE the `201 Created` response reached the client, the client cannot distinguish timeout-before-commit from timeout-after-commit. Without `Idempotency-Key`, retrying creates a duplicate order/charge!
- **4 Mandatory `Idempotency-Key` State-Machine Rules (IETF Draft / Stripe Standard):**
  1. **Tenant + Route Scoping:** Uniqueness key is ALWAYS `(tenant_id, route_key, idempotency_key)` — NEVER global across tenants (otherwise Tenant B could probe or collide with Tenant A's key!).
  2. **Payload Fingerprint Check (`SHA-256`):** Hash the canonical request body (`payload_hash`). If the exact same `Idempotency-Key` is reused with a **different** payload -> reject immediately with **`422 Unprocessable Content`** (`idempotency-payload-mismatch`)!
  3. **In-Flight Lock (`409 Conflict`):** Insert the idempotency row in state `IN_PROGRESS` inside a unique-constrained transaction BEFORE executing side effects. If a second identical request arrives while the first is still running -> return **`409 Conflict`** (`Retry-After: 1`) instead of executing twice in parallel!
  4. **Stored Response Replay (`2xx`/`4xx`) vs Recovery (`5xx`):** Persist final `status_code` + `response_body` atomically with the domain mutation (`COMPLETED`, retained `>= 24–72 hours`). Replays return the exact stored response with header `Idempotent-Replayed: true`. If a transient `5xx` occurs BEFORE committing domain state, delete/mark `FAILED_RETRYABLE` so the client can safely retry with the same key!
- **Optimistic Concurrency on `PUT`/`PATCH` (`ETag` / `If-Match`):** Prevent lost updates when two users edit the same record concurrently by requiring `If-Match: "<version>"` (`UPDATE ... WHERE id = $1 AND tenant_id = $2 AND version = $3`) and returning **`412 Precondition Failed`** (or `409 Conflict`) on stale versions.

## 4. Architecture & Implementation
```sql
-- Tenant-scoped idempotency ledger table (PostgreSQL)
CREATE TABLE api_idempotency_keys (
  tenant_id       UUID NOT NULL,
  route_key       TEXT NOT NULL,          -- e.g. 'POST:/api/v1/orders'
  idempotency_key TEXT NOT NULL,
  payload_sha256  TEXT NOT NULL,
  state           TEXT NOT NULL CHECK (state IN ('IN_PROGRESS', 'COMPLETED')),
  response_status INTEGER,
  response_body   JSONB,
  created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  expires_at      TIMESTAMPTZ NOT NULL,
  PRIMARY KEY (tenant_id, route_key, idempotency_key)
);
CREATE INDEX idx_idempotency_expires_at ON api_idempotency_keys (expires_at);
```
Deterministic decision helper (strict TS, zero casts):
```typescript
export type IdempotencyDecision =
  | { readonly action: 'EXECUTE_NEW' }
  | { readonly action: 'REPLAY_CACHED'; readonly status: number; readonly body: unknown }
  | { readonly action: 'REJECT_PAYLOAD_MISMATCH'; readonly status: 422 }
  | { readonly action: 'REJECT_IN_FLIGHT_CONFLICT'; readonly status: 409 };

export interface ExistingIdempotencyRecord {
  readonly payloadSha256: string;
  readonly state: 'IN_PROGRESS' | 'COMPLETED';
  readonly responseStatus: number | null;
  readonly responseBody: unknown;
}

export function evaluateIdempotencyLookup(
  existing: ExistingIdempotencyRecord | null,
  incomingPayloadSha256: string
): IdempotencyDecision {
  if (!existing) return { action: 'EXECUTE_NEW' };
  if (existing.payloadSha256 !== incomingPayloadSha256) {
    return { action: 'REJECT_PAYLOAD_MISMATCH', status: 422 };
  }
  if (existing.state === 'IN_PROGRESS') {
    return { action: 'REJECT_IN_FLIGHT_CONFLICT', status: 409 };
  }
  return {
    action: 'REPLAY_CACHED',
    status: existing.responseStatus ?? 200,
    body: existing.responseBody,
  };
}
```

## 5. Platform / Vendor Variations
| Mutation Pattern | Best Concurrency Control | Caveat |
| :--- | :--- | :--- |
| **Create (`POST /orders`, `POST /payments`)** | `Idempotency-Key` + DB primary key `(tenant_id, route_key, key)` | Commit idempotency completion in the SAME DB transaction as the order + outbox row! |
| **Update (`PATCH /invoices/:id`)** | `ETag` + `If-Match` (or `version` column CAS) | Return `412 Precondition Failed` on mismatch so UI prompts user to refresh |
| **External Gateway Call Inside Request** | Pass the exact same `Idempotency-Key` onward to Stripe/Xendit/Midtrans | Prevents double charge even if our app crashes right after calling the gateway |

## 6. Decision Matrix & Trade-Offs
| Store for Idempotency Keys | Atomicity with Domain DB | Cleanup / TTL | Verdict |
| :--- | :---: | :---: | :--- |
| **Same Relational DB (Postgres/MySQL)** | **100% ACID transactional** | Scheduled `DELETE WHERE expires_at < NOW()` | **Best for money, orders & state transitions** |
| **Redis-Only (`SET NX EX`)** | Non-atomic with Postgres! (Redis flush/failover causes duplicates) | Automatic TTL | Acceptable ONLY for low-stakes rate-limited UI actions, NOT financial ledger writes |

## 7. Real Production Scenario
A mobile checkout client times out at 5s on a slow 3G connection and automatically retries `POST /api/v1/orders` twice during a `v1 -> v2` rollout. Because the backend checks Redis for idempotency *before* DB commit and releases the lock on timeout, two parallel requests charge the customer twice. Moving `api_idempotency_keys` into the same PostgreSQL transaction as `orders` + `outbox_events` with `payload_sha256` verification and `409` in-flight locking reduces duplicate orders to zero.

## 8. Failure Modes & Edge Cases
- **WRONG:** Generating `Idempotency-Key` on the **server** (defeats the entire purpose — retries generate a brand-new key every time!).
- **RIGHT:** Require the **client** to generate a UUIDv4/v7 `Idempotency-Key` once per logical user intent and resend the exact same header across retries.
- **WRONG:** Silently returning the cached `201` response when a buggy client reuses the same `Idempotency-Key` with a DIFFERENT `amount` (`Rp 10.000` vs `Rp 500.000`).
- **RIGHT:** Compare `payload_sha256` and fail loudly with `422 Unprocessable Content`.

## 9. Testing & Verification
- Integration test 4 cases on every idempotent `POST` route: (1) first call -> `201`, (2) identical retry -> exact cached `201` + `Idempotent-Replayed: true` + DB row count still `1`, (3) same key + mutated payload -> `422`, (4) two concurrent parallel calls with same key -> one `201`, one `409` (never 2 rows!).

## 10. Operational Considerations
- Retain completed idempotency keys for `24–72 hours` (or `7 days` for async batch clients); purge expired rows in bounded batches (`LIMIT 10000`) to avoid table bloat and lock spikes.

## 11. Authoritative References
- IETF Draft — *The `Idempotency-Key` HTTP Header Field* (`https://datatracker.ietf.org/doc/draft-ietf-httpapi-idempotency-key-header/`).
- IETF RFC 9110 §13.1.1 — *`If-Match` Conditional Requests*.
- Stripe Engineering — *Designing Robust and Predictable APIs with Idempotency*.

## 12. Limitations & When NOT to Use
- Do NOT require `Idempotency-Key` on read-only `GET`/`HEAD` routes or naturally idempotent `PUT` replacements (use `If-Match` for concurrent updates instead).
