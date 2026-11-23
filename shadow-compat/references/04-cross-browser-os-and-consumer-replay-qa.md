# 04 — Cross-Browser, iOS Safari/Mobile Quirks, OS Case Parity & Consumer Replay QA

## 1. Purpose & Activation Conditions
Eliminate platform-specific failures across **iOS Safari / WebKit**, **Firefox**, **Windows vs Linux filesystems**, and **unreachable external API consumers** using concrete platform guards and honest **historical payload consumer replay (`test_consumer_replay.py`)**. Activate when supporting multi-browser/mobile web apps, deploying Windows-developed code to Linux CI/Docker, or validating changes for external consumers you cannot execute locally.

## 2. Prerequisites
- Target browser/OS support matrix (Chromium, Safari/WebKit iOS & macOS, Firefox, Linux Docker runtime).
- Sanitized (zero PII/secret!) historical request/response fixtures when replaying unreachable partner consumers.

## 3. Technical Principles & Constraints
- **Top 5 Cross-Browser & iOS Safari Landmines:**
  1. **iOS `100vh` Clipping:** Mobile Safari includes the dynamic URL bar in `100vh`, burying fixed bottom CTAs! Always use `min-height: 100dvh` (`min-h-dvh`) + `padding-bottom: env(safe-area-inset-bottom)`.
  2. **iOS Input Auto-Zoom Trap:** Focusing any `<input>`, `<select>`, or `<textarea>` with `font-size < 16px` triggers unwanted Safari page zoom! Always enforce `font-size >= 16px` (`1rem`) on mobile form inputs!
  3. **Safari/WebKit Strict `Date` Parsing:** `new Date("2026-11-10 14:30:00")` works in Chrome V8 yet returns **`Invalid Date` (`NaN`)** in Safari WebKit! Always transmit and parse strict ISO-8601 (`"2026-11-10T14:30:00Z"`).
  4. **Safari ITP / Third-Party Cookies:** Cross-site `SameSite=None` cookies are blocked aggressively by Safari ITP — co-host API under same registrable site (`api.example.com` + `app.example.com`) or use BFF proxy (`shadow-auth`).
  5. **Baseline Feature Checks:** Gate Newly Available CSS/JS APIs (Anchor Positioning, View Transitions, Scroll-driven animations) behind `@supports` or runtime feature detection (`/modern-web-guidance`).
- **Windows Dev -> Linux CI/Docker Parity:**
  - Windows NTFS is **case-insensitive** (`import './Header'` succeeds even if file is `header.tsx`), while Linux Docker crashes with `MODULE_NOT_FOUND`! Enforce `"forceConsistentCasingInFileNames": true` in `tsconfig.json`, fix renamed casing with two-step `git mv`, keep `.gitattributes` `*.sh text eol=lf`, and avoid hardcoded `\` Windows path separators (`path.join` / POSIX URLs only!).
- **Honest Consumer Replay Discipline (`test_consumer_replay.py`):**
  - When external partners or older mobile binaries cannot be executed directly in CI, inventory consumers by `(name, version, owner, reachability)`.
  - Run available clients directly AND replay **approved sanitized historical payloads** for unreachable clients.
  - **Honesty Mandate:** Explicitly report what local replay proves (server parses old requests, emits expected fields) AND what replay **CANNOT** prove (whether a remote closed-source partner decoder rejects unknown additive fields, client retry backoff behavior, TLS cipher compatibility) — routing residual risk cleanly to the contract owner for staged rollout or deferral!

## 4. Architecture & Implementation

```ts
// Strict TypeScript Cross-Browser Safe ISO Date Parser & Platform Capability Matrix (0 any, 0 casts)
const STRICT_ISO_UTC_RE = /^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d{1,3})?(?:Z|[+-]\d{2}:\d{2})$/

export function parseCrossBrowserIsoDate(raw: string): Date {
  const normalized = raw.trim()
  if (!STRICT_ISO_UTC_RE.test(normalized)) {
    throw new RangeError(
      `NON_ISO_DATE: '${raw}' breaks Safari/WebKit; require ISO-8601 with 'T' separator and timezone offset`,
    )
  }
  const date = new Date(normalized)
  if (Number.isNaN(date.getTime())) {
    throw new RangeError(`INVALID_DATE_VALUE: '${raw}'`)
  }
  return date
}

