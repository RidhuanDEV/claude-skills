# 03. Google Play Console Compliance, 16 KB Alignment, Signing & Play Integrity API

## 1. Purpose & Activation Conditions
Use this playbook when building, signing, and preparing Android releases (Kotlin/Java, Flutter Android, React Native/Expo Android) for Google Play Console internal, closed, or production tracks. Google Play enforces strict automated release gates: `.aab` packaging, annual `targetSdkVersion` mandates, **16 KB ELF page-size alignment** for native `.so` binaries on Android 15+, Play Integrity API migration away from deprecated SafetyNet, and Play Data Safety compliance.

Activate this playbook when:
- Configuring `build.gradle` / `build.gradle.kts` release `signingConfigs`, R8 shrinking, and Play App Signing.
- Auditing native `.so` libraries for **16 KB page-size compatibility** (NDK r27+ / AGP 8.5.1+).
- Migrating legacy `play-services-safetynet` checks to server-verified **Google Play Integrity API**.

## 2. Prerequisites
- Access to `android/app/build.gradle*`, `src/main/AndroidManifest.xml`, `src/debug/`, ProGuard/R8 rules, and CI secret management.
- Awareness of the exact Play Console release channel (`internal | beta | production`), build flavor, and active Google Play annual `targetSdkVersion` requirement.

## 3. Technical Principles & Constraints
1. **Android App Bundle (`.aab`) & Play App Signing**:
   - Build release artifacts strictly as signed `.aab` bundles (`./gradlew bundleRelease`), enrolling in **Play App Signing** so Google safeguards the final app signing key while CI uses an upload key.
   - **NEVER** commit `.jks` / `.keystore` files or hardcode `storePassword` / `keyPassword` in `build.gradle*` or Git — inject exclusively via `System.getenv(...)` or untracked, `.gitignore`d `keystore.properties`.
2. **Active `targetSdkVersion` & Non-Debuggable Release Manifests**:
   - Verify `targetSdk` satisfies Google Play's active annual target API policy for both new apps and updates (API 36 since 2026-08-31; existing apps must target at least API 35 to stay visible to new users on newer devices — `https://developer.android.com/google/play/requirements/target-sdk`).
   - Enforce `android:debuggable="false"` (never hardcoded `true` in `src/main/AndroidManifest.xml`), `android:usesCleartextTraffic="false"`, and `isMinifyEnabled = true` + `isShrinkResources = true` on release variants.
   - Upload R8 `mapping.txt` and native debug symbols to Play Console / crash reporting for every release build.
3. **16 KB Memory Page-Size Alignment (Android 15+ Mandate)**:
   - Android 15+ devices support 16 KB memory pages, and Google Play requires apps targeting Android 15+ with native `.so` libraries (e.g., Flutter engine, React Native Hermes/JSI, SQLCipher, ML/OCR native libs) to align `LOAD` segments to `16 KB` (`2**14`, `0x4000`).
   - Upgrade to **AGP 8.5.1+** (uncompressed shared library zip alignment) and **NDK r27+** (or linker flag `-Wl,-z,max-page-size=16384`), and verify the resulting `.aab`/`.apk` native `.so` ELF headers rather than assuming third-party AARs are aligned!
4. **Google Play Integrity API (Replaces Deprecated SafetyNet)**:
   - Remove all references to deprecated `com.google.android.gms:play-services-safetynet` (`SafetyNet.getClient`).
   - Use `com.google.android.play:integrity` (prefer **Standard API** warm-up for lower latency on frequent calls, or **Classic API** for one-off flows) and decrypt + verify the signed integrity verdict **strictly on the backend server** (`requestDetails.requestHash`, `appIntegrity.appRecognitionVerdict`, `deviceIntegrity.deviceRecognitionVerdict`, `accountDetails`).
5. **Play Data Safety & Minimal Permissions**:
   - Align Google Play Console Data Safety declarations with actual collected telemetry/SDK data, avoid unnecessary broad permissions (`QUERY_ALL_PACKAGES`, `READ_MEDIA_IMAGES` when Photo Picker suffices, `MANAGE_EXTERNAL_STORAGE`), and support Android's Photo Picker & runtime granular permissions cleanly.

