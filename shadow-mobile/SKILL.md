---
name: shadow-mobile
description: "Mobile Build, MASVS v2.1.0 & Store Release Engineering. Use when hardening, signing, or releasing Android/iOS/Flutter/React Native apps, checking PrivacyInfo.xcprivacy, Play Integrity API, targetSdkVersion, Universal/App Links, or Maestro/Detox E2E."
---

# `/shadow-mobile` — Mobile Hardening (`OWASP MASVS v2.1.0`), Signing & Store Release Gate

Use this skill whenever the **Monarch** invokes `/shadow-mobile`, configures Android/iOS/Flutter/React Native production builds, sets up deep links or attestation, or prepares binaries for Google Play Console or Apple App Store Connect submission.

Grounded in authoritative standards and platform rules documented in [`references/MASVS-2-1-AND-STORE-RELEASE-GATES.md`](references/MASVS-2-1-AND-STORE-RELEASE-GATES.md):
1. **OWASP MASVS v2.1.0 (Mobile Application Security Verification Standard)** — `https://mas.owasp.org/MASVS/` (`MASVS-STORAGE`, `MASVS-CRYPTO`, `MASVS-AUTH`, `MASVS-NETWORK`, `MASVS-PLATFORM`, `MASVS-CODE`, `MASVS-RESILIENCE`, `MASVS-PRIVACY`).
2. **Apple App Store & `PrivacyInfo.xcprivacy` Requirements** + **Google Play Policy, `targetSdkVersion` & Play Integrity API**.

---

## 1. The 5-Gate Mobile Production & Store Readiness Workflow

### Gate 1: OWASP MASVS v2.1.0 Security & Storage Audit
- **`MASVS-STORAGE`**: Sensitive tokens/keys live strictly in iOS **Keychain** (`kSecAttrAccessibleAfterFirstUnlockThisDeviceOnly`) or Android **Keystore / EncryptedSharedPreferences** — never plaintext `AsyncStorage`, `UserDefaults`, or `SharedPreferences`.
- **`MASVS-NETWORK`**: Enforce TLS 1.2+/1.3 (`android:usesCleartextTraffic="false"` and iOS `NSAllowsArbitraryLoads` = `false`); disable WebView file/universal access unless strictly sandboxed.
- **`MASVS-PLATFORM`**: Explicitly set `android:exported="false"` on internal `Activity`, `Service`, `BroadcastReceiver`, and `ContentProvider` components; validate deep-link URLs against allowlists.
- **`MASVS-RESILIENCE`**: Use **Google Play Integrity API** (not deprecated SafetyNet) and iOS **App Attest** (`DCAppAttestService`) for high-risk financial/auth requests, plus R8/ProGuard obfuscation (`minifyEnabled true`, `shrinkResources true`) and symbol upload (`mapping.txt` / `.dSYM`).

### Gate 2: Apple App Store & `PrivacyInfo.xcprivacy` (`MASVS-PRIVACY`)
- Ship `PrivacyInfo.xcprivacy` declaring `NSPrivacyTracking`, `NSPrivacyTrackingDomains`, `NSPrivacyCollectedDataTypes`, and `NSPrivacyAccessedAPITypes` for Apple's Required Reason APIs (`FileTimestamp`, `SystemBootTime`, `DiskSpace`, `ActiveKeyboards`, `UserDefaults`) so App Store Connect does not reject the build (`ITMS-91053`).
- Verify `Info.plist` purpose strings (`NSCameraUsageDescription`, `NSFaceIDUsageDescription`, etc.) are specific and accurate.

### Gate 3: Google Play Console & Android Build Readiness
- Build signed **Android App Bundle (`.aab`)** with Play App Signing; verify `targetSdkVersion` meets current Google Play minimum API level policy.
- Verify 16 KB ELF alignment for native `.so` libraries on Android 15+ devices (`NDK r27+` / AGP 8.5.1+).
- Never hardcode `storePassword`, `keyPassword`, or `.jks`/`.p12` credentials in `build.gradle` or Git — load exclusively from CI secrets/environment variables.

### Gate 4: Verified Deep Linking (Universal Links & App Links)
- **iOS Universal Links**: Serve signed `/.well-known/apple-app-site-association` over HTTPS (`200 OK`, no redirects, `application/json`).
- **Android App Links**: Serve `/.well-known/assetlinks.json` containing the exact Play App Signing **SHA-256** fingerprint (`adb shell pm get-app-links`).

### Gate 5: Mobile E2E & Crash-Free Gate
- Run automated mobile E2E flows (Maestro / Detox / Flutter `integration_test`) across key auth, offline-resume, deep-link, and payment/form journeys before signing the store release candidate.

---

## 2. Automated Mobile Release & MASVS Gate Script

```powershell
python "shadow-mobile/scripts/mobile_release_gate.py" --scan .
python "shadow-mobile/scripts/mobile_release_gate.py" --self-test
```

Report findings with exact `MASVS ID / Store Policy`, `file:line`, impact (rejection risk vs security exploit), and concrete XML/Gradle/Plist patch.
