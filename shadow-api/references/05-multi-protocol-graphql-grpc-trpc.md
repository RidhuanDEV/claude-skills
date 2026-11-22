# 05. Multi-Protocol APIs: GraphQL, gRPC & tRPC

## 1. Purpose & Activation Conditions
Choose and harden non-REST API protocols — **GraphQL**, **gRPC / Protobuf / ConnectRPC**, and **tRPC** — preventing GraphQL N+1 / depth-bomb DoS, Protobuf breaking wire numbers, and cross-team coupling. Load when designing or auditing GraphQL schemas, gRPC services, or monorepo tRPC routers.

## 2. Prerequisites
- Clear consumer profile (public partners vs internal microservices vs single-repo TypeScript frontend) and AuthZ boundary (`shadow-auth`).

## 3. Technical Principles & Constraints
- **Protocol Selection Discipline:**
  - **REST (OpenAPI 3.1):** Default for public/partner APIs, HTTP CDN caching, webhooks, and polyglot clients.
  - **GraphQL:** Choose ONLY when diverse UI clients genuinely need flexible graph projections across nested relations — NEVER for simple flat CRUD!
  - **gRPC / ConnectRPC (Protobuf):** Choose for high-throughput internal service-to-service RPC, bidirectional streaming, or strict polyglot binary contracts.
  - **tRPC:** Choose strictly inside a **single TypeScript monorepo** with tightly coupled frontend + backend (NEVER expose tRPC as a public third-party API!).
- **Mandatory GraphQL Hardening Rules:**
  1. **Zero N+1 Queries:** Instantiate a fresh **per-request `DataLoader`** batching context on every HTTP request (never share a global DataLoader across users/tenants — causes cross-tenant cache bleed!).
  2. **Depth + Complexity/Cost Bounds:** Enforce hard max query depth (`<= 7`), max alias count, and query-cost budget BEFORE execution (blocks cyclic `user { friends { friends { ... } } }` DoS!).
  3. **Production Introspection & Persisted Queries:** Disable public schema introspection in production (or gate to authenticated developers) and prefer **Persisted Queries** for public apps.
  4. **Field-Level Authorization:** Check tenant/permission guards inside resolvers/domain services, NOT just on top-level query entry points.
- **Mandatory gRPC / Protobuf Rules:**
  1. **NEVER reuse deleted or renamed field tag numbers** — mark removed tags `reserved 4, 5;` and `reserved "old_field";` so wire decoding never silently corrupts older clients.
  2. Run `buf lint` and `buf breaking` in CI against `main`.
  3. Require explicit per-call **deadlines/timeouts** and W3C `traceparent` metadata propagation on every RPC.

## 4. Architecture & Implementation
```typescript
// Per-Request Tenant-Scoped DataLoader Factory (Prevents BOTH N+1 AND Cross-Tenant Cache Bleed)
export interface TenantBatchLoader<K, V> {
  load(key: K): Promise<V | null>;
}

export function createScopedBatchLoader<V>(
  tenantId: string,
  batchFetch: (tenantId: string, keys: readonly string[]) => Promise<ReadonlyMap<string, V>>
): TenantBatchLoader<string, V> {
  const pendingKeys: string[] = [];
  const cache = new Map<string, Promise<V | null>>();
  let scheduled = false;
  const resolvers = new Map<string, { readonly resolve: (val: V | null) => void; readonly reject: (err: unknown) => void }>();

  const flush = async (): Promise<void> => {
    scheduled = false;
    const keysToFetch = pendingKeys.splice(0, pendingKeys.length);
    try {
      const results = await batchFetch(tenantId, keysToFetch);
      for (const k of keysToFetch) {
        resolvers.get(k)?.resolve(results.get(k) ?? null);
        resolvers.delete(k);
      }
    } catch (err: unknown) {
      for (const k of keysToFetch) {
        resolvers.get(k)?.reject(err);
        resolvers.delete(k);
      }
    }
  };

  return {
    load(key: string): Promise<V | null> {
      const cached = cache.get(key);
      if (cached) return cached;
      const promise = new Promise<V | null>((resolve, reject) => {
        pendingKeys.push(key);
        resolvers.set(key, { resolve, reject });
        if (!scheduled) {
          scheduled = true;
          queueMicrotask(() => void flush());
        }
      });
      cache.set(key, promise);
      return promise;
    },
  };
}
```
Safe Protobuf evolution example (`reserved` protects wire compatibility):
```protobuf
syntax = "proto3";
package orders.v1;

message OrderSummary {
  string id = 1;
  string tenant_id = 2;
  int64 total_minor = 3;
  reserved 4;
  reserved "legacy_float_price";
  string currency = 5;
}
```