## 4. Architecture & Implementation
### Hardened `android/app/build.gradle.kts` Release Signing & R8 Template
```kotlin
android {
    compileSdk = 36

    defaultConfig {
        applicationId = "com.example.app"
        minSdk = 24
        targetSdk = 36 // Google Play: new apps & updates must target API 36 since 2026-08-31
        versionCode = (System.getenv("ANDROID_VERSION_CODE") ?: "1").toInt()
        versionName = System.getenv("ANDROID_VERSION_NAME") ?: "1.0.0"
    }

    signingConfigs {
        create("release") {
            val keystorePath = System.getenv("ANDROID_KEYSTORE_PATH")
            if (!keystorePath.isNullOrBlank()) {
                storeFile = file(keystorePath)
                storePassword = System.getenv("ANDROID_STORE_PASSWORD")
                keyAlias = System.getenv("ANDROID_KEY_ALIAS")
                keyPassword = System.getenv("ANDROID_KEY_PASSWORD")
            }
        }
    }

    buildTypes {
        getByName("release") {
            isDebuggable = false
            isMinifyEnabled = true
            isShrinkResources = true
            signingConfig = signingConfigs.getByName("release")
            proguardFiles(
                getDefaultProguardFile("proguard-android-optimize.txt"),
                "proguard-rules.pro"
            )
            ndk {
                debugSymbolLevel = "FULL"
            }
        }
    }
}
```

### Strict TypeScript Server-Side Play Integrity Verdict Evaluator
```typescript
export interface PlayIntegrityVerdict {
  readonly packageName: string;
  readonly expectedPackageName: string;
  readonly requestHashMatches: boolean;
  readonly appRecognitionVerdict:
    | 'PLAY_RECOGNIZED'
    | 'UNRECOGNIZED_VERSION'
    | 'UNEVALUATED';
  readonly deviceRecognitionVerdicts: readonly string[];
  readonly timestampMillis: number;
  readonly serverNowMillis: number;
}

const MAX_VERDICT_AGE_MS = 120_000;

export function evaluatePlayIntegrityVerdict(
  verdict: PlayIntegrityVerdict,
): { readonly allowHighRiskAction: boolean; readonly reason: string } {
  if (verdict.packageName !== verdict.expectedPackageName) {
    return { allowHighRiskAction: false, reason: 'PACKAGE_NAME_MISMATCH' };
  }
  if (!verdict.requestHashMatches) {
    return { allowHighRiskAction: false, reason: 'REQUEST_HASH_MISMATCH' };
  }
  if (Math.abs(verdict.serverNowMillis - verdict.timestampMillis) > MAX_VERDICT_AGE_MS) {
    return { allowHighRiskAction: false, reason: 'STALE_INTEGRITY_VERDICT' };
  }
  if (verdict.appRecognitionVerdict !== 'PLAY_RECOGNIZED') {
    return { allowHighRiskAction: false, reason: 'UNRECOGNIZED_APP_BINARY' };
  }
  const meetsDevice = verdict.deviceRecognitionVerdicts.includes(
    'MEETS_DEVICE_INTEGRITY',
  );
  if (!meetsDevice) {
    return { allowHighRiskAction: false, reason: 'DEVICE_INTEGRITY_NOT_MET' };
  }
  return { allowHighRiskAction: true, reason: 'VERIFIED' };
}
```

## 5. Platform / Vendor Variations
- **Flutter Android**: Verify Flutter SDK version ships a 16 KB-aligned `libflutter.so`, inspect native plugins (`sqflite`, `camera`, `ocr`), and build with `flutter build appbundle --release --obfuscate --split-debug-info=build/symbols`.
- **React Native / Expo**: Upgrade to React Native 0.77+ / Expo SDK 52+ with AGP 8.5.1+ & NDK r27+ for 16 KB native `.so` alignment; manage upload keystores strictly inside EAS Secrets / CI vaults rather than committing `.jks` files.
- **Enterprise Sideload / MDM Internal Channels**: Explicitly document channel differences (`UNRECOGNIZED_VERSION` occurs on sideloaded enterprise APKs!) so Play Integrity checks fail appropriately or bind to certificate-digest allowlists for private MDM builds rather than locking out internal staff.

