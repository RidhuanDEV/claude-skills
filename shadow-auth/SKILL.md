---
name: shadow-auth
description: Identity, Authentication (AuthN), Authorization (RBAC/ABAC), OAuth2/OIDC, SSO, Session & JWT Refresh Rotation Lifecycle, Multi-Tenant Isolation, and Security Audit Trails. Trigger with /shadow-auth.
---

# Shadow Auth (`/shadow-auth`) — Identity, RBAC/ABAC, Multi-Tenancy & Session Lifecycle

Use this skill whenever designing, implementing, or modifying login, registration, password reset, MFA, SSO/OAuth2/OIDC, role/permission guards, or multi-tenant data isolation.

---

## 1. Authentication & Credential Security Rules (OWASP ASVS V2 & V3)

1. **Password Hashing**: Always hash passwords with `Argon2id` (preferred) or `bcrypt` (cost $\ge 12$). Never use SHA-256/MD5 or reversible encryption for passwords.
2. **Account Enumeration Prevention**: Login, registration, and forgot-password endpoints must return generic user-facing messages and consistent timing so attackers cannot probe valid emails/usernames.
3. **Brute-Force & Credential Stuffing Protection**: Enforce rate limiting per IP and per account identifier (e.g., max 5 failed attempts per 15 minutes with progressive lockout or CAPTCHA challenge).
4. **Session & Token Lifecycle**:
   - **Cookie Sessions / Refresh Tokens**: Store in `HttpOnly`, `Secure`, `SameSite=Lax` (or `Strict`) cookies.
   - **JWT + Refresh Token Rotation**: Keep access tokens short-lived (`5–15 minutes`); persist hashed refresh tokens in DB/Redis with a `token_family_id` so reuse of a rotated refresh token immediately revokes the entire session family.
   - **Immediate Revocation**: Password change, role downgrade, or account deactivation must immediately invalidate all active sessions/refresh tokens for that user.

---

## 2. Authorization Architecture (RBAC, ABAC & Zero-IDOR)

1. **Server-Side Enforcement at Every Entry Point**:
   - UI route guards and hidden buttons are for UX only — **every** API route, GraphQL resolver, server action, and export endpoint MUST enforce both **Authentication** and **Authorization** on the server.
2. **Permission Matrix Design (`Role -> Permission -> Resource Scope`)**:
   - Prefer fine-grained permissions (`invoice:create`, `invoice:approve`, `invoice:read:own`, `invoice:read:tenant`) mapped to roles rather than scattering `if (user.role === 'ADMIN')` checks across controllers.
3. **Strict Multi-Tenant & Ownership Isolation (Anti-IDOR)**:
   - Never fetch, update, or delete by primary key `id` alone (`WHERE id = $1`).
   - Always scope queries by the authenticated user's `tenant_id` / `organization_id` (`WHERE id = $1 AND tenant_id = $2`) or enforce PostgreSQL Row-Level Security (`RLS`).
   - Never trust `tenant_id`, `user_id`, or `role` sent in the request body/query if it belongs to the authenticated caller's session context.

---

## 3. Immutable Security Audit Trail (`audit_logs`)

Every privileged or security-sensitive action (login success/failure, password reset, role/permission change, user impersonation, approval/rejection, data export, record deletion) MUST write an append-only audit log entry containing:
- `id` (UUIDv7 / ULID)
- `timestamp` (UTC `TIMESTAMPTZ`)
- `actor_user_id`, `actor_role`, `tenant_id`
- `ip_address`, `user_agent`, `request_id`
- `action` (e.g., `USER_ROLE_UPDATED`, `INVOICE_APPROVED`)
- `target_entity`, `target_id`
- `before_state` & `after_state` (with secrets/PII redacted)
