# 04. Verified Deep Links, Local Storage Upgrade Migrations & Maestro/Detox E2E

## 1. Purpose & Activation Conditions
Use this playbook when configuring verified **iOS Universal Links** and **Android App Links**, testing **in-place app upgrades with local storage migrations** (preventing crashes when users upgrade from `vN-1` to `vN` or kill the app mid-migration), validating backward compatibility for older installed mobile versions, and writing deterministic mobile E2E flows (Maestro, Detox, or Flutter `integration_test`).

Activate this playbook when:
- Hosting `/.well-known/apple-app-site-association` (AASA) or `/.well-known/assetlinks.json` and validating deep-link allowlists (`MASVS-PLATFORM`).
- Changing local SQLite/Room/Drift/Realm/Keychain schemas or offline queue formats between mobile releases.
- Setting up mobile E2E release-candidate verification across login, offline-resume, deep-link routing, and critical checkout/approval journeys.

## 2. Prerequisites
- Exact iOS `TeamID.BundleID`, Android `applicationId`, and **Play App Signing** SHA-256 certificate fingerprint (NOT just local debug keystore SHA-256!).
- Supported installed client version matrix (oldest version still permitted by the backend API `/shadow-compat`).
- Local simulator/emulator or CI device runner for executing Maestro/Detox/Flutter integration suites when authorized (`L1`/`L2`).

## 3. Technical Principles & Constraints
1. **Verified HTTPS Deep Links Over Unverified Custom Schemes**:
   - Prefer **iOS Universal Links** and **Android App Links** (`android:autoVerify="true"`) over custom URI schemes (`myapp://`) for auth callbacks, magic links, and sensitive actions because any third-party app on a device can hijack an unverified custom scheme.
   - Serve `/.well-known/apple-app-site-association` over HTTPS (`200 OK`, zero redirects, `Content-Type: application/json`, `<= 128 KB`, no `.json` file extension).
   - Serve `/.well-known/assetlinks.json` over HTTPS (`200 OK`, zero redirects, `application/json`) containing the exact **Google Play App Signing SHA-256** fingerprint (plus CI/internal track fingerprint if distinct).
   - Validate every incoming deep-link path, query parameter, and auth state against a strict allowlist before navigating — never open arbitrary URLs or execute unauthenticated privileged mutations from a deep link!
2. **In-Place Upgrade & Interrupted-Migration Safety**:
   - Fresh-install tests hide upgrade crashes! Whenever local DB tables, encrypted preferences, or Keychain/Keystore formats change, exercise **upgrade from a supported installed version containing realistic existing data** AND verify recovery if the app is killed mid-migration (transactional SQLite schema migrations / atomic file swap + schema version flag).
3. **Old-Client Backend Compatibility Contract**:
   - Mobile users do NOT upgrade instantaneously when a store release ships. Always record explicitly **whether old installed mobile clients can still communicate safely with the newly deployed backend** (`/shadow-compat` additive evolution) and maintain a server-driven `min_supported_version` force-upgrade endpoint only for genuine breaking security emergencies.
4. **Deterministic Mobile E2E Verification (Maestro / Detox / Flutter)**:
   - Cover 5 high-value mobile journeys before store submission: (1) cold start + auth/PKCE login, (2) offline mode + local draft persistence + reconnect sync, (3) deep-link cold entry (both signed-in and signed-out redirect), (4) core primary workflow + negative validation error preserving user input, and (5) in-place upgrade smoke check.
   - Use stable accessibility/test IDs (`testID` / `semanticsIdentifier` / `contentDescription`) — never brittle screen coordinates or localized text strings that break under i18n.

