# 04. JWT, JWKS & Key Rotation

## 1. Purpose & Activation Conditions
Harden JWT signing, verification, short-lived access tokens, refresh-token rotation with reuse detection, and zero-downtime asymmetric JWKS key rotation. Load when designing or reviewing JWT-based APIs, JWKS verifiers, or token refresh pipelines.

## 2. Prerequisites
- Asymmetric keypair management (`EdDSA`/`ES256`/`RS256` via KMS/Secrets Manager) and persistent store (DB/Redis) for refresh-token families.

## 3. Technical Principles & Constraints
- **Strict Verification Rules (Zero Algorithm Confusion):**
  1. Explicitly pin an allowlist of **asymmetric** algorithms (`['EdDSA']` or `['RS256', 'ES256']`) in the verifier — NEVER derive the verification algorithm from the untrusted JWT header `alg`, NEVER accept `alg: "none"`, and NEVER allow `HS256` with an RSA public key!
  2. Always verify `iss`, `aud`, `exp`, `nbf`, and `sub` (plus `tid`/`tenant_id` for multi-tenant systems).
  3. Never trust `jku`, `x5u`, or embedded `jwk` header URLs supplied inside the token (SSRF + key-injection takeover!); fetch JWKS exclusively from a server-configured allowlisted issuer URL.
- **Short-Lived Access + Rotating Refresh Families:**
  - Access JWT TTL: **`5–15 minutes` (`<= 900s`)**. Never issue 7-day or 30-day non-revocable access JWTs!
  - Refresh tokens: opaque `>= 256-bit` CSPRNG secrets stored **hashed (`SHA-256`)** in DB with `(token_hash, family_id, user_id, replaced_by_hash, revoked_at, expires_at)`.
  - **Reuse Detection (Theft Containment):** Every `/auth/refresh` atomically marks the old refresh token rotated (`replaced_by_hash`) and mints a fresh pair. If an **already-rotated** refresh token is ever presented again, assume token theft and **immediately revoke the ENTIRE `family_id`**!
- **Zero-Downtime JWKS Key Rotation (`kid` Rollover):**
  1. Generate new key `kid_v2` and publish **BOTH** `kid_v1` and `kid_v2` in `/.well-known/jwks.json`.
  2. Wait `>= jwks_cache_ttl` (e.g., 15–60 min) so all verifiers cache `kid_v2`.
  3. Switch signer to sign new tokens with `kid_v2`.
  4. Wait `>= max_access_ttl` (e.g., 15 min) until all `kid_v1` tokens expire naturally.
  5. Remove `kid_v1` from JWKS (or remove immediately during emergency key compromise!).

## 4. Architecture & Implementation
```typescript
export interface RefreshTokenRow {
  readonly tokenHashHex: string;
  readonly familyId: string;
  readonly userId: string;
  readonly tenantId: string;
  readonly rotatedAtIso: string | null;
  readonly revokedAtIso: string | null;
  readonly expiresAtIso: string;
}

export interface RefreshStore {
  findByHash(tokenHashHex: string): Promise<RefreshTokenRow | null>;
  revokeEntireFamily(familyId: string, reason: string): Promise<void>;
  rotateAtomically(oldHash: string, newRow: RefreshTokenRow): Promise<boolean>;
}

export type RefreshOutcome =
  | { readonly status: 'ROTATED'; readonly userId: string; readonly tenantId: string; readonly familyId: string }
  | { readonly status: 'REPLAY_FAMILY_REVOKED' }
  | { readonly status: 'INVALID_OR_EXPIRED' };

export async function handleRefreshTokenRotation(
  presentedHashHex: string,
  nowMs: number,
  store: RefreshStore,
  nextRowBuilder: (prev: RefreshTokenRow) => RefreshTokenRow
): Promise<RefreshOutcome> {
  const existing = await store.findByHash(presentedHashHex);
  if (!existing) return { status: 'INVALID_OR_EXPIRED' };

  if (existing.revokedAtIso !== null || Date.parse(existing.expiresAtIso) <= nowMs) {
    return { status: 'INVALID_OR_EXPIRED' };
  }

  // Reuse of an already-rotated token signals theft -> burn the entire session family immediately
  if (existing.rotatedAtIso !== null) {
    await store.revokeEntireFamily(existing.familyId, 'refresh_token_replay_detected');
    return { status: 'REPLAY_FAMILY_REVOKED' };
  }

  const nextRow = nextRowBuilder(existing);
  const rotated = await store.rotateAtomically(existing.tokenHashHex, nextRow);
  if (!rotated) {
    // Concurrent race on same refresh token -> treat as potential replay/race and revoke family safely
    await store.revokeEntireFamily(existing.familyId, 'concurrent_refresh_conflict');
    return { status: 'REPLAY_FAMILY_REVOKED' };
  }

  return { status: 'ROTATED', userId: existing.userId, tenantId: existing.tenantId, familyId: existing.familyId };
}
```

