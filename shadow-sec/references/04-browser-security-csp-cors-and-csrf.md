# 04. Browser Security: CSP, CORS, XSS & Clickjacking

## 1. Purpose & Activation Conditions
Harden web applications against XSS, credentialed CORS hijacking, clickjacking, MIME sniffing, and cross-origin leaks using strict per-request nonce CSP, exact-origin CORS, and Fetch Metadata policies. Load when configuring security middleware, reverse-proxy headers, or rich-text/HTML rendering.

## 2. Prerequisites
- Knowledge of legitimate frontend origins, third-party script/analytics hosts, and cookie vs token auth topology (`shadow-auth`).

## 3. Technical Principles & Constraints
- **Strict Nonce-Based CSP (`OWASP ASVS v5.0.0-3.4.x`):**
  - Generate a fresh **`>= 128-bit` CSPRNG nonce per HTTP response** (`crypto.randomBytes(16).toString('base64')`) and emit `Content-Security-Policy: default-src 'self'; script-src 'self' 'nonce-<n>' 'strict-dynamic'; object-src 'none'; base-uri 'self'; frame-ancestors 'none'`.
  - **NEVER** allow `'unsafe-eval'` or wildcard `script-src *` in production; avoid `'unsafe-inline'` for scripts! (Note: NEVER cache an HTML response containing a per-request nonce in a shared CDN cache!)
