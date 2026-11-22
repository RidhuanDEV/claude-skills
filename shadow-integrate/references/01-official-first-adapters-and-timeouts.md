# 01. Official-First Adapters, Credentials & Bounded Timeouts

## 1. Purpose & Activation Conditions
Design resilient, decoupled external API integrations using official-first SDK verification, clean Anti-Corruption Adapter boundaries, strict connection/read timeouts, and fail-closed credential & PII redaction. Load whenever integrating a new third-party payment, messaging, shipping, ERP, or government API (`Midtrans`, `Xendit`, `Stripe`, `SNAP BI`, `SatuSehat`, `BSrE`).

## 2. Prerequisites
- Verified official vendor documentation (`/context7` or official portal) and `shadow-monarch/scripts/official_first_verifier.py` for package provenance.

## 3. Technical Principles & Constraints
- **Official-First SDK Discipline (`OFFICIAL-FIRST-DEPENDENCY-POLICY.md`):**
  1. Inspect existing repository adapters first (`Reuse -> Official SDK -> Verified Pkg -> Justified Custom`).
  2. Before installing any new vendor SDK, inspect non-destructively (`npm view <pkg> version repository maintainers engines`) and confirm publisher authenticity (avoid typosquatted payment SDKs!).
  3. Wrap EVERY third-party SDK behind an internal **Anti-Corruption Port/Interface** (`PaymentGatewayPort`, `CourierClientPort`) and validate raw vendor JSON responses at the boundary (`Zod`/`Pydantic`) so external vendor quirks never bleed across controllers or domain logic!
- **Explicit Timeouts Everywhere (Zero Infinite Hangs!):** NEVER invoke `fetch()`, `axios`, `httpx`, or Go `http.DefaultClient` with unbounded default timeouts! Always set explicit `connectTimeout` (`2–3s`) and `totalResponseTimeout` (`5–10s`, e.g., `AbortSignal.timeout(8000)`), and bound connection pool sockets per upstream host so one stalling vendor cannot exhaust all Node/Go/Python sockets (Bulkhead isolation!).
- **Strict Sandbox vs Production Isolation:** Separate API keys, base URLs, and webhook signing secrets per environment (`SANDBOX` vs `PRODUCTION`); assert startup config fails closed if production keys appear in local/dev configs or vice versa.
- **Zero Secrets/PII in Integration Logs:** Redact `Authorization`, `X-API-Key`, `X-Signature`, `client_secret`, card numbers, `NIK`, and webhook secrets BEFORE logging outbound request/response telemetry!

## 4. Architecture & Implementation
```typescript
export interface PaymentChargeRequest {
  readonly idempotencyKey: string;
  readonly orderId: string;
  readonly amountMinor: number;
  readonly currency: 'IDR' | 'USD';
}

export type ProviderCallOutcome =
  | { readonly state: 'CONFIRMED_SUCCESS'; readonly providerRef: string }
  | { readonly state: 'CONFIRMED_DECLINED'; readonly declineCode: string }
  | { readonly state: 'UNKNOWN_AMBIGUOUS'; readonly reason: string; readonly correlationId: string };

export interface PaymentGatewayPort {
  readonly providerName: string;
  createCharge(req: PaymentChargeRequest): Promise<ProviderCallOutcome>;
  inquireStatus(orderId: string, correlationId: string): Promise<ProviderCallOutcome>;
}

// Safe bounded outbound HTTP helper with explicit timeout & redacted diagnostic logging
export async function fetchWithBoundedTimeout(
  url: string,
  init: RequestInit,
  timeoutMs = 8000
): Promise<Response> {
  const signal = AbortSignal.timeout(timeoutMs);
  return fetch(url, { ...init, signal, redirect: 'manual' });
}
```

## 5. Platform / Vendor Variations
| Runtime | Safe Timeout Enforcement | Classic Pitfall |
| :--- | :--- | :--- |
| **Node.js 20+ (`fetch` / `undici`)** | `AbortSignal.timeout(8000)` + custom `Agent({ connectTimeout: 3000 })` | Default `fetch()` has a 300s headers timeout — stalls worker event loop queues under outage! |
| **Python (`httpx`)** | `httpx.Timeout(connect=3.0, read=8.0, write=5.0, pool=3.0)` | Using `requests.get(url)` without `timeout=` hangs threads **forever**! |
| **Go (`net/http`)** | Dedicated `&http.Client{ Timeout: 8 * time.Second, Transport: ... }` | `http.DefaultClient` has **zero timeout (`0`)**! |

## 6. Decision Matrix & Trade-Offs
| Integration Option | Maintenance | Type Safety | Choose When |
| :--- | :---: | :---: | :--- |
| **Official Vendor SDK behind Internal Port** | Low | High | Actively maintained official SDK (`stripe`, `midtrans-client`, `xendit-node`) |
| **Typed Thin `fetch` Client behind Internal Port** | Medium | High (Zod/Pydantic) | Official SDK is abandoned, pulls heavy transitive CVEs, or spec is custom (`SNAP BI`, `SatuSehat`) |
| **Calling Vendor SDK Directly in Controllers** | Terrible | Fragile | **NEVER — couples domain logic to vendor lock-in** |

## 7. Real Production Scenario
A Go microservice calls an external courier tracking API using `http.DefaultClient.Get(url)` (infinite timeout). When the courier API suffers a silent TCP blackhole outage, 400 goroutines pile up waiting forever, saturating DB connections and crashing the order API. Replacing `http.DefaultClient` with a dedicated `http.Client` (`connectTimeout = 3s`, `Timeout = 8s`) behind a `CourierPort` adapter + circuit breaker isolates courier outages cleanly with zero impact on checkout.

## 8. Failure Modes & Edge Cases
- **WRONG:** Installing an unverified community npm package (`midtrans-snap-wrapper-unofficial`) without inspecting publisher/downloads/repo when an official SDK or clean HTTP spec exists.
- **RIGHT:** Verify publisher & provenance (`npm view`), prefer official SDK or clean audited HTTP adapter behind an internal Port, and document the 8-field Decision Record.
- **WRONG:** Logging raw `res.headers` or `req.headers` on failed provider HTTP calls (leaks `Authorization: Basic ...` / `Bearer ...` API keys into Loki/CloudWatch!).
- **RIGHT:** Strip `authorization`, `x-api-key`, `x-signature`, and token payloads at the HTTP client logger interceptor.

## 9. Testing & Verification
- Test adapter boundary with mocked slow upstream (`delay > timeoutMs`) -> assert clean `AbortError` mapped to `UNKNOWN_AMBIGUOUS` within `timeoutMs + 200ms` (never hangs!).
- Test malformed vendor JSON response -> assert boundary schema parser fails safely without crashing worker process.

## 10. Operational Considerations
- Emit per-provider SLI metrics (`provider`, `operation`, `status_class`, `latency_ms`, `breaker_state`) so SRE sees immediately when Midtrans, Xendit, or SatuSehat degrades (`/shadow-observe`).

## 11. Authoritative References
- OWASP API Security Top 10 (2023) — `API10:2023` (*Unsafe Consumption of APIs*, `https://api-security.owasp.org/`).
- Shadow Monarch Official-First Policy (`shadow-monarch/reference/OFFICIAL-FIRST-DEPENDENCY-POLICY.md`).

## 12. Limitations & When NOT to Use
- Do NOT write a generic multi-vendor abstraction layer upfront for 5 speculative providers you don't use yet — wrap the 1–2 real active providers behind a minimal clean Port reflecting actual domain needs.
