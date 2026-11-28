# 07. SSO SDK Coexistence, M2M & API Key Lifecycle

## 1. Purpose & Activation Conditions
Safely integrate and coexist multiple identity surfaces — existing internal/local SSO SDKs (such as `your-org-sso`), external OIDC/SAML SSO, browser cookie sessions, JWKS API tokens, and M2M / developer API keys — without breaking existing contracts or introducing unverified supply-chain swaps. Load when integrating local SSO SDKs, supporting hybrid cookie+JWT auth, or issuing partner/M2M credentials.

## 2. Prerequisites
- Inspection of existing auth dependencies (`package.json`, local `sdk/` folders, existing middleware) via `shadow-monarch/scripts/official_first_verifier.py --check-auth-sdk`.

## 3. Technical Principles & Constraints
- **Local / Internal SSO SDK Preservation Rule (`OFFICIAL-FIRST-DEPENDENCY-POLICY.md`):**
  1. Always inspect the existing local SDK (`exports`, version, token/session model, verifier hooks) BEFORE writing auth code.
  2. **NEVER** silently replace a local file-linked SDK (e.g., `your-org-sso` at `file:../sdk/sso-client`) with an unverified similarly named npm package (high dependency-confusion / typosquatting risk!) or rewrite login flows without explicit Monarch approval.
  3. Report build/Docker portability caveats for `file:../sdk/...` paths honestly as a separate note while preserving the authoritative SDK.
  4. **Never Trust Frontend Claims Alone:** Never accept frontend-supplied `username`/`email`/`role` as proof of SSO authentication; verify the IdP/SSO token or session cryptographically on the server before mapping local accounts.
- **Unified Principal Resolution (Coexisting SSO + Cookie + JWKS JWT):** When a backend must simultaneously accept (a) browser `__Host-sid` cookies from local/SSO login AND (b) `Authorization: Bearer <jwt>` verified against JWKS for legacy/mobile APIs, funnel BOTH authenticators through ONE unified auth middleware producing a single immutable `AuthenticatedPrincipal` (`userId`, `tenantId`, `role`, `authMethod`, `sessionId?`) so downstream RBAC/tenant isolation behaves identically!
- **Scoped Prefixed API Keys & M2M Security:**
  - Issue keys with recognizable prefix + lookup ID + `>= 256-bit` CSPRNG secret: `sk_live_<keyId>_<random32>`.
  - Store **ONLY** the keyed `HMAC-SHA256(rawKey, serverPepper)` hex digest at rest (zero plaintext keys in DB!), compare using `crypto.timingSafeEqual`, bind to explicit `tenantId` + least-privilege `scopes[]` + optional expiry, and support **dual-key overlap rotation**.
  - For internal service-to-service (M2M) calls, prefer **mTLS**, **OAuth 2.0 Client Credentials + DPoP / Workload Identity (SPIFFE / OIDC)** over long-lived static shared API keys.

## 4. Architecture & Implementation
```typescript
import crypto from 'node:crypto';

export interface StoredApiKeyRecord {
  readonly keyId: string;
  readonly tenantId: string;
  readonly secretHashHex: string;
  readonly scopes: readonly string[];
  readonly expiresAtIso: string | null;
  readonly revoked: boolean;
}

export function verifyScopedApiKey(
  rawHeaderKey: string,
  pepper: string,
  requiredScope: string,
  lookupByKeyId: (keyId: string) => StoredApiKeyRecord | null
): { readonly allowed: boolean; readonly tenantId: string | null; readonly reason: string } {
  const parts = rawHeaderKey.split('_');
  if (parts.length !== 4 || parts[0] !== 'sk' || parts[1] !== 'live') {
    return { allowed: false, tenantId: null, reason: 'malformed_key' };
  }
  const keyId = parts[2] ?? '';
  const record = lookupByKeyId(keyId);
  if (!record || record.revoked) return { allowed: false, tenantId: null, reason: 'revoked_or_unknown' };
  if (record.expiresAtIso && Date.parse(record.expiresAtIso) <= Date.now()) {
    return { allowed: false, tenantId: null, reason: 'expired' };
  }
  const candidateHash = crypto.createHmac('sha256', pepper).update(rawHeaderKey, 'utf8').digest();
  const storedHash = Buffer.from(record.secretHashHex, 'hex');
  if (candidateHash.length !== storedHash.length || !crypto.timingSafeEqual(candidateHash, storedHash)) {
    return { allowed: false, tenantId: null, reason: 'invalid_secret' };
  }
  if (!record.scopes.includes(requiredScope)) {
    return { allowed: false, tenantId: null, reason: 'insufficient_scope' };
  }
  return { allowed: true, tenantId: record.tenantId, reason: 'verified' };
}
```

