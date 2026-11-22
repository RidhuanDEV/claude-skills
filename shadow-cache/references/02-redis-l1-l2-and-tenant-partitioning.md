# 02 — Redis/Valkey L2 & In-Process L1 Caching, Tenant Partitioning & Coherency

## 1. Purpose & Activation Conditions
Architect multi-tier **L1 (In-Process Bounded LRU)** + **L2 (Distributed Redis/Valkey)** caches with airtight **tenant isolation**, **schema-versioned keys**, **Cache-Aside Delete-on-Write** coherency, safe eviction policies, and graceful degradation when Redis is unavailable. Activate when introducing Redis caching, fixing cross-tenant cache leaks, eliminating OOM from in-process `Map` caches, or designing cache invalidation across service replicas.

## 2. Prerequisites
- Defined authoritative data source (PostgreSQL/MySQL) — Redis is treated strictly as an ephemeral accelerator (unless explicitly architected as a durable queue/stream under `/shadow-concurrency`).
- Confirmed multi-tenant isolation model (`tenant_id` + optional `user_id` / `role_hash`) from `/shadow-auth`.

## 3. Technical Principles & Constraints
- **Mandatory Key Naming Contract (`{env}:tenant_{tenantId}:{domain}:v{schemaVer}:{entityId}`):**
  - **Environment prefix (`prod:` / `staging:`):** Prevents accidental staging traffic from colliding with production if clusters share infrastructure.
  - **Tenant & principal scope (`tenant_42:` or `public:`):** NEVER store tenant-specific or user-specific payloads under a global key (`orders:list`). If data depends on RBAC permissions, include the normalized permission/role scope hash too.
  - **Schema version (`v1:`, `v2:`):** Rolling deploys where `v2` expects a new JSON field will crash or corrupt `v1` pods if both share the same unversioned key. Bump `v2` in the key prefix for instant zero-downtime cache isolation across deploys!
- **Cache-Aside + Delete-on-Write (Commit DB First!):**
  - Read path: Check L1 -> Check L2 Redis -> Query DB -> Populate L2 (with `EX` + jitter) -> Populate L1.
  - Write path: **1. Commit DB transaction FIRST -> 2. `DEL` Redis key (never `SET` before DB commit, and prefer `DEL` over `SET` to avoid concurrent write-order race conditions!) -> 3. Publish tiny key-invalidation event (if using L1 across replicas).**
