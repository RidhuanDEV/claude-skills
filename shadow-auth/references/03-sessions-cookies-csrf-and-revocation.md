# 03. Sessions, Cookies, CSRF & Revocation

## 1. Purpose & Activation Conditions
Design hijacking-resistant browser sessions, hardened cookie attributes, CSRF defenses, session-fixation rotation, and bounded-SLA revocation across REST APIs and realtime channels. Load when building cookie-based auth, BFF sessions, logout flows, or role-downgrade revocation.

## 2. Prerequisites
- HTTPS everywhere (HSTS), server-side session store (Redis/Postgres), and knowledge of cross-site vs same-site frontend topology.

## 3. Technical Principles & Constraints
- **Hardened Session Cookie Invariants (`OWASP ASVS V3`):**
  - High-entropy opaque session ID (`>= 128` bits CSPRNG, stored **hashed** in Redis/DB so a read-only cache dump cannot hijack live sessions).
  - Mandatory flags: `HttpOnly`, `Secure`, `SameSite=Lax` (or `Strict` for admin panels; use `SameSite=None; Secure` ONLY when cross-site embedding is truly required, paired with explicit CSRF defense), and `__Host-` cookie prefix (`Path=/`, no `Domain` attribute -> blocks subdomain cookie-tossing!).
- **Session Fixation & Privilege-Elevation Rotation:** Always regenerate a brand-new session ID and invalidate the old one upon: (1) login, (2) MFA step-up, (3) role/privilege change, and (4) password reset.
- **Idle + Absolute Timeouts:** Enforce BOTH an **idle timeout** (e.g., `30 min`–`24h` based on sensitivity) AND an **absolute lifetime** (e.g., `7–30 days`, `8–12 hours` for high-privilege admin/fintech portals).
- **CSRF Defense-in-Depth:** Do not rely on `SameSite` alone for state-changing endpoints if subdomains or legacy browsers exist. Pair `SameSite=Lax` with:
  - Strict `Origin` / `Sec-Fetch-Site` (`same-origin`) validation on `POST`/`PUT`/`PATCH`/`DELETE`, AND/OR
  - Synchronizer CSRF token bound to the server session (or double-submit HMAC-bound token),
  - Rejecting simple content-types (`text/plain`, `application/x-www-form-urlencoded`) on JSON APIs.
- **Immediate Revocation Propagation:** Logout, password change, account disablement, or role downgrade MUST synchronously delete/invalidate the server session record (or increment `user.auth_version` checked in Redis) AND publish a revocation event to terminate active WebSocket/SSE connections (`/shadow-realtime`).

## 4. Architecture & Implementation
```typescript
import { createHash, randomBytes } from 'node:crypto';

export interface CookieHeaderOptions {
  readonly name: string;
  readonly value: string;
  readonly maxAgeSec: number;
  readonly sameSite: 'Strict' | 'Lax';
}

export function createOpaqueSessionToken(): { readonly rawToken: string; readonly tokenHashHex: string } {
  const rawToken = randomBytes(32).toString('base64url');
  const tokenHashHex = createHash('sha256').update(rawToken, 'utf8').digest('hex');
  return { rawToken, tokenHashHex };
}

export function serializeHardenedHostCookie(opts: CookieHeaderOptions): string {
  // __Host- prefix enforces Secure, Path=/, and zero Domain attribute (blocks subdomain cookie injection)
  const name = opts.name.startsWith('__Host-') ? opts.name : `__Host-${opts.name}`;
  return `${name}=${opts.value}; Path=/; Max-Age=${opts.maxAgeSec}; HttpOnly; Secure; SameSite=${opts.sameSite}`;
}

export function isCsrfOriginAllowed(
  method: string,
  originHeader: string | undefined,
  secFetchSite: string | undefined,
  allowedOrigins: ReadonlySet<string>
): boolean {
  const safeMethods = new Set(['GET', 'HEAD', 'OPTIONS']);
  if (safeMethods.has(method.toUpperCase())) return true;
  if (secFetchSite && secFetchSite !== 'same-origin' && secFetchSite !== 'none') {
    return false;
  }
  if (!originHeader) return false;
  return allowedOrigins.has(originHeader);
}
```

