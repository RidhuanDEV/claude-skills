# 02. iOS App Store Compliance, `PrivacyInfo.xcprivacy` & App Attest

## 1. Purpose & Activation Conditions
Use this playbook when preparing iOS builds (Swift/UIKit/SwiftUI, Flutter iOS, React Native/Expo iOS) for TestFlight or Apple App Store Connect submission. Apple enforces automated static validation (`ITMS-91053` missing Required Reason API declarations, ATS compliance, SDK privacy signatures, and account-deletion policy) that rejects non-compliant `.ipa` archives immediately upon upload.

Activate this playbook when:
- Authoring or auditing `PrivacyInfo.xcprivacy` across the main app target and bundled third-party SDKs (CocoaPods / Swift Package Manager).
- Configuring `Info.plist` transport security (`NSAppTransportSecurity`), purpose strings, Sign in with Apple parity, and in-app account deletion flows.
- Integrating **Apple App Attest (`DCAppAttestService`)** for server-verified client integrity on high-risk endpoints, or configuring Xcode signing & `.dSYM` crash symbolication.

## 2. Prerequisites
- Access to `ios/<Target>/Info.plist`, `PrivacyInfo.xcprivacy`, `Podfile.lock` / `Package.resolved`, and Xcode project / Fastlane signing configuration.
- Knowledge of all analytics, crash-reporting, and ad/attribution SDKs bundled in the app binary (coordinate with `/shadow-analytics` and `/shadow-privacy`).

## 3. Technical Principles & Constraints
1. **Mandatory `PrivacyInfo.xcprivacy` Required Reason API Declarations (`ITMS-91053`)**:
   - Declare every Required Reason API category accessed by your app (and verify third-party SDKs ship their own signed privacy manifests):
     - `NSPrivacyAccessedAPICategoryFileTimestamp` (e.g., `C617.1`, `DDA9.1`)
     - `NSPrivacyAccessedAPICategorySystemBootTime` (e.g., `35F9.1`)
     - `NSPrivacyAccessedAPICategoryDiskSpace` (e.g., `E174.1`, `85F4.1`)
     - `NSPrivacyAccessedAPICategoryActiveKeyboards` (e.g., `54BD.1`)
     - `NSPrivacyAccessedAPICategoryUserDefaults` (e.g., `CA92.1` app-only access)
   - Keep `NSPrivacyTracking`, `NSPrivacyTrackingDomains`, and `NSPrivacyCollectedDataTypes` strictly aligned with App Store Connect Privacy Nutrition Labels and actual runtime consent (App Tracking Transparency `ATTrackingManager` when `NSPrivacyTracking = true`).
2. **App Transport Security (`ATS`) & Accurate Usage Strings**:
   - Production `Info.plist` MUST enforce `NSAllowsArbitraryLoads = false` (never leave blanket `true` from local dev). Scope any rare legacy domain exception narrowly with explicit justification.
   - Every sensitive capability (`NSCameraUsageDescription`, `NSPhotoLibraryUsageDescription`, `NSLocationWhenInUseUsageDescription`, `NSFaceIDUsageDescription`) MUST explain the exact user benefit — generic strings like `"App needs camera"` trigger App Review rejection (`Guideline 5.1.1`).
3. **App Review Policy Parity (Sign in with Apple & Account Deletion)**:
   - If the app offers third-party social login (Google, Facebook, etc.), Apple requires offering **Sign in with Apple** as an equivalent option (`Guideline 4.8`).
   - If the app supports account creation inside the app, Apple mandates initiating **in-app account deletion** directly inside the app (`Guideline 5.1.1(v)`) — never force users to email support or call a hotline (aligns with anti-Roach-Motel rules in `/shadow-design` and DSAR erasure in `/shadow-privacy`).
4. **Server-Verified Apple App Attest (`MASVS-RESILIENCE`)**:
   - For high-risk financial, voucher, or anti-abuse APIs, use `DCAppAttestService` to generate a Secure Enclave hardware key, verify the CBOR attestation certificate chain **on the backend server** against Apple's Root CA, and validate per-request assertions with single-use server challenges. Never trust client-side boolean jailbreak checks alone.
