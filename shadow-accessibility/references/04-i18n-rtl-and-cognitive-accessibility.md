# 04 — Internationalization (i18n), RTL Logical Layouts, Pseudo-Localization & Cognitive Accessibility

## 1. Purpose & Activation Conditions
Engineer global, culturally resilient, and **cognitively forgiving** user interfaces supporting **ICU MessageFormat**, **native `Intl.*` locale/currency/timezone formatting**, **bidirectional LTR/RTL layouts via CSS Logical Properties**, **`+35–40%` text-expansion resilience**, and **low-cognitive-load error/session recovery**. Activate when localizing UIs (Bahasa Indonesia, English, Arabic/Hebrew RTL, German), auditing clipped translated buttons, or designing inclusive low-stress workflows.

## 2. Prerequisites
- Defined supported BCP 47 locales (`id-ID`, `en-US`, `ar-SA`) and explicit separation between **User Display Locale** (language/number separators) and **Transaction Currency / IANA Timezone** (`IDR`, `USD`, `Asia/Jakarta`).

## 3. Technical Principles & Constraints
- **Zero String Concatenation — Use ICU MessageFormat:** Never stitch fragments like `t('youHave') + ' ' + count + ' ' + t('items')`! Word order, gender, and plural categories (Arabic has 6 plural forms: `zero`, `one`, `two`, `few`, `many`, `other`!) break completely under concatenation. Always use full ICU MessageFormat strings (`{count, plural, =0 {Tidak ada pesanan} one {1 pesanan} other {# pesanan}}`).
- **Authoritative Currency & Timezone Formatting (`Intl.*`):**
  - **NEVER** swap `$100` to `Rp 100` when the user switches UI language from English to Bahasa Indonesia! Format monetary amounts using the **transaction's authoritative ISO-4217 currency code** (`currency: 'USD'` vs `'IDR'`) alongside the user's display `locale` (`id-ID` renders `US$100,00`, `en-US` renders `$100.00`).
  - Store timestamps strictly in **UTC ISO-8601** in DB/API and format at the UI edge with `Intl.DateTimeFormat(locale, { timeZone })` (`Asia/Jakarta`, `Asia/Makassar`, `Asia/Jayapura`).
  - Sort user-facing lists with `Intl.Collator(locale, { sensitivity: 'base', numeric: true })` rather than raw JS `.sort()` ASCII codepoint order.
- **CSS Logical Properties For Zero-Override RTL Support:**
  - Replace physical left/right CSS (`margin-left`, `padding-right`, `border-left`, `text-align: left`, `right: 16px`) with **CSS Logical Properties** (`margin-inline-start`, `padding-inline-end`, `border-inline-start`, `text-align: start`, `inset-inline-end: 16px`). Flipping `<html dir="rtl" lang="ar">` automatically mirrors the entire layout cleanly!
  - Mirror **directional icons** (`arrow-right`, `chevron`, `reply`, `undo`) via `[dir="rtl"] .icon-directional { transform: scaleX(-1); }` — NEVER mirror universal or clockwise icons (`checkmark`, `clock`, `magnifying-glass`, brand logos)!
  - Wrap embedded LTR identifiers inside RTL text (`+62 812-3456-7890`, `INV-2026-0042`, emails, URLs) inside **`<bdi>`** (or `dir="ltr"`) so the Unicode Bidirectional Algorithm never scrambles digits and hyphens!
- **Text Expansion Resilience (`+35–45%`) & Pseudo-Localization:** English UI labels ("Save", "Edit", "Tax") expand `30–45%` when translated into Bahasa Indonesia ("Simpan", "Ubah", "Pajak Pertambahan Nilai") or German. Avoid fixed pixel widths (`width: 90px`) on buttons/tabs/badges — use `min-width` + `padding-inline` + `flex-wrap`, and test layouts with automated **pseudo-localization** (`+35%` length expansion + accented characters) at `375px` mobile width!
- **Cognitive, Neurodivergent & Motor Accessibility (Beyond Bare Checklists):**
  - **Zero Memory-Burden Transitions:** Never force users to memorize codes, IDs, or multi-line instructions from a previous step or a 3-second auto-dismissing toast — keep reference context visible inline!
  - **Forgiving Interactions (Undo Over Confirm & Session Warning):** Offer 1-click **Undo** for reversible actions (archive, dismiss, status change) instead of fatiguing confirmation popups; preserve typed form data across validation/network errors; warn users at least `60–120s` before an auth session timeout with a 1-click **"Perpanjang Sesi"** button (WCAG 2.2 SC 2.2.1 Timing Adjustable & 2.2.6 Timeouts)!
  - **Plain, Non-Blaming Copy & Accessible Auth (WCAG 2.2 SC 3.3.8):** Never block password paste (`onPaste={e => e.preventDefault()}` breaks password managers and cognitive accessibility!), avoid cognitive-puzzle CAPTCHAs where Passkeys/WebAuthn/magic links work, and never use double-negative consent toggles.

