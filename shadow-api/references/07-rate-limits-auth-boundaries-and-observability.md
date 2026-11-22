# 07. Rate Limits, Auth Boundaries & API Observability

## 1. Purpose & Activation Conditions
Protect public and internal APIs against abuse (`OWASP API4:2023`), enforce strict auth/DTO boundaries at ingress, wire production structured wide-event logging (`BACKEND.md §12`), and manage ephemeral local verification servers cleanly (`Rule #29`). Load when hardening API middleware, adding rate limiters, or instrumenting API handlers.

## 2. Prerequisites
- Centralized auth principal (`shadow-auth`), Redis rate-limit store, and structured JSON logger (`pino`/`structlog`/`log/slog`).

## 3. Technical Principles & Constraints
- **Tiered Rate Limiting + Standard Headers (IETF RateLimit Draft):**
  - Apply distinct buckets: **Auth/OTP/Reset** (strict: e.g., `5/15m` per IP+account), **Expensive Search/Export/AI** (`10–30/m` per tenant), **Standard Authenticated CRUD** (`100–600/m` per tenant/API key).
  - Return HTTP **`429 Too Many Requests`** with `Retry-After` (seconds), `RateLimit-Limit`, `RateLimit-Remaining`, and `RateLimit-Reset` headers — plus RFC 9457 `application/problem+json` body.
  - Bound request body size (`100 KB–1 MB` for JSON routes) and handler/upstream timeouts at BOTH reverse proxy (Nginx/Cloudflare) and app middleware!
- **OWASP API Security Top 10 Core Ingress Controls:**
  - Validate every incoming body/query/param against strict explicit schemas (`Zod`/`Pydantic`) rejecting unknown fields (`strict()`/`extra="forbid"`) -> blocks Mass Assignment (`API3:2023 BOPLA`).
  - Serialize responses through explicit **Response DTOs** — never return raw ORM/DB model objects (`res.json(user)` accidentally leaks `passwordHash`, `totpSecret`, or internal flags!).
  - Never trust client-supplied `username`, `role`, or `tenant_id` without server-verified claims (`shadow-auth`).
- **Canonical Structured Wide-Event Logging (`BACKEND.md §12`):**
  - Emit **1 canonical JSON wide-event per completed request** carrying `requestId`, `traceId`, `method`, **normalized route template** (`/api/v1/orders/:id` — NEVER raw URL with IDs/query tokens!), `status`, `latencyMs`, `tenantId`, and `errorCode`.
  - Fail-closed redaction on `authorization`, `cookie`, `x-api-key`, `password`, `token`, `secret`, `nik`, `otp` + anti-CRLF sanitization; zero raw `console.log` in production backend routes.
- **Bounded Local Verification & Server Cleanup (`Rule #29`):** When verifying affected routes via `shadow_api` MCP (`test_api_endpoint` / bounded `run_api_collection`) against a task-spawned local server, track its exact PID and stop ONLY that tracked PID (`resource_cleanup.py --cleanup-owned`) on exit unless the Monarch asked to keep it running.

## 4. Architecture & Implementation
```typescript
export interface RateLimitSnapshot {
  readonly limit: number;
  readonly remaining: number;
  readonly resetAfterSec: number;
  readonly allowed: boolean;
}

export function buildRateLimitHeaders(snap: RateLimitSnapshot): Readonly<Record<string, string>> {
  const headers: Record<string, string> = {
    'RateLimit-Limit': String(snap.limit),
    'RateLimit-Remaining': String(Math.max(0, snap.remaining)),
    'RateLimit-Reset': String(Math.max(0, Math.ceil(snap.resetAfterSec))),
  };
  if (!snap.allowed) {
    headers['Retry-After'] = String(Math.max(1, Math.ceil(snap.resetAfterSec)));
  }
  return headers;
}

// Explicit Response DTO mapper (prevents BOPLA / accidental internal column exposure)
export interface UserDbRow {
  readonly id: string;
  readonly tenant_id: string;
  readonly display_name: string;
  readonly role: string;
  readonly password_hash: string;
  readonly totp_secret_enc: string | null;
}

export interface PublicUserDto {
  readonly id: string;
  readonly displayName: string;
  readonly role: string;
}

export function toPublicUserDto(row: UserDbRow): PublicUserDto {
  return {
    id: row.id,
    displayName: row.display_name,
    role: row.role,
  };
}
```

