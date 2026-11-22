# 02. OAuth 2.0, OIDC & PKCE Flows

## 1. Purpose & Activation Conditions
Implement RFC-compliant OAuth 2.0 / OpenID Connect (OIDC) login, social/enterprise SSO, and token exchanges resistant to authorization-code interception, CSRF, open-redirect hijacking, and token-substitution attacks. Load when integrating Google/Microsoft/Keycloak/Okta/custom OIDC IdPs.

## 2. Prerequisites
- Registered OAuth client with exact HTTPS redirect URIs (zero wildcards) and server-side session/state store.

## 3. Technical Principles & Constraints
- **Authorization Code + PKCE (`S256`) Mandatory (RFC 7636 & OAuth 2.1):** Use ONLY the Authorization Code flow with **PKCE (`code_challenge_method=S256`)** for BOTH public clients (SPA/mobile) and confidential web backends. NEVER use legacy Implicit (`response_type=token`) or Resource Owner Password Credentials (`grant_type=password`).
- **Cryptographic `state` & `nonce` Binding:**
  - Generate `>= 128-bit` CSPRNG `state` bound to the user's browser (`HttpOnly`, `Secure`, `SameSite=Lax` cookie) to prevent login-CSRF / account-linking hijacking.
  - Generate `>= 128-bit` CSPRNG `nonce` stored server-side/cookie and verify exact match inside the signed OIDC `id_token` to block replay attacks.
- **Strict ID Token Verification:** Validate ALL 6 claims via the IdP's verified JWKS endpoint (never decode base64 without signature verification!):
  1. Cryptographic signature + pinned asymmetric `alg` (`RS256`/`ES256`/`EdDSA`, reject `none`),
  2. Exact `iss` (issuer),
  3. Exact `aud` (your `client_id`),
  4. `exp` / `iat` (bounded clock skew `<= 60s`),
  5. Exact `nonce` match,
  6. `email_verified === true` before linking an existing local account by email (NEVER auto-merge on unverified email!).
- **BFF (Backend-for-Frontend) Pattern for Browser Apps:** For web SPAs handling sensitive data, terminate OAuth token exchange on your **confidential backend (BFF)** and issue a hardened `HttpOnly` session cookie to the browser instead of exposing OAuth access/refresh tokens in `localStorage` (eliminates XSS token exfiltration!).

## 4. Architecture & Implementation
```typescript
import { createHash, randomBytes, timingSafeEqual } from 'node:crypto';

export interface PkceChallengePair {
  readonly codeVerifier: string;
  readonly codeChallenge: string;
  readonly codeChallengeMethod: 'S256';
  readonly state: string;
  readonly nonce: string;
}

export function createOidcAuthRequestParams(): PkceChallengePair {
  const codeVerifier = randomBytes(32).toString('base64url');
  const codeChallenge = createHash('sha256').update(codeVerifier, 'ascii').digest('base64url');
  return {
    codeVerifier,
    codeChallenge,
    codeChallengeMethod: 'S256',
    state: randomBytes(24).toString('base64url'),
    nonce: randomBytes(24).toString('base64url'),
  };
}

export function assertOidcCallbackStateMatches(expectedState: string, receivedState: string): void {
  const a = Buffer.from(expectedState, 'utf8');
  const b = Buffer.from(receivedState, 'utf8');
  if (a.length === 0 || a.length !== b.length || !timingSafeEqual(a, b)) {
    throw new Error('OIDC_STATE_MISMATCH_CSRF_BLOCKED');
  }
}

export interface VerifiedIdTokenClaims {
  readonly iss: string;
  readonly sub: string;
  readonly aud: string | readonly string[];
  readonly exp: number;
  readonly nonce?: string;
  readonly email?: string;
  readonly email_verified?: boolean;
}

export function assertIdTokenClaimsValid(
  claims: VerifiedIdTokenClaims,
  expected: { readonly issuer: string; readonly clientId: string; readonly nonce: string; readonly nowSec: number }
): void {
  if (claims.iss !== expected.issuer) throw new Error('OIDC_ISSUER_MISMATCH');
  const audList = Array.isArray(claims.aud) ? claims.aud : [claims.aud];
  if (!audList.includes(expected.clientId)) throw new Error('OIDC_AUDIENCE_MISMATCH');
  if (claims.exp <= expected.nowSec - 60) throw new Error('OIDC_TOKEN_EXPIRED');
  if (!claims.nonce || claims.nonce !== expected.nonce) throw new Error('OIDC_NONCE_MISMATCH');
}
```

