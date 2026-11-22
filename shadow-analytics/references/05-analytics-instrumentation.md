# 05. Analytics Instrumentation

## 1. Purpose & Activation Conditions
Architect reliable, low-latency, ad-blocker-resilient analytics collection across client SDKs, first-party reverse proxies, and server-side event pipelines (PostHog, GA4, Mixpanel, or custom ingest). Load when choosing client vs server instrumentation, configuring a first-party `/ingest` proxy, preventing unload event loss, or filtering bot/QA traffic.

## 2. Prerequisites
- Typed tracking plan (`02-event-taxonomy-and-tracking-plans.md`), identity rules (`03-identity-resolution.md`), and consent gate (`04-privacy-and-consent-architecture.md`).

## 3. Technical Principles & Constraints
- **Hybrid Split of Truth (Non-Negotiable):**
  - **Server-Side Truth:** Emit ALL business-critical, financial, subscription, and state-transition events (`Order_Completed`, `Payment_Succeeded`, `Subscription_Canceled`, `Account_Created`) directly from your backend/outbox. Browser ad-blockers, network drops, and closed tabs routinely drop **10%–30%** of client-side events.
  - **Client-Side Behavioral Telemetry:** Emit UI interactions (`Page_Viewed`, `Search_Queried`, `Filter_Applied`, `Experiment_Exposed`) from web/mobile SDKs routed through a **first-party reverse proxy** (e.g., `https://app.example.com/ingest` with non-generic path if needed, respecting user consent and Do-Not-Track policies — NEVER to bypass explicit consent refusal).
- **Non-Blocking Transport & Unload Reliability:** Never block user navigation (`await fetch(...)`) on analytics. Batch events client-side, flush on `visibilitychange` (`hidden`) using `navigator.sendBeacon()` or `fetch(..., { keepalive: true })`, and enforce strict payload/timeout budgets on server SDKs so an analytics outage NEVER degrades checkout latency.
- **Bot, Crawler & QA Hygiene:** Filter known search/monitoring bots (`Googlebot`, `UptimeRobot`, headless CI runners) and internal staging/QA environments (`env !== 'production'`) at ingestion so funnels and A/B denominators remain unpolluted.

## 4. Architecture & Implementation
```typescript
export interface AnalyticsTransport {
  sendBatch(events: readonly Record<string, unknown>[]): Promise<void>;
}

export class ResilientServerAnalytics {
  private readonly queue: Record<string, unknown>[] = [];
  private readonly maxBatchSize: number;
  private readonly maxQueueSize: number;
  private readonly transport: AnalyticsTransport;
  private droppedCount = 0;

  constructor(transport: AnalyticsTransport, maxBatchSize = 50, maxQueueSize = 2000) {
    this.transport = transport;
    this.maxBatchSize = maxBatchSize;
    this.maxQueueSize = maxQueueSize;
  }

  enqueue(event: Record<string, unknown>): boolean {
    if (this.queue.length >= this.maxQueueSize) {
      // Bounded memory: drop telemetry before risking OOM in request path
      this.droppedCount += 1;
      return false;
    }
    this.queue.push(event);
    if (this.queue.length >= this.maxBatchSize) {
      void this.flush();
    }
    return true;
  }

  async flush(): Promise<void> {
    if (this.queue.length === 0) return;
    const batch = this.queue.splice(0, this.maxBatchSize);
    try {
      await this.transport.sendBatch(batch);
    } catch {
      // Log aggregated drop counter; never throw into user-facing HTTP handler
      this.droppedCount += batch.length;
    }
  }

  getDroppedCount(): number {
    return this.droppedCount;
  }
}
```
Client-side unload-safe flush:
```typescript
export function registerUnloadFlush(flushUrl: string, getPendingBatch: () => readonly unknown[]): () => void {
  const handleVisibilityChange = (): void => {
    if (document.visibilityState !== 'hidden') return;
    const batch = getPendingBatch();
    if (batch.length === 0) return;
    const body = JSON.stringify({ batch });
    if (typeof navigator.sendBeacon === 'function') {
      const blob = new Blob([body], { type: 'application/json' });
      navigator.sendBeacon(flushUrl, blob);
      return;
    }
    void fetch(flushUrl, { method: 'POST', body, headers: { 'content-type': 'application/json' }, keepalive: true });
  };
  document.addEventListener('visibilitychange', handleVisibilityChange);
  return () => document.removeEventListener('visibilitychange', handleVisibilityChange);
}
```