## 5. Platform / Vendor Variations
| Layer | Rate Limiting Mechanism | Trade-Off |
| :--- | :--- | :--- |
| **Edge / Reverse Proxy (Cloudflare / Nginx / Kong)** | IP/ASN volumetric DDoS & bot shielding | Cannot easily enforce tenant-plan quotas without JWT inspection |
| **Application Redis Sliding Window / Token Bucket** | Exact per-`tenant_id`, per-`api_key`, per-`user_id` fairness | Requires fail-open vs fail-closed decision if Redis is unreachable (fail-closed for OTP/auth, fail-open with local fallback for general reads!) |

## 6. Decision Matrix & Trade-Offs
| Endpoint Class | Fail Mode if Rate-Limit Redis Down | Body Limit | Timeout Budget |
| :--- | :---: | :---: | :---: |
| **Auth / Login / OTP / Reset** | **Fail-Closed (or strict local in-memory cap)** | `16 KB` | `5s` |
| **Standard Authenticated CRUD** | Local fallback cap + alert | `256 KB` | `10s` |
| **Heavy Report / Export** | Local strict concurrency semaphore | `64 KB` | Return `202` LRO (`06`) |

## 7. Real Production Scenario
A backend API returns raw Prisma `findUnique()` results directly (`res.json(user)`). Three months later another engineer adds `totpSecret` and `resetTokenHash` columns to the `users` table; the profile endpoint silently starts leaking both columns in JSON responses to every client (`OWASP API3:2023 Excessive Data Exposure`). Switching to explicit allowlisted `toPublicUserDto` mappers + OpenAPI response contract tests prevents accidental field leaks permanently.

## 8. Failure Modes & Edge Cases
- **WRONG:** Trusting raw `X-Forwarded-For` header directly for IP rate limiting without configuring trusted reverse-proxy hops (attackers spoof `X-Forwarded-For: 1.2.3.<rand>` on every request to bypass all rate limits!).
- **RIGHT:** Configure exact `trust proxy` hop count matching your load balancer/Cloudflare edge, and key authenticated rate limits primarily on verified `tenantId`/`userId`.
- **WRONG:** Logging raw request URLs `/api/v1/verify?token=eyJ...` or raw `req.headers` in HTTP access logs.
- **RIGHT:** Log normalized route templates (`/api/v1/verify`) with query tokens and sensitive headers stripped at logger root.

## 9. Testing & Verification
- Test rate-limit headers & `429` problem+json response on burst fixture; assert spoofed `X-Forwarded-For` does not bypass limits.
- Assert response DTO tests verify forbidden fields (`password_hash`, `totp_secret_enc`) are absent from serialized JSON.

## 10. Operational Considerations
- Track API golden signals per normalized route template (`RPS`, `4xx%`, `5xx%`, `p50/p95/p99 latency`, `429 throttle rate`) in `/shadow-observe` dashboards.

## 11. Authoritative References
- OWASP API Security Top 10 (2023) — `API3:2023` & `API4:2023` (`https://api-security.owasp.org/`).
- IETF Draft — *RateLimit Header Fields for HTTP* (`https://datatracker.ietf.org/doc/draft-ietf-httpapi-ratelimit-headers/`).
- Shadow Monarch Backend Logging Policy (`shadow-monarch/reference/BACKEND.md §12`).

## 12. Limitations & When NOT to Use
- Application-level rate limiting alone cannot absorb volumetric L3/L4 network DDoS attacks; always pair with edge/WAF rate controls for public internet APIs (`/shadow-ops`).
