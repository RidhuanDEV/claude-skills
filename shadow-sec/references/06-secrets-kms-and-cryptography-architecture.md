# 06. Secrets, KMS & Cryptography Architecture

## 1. Purpose & Activation Conditions
Design safe application cryptography (AEAD encryption at rest, KMS envelope encryption, key rotation, CSPRNG) and zero-leak secrets lifecycle management across Git, CI/CD, and runtime environments. Load when encrypting sensitive fields (`NIK`, `bank_account`, `TOTP secrets`, `OAuth tokens`), managing KMS keys, or auditing secret storage.

## 2. Prerequisites
- Classification of sensitive fields requiring column/envelope encryption (`/shadow-privacy`, UU PDP Pasal 4 Ayat (2)) and a managed secrets/KMS backend.

## 3. Technical Principles & Constraints
- **Use Modern Authenticated Encryption (AEAD) Only (`OWASP ASVS v5.0.0 V11`):**
  - Standard choice: **`AES-256-GCM`** (or `ChaCha20-Poly1305` / `XChaCha20-Poly1305`) using built-in vetted crypto libraries — NEVER roll custom ciphers!
  - **NEVER use `AES-ECB`** (leaks plaintext block patterns!), unauthenticated `AES-CBC` (padding-oracle attacks!), `MD5`/`SHA-1` for signatures/integrity, or `Math.random()` for security tokens!
  - **Nonce Uniqueness Invariant (CRITICAL):** Generate a brand-new `96-bit` (`12-byte`) CSPRNG IV (`crypto.randomBytes(12)`) for EVERY single `AES-256-GCM` encryption call — reusing a `(key, nonce)` pair in GCM completely breaks confidentiality AND authentication!
  - **Bind Additional Authenticated Data (AAD):** Pass contextual metadata (`${tenantId}:${table}:${column}:${recordId}`) as GCM AAD so an attacker with partial DB access cannot copy a ciphertext blob from User A's row into User B's row (prevents ciphertext-swapping attacks!).
- **Envelope Encryption & Versioned Key Rotation (`key_version` / `kid`):**
  - Store `kid` (key identifier/version) alongside `(iv, authTag, ciphertext)` so rotating keys re-encrypts lazily or in background batches without breaking reads of historical rows!
  - For high-scale KMS usage, encrypt each record (or tenant) with a Data Encryption Key (DEK) wrapped by a Cloud KMS Key Encryption Key (KEK).
- **Zero Secrets in Git, Logs, or Container Images (`NIST SSDF PS.1`):**
  - `.gitignore` MUST exclude `.env*` (except safe `.env.example` with placeholders), `*.pem`, `*.key`, `*.p12`, `credentials.json`, and local DB dumps.
  - Inject runtime secrets from a secrets manager (AWS Secrets Manager, GCP Secret Manager, HashiCorp Vault, Doppler) or scoped CI secrets — never bake secrets into `Dockerfile` `ENV`/`ARG` layers or frontend `NEXT_PUBLIC_*`/`VITE_*` env vars!

## 4. Architecture & Implementation
```typescript
import { createCipheriv, createDecipheriv, randomBytes } from 'node:crypto';

export interface EncryptedEnvelope {
  readonly kid: string;
  readonly ivB64: string;
  readonly tagB64: string;
  readonly ciphertextB64: string;
}

export function encryptFieldAes256Gcm(
  plaintext: string,
  key32Bytes: Buffer,
  kid: string,
  aadContext: string // e.g., `${tenantId}:users:totp_secret:${userId}`
): EncryptedEnvelope {
  if (key32Bytes.length !== 32) {
    throw new Error('AES-256-GCM requires an exact 32-byte key');
  }
  const iv = randomBytes(12); // Fresh 96-bit CSPRNG nonce per encryption
  const cipher = createCipheriv('aes-256-gcm', key32Bytes, iv);
  cipher.setAAD(Buffer.from(aadContext, 'utf8'));
  const ciphertext = Buffer.concat([cipher.update(plaintext, 'utf8'), cipher.final()]);
  const tag = cipher.getAuthTag();
  return {
    kid,
    ivB64: iv.toString('base64'),
    tagB64: tag.toString('base64'),
    ciphertextB64: ciphertext.toString('base64'),
  };
}

export function decryptFieldAes256Gcm(
  envelope: EncryptedEnvelope,
  resolveKeyByKid: (kid: string) => Buffer | null,
  aadContext: string
): string {
  const key = resolveKeyByKid(envelope.kid);
  if (!key || key.length !== 32) {
    throw new Error(`Unknown or invalid decryption key '${envelope.kid}'`);
  }
  const decipher = createDecipheriv('aes-256-gcm', key, Buffer.from(envelope.ivB64, 'base64'));
  decipher.setAAD(Buffer.from(aadContext, 'utf8'));
  decipher.setAuthTag(Buffer.from(envelope.tagB64, 'base64'));
  const plaintext = Buffer.concat([
    decipher.update(Buffer.from(envelope.ciphertextB64, 'base64')),
    decipher.final(),
  ]);
  return plaintext.toString('utf8');
}
```

