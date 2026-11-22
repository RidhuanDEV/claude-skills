# 08. Audit Trails, RAG Policy Handoff & Auth Testing

## 1. Purpose & Activation Conditions
Design immutable security audit logs (`audit_logs`), execute automated negative authorization test matrices, and enforce synchronized policy-revision handoffs for search and RAG retrieval (`/shadow-search`, `/shadow-eval`). Load when implementing audit logging, writing auth test suites, or auditing auth boundaries for RAG/search systems.

## 2. Prerequisites
- Centralized auth middleware (`06`, `07`) and redacting structured logger (`BACKEND.md §12`).

## 3. Technical Principles & Constraints
- **Strict Separation: Ephemeral App Logs vs Immutable Security `audit_logs`:** Operational logs expire in 14–30 days; security/business audit trails (`login_success`, `login_failed`, `mfa_changed`, `role_updated`, `impersonation_started`, `api_key_created`, `bulk_export`, `record_deleted`) persist in an **append-only `audit_logs` table** with `id` (UUIDv7), `timestamp` (UTC `TIMESTAMPTZ`), `actor_user_id`, `actor_role`, `tenant_id`, `ip_address`, `user_agent`, `request_id`, `action`, `target_entity`, `target_id`, and redacted `before_state`/`after_state`.
- **Zero Secret Leakage in Audit & Test Logs:** Redact `Authorization`, `Cookie`, `x-api-key`, password fields, TOTP seeds, and raw PII (NIK/NPWP) BEFORE writing audit records or test failure artifacts.
- **Mandatory 5-Case Automated Policy Matrix per Protected Route:**
  1. **Unauthenticated caller** -> `401` (preserving established `WWW-Authenticate` challenge if any),
  2. **Authenticated wrong-tenant caller (guessed ID)** -> `403` refusal or `404` concealment (preserving service contract),
  3. **Authenticated lower-role caller (e.g., `viewer` -> `admin-export`)** -> `403`,
  4. **Revoked / downgraded token or spoofed client headers (`X-Role: admin`, `X-Username: boss`)** -> `401`/`403` (client headers ignored!),
  5. **Authorized owner/role in matching tenant** -> `200`/`201` (verifying zero cross-tenant rows in response body).
- **Search & Generated-Answer Policy Handoff:** When evaluating or serving retrieval/RAG (`/shadow-search`, `/shadow-eval`):
  - Obtain the current policy revision independently from the authorized policy owner (never trust candidate trace metadata alone).
  - Freeze tenant, principal-specific permitted document IDs, and revocations for each query at that exact policy revision.
  - Inspect ranked results AND actual generation context separately (including entries below metric cutoff); missing or stale authorization evidence requires a release **HOLD**.
  - Verify pre-top-K enforcement directly in the serving implementation, not just from returned trace logs!

## 4. Architecture & Implementation
```sql
-- Append-only immutable security audit trail schema (PostgreSQL)
CREATE TABLE security_audit_logs (
  id             UUID PRIMARY KEY,               -- UUIDv7 for time-ordered indexing
  occurred_at    TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  tenant_id      UUID NOT NULL,
  actor_user_id  UUID,                           -- NULL allowed only for unauthenticated login_failed
  actor_role     TEXT NOT NULL,
  action         TEXT NOT NULL,                  -- e.g. 'USER_ROLE_UPDATED', 'INVOICE_EXPORTED'
  target_entity  TEXT NOT NULL,
  target_id      TEXT NOT NULL,
  request_id     TEXT NOT NULL,
  ip_address     INET,
  user_agent     TEXT,
  before_state   JSONB,                          -- Redacted: zero passwords/tokens/raw PII
  after_state    JSONB
);

CREATE INDEX idx_audit_tenant_time ON security_audit_logs (tenant_id, occurred_at DESC);
-- Enforce append-only discipline via DB role privileges (app role gets INSERT + SELECT only, NO UPDATE/DELETE!)
REVOKE UPDATE, DELETE ON security_audit_logs FROM app_service_role;
```
Automated policy-matrix test execution:
```powershell
python "shadow-auth/scripts/auth_policy_verifier.py" --self-test
python -m unittest discover -s "shadow-auth/tests" -v
```

## 5. Platform / Vendor Variations
| Verification Layer | Tooling / Method | Approval Level |
| :--- | :--- | :--- |
| **Offline Config & Matrix Verification** | `auth_policy_verifier.py` | `L0`/`L1` (safe default) |
| **Local Loopback HTTP Matrix Tests** | `shadow-auth/tests/test_auth_policy_matrix.py` / Supertest / Pytest | `L1` (ephemeral local fixture) |
| **Live External Staging/Prod Auth Probing** | DAST / Pentest | **`L3`/`L4` (FORBIDDEN without explicit Monarch approval)** |

## 6. Decision Matrix & Trade-Offs
| Audit Event Category | Synchronous Write in Same DB Tx? | Why |
| :--- | :---: | :--- |
| **Role/Permission Change, Approval, Deletion, Export** | **YES (Same ACID Tx)** | Action MUST NOT succeed if audit record fails to commit |
| **High-Frequency Login Failure Burst** | Async / Dedicated Audit Stream | Prevents credential-stuffing DoS from saturating primary OLTP DB |

## 7. Real Production Scenario
During an ISO 27001 / POJK audit, an application cannot prove who granted `superadmin` to a compromised account because role changes were only printed to ephemeral stdout logs rotated every 7 days — and stdout logs accidentally printed raw `Authorization: Bearer` headers. Introducing the append-only `security_audit_logs` table (with `REVOKE UPDATE, DELETE` on the app DB role), header redaction middleware, and synchronous transactional writes on privilege changes passes the audit cleanly.

## 8. Failure Modes & Edge Cases
- **WRONG:** Only testing the happy path (`"admin can export invoices -> 200"`) while never asserting that `viewer` or `tenant-b` gets `403`/`404` on the exact same endpoint.
- **RIGHT:** Treat negative authz matrix tests (`401`, `403`, cross-tenant `403`/`404`, header spoofing ignored) as mandatory merge blockers for every route.
- **WRONG:** Trusting `returned_docs` in a RAG evaluation trace as sufficient proof that pre-top-K ACL filtering is enforced in production serving code.
- **RIGHT:** Verify pre-top-K filtering directly in the vector/search query implementation and tie eval runs to an independently frozen policy revision.

## 9. Testing & Verification
- Preserve and execute `shadow-auth/tests/test_auth_policy_matrix.py` alongside `test_auth_policy_verifier.py`; confirm `Authorization`/`Cookie`/`x-api-key` appear as `[REDACTED]` in recorded audit logs.

## 10. Operational Considerations
- Partition `security_audit_logs` monthly by `occurred_at` and archive cold partitions to immutable WORM object storage (S3 Object Lock) per statutory retention requirements (typically 1–5 years in regulated fintech/gov).

## 11. Authoritative References
- OWASP Logging Cheat Sheet & ASVS 5.0 V7/V16 (`https://cheatsheetseries.owasp.org/cheatsheets/Logging_Cheat_Sheet.html`).
- NIST SP 800-92 — *Guide to Computer Security Log Management*.

## 12. Limitations & When NOT to Use
- Audit logs provide forensic accountability and non-repudiation, not preventive blocking; always pair audit trails with proactive server-side enforcement (`06`) and anomaly alerting (`/shadow-observe`).
