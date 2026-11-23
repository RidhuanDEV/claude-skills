# 02. Zero-Plaintext Credential Vault Cutover & Vendor Access Revocation

## 1. Purpose & Activation Conditions
Use this playbook when transferring administrative ownership of production infrastructure, databases, cloud consoles, DNS/TLS, payment gateways, and CI/CD pipelines from the delivery vendor to the client's IT team. True handover security requires **zero plaintext secret leakage** and verifiable proof that **new client admin access works BEFORE and AFTER old vendor access is revoked**.

Activate this playbook when:
- Drafting the Credential Inventory Matrix and Vault Cutover Manifest (`access_receipt_ref`) ahead of BAST sign-off.
- Rotating production secrets, SSH keys, database admin passwords, API keys, and cloud IAM roles during ownership transfer.
- Auditing whether legacy contractor/vendor accounts, personal SSH keys, or staging bypass tokens still retain hidden access post-cutover.

## 2. Prerequisites
- Complete inventory of runtime services, external integrations (`/shadow-integrate`), email/DNS records (`/shadow-email`), and infrastructure hosts (`/shadow-ops`).
- Client-owned secret manager or encrypted password vault (e.g., HashiCorp Vault, AWS Secrets Manager, GCP Secret Manager, Azure Key Vault, Bitwarden Enterprise, or encrypted KeePassXC `.kdbx` with out-of-band passphrase exchange).
- Explicit `L4` authorization window from the client IT lead before rotating live production credentials or revoking IAM principals.

## 3. Technical Principles & Constraints
1. **The Access Cutover Invariant (Two-Sided Proof)**:
   - A credential transfer item is `VERIFIED` ONLY when **BOTH** conditions hold simultaneously:
     `new_client_access_verified === true && old_vendor_access_revoked === true`
   - Never revoke vendor break-glass access BEFORE verifying the client's own admin login and secret-decryption path works end-to-end (prevents total lockout). Conversely, never sign final BAST while vendor personal accounts or unrotated shared root passwords remain active!
2. **Absolute Zero-Plaintext Rule**:
   - **NEVER** paste live production passwords, `.env` secrets, SSH private keys, database strings, API tokens, or `.jks`/`.p12` signing passwords inside `.docx` BAST reports, `.xlsx` spreadsheets, Git commits, email bodies, or WhatsApp chats.
   - The Handover Credential Matrix stores ONLY **service name, secret reference ID (`<SECRET_REF:...>`), vault path, client owner role, rotation timestamp, and revocation status**.
3. **Full Surface Coverage (Including Hidden Persistence Paths)**:
   - Audit and transfer ALL 9 credential classes: (1) Cloud/VPS root & IAM/SSO, (2) Server SSH `authorized_keys` & bastion certs, (3) DB Admin & App/Read-Only roles, (4) Redis/Queue credentials, (5) Object Storage (S3/MinIO) keys, (6) SMTP/ESP & Domain/DNS/TLS registrar, (7) Payment/External Webhook HMAC secrets, (8) Mobile Store / Play App Signing / Apple Team roles, and (9) CI/CD deploy keys & container registry tokens.
4. **Least-Privilege Post-Cutover Warranty Access**:
   - If the contract includes a warranty/Harwat support period (`/shadow-maintain`), DO NOT retain permanent shared root access; provision time-bounded, individually attributable break-glass or read-only support roles controlled by the client's IAM policy.

## 4. Architecture & Implementation
### Zero-Plaintext Vault Cutover Manifest (`docs/handover/vault-cutover-manifest.json`)
```json
{
  "contract_ref": "SPK-2026-089/IT-GOV",
  "cutover_window_utc": "2026-05-01T08:00:00Z/2026-05-01T10:00:00Z",
  "vault_cutover": [
    {
      "service": "primary-postgres-prod",
      "secret_ref": "<SECRET_REF:prod/db/admin>",
      "vault_path": "vault://kv-prod/data/core/postgres",
      "client_owner_role": "client-dba-admin",
      "new_client_access_verified": true,
      "old_vendor_access_revoked": true,
      "rotated_at_utc": "2026-05-01T08:30:00Z"
    },
    {
      "service": "payment-gateway-webhook-hmac",
      "secret_ref": "<SECRET_REF:prod/payments/hmac>",
      "vault_path": "vault://kv-prod/data/payments/webhook",
      "client_owner_role": "client-secops-lead",
      "new_client_access_verified": true,
      "old_vendor_access_revoked": true,
      "rotated_at_utc": "2026-05-01T08:45:00Z"
    }
  ]
}
```

