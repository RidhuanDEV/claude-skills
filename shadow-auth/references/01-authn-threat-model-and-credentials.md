# 01. AuthN Threat Model & Credential Security

## 1. Purpose & Activation Conditions
Design phishing-resistant, brute-force-hardened authentication grounded in **NIST SP 800-63-4** and **OWASP ASVS 5.0 (V2)**. Load when building or auditing login, registration, password storage, password reset, account lockout, or credential-stuffing defenses.

## 2. Prerequisites
- TLS 1.2+/1.3 transport enforcement, structured redacting logger (`BACKEND.md §12`), and Redis/DB rate-limit store.

## 3. Technical Principles & Constraints
- **Memory-Hard Password Hashing (`OWASP ASVS V2.4`):** Use **Argon2id** (preferred: `m=19456 KiB`–`65536 KiB`, `t=2–3`, `p=1`, random `128-bit` salt) or **bcrypt** (`cost >= 12`, aware of 72-byte truncation -> pre-hash carefully or enforce Argon2id). NEVER use `SHA-256`, `MD5`, unsalted hashes, or reversible encryption for passwords.
- **NIST SP 800-63-4 Password Policy:** Require minimum `>= 8` (recommended `>= 12–15` for staff/admin) up to `>= 64` characters, allow spaces and Unicode, **block breached/common passwords** against known breach corpuses (e.g., k-anonymity HIBP / offline top-100k list), and **do NOT impose arbitrary periodic 90-day forced rotation** or brittle composition rules that weaken entropy.
- **Account Enumeration & Timing-Side-Channel Defense:** Login, registration, and forgot-password MUST return uniform generic messages (`"Invalid credentials"` / `"If an account exists, instructions have been sent"`). When a user email is NOT found during login, still execute a dummy `Argon2id`/`bcrypt` verify against a constant dummy hash so response latency does not reveal valid accounts!
- **Layered Brute-Force & Credential-Stuffing Controls:** Apply sliding-window rate limits per **IP/subnet**, per **normalized account identifier**, and global credential-stuffing burst alerts. Prefer exponential backoff + CAPTCHA/Turnstile challenge over permanent indefinite lockouts (which let attackers DoS legitimate users).
- **Single-Use Time-Bound Recovery Tokens:** Password-reset and magic-link tokens carry `>= 128` bits of CSPRNG entropy, expire in `<= 15 minutes`, are stored **hashed (`SHA-256`)** in the database, and are marked used atomically on first redemption (built strictly from static `APP_CANONICAL_ORIGIN`, never `req.headers.host`).

## 4. Architecture & Implementation
```typescript
import { timingSafeEqual } from 'node:crypto';

export interface PasswordHasher {
  verify(hash: string, plainPassword: string): Promise<boolean>;
}

export interface UserCredentialRecord {
  readonly userId: string;
  readonly tenantId: string;
  readonly passwordHash: string;
  readonly disabled: boolean;
}

export async function verifyLoginTimingSafe(
  email: string,
  plainPassword: string,
  dummyPasswordHash: string,
  findUser: (normalizedEmail: string) => Promise<UserCredentialRecord | null>,
  hasher: PasswordHasher
): Promise<{ readonly authenticated: boolean; readonly user?: UserCredentialRecord }> {
  const normalized = email.trim().toLowerCase();
  const user = await findUser(normalized);
  // Always run full memory-hard verification even when user does not exist (closes timing oracle)
  const targetHash = user ? user.passwordHash : dummyPasswordHash;
  const passwordValid = await hasher.verify(targetHash, plainPassword);

  if (!user || user.disabled || !passwordValid) {
    return { authenticated: false };
  }
  return { authenticated: true, user };
}

export function constantTimeTokenDigestEqual(aHex: string, bHex: string): boolean {
  const a = Buffer.from(aHex, 'hex');
  const b = Buffer.from(bHex, 'hex');
  return a.length === b.length && timingSafeEqual(a, b);
}
```

