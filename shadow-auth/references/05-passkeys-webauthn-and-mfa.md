# 05. Passkeys, WebAuthn (FIDO2) & MFA

## 1. Purpose & Activation Conditions
Implement phishing-resistant Passkeys / WebAuthn (FIDO2), RFC 6238 TOTP MFA, recovery codes, and step-up authentication for sensitive actions. Load when hardening admin/fintech logins, migrating away from SMS OTP, or auditing WebAuthn ceremonies.

## 2. Prerequisites
- Reliable HTTPS origin (`rpId` bound to registrable domain) and server-side single-use challenge store (Redis with `<= 5m` TTL).

## 3. Technical Principles & Constraints
- **Phishing-Resistant Origin Binding (`WebAuthn / FIDO2`):** Unlike passwords or 6-digit TOTP codes (which real-time AiTM proxies can relay), WebAuthn cryptographically binds every assertion signature to the exact browser `origin` and `rpIdHash`.
- **Mandatory Server-Side WebAuthn Verification Checks:**
  1. Challenge matches single-use CSPRNG challenge stored server-side (`TTL <= 5m`) and is deleted atomically on verification (prevents replay!).
  2. `clientDataJSON.type` is strictly `"webauthn.create"` (registration) or `"webauthn.get"` (login).
  3. `clientDataJSON.origin` exactly matches allowlisted production origin(s).
  4. `authenticatorData.rpIdHash` matches `SHA-256(rpId)`.
  5. `UP` (User Present) flag is set; `UV` (User Verified — biometric/PIN) is required for passwordless/step-up flows.
  6. **Sign-Count Anomaly Check:** If stored `signCount > 0` and incoming `newSignCount <= storedSignCount`, flag possible cloned authenticator (note: synced multi-device passkeys like iCloud Keychain/Google Password Manager legitimately keep `signCount === 0` — handle `0 -> 0` explicitly without false lockout!).
- **TOTP MFA & Recovery Codes:** Encrypt TOTP shared secrets at rest (`AES-256-GCM` + KMS), allow `±1` 30-second window max, track the last consumed time-step per user to block same-window replay, and issue `8–10` single-use recovery codes stored **hashed** (never plaintext!).
- **Step-Up Authentication:** Require fresh authentication (`auth_time` within `<= 5–15m` or fresh WebAuthn/MFA ceremony) before sensitive mutations (adding payout bank account, exporting bulk PII, changing MFA/password, deleting workspace).

## 4. Architecture & Implementation
```typescript
export interface StoredPasskeyCredential {
  readonly credentialId: string;
  readonly userId: string;
  readonly publicKeyCoseBase64: string;
  readonly signCount: number;
  readonly backedUp: boolean;
}

export interface AssertionChecksInput {
  readonly expectedChallenge: string;
  readonly receivedChallenge: string;
  readonly expectedOrigin: string;
  readonly receivedOrigin: string;
  readonly userVerified: boolean;
  readonly requireUserVerification: boolean;
  readonly storedSignCount: number;
  readonly incomingSignCount: number;
}

export function evaluateWebAuthnPolicyChecks(
  input: AssertionChecksInput
): { readonly ok: boolean; readonly reason: string } {
  if (input.receivedChallenge !== input.expectedChallenge) {
    return { ok: false, reason: 'challenge_mismatch_or_expired' };
  }
  if (input.receivedOrigin !== input.expectedOrigin) {
    return { ok: false, reason: 'origin_mismatch_phishing_blocked' };
  }
  if (input.requireUserVerification && !input.userVerified) {
    return { ok: false, reason: 'user_verification_required' };
  }
  // Synced passkeys legitimately report signCount=0 on both sides; non-zero counters must strictly increase
  if ((input.storedSignCount > 0 || input.incomingSignCount > 0) && input.incomingSignCount <= input.storedSignCount) {
    return { ok: false, reason: 'sign_count_clone_anomaly' };
  }
  return { ok: true, reason: 'policy_verified' };
}
```

## 5. Platform / Vendor Variations
| Factor Type | Phishing-Resistant? | Best Role | Key Operational Caveat |
| :--- | :---: | :--- | :--- |
| **Passkeys / WebAuthn (Platform + Roaming FIDO2)** | **YES** | Primary login & admin/fintech MFA | Support multiple registered keys + audited recovery flow for lost devices |
| **Authenticator App TOTP (RFC 6238)** | No (AiTM proxy vulnerable) | Broad consumer MFA fallback | Block same-30s code replay; store secret KMS-encrypted |
| **SMS / Email OTP** | No (SIM swap / inbox hijack) | Baseline recovery / low-risk verification ONLY | Strict per-recipient rate limits (`shadow-email` Module `08`) |

## 6. Decision Matrix & Trade-Offs
| Authentication Tier | Recommended Policy | Step-Up Trigger |
| :--- | :--- | :--- |
| **Public Consumer App** | Passkeys optional + Password + TOTP/Email MFA | Email/password change, payout edits |
| **B2B Admin / Finance / Regulated** | Mandatory Passkeys/FIDO2 (or TOTP + strict device policy) | Bulk PII export, role grants, API key creation, wire transfers |

## 7. Real Production Scenario
An admin team relies on password + TOTP MFA. A targeted phishing email sends an engineer to `login-company-portal.example`, where an evilginx reverse proxy captures both password and live 6-digit TOTP code in real time and steals the session cookie. Enrolling hardware/platform **Passkeys** for all admin roles stops the exact same proxy cold because the browser signs for `login-company-portal.example` instead of `portal.company.com`, failing server `origin`/`rpIdHash` verification automatically.

## 8. Failure Modes & Edge Cases
- **WRONG:** Rejecting synced iCloud/Google Passkeys because `incomingSignCount === 0 && storedSignCount === 0` fails a naive `newCount > oldCount` check.
- **RIGHT:** Allow `0 === 0` for synced passkeys while flagging anomalies whenever either stored or incoming counter is non-zero and fails to strictly increment.
- **WRONG:** Storing unhashed TOTP secrets or plaintext recovery codes in the `users` table without encryption or replay tracking.
- **RIGHT:** Encrypt TOTP secrets via KMS envelope encryption, hash single-use recovery codes (`Argon2id` or `HMAC-SHA256`), and record `last_totp_step` per user.

## 9. Testing & Verification
- Use official vetted WebAuthn libraries (`@simplewebauthn/server`, `py_webauthn`, `go-webauthn/webauthn`) and run unit tests for challenge replay, wrong origin, missing `UV` flag, `0->0` synced passkey acceptance, and `5->5` clone rejection.
- Verify TOTP replay test: submitting the exact same 6-digit code twice within the same 30s window succeeds once and rejects the second attempt (`401`).

## 10. Operational Considerations
- Always support registering `>= 2` authenticators per privileged user and provide a documented identity-verified account recovery procedure (never silently disable MFA via unverified support email!).

## 11. Authoritative References
- W3C WebAuthn Level 2 / Level 3 Specification (`https://www.w3.org/TR/webauthn/`).
- NIST SP 800-63B-4 — *AAL3 Phishing-Resistant Authenticators* (`https://csrc.nist.gov/pubs/sp/800/63/4/final`).
- IETF RFC 6238 — *TOTP: Time-Based One-Time Password Algorithm*.

## 12. Limitations & When NOT to Use
- Do NOT write custom CBOR/COSE/ASN.1 WebAuthn cryptographic verification parsers by hand — subtle signature-malleability bugs are common; always use maintained official WebAuthn server libraries.