## 5. Platform / Vendor Variations
| Coexistence Scenario | Safe Routing / Precedence Rule | Pitfall to Avoid |
| :--- | :--- | :--- |
| **Cookie Session + Bearer JWKS JWT on Same API** | Check explicit `Authorization: Bearer` first (if present, MUST validate or `401` — never silently fall back to cookie!), else validate `__Host-sid` cookie + CSRF origin check | Skipping CSRF check when auth succeeds via cookie! |
| **External SSO + Local Password Account** | Match by immutable `(idp_issuer, idp_subject)` table `user_identities`, NOT mutable email | Allowing unverified OIDC email to silently hijack a local admin account |
| **Service-to-Service Delegation** | OAuth 2.0 Token Exchange (RFC 8693) preserving `act` (actor) + `sub` (end user) claims | Forwarding a super-admin M2M service token that bypasses end-user tenant boundaries |

## 6. Decision Matrix & Trade-Offs
| M2M Credential Type | Rotation Ergonomics | Theft Blast Radius | Best Fit |
| :--- | :---: | :---: | :--- |
| **OIDC Workload Identity / mTLS (Short-Lived)** | Automatic | Minimal (minutes, sender-constrained) | Cloud/K8s internal microservices |
| **OAuth 2.0 Client Credentials + DPoP** | High | Low (sender-constrained) | B2B partner APIs & regulated fintech (SNAP BI) |
| **Prefixed Hashed Scoped API Keys** | Manual (dual-key overlap) | Medium (bounded by scope + tenant + TTL) | Developer/webhook partner integrations |

## 7. Real Production Scenario
A government/enterprise portal migrates web logins to an external SSO while mobile clients still send JWKS-verified JWTs. An engineer leaves cookie auth and JWT auth on two separate middlewares — the JWT middleware sets `req.user.orgId` while the cookie middleware sets `req.session.tenantId`. Because downstream invoice queries read `req.user?.orgId`, cookie users trigger `undefined` lookups or bypass filters. Unifying both authenticators into a single strict `AuthenticatedPrincipal` contract + adding `test_sso_coexistence` integration tests resolves the mismatch permanently.

## 8. Failure Modes & Edge Cases
- **WRONG:** Replacing `file:../sdk/sso-client` with `npm install your-org-sso` without verifying registry ownership or Monarch approval.
- **RIGHT:** Run `official_first_verifier.py --check-auth-sdk`, inspect local SDK exports, preserve the local authoritative SDK, and document any workspace packaging notes separately.
- **WRONG:** Comparing API keys with `===` or storing raw API keys in Postgres so support staff can "view the user's key later."
- **RIGHT:** Show the generated API key **exactly once** on creation, store only `HMAC-SHA256` digest + prefix (`sk_live_abc1...`), and compare via `crypto.timingSafeEqual`.

## 9. Testing & Verification
- Run `python shadow-auth/scripts/auth_policy_verifier.py --check-sso-coexistence <cfg.json>`.
- Test auth-mode precedence: invalid `Bearer` token alongside a valid cookie MUST return `401` (never silently degrade to cookie!); valid cookie without valid `Origin` on `POST` MUST return `403`.

## 10. Operational Considerations
- Maintain a `last_used_at` timestamp (throttled updates, e.g., once/hour) and `key_prefix` on API key records so security teams can audit dormant keys and rotate keys cleanly without breaking active partners.

## 11. Authoritative References
- IETF RFC 8693 — *OAuth 2.0 Token Exchange* (`https://datatracker.ietf.org/doc/html/rfc8693`).
- IETF RFC 9449 — *OAuth 2.0 Demonstrating Proof of Possession (DPoP)* (`https://datatracker.ietf.org/doc/html/rfc9449`).
- Shadow Monarch Official-First Policy (`shadow-monarch/reference/OFFICIAL-FIRST-DEPENDENCY-POLICY.md`).

## 12. Limitations & When NOT to Use
- Static API keys (even hashed and scoped) should NEVER be embedded in public browser JavaScript bundles or mobile APKs; treat them strictly as confidential server-to-server secrets.
