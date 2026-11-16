# OWASP MASVS v2.1.0 & App Store / Google Play Release Gates

> **Normative Sources**:
> - **OWASP MASVS v2.1.0**: [mas.owasp.org/MASVS](https://mas.owasp.org/MASVS/)
> - **Apple Privacy Manifest (`PrivacyInfo.xcprivacy`)**: Apple Developer Documentation — Privacy manifest files & Required Reason APIs
> - **Google Play Integrity API & Target API Level Policy**: Android Developers / Google Play Console Help

---

## 1. OWASP MASVS v2.1.0 Control Matrix

| MASVS Control Group | Engineering Verification & Production Standard |
|---|---|
| `MASVS-STORAGE` | Credentials, refresh tokens, and PII stored exclusively in iOS Keychain or Android Keystore-backed storage; exclude sensitive dirs from OS cloud backups (`android:allowBackup="false"` / `dataExtractionRules`) |
| `MASVS-CRYPTO` | Use OS cryptographic providers with AES-256-GCM / ChaCha20-Poly1305; zero hardcoded encryption keys or static IVs in app binaries |
| `MASVS-AUTH` | OAuth2 PKCE + system browser (`ASWebAuthenticationSession` / Chrome Custom Tabs, never embedded WebViews); biometric unlock tied to Keystore/Keychain crypto objects |
| `MASVS-NETWORK` | `android:usesCleartextTraffic="false"` and iOS `NSAllowsArbitraryLoads = false`; certificate pinning only with rotation fallback (`backup pin` / dynamic remote config) |
| `MASVS-PLATFORM` | Internal `Activity`/`Service`/`Receiver`/`Provider` declare `android:exported="false"`; deep links validate scheme/host/path; WebView disables `setAllowFileAccess(true)` |
| `MASVS-CODE` | Release builds enforce `debuggable="false"`, R8/ProGuard minification (`minifyEnabled true`), stripped debug logs, and verified dependency lockfiles |
| `MASVS-RESILIENCE` | High-risk flows verified server-side via **Google Play Integrity API** (replaces deprecated SafetyNet) or **Apple App Attest**; never rely solely on client-side root/jailbreak booleans |
| `MASVS-PRIVACY` | Minimal telemetry/permissions, explicit consent before tracking SDK initialization, and valid iOS `PrivacyInfo.xcprivacy` + Google Play Data Safety alignment |

---

## 2. iOS App Store Pre-Flight Checklist

1. **`PrivacyInfo.xcprivacy`**:
   - Required when the app or any bundled third-party SDK calls Required Reason APIs:
     - `NSPrivacyAccessedAPICategoryFileTimestamp`
     - `NSPrivacyAccessedAPICategorySystemBootTime`
     - `NSPrivacyAccessedAPICategoryDiskSpace`
     - `NSPrivacyAccessedAPICategoryActiveKeyboards`
     - `NSPrivacyAccessedAPICategoryUserDefaults`
   - Declare accurate `NSPrivacyCollectedDataTypes` and `NSPrivacyTracking` status matching App Store Connect Privacy Nutrition Labels.
2. **Transport & Permissions (`Info.plist`)**:
   - Ensure `NSAppTransportSecurity` does NOT enable `NSAllowsArbitraryLoads = true` in release builds.
   - Verify descriptive usage strings (`NSCameraUsageDescription`, `NSPhotoLibraryUsageDescription`, `NSLocationWhenInUseUsageDescription`).
3. **Signing & Symbols**:
   - Archive with Xcode Distribution Certificate + App Store Provisioning Profile (Fastlane `match` or Xcode Cloud) and upload `.dSYM` symbols to crash reporting.

---

## 3. Google Play Console Pre-Flight Checklist

1. **Manifest & SDK Compliance**:
   - `android:debuggable="false"` (never hardcoded `true` in `src/main/AndroidManifest.xml`).
   - `android:usesCleartextTraffic="false"` (allow localhost HTTP only via `src/debug/res/xml/network_security_config.xml`).
   - `targetSdkVersion` updated to satisfy active Google Play annual API target mandate; `.aab` built via `./gradlew bundleRelease`.
   - Native `.so` libraries aligned for **16 KB page sizes** (Android 15+ compatibility).
2. **Play Integrity API (Replacing Deprecated SafetyNet)**:
   - Migrate any `com.google.android.gms:play-services-safetynet` usage to `com.google.android.play:integrity` and verify the signed integrity token **on the backend server** before issuing high-risk tokens or transactions.
3. **Signing Hygiene (`build.gradle` / `build.gradle.kts`)**:
   - Load `storePassword`, `keyPassword`, and keystore path via `System.getenv(...)` or untracked `keystore.properties` (listed in `.gitignore`). Never commit `.jks` / `.keystore` files or plaintext passwords to Git.