export interface ConsumerReplayEvidence {
  readonly consumerId: string
  readonly version: string
  readonly reachableInCi: boolean
  readonly measuredByReplay: readonly string[]
  readonly unmeasuredResidualRisks: readonly string[]
  readonly ownerSignoffRequired: boolean
}
```

### Cross-Platform Compatibility Verification Checklist

| Platform Risk | Concrete Guardrail | Automated Catch Mechanism |
| :--- | :--- | :--- |
| **iOS Safari bottom bar clipped** | `min-height: 100dvh` + `env(safe-area-inset-bottom)` | Playwright WebKit mobile viewport (`375x812`) |
| **iOS input focus auto-zoom** | `input, select, textarea { font-size: max(1rem, 16px); }` on `< 768px` | CSS audit + iOS WebKit check |
| **WebKit `Invalid Date`** | Enforce `T` separator + `Z`/offset (`parseCrossBrowserIsoDate`) | Unit test + WebKit E2E |
| **Windows -> Linux case crash** | `forceConsistentCasingInFileNames: true` + `.gitattributes` `eol=lf` | Linux container CI build |
| **Unreachable external partner** | Sanitized payload replay + explicit `unmeasuredResidualRisks` report | `test_consumer_replay.py` + contract-owner review |

## 5. Platform/Vendor Variations
- **Playwright WebKit Project (`playwright.config.ts`):** Even on Windows and Linux without a Mac, Playwright ships real WebKit binaries — enabling a lightweight WebKit smoke project catches `90%+` of Safari JS/CSS/date bugs before users ever see them (`/shadow-browser`)!
- **Progressive Web Apps & Older Android WebViews:** Check Baseline target audience in Indonesia (mid-range Android Chrome WebViews may lag 12–18 months behind latest Chrome); keep core checkout/auth functional on Baseline Widely Available APIs.

## 6. Decision Matrix & Trade-Offs

| Verification Scope | Fidelity | Cost | When Required |
| :--- | :--- | :--- | :--- |
| **Chromium + WebKit Playwright Smoke** | High for web Safari/Chrome | Low (`< 60s`) | Every customer-facing web release |
| **Sanitized Consumer Replay (`test_consumer_replay.py`)** | Partial (honestly bounded!) | Low | Unreachable partner webhooks & legacy mobile apps |
| **Full Real-Device Cloud Farm (BrowserStack)** | Highest (real iOS hardware) | Medium–High (`L3`) | Pre-launch major mobile/PWA releases |

## 7. Real Production Scenario
A financial portal launched an invoice viewer tested only on Chrome Windows. On day one, two bugs spiked support tickets: (1) Linux production build failed due to `import './InvoiceRow'` vs `invoiceRow.tsx`, and (2) all iOS Safari users saw `NaN/NaN/NaN` on due dates because the API returned `"2026-11-10 14:30:00"` (MySQL datetime format without `T` or `Z`), plus tapping the search box zoomed Safari to 125% hiding the Cancel button! Enforcing strict ISO-8601 serialization, `16px` mobile inputs, `100dvh`, `forceConsistentCasingInFileNames`, and a Playwright WebKit smoke test eliminated all three defect classes permanently.

## 8. Failure Modes & Edge Cases
- **WRONG:** Reporting `"100% Partner Backward Compatibility Verified"` after running local JSON replay without checking whether the partner's real Java/Go JSON parser has `FAIL_ON_UNKNOWN_PROPERTIES` enabled!
  **RIGHT:** Capture each consumer's real decoder strictness where known, state `unmeasuredResidualRisks` explicitly when unreachable, and coordinate staged rollout with the contract owner.
- **WRONG:** Disabling pinch-to-zoom (`maximum-scale=1`) to stop iOS input auto-zoom (breaks WCAG 2.2 accessibility!).
  **RIGHT:** Set `font-size: 16px` (`1rem`) on mobile inputs instead — stops auto-zoom natively while preserving pinch-to-zoom!

## 9. Testing & Verification
- Run `python -m unittest discover -s shadow-compat/tests -v` (verifies `test_consumer_replay.py` AND `test_compat_deprecation_verifier.py`).
- Run a Playwright WebKit smoke check on critical forms/dates before major frontend releases (`/shadow-browser`).

## 10. Operational Considerations
- Maintain a lightweight `docs/architecture/CONSUMER-INVENTORY.md` listing active API versions, mobile app minimum versions, and external partner owners so deprecation & compatibility reviews never fly blind.

## 11. Authoritative References
- MDN Web Docs — *Baseline Browser Compatibility*, `dvh`, `env(safe-area-inset-*)`, ISO-8601 `Date.parse`.
- `shadow-compat/tests/test_consumer_replay.py` (strict decoders, omitted cursors, ordering changes).

## 12. Limitations & When NOT to Use
- Do NOT use `shadow-compat` to design brand-new APIs from scratch (`/shadow-api`) or native App Store binary compliance (`/shadow-mobile`) — `shadow-compat` specifically governs **safe evolution, deprecation, upgrades, and cross-platform survival**!