## 4. Architecture & Implementation
### Android `/.well-known/assetlinks.json` & iOS `/.well-known/apple-app-site-association`
```json
[
  {
    "relation": ["delegate_permission/common.handle_all_urls"],
    "target": {
      "namespace": "android_app",
      "package_name": "com.example.app",
      "sha256_cert_fingerprints": [
        "AA:BB:CC:DD:EE:FF:00:11:22:33:44:55:66:77:88:99:AA:BB:CC:DD:EE:FF:00:11:22:33:44:55:66:77:88:99"
      ]
    }
  }
]
```
```json
{
  "applinks": {
    "details": [
      {
        "appIDs": ["TEAMID1234.com.example.app"],
        "components": [
          { "/": "/orders/*", "comment": "Order detail deep link" },
          { "/": "/auth/callback", "comment": "OAuth2 PKCE redirect" },
          { "/": "/admin/*", "exclude": true, "comment": "Keep admin web-only" }
        ]
      }
    ]
  }
}
```

### Strict TypeScript Deep-Link Allowlist Router & Crash-Safe Migration Guard
```typescript
export type SafeMobileRoute =
  | { readonly kind: 'ORDER_DETAIL'; readonly orderId: string }
  | { readonly kind: 'AUTH_CALLBACK'; readonly code: string; readonly state: string }
  | { readonly kind: 'REJECTED'; readonly reason: string };

const ORDER_ID_RE = /^ORD-[A-Z0-9]{6,20}$/;

export function parseTrustedDeepLink(
  rawUrl: string,
  allowedHost: string,
): SafeMobileRoute {
  let parsed: URL;
  try {
    parsed = new URL(rawUrl);
  } catch {
    return { kind: 'REJECTED', reason: 'MALFORMED_URL' };
  }
  if (parsed.protocol !== 'https:' || parsed.hostname !== allowedHost) {
    return { kind: 'REJECTED', reason: 'UNTRUSTED_ORIGIN' };
  }
  if (parsed.pathname.startsWith('/orders/')) {
    const orderId = parsed.pathname.slice('/orders/'.length);
    if (ORDER_ID_RE.test(orderId)) {
      return { kind: 'ORDER_DETAIL', orderId };
    }
    return { kind: 'REJECTED', reason: 'INVALID_ORDER_ID' };
  }
  if (parsed.pathname === '/auth/callback') {
    const code = parsed.searchParams.get('code') ?? '';
    const state = parsed.searchParams.get('state') ?? '';
    if (code.length >= 16 && state.length >= 16) {
      return { kind: 'AUTH_CALLBACK', code, state };
    }
    return { kind: 'REJECTED', reason: 'MISSING_OAUTH_PARAMS' };
  }
  return { kind: 'REJECTED', reason: 'UNMAPPED_ROUTE' };
}
```

### Maestro Deterministic E2E Flow Example (`e2e/order-approval-and-deeplink.yaml`)
```yaml
appId: com.example.app
---
- launchApp:
    clearState: false
- assertVisible:
    id: "home-dashboard-root"
- openLink: "https://app.example.com/orders/ORD-202604"
- assertVisible:
    id: "order-detail-header"
- tapOn:
    id: "approve-order-button"
- assertVisible:
    id: "approval-confirmation-sheet"
```

## 5. Platform / Vendor Variations
- **Android App Links Verification**: Test directly on device/emulator via `adb shell pm get-app-links com.example.app` (must report `verified` for your production domain, not `1024` / `legacy_failure`) and remember Play Console uses the **App Signing** certificate SHA-256 rather than the upload key SHA-256!
- **iOS Universal Links Caching**: Apple CDN (`app-site-association.cdn-apple.com`) caches AASA files aggressively; test updates using `?mode=developer` associated-domain entitlement on development builds before releasing.
- **Flutter / React Native Local Storage Upgrades**: Wrap Room/Drift/SQLite `onUpgrade` steps inside a single transaction (`BEGIN ... COMMIT`) with additive columns first, and preserve fallback readers for older Keychain/SecureStore key encodings so mid-upgrade force-quits recover cleanly on next launch.

