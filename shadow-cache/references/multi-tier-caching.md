# Multi-Tier Caching: HTTP/CDN Edge, L1+L2, Singleflight & Stampede Defense

## 1. Core Concepts
High-scale caching coordinates four distinct tiers — **L0 Browser/CDN Edge**, **L1 In-Process Bounded LRU**, **L2 Distributed Redis/Valkey**, and **L3 Client Query Cache (`TanStack Query`/`SWR`)** — while defending against **stampedes (singleflight + jitter)**, **penetration (negative caching/Bloom filters)**, and **cross-tenant key leakage**.

## 2. Technical Rules & Tier Selection Matrix

| Tier | Choose For | Mandatory Safety Rule |
| :--- | :--- | :--- |
| **L0 HTTP / CDN Edge** | Public catalogs, static assets, public marketing pages | Use `Cache-Control: public, max-age=..., stale-while-revalidate=...` + `ETag`/`Surrogate-Key`. **Force `Cache-Control: private, no-store` on all authenticated/PII routes!** |
| **L1 In-Process LRU** | Ultra-hot read-mostly config, JWKS public keys, feature flags | Enforce strict `maxEntries` (never unbounded `Map`!) and short TTL (`5–60s`) or pub/sub invalidation. |
| **L2 Redis / Valkey** | Shared tenant queries, rate limits, idempotency receipts | Format keys strictly as `{env}:{tenantId}:{domain}:v{schemaVer}:{id}`; never run `KEYS *` or `FLUSHDB` in prod. |
| **L3 Client (`TanStack Query`)** | Browser server-state synchronization & optimistic mutations | Include `tenantId` and filter params in query keys `['orders', tenantId, { status }]`; invalidate on mutation settle. |

## 3. Implementation Examples
```ts
// 1. In-Flight Request Coalescing (Singleflight) + Jittered TTL (Prevents Cache Stampede)
const inFlightLoads = new Map<string, Promise<unknown>>()

export function computeJitteredTtlSec(baseTtlSec: number, jitterRatio = 0.15, rand = Math.random): number {
  const delta = baseTtlSec * jitterRatio * (rand() * 2 - 1)
  return Math.max(1, Math.round(baseTtlSec + delta))
}

export async function loadWithSingleflight<T>(
  namespacedKey: string,
  loader: () => Promise<T>,
  registry: Map<string, Promise<T>> = new Map<string, Promise<T>>(),
): Promise<T> {
  const existing = registry.get(namespacedKey)
  if (existing) {
    return existing
  }
  const promise = loader().finally(() => {
    registry.delete(namespacedKey)
  })
  registry.set(namespacedKey, promise)
  return promise
}
```

## 4. Best Practices
- Use **Cache-Aside + Delete-on-Write**: commit the authoritative DB transaction first, then delete/invalidate the cache key (never write to cache before the DB transaction commits!).
- Cache a short-lived `"__NOT_FOUND__"` sentinel (`TTL = 30–60s`) for missing IDs to stop cache-penetration attacks from hammering the database.

## 5. Anti-patterns (WRONG vs RIGHT)
- **WRONG:** Caching `GET /api/v1/orders` under key `orders:list` without `tenantId` (leaks Tenant A's orders to Tenant B!) or setting `Cache-Control: public` on an endpoint that reads `Authorization` / session cookies.
- **RIGHT:** Always bind `tenantId` in the key prefix (`prod:t-alpha:orders:v1:list`) and set `Vary: Authorization` or `Cache-Control: private, no-store`.
- **WRONG:** Letting 1,000 concurrent requests miss an expired hot key and query PostgreSQL simultaneously.
- **RIGHT:** Wrap cache-miss loaders in **Singleflight** request coalescing + jittered TTLs.

## 6. Production Considerations
- Ensure the service degrades gracefully (circuit-breaker + shed non-critical queries) if Redis becomes unreachable rather than crashing the entire application.
