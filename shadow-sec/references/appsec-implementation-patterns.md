# Application Security Implementation Patterns (OWASP ASVS 5.0)

> Use this playbook when implementing or auditing injection defenses, SSRF guards, authorization/IDOR boundaries, browser security headers (`CSP`, `HSTS`, `CORS`), or secure file handling under **OWASP ASVS v5.0.0** (`17 chapters V1–V17`, citation format `v5.0.0-C.S.R`).

## 1. Core Concepts
Compliance audits find flaws, while defensive engineering eliminates vulnerability classes structurally:
- **Zero-Trust Boundaries:** Validate structure (`V2`), enforce tenant/owner predicates inside data queries (`V8`), parameterize interpreters (`V1`), and resolve network destinations to concrete IPs before outbound fetches (`V13`).
- **Fail-Closed Defaults:** Unmapped roles deny access, invalid origins omit CORS headers, and error envelopes suppress internal stack traces (`V16`).

## 2. Technical Rules & Decision Matrix

| Vulnerability Class | ASVS 5.0 Chapter / Ref | Server-Side Defense Pattern | Verification Check |
| :--- | :--- | :--- | :--- |
| SQL / Command Injection | `V1` (`v5.0.0-1.2.4`) | Bound `$1, $2` SQL params; `execFile` with `shell: false` | Static grep + negative probe `' OR 1=1 --` |
| SSRF (Server-Side Request Forgery) | `V4` / `V13` | HTTPS-only + DNS-resolve ALL A/AAAA records + block private CIDRs + manual redirects | Test `127.0.0.1`, `169.254.169.254`, `[::1]`, decimal IP |
| IDOR / BOLA & Cross-Tenant Leak | `V8` (`v5.0.0-8.2.1`) | Derive `actorId` & `tenantId` from verified session/JWT; filter in DB `WHERE` clause | Cross-tenant read/mutate probe returns `403`/`404` |
| XSS, Clickjacking & CORS Abuse | `V3` (`v5.0.0-3.4.x`) | Per-request cryptographic nonce CSP + `frame-ancestors 'none'` + exact Origin allowlist | Inspect response headers; test untrusted `Origin` |
| Unsafe File Upload | `V5` (`v5.0.0-5.2.x`) | Magic-byte MIME verification + UUID object key + non-executable bucket + download `Content-Disposition` | Upload `.html`/polyglot renamed `.png` -> rejected |

## 3. Implementation Examples

### Strict-TS DNS-Resolved Anti-SSRF Guard (Blocks Cloud Metadata & Private Subnets)
```ts
import { lookup } from "node:dns/promises";
import { isIP } from "node:net";

function isForbiddenIpv4(ip: string): boolean {
  const parts = ip.split(".").map((n) => Number.parseInt(n, 10));
  if (parts.length !== 4 || parts.some((n) => Number.isNaN(n) || n < 0 || n > 255)) return true;
  const [a = -1, b = -1] = parts;
  return (
    a === 0 || a === 10 || a === 127 ||
    (a === 169 && b === 254) ||
    (a === 172 && b >= 16 && b <= 31) ||
    (a === 192 && b === 168) ||
    (a === 100 && b >= 64 && b <= 127)
  );
}

function isForbiddenIp(ip: string): boolean {
  const normalized = ip.toLowerCase();
  if (isIP(normalized) === 4) return isForbiddenIpv4(normalized);
  if (normalized.startsWith("::ffff:")) return isForbiddenIpv4(normalized.slice(7));
  return (
    normalized === "::1" || normalized === "::" ||
    normalized.startsWith("fe80:") ||
    normalized.startsWith("fc") || normalized.startsWith("fd")
  );
}

export async function assertSafeOutboundUrl(rawUrl: string, allowedHosts: ReadonlySet<string>): Promise<URL> {
  const parsed = new URL(rawUrl);
  if (parsed.protocol !== "https:") throw new Error("SSRF_BLOCKED_PROTOCOL");
  if (!allowedHosts.has(parsed.hostname.toLowerCase())) throw new Error("SSRF_HOST_NOT_ALLOWED");

  const records = await lookup(parsed.hostname, { all: true });
  if (records.length === 0 || records.some((r) => isForbiddenIp(r.address))) {
    throw new Error("SSRF_FORBIDDEN_DESTINATION_IP");
  }
  return parsed;
}
```

### Nonce CSP, HSTS & Parameterized Tenant-Scoped Query
```ts
export function buildSecurityHeaders(nonce: string, allowedOrigin: string | null): Readonly<Record<string, string>> {
  const headers: Record<string, string> = {
    "Strict-Transport-Security": "max-age=31536000; includeSubDomains",
    "Content-Security-Policy": `default-src 'self'; script-src 'self' 'nonce-${nonce}'; object-src 'none'; base-uri 'self'; frame-ancestors 'none'`,
    "X-Content-Type-Options": "nosniff",
    "Referrer-Policy": "strict-origin-when-cross-origin",
  };
  if (allowedOrigin) {
    headers["Access-Control-Allow-Origin"] = allowedOrigin;
    headers["Vary"] = "Origin";
  }
  return headers;
}
```

## 4. Best Practices
- Pin egress connections directly to the validated DNS resolution IP (with matching TLS `servername` SNI) or enforce egress proxy firewalls to eliminate TOCTOU DNS-rebinding windows.
- Log security-relevant events (`auth.denied`, `authz.idor_attempt`, `ssrf.blocked`) to the immutable security audit channel without logging raw bearer tokens, cookies, or passwords (`V16`).
- Pair parameterized queries with server-derived `tenant_id` predicates (`WHERE invoice_id = $1 AND tenant_id = $2`) on every read, update, and delete route.

## 5. Anti-Patterns (`WRONG` vs `RIGHT`)
- **WRONG (Naive hostname string filter for SSRF):** Checking `!url.includes("localhost") && !url.startsWith("http://127.")` (trivially bypassed via `http://2130706433/`, `http://[::1]/`, or DNS A-record pointing to `169.254.169.254`).
  **RIGHT:** Enforce HTTPS-only, allowlist exact domains when fixed, resolve DNS upfront (`all: true`), reject all non-public IPv4/IPv6 ranges, and set `redirect: "manual"`.
- **WRONG (Wildcard CORS with credentials / Echoing `Origin`):** Setting `Access-Control-Allow-Origin: req.headers.origin` + `Access-Control-Allow-Credentials: true` or using `req.body.userId` without ownership proof.
  **RIGHT:** Match `Origin` strictly against a configured allowlist, emit `Vary: Origin`, and bind resource ownership to server-verified claims.

## 6. Production Considerations
- **Approval Boundaries:** SAST/STRIDE code inspection is `L0_READ_ONLY`, high-volume active fuzzing/DAST against shared targets is `L3_RESOURCE_INTENSIVE`, and live secret rotation or IAM edits require `L4_HIGH_IMPACT` approval.
- **Zero Info Leakage:** Map internal database errors (`23505`, timeouts) to clean RFC 9457 error responses in HTTP handlers while keeping diagnostics structured in private logs.