## 6. Decision Matrix & Trade-Offs
| E2E / Deep-Link Choice | Strengths | Limitations | Recommendation |
| :--- | :--- | :--- | :--- |
| **Maestro (YAML)** | Fast setup across Android, iOS, Flutter & RN; resilient view hierarchy waits | Fewer low-level JS internals hooks than Detox | **Recommended Default** for cross-platform release gates |
| **Detox (React Native)** | Gray-box synchronization directly with RN bridge | RN-only; heavier native build configuration | Great for mature pure-RN CI pipelines |
| **Flutter `integration_test` / Patrol** | Native Dart access + OS permission dialog support (Patrol) | Flutter-only | Recommended for Flutter-native teams |

## 7. Real Production Scenario
**Context:** A retail delivery app shipped `v3.0.0`, which added a `NOT NULL` column to the local offline-orders SQLite table via an untested `onUpgrade` migration and deployed `assetlinks.json` containing the developer's upload-key SHA-256 instead of the Play App Signing SHA-256.
**Failure:** Every fresh-install QA check passed, so the release promoted to `100%`. Immediately, 100% of existing drivers upgrading from `v2.9.4` crashed in a launch loop (`SQLiteException: cannot add a NOT NULL column without default value`), and email tracking links opened in Chrome instead of the app.
**Fix:** Adding an upgrade-from-`v2.9.4` migration test (with pre-populated offline drafts + simulated mid-migration kill) and verifying `adb shell pm get-app-links` against the Play App Signing SHA-256 prevented repeat launch-loop incidents across all subsequent releases.

## 8. Failure Modes & Edge Cases
- **WRONG (Testing only fresh installs & using local debug/upload SHA-256 in `assetlinks.json`):** Masks SQLite/Keychain upgrade crashes completely and breaks Android App Links for every Play Store user.
  **RIGHT:** Test in-place upgrade from supported installed versions with existing data + interrupted-migration recovery, and publish the exact Play App Signing SHA-256 fingerprint in `assetlinks.json`.
- **WRONG (Opening arbitrary URLs from deep-link query params like `myapp://open?url=https://evil.com`):** Creates an open-redirect / WebView phishing exploit (`MASVS-PLATFORM`).
  **RIGHT:** Parse deep links with a strict HTTPS host + regex route allowlist (`parseTrustedDeepLink`) and reject unmapped or malformed inputs cleanly.

## 9. Testing & Verification
- Verify `/.well-known/apple-app-site-association` and `/.well-known/assetlinks.json` return HTTP `200 OK`, zero redirects, valid JSON, and matching `TeamID.BundleID` / Play App Signing SHA-256.
- Run upgrade-migration unit/instrumented tests (`vN-1` seeded DB -> interrupted migration -> retry `vN` launch -> verify zero data loss) and document explicit old-client API compatibility status alongside release notes.
- Execute targeted Maestro / Detox / Flutter E2E flows on the release candidate before sign-off (remember: repo-wide broad device-farm sweeps are `L2`/`L3` approval-gated).

## 10. Operational Considerations
- Keep a rolling matrix of supported live mobile versions (`vN`, `vN-1`, `vN-2`) in release documentation so backend engineers never drop an API field still required by active store installations (`/shadow-compat`).
- Verify cold-start deep links when the user's token has expired (`401`): preserve the intended destination route safely across login and return the user cleanly after re-authentication (`/shadow-design`).

## 11. Authoritative References
- **Apple Developer Documentation** — *Supporting associated domains & Universal Links (`apple-app-site-association`)*.
- **Android Developers** — *Verify Android App Links (`assetlinks.json` & `adb shell pm get-app-links`)*.
- **Maestro Mobile UI Testing** — `https://maestro.mobile.dev/` & **OWASP MASTG** (`MASVS-PLATFORM` deep-link testing).

## 12. Limitations & When NOT to Use
- **Do NOT use** mobile E2E suites to replace backend contract/security tests (`/shadow-test`, `/shadow-api`, `/shadow-sec`) or web browser E2E (`/shadow-browser`).
- **Do NOT use** unverified custom URI schemes for OAuth2 callbacks or password-reset links on modern iOS/Android versions.