## 5. Platform / Vendor Variations
| Architecture | Best Session Pattern | Revocation Latency |
| :--- | :--- | :--- |
| **Monolith / BFF (`Next.js`, `Laravel`, `Django`, `Express`)** | Server-side Redis/Postgres opaque session + `__Host-sid` cookie | **Instant (`< 100ms`)** |
| **Hybrid SPA + Microservices** | BFF terminates cookie -> mints short-lived internal JWT (`<= 5m`) + Redis `auth_version` check on sensitive actions | Instant on BFF; `<= 5m` or instant via Redis check |
| **Cross-Subdomain Portal (`app.x.com` + `api.x.com`)** | Same-site `Domain=.x.com` (cannot use `__Host-`) + mandatory `Origin` allowlist + synchronizer CSRF token | Instant via shared Redis session store |

## 6. Decision Matrix & Trade-Offs
| Session Strategy | Instant Revocation | Payload Size | Horizontal Scaling |
| :--- | :---: | :---: | :--- |
| **Server-Side Hashed Session (Redis/DB)** | **Yes (Instant)** | Tiny (32-byte ID) | High (Redis cluster / sticky-free) |
| **Pure Stateless Cookie JWT** | **No** (until `exp`!) | Large (sent every request) | High, **bad for logout/role-downgrade** |
| **BFF Cookie + Short Internal JWT (`<= 5m`)** | **Yes** | Tiny externally | **Best enterprise balance** |

## 7. Real Production Scenario
A finance admin disables a terminated employee's account at 09:00, yet the employee continues exporting customer invoices until 17:00 because the backend uses stateless 12-hour cookies without server-side session checks, and WebSocket streams never re-validate revocation. Migrating to Redis-backed hashed sessions (`createOpaqueSessionToken`) + `DELETE session` + pub/sub revocation push to WebSocket hubs terminates access across both HTTP and realtime sockets within `< 1 second`.

## 8. Failure Modes & Edge Cases
- **WRONG:** Leaving the pre-login anonymous session ID unchanged after login (session fixation vulnerability).
- **RIGHT:** Issue a fresh CSPRNG session ID on login/MFA/privilege change and delete the previous session ID atomically.
- **WRONG:** Implementing logout ONLY by clearing the cookie on the frontend (`document.cookie` or `Set-Cookie: Max-Age=0`) without invalidating the session row on the server (a copied cookie remains valid!).
- **RIGHT:** Always delete/revoke the server-side session record first, THEN emit expired `Set-Cookie` clearing header.

## 9. Testing & Verification
- Test session fixation: capture pre-login session ID -> log in -> assert new session ID differs AND old session ID returns `401`.
- Test logout & revocation: copy valid session cookie -> call `POST /logout` (or change password) -> replay copied cookie -> assert `401`.
- Test CSRF: send state-changing `POST` with `Origin: https://evil.example` -> assert `403`.

## 10. Operational Considerations
- Provide a `"Sign out all devices"` endpoint listing active sessions (`device_label`, `last_seen_at`, coarse geo — never raw session tokens!) and revoking all session rows for `user_id` except optionally the current one.

## 11. Authoritative References
- OWASP Session Management Cheat Sheet (`https://cheatsheetseries.owasp.org/cheatsheets/Session_Management_Cheat_Sheet.html`).
- OWASP Cross-Site Request Forgery Prevention Cheat Sheet (`https://cheatsheetseries.owasp.org/cheatsheets/Cross-Site_Request_Forgery_Prevention_Cheat_Sheet.html`).
- IETF RFC 6265bis — *HTTP State Management Mechanism* (`__Host-` & `SameSite`).

## 12. Limitations & When NOT to Use
- Cookie sessions are designed for browser user agents; for native mobile apps or M2M backend clients, use OAuth 2.1 tokens in Keychain/Keystore or mTLS/scoped API keys (`04`, `07`).
