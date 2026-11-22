# 03 — Accessible Forms, ARIA Live Regions, Color Contrast & Reduced Motion

## 1. Purpose & Activation Conditions
Engineer **error-tolerant accessible forms**, reliable **ARIA live region announcements**, **WCAG 2.2 AA/AAA color contrast & color-blind-safe status encoding**, and **motion/zoom/target-size resilience**. Activate when building forms, validation summaries, toast notifications, data-filter counters, status badges, charts, or animated components.

## 2. Prerequisites
- Design system semantic color tokens (`@theme` / `:root`) and clear error copy guidelines (`antislop-copywriting`).

## 3. Technical Principles & Constraints
- **Programmatic Labels — Placeholder Is NEVER a Label:**
  - Every visible `<input>`, `<select>`, and `<textarea>` MUST have a persistent programmatic label via `<label for="id">`, wrapping `<label>`, or `aria-labelledby`/`aria-label` (for search boxes with visible search button). Placeholders vanish the instant users start typing, fail `4.5:1` contrast, and fail screen-reader consistency!
  - Associate helper hints, format constraints (`DD/MM/YYYY`), and live error messages using `aria-describedby="email-hint email-error"`.
  - Group related radio buttons and checkboxes inside `<fieldset><legend>...</legend></fieldset>` so screen readers announce the question before each option!
- **Accessible Validation Failure Sequence:**
  1. Set `aria-invalid="true"` on every invalid input.
  2. Link each field's specific recovery message via `aria-describedby` (plain, non-blaming guidance explaining *how* to fix it).
  3. On submit failure, focus either an accessible **Error Summary Banner** (`role="alert"`, `tabindex="-1"`, listing clickable links to each invalid field) OR move focus directly to the **first invalid input**.
  4. **NEVER wipe valid form values** (especially long forms!) on validation failure or transient `500` error!
- **ARIA Live Regions Must Be Pre-Mounted:**
  - Mount the live region container (`<div aria-live="polite" aria-atomic="true" class="sr-only">`) in the DOM **at initial page load**, then inject status text dynamically ("Menampilkan 12 dari 48 pesanan", "Perubahan tersimpan") — mounting the `aria-live` element AND its text in the exact same React render tick frequently fails to announce in NVDA and VoiceOver!
  - Use `aria-live="polite"` / `role="status"` for non-blocking updates and reserve `role="alert"` / `aria-live="assertive"` strictly for urgent errors.
- **WCAG 2.2 Contrast, Color Independence & Target Size Floors:**
  - **Normal text (`< 18pt` / `< 24px` or `< 14pt` bold):** `>= 4.5:1` (AA) / `>= 7.0:1` (AAA).
  - **Large text (`>= 24px` regular or `>= 18.67px` bold) & UI Boundaries (input borders, icons, focus rings, chart bars):** `>= 3.0:1`!
  - **Never Color Alone (WCAG 1.4.1):** Pair green/yellow/red status badges with **text labels + distinct icons/shapes** (checkmark, warning triangle, cross) and use patterns/direct data labels in charts so protanopia/deuteranopia users (`~8%` of males) distinguish states effortlessly.
  - **Target Size:** Minimum `24×24px` desktop (WCAG 2.2 AA SC 2.5.8) and **`44×44px`** mobile touch target (`antislop-layoutmobile`).
- **Motion & `200%` Zoom Reflow Resilience:**
  - Honor `@media (prefers-reduced-motion: reduce)` by disabling parallax, auto-playing carousels, bounce animations, and smooth-scroll jumps (replace with instant state transitions or gentle opacity fade).
  - **NEVER** set `maximum-scale=1` or `user-scalable=no` in `<meta name="viewport">`! Ensure full readability and zero horizontal scroll at `200%` browser zoom and `320px` CSS width.

## 4. Architecture & Implementation

```html
<!-- Accessible Form Field + Pre-Mounted Live Region + Color-Independent Status Badge -->
<form novalidate aria-describedby="form-error-summary">
  <div id="form-error-summary" role="alert" tabindex="-1" hidden>
    <h2>Periksa 1 kolom yang perlu diperbaiki</h2>
    <ul>
      <li><a href="#work-email">Email kantor: masukkan alamat email yang valid (contoh: nama@perusahaan.co.id)</a></li>
    </ul>
  </div>

  <div class="field">
    <label for="work-email">Email kantor <span aria-hidden="true">*</span></label>
    <input
      id="work-email"
      name="email"
      type="email"
      autocomplete="email"
      required
      aria-invalid="true"
      aria-describedby="work-email-hint work-email-error"
    />
    <p id="work-email-hint">Digunakan untuk mengirim bukti invoice.</p>
    <p id="work-email-error" class="error-text">
      <svg aria-hidden="true" width="16" height="16"><use href="#icon-alert-circle" /></svg>
      Masukkan format email yang valid, misalnya nama@perusahaan.co.id.
    </p>
  </div>

  <!-- Pre-mounted polite live region for async filter/save announcements -->
  <div id="status-announcer" role="status" aria-live="polite" aria-atomic="true" class="sr-only"></div>
</form>
```

```css
/* Reduced Motion Guard + Safe sr-only Utility */
.sr-only {
  position: absolute;
  width: 1px;
  height: 1px;
  padding: 0;
  margin: -1px;
  overflow: hidden;
  clip-path: inset(50%);
  white-space: nowrap;
  border: 0;
}

@media (prefers-reduced-motion: reduce) {
  *,
  *::before,
  *::after {
    animation-duration: 0.01ms !important;
    animation-iteration-count: 1 !important;
    transition-duration: 0.01ms !important;
    scroll-behavior: auto !important;
  }
}
```

