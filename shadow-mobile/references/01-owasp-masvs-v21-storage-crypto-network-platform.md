# 01. OWASP MASVS v2.1.0 — Storage, Crypto, Auth, Network & Platform Hardening

## 1. Purpose & Activation Conditions
Use this playbook when engineering, auditing, or hardening native Android (Kotlin/Java), iOS (Swift), Flutter, or React Native applications against **OWASP MASVS v2.1.0** (`MASVS-STORAGE`, `MASVS-CRYPTO`, `MASVS-AUTH`, `MASVS-NETWORK`, `MASVS-PLATFORM`, `MASVS-CODE`). Client binaries run on untrusted end-user devices; security controls MUST assume an attacker has physical access, debuggers, and traffic proxies.

Activate this playbook when:
- Storing authentication tokens, biometric secrets, offline databases, or Specific PII (`NIK`, financial records) on mobile devices.
- Configuring network security (`NSAppTransportSecurity`, Android `network_security_config.xml`, certificate pinning with rotation).
- Hardening exported Android IPC components (`Activity`, `Service`, `BroadcastReceiver`, `ContentProvider`), WebViews, or release obfuscation (`R8`/`ProGuard`).

## 2. Prerequisites
- Target mobile project manifests (`AndroidManifest.xml`, `Info.plist`, `build.gradle*`) and knowledge of exact shipping channel, build variant (`debug | staging | release`), and target OS matrix.
- Local access to `shadow-mobile/scripts/mobile_release_gate.py` for deterministic static verification (always supplement source scans by inspecting the **merged manifest** or signed package using native build tools!).
- Server-side auth architecture aligned with `/shadow-auth` (OAuth2 PKCE, short-lived access tokens, refresh token rotation).

## 3. Technical Principles & Constraints
1. **Hardware-Backed Secret Storage (`MASVS-STORAGE`)**:
   - Store tokens, session keys, and PII exclusively in **iOS Keychain** (`kSecAttrAccessibleAfterFirstUnlockThisDeviceOnly` or stricter) or **Android Keystore**-backed encryption (e.g., Jetpack DataStore + Tink AEAD / Keystore-wrapped master key).
   - **NEVER** store secrets or tokens in plaintext `AsyncStorage`, `UserDefaults`, `SharedPreferences`, SQLite without SQLCipher/Keystore wrapping, or unencrypted external storage.
   - Exclude sensitive directories from OS cloud backups (`android:allowBackup="false"`, `android:dataExtractionRules` for Android 12+, and iOS `NSURLIsExcludedFromBackupKey = true`).
2. **Modern OS Cryptography (`MASVS-CRYPTO`)**:
   - Use OS-provided cryptographic APIs (`CryptoKit`, Android Keystore / Tink) with authenticated encryption (`AES-256-GCM` or `ChaCha20-Poly1305`) and unique random nonces per operation.
   - Zero hardcoded symmetric keys, static IVs, ECB mode, or deprecated hashes (`MD5`/`SHA-1`) for security primitives.
3. **System Browser OAuth2 PKCE & Crypto-Bound Biometrics (`MASVS-AUTH`)**:
   - Execute OAuth2/OIDC login exclusively through system browsers (`ASWebAuthenticationSession` on iOS, Chrome Custom Tabs on Android) with PKCE (`S256`) — NEVER inside embedded `WebView` / `WKWebView` (violates RFC 8252 and exposes credentials to host app interception).
   - Bind biometric authentication (`BiometricPrompt` / `LocalAuthentication`) to a Keystore/Keychain `CryptoObject` rather than a bypassable client-side `if (biometricSucceeded)` boolean!
4. **TLS Enforcement & Rotatable Pinning (`MASVS-NETWORK`)**:
   - Enforce `android:usesCleartextTraffic="false"` in `src/main/AndroidManifest.xml` (restrict localhost HTTP exclusively to `src/debug/res/xml/network_security_config.xml`) and `NSAllowsArbitraryLoads = false` in production `Info.plist`.
   - If implementing certificate/SPKI pinning for high-risk banking apps, ALWAYS pin the **Subject Public Key Info (SPKI)** with at least one backup pin + expiration/remote rotation strategy so an emergency certificate rotation does not brick installed apps!
