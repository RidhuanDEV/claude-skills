---
name: shadow-mobile
description: "Use when signing or releasing Android/iOS apps, target SDK, Play Integrity, App Links, or PrivacyInfo.xcprivacy."
---

# `/shadow-mobile` — Mobile Hardening (`OWASP MASVS v2.1.0`), Signing & Store Release Gate

Use this skill whenever the **Monarch** invokes `/shadow-mobile`, configures Android/iOS/Flutter/React Native production builds, sets up deep links or attestation, or prepares binaries for Google Play Console or Apple App Store Connect submission.

Grounded in authoritative standards and platform rules indexed in the `## Reference Guide` below:
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
Use official CLI generators (`create-expo-app`, `flutter create`) and non-destructively verified packages with pinned versions per `shadow-monarch/reference/OFFICIAL-FIRST-DEPENDENCY-POLICY.md` (`official_first_verifier.py`).

Bind release advice to the shipping channel, build variant and artifact digest. Source scans exclude build output. Inspect the merged manifest or signed package with the project's existing build tools for final effective settings. For storage changes exercise upgrade from a supported installed version with existing data and interrupted migration. Record whether old clients can still use the deployed service.

## Reference Guide

Load only the specific playbook matching your active mobile security or store-release subtask:

| Task / Scenario | Load Reference |
| :--- | :--- |
| OWASP MASVS v2.1.0 (`STORAGE`, `CRYPTO`, `AUTH`, `NETWORK`, `PLATFORM`, `CODE`), Rotatable SPKI Pinning & Merged Manifest Checks | [references/01-owasp-masvs-v21-storage-crypto-network-platform.md](references/01-owasp-masvs-v21-storage-crypto-network-platform.md) |
| iOS App Store Compliance, `PrivacyInfo.xcprivacy` (`ITMS-91053`), ATS, Sign in with Apple & Server-Verified App Attest | [references/02-ios-app-store-privacy-manifest-and-app-attest.md](references/02-ios-app-store-privacy-manifest-and-app-attest.md) |
| Google Play Console `.aab`, 16 KB ELF Page Alignment (`NDK r27+`), Signing Hygiene & Server-Verified Play Integrity API | [references/03-android-play-console-16kb-signing-and-integrity.md](references/03-android-play-console-16kb-signing-and-integrity.md) |
| Verified Universal Links / App Links (`AASA` / `assetlinks.json`), In-Place Upgrade Migrations & Maestro/Detox E2E | [references/04-deep-links-upgrade-migrations-and-maestro-e2e.md](references/04-deep-links-upgrade-migrations-and-maestro-e2e.md) |
| Automated Mobile MASVS & Store Release Gate Auditor | [scripts/mobile_release_gate.py](scripts/mobile_release_gate.py) (`python shadow-mobile/scripts/mobile_release_gate.py --self-test`) |
| Specialist Evaluation Suite & Behavioral Red Flags | [evaluations.md](evaluations.md) |

Do not load unrelated references unnecessarily.
