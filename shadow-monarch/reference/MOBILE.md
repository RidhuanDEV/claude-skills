# MOBILE — Cross-Platform & Native Mobile Architecture

Use when designing, building, debugging, or reviewing mobile applications across Flutter, React Native / Expo,
Kotlin (Android), or Swift (iOS). Pair with `lang-DART-FLUTTER.md`, `lang-TYPESCRIPT-NODE.md`, or `lang-JAVA-KOTLIN.md`
for language-specific idioms, and `DESIGN.md` for touch/responsive UX.

## 1. Mobile is a hostile runtime environment

Unlike servers or desktop browsers, mobile apps deal with:
- Unreliable, high-latency, metered networks (tunnel transitions, airplane mode, captive portals).
- Aggressive OS process death in the background (low memory killer on Android/iOS).
- Strict main/UI thread frame budgets (16.6ms for 60fps, 8.3ms for 120Hz ProMotion).
- Multi-version fragmentation: users stay on old app builds for weeks or months after a backend deploy.

## 2. App lifecycle & state restoration

- **Never assume in-memory state survives backgrounding**: when the user switches to camera, browser, or OTP SMS app,
  the OS may kill the process. Persist critical in-progress state (multi-step forms, checkout drafts, navigation route)
  and restore cleanly on resume.
- **Lifecycle hooks** (`AppLifecycleState` / `AppState` / `LifecycleOwner`):
  - Pause timers, camera/location streams, polling, and animations when `paused`/`inactive`.
  - Refresh stale auth tokens, sync queues, and time-sensitive views when returning to `resumed`.
- Cancel in-flight async work or guard state updates when a screen/widget is unmounted/disposed.

## 3. Network resilience, offline-first & synchronization

- **Optimistic vs authoritative actions**:
  - Read-heavy/collaborative actions can use local cache + background sync (SQLite / Drift / WatermelonDB / Room).
  - Financial, inventory, or authorization actions must confirm with the server using **idempotency keys** so network
    retries on flaky cellular connections never duplicate transactions.
- **Offline queue & conflict resolution**:
  - Queue offline mutations with timestamps and idempotency keys; replay in order when connectivity returns.
  - Handle `409 Conflict` / stale version errors explicitly rather than silently overwriting newer server data.
- **Pagination & payload size**: use cursor pagination, compress payloads, cache images to disk with size/TTL limits,
  and avoid fetching oversized nested JSON payloads over cellular data.

## 4. Mobile security & storage

- **Secrets never live in the app binary**: APK/IPA bundles are trivially decompiled. API keys bundled in the client
  must be public-scoped only; privileged secrets stay on your backend.
- **Secure storage vs preferences**:
  - Store access/refresh tokens, biometric keys, and sensitive PII only in hardware-backed encrypted storage
    (`Android Keystore` / `EncryptedSharedPreferences`, iOS `Keychain`, `flutter_secure_storage`, `expo-secure-store`).
  - Plain `SharedPreferences` / `AsyncStorage` / `UserDefaults` are only for non-sensitive UI preferences (theme, locale).
- **Transport & WebViews**: enforce HTTPS/TLS (certificate pinning only when rotation strategy is managed); restrict
  WebView JavaScript bridges and allowed domains; strip sensitive logs in release builds.

## 5. Deep linking, push notifications & permissions

- **Deep links (App Links / Universal Links)**: validate every path/query parameter from a deep link as untrusted input;
  handle unauthenticated users by saving the target route, completing login, and redirecting afterward.
- **Push notifications (FCM / APNs)**: handle all 3 states — **Foreground** (in-app banner/state refresh), **Background**
  (tap routing), and **Terminated / Cold Start** (initial notification payload read after auth/router initialization).
  Keep notification handlers idempotent.
- **Runtime permissions**: request permissions (Camera, Location, Notifications, Photos) **in context** right when the
  user triggers the feature, not all at once on first launch. Handle `denied` and `permanentlyDenied` (offer a clear button
  to open OS App Settings).

## 6. Backward compatibility, versioning & release

- **API contract compatibility**: backend endpoints consumed by mobile apps must remain backward-compatible with all
  active store versions (additive fields only; never rename/remove required fields without a versioned endpoint or a
  forced-upgrade cutoff).
- **Force update / maintenance gate**: include a lightweight version-check endpoint at startup (`min_supported_version`,
  `latest_version`, `maintenance_mode`) so critical security or contract breaks can prompt an immediate store update.

## 7. Anti-patterns

Hardcoding backend secret keys in mobile env files · storing JWTs in plain `SharedPreferences`/`AsyncStorage` · blocking
the UI thread with JSON parsing or image decoding of large payloads · assuming all users are on the latest app version ·
crashing when the user denies a camera/location permission · firing duplicate orders when the user taps "Pay" on a slow 3G connection.