## 5. Platform / Vendor Variations
| Client Type | Recommended OAuth 2.1 / OIDC Architecture | Token Storage Rule |
| :--- | :--- | :--- |
| **Server-Rendered / BFF Web App (Next.js / Express / Laravel)** | Confidential Authorization Code + PKCE `S256` on backend | Tokens stored server-side (encrypted Redis/DB); browser holds `HttpOnly` session cookie |
| **Native Mobile (Android / iOS / Flutter)** | System Browser (`Custom Tabs` / `ASWebAuthenticationSession`) + PKCE `S256` — **NEVER embedded WebViews** | Android Keystore / iOS Keychain (`/shadow-mobile`) |
| **Pure Static SPA (No BFF)** | Public Authorization Code + PKCE `S256` + short-lived in-memory access tokens + rotating refresh | Avoid `localStorage` for high-sensitivity tokens; upgrade to BFF when handling money/PII |

## 6. Decision Matrix & Trade-Offs
| Flow / Pattern | XSS Token Theft Risk | Implementation Complexity | Verdict |
| :--- | :---: | :---: | :--- |
| **BFF + `HttpOnly` Cookie** | Very Low (tokens unreachable from JS) | Medium | **Recommended default for production web apps** |
| **SPA PKCE + `localStorage` JWT** | High (any XSS steals refresh token) | Low | Avoid for fintech/enterprise/PII apps |
| **Implicit Flow (`#access_token`)** | Extreme (URL history/referrer leaks) | Low | **Deprecated & FORBIDDEN (OAuth 2.1)** |

## 7. Real Production Scenario
A SaaS app allows `"Sign in with Google"` and automatically links incoming OIDC logins to existing local accounts solely by matching `claims.email` WITHOUT checking `email_verified === true` and WITHOUT verifying `state`. An attacker registers an unverified third-party OIDC account with a victim's corporate email (or tricks the victim's browser via login-CSRF) and hijacks the victim's admin workspace. Enforcing `state` + `nonce`, verifying `email_verified === true`, and requiring explicit confirmation before linking an OIDC identity to an existing password account closes both account-takeover vectors.

## 8. Failure Modes & Edge Cases
- **WRONG:** Binding enterprise tenant membership strictly from the user's email domain suffix (`@acme.com`) across a multi-tenant IdP (or trusting `returnTo` query parameter blindly -> open redirect).
- **RIGHT:** Bind tenant strictly from the verified IdP connection/organization claim (`tid`/`org_id`) and restrict post-login `returnTo` strictly to relative same-origin paths (`/^\/(?!\/)/`).
- **WRONG:** Using `access_token` as an authentication proof without validating audience/introspection, or decoding `id_token` JWT payload via `JSON.parse(atob(...))` without signature verification.
- **RIGHT:** Verify `id_token` signatures against the IdP's HTTPS JWKS endpoint using a vetted library (`jose`, `openid-client`, `authlib`).

## 9. Testing & Verification
- Test negative OIDC callback scenarios in integration tests: mismatched `state` -> `403`, wrong `nonce` -> `401`, wrong `aud` -> `401`, `email_verified: false` -> blocks automatic account merge, open-redirect `returnTo=https://evil.test` -> sanitized to `/`.
- Run `python shadow-auth/scripts/auth_policy_verifier.py --check-sso-coexistence <cfg.json>`.

## 10. Operational Considerations
- Cache IdP JWKS keys with bounded TTL and automatic refresh-on-unknown-`kid` (rate-limited to prevent JWKS-fetch DoS on forged `kid` floods).

## 11. Authoritative References
- IETF RFC 7636 — *Proof Key for Code Exchange (PKCE)* (`https://datatracker.ietf.org/doc/html/rfc7636`).
- IETF RFC 9700 — *Best Current Practice for OAuth 2.0 Security* (`https://datatracker.ietf.org/doc/html/rfc9700`).
- OpenID Connect Core 1.0 Specification (`https://openid.net/specs/openid-connect-core-1_0.html`).

## 12. Limitations & When NOT to Use
- Do NOT implement a custom OAuth 2.0 Authorization Server from scratch unless building an identity product; reuse proven standards-compliant IdPs (Keycloak, Auth0, Entra ID, Cognito, Ory, or your verified existing internal SSO server).