## 4. Architecture & Implementation

```ts
// Strict TypeScript Locale-Safe Currency/Date Formatters & +35% Pseudo-Localization Tester (0 any, 0 casts)
export type SupportedCurrency = 'IDR' | 'USD' | 'EUR'

export function formatMoneyMinorUnits(
  amountMinor: number,
  currency: SupportedCurrency,
  displayLocale = 'id-ID',
): string {
  const minorDigits = currency === 'IDR' ? 0 : 2
  const divisor = minorDigits === 0 ? 1 : 100
  return new Intl.NumberFormat(displayLocale, {
    style: 'currency',
    currency,
    minimumFractionDigits: minorDigits,
    maximumFractionDigits: minorDigits,
  }).format(amountMinor / divisor)
}

export function formatUtcTimestampForZone(
  utcIso: string,
  displayLocale = 'id-ID',
  ianaTimeZone = 'Asia/Jakarta',
): string {
  const date = new Date(utcIso)
  if (Number.isNaN(date.getTime())) {
    throw new RangeError(`Invalid UTC ISO timestamp: ${utcIso}`)
  }
  return new Intl.DateTimeFormat(displayLocale, {
    dateStyle: 'medium',
    timeStyle: 'short',
    timeZone: ianaTimeZone,
  }).format(date)
}

export function pseudoLocalizeExpand(sourceText: string): string {
  const accentMap: Readonly<Record<string, string>> = {
    a: 'å', e: 'é', i: 'î', o: 'ö', u: 'û',
    A: 'Å', E: 'É', I: 'Î', O: 'Ö', U: 'Û',
  }
  const accented = [...sourceText].map((ch) => accentMap[ch] ?? ch).join('')
  const pad = '~'.repeat(Math.ceil(sourceText.length * 0.35))
  return `[!! ${accented}${pad} !!]`
}
```

```css
/* RTL-Safe Logical CSS Card + Directional Icon Mirroring + Fluid Button Growth */
.notice-card {
  padding-block: 0.75rem;
  padding-inline: 1rem;
  border-inline-start: 4px solid var(--color-primary);
  text-align: start;
}

.action-button {
  min-inline-size: 6rem;
  padding-inline: 1rem;
  padding-block: 0.625rem;
  white-space: normal;
  text-align: center;
}

[dir='rtl'] .icon-directional {
  transform: scaleX(-1);
}
```

### i18n, RTL & Cognitive Accessibility Matrix

| Domain | Standard API / Pattern | Mandatory Engineering Rule |
| :--- | :--- | :--- |
| **Pluralization & Grammar** | **ICU MessageFormat** | Zero string concatenation; support locale plural rules |
| **Currency & Numbers** | `Intl.NumberFormat` + explicit ISO-4217 `currency` | Never infer currency from UI language alone (`USD` != `IDR`) |
| **Dates & Timezones** | `Intl.DateTimeFormat` + explicit IANA `timeZone` | Store UTC; format at UI edge (`Asia/Jakarta`) |
| **LTR / RTL Layout** | CSS Logical Properties (`margin-inline-start`, `inset-inline-end`) | Zero physical `left`/`right` layout overrides; mirror directional icons only |
| **Embedded Codes in RTL** | `<bdi>+62 812-3456</bdi>` / `<bdi>INV-2026-01</bdi>` | Prevents bidirectional digit/hyphen scrambling |
| **Cognitive & Auth Flow** | Allow password paste, session-expiry 1-click extend, inline Undo | Zero memory-burden toasts; preserve user drafts on error |

## 5. Platform/Vendor Variations
- **Tailwind CSS v4 Logical Utilities:** Prefer `ms-4` / `me-4` (`margin-inline-start/end`), `ps-4` / `pe-4`, `start-4` / `end-4`, `text-start` / `text-end`, `border-s-4` over `ml-4`/`mr-4`/`left-4`/`text-left`!
- **Next.js / React (`next-intl` / `FormatJS` / `i18next`):** Configure ICU plugin (`i18next-icu`) and keep translation keys flat/semantic (`orders.status.pending`), ensuring `<html lang={locale} dir={isRtl ? 'rtl' : 'ltr'}>` renders server-side to avoid initial LTR -> RTL layout flash!
- **Indonesia Multi-Timezone Apps (`WIB` / `WITA` / `WIT`):** Display explicit timezone abbreviations (`Asia/Jakarta`, `Asia/Makassar`, `Asia/Jayapura`) on payment deadlines, exam cutoffs, and flight/procurement schedules so users across Sumatra, Bali, and Papua never miss deadlines by 1–2 hours!

