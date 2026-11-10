---
name: shadow-sec
description: Comprehensive Application & SDLC Security Auditor grounded in NIST SSDF (SP 800-218) and OWASP ASVS 5.0.0. Covers STRIDE Threat Modeling, Supply-Chain Security & SBOM, SAST/DAST, Secret Scanning, and Verifiable API/Auth/Data Controls. Trigger with /shadow-sec.
---

# `/shadow-sec` — SDLC Security, Threat Modeling, Supply-Chain & OWASP ASVS 5.0 Auditor

Use this skill whenever the **Monarch** invokes `/shadow-sec`, before releasing to Staging/Production (**SDLC Stage 4 & Stage 6 Security Gate**), or when performing a security / VAPT review.

Grounded in two authoritative international standards documented in [`references/NIST-SSDF-AND-OWASP-ASVS-5.md`](references/NIST-SSDF-AND-OWASP-ASVS-5.md):
1. **[NIST SSDF (SP 800-218)](https://csrc.nist.gov/pubs/sp/800/218/final)** — Secure Software Development Framework across the entire SDLC (`PO`, `PS`, `PW`, `RV`).
2. **[OWASP ASVS 5.0.0](https://asvs.owasp.org/)** — Application Security Verification Standard (Level 2 standard for enterprise/production apps; Level 3 for critical financial/government apps).

---

## 1. The 5-Pillar Security Audit Workflow (Read-Only by Default)

### Pillar 1: STRIDE Threat Modeling (Architecture & Feature Level)
Evaluate affected components against the 6 STRIDE threat categories:
- **S — Spoofing**: Can an attacker forge identity, webhook signatures, or JWT claims? (Check `/shadow-auth` & `/shadow-integrate`).
- **T — Tampering**: Can request parameters (`role`, `price`, `tenant_id`, `status`) be mass-assigned or modified in transit?
- **R — Repudiation**: Are sensitive state transitions and approvals recorded in an immutable `audit_logs` table?
- **I — Information Disclosure**: Are stack traces, internal IDs, other tenants' records (IDOR), or PII leaked in API responses or logs?
- **D — Denial of Service**: Are login, file upload, export, and expensive search routes protected by rate limits, pagination bounds, and timeouts?
- **E — Elevation of Privilege**: Are server-side RBAC/ABAC guards enforced on every controller/resolver?

### Pillar 2: Secret Scanning & Provenance Protection (`NIST SSDF PS.1`)
- Verify `.gitignore` blocks `.env*`, `*.pem`, `*.key`, `*.p12`, `credentials.json`, and local SQLite/dump files.
- Scan both working files and `git ls-files` for hardcoded API keys, database DSNs with passwords, private keys, or Bearer tokens.

### Pillar 3: Supply-Chain Security, Lockfile Integrity & SBOM (`NIST SSDF PW.4` & `ASVS V14`)
- Run package vulnerability audits (`npm audit --omit=dev`, `pip-audit`, `govulncheck`, `composer audit`, `cargo audit`).
- Verify lockfiles (`package-lock.json`, `pnpm-lock.yaml`, `poetry.lock`, `go.sum`) are committed and in sync.
- Flag unmaintained, typosquatted, or overly permissive packages, and generate a CycloneDX/SPDX Software Bill of Materials (`SBOM`) when preparing client handover (`/shadow-handover`).

### Pillar 4: Verifiable OWASP ASVS 5.0 Control Audit (`SAST` Code Inspection)
Read [`references/NIST-SSDF-AND-OWASP-ASVS-5.md`](references/NIST-SSDF-AND-OWASP-ASVS-5.md) and verify:
- **V1 Architecture & Tenant Isolation**: Zero cross-tenant data leakage (`tenant_id` scoped on all queries).
- **V2 & V3 AuthN & Session**: Argon2id/bcrypt hashing, `HttpOnly`/`Secure`/`SameSite` cookies, refresh token rotation.
- **V4 Access Control**: Zero BOLA/IDOR; server-side permission checks on every route.
- **V5 Validation & Injection Prevention**: Parameterized SQL queries only (`0` string interpolation in SQL/shell commands); strict schema validation; XSS output encoding.
- **V8 Data Protection**: Secrets/PII redacted from logs; sensitive fields encrypted at rest; strict `Cache-Control: no-store` on private responses.
- **V12 Files & SSRF**: File uploads validated by MIME magic bytes + size limits + randomized storage filenames; outbound URLs checked against private IP ranges (`127.0.0.1`, `169.254.169.254`, `10.0.0.0/8`) to prevent SSRF.

### Pillar 5: Actionable Security Report Format
Deliver findings ordered by severity (`CRITICAL`, `HIGH`, `MEDIUM`, `LOW`) with:
- **ASVS / NIST SSDF Control ID** (e.g., `ASVS V4.2.1 — IDOR`, `NIST PW.8`)
- **Exact Location** (`file:line` or endpoint route)
- **Exploit Scenario & Business Impact**
- **Concrete Remediation Patch**
