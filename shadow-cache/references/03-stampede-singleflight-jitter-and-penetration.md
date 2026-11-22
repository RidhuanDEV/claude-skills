# 03 — Stampede Defense (Singleflight, Probabilistic Early Refresh, Jitter) & Anti-Penetration

## 1. Purpose & Activation Conditions
Protect backend databases and upstream APIs from the three catastrophic cache failure modes — **Cache Stampede (Thundering Herd / Hot-Key Breakdown)**, **Cache Avalanche (Synchronized Mass Expiration)**, and **Cache Penetration (Non-Existent Key Flooding)** — using Singleflight coalescing, distributed mutex / logical stale-while-revalidate, randomized TTL jitter, negative caching sentinels, and Bloom filters. Activate when caching expensive aggregations, dashboards, flash-sale catalogs, or public ID lookup endpoints.

## 2. Prerequisites
- Partitioned, versioned L2 Redis cache (`02-redis-l1-l2-and-tenant-partitioning.md`).
- Identified hot keys (`p99` request concentration) and slow loaders (`> 50ms` SQL/API cost).

## 3. Technical Principles & Constraints
- **Three Distinct Failure Modes Require Three Distinct Defenses:**
  1. **Cache Stampede (Hot-Key Breakdown):** ONE very hot key expires while 1,000 concurrent requests arrive -> all 1,000 miss and execute the same heavy SQL query simultaneously. **Defense:** In-process **Singleflight** request coalescing + cross-replica **distributed mutex / logical soft-TTL (Stale-While-Revalidate)** or **Probabilistic Early Expiration (XFetch)**.
  2. **Cache Avalanche:** 50,000 bulk-warmed keys share identical `EX 3600` (e.g., midnight cron warm-up) -> all 50,000 expire at `01:00:00` sharp -> DB collapses. **Defense:** Random **TTL Jitter** (`baseTtl * (1 ± 0.15)`), staggered warm-up, and Redis cluster high availability + circuit breaker.
  3. **Cache Penetration:** Bots/attackers request 100,000 random non-existent IDs (`/products/fake-99999`) -> every request misses Redis AND queries the DB -> DB CPU hits 100%. **Defense:** Strict input/UUID validation at edge + short-TTL **Negative Caching** (`"__NOT_FOUND__"` sentinel with `EX 30–60` + jitter) and/or a **Bloom Filter** for massive public ID spaces.
- **Prevent Error Poisoning Inside Singleflight:** If the shared leader Promise rejects (transient DB blip), clean up the in-flight map entry inside `.finally()` IMMEDIATELY so callers do NOT get pinned to a cached rejected Promise forever — and NEVER cache `5xx` transient errors as `"__NOT_FOUND__"`! Only cache verified domain `NOT_FOUND` results.
- **Logical Soft-TTL (Background Stale-While-Revalidate) For Ultra-Hot Keys:** Store `{ value, softExpiresAt }` in Redis with physical `EX = softTtl * 3`. When `now > softExpiresAt`, return the slightly stale value instantly to 999 callers while ONLY the 1 replica acquiring `SET lockKey 1 NX EX 10` refreshes the DB in the background — eliminating tail-latency spikes at expiry completely!

## 4. Architecture & Implementation

