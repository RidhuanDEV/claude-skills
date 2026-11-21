---
name: shadow-cache
description: "Client & Server Caching Architecture. Use when implementing or debugging TanStack Query/SWR invalidation, Redis caching, cache stampede protection, optimistic UI updates, or Idempotency-Key patterns."
---

# Shadow Cache (`/shadow-cache`) — Client/Server Caching, Invalidation & Realtime Sync

Use this skill when designing or debugging data fetching, caching layers (`TanStack Query`, `SWR`, `Redis`, HTTP `Cache-Control`), cache invalidation, optimistic UI updates, or request idempotency.

---

## 1. Client-Side Server-State Management (`TanStack Query` / `SWR`)

1. **Structured Query Keys Factory**:
   - Never scatter ad-hoc string arrays across components. Define a typed query-key factory per domain:
     ```typescript
     export const orderKeys = {
       all: ['orders'] as const,
       lists: () => [...orderKeys.all, 'list'] as const,
       list: (filters: OrderFilterDto) => [...orderKeys.lists(), filters] as const,
       details: () => [...orderKeys.all, 'detail'] as const,
       detail: (id: string) => [...orderKeys.details(), id] as const,
     };
     ```
2. **Deterministic Mutation Invalidation**:
   - Every `useMutation` (`POST`, `PUT`, `PATCH`, `DELETE`) MUST invalidate affected list and detail keys in `onSuccess` (or roll back cleanly in `onError` when using optimistic updates).
3. **Never Duplicate Server State in Global Client Stores (`Zustand`/`Redux`)**:
   - Keep `Zustand`/`Context` strictly for true client UI state (sidebar open, theme, multi-step wizard draft); let `TanStack Query` own API responses, caching, background refetching, and pagination.

---

## 2. Server-Side Redis & HTTP Caching Patterns

1. **Key Naming & Tenant Isolation**:
   - Prefix every Redis key with environment, tenant, domain, and schema version: `prod:tenant_42:user_profile:v1:user_99`.
   - **Never cache tenant-specific data under a global key without `tenant_id` or `user_id`!**
2. **Explicit TTL + Jitter (Anti-Cache-Avalanche)**:
   - Every cached key (except explicit persistent queues/locks) MUST have a `TTL` (`EX`). Add random jitter ($\pm 10\%$) to TTLs on bulk-warmed keys so thousands of keys do not expire at the exact same second.
3. **Cache Stampede / Thundering Herd Protection**:
   - For expensive aggregation/dashboard queries, use single-flight locking (mutex lock or stale-while-revalidate) so 200 concurrent requests on a cache miss trigger only **1** database query instead of 200.
4. **Negative Caching**:
   - When an ID lookup misses in the DB, cache a short-lived sentinel (`"__NULL__"` with `EX 30`) to protect the database against repeated lookups for non-existent IDs.

---

## 3. Idempotency Keys for State-Mutating Endpoints (`Idempotency-Key`)

For payment, order creation, approval, or webhook endpoints:
- Accept an `Idempotency-Key` header (or deterministic event ID).
- Scope the key to the authenticated principal, tenant and operation. Bind it to a canonical fingerprint of validated business inputs. A reused key with a different fingerprint must reject without disclosing the old result. Recheck authorization before replay.
- Atomically reserve the scoped key. Use the established pending response for concurrent matching requests. Tie completion to the durable business commit or provider receipt. If the process dies between the remote effect and local acknowledgment, reconcile by stable operation ID before retrying. Derive retention from the business retry window and upstream deduplication guarantees. Exercise competing requests, lost acknowledgment, expired keys and revoked access.
4. **Coherency Boundaries & Multi-Tier Invalidation**:
   - Separate public catalog caches from tenant/user-authorized keys (`user_id`/`tenant_id` in cache key mandatory to prevent cross-user leakage).
   - Define exact invalidation triggers across CDN/edge, Redis, and client `TanStack Query` caches so stale authorization or balance views never persist past security/mutation events.

For a single transactional database, `python -m unittest discover -s tests` from the skill directory exercises competing connections, changed payload, tenant/principal isolation, revoked access, interrupted commit and lost reply. External side effects require a separate provider reconciliation test.

## Deep Engineering Reference (Load On-Demand)
- For HTTP/CDN Edge caching (`Cache-Control`/`ETag`/`Vary`/`Surrogate-Key`), L1 LRU + L2 Redis two-tier caching, Singleflight stampede defense, Bloom filter anti-penetration, and negative caching -> read [Multi-tier caching architecture](references/multi-tier-caching.md).