## 5. Platform / Vendor Variations
| Protocol | Schema / Breaking-Change Linter | Caching Nuance |
| :--- | :--- | :--- |
| **REST** | `redocly lint` / `spectral` / `api_contract_verifier.py` | Native HTTP `ETag`, `Cache-Control`, CDN edge caching |
| **GraphQL** | `graphql-inspector diff` + `graphql-armor` (depth/alias/cost) | `POST` bodies bypass standard HTTP caches; requires APQ (`GET`) or resolver cache |
| **gRPC / ConnectRPC** | `buf lint` + `buf breaking` | ConnectRPC supports HTTP/1.1 JSON + browser fetch natively alongside gRPC binary |
| **tRPC** | TypeScript compiler (`tsc --noEmit`) | Zero runtime contract for non-TS clients; add OpenAPI adapter if external consumers appear |

## 6. Decision Matrix & Trade-Offs
| Criterion | REST (OpenAPI 3.1) | GraphQL | gRPC / ConnectRPC | tRPC |
| :--- | :---: | :---: | :---: | :---: |
| **Public / Partner APIs** | **Best** | Moderate (high abuse surface) | Low (browser/proxy friction) | **Avoid** |
| **Complex Nested UI Views** | Multiple calls / BFF | **Best** | Low | Good (TS monorepo) |
| **High-Throughput Internal RPC** | Good | Poor | **Best** | TS-only |
| **HTTP Edge Caching** | **Native** | Complex | Complex | Limited |

## 7. Real Production Scenario
A B2B portal exposes GraphQL without depth limits or DataLoader. An attacker sends a 12-level nested query `organization { projects { tasks { comments { author { projects { ... } } } } } }` with 30 aliases in one HTTP request, spawning 18,000 SQL queries and exhausting the Postgres connection pool in 4 seconds. Adding `graphql-armor` (max depth `6`, max aliases `15`, cost limit `500`), per-request tenant-scoped DataLoaders, and persisted queries neutralizes the attack and reduces p95 query latency by 82%.

## 8. Failure Modes & Edge Cases
- **WRONG:** Instantiating a `DataLoader` at module scope (shared across incoming requests -> leaks Tenant A's cached rows straight into Tenant B's response!).
- **RIGHT:** Create DataLoaders strictly per request inside request context scoped to `actor.tenantId`.
- **WRONG:** Deleting field `4` in `.proto` and immediately assigning a new string field to tag `4` (old clients decode bytes into the wrong type!).
- **RIGHT:** Always `reserved 4;` and allocate a fresh tag number (`5`) for new fields.

## 9. Testing & Verification
- Add negative GraphQL tests asserting depth `> 7`, alias flooding (`> 15`), and unauthorized nested fields return structured refusal errors without hitting the DB.
- Run `buf breaking` on every `.proto` PR and verify gRPC calls enforce non-zero deadlines.

## 10. Operational Considerations
- Log GraphQL operation names (`operationName`) and normalized gRPC method names in structured telemetry (`07`) rather than raw `POST /graphql` (otherwise all GraphQL traffic collapses into one blind metric bucket!).

## 11. Authoritative References
- GraphQL Specification & Security Guidance (`https://spec.graphql.org/`, OWASP GraphQL Cheat Sheet).
- Buf / Protocol Buffers Language Guide (`https://protobuf.dev/programming-guides/proto3/`).

## 12. Limitations & When NOT to Use
- Do NOT adopt GraphQL Federation across 2 small teams merely to avoid writing 5 clean REST endpoints — federation introduces significant gateway, caching, and authorization complexity.