- **Strict L1 In-Process Bounds:** NEVER use an unbounded `new Map()` in Node.js/Python/Go as a cache! Every L1 cache MUST enforce `maxEntries` (LRU/TinyLFU eviction) and a short `ttlSec` (`5–60s`), reserved strictly for ultra-hot, small, read-mostly objects (JWKS public keys, tenant feature flags, static lookup tables).
- **Zero Blocking Production Commands:** NEVER execute `KEYS *`, `FLUSHDB`, or `FLUSHALL` in production Redis (Redis is single-threaded — `KEYS *` over 2M keys freezes the entire cluster for seconds and trips every service's timeouts!). Use explicit key `UNLINK`, **Generation/Namespace Version Counters** (increment `tenant_42:orders:gen` to logically invalidate 10,000 list keys in O(1)!), or bounded `SCAN`.
- **Eviction Policy & Graceful Fallback:** Configure dedicated Redis cache instances with `maxmemory` + `maxmemory-policy allkeys-lru` or `allkeys-lfu` (NEVER share the same Redis eviction pool between ephemeral cache keys and durable BullMQ queues — `allkeys-lru` will silently evict your job queues!). Wrap Redis calls in tight timeouts (`50–150ms`) + circuit breaker so a Redis blip degrades gracefully to DB (with shedding) rather than crashing requests with 500s.

## 4. Architecture & Implementation

```ts
// Strict TypeScript Tenant-Scoped Key Builder + Bounded L1 LRU + Cache-Aside Helper (0 any, 0 casts)
export interface RedisLike {
  get(key: string): Promise<string | null>
  set(key: string, value: string, mode: 'EX', ttlSec: number): Promise<unknown>
  unlink(key: string): Promise<number>
}

export interface CacheKeyParts {
  readonly env: 'prod' | 'staging' | 'dev'
  readonly tenantId: string // use 'public' ONLY for verified non-tenant data
  readonly domain: string
  readonly schemaVersion: number
  readonly entityId: string
}

export function buildVersionedCacheKey(parts: CacheKeyParts): string {
  const clean = (segment: string): string => segment.replace(/[^a-zA-Z0-9._-]/g, '_')
  const scope = parts.tenantId === 'public' ? 'public' : `tenant_${clean(parts.tenantId)}`
  return `${parts.env}:${scope}:${clean(parts.domain)}:v${parts.schemaVersion}:${clean(parts.entityId)}`
}

export class BoundedL1Cache<T> {
  private readonly store = new Map<string, { readonly value: T; readonly expiresAt: number }>()

  public constructor(
    private readonly maxEntries: number,
    private readonly defaultTtlMs: number,
  ) {
    if (maxEntries <= 0 || defaultTtlMs <= 0) {
      throw new Error('BoundedL1Cache requires positive maxEntries and defaultTtlMs')
    }
  }

  public get(key: string, now = Date.now()): T | undefined {
    const entry = this.store.get(key)
    if (!entry) return undefined
    if (now >= entry.expiresAt) {
      this.store.delete(key)
      return undefined
    }
    // Refresh LRU recency
    this.store.delete(key)
    this.store.set(key, entry)
    return entry.value
  }

  public set(key: string, value: T, ttlMs = this.defaultTtlMs, now = Date.now()): void {
    if (this.store.has(key)) {
      this.store.delete(key)
    } else if (this.store.size >= this.maxEntries) {
      const oldestKey = this.store.keys().next().value
      if (oldestKey !== undefined) {
        this.store.delete(oldestKey)
      }
    }
    this.store.set(key, { value, expiresAt: now + ttlMs })
  }

  public delete(key: string): void {
    this.store.delete(key)
  }
}
```

### O(1) Namespace Generation Invalidation Pattern (Zero `KEYS *`)
When a tenant has 200 cached filtered list pages (`orders:list:page=1&status=paid`, `page=2...`), deleting them with `KEYS *orders:list*` stalls Redis. Instead:
1. Read `gen = await redis.get("prod:tenant_42:orders:v1:gen") ?? "1"`.
2. Build list cache key incorporating `gen`: `prod:tenant_42:orders:v1:g${gen}:p1_paid`.
3. On any order mutation (after DB commit), simply call `await redis.incr("prod:tenant_42:orders:v1:gen")` (`O(1)` atomic!) — all old paginated keys become unreachable instantly and expire naturally via their finite TTL!

## 5. Platform/Vendor Variations
- **Redis 7.x / Valkey 8.x:** Prefer non-blocking `UNLINK` over `DEL` for large hash/JSON values (`> 64KB`) so memory reclamation happens on a background thread; use Redis Cluster hash tags (`{tenant_42}`) when executing multi-key `MGET`/`EVAL` Lua scripts so all keys for one tenant hash to the same slot.
- **Dedicated Cache vs Durable State Redis:** Run **two separate Redis instances/databases** — Cache instance (`allkeys-lfu`, persistence disabled `save ""` / `appendonly no` for speed) vs Queue/Session/Lock instance (`noeviction`, AOF enabled).
- **Multi-Replica L1 Coherency:** If using L1 across 6 pods, subscribe to Redis Pub/Sub invalidation channels (or Valkey/Redis Client-Side Tracking) OR restrict L1 strictly to data tolerating `<= 15s` staleness (e.g., JWKS keys, public tier rates).

## 6. Decision Matrix & Trade-Offs

| Pattern | Consistency | Latency | Memory Safety | Best Fit |
| :--- | :--- | :--- | :--- | :--- |
| **L1 Bounded LRU (`5–30s` TTL)** | Eventual across pods | `< 0.05ms` | Safe ONLY with `maxEntries` | JWKS keys, tenant plan flags, tiny lookup maps |
| **L2 Redis Cache-Aside + `UNLINK` on Write** | High (near-immediate post-commit) | `0.5–2ms` | Safe with `allkeys-lfu` + TTL | Entity details, user profiles, dashboard aggregates |
| **O(1) Generation Counter Prefix** | Immediate logical purge | `+1` fast `GET` | Safe (old keys expire via TTL) | Paginated/filtered lists without `KEYS *` |
| **Write-Through to Redis Before DB Commit** | **BROKEN on rollback** | Medium | High stale-corruption risk | **AVOID** — always commit DB first! |

## 7. Real Production Scenario
A B2B ERP deployed an order-list Redis cache under key `orders:list:page=1` and ran `KEYS orders:list:*` on every order save. Within 2 hours, two severe incidents struck simultaneously: Tenant B saw Tenant A's invoices in production, and Redis latency spiked to `4.2s` during bulk imports because `KEYS` froze the single-threaded event loop. Migrating to `prod:tenant_{id}:orders:v2:g{gen}:...` with `INCR` generation invalidation and blocking unpartitioned keys via `cache_policy_verifier.py` eliminated both cross-tenant leaks and Redis stalls permanently.

## 8. Failure Modes & Edge Cases
- **WRONG:** Deleting Redis cache *before* committing the SQL transaction (a concurrent reader immediately repopulates Redis with the *old* uncommitted row, leaving stale data stuck until TTL expires!).
  **RIGHT:** Commit the DB transaction first, THEN `UNLINK` the cache key (and for ultra-high-contention rows, optionally schedule a delayed second delete or use short TTL + DB outbox invalidation).
- **WRONG:** Sharing one Redis instance with `allkeys-lru` for both API cache AND BullMQ/Sidekiq queues.
  **RIGHT:** Separate ephemeral cache (`allkeys-lfu`) from durable queues/locks (`noeviction`).
- **WRONG:** Storing `10MB` unpaginated tenant JSON blobs inside a single Redis string ("big key" blocks network I/O and stalls all other tenants on that shard).
  **RIGHT:** Cap cached values (`< 100KB`), compress large safe payloads if needed, or cache compact normalized projections / paginated slices.

## 9. Testing & Verification
- Run `python shadow-cache/scripts/cache_policy_verifier.py --check-cache-config cache_policy.json` in CI.
- Add multi-tenant isolation integration tests: seed Tenant A and Tenant B with identical entity IDs or list queries, warm cache for Tenant A, fetch as Tenant B, and assert zero cross-tenant bleed.
- Chaos-test Redis outage in staging (`shadow-resilience`): block Redis port and verify API falls back gracefully with bounded DB load instead of throwing unhandled `ECONNREFUSED` 500s.

## 10. Operational Considerations
- Monitor Redis `keyspace_hits / (keyspace_hits + keyspace_misses)`, `evicted_keys`, `used_memory_rss / maxmemory`, and slowlog (`SLOWLOG GET 10`). A hit ratio `< 70%` on a hot cache usually signals over-fragmented keys or undersized `maxmemory`.
- Avoid unversioned `JSON.parse` without runtime schema validation (Zod/Valibot) when reading cached payloads — treat cache corruption or schema drift as a clean cache miss (delete & reload from DB).

## 11. Authoritative References
- Redis / Valkey Documentation — *Key Eviction (`maxmemory-policy`), `UNLINK`, Client-Side Caching & Key Naming*.
- Facebook Engineering — *Scaling Memcache at Facebook* (NSDI — Lease/Delete-on-Write coherency lessons).

## 12. Limitations & When NOT to Use
- Do NOT cache security-critical authorization decisions (revoked JWTs, suspended accounts) for minutes without an immediate revocation hook (`/shadow-auth`).
- Do NOT put Redis in front of simple primary-key PostgreSQL lookups that already return in `1–2ms` with plenty of DB headroom — unnecessary caching adds invalidation bugs for negligible latency gain.