### Strict TypeScript Vault Cutover & Secret-Leak Auditor
```typescript
export interface VaultCutoverEntry {
  readonly service: string;
  readonly secretRef: string;
  readonly vaultPath: string;
  readonly clientOwnerRole: string;
  readonly newClientAccessVerified: boolean;
  readonly oldVendorAccessRevoked: boolean;
  readonly rotatedAtUtc: string | null;
}

const PLAINTEXT_SECRET_RE = /(?:postgres(?:ql)?:\/\/[^:\s]+:[^@\s]+@|sk_live_[A-Za-z0-9]+|-----BEGIN [A-Z ]+PRIVATE KEY-----|password\s*=\s*[^\s<]+)/i;

export function auditVaultCutoverManifest(
  entries: readonly VaultCutoverEntry[],
): { readonly cutoverComplete: boolean; readonly issues: readonly string[] } {
  const issues: string[] = [];
  for (const entry of entries) {
    if (PLAINTEXT_SECRET_RE.test(entry.secretRef) || PLAINTEXT_SECRET_RE.test(entry.vaultPath)) {
      issues.push(`${entry.service}: PLAINTEXT_SECRET_DETECTED_IN_MANIFEST`);
    }
    if (!entry.newClientAccessVerified) {
      issues.push(`${entry.service}: CLIENT_ACCESS_UNVERIFIED`);
    }
    if (!entry.oldVendorAccessRevoked) {
      issues.push(`${entry.service}: VENDOR_ACCESS_STILL_ACTIVE`);
    }
    if (entry.rotatedAtUtc === null || entry.rotatedAtUtc.trim() === '') {
      issues.push(`${entry.service}: MISSING_ROTATION_TIMESTAMP`);
    }
  }
  return {
    cutoverComplete: entries.length > 0 && issues.length === 0,
    issues,
  };
}
```

## 5. Platform / Vendor Variations
- **Cloud-Native Managed Accounts (AWS / GCP / Azure)**: Transfer billing & root ownership or deploy directly into client-owned AWS Organization/GCP Project from Day 1; rotate IAM access keys, OIDC GitHub Actions trust policies, and KMS key administrators cleanly.
- **On-Premise / Government Data Center (`PDN` / Institutional VM)**: Audit `/root/.ssh/authorized_keys`, `/home/*/.ssh/authorized_keys`, `sudoers.d/`, PostgreSQL `pg_roles`, and local `.env` file permissions (`chmod 600`) during on-site cutover with the client sysadmin.
- **Third-Party SaaS (Domain Registrar, Cloudflare, Resend/SES, Midtrans/Xendit)**: Verify the primary billing email and MFA/2FA device belong to a client institutional account (not a contractor's personal Gmail!).

## 6. Decision Matrix & Trade-Offs
| Transfer Mechanism | Security Posture | Operational Friction | Recommendation |
| :--- | :--- | :--- | :--- |
| **Client-Owned Secret Manager / Vault + Live Rotation** | Highest — auditable & revocable | Moderate (1–2h supervised cutover session) | **Recommended Default** |
| **Encrypted `.kdbx` (KeePassXC) + Separate Out-of-Band Passphrase + Mandatory Rotation** | High for air-gapped/on-prem agencies | Low tooling barrier | Acceptable when no cloud Vault exists |
| **Password Table Inside `BAST.docx` or Excel Email** | **CRITICAL RISK** — permanent leak | Low | **Strictly Forbidden** |

## 7. Real Production Scenario
**Context:** Six months after vendor handover of an enterprise portal, an ex-contractor's compromised laptop triggered unauthorized reads of customer data via an unrevoked `vendor-deploy` SSH key still sitting in `/home/deploy/.ssh/authorized_keys` and an old static S3 IAM key never listed in the handover doc.
**Fix:** Adopting the 9-class Vault Cutover Manifest enforcing `new_client_access_verified === true && old_vendor_access_revoked === true` with logged SSH/IAM audit queries eliminated lingering contractor persistence paths across all subsequent handovers.

## 8. Failure Modes & Edge Cases
- **WRONG (Revoking vendor access before verifying client admin login, or pasting `.env` passwords into `BAST.docx`):** Locks everyone out of production or permanently embeds plaintext credentials into archived institutional PDFs.
  **RIGHT:** Provision client admin -> verify client login & secret decryption -> rotate shared credentials -> revoke vendor principals -> record vault paths ONLY (`<SECRET_REF:...>`) in the manifest.
- **WRONG (Forgetting DNS registrar, SSL/ACME account, or CI/CD deploy tokens during cutover):** One year later, the domain or TLS cert expires and nobody at the client owns the vendor's personal registrar login.
  **RIGHT:** Include Domain/DNS, TLS, Email ESP, Payment Gateway, and CI/CD tokens explicitly in the 9-class Credential Inventory Matrix.

## 9. Testing & Verification
- Run `auditVaultCutoverManifest` and `shadow-doc/scripts/doc_scaffold.py validate --doc <BAST.json> --strict` to verify zero leaked secret strings across handover documents.
- Confirm client admin independently logs into Vault, DB, cloud console, and CI/CD while testing that old vendor tokens return `401`/`403` (`Permission denied`).

## 10. Operational Considerations
- Schedule credential rotation during a low-traffic window with dual-secret overlap (grace period for JWT signing keys via JWKS or DB dual-user cutover) so live traffic suffers zero downtime during handover.

## 11. Authoritative References
- **ISO/IEC 27001:2022** — *Annex A.5.15 (Access Control), A.5.17 (Authentication Information), A.5.18 (Access Rights)*.
- **OWASP Secrets Management Cheat Sheet** — `https://cheatsheetseries.owasp.org/cheatsheets/Secrets_Management_Cheat_Sheet.html`.

## 12. Limitations & When NOT to Use
- **Do NOT use** this playbook to design initial application authentication/JWT flows — route to `/shadow-auth`.
- **Do NOT execute** live production credential rotation or IAM revocation without explicit `L4` approval from the Monarch and client IT owner.
