# 04 — Rendering & Client Compatibility (`CORE`)

## 1. Purpose & Activation Conditions
Load when authoring responsive HTML + `text/plain` email templates (`React Email` / `MJML`), fixing Outlook Windows Word-engine breaks, preventing Gmail `102 KB` clipping, or ensuring Dark Mode contrast and RTL support.

## 2. Prerequisites
Module `03` (template registry & `multipart/alternative`).

## 3. Technical Principles & Constraints
- **Outlook Windows Word Rendering Engine:** Ignores CSS Grid, Flexbox, `max-width` on `<div>`, `border-radius` on `<a>`, and background CSS gradients. Use table-based layouts (`max-width: 600px`, `role="presentation"`) + Outlook conditional VML (`<!--[if mso]>`) for rounded CTA buttons.
- **Gmail `102 KB` Clipping Ceiling:** Gmail truncates any HTML part exceeding **`102 KB`**, hiding footers and unsubscribe links. Enforce a CI safety budget of **`<= 95,000` UTF-8 bytes**.
- **Blocked Media Formats:** Gmail & Outlook strip `<svg>` elements and `data:image/png;base64,...` URIs. Always host `2x` PNGs over HTTPS with explicit `width`, `height`, and `alt`.
- **Dark Mode Inversion:** iOS Mail, Gmail mobile, and Outlook invert light/dark colors unpredictably; include `<meta name="color-scheme" content="light dark">` and design logos/badges so dark ink never vanishes against `#121212`.

## 4. Architecture & Implementation
```html
<!--[if mso]>
<v:roundrect xmlns:v="urn:schemas-microsoft-com:vml" xmlns:w="urn:schemas-microsoft-com:office:word"
  href="https://example.com/verify?token={{TOKEN}}" style="height:44px;v-text-anchor:middle;width:220px;"
  arcsize="14%" stroke="f" fillcolor="#0F172A">
  <w:anchorlock/>
  <center style="color:#FFFFFF;font-family:Arial,sans-serif;font-size:15px;font-weight:bold;">
    Verify Email Address
  </center>
</v:roundrect>
<![endif]-->
<!--[if !mso]><!-- -->
<a href="https://example.com/verify?token={{TOKEN}}"
   style="display:inline-block;background-color:#0F172A;color:#FFFFFF;font-family:Arial,sans-serif;font-size:15px;font-weight:700;line-height:44px;text-align:center;text-decoration:none;border-radius:6px;padding:0 24px;mso-hide:all;">
  Verify Email Address
</a>
<!--<![endif]-->
```
Validate every compiled template in CI using `python shadow-email/scripts/email_deliverability_verifier.py --check-artifact compiled.json`.

## 5. Platform / Vendor Variations
- **React Email (`@react-email/components`):** Best fit for TypeScript/Next.js repos (typed props, shared brand tokens, `render(el, { plainText: true })`).
- **MJML (`mjml`):** Best cross-language compiler (Python/Go/PHP/Node) guaranteeing Outlook-safe table output automatically.
- **Preheader Hygiene:** Put concise summary text in a visually hidden first element padded with `&zwnj;&nbsp;` so inbox previews do not display `"Logo | View in browser"`.

## 6. Decision Matrix & Trade-Offs
| Template Requirement | Recommended Pattern | Why |
| :--- | :--- | :--- |
| TypeScript monorepo sharing design tokens | **React Email** (compiled to inline HTML + `text/plain`) | Strict prop types, unit-testable JSX |
| Polyglot backend (Go/Python/Laravel) | **MJML** pre-compiled in build step | Battle-tested Outlook/Gmail HTML output |
| Critical OTP / Verification Code | Large `28–32px` monospace text, `0` required images | Readable even when corporate clients block remote images |
| Brand Logo in Dark Mode | Hosted `2x` PNG on subtle pill/light halo | Stays legible under forced color inversion |

## 7. Real Production Scenario
A Tailwind-styled invoice email exceeded `118 KB` because compiled utility CSS was inlined repeatedly into every table cell; Gmail clipped the payment summary and unsubscribe link, and Outlook desktop stacked columns awkwardly. Migrating to lean React Email tables cut size to `28 KB` (`<= 95 KB` CI gate) and rendered cleanly across Outlook, Gmail, and Apple Mail.

## 8. Failure Modes & Edge Cases (`WRONG` vs `RIGHT`)
- **WRONG:** Shipping `<div class="flex gap-4">` or `<img src="data:image/svg+xml;...">` or hiding OTP inside a PNG graphic.
  **RIGHT:** Compile to inline-styled `<table>` HTML + `text/plain` alternative, host HTTPS PNGs, and render all critical info (OTP, amounts, URLs) as crisp selectable text.
- **WRONG:** Shipping raw `{{customerName}}` when a template variable is missing.
  **RIGHT:** Validate template props with strict TypeScript/Zod AND run `email_deliverability_verifier.py --check-artifact` in CI.

## 9. Testing & Verification
Run `email_deliverability_verifier.py --check-artifact`, inspect rendered HTML + plain text in **Mailpit** (`:8025`), and smoke-test critical templates in Outlook Windows, Gmail Web/Mobile, and Apple Mail Dark Mode before major redesigns.

## 10. Operational Considerations
Keep image assets hosted on a stable versioned CDN URL (`https://cdn.example.com/email/v2/logo.png`) — deleting old CDN assets breaks archived receipts in customer inboxes years later!

## 11. Authoritative References
- Can I email (`caniemail.com` compatibility matrix); React Email & MJML documentation; WCAG 2.2 AA contrast guidelines.

## 12. Limitations & When NOT to Use
Do not invest in complex interactive AMP for Email (`text/x-amp-html`) unless you have explicit ESP & Gmail sender whitelisting and dedicated QA — standard HTML + `text/plain` covers 99% of production needs reliably.