## 6. Decision Matrix & Trade-Offs
| Integrity & Release Gate | Strict Enforcement (Fintech / Payments) | Standard Consumer / B2B App |
| :--- | :--- | :--- |
| **Play Integrity Device Verdict** | Require `MEETS_STRONG_INTEGRITY` or `MEETS_DEVICE_INTEGRITY` + server step-up MFA on failure | `MEETS_BASIC_INTEGRITY` / telemetry + rate limits (avoid blocking legitimate custom ROMs unfairly) |
| **16 KB ELF Page Alignment** | **Mandatory** for Play Console Android 15+ compliance | **Mandatory** whenever any `.so` library ships in `.aab` |
| **Staged Rollout** | `5% -> 20% -> 50% -> 100%` watching Play Vitals ANR/crash rate | `10% -> 50% -> 100%` over 48–72h |

## 7. Real Production Scenario
**Context:** A logistics Flutter app targeting `targetSdk = 36` built cleanly locally and passed unit tests, but crashed instantly on Pixel 9 Android 15 16 KB devices (`dlopen failed: empty/missing DT_HASH / not 16KB aligned`) due to a bundled barcode-scanner `.so` compiled with NDK r23.
**Fix:** Running `llvm-objdump -p` against extracted `.so` files from the release `.aab` identified the unaligned third-party AAR (`align 2**12` instead of `2**14`), upgrading the scanner SDK + NDK r27+, and adding an automated 16 KB ELF alignment check in CI eliminated the crash before Production rollout.

## 8. Failure Modes & Edge Cases
- **WRONG (Hardcoding keystore passwords in `build.gradle` and calling deprecated SafetyNet):** Leaking signing credentials into Git history (`MASVS_CRYPTO_HARDCODED_SIGNING_SECRET`) and failing on Android devices where SafetyNet API is shut down.
  **RIGHT:** Load signing credentials strictly via CI environment variables / Play App Signing, and verify Google Play Integrity verdicts server-side.
- **WRONG (Checking Play Integrity verdict on the client without verifying `requestHash` and `timestampMillis` on the server):** Enables trivial token replay and hooking bypasses.
  **RIGHT:** Bind each high-risk request payload to a cryptographic `requestHash` (`SHA-256`) and validate package name, freshness (`<= 2 min`), app recognition, and device integrity strictly on the backend.

## 9. Testing & Verification
- Run `python shadow-mobile/scripts/mobile_release_gate.py --scan .` and confirm `0` findings for cleartext, debuggable, SafetyNet, exported IPC, and hardcoded keystore secrets.
- On release `.aab` artifacts, inspect native libraries (`bundletool` + `llvm-objdump -p *.so | grep LOAD` verifying `align 2**14` for 16 KB alignment) and verify merged manifest via `apkanalyzer manifest print`.
- Test on an Android 15 16 KB emulator image before promoting from internal test track to production rollout.

## 10. Operational Considerations
- Monitor **Android Vitals** (crash-free sessions `>= 99.5%`, user-perceived ANR rate `< 0.47%`) during staged Play Store rollouts (`5% -> 20% -> 100%`); halt rollout immediately if ANR or crash thresholds breach!
- Remember Google Play does not support instant binary downgrade to older `versionCode`s — always pair mobile releases with server-side feature flags and backward-compatible APIs (`/shadow-compat`).

## 11. Authoritative References
- **Android Developers** — *Support 16 KB page sizes* (`https://developer.android.com/guide/practices/page-sizes`).
- **Android Developers** — *Google Play Integrity API overview & server-side verification*.
- **Google Play Console Help** — *Target API level requirements for Google Play apps* & *Play App Signing*.

## 12. Limitations & When NOT to Use
- **Do NOT use** Play Integrity API as a substitute for server-side authentication, RBAC, or rate limiting (`/shadow-auth`, `/shadow-api`).
- **Do NOT use** this playbook for Universal Links / App Links verification or Maestro/Detox upgrade E2E — load [`04-deep-links-upgrade-migrations-and-maestro-e2e.md`](04-deep-links-upgrade-migrations-and-maestro-e2e.md).