```ts
// Strict TypeScript Singleflight + Jittered TTL + Negative Caching Sentinel + Soft-TTL SWR (0 any, 0 casts)
export const NOT_FOUND_SENTINEL = '__NOT_FOUND__' as const

export interface SwrEnvelope<T> {
  readonly payload: T | typeof NOT_FOUND_SENTINEL
  readonly softExpiresAtMs: number
}

export function computeJitteredTtlSec(baseTtlSec: number, jitterRatio = 0.15, rand: () => number = Math.random): number {
  if (baseTtlSec <= 0) {
    throw new Error('baseTtlSec must be positive')
  }
  const boundedJitter = Math.min(0.4, Math.max(0, jitterRatio))
  const delta = baseTtlSec * boundedJitter * (rand() * 2 - 1)
  return Math.max(1, Math.round(baseTtlSec + delta))
}

export async function runSingleflight<T>(
  key: string,
  loader: () => Promise<T>,
  inFlight: Map<string, Promise<T>>,
): Promise<T> {
  const existing = inFlight.get(key)
  if (existing) {
    return existing
  }
  const promise = loader().finally(() => {
    inFlight.delete(key)
  })
  inFlight.set(key, promise)
  return promise
}

// Probabilistic Early Expiration (XFetch): refreshes hot keys slightly before expiry without locks
export function shouldRefreshEarlyXFetch(
  remainingTtlMs: number,
  lastComputeDeltaMs: number,
  beta = 1.0,
  rand: () => number = Math.random,
): boolean {
  if (remainingTtlMs <= 0) return true
  const u = Math.max(1e-9, rand())
  const threshold = -lastComputeDeltaMs * beta * Math.log(u)
  return threshold >= remainingTtlMs
}

export interface RedisCacheClient {
  get(key: string): Promise<string | null>
  setEx(key: string, ttlSec: number, value: string): Promise<void>
  acquireLockNx(lockKey: string, ttlSec: number): Promise<boolean>
}

export async function loadWithNegativeCacheAndSingleflight<T>(opts: {
  readonly cacheKey: string
  readonly redis: RedisCacheClient
  readonly inFlight: Map<string, Promise<T | null>>
  readonly hitTtlSec: number
  readonly negativeTtlSec: number
  readonly parse: (raw: string) => T | null
  readonly serialize: (val: T) => string
  readonly loadFromDb: () => Promise<T | null>
}): Promise<T | null> {
  const cached = await opts.redis.get(opts.cacheKey)
  if (cached === NOT_FOUND_SENTINEL) {
    return null
  }
  if (cached !== null) {
    const parsed = opts.parse(cached)
    if (parsed !== null) return parsed
  }

  return runSingleflight(
    opts.cacheKey,
    async () => {
      const value = await opts.loadFromDb()
      if (value === null) {
        const negTtl = computeJitteredTtlSec(opts.negativeTtlSec, 0.2)
        await opts.redis.setEx(opts.cacheKey, negTtl, NOT_FOUND_SENTINEL)
        return null
      }
      const hitTtl = computeJitteredTtlSec(opts.hitTtlSec, 0.15)
      await opts.redis.setEx(opts.cacheKey, hitTtl, opts.serialize(value))
      return value
    },
    opts.inFlight,
  )
}
```

## 5. Platform/Vendor Variations
- **Go (`golang.org/x/sync/singleflight`):** First-class stdlib-adjacent `singleflight.Group` with `Do(key, fn)` and `Forget(key)` — watch out for shared context cancellation (detach loader timeout from the first caller's `req.Context()` so if Caller #1 disconnects after 50ms, Callers #2–#500 don't all get canceled!).
- **Redis Stack / Valkey Bloom Filter (`BF.ADD`, `BF.EXISTS`):** For public catalogs with `> 10M` SKUs under heavy scraper/scanner traffic, check a Bloom filter before touching PostgreSQL; remember standard Bloom filters do NOT support deletes (rebuild periodically or use Cuckoo filter / short negative cache).
- **Multi-Replica Distributed Coalescing:** In-process Singleflight collapses 1,000 requests on 1 pod into 1 DB call (so 10 pods = at most 10 DB calls — already a 100x reduction!). Only add Redis distributed lock (`SET lockKey token NX PX 5000`) + jittered sleep retry or logical Soft-TTL SWR when even 10 concurrent DB queries would overload PostgreSQL.

## 6. Decision Matrix & Trade-Offs

| Defense Mechanism | Solves | Complexity | Latency at Expiry | Best Use Case |
| :--- | :--- | :--- | :--- | :--- |
| **In-Process Singleflight** | Stampede (within pod) | Very Low | Waits for 1 leader | Default on every expensive L2 cache miss |
| **TTL Jitter (`±10–20%`)** | Avalanche (mass expiry) | Trivial | Smooth spread | Mandatory on all bulk-warmed / high-traffic keys |
| **Soft-TTL + Background Refresh (SWR)** | Stampede (multi-pod) + Zero p99 spike | Medium | **Zero spike** (serves stale) | Flash-sale homepage, executive KPI dashboards |
| **Probabilistic Early Expiration (XFetch)** | Stampede (lock-free!) | Low–Medium | Near-zero | High-QPS read-heavy keys with predictable compute time |
| **Negative Caching (`__NOT_FOUND__`, `30–60s`)** | Penetration (missing IDs) | Low | Fast hit | Public `/products/:id`, `/users/:slug`, API lookup endpoints |
| **Bloom Filter (`BF.EXISTS`)** | Massive random-ID penetration | Medium | Sub-ms rejection | `> 10M` sparse ID spaces under hostile bot scanning |

