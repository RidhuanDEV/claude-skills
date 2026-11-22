# React & Next.js Performance Engineering (Eliminating Waterfalls, Bundle & RSC)

> Distilled from verified 1st-party React/Next.js performance engineering patterns (`vercel-labs/agent-skills` `react-best-practices`). Load when building or optimizing React/Next.js Server Components, async data loaders, bundle budgets, or client re-render bottlenecks.

## 1. Core Concepts
Frontend latency in modern React/Next.js applications is dominated by two **CRITICAL-priority** bottlenecks before micro-optimizations even matter:
- **Sequential Async Waterfalls:** Awaiting independent fetches (`user`, `permissions`, `stats`) sequentially multiplies network RTT linearly (`3 × 120ms = 360ms`) instead of running concurrently (`120ms`).
- **Bundle & RSC Boundary Bloat:** Importing from barrel re-export files (`import { Icon } from "huge-lib"`) or passing entire ORM entities across the Server-to-Client boundary inflates initial JS parse time, TTI, and hydration payload.

## 2. Technical Rules & Decision Matrix

| Priority | Bottleneck Category | Concrete Pattern | Measurable Impact |
| :--- | :--- | :--- | :--- |
| **CRITICAL** | Sequential Async Fetches (`async-parallel`) | Launch independent promises immediately (`Promise.all`) or start early & `await` late (`async-defer-await`) | Cuts SSR/API TTFB by `2x–5x` |
| **CRITICAL** | Streaming Slow Subtrees (`async-suspense-boundaries`) | Wrap slow secondary panels in `<Suspense fallback={<Skeleton />}>` instead of blocking top-level `page.tsx` | Unblocks hero LCP immediately |
| **CRITICAL** | Barrel & Heavy Component Bloat (`bundle-barrel-imports`) | Import concrete module paths (`lucide-react/dist/esm/icons/...` or bundler `optimizePackageImports`) + lazy-load heavy modals/charts/editors (`next/dynamic` / `React.lazy`) | Cuts initial JS bundle by `30–70%` |
| **HIGH** | RSC Serialization & Request Dedup (`server-cache`) | Wrap shared per-request loaders in `React.cache()`; pass ONLY minimal DTO fields to `"use client"` components; authenticate INSIDE every Server Action | Prevents duplicate DB hits & data leaks |
| **MEDIUM** | Derived State & Re-Render Loops | Compute derived values inline during render (not `useEffect` + `setState` cascades); use functional state updates `setCount((c) => c + 1)` | Eliminates extra commit passes & INP jank |

## 3. Implementation Examples

### Eliminating Async Waterfalls + Per-Request `React.cache()` + Minimal RSC DTO
```tsx
import { cache } from "react";

export interface UserSummaryDto {
  readonly id: string;
  readonly displayName: string;
  readonly role: "ADMIN" | "MEMBER";
}

// Per-request deduplication across layout + page + nested server components
export const getCurrentUser = cache(async (userId: string): Promise<UserSummaryDto | null> => {
  const row = await dbFindUser(userId);
  if (!row) return null;
  // Pass ONLY minimal safe DTO across the Server -> Client serialization boundary
  return { id: row.id, displayName: row.displayName, role: row.role };
});

export async function loadDashboardData(userId: string, includeAudit: boolean) {
  // Start independent async work immediately in parallel (zero waterfall)
  const userPromise = getCurrentUser(userId);
  const metricsPromise = dbLoadMetrics(userId);
  const auditPromise = includeAudit ? dbLoadRecentAudit(userId) : Promise.resolve([]);

  const [user, metrics, audit] = await Promise.all([userPromise, metricsPromise, auditPromise]);
  return { user, metrics, audit };
}
```

### Deferring Heavy Client Modules (`dynamic` / `lazy`) & Avoiding `useEffect` Sync Chains
```tsx
import dynamic from "next/dynamic";

// Heavy charting / rich-text editor loaded ONLY when rendered (never in initial critical bundle)
const AnalyticsChart = dynamic(() => import("./AnalyticsChart"), {
  ssr: false,
  loading: () => <div className="h-64 animate-pulse rounded-lg bg-muted" aria-busy="true" />,
});

// Derive filtered list during render instead of useState + useEffect double-render
export function OrderList({ orders, statusFilter }: { readonly orders: readonly OrderItem[]; readonly statusFilter: string }) {
  const visibleOrders = statusFilter === "ALL" ? orders : orders.filter((o) => o.status === statusFilter);
  return <section>{visibleOrders.length} orders <AnalyticsChart /></section>;
}
```

## 4. Best Practices
- Defer non-blocking post-response side effects (analytics flush, audit logging, cache warming) with framework background APIs (`next/server` `after()`) so user responses return immediately.
- Verify bundle sizes and Core Web Vitals (`LCP`, `INP`, `CLS`) empirically with build analyzer output + Chrome DevTools / Lighthouse rather than guessing.
- Treat every Next.js **Server Action** as a public HTTP `POST` endpoint: validate inputs with a schema and re-verify session/RBAC ownership server-side inside the action itself.

## 5. Anti-Patterns (`WRONG` vs `RIGHT`)
- **WRONG (Sequential waterfall + leaking full DB rows to client components):**
  ```ts
  const user = await getUser(id);         // waits 100ms
  const orders = await getOrders(id);     // waits another 120ms unnecessarily
  const billing = await getBilling(id);   // waits another 90ms (total 310ms!)
  ```
  **RIGHT:** Launch independent fetches concurrently via `Promise.all([getUser(id), getOrders(id), getBilling(id)])` and serialize only narrow DTO fields into `"use client"` props.
- **WRONG (Barrel imports pulling entire 200KB+ packages & `useEffect` state mirroring):** Importing `{ ChevronRight } from "@/components/ui"` (mega barrel re-exporting charts/editors) or using `useEffect(() => setFiltered(items.filter(...)), [items])`.
  **RIGHT:** Import direct component paths (or enable `optimizePackageImports`), dynamically load heavy widgets, and compute derived values directly in render.

## 6. Production Considerations
- **Hydration & Streaming Safety:** Pair `<Suspense>` boundaries with fixed-height skeletons matching final layout geometry so streaming never causes CLS layout shifts.
- **Auth in Server Actions:** Never rely solely on middleware or UI hiding to guard Server Actions — enforce server-side authentication and tenant authorization inside every action body (`/shadow-auth`).
