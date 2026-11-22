# 03. Pagination, Filtering & Sorting

## 1. Purpose & Activation Conditions
Design high-performance, deterministic collection endpoints using keyset/cursor pagination, bounded page limits, safe filter/sort allowlists, and stable tie-breakers. Load when building list/search endpoints or diagnosing slow `OFFSET` queries and duplicate/missing rows during paging.

## 2. Prerequisites
- Composite database index matching the exact `(tenant_id, sort_col DESC, id DESC)` predicate (`/shadow-db`).

## 3. Technical Principles & Constraints
- **Hard Page-Size Ceiling (`OWASP API4:2023`):** Every collection endpoint MUST enforce a validated maximum page size (default `20`, hard cap `limit <= 100`). Unbounded `GET /orders` or `?limit=99999` is a trivial Memory/DB Denial-of-Service vector.
- **Keyset (Cursor) Pagination Default for Feeds & Large Tables:**
  - `OFFSET 500000` forces Postgres/MySQL to scan and discard 500,000 rows (`O(N)` degradation) AND produces **duplicate or skipped items** whenever rows are inserted/deleted between pages!
  - Keyset pagination queries `WHERE (created_at, id) < ($cursorTs, $cursorId) ORDER BY created_at DESC, id DESC LIMIT $limit + 1` in **`O(log N)` constant time** with zero drift.
  - Always include a **strictly unique tie-breaker** (`id`) in BOTH `ORDER BY` and the cursor tuple so rows sharing the exact same `created_at` millisecond are never skipped!
  - Encode cursors as **opaque base64url JSON** (optionally HMAC-signed if tamper sensitivity matters) so clients treat cursors as black boxes and never depend on internal column names.
- **Strict Allowlist for `sort` and `filter` Fields:** NEVER interpolate user query strings (`?sort=users;DROP...`) into SQL `ORDER BY` or `WHERE` clauses. Map allowed sort keys through a static `Record<AllowedSortKey, string>` dictionary and bound filter array sizes (`<= 50` IDs).

## 4. Architecture & Implementation
```typescript
export interface CursorPayload {
  readonly createdAtIso: string;
  readonly id: string;
}

export function encodeCursor(cursor: CursorPayload): string {
  return Buffer.from(JSON.stringify(cursor), 'utf8').toString('base64url');
}

export function decodeCursor(raw: string): CursorPayload | null {
  try {
    const parsed: unknown = JSON.parse(Buffer.from(raw, 'base64url').toString('utf8'));
    if (typeof parsed !== 'object' || parsed === null) return null;
    const ts = 'createdAtIso' in parsed && typeof parsed.createdAtIso === 'string' ? parsed.createdAtIso : null;
    const id = 'id' in parsed && typeof parsed.id === 'string' ? parsed.id : null;
    if (!ts || !id || Number.isNaN(Date.parse(ts))) return null;
    return { createdAtIso: ts, id };
  } catch {
    return null;
  }
}

export function clampPageLimit(rawLimit: unknown, defaultLimit = 20, maxLimit = 100): number {
  const n = typeof rawLimit === 'number' ? rawLimit : Number.parseInt(String(rawLimit ?? ''), 10);
  if (!Number.isFinite(n) || n < 1) return defaultLimit;
  return Math.min(Math.floor(n), maxLimit);
}
```
Indexed keyset query in PostgreSQL (`LIMIT $limit + 1` trick avoids expensive `COUNT(*)` on every page!):
```sql
-- Matching index: CREATE INDEX idx_orders_tenant_created_id ON orders (tenant_id, created_at DESC, id DESC);
SELECT id, status, total_minor, created_at
FROM orders
WHERE tenant_id = $1
  AND ($2::timestamptz IS NULL OR (created_at, id) < ($2::timestamptz, $3::uuid))
ORDER BY created_at DESC, id DESC
LIMIT $4; -- Pass limit + 1; if rows.length > limit -> hasMore = true and slice(0, limit)
```

## 5. Platform / Vendor Variations
| Pagination Style | Deep-Page Performance | Arbitrary Page Jump (`Page 14`) | Best Fit |
| :--- | :---: | :---: | :--- |
| **Keyset / Cursor (`after`, `limit`)** | **`O(log N)` constant** | No (Next/Prev only) | Infinite scroll, feeds, transactions, logs, partner APIs |
| **Bounded Offset (`page`, `limit <= 100`)** | Degrades past page ~100 | Yes | Small admin tables (`< 10k` rows) where jump-to-page is explicitly required |
| **Search PIT / `search_after`** | Constant across shards | No | Elasticsearch / OpenSearch (`/shadow-search`) |

## 6. Decision Matrix & Trade-Offs
| Feature | Include by Default? | Performance Impact | Recommendation |
| :--- | :---: | :---: | :--- |
| **`hasMore` via `LIMIT + 1`** | **YES** | Zero extra query | Standard on all cursor APIs |
| **Exact `totalCount` (`COUNT(*)`)** | No (opt-in or capped) | Full index/table scan on millions of rows | Omit on feeds; use estimated/capped count (`1000+`) on huge tables |
| **Dynamic Multi-Column `sort`** | Only allowlisted pairs | Unindexed sort causes disk temp spill | Allowlist 2–4 indexed sort presets only |

## 7. Real Production Scenario
An e-commerce admin portal lists `orders` with `OFFSET` pagination and computes `SELECT COUNT(*) FROM orders WHERE tenant_id = $1` on every scroll. At 4 million rows, page 500 takes `6.8 seconds` and new incoming orders shift rows so operators accidentally approve the same order twice across page boundaries. Switching to keyset pagination with `(created_at DESC, id DESC)` and `LIMIT + 1` drops p95 latency from `6.8s` to `9ms` and eliminates row-shift duplicates.

## 8. Failure Modes & Edge Cases
- **WRONG:** Sorting by `ORDER BY created_at DESC` WITHOUT a unique `id` tie-breaker (two rows inserted in the same millisecond silently vanish or repeat across cursor pages!).
- **RIGHT:** Always pair non-unique sort columns with the primary key tie-breaker `(created_at DESC, id DESC)`.
- **WRONG:** Accepting malformed base64 cursors and crashing with HTTP `500`.
- **RIGHT:** Validate decoded cursor shape strictly and return RFC 9457 `400 Bad Request` (`invalid-cursor`) on malformed tokens.

## 9. Testing & Verification
- Test pagination invariants: (1) `limit=500` rejected/clamped `<= 100`, (2) 3 rows sharing identical `created_at` paginate across page size `2` with zero duplicates and zero skips, (3) malformed cursor returns `400` problem+json, (4) invalid `sort=password_hash` returns `400`.
- Run `python shadow-api/scripts/api_contract_verifier.py --check-openapi-contract <spec.json>`.

## 10. Operational Considerations
- Verify every allowlisted sort/filter combination against `EXPLAIN (ANALYZE, BUFFERS)` (`/shadow-db`) before shipping to ensure index scans instead of sequential sorts.

## 11. Authoritative References
- OWASP API Security Top 10 (2023) — `API4:2023` (*Unrestricted Resource Consumption*).
- Use The Index, Luke! — *We Need Tooling for Keyset Pagination* (`https://use-the-index-luke.com/no-offset`).
- Stripe API Design — *Cursor Pagination (`starting_after` / `has_more`)*.

## 12. Limitations & When NOT to Use
- Keyset pagination does not support arbitrary `"Jump to page 37"` UI controls; if a small back-office report (`< 5,000` rows) genuinely needs page numbers, use bounded offset pagination with a hard maximum page cap and explicit tie-breaker.