5. **Least-Privilege IPC, Hardened WebViews & Release Stripping (`MASVS-PLATFORM`, `MASVS-CODE`)**:
   - Explicitly declare `android:exported="false"` on internal `Activity`, `Service`, `BroadcastReceiver`, and `ContentProvider` entries; exported IPC components MUST enforce signature-level `android:permission` or strict caller validation.
   - Disable `setAllowFileAccess(true)`, `setAllowUniversalAccessFromFileURLs(true)`, and unnecessary JavaScript bridges on WebViews.
   - Release builds MUST enforce `android:debuggable="false"`, `isMinifyEnabled = true`, `isShrinkResources = true`, stripped verbose/PII logs, and archived `mapping.txt` / `.dSYM` crash symbols.

## 4. Architecture & Implementation
### OWASP MASVS v2.1.0 Control Verification Matrix
| MASVS Group | Primary Control | Concrete Engineering Verification |
| :--- | :--- | :--- |
| `MASVS-STORAGE` | Keychain / Keystore + backup exclusion | Zero tokens in `AsyncStorage`/`UserDefaults`; `allowBackup="false"` + `dataExtractionRules` |
| `MASVS-CRYPTO` | OS AEAD (`AES-256-GCM`), no hardcoded keys | Random 96-bit nonce per encryption; keys generated inside Secure Enclave / StrongBox |
| `MASVS-AUTH` | RFC 8252 PKCE + CryptoObject biometrics | `ASWebAuthenticationSession` / Custom Tabs; server validates session tokens independently |
| `MASVS-NETWORK` | TLS 1.2+/1.3, ATS & cleartext disabled | `usesCleartextTraffic="false"`, `NSAllowsArbitraryLoads=false`, SPKI backup pins if pinned |
| `MASVS-PLATFORM` | `exported="false"`, WebView sandboxing | Merged manifest audit + strict URI allowlist on custom schemes/WebViews |
| `MASVS-CODE` | `debuggable="false"`, R8, verified lockfiles | Inspect merged release manifest & signed `.aab`/`.ipa` artifact digest |

### Hardened Android `network_security_config.xml` & Main Manifest Snippet
```xml
<!-- android/app/src/main/res/xml/network_security_config.xml -->
<network-security-config>
  <base-config cleartextTrafficPermitted="false">
    <trust-anchors>
      <certificates src="system" />
    </trust-anchors>
  </base-config>
  <domain-config cleartextTrafficPermitted="false">
    <domain includeSubdomains="false">api.example.com</domain>
    <pin-set expiration="2027-06-01">
      <!-- Primary SPKI pin + backup offline key pin to avoid bricking on cert rotation -->
      <pin digest="SHA-256">PRIMARY_SPKI_BASE64_HASH_PLACEHOLDER=</pin>
      <pin digest="SHA-256">BACKUP_SPKI_BASE64_HASH_PLACEHOLDER=</pin>
    </pin-set>
  </domain-config>
</network-security-config>
```

### Strict TypeScript / React Native Secure Token Storage Wrapper Contract
```typescript
export interface SecureKeyValueStore {
  setItem(key: string, value: string): Promise<void>;
  getItem(key: string): Promise<string | null>;
  deleteItem(key: string): Promise<void>;
}

const SENSITIVE_KEY_PREFIX = 'secure.auth.';

export async function saveRefreshToken(
  store: SecureKeyValueStore,
  token: string,
): Promise<void> {
  if (token.trim().length < 16) {
    throw new Error('INVALID_TOKEN_FORMAT');
  }
  // Delegates exclusively to Keychain (ThisDeviceOnly) / Android Keystore adapter
  await store.setItem(`${SENSITIVE_KEY_PREFIX}refresh_token`, token);
}
```

## 5. Platform / Vendor Variations
- **Flutter**: Use `flutter_secure_storage` configured with `IOSOptions(accessibility: KeychainAccessibility.first_unlock_this_device)` and Keystore-backed Android encrypted storage; avoid `shared_preferences` for tokens/PII.
- **React Native / Expo**: Use `expo-secure-store` (`AFTER_FIRST_UNLOCK_THIS_DEVICE_ONLY`) or `react-native-keychain` rather than `@react-native-async-storage/async-storage` for any session credential; keep Expo dev-client localhost allowances strictly out of production builds.
- **Native Android (Kotlin) & iOS (Swift)**: Prefer Android Keystore + Google Tink AEAD (note `EncryptedSharedPreferences` deprecation trajectory in `androidx.security:security-crypto`) and iOS `SecItemAdd` / `CryptoKit` with `kSecAttrAccessibleAfterFirstUnlockThisDeviceOnly`.