## 5. Platform / Vendor Variations
| Runtime | Official / Standard Password Hashing Library | Key Caution |
| :--- | :--- | :--- |
| **Node.js / TypeScript** | `@node-rs/argon2` or `argon2` (`node:crypto.scrypt` fallback) | Never run sync hashing on the main event loop (blocks all HTTP requests!) |
| **Python** | `argon2-cffi` / `pwdlib` | Avoid unmaintained `passlib` on Python 3.13+ (`crypt` removed) |
| **Go** | `golang.org/x/crypto/argon2` | Format PHC string (`$argon2id$v=19$...`) for future parameter upgrades |
| **PHP / Laravel** | `password_hash(..., PASSWORD_ARGON2ID)` / `Hash::make` | Verify `password_needs_rehash()` on login to transparently upgrade legacy hashes |

## 6. Decision Matrix & Trade-Offs
| Threat | Weak Pattern | Hardened Pattern | UX Impact |
| :--- | :--- | :--- | :--- |
| **Offline DB Dump Cracking** | `SHA-256(salt + pw)` (billions/sec on GPU) | `Argon2id` (memory-hard) | ~60–150ms login (imperceptible) |
| **Account Enumeration** | `404 User not found` vs `401 Bad password` | Uniform `401` + dummy hash verify | Minimal |
| **Credential Stuffing** | No rate limit or permanent lockout | Per-IP + per-account backoff + breached-password check + MFA/Passkeys | Stops bots without locking victims permanently |

## 7. Real Production Scenario
A B2B portal returns `404` in `4ms` for unknown emails and `401` in `180ms` for known emails with wrong passwords. Attackers enumerate 12,000 valid corporate employee accounts in 3 minutes and launch targeted phishing + credential stuffing. Refactoring to `verifyLoginTimingSafe` with uniform `401` responses, dummy Argon2id execution, and Redis sliding-window rate limits eliminates the enumeration oracle completely.

## 8. Failure Modes & Edge Cases
- **WRONG:** Storing password-reset tokens in plaintext DB columns or placing raw reset/OTP tokens inside query logs or email subject lines.
- **RIGHT:** Hash recovery tokens with `SHA-256` at rest, enforce `<= 15m` TTL + single-use atomic consumption, and redact `Authorization`/`token`/`password` from all logs.
- **WRONG:** Locking an account permanently after 5 failed attempts without automated unlock or recovery path (trivial targeted DoS).
- **RIGHT:** Apply exponential per-IP/account cooldown + challenge, notify account owner on repeated suspicious failures, and escalate to Passkeys/MFA.

## 9. Testing & Verification
- Run `python shadow-auth/scripts/auth_policy_verifier.py --check-session-config <cfg.json>`.
- Add unit tests asserting identical HTTP status, response body, and comparable timing (dummy hash invoked) for both unknown email and wrong password.

## 10. Operational Considerations
- Support transparent hash migration on login: if a legacy `bcrypt` hash verifies, re-hash immediately with `Argon2id` and persist so legacy algorithms age out without forcing mass password resets.

## 11. Authoritative References
- NIST SP 800-63-4 / 800-63B-4 — *Digital Identity Guidelines: Authentication and Authenticator Management* (`https://csrc.nist.gov/pubs/sp/800/63/4/final`).
- OWASP ASVS 5.0 — *V2 Authentication Verification Requirements* (`https://asvs.owasp.org/`).
- OWASP Password Storage Cheat Sheet (`https://cheatsheetseries.owasp.org/cheatsheets/Password_Storage_Cheat_Sheet.html`).

## 12. Limitations & When NOT to Use
- Password hardening alone cannot stop real-time AiTM phishing proxies; for privileged admin, finance, or enterprise accounts, enforce phishing-resistant **Passkeys / WebAuthn (FIDO2)** (`05-passkeys-webauthn-and-mfa.md`).