## 7. Real Production Scenario
A national news & e-commerce portal warmed 25,000 category cache keys at `00:00 WIB` with fixed `EX 3600`. Every hour on the hour (`01:00`, `02:00`, `03:00`), PostgreSQL CPU spiked to `100%` for 45 seconds as thousands of requests missed simultaneously; meanwhile, an SEO scraper probing 80,000 deleted article slugs caused 1,400 DB `SELECT` misses/second. Adding `±15%` TTL jitter, Singleflight coalescing on miss loaders, and a `45s` `"__NOT_FOUND__"` sentinel dropped DB peak CPU from `100%` to `19%` and cut API p99 from `3.4s` to `48ms`.

## 8. Failure Modes & Edge Cases
- **WRONG:** Caching a `"__NOT_FOUND__"` sentinel when PostgreSQL throws a connection timeout or `503` error (turns a 2-second DB hiccup into a 60-second false `404` outage for valid products!).
  **RIGHT:** Catch transient DB/network errors and propagate/degrade WITHOUT writing the negative sentinel; write `"__NOT_FOUND__"` ONLY when the DB definitively returns 0 rows.
- **WRONG:** Caching `"__NOT_FOUND__"` with a `24-hour` TTL (when an admin creates that newly requested SKU 5 minutes later, customers keep seeing `404` for a day!).
  **RIGHT:** Keep negative cache TTL short (`30–60s` + jitter) AND delete the key upon entity creation (`POST`) after DB commit.
- **WRONG:** Binding the shared Singleflight DB loader directly to Caller #1's HTTP `AbortSignal` / `context.Context`.
  **RIGHT:** Give the shared Singleflight loader its own bounded server timeout (`AbortSignal.timeout(5000)`) so one impatient mobile client closing its tab does not fail 200 coalesced callers!

## 9. Testing & Verification
- Run `python shadow-cache/scripts/cache_policy_verifier.py --check-cache-config cache_policy.json` to assert `singleflight`/`swr` on expensive loaders and `jitter_ratio > 0` on bulk-warmed/hot keys.
- Write a concurrency unit test firing `Promise.all(Array.from({ length: 100 }, () => load()))` against a mocked slow DB (`50ms`) and assert `dbCallCount === 1` and all 100 callers receive identical valid data; run a second test asserting `dbCallCount === 1` when `loadFromDb` returns `null` (negative sentinel cached) and `dbCallCount === 2` when `loadFromDb` throws a transient error (no error poisoning).

## 10. Operational Considerations
- Monitor `cache_negative_hits_total` alongside `cache_misses_total` — a sudden spike in negative hits is an early warning of an active scraping/enumeration attack (coordinate WAF/rate limiting with `/shadow-sec` and `/shadow-api`).
- Ensure background Soft-TTL refresh failures log structured warnings (`shadow-observe`) and never leave stale data pinned indefinitely past the outer hard physical TTL.

## 11. Authoritative References
- Vattani, Chierichetti & Lowenstein (VLDB 2015) — *Optimal Probabilistic Cache Stampede Prevention (XFetch)*.
- Go Standard Library (`x/sync/singleflight`) — Request Coalescing Design.
- Redis Labs Engineering — *Cache Penetration, Breakdown & Avalanche Patterns*.

## 12. Limitations & When NOT to Use
- Do NOT use Singleflight across callers with **different tenant/user permissions** unless the Singleflight key itself contains the exact `tenantId` + permission scope — otherwise Caller #2 receives Caller #1's privileged payload!
- Do NOT use Soft-TTL stale serving for strong-consistency financial balances, auth revocation, or inventory lock checks.