## 5. Platform / Vendor Variations
| Library / Stack | Recommended Verification Setup | Classic Pitfall |
| :--- | :--- | :--- |
| **Node.js (`jose`)** | `jwtVerify(token, createRemoteJWKSet(url), { algorithms: ['EdDSA', 'RS256'], issuer, audience })` | Using `decodeJwt()` instead of `jwtVerify()`, or omitting `algorithms` |
| **Python (`PyJWT`)** | `jwt.decode(token, key, algorithms=["RS256"], audience=..., issuer=...)` | Passing untrusted `header["alg"]` into `algorithms=[...]` |
| **Go (`golang-jwt/jwt/v5`)** | `jwt.WithValidMethods([]string{"EdDSA", "RS256"})`, `jwt.WithAudience(...)`, `jwt.WithIssuer(...)` | Forgetting `WithValidMethods` check inside keyfunc |

## 6. Decision Matrix & Trade-Offs
| Signing Algorithm | Key Size / Speed | Multi-Service Verification | Recommendation |
| :--- | :---: | :---: | :--- |
| **`EdDSA` (Ed25519)** | Tiny & fastest | Public JWKS (no shared secret) | **Best modern default** |
| **`ES256` / `RS256`** | Standard / Universal | Public JWKS (no shared secret) | **Universal enterprise / OIDC standard** |
| **`HS256` (Symmetric)** | Fast | Every verifier needs signing secret! | Internal single-service ONLY; avoid across microservices |

## 7. Real Production Scenario
An identity team rotates its RS256 signing key in production by overwriting the single key in `/.well-known/jwks.json` directly. Every active user's 10-minute access token immediately fails verification across 14 backend microservices, causing a 10-minute global outage. Adopting the 5-step dual-key `kid` overlap rollover eliminates rotation downtime permanently.

## 8. Failure Modes & Edge Cases
- **WRONG:** Storing sensitive PII (`nik`, `salary`, `passwordHash`) or massive permission arrays (500 permissions -> `8 KB` HTTP header overflow!) inside JWT payloads (JWTs are Base64URL-encoded, NOT encrypted!).
- **RIGHT:** Keep JWT claims minimal (`sub`, `tid`, `role`/`ver`, `iss`, `aud`, `exp`, `jti`) and resolve granular permissions/ABAC from fast server cache/ReBAC.
- **WRONG:** Allowing a single-tab SPA race (two simultaneous `401` fetches calling `/auth/refresh` concurrently) to self-revoke legitimate users without client-side refresh singleflight locking.
- **RIGHT:** Coalesce concurrent client `/auth/refresh` calls via a single in-flight promise (or tiny 5s grace window strictly bound to identical session/device fingerprint where appropriate) while keeping hard family revocation on post-window replay.

## 9. Testing & Verification
- Run `python shadow-auth/scripts/auth_policy_verifier.py --check-session-config <cfg.json>`.
- Add automated JWT negative tests: `alg: none` -> `401`, `HS256` signed with RSA PEM -> `401`, expired `exp` -> `401`, wrong `aud` -> `401`, replayed rotated refresh token -> `401` AND revokes active sibling token in same `family_id`.

## 10. Operational Considerations
- Monitor `refresh_token_replay_detected` counters as a high-priority security alert (sudden spike signals either an active XSS/MITM theft campaign or a broken client refresh mutex).

## 11. Authoritative References
- IETF RFC 8725 — *JSON Web Token Best Current Practices* (`https://datatracker.ietf.org/doc/html/rfc8725`).
- IETF RFC 7517 / RFC 7519 — *JSON Web Key (JWK) & JSON Web Token (JWT)*.
- OWASP JSON Web Token Cheat Sheet (`https://cheatsheetseries.owasp.org/cheatsheets/JSON_Web_Token_for_Java_Cheat_Sheet.html`).

## 12. Limitations & When NOT to Use
- Do NOT use JWTs as browser session cookies for monolithic web apps when a simple Redis/DB server-side session (`03`) gives instant revocation, smaller headers, and zero key-management complexity.