5. **Deterministic Signing & `.dSYM` Symbol Archival**:
   - Sign archives via CI-managed Xcode Distribution Certificates & Provisioning Profiles (Xcode Cloud or Fastlane `match` with encrypted read-only repo); NEVER commit `.p12` certificates, provisioning passwords, or App Store Connect API `.p8` keys to Git.
   - Upload `.dSYM` bundles on every release build so production crashes symbolicate cleanly.

## 4. Architecture & Implementation
### Compliant `PrivacyInfo.xcprivacy` Minimal Production Template
```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>NSPrivacyTracking</key>
  <false/>
  <key>NSPrivacyTrackingDomains</key>
  <array/>
  <key>NSPrivacyCollectedDataTypes</key>
  <array>
    <dict>
      <key>NSPrivacyCollectedDataType</key>
      <string>NSPrivacyCollectedDataTypeEmailAddress</string>
      <key>NSPrivacyCollectedDataTypeLinked</key>
      <true/>
      <key>NSPrivacyCollectedDataTypeTracking</key>
      <false/>
      <key>NSPrivacyCollectedDataTypePurposes</key>
      <array>
        <string>NSPrivacyCollectedDataTypePurposeAppFunctionality</string>
      </array>
    </dict>
  </array>
  <key>NSPrivacyAccessedAPITypes</key>
  <array>
    <dict>
      <key>NSPrivacyAccessedAPIType</key>
      <string>NSPrivacyAccessedAPICategoryUserDefaults</string>
      <key>NSPrivacyAccessedAPITypeReasons</key>
      <array>
        <string>CA92.1</string>
      </array>
    </dict>
  </array>
</dict>
</plist>
```

### Strict TypeScript Server-Side App Attest Challenge & Verification Contract
```typescript
export interface AppAttestChallenge {
  readonly challengeId: string;
  readonly nonceBase64: string;
  readonly expiresAtMs: number;
  readonly consumed: boolean;
}

export interface AppAttestAssertionInput {
  readonly keyId: string;
  readonly challengeId: string;
  readonly counter: number;
  readonly previousCounter: number;
  readonly signatureVerified: boolean;
  readonly nowMs: number;
}

export function validateAppAttestAssertion(
  challenge: AppAttestChallenge,
  assertion: AppAttestAssertionInput,
): { readonly accepted: boolean; readonly reason: string } {
  if (challenge.consumed || assertion.nowMs > challenge.expiresAtMs) {
    return { accepted: false, reason: 'CHALLENGE_EXPIRED_OR_REPLAYED' };
  }
  if (!assertion.signatureVerified) {
    return { accepted: false, reason: 'INVALID_SECURE_ENCLAVE_SIGNATURE' };
  }
  if (assertion.counter <= assertion.previousCounter) {
    return { accepted: false, reason: 'NON_MONOTONIC_ASSERTION_COUNTER' };
  }
  return { accepted: true, reason: 'ATTESTED' };
}
```

## 5. Platform / Vendor Variations
- **Flutter iOS**: Add `PrivacyInfo.xcprivacy` inside `ios/Runner/Resources/` and ensure Xcode Copy Bundle Resources includes it; upgrade Flutter plugins (`firebase_*`, `sentry_flutter`, `shared_preferences`) to versions bundling Apple-signed SDK manifests.
- **React Native / Expo (EAS Build)**: Configure `ios.privacyManifests` in `app.json` / `app.config.ts` so `expo prebuild` generates a valid `PrivacyInfo.xcprivacy` deterministically across CI builds.
- **Native SwiftUI / UIKit (SPM)**: Generate an Xcode **Privacy Report** (`Product -> Archive -> Generate Privacy Report`) to inspect the aggregated privacy manifest across your target plus every Swift Package dependency before uploading to App Store Connect.

