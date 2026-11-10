# NIST SSDF (SP 800-218) & OWASP ASVS 5.0.0 Verification Matrix

Reference guide for `/shadow-sec` to map every security review and SDLC gate to verifiable international standards.

---

## 1. NIST SSDF (SP 800-218) Integration Across the Shadow Army SDLC

| NIST SSDF Practice Group | Practice ID | Shadow Army SDLC Stage & Responsible Skill | Verifiable Artifact |
| :--- | :--- | :--- | :--- |
| **Prepare the Organization (`PO`)** | `PO.1` / `PO.3` | Toolchain & baseline guardrails (`shadow-monarch`, `/shadow-bootstrap`) | Strict compiler flags, linter, `.gitignore`, pre-commit secret guard |
| **Protect the Software (`PS`)** | `PS.1` / `PS.2` / `PS.3` | Source code integrity, secret protection & release provenance (`/shadow-git`, `/shadow-release`, `/shadow-handover`) | Zero secrets in Git history, signed/tagged releases, SBOM inventory |
| **Produce Well-Secured Software (`PW`)** | `PW.1` / `PW.4` / `PW.5` / `PW.8` | Secure architecture (`/shadow-architect`), Auth (`/shadow-auth`), dependency hygiene & automated testing (`/shadow-test`, `/shadow-sec`) | STRIDE threat model, parameterized queries, `0` high/critical CVEs, 401/403 IDOR tests |
| **Respond to Vulnerabilities (`RV`)** | `RV.1` / `RV.2` / `RV.3` | Post-production monitoring, triage, hotfix & RCA (`/shadow-observe`, `/shadow-maintain`) | CVE patch SLA, regression test for every security fix, blameless RCA |

---

## 2. OWASP ASVS 5.0.0 Core Verification Checklist (Level 2 Baseline)

| ASVS Category | Control Requirement | Verification Method in Codebase |
| :--- | :--- | :--- |
| **V1: Architecture & Threat Modeling** | Trust boundaries, tenant isolation, and third-party adapters explicitly separated. | Verify every DB query on multi-tenant tables filters by authenticated `tenant_id`. |
| **V2: Authentication** | Passwords hashed with `Argon2id` or `bcrypt` ($\ge 12$ rounds); brute-force rate limiting active; generic error messages on login/forgot-password. | Inspect auth service and Nginx/app rate-limiter config. |
| **V3: Session Management** | Session/Refresh tokens use CSPRNG ($\ge 128$ bits entropy), `HttpOnly`, `Secure`, `SameSite`, and revoke immediately on logout/password reset. | Inspect cookie options and token revocation table/Redis store. |
| **V4: Access Control** | Deny-by-default; RBAC/ABAC enforced server-side on every API route; object ownership verified (anti-BOLA/IDOR); mass assignment blocked via strict DTO allowlists. | Check route middleware/guards and DTO schemas (`zod`/`class-validator`/`pydantic`). |
| **V5: Input Validation & Injection** | All SQL/NoSQL/OS queries use parameterized bindings; HTML output escaped; JSON payloads bounded in size (`client_max_body_size` / body-parser limit). | Grep for raw SQL template strings (`$queryRawUnsafe`, `fmt.Sprintf("SELECT...`), `exec()`, `eval()`, `dangerouslySetInnerHTML`. |
| **V6: Cryptography at Rest** | Standard algorithms only (`AES-256-GCM`, `Ed25519`, `RS256`); zero hardcoded keys/IVs; keys loaded from secret manager/env. | Inspect crypto helpers and `.env.example`. |
| **V7: Error Handling & Logging** | Production errors return generic messages with `requestId` (never raw stack traces or SQL errors); logs exclude passwords, tokens, and PII. | Inspect global exception filter and logger redaction list. |
| **V8: Data Protection** | Sensitive endpoints set `Cache-Control: no-store`; PII export/deletion follows retention rules (`/shadow-data`). | Inspect response headers and export authorization guards. |
| **V9 & V10: Communications & Webhooks** | TLS 1.2/1.3 enforced; HSTS active; webhooks verified via constant-time `HMAC-SHA256` + timestamp replay window. | Inspect Nginx/Caddy TLS config and webhook handlers (`/shadow-integrate`). |
| **V12: Files, Uploads & SSRF** | Upload size bounded, MIME magic bytes checked, stored outside webroot with generated UUID name; user-supplied URLs validated against internal/metadata IP blocklists. | Inspect upload middleware and outbound HTTP clients. |
| **V13: API & Web Service** | CORS origin explicitly allowlisted (never `*` with credentials); GraphQL depth/complexity bounded; list endpoints paginated (`limit <= 100`). | Inspect CORS config and pagination DTOs. |
| **V14: Configuration & Supply Chain** | Lockfile committed; `npm/pip/composer/go audit` clean; debug endpoints disabled in `production`. | Run package audit CLI and inspect startup config. |