## 5. Platform / Vendor Variations
| Platform | Core Strength | Key Limitation / Watch-Out |
| --- | --- | --- |
| **PostHog** | Open-source/self-hostable, product analytics + feature flags + experiments + session replay in one | High-volume autocapture inflates billing; disable autocapture or filter selectively |
| **Google Analytics 4 (GA4)** | Free acquisition/ad attribution + BigQuery export | Sampling/thresholding in UI, weak product experimentation & identity merge; use BigQuery raw export for serious analysis |
| **Mixpanel** | Fast interactive funnel/retention/cohort UI | Pricing scales on Monthly Tracked Users (MTUs) or events; requires clean server/client dedup |
| **Snowplow / First-Party Collector -> Warehouse** | Full data ownership, strict JSON Schema validation at edge, zero vendor lock-in | Higher infra & BI engineering overhead |

## 6. Decision Matrix & Trade-Offs
| Instrumentation Path | Ad-Blocker Survival | Captures UI Micro-Interactions | Captures Authoritative Revenue |
| --- | --- | --- | --- |
| **3rd-Party Client SDK Only** | Low (70%–85%) | Yes | **NO** (unacceptable revenue drift) |
| **1st-Party Proxy Client SDK** | High (92%–98%, when consented) | Yes | Partial (still vulnerable to tab close) |
| **Server-Side Outbox / Collector** | 100% | No (no hover/scroll/client perf) | **YES (100% authoritative)** |
| **Hybrid (1st-Party Client + Server Truth)** | 95%–100% | Yes | **YES (Recommended Standard)** |

## 7. Real Production Scenario
A marketplace launches a new checkout page and tracks `Order_Completed` exclusively from the browser "Thank You" page via GA4. Finance reconciles monthly GMV and discovers GA4 under-reports revenue by 19% because mobile users close the tab during 3DS redirect or run privacy blockers. Moving `Order_Completed` and `Payment_Failed` to backend webhook handlers (persisted via transactional outbox with deterministic `order_completed:<id>` `event_id`) reduces warehouse-to-ledger revenue variance to `< 0.1%`.

## 8. Failure Modes & Edge Cases
- **WRONG:** Awaiting a third-party analytics HTTP call (`await posthog.capture(...)`) inside a synchronous checkout API route without a tight timeout or async queue — when the vendor has a 5-second blip, checkout times out.
- **RIGHT:** Buffer analytics asynchronously in a bounded non-blocking queue (or durable outbox for revenue events) with strict timeouts (`<= 1.5s`) and graceful degradation.
- **WRONG:** Using `beforeunload` synchronous XHR (deprecated, breaks bfcache, silently killed on mobile Safari).
- **RIGHT:** Flush on `visibilitychange` (`document.visibilityState === 'hidden'`) via `navigator.sendBeacon()` or `fetch(..., { keepalive: true })`.

## 9. Testing & Verification
- Block third-party tracker domains in browser DevTools and verify: (1) core app flows work with zero unhandled exceptions, (2) server-side revenue events still land in staging warehouse 100%, and (3) consented first-party `/ingest` calls succeed cleanly.
- Load-test server analytics queue overflow: confirm bounded memory holds flat and core API p95 latency stays unchanged when the analytics endpoint returns `503`.

## 10. Operational Considerations
- Strip/anonymize reverse-proxy headers carefully (`X-Forwarded-For` -> pass client IP only for coarse geo lookup if policy permits, never persist raw IP unnecessarily).
- Call `analytics.shutdown()` / `flush()` on graceful server `SIGTERM` so in-flight batched server events are not lost during rolling deployments.

## 11. Authoritative References
- MDN Web Docs — *Navigator.sendBeacon() & Page Visibility API* (`https://developer.mozilla.org/en-US/docs/Web/API/Navigator/sendBeacon`).
- PostHog Documentation — *Using a Reverse Proxy* (`https://posthog.com/docs/advanced/proxy`).
- Google Analytics 4 — *Measurement Protocol Best Practices* (`https://developers.google.com/analytics/devguides/collection/protocol/ga4`).

## 12. Limitations & When NOT to Use
- A first-party reverse proxy MUST NEVER be used to bypass an explicit user consent refusal (`04-privacy-and-consent-architecture.md`); it exists to prevent accidental breakage of consented first-party product telemetry.
- Do not double-count revenue by firing BOTH client `Order_Completed` and server `Order_Completed` into the same metric without shared `event_id` deduplication (`06-analytics-data-architecture.md`).
