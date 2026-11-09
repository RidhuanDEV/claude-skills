---
name: shadow-sec
description: "Run a comprehensive Fullstack Security, Secret Leak, Dependency Vulnerability, and OWASP Top 10 / API Auth audit before pushing or delivering a project. Trigger with /shadow-sec."
---

# /shadow-sec — Pre-Push Security, Secret Leak & OWASP Auditor (Shadow Army)

Use this skill whenever the **Monarch** invokes `/shadow-sec` or requests a security / VAPT check on a codebase.
Combines local static scanning with `shadow-monarch/reference/SECURITY.md` and `reference/SECOPS-PENTEST.md`.

## Audit Workflow

1. **Secret & Credential Leak Scan**:
   - Check `.gitignore` to ensure `.env`, `.env.*`, private keys (`.pem`, `.key`), and local credentials are ignored and NOT tracked in `git ls-files`.
   - Scan source files for hardcoded API keys, JWT secrets, tokens, database passwords, or private URLs.
2. **Dependency Vulnerability Check**:
   - Run read-only package audit (`npm audit --omit=dev`, `govulncheck`, `pip-audit`, or `composer audit` depending on stack).
3. **Backend API & Auth Guard Audit (OWASP API Top 10)**:
   - Verify all mutating/sensitive routes enforce authentication and server-side RBAC/ownership checks (preventing BOLA/IDOR).
   - Verify raw SQL queries use parameterized bindings (no string concatenation SQLi).
   - Verify CORS, rate limiting, helmet/security headers, and file upload MIME/size validation.
4. **Report Format**:
   - Deliver a concise findings table to the **Monarch** grouped by severity (`CRITICAL`, `HIGH`, `MEDIUM`, `LOW`) with exact `file:line` locations and concrete fixes.
