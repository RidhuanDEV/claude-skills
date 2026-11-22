---
name: shadow-auth
description: "Identity, AuthN & AuthZ Engineering Specialist. Use when designing or auditing login, Argon2id/MFA/Passkeys, OAuth2/OIDC PKCE, cookie/CSRF sessions, JWT/JWKS rotation, RBAC/ABAC/ReBAC, multi-tenant anti-IDOR isolation, SSO SDK coexistence (ridhuan-sso), or immutable security audit trails. Do NOT use for generic AppSec SAST/SSRF audits (/shadow-sec)."
---

# Shadow Auth (`/shadow-auth`) — Identity, AuthN, AuthZ & Multi-Tenant Isolation

Use this skill whenever the **Monarch** designs, implements, migrates, or audits authentication, sessions, OAuth2/OIDC SSO, Passkeys/MFA, JWT/JWKS rotation, RBAC/ABAC/ReBAC, multi-tenant anti-IDOR boundaries, API keys, or immutable security audit trails.

## 1. Core Engineering Principles & Non-Negotiables

1. **Hardened Credentials & Enumeration Defense (NIST SP 800-63-4 / ASVS 5.0):** Hash passwords with `Argon2id` (preferred) or `bcrypt >= 12`, block breached passwords, execute timing-safe dummy hashing on unknown users, and rate-limit per IP + account without permanent DoS lockouts.
2. **Session, Cookie & Token Discipline:** Use `__Host-` `HttpOnly`, `Secure`, `SameSite=Lax/Strict` cookies with CSRF `Origin` checks and fixation rotation on login/step-up; keep access JWTs `<= 5–15m` with pinned asymmetric `allowed_algs` (`EdDSA`/`RS256`/`ES256`, NEVER `alg: none`), dual-key `kid` JWKS rollover, rotating refresh tokens with **token-family reuse revocation**, and immediate revocation propagation (including `/shadow-realtime`).
3. **Server-Side Deny-by-Default & Zero-IDOR:** Enforce AuthN + AuthZ on every server route/resolver/worker (never UI-only). Scope every multi-tenant DB query by authenticated `tenant_id` (`WHERE id = $1 AND tenant_id = $2` + Postgres RLS); reject client-supplied `tenant_id`/`role`/`username` (confused deputy & mass assignment).
4. **Local SSO SDK Preservation (`OFFICIAL-FIRST-DEPENDENCY-POLICY.md`):** Inspect existing local/internal SSO SDKs (`ridhuan-sso` / `file:../sdk/sso-client`) first via `official_first_verifier.py --check-auth-sdk`; NEVER silently replace with an unverified npm lookalike or trust frontend `username` without server-verified claims. Resolve coexisting SSO + cookie + JWKS JWT into one canonical `AuthenticatedPrincipal`.
5. **Immutable Audit Trails & Search/RAG Policy Handoff:** Write append-only redacted `security_audit_logs` on every privileged mutation. For search/RAG comparisons, obtain the policy revision independently from the policy owner, freeze permitted IDs & revocations per query, inspect ranked + generation context separately, and verify pre-top-K enforcement in the serving code independently.

## 2. Deterministic Verification CLI & Scenario Benchmarks

Run offline checks (`L0`/`L1`) before claiming `VERIFIED-LOCAL`:
```powershell
python "shadow-auth/scripts/auth_policy_verifier.py" --self-test
python "shadow-auth/scripts/auth_policy_verifier.py" --check-session-config path/to/session_cfg.json
python "shadow-auth/scripts/auth_policy_verifier.py" --check-policy-matrix path/to/policy_matrix.json
python "shadow-auth/scripts/auth_policy_verifier.py" --check-sso-coexistence path/to/sso_cfg.json
python -m unittest discover -s "shadow-auth/tests" -v
```
Graded specialist scenarios live in [evaluations.md](evaluations.md) (10 scenarios covering cross-tenant IDOR, SSO+cookie+JWKS coexistence, `ridhuan-sso` preservation, refresh-token replay, Passkeys, and ReBAC Zookie consistency).

## Reference Guide

Load **only** the 1–2 modules matching the active subtask (never load all 8 at once):

| Task / Scenario | Tier | Load Reference |
| :--- | :--- | :--- |
| AuthN threat model, Argon2id/bcrypt, NIST SP 800-63-4, timing-safe anti-enumeration & recovery | CORE | [references/01-authn-threat-model-and-credentials.md](references/01-authn-threat-model-and-credentials.md) |
| OAuth 2.1 / OIDC Authorization Code + PKCE `S256`, `state`/`nonce`, ID-token checks & BFF pattern | CORE | [references/02-oauth2-oidc-and-pkce-flows.md](references/02-oauth2-oidc-and-pkce-flows.md) |
| `__Host-` `HttpOnly`/`Secure` cookies, CSRF `Origin`, fixation rotation & instant revocation | CORE | [references/03-sessions-cookies-csrf-and-revocation.md](references/03-sessions-cookies-csrf-and-revocation.md) |
| Short-lived JWTs, pinned `allowed_algs`, refresh-token family replay revocation & JWKS `kid` rollover | CORE | [references/04-jwt-jwks-and-key-rotation.md](references/04-jwt-jwks-and-key-rotation.md) |
| Passkeys / WebAuthn (FIDO2) `origin`/`rpIdHash`/`signCount`, TOTP replay protection & step-up MFA | ADVANCED | [references/05-passkeys-webauthn-and-mfa.md](references/05-passkeys-webauthn-and-mfa.md) |
| Deny-by-default RBAC/ABAC/ReBAC (Zanzibar Zookie), multi-tenant anti-IDOR & mass-assignment guard | CORE | [references/06-authz-rbac-abac-rebac-and-multi-tenant.md](references/06-authz-rbac-abac-rebac-and-multi-tenant.md) |
| Local SSO SDK (`ridhuan-sso`) preservation, cookie+JWKS coexistence, M2M mTLS/DPoP & hashed API keys | SPECIALIST | [references/07-sso-sdk-coexistence-and-m2m.md](references/07-sso-sdk-coexistence-and-m2m.md) |
| Append-only `security_audit_logs`, 5-case policy test matrix & search/RAG policy-revision handoff | OPERATIONAL | [references/08-audit-trails-and-auth-security-testing.md](references/08-audit-trails-and-auth-security-testing.md) |

Do not load unrelated references unnecessarily.
