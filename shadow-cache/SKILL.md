---
name: shadow-cache
description: "Client & Server Caching Architecture. Use when designing or debugging HTTP/CDN Cache-Control/Surrogate-Key invalidation, Redis/Valkey L2 & bounded L1 LRU caches, multi-tenant key partitioning, Singleflight stampede & negative caching, TanStack Query/SWR optimistic updates, or Idempotency-Key patterns. Do NOT use for search indexing (shadow-search) or durable queues (shadow-concurrency)."
---

# Shadow Cache (`/shadow-cache`) — Multi-Tier Caching, Coherency, Stampede Defense & Idempotency

Use this skill when designing or debugging data fetching and caching layers across **L0 HTTP/CDN Edge** (`Cache-Control`, `ETag`, `Surrogate-Key`), **L1 In-Process Bounded LRU**, **L2 Distributed Redis/Valkey**, **L3 Client Server-State** (`TanStack Query`, `SWR`), cache invalidation/coherency, optimistic UI rollback, or transactional `Idempotency-Key` safety.

- **Owner:** HTTP/CDN caching headers & surrogate-key purging, tenant-partitioned versioned Redis keys, bounded L1 LRU caches, Singleflight/XFetch/jitter stampede & anti-penetration defenses, TanStack Query/SWR key factories & optimistic rollback, and scoped `Idempotency-Key` contracts.
- **Boundaries:** Search index relevance & alias reindexing (`shadow-search`), durable async outbox/queues (`shadow-concurrency`), realtime WebSocket/SSE sync (`shadow-realtime`), and external provider webhook reconciliation (`shadow-integrate`).

## Reference Guide

Load ONLY the 1–2 modular playbooks needed for the active caching subtask:

| Module | Topic | Load When |
| :--- | :--- | :--- |
| [01-http-cdn-edge-and-surrogate-keys.md](references/01-http-cdn-edge-and-surrogate-keys.md) | `Cache-Control` (`private, no-store` vs `s-maxage`), `ETag`/`304`, `Vary`, `Surrogate-Key`/`Cache-Tag` purging | Fixing stale CDN pages after admin edits, blocking PII leaks at CDN edge, tuning public catalog caching |
| [02-redis-l1-l2-and-tenant-partitioning.md](references/02-redis-l1-l2-and-tenant-partitioning.md) | Tenant/versioned Redis keys, bounded L1 LRU, Cache-Aside Delete-on-Write, O(1) generation counters, Redis isolation | Designing Redis keys safely, fixing cross-tenant leaks, replacing unbounded `Map` caches, banning `KEYS *` |
| [03-stampede-singleflight-jitter-and-penetration.md](references/03-stampede-singleflight-jitter-and-penetration.md) | Singleflight coalescing, Soft-TTL SWR, XFetch, TTL jitter, `"__NOT_FOUND__"` negative caching, Bloom filters | Stopping hot-key stampedes, midnight cache avalanches, or missing-ID cache penetration floods |
| [04-tanstack-query-optimistic-ui-and-idempotency.md](references/04-tanstack-query-optimistic-ui-and-idempotency.md) | Tenant-scoped Query Key Factories, optimistic rollback, `queryClient.clear()`, transactional `Idempotency-Key` | Implementing TanStack Query/SWR mutations, preventing server-state duplication in Zustand, hardening idempotent writes |
| [evaluations.md](evaluations.md) | Graded specialist evaluation scenarios (`CACHE-EVAL-01..07`) | Auditing CDN privacy, tenant key isolation, stampede/penetration defenses, and idempotency contracts |

---

## 1. Client-Side Server-State Management (`TanStack Query` / `SWR`)