### WCAG 2.2 Contrast & Threshold Reference Table

| Surface / Element | WCAG 2.2 AA Minimum | WCAG 2.2 AAA Enhanced | Common Violation Example |
| :--- | :--- | :--- | :--- |
| **Body & Label Text** | `>= 4.5:1` | `>= 7.0:1` | `#9CA3AF` on `#FFFFFF` (`2.54:1` — **FAIL**) |
| **Large Text (`>= 24px` or `18.67px` bold)** | `>= 3.0:1` | `>= 4.5:1` | Light pastel headline on white hero |
| **Input Borders, Icons, Focus Rings, Checkboxes** | `>= 3.0:1` | `>= 3.0:1` | `#E5E7EB` input border on `#FFFFFF` (`1.24:1` — **FAIL**) |
| **Interactive Target Size** | `>= 24×24px` (Mobile `44×44px`) | `>= 44×44px` | `16×16px` close `×` icon inside dense table |

## 5. Platform/Vendor Variations
- **Screen Reader Live-Region Quirks (NVDA / VoiceOver / TalkBack):** VoiceOver on iOS Safari sometimes ignores updates to an empty `role="status"` if identical text is written twice in a row ("Saved" -> "Saved") — toggle or clear the text briefly before reinserting when repeating identical confirmations!
- **HTML Native `:user-valid` / `:user-invalid` (`modern-web-guidance`):** Baseline CSS pseudo-classes `:user-invalid` style invalid fields ONLY *after* user interaction (preventing intimidating red borders before the user even types a single letter!), paired with server/client `aria-invalid="true"`.
- **Dark Mode Contrast:** Never invert light-mode gray tokens mechanically into dark mode — verify contrast ratios independently on both light AND dark theme tokens with `a11y_html_verifier.py --check-contrast`.

## 6. Decision Matrix & Trade-Offs

| Notification / Feedback Type | ARIA Mechanism | Steals Focus? | Auto-Dismiss? |
| :--- | :--- | :--- | :--- |
| **Async Filter Count ("12 of 48 results")** | Pre-mounted `aria-live="polite"` | **No** | Persistent inline |
| **Non-Critical Save Toast ("Draft saved")** | Pre-mounted `role="status"` | **No** | Optional (`>= 6s`, pause on hover/focus) |
| **Actionable Error / Ref ID / Undo Prompt** | Inline `role="alert"` | Only error summary on form submit | **NEVER auto-dismiss in 3s!** |

## 7. Real Production Scenario
A SaaS dashboard used light-gray `#9CA3AF` body captions (`2.54:1` contrast) and `#E5E7EB` input borders (`1.24:1` contrast) on white backgrounds, plus colored dots alone (`●`) for invoice payment status and 3-second auto-dismissing error toasts. Running `a11y_html_verifier.py --check-contrast`, darkening secondary text to `#4B5563` (`7.56:1`), upgrading input borders to `#6B7280` (`4.83:1`), pairing status dots with icons + text (`Lunas`, `Menunggu`, `Gagal`), and persisting inline error alerts with `Ref ID` resolved 100% of contrast and screen-reader defects while also cutting support tickets about "blank invisible inputs" on office monitors.

## 8. Failure Modes & Edge Cases
- **WRONG:** Styling `disabled` submit buttons as the only validation cue on long forms (users cannot tell *which* field is missing and screen readers skip disabled buttons!).
  **RIGHT:** Keep the submit button enabled (or explain missing requirements clearly), validate on submit, focus the error summary / first invalid field, and announce exact fixes via `aria-describedby`.
- **WRONG:** Adding `<meta name="viewport" content="width=device-width, initial-scale=1, maximum-scale=1, user-scalable=no">` (blocks low-vision users from zooming — immediate WCAG 1.4.4 Resize Text failure!).
  **RIGHT:** Always keep `<meta name="viewport" content="width=device-width, initial-scale=1">` allowing `>= 200%` zoom cleanly.

## 9. Testing & Verification
- Run `python shadow-accessibility/scripts/a11y_html_verifier.py --check-contrast "#4B5563" "#FFFFFF"` on every semantic text/border token pair in both light and dark modes.
- Run `python -m unittest discover -s shadow-accessibility/tests -v` (verifies `test_a11y_controls.py` and `test_a11y_html_verifier.py`).
- Test live with browser zoom `200%` and OS `prefers-reduced-motion: reduce` enabled (`/shadow-browser`).

## 10. Operational Considerations
- Document which exact assistive technology combinations were tested (`NVDA + Firefox`, `VoiceOver + Safari`, `TalkBack + Chrome`) in QA release notes — never claim screen-reader verification without actually testing one!

## 11. Authoritative References
- W3C WCAG 2.2 — *SC 1.4.1 Use of Color, 1.4.3 Contrast (Minimum), 1.4.11 Non-Text Contrast, 2.3.3 Animation from Interactions, 2.5.8 Target Size, 3.3.1–3.3.3 Error Identification & Suggestion*.
- MDN Web Docs — *ARIA Live Regions & `:user-invalid`*.

## 12. Limitations & When NOT to Use
- Automated contrast checkers cannot evaluate text overlaid on photographs or CSS gradients — always put a dark/light scrim (`rgba(0,0,0,0.65)`) behind text over photography and inspect worst-case contrast manually.
