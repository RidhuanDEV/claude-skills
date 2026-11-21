# Modern Authentication, Passkeys, ReBAC, M2M & API Key Lifecycle

## 1. Core Concepts
Enterprise identity spans **phishing-resistant human login (WebAuthn/Passkeys, MFA/TOTP, OIDC SSO)**, **machine-to-machine workload identity (mTLS, OAuth2 Client Credentials, DPoP)**, **hashed-at-rest API keys**, and **server-enforced authorization (RBAC, ABAC, and Zanzibar ReBAC)**.

## 2. Technical Rules & Modality Matrix

| Need | Choose Mechanism | Mandatory Implementation Rule |
| :--- | :--- | :--- |
| **Consumer / Staff Phishing-Resistant Auth** | Passkeys / WebAuthn (FIDO2) | Verify single-use challenge (`TTL <= 5m`), exact `origin`, `rpIdHash`, and monotonic `signCount` server-side. |
| **B2B Enterprise Multi-Tenant SSO** | OIDC (PKCE `S256`) / SAML 2.0 | Bind tenant strictly from verified IdP connection metadata — never from unverified email domain suffix alone. |
| **Coarse Role Permissions** | Tenant-Scoped RBAC | Check `(claims.tenantId === resource.tenantId && roleHasPermission(claims.role, action))` on every route. |
| **Hierarchical / Shared Document Graph** | ReBAC (OpenFGA / SpiceDB / Zanzibar) | Pass a **consistency token (Zookie)** on reads after permission revocation so stale replicas never grant revoked access. |
| **Developer / Partner API Access** | Prefixed Scoped API Keys | Generate `sk_live_<keyId>_<random32>`, store ONLY `SHA-256`/`HMAC` digest at rest, support dual-key rotation overlap. |

## 3. Implementation Examples
```ts
// Timing-Safe Scoped API Key Verification (Hashed-at-Rest, Zero Plaintext Storage)
import crypto from 'node:crypto'

export interface StoredApiKeyRecord {
  readonly keyId: string
  readonly tenantId: string
  readonly secretHashHex: string
  readonly scopes: ReadonlyArray<string>
  readonly expiresAtIso: string | null
  readonly revoked: boolean
}

export function verifyScopedApiKey(
  rawHeaderKey: string,
  pepper: string,
  requiredScope: string,
  lookupByKeyId: (keyId: string) => StoredApiKeyRecord | null,
): { readonly allowed: boolean; readonly tenantId: string | null; readonly reason: string } {
  const parts = rawHeaderKey.split('_')
  if (parts.length !== 4 || parts[0] !== 'sk' || parts[1] !== 'live') {
    return { allowed: false, tenantId: null, reason: 'malformed_key' }
  }
  const keyId = parts[2] ?? ''
  const record = lookupByKeyId(keyId)
  if (!record || record.revoked) return { allowed: false, tenantId: null, reason: 'revoked_or_unknown' }
  if (record.expiresAtIso && Date.parse(record.expiresAtIso) <= Date.now()) {
    return { allowed: false, tenantId: null, reason: 'expired' }
  }
  const candidateHash = crypto.createHmac('sha256', pepper).update(rawHeaderKey, 'utf8').digest()
  const storedHash = Buffer.from(record.secretHashHex, 'hex')
  if (candidateHash.length !== storedHash.length || !crypto.timingSafeEqual(candidateHash, storedHash)) {
    return { allowed: false, tenantId: null, reason: 'invalid_secret' }
  }
  if (!record.scopes.includes(requiredScope)) {
    return { allowed: false, tenantId: null, reason: 'insufficient_scope' }
  }
  return { allowed: true, tenantId: record.tenantId, reason: 'verified' }
}
```

## 4. Best Practices
- Rotate session IDs and issue a new refresh-token family on privilege elevation or password/MFA changes; revoke the entire refresh-token family immediately if a rotated refresh token is replayed.
- Redact `Authorization`, `Cookie`, `x-api-key`, and token payloads at the logger root before any log line leaves the process.

## 5. Anti-patterns (WRONG vs RIGHT)
- **WRONG:** Storing API keys in plaintext or comparing secrets with `===` (vulnerable to DB dump leakage and timing attacks), or trusting client headers (`X-Tenant-Id`, `X-Role`, `X-Username`) for authorization.
- **RIGHT:** Hash API keys with HMAC-SHA256 + server pepper, compare with `crypto.timingSafeEqual`, and derive identity/tenant exclusively from verified server tokens.

## 6. Production Considerations
- Maintain an automated negative authorization test matrix verifying `401` (unauthenticated/expired), `403` (cross-tenant IDOR attempt), and `403` (viewer attempting admin action) on every protected endpoint.