## 5. Platform / Vendor Variations
| Use Case | Correct Cryptographic Primitive | Common Mistake |
| :--- | :--- | :--- |
| **Field Encryption at Rest (`NIK`, `TOTP`, OAuth refresh token)** | `AES-256-GCM` with `kid` + AAD + KMS wrapping | Hardcoded static IV or `AES-256-ECB` |
| **Deterministic Lookup of Encrypted Field (e.g., search by `NIK`)** | Separate blind index column `HMAC-SHA256(normalized_nik, search_pepper)` | Encrypting with deterministic ECB so `WHERE enc = $1` works |
| **Password Storage** | `Argon2id` / `bcrypt >= 12` (`shadow-auth`) | Encrypting passwords with AES so they can be decrypted |
| **Webhook / Token Integrity** | `HMAC-SHA256` + `timingSafeEqual` | Comparing digests with `===` or using unkeyed `SHA-256(secret + body)` (length-extension risk) |

## 6. Decision Matrix & Trade-Offs
| Secret Storage Approach | Auditability & Rotation | Leakage Risk | Recommended For |
| :--- | :---: | :---: | :--- |
| **Cloud KMS / Secrets Manager + IAM/OIDC** | High (auto-rotation + CloudTrail) | Very Low | All staging & production services |
| **SOPS / Sealed Secrets (Encrypted in Git)** | Medium | Low (key stays in KMS) | GitOps Kubernetes manifests |
| **Plaintext `.env` Committed / Shared in Chat** | None | **CRITICAL** | **FORBIDDEN** |

## 7. Real Production Scenario
A developer encrypts `totp_secret` with `AES-256-GCM` using a hardcoded static IV `Buffer.alloc(12, 0)` and commits `.env` containing `FIELD_ENCRYPTION_KEY` to a private repo branch. When rotated later, there is no `kid` field, so rotating the key locks out every existing user's MFA. Adopting `EncryptedEnvelope` (`kid`, fresh 12-byte CSPRNG IV, AAD context) + KMS key resolution + mandatory rotation runbook fixes both confidentiality and zero-downtime key rotation.

## 8. Failure Modes & Edge Cases
- **WRONG:** Pushing a secret to Git and "fixing" it by running `git rm .env && git commit` (the secret remains permanently in Git history and automated scanners scrape public commits in seconds!).
- **RIGHT:** Immediately **rotate & revoke** the exposed credential at the provider (`L4` authorized action), audit provider access logs for abuse, scrub Git history if needed, and enforce pre-commit secret scanning (`gitleaks` / `shadow_gate.py`).
- **WRONG:** Prefixing backend secrets with `NEXT_PUBLIC_` or `VITE_` (embeds them straight into public client JavaScript bundles!).
- **RIGHT:** Keep server secrets strictly server-side with zero public bundler prefixes.

## 9. Testing & Verification
- Unit-test `encryptFieldAes256Gcm` / `decryptFieldAes256Gcm`: (1) two encryptions of identical plaintext produce distinct IVs & ciphertexts, (2) tampering 1 bit in ciphertext or tag throws, (3) decrypting with a different `aadContext` (wrong `tenantId` or `userId`) throws!
- Run `python shadow-quality/scripts/shadow_gate.py --repo .` (includes static secret scanning).

## 10. Operational Considerations
- Schedule annual (or immediate post-incident) KEK/DEK rotation drills; verify that `resolveKeyByKid` supports decrypting both `v1` and `v2` during background re-encryption windows.

## 11. Authoritative References
- NIST SP 800-38D — *Recommendation for Block Cipher Modes of Operation: Galois/Counter Mode (GCM)* (`https://csrc.nist.gov/pubs/sp/800/38/d/final`).
- OWASP Cryptographic Storage Cheat Sheet (`https://cheatsheetseries.owasp.org/cheatsheets/Cryptographic_Storage_Cheat_Sheet.html`).
- OWASP Secrets Management Cheat Sheet (`https://cheatsheetseries.owasp.org/cheatsheets/Secrets_Management_Cheat_Sheet.html`).

## 12. Limitations & When NOT to Use
- Application-layer field encryption protects against SQL dumps and snapshot leaks, NOT against an attacker who compromises the running app server memory/IAM role; combine encryption with strict network isolation, least-privilege IAM, and audit alerts.
