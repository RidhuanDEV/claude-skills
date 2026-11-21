# Internationalization (i18n), Localization (l10n) & RTL Layout Engineering

## 1. Core Concepts
Global-ready interfaces decouple UI copy, grammar, directionality, and formatting from hardcoded English/Indonesian assumptions using **ICU MessageFormat**, **native `Intl.*` formatters**, **CSS Logical Properties for bidirectional (LTR/RTL) layouts**, and **text-expansion resilience (+35–45%)**.

## 2. Technical Rules & Formatting Matrix

| Domain | Standard API / Pattern | Mandatory Engineering Rule |
| :--- | :--- | :--- |
| **Pluralization & Grammar** | **ICU MessageFormat** (`{count, plural, one {...} other {...}}`) | Never concatenate translated fragments (`t('a') + count + t('b')`). |
| **Currency & Numbers** | `new Intl.NumberFormat(locale, { style: 'currency', currency })` | Pair exact ISO-4217 currency code (`IDR`, `USD`, `EUR`) with minor-unit integer math; never guess currency symbols from locale alone! |
| **Dates & Timezones** | `new Intl.DateTimeFormat(locale, { timeZone })` | Store UTC in DB/API; format at the UI edge with explicit IANA timezone (`Asia/Jakarta`). |
| **LTR / RTL Layout** | **CSS Logical Properties** (`margin-inline-start`, `padding-inline`, `text-align: start`) | Flip `<html dir="rtl" lang="ar">` cleanly; mirror directional icons (`arrow`, `chevron`, `reply`), never universal icons (`check`, `clock`). |
| **Bidirectional Isolation** | `<bdi>` or `dir="ltr"` on codes, phone numbers, SKUs, and emails | Prevents RTL punctuation/number reordering from scrambling `+62 812-3456` or `INV-2026-01`. |

## 3. Implementation Examples
```ts
// 1. Locale-Safe Currency & UTC-to-Timezone Date Formatter + Pseudo-Localization Stress Generator
export function formatMoneyMinorUnits(amountMinor: number, currency: 'IDR' | 'USD', locale = 'id-ID'): string {
  const divisor = currency === 'IDR' ? 1 : 100
  return new Intl.NumberFormat(locale, {
    style: 'currency',
    currency,
    minimumFractionDigits: currency === 'IDR' ? 0 : 2,
    maximumFractionDigits: currency === 'IDR' ? 0 : 2,
  }).format(amountMinor / divisor)
}

export function pseudoLocalizeExpand(sourceText: string): string {
  const map: Readonly<Record<string, string>> = { a: 'å', e: 'é', i: 'î', o: 'ö', u: 'û', A: 'Å', E: 'É', I: 'Î', O: 'Ö', U: 'Û' }
  const accented = [...sourceText].map((ch) => map[ch] ?? ch).join('')
  const pad = '~'.repeat(Math.ceil(sourceText.length * 0.35))
  return `[!! ${accented}${pad} !!]`
}
```
```css
/* 2. RTL-Safe Logical CSS Card & Directional Icon Rule */
.notice-card {
  padding-block: 0.75rem;
  padding-inline: 1rem;
  border-inline-start: 4px solid var(--primary);
  text-align: start;
}
[dir='rtl'] .icon-directional {
  transform: scaleX(-1);
}
```

## 4. Best Practices
- Use `Intl.Collator(locale, { sensitivity: 'base', numeric: true })` for user-facing list sorting instead of raw `.sort()` ASCII order.
- Allow buttons, tabs, and form labels to grow with `min-width` + `padding-inline` rather than fixed pixel widths (`width: 90px`) so German/Indonesian/French translations never clip.

## 5. Anti-patterns (WRONG vs RIGHT)
- **WRONG:** `margin-left: 12px; text-align: left; right: 16px;` across components (breaks completely in RTL locales and requires hundreds of `[dir="rtl"]` overrides).
- **RIGHT:** `margin-inline-start: 12px; text-align: start; inset-inline-end: 16px;` (works identically in both LTR and RTL with zero overrides).
- **WRONG:** Converting currency symbol (`$` -> `Rp`) when switching language without converting or preserving the actual currency unit (`USD 100 != IDR 100`!).
- **RIGHT:** Format using the transaction's authoritative `currency` code alongside the user's display `locale`.

## 6. Production Considerations
- Run automated pseudo-localization (`+35%` expansion) and `<html dir="rtl">` layout checks at `375px` mobile width to verify zero clipped buttons or horizontal scrollbars.