## 6. Decision Matrix & Trade-Offs
| iOS Release Control | Skip Consequence | Implementation Effort | Verdict |
| :--- | :--- | :--- | :--- |
| **`PrivacyInfo.xcprivacy` + SDK Manifest Audit** | Automatic App Store Connect rejection (`ITMS-91053`) | Low (1–2h) | **Mandatory Gate** |
| **In-App Account Deletion Flow** | App Review rejection (`Guideline 5.1.1(v)`) | Medium (backend DSAR + UI) | **Mandatory if app allows signup** |
| **Apple App Attest (`DCAppAttestService`)** | Higher bot/emulator abuse on high-value APIs | Medium (server CBOR + counter state) | Recommended for fintech/banking/promotions |

## 7. Real Production Scenario
**Context:** A React Native e-commerce app queued a critical Friday release to TestFlight. Ten minutes after upload, App Store Connect rejected the archive with `ITMS-91053: Missing API declaration` for `NSPrivacyAccessedAPICategoryUserDefaults` and `NSPrivacyAccessedAPICategoryFileTimestamp`, plus an App Review hold because the app offered Google Sign-In without Sign in with Apple.
**Resolution:** Generating an Xcode Privacy Report revealed two outdated native pods lacking signed manifests. Upgrading those pods, declaring `CA92.1` + `C617.1` in `PrivacyInfo.xcprivacy`, adding Sign in with Apple, and wiring `mobile_release_gate.py` into CI cleared App Review on the next submission with zero rejections.

## 8. Failure Modes & Edge Cases
- **WRONG (Leaving `NSAllowsArbitraryLoads = true` in `Info.plist` and omitting `PrivacyInfo.xcprivacy`):** Ships cleartext network vulnerability AND triggers instant App Store Connect rejection.
  **RIGHT:** Set `NSAllowsArbitraryLoads = false`, ship an accurate `PrivacyInfo.xcprivacy`, and generate the aggregated Xcode Privacy Report from the release archive before submission.
- **WRONG (Validating App Attest on the iOS client or skipping monotonic counter checks):** Allows replaying captured assertions from compromised devices indefinitely.
  **RIGHT:** Verify CBOR attestation & assertion signatures strictly on the backend server using single-use expiring nonces and monotonically increasing counters.

## 9. Testing & Verification
- Run `python shadow-mobile/scripts/mobile_release_gate.py --scan .` to confirm `MASVS_NETWORK_IOS_ATS_BYPASS` and `MASVS_PRIVACY_MISSING_XCPRIVACY` produce `0` findings.
- On macOS CI/Xcode runners, run `plutil -lint ios/Runner/Info.plist ios/Runner/PrivacyInfo.xcprivacy` and generate the Xcode Privacy Report from the actual Release `.xcarchive`.

## 10. Operational Considerations
- Keep App Store Connect **Privacy Nutrition Labels** synchronized whenever `/shadow-analytics` adds a new telemetry SDK or event property — undeclared tracking domains cause immediate review holds.
- Archive `.dSYM` files and release commit SHAs per TestFlight build number to maintain clean post-launch crash triage (`/shadow-maintain`).

## 11. Authoritative References
- **Apple Developer Documentation** — *Privacy manifest files (`PrivacyInfo.xcprivacy`)* & *Describing use of required reason API*.
- **Apple Developer Documentation** — *Establishing your app's integrity (App Attest / `DCAppAttestService`)*.
- **Apple App Review Guidelines** — *Section 4.8 (Sign in with Apple) & Section 5.1.1(v) (Account Deletion)*.

## 12. Limitations & When NOT to Use
- **Do NOT use** this playbook for Android `.aab`, 16 KB ELF alignment, or Google Play Integrity — load [`03-android-play-console-16kb-signing-and-integrity.md`](03-android-play-console-16kb-signing-and-integrity.md).
- **Do NOT use** for legal UU PDP / GDPR privacy policy drafting — coordinate legal/privacy notices with `/shadow-privacy`.