- **Zero-Trust CORS Policy:**
  - NEVER combine `Access-Control-Allow-Origin: *` with `Access-Control-Allow-Credentials: true`.
  - NEVER reflect arbitrary `req.headers.origin` directly (allows any attacker site to read authenticated API responses using the victim's cookies!).
  - Match `Origin` strictly against an exact configured `ReadonlySet<string>` allowlist, emit `Vary: Origin`, and omit CORS headers completely for untrusted origins.
- **XSS Output Encoding & Safe Rich Text:** Rely on framework auto-escaping (React/Vue/Angular); NEVER pass user input to `dangerouslySetInnerHTML`, `v-html`, `innerHTML`, or `href="javascript:..."` (validate URL schemes strictly to `https:`/`http:`/`mailto:`). When rich HTML (e.g., Markdown) is truly required, sanitize with a vetted allowlist sanitizer (`DOMPurify` / `sanitize-html`) on a locked-down tag/attribute profile.
- **Complete Security Header Baseline:**
  - `Strict-Transport-Security: max-age=31536000; includeSubDomains` (HTTPS only),
  - `X-Content-Type-Options: nosniff`,
  - `Referrer-Policy: strict-origin-when-cross-origin`,
  - `Permissions-Policy: camera=(), microphone=(), geolocation=()` (restrict unused browser APIs),
  - `Cache-Control: no-store` on authenticated API responses containing sensitive user/financial data.

## 4. Architecture & Implementation
```typescript
import { randomBytes } from 'node:crypto';

export function generateCspNonce(): string {
  return randomBytes(16).toString('base64');
}

export function buildHardenedBrowserHeaders(
  nonce: string,
  requestOrigin: string | undefined,
  allowedOrigins: ReadonlySet<string>,
  isSensitiveResponse: boolean
): Readonly<Record<string, string>> {
  const headers: Record<string, string> = {
    'Strict-Transport-Security': 'max-age=31536000; includeSubDomains',
    'Content-Security-Policy': [
      "default-src 'self'",
      `script-src 'self' 'nonce-${nonce}'`,
      "object-src 'none'",
      "base-uri 'self'",
      "frame-ancestors 'none'",
      'upgrade-insecure-requests',
    ].join('; '),
    'X-Content-Type-Options': 'nosniff',
    'Referrer-Policy': 'strict-origin-when-cross-origin',
    'Permissions-Policy': 'camera=(), microphone=(), geolocation=()',
  };

  if (requestOrigin && allowedOrigins.has(requestOrigin)) {
    headers['Access-Control-Allow-Origin'] = requestOrigin;
    headers['Access-Control-Allow-Credentials'] = 'true';
    headers['Vary'] = 'Origin';
  }
  if (isSensitiveResponse) {
    headers['Cache-Control'] = 'no-store';
  }
  return headers;
}

export function isSafeHttpHref(rawUrl: string): boolean {
  try {
    const parsed = new URL(rawUrl, 'https://placeholder.invalid');
    return parsed.protocol === 'https:' || parsed.protocol === 'http:' || parsed.protocol === 'mailto:';
  } catch {
    return false;
  }
}
```

## 5. Platform / Vendor Variations
| Stack | CSP / Security Header Integration | Key Caution |
| :--- | :--- | :--- |
| **Next.js App Router** | Generate nonce in `middleware.ts` -> forward via `x-nonce` header into Server Components | Pages using per-request nonces must opt into dynamic rendering (`no-store`) — never serve cached stale nonces |
| **Express / Fastify / Hono** | `helmet` / custom middleware with explicit CSP directives (disable default loose overrides) | Always verify exact rendered response headers in integration tests |
| **Nginx / Cloudflare Edge** | Set baseline `HSTS`, `nosniff`, `Referrer-Policy` at edge; avoid duplicating conflicting CSP headers from both edge and app | Duplicate `Access-Control-Allow-Origin` headers break browser fetch! |

## 6. Decision Matrix & Trade-Offs
| Mechanism | Stops Stored XSS? | Stops Cross-Origin Cookie Read? | Complexity |
| :--- | :---: | :---: | :---: |
| **Strict Nonce CSP (`script-src 'nonce-...'`)** | **High defense-in-depth** | No | Medium |
| **Exact-Origin CORS Allowlist + `Vary: Origin`** | No | **YES** | Low |
| **DOMPurify + `isSafeHttpHref`** | **YES (Primary)** | No | Low |

## 7. Real Production Scenario
To quickly unblock a staging frontend CORS error, an engineer sets `cors({ origin: true, credentials: true })` (which echoes ANY `Origin` header back with `Allow-Credentials: true`) and merges it to production. Any malicious webpage visited by a logged-in user can now issue `fetch('https://api.company.com/api/v1/me/export', { credentials: 'include' })` and exfiltrate the user's private data silently. Switching to `allowedOrigins.has(requestOrigin)` + `Vary: Origin` and gating headers in CI with `appsec_control_verifier.py --check-security-headers` closes the vulnerability immediately.

## 8. Failure Modes & Edge Cases
- **WRONG:** Allowing `origin.endsWith('example.com')` in CORS validation (trivially bypassed by registering `https://evil-example.com`!).
- **RIGHT:** Match exact full origin strings (`https://app.example.com`) including scheme, hostname, and port inside a `Set`.
- **WRONG:** Allowing `<a href={userWebsite}>` without scheme validation (`javascript:alert(document.cookie)` executes XSS right inside React!).
- **RIGHT:** Validate every user-supplied link with `isSafeHttpHref` (`https:`/`http:`/`mailto:` only).

## 9. Testing & Verification
- Run `python shadow-sec/scripts/appsec_control_verifier.py --check-security-headers <headers.json>`.
- Test CORS with `Origin: https://evil-example.com` -> assert `Access-Control-Allow-Origin` header is **absent**.
- Test CSP rollout safely first via `Content-Security-Policy-Report-Only` + `report-to` collector before enforcing hard blocking on legacy pages.

## 10. Operational Considerations
- Monitor CSP violation reports (`report-to`) to catch accidental third-party script tampering (Magecart/supply-chain skimmers) early in production.

## 11. Authoritative References
- OWASP ASVS v5.0.0 — *V3 Web Frontend Security* (`https://asvs.owasp.org/`).
- W3C Content Security Policy Level 3 (`https://www.w3.org/TR/CSP3/`).
- OWASP Cross Site Scripting Prevention Cheat Sheet (`https://cheatsheetseries.owasp.org/cheatsheets/Cross_Site_Scripting_Prevention_Cheat_Sheet.html`).

## 12. Limitations & When NOT to Use
- CSP is a strong defense-in-depth layer against XSS, NOT a substitute for proper output encoding, sanitized Markdown, and `HttpOnly` session cookies (`shadow-auth`).