1. **Tenant-Scoped Typed Query Keys Factory**:
   - Never scatter ad-hoc string arrays across components; always include `tenantId` in multi-tenant apps and call `queryClient.clear()` on logout or tenant switch:
     ```typescript
     export const orderKeys = {
       all: (tenantId: string) => ['tenant', tenantId, 'orders'] as const,
       lists: (tenantId: string) => [...orderKeys.all(tenantId), 'list'] as const,
       list: (tenantId: string, filters: OrderFilterDto) => [...orderKeys.lists(tenantId), filters] as const,
       details: (tenantId: string) => [...orderKeys.all(tenantId), 'detail'] as const,
       detail: (tenantId: string, id: string) => [...orderKeys.details(tenantId), id] as const,
     }
     ```
2. **Deterministic Mutation Invalidation & Optimistic Rollback**:
   - Every `useMutation` (`POST`, `PUT`, `PATCH`, `DELETE`) MUST cancel in-flight queries, snapshot & roll back cleanly in `onError` when optimistic, and invalidate affected list/detail keys in `onSettled`/`onSuccess`.
3. **Never Duplicate Server State in Global Client Stores (`Zustand`/`Redux`)**:
   - Keep `Zustand`/`Context` strictly for true client UI state (sidebar open, theme, multi-step wizard draft); let `TanStack Query`/`SWR` own API responses, caching, background refetching, and pagination.

---

## 2. Server-Side L0 CDN, L1 LRU & L2 Redis Invariants

1. **HTTP Privacy Floor & Edge Coherency**:
   - Force `Cache-Control: private, no-store` on all authenticated/PII routes (NEVER `public` or `s-maxage`). On public mutable catalogs, decouple short browser `max-age` (`30–60s`) from CDN `s-maxage` + `Surrogate-Key` purge triggered AFTER DB commit.
2. **Key Naming & Tenant Isolation**:
   - Prefix every Redis key with environment, tenant, domain, and schema version: `prod:tenant_42:user_profile:v1:user_99`. **Never cache tenant-specific data under a global key without `tenant_id` or `user_id`**, and never run `KEYS *` or `FLUSHDB` in production.
3. **Bounded L1 + Explicit TTL + Jitter (Anti-OOM & Anti-Avalanche)**:
   - Every in-process L1 cache MUST enforce `maxEntries` + bounded TTL (never unbounded `Map`). Every Redis cache key MUST have a finite `TTL` (`EX`) with random jitter ($\pm 15\%$) on bulk-warmed/hot keys.
4. **Stampede & Penetration Defense**:
   - Wrap expensive hot-key loaders in **Singleflight** coalescing (plus optional Soft-TTL SWR / distributed lock) and guard missing IDs with short-TTL `"__NOT_FOUND__"` negative caching (`30–60s` + jitter, never caching transient `5xx` errors).

---

## 3. Idempotency Keys for State-Mutating Endpoints (`Idempotency-Key`)

For payment, order creation, approval, or webhook endpoints:
- Accept an `Idempotency-Key` header (or deterministic event ID).
- Scope the key to the authenticated principal, tenant, and operation. Bind it to a canonical fingerprint of validated business inputs. A reused key with a different fingerprint must reject without disclosing the old result. Recheck authorization before replay.
- Atomically reserve the scoped key. Use the established pending response for concurrent matching requests. Tie completion to the durable business commit or provider receipt. If the process dies between the remote effect and local acknowledgment, reconcile by stable operation ID before retrying. Derive retention from the business retry window and upstream deduplication guarantees. Exercise competing requests, lost acknowledgment, expired keys, and revoked access.
- Define exact invalidation triggers across CDN/edge, Redis, and client `TanStack Query` caches so stale authorization or balance views never persist past security/mutation events.

---

## 4. Deterministic Cache Policy & Idempotency Verification

For a single transactional database, `test_idempotency.py` exercises competing connections, changed payload, tenant/principal isolation, revoked access, interrupted commit, and lost reply (external side effects require a separate provider reconciliation test). Pair it with `cache_policy_verifier.py` for multi-tier configuration hygiene:

```powershell
python shadow-cache/scripts/cache_policy_verifier.py --self-test
python shadow-cache/scripts/cache_policy_verifier.py --check-cache-config path/to/cache_policy.json
python -m unittest discover -s shadow-cache/tests -v
```