## 6. Decision Matrix & Trade-Offs
| Security Design Choice | Benefit | Operational Risk / Trade-Off | Recommendation |
| :--- | :--- | :--- | :--- |
| **System TLS (ATS / `cleartext=false`) without Pinning** | Zero rotation outage risk; standard enterprise baseline | Vulnerable if user installs malicious root CA on compromised device | Default for standard consumer & B2B apps |
| **SPKI Pinning + Backup Pin + Expiration Date** | Blocks MITM proxies even with rogue user CA | Must ship app updates well ahead of pin expiration | Use for banking/fintech/OJK high-risk apps only |
| **Leaf Cert Pinning (Single Pin, No Backup)** | Minimal upfront config | Emergency CA revocation bricks 100% of installed users | **Anti-Pattern — Never Use** |

## 7. Real Production Scenario
**Context:** A mobile fintech app shipped with an unguarded exported `BroadcastReceiver` (`android:exported="true"`, no `android:permission`) intended for internal payment-status broadcasts, and pinned a single leaf TLS certificate with no backup pin.
**Incident:** During an external MASVS pentest, a proof-of-concept malicious app on the same device forged payment-success intents into the exported receiver. Three months later, an emergency TLS certificate renewal locked out 82,000 installed users until an emergency store release propagated over 36 hours.
**Fix:** Setting `android:exported="false"` on internal IPC components, validating payment states strictly server-side, and migrating to SPKI pinning with an offline backup key + expiration date resolved both classes of failure permanently.

## 8. Failure Modes & Edge Cases
- **WRONG (Storing JWT refresh tokens in `AsyncStorage` or `UserDefaults` + client-side boolean biometric check):** Reading `if (await authenticateBiometrics()) { unlockApp(); }` while refresh tokens sit readable in unencrypted app backups.
  **RIGHT:** Store refresh tokens in Keychain (`ThisDeviceOnly`) / Android Keystore with `allowBackup="false"`, and unlock the decryption key via a hardware-bound `CryptoObject`.
- **WRONG (Scanning only `src/main/AndroidManifest.xml` without inspecting the merged release manifest):** A third-party SDK library manifest quietly merges `android:usesCleartextTraffic="true"` or an exported `ContentProvider` into the final `.aab`.
  **RIGHT:** Run `mobile_release_gate.py --scan .` on source AND inspect the build system's merged release manifest (`build/outputs/logs/manifest-merger-release-report.txt` / `apkanalyzer manifest print`) before signing!

## 9. Testing & Verification
- Run `python shadow-mobile/scripts/mobile_release_gate.py --scan .` and `python shadow-mobile/scripts/mobile_release_gate.py --self-test` (`10/10` precision/recall probes).
- Run `python -m unittest discover -s shadow-mobile/tests -v`.
- On actual release builds, inspect the **merged release manifest** and signed binary (`apkanalyzer` / `codesign --display --entitlements`) tied to the exact release variant and artifact digest.

## 10. Operational Considerations
- Bind every MASVS audit finding to the exact shipping channel (`internal | beta | production`), build variant, and artifact SHA-256 digest so dev/debug exceptions never leak silently into store submissions.
- Coordinate API deprecation windows with `/shadow-compat` because mobile users lag on older app versions for weeks or months after a release.

## 11. Authoritative References
- **OWASP MASVS v2.1.0** — *Mobile Application Security Verification Standard* (`https://mas.owasp.org/MASVS/`).
- **OWASP MASTG** — *Mobile Application Security Testing Guide* (`https://mas.owasp.org/MASTG/`).
- **RFC 8252** — *OAuth 2.0 for Native Apps* (PKCE + external user-agent requirement).
- **Android Developers** — *Network Security Configuration & Application Security Best Practices*.

## 12. Limitations & When NOT to Use
- **Do NOT rely** on client-side mobile hardening alone to enforce business authorization or prevent API tampering — server-side authorization (`/shadow-auth`, `/shadow-sec`) remains the primary trust boundary.
- **Do NOT use** this playbook for iOS `PrivacyInfo.xcprivacy` declarations or Android 16 KB page-size store rules — load Playbooks `02` and `03` respectively.