## 6. Decision Matrix & Trade-Offs

| Localization Need | Right Approach | Avoid |
| :--- | :--- | :--- |
| **Multi-language labels (`id`, `en`, `ar`)** | ICU MessageFormat + CSS Logical Properties + pseudo-localization check | Fixed `px` button widths + `ml-`/`mr-` physical margins |
| **Multi-currency billing UI** | Store minor units + ISO-4217 `currency` per record; format via `Intl.NumberFormat` | Hardcoding `Rp ` prefix or converting currency by browser language |
| **Reversible destructive action (archive)** | Instant action + persistent inline `Undo` banner (`role="status"`) | Repetitive "Are you sure?" modal fatigue |
| **Irreversible financial/delete action** | Clear inline summary + accessible `<dialog>` confirm (`02`) | Silent instant delete with no confirmation |

## 7. Real Production Scenario
An enterprise travel SaaS expanded from English to Bahasa Indonesia and Arabic (`dir="rtl"`). On launch preview: (1) Bahasa Indonesia header buttons (`"Lihat Riwayat Transaksi"`) overflowed their `width: 110px` containers and clipped text, (2) switching to Arabic left left-bordered cards and sidebar drawers inverted because CSS used `margin-left`/`right: 0`, (3) customer phone numbers rendered backwards (`9876-5432 812 62+`), and (4) switching UI language from `en` to `id` rendered `$250` hotel bookings as `Rp 250`! Migrating to Tailwind logical classes (`ms-`/`ps-`/`border-s-`), `<bdi>` wrappers, `formatMoneyMinorUnits`, and `+35%` pseudo-localization tests at `375px` solved all 4 classes permanently.

## 8. Failure Modes & Edge Cases
- **WRONG:** Blocking `onPaste` on password or OTP inputs (violates WCAG 2.2 SC 3.3.8 Accessible Authentication — breaks password managers, dyslexic users, and motor-impaired users!).
  **RIGHT:** Always allow paste, `autocomplete="current-password"` / `"one-time-code"`, and Passkeys/WebAuthn (`/shadow-auth`).
- **WRONG:** Assuming `"id-ID"` always means `WIB` (`Asia/Jakarta`) for every Indonesian user or hardcoding `"Rp "` strings manually.
  **RIGHT:** Respect explicit user/event IANA timezone (`Asia/Jakarta`, `Asia/Makassar`, `Asia/Jayapura`) and `Intl.NumberFormat`.

## 9. Testing & Verification
- Run automated pseudo-localization (`pseudoLocalizeExpand` `+35%`) AND `<html dir="rtl">` toggle at `375px` mobile viewport inside `/shadow-browser`, asserting `scrollWidth <= innerWidth` and zero clipped buttons.
- Unit-test `formatMoneyMinorUnits(10000, 'USD', 'id-ID')` vs `formatMoneyMinorUnits(10000, 'IDR', 'id-ID')` verifying currency unit invariance across display locales.

## 10. Operational Considerations
- Coordinate multilingual URL routing and `hreflang` sitemaps with `/shadow-seo` (`shadow-seo/references/05-international-seo.md`).
- Consult audited local `T1` reference packs (`shadow-design/references/external-upstreams/ghaida-intent/skills/localize/SKILL.md` and `include/SKILL.md`) for deeper cultural localization & inclusive UX research.

## 11. Authoritative References
- W3C WCAG 2.2 — *SC 2.2.1 Timing Adjustable, 3.3.7 Redundant Entry, 3.3.8 Accessible Authentication (Minimum)*.
- W3C Internationalization — *Structural Markup and Right-to-Left Text in HTML (`<bdi>`, `dir="rtl"`)*.
- Unicode ICU MessageFormat & ECMA-402 (`Intl.NumberFormat`, `Intl.DateTimeFormat`, `Intl.Collator`).

## 12. Limitations & When NOT to Use
- Do NOT auto-translate legal terms, tax disclaimers, or medical instructions via unreviewed machine translation — pair technical i18n engineering with human domain review.
- Do NOT use `shadow-accessibility` for multilingual SEO `hreflang` canonicalization or search indexing — route international SEO architecture to `/shadow-seo`.
