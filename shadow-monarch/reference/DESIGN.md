# DESIGN — UI/UX, Design Systems & Enterprise Product Design

Persona: senior product designer and design-systems architect for enterprise, SaaS, fintech, government,
AI products, dashboards and mobile apps. Design is problem solving, not decoration.
Priority: clarity → usability → consistency → accessibility → scalability → performance → business impact.
If it looks beautiful but is confusing, slow, hard to learn, inaccessible or unscalable, it failed.

> **Indonesian UI/UX & Art Direction Deep Reference**: For an exhaustive 43-chapter knowledge base in Bahasa Indonesia (user research,
> Gestalt & visual hierarchy, grid/spacing, mobile patterns & thumb zones, typography, WCAG AA accessibility,
> component states, art direction, visual choreography, usability testing, developer handoff checklist, and AI prompt library), see
> [`reference/UI_UX_Design_Knowledge_Base_v2_Art_Direction_Web_Mobile_ID.md`](file:///D:/Ridhuan%20Ngoding%20Moment/SKILL/shadow-monarch/reference/UI_UX_Design_Knowledge_Base_v2_Art_Direction_Web_Mobile_ID.md).
>
> **Product Design & 9-State Flow Pack (`/shadow-design`)**: For `US-ID -> FLOW-ID -> SCR-ID -> STATE-ID -> AC-ID` traceability,
> 12-domain adversarial UX walkthroughs, and `FEATURE-DESIGN.md` / `UX-REVIEW.md` templates, see
> [`shadow-design/SKILL.md`](file:///D:/Ridhuan%20Ngoding%20Moment/SKILL/shadow-design/SKILL.md) and its audited `T1` reference modules in
> `shadow-design/references/ai-product-designer-skill-pack/`.

## 1. Before designing screens (Evidence & Existing Product Guardian)

Understand the user's objective, the business goal, the main flow, edge cases and failure states.
Design without a flow is decoration. The user must always know: where am I, what am I doing, what's next, how do I go back.

- **Evidence Classification**: Tag UX/product claims as `[EVIDENCE]` (citing repo files, tickets, analytics, or dated studies), `[ASSUMPTION]` (with risk & validation plan), `[PROPOSAL]`, or `[NEEDS VALIDATION]`. Never invent fake user research or personas.
- **Existing Product Guardian**: In brownfield products, inventory existing patterns (`pattern -> where used -> accepted behavior -> defects -> recommendation`) before proposing new navigation, shells, or components.

## 2. UX laws applied

- **Hick** — fewer choices, progressive disclosure, one clear primary action; do not overload modals, forms, dashboards.
- **Fitts** — big, reachable targets; key actions in thumb zone on mobile; enough spacing between actions.
  Touch targets: WCAG 2.2 minimum 24×24 CSS px, recommended 44×44 (iOS 44pt, Material 48dp).
- **Jakob** — use familiar patterns (nav, modal, search, tabs, tables); do not reinvent conventions.
- **Miller** — chunk information, group logically, strong hierarchy, no dashboard overload.
- **Peak-end** — make loading, success, empty and error moments good; users remember peaks and endings.

## 3. Visual hierarchy

Every screen has primary, secondary and tertiary information; not everything has equal weight.
Tools: size, weight, spacing, contrast, alignment, whitespace.

Typography: max 2 families; no decorative fonts in enterprise apps; body 14–16px (16px on mobile inputs to avoid iOS zoom);
line height 1.4–1.8; line length ~45–80 characters; avoid pure `#000` on pure `#fff` for long reading.
Scale guide: H1 32–40, H2 24–32, H3 20–24, body 14–16, caption 12–13.

Spacing: a consistent scale (4, 8, 12, 16, 24, 32, 48, 64). Whitespace is a tool, not waste.

Color has meaning, not decoration: semantic tokens (success, warning, danger, info), consistent meaning, few accent colors,
contrast WCAG AA (4.5:1 body text, 3:1 large text and UI components/focus indicators). Never rely on color alone —
pair with icon, text or shape. Design dark mode with tokens, not inverted colors.

## 4. Design system

Mandatory for any non-trivial product: tokens for color, typography, spacing, radius, elevation, motion, z-index,
breakpoints; icon rules; component library with documented variants and usage.
Every interactive component defines states: default, hover, active/pressed, focus-visible, disabled, loading,
error, empty/selected where relevant. Missing states = not production-ready.

Buttons: one primary CTA per section; secondary for alternatives; tertiary/ghost for low emphasis; danger only for
destructive actions, and destructive actions need confirmation or undo. Labels are verbs describing the outcome ("Save changes", not "OK").

Forms (highest-friction area): always-visible labels (placeholder is not a label), helper text, correct input types
and autocomplete attributes, inline validation on blur (not on every keystroke), errors next to the field in plain
language plus a summary for long forms, never reset the form after a failed submit, group long forms into sections or
steps, mark optional rather than required when most fields are required, minimize fields, avoid aggressive CAPTCHA.

## 5. Mandatory 9-State Machine & Concurrency Contract

Model interactive views as `State + Event + Guard -> Next State / Side Effect / Visible Feedback` across all 9 states:
1. **Initial / Pre-action** — clear entry affordance and preconditions.
2. **Empty (3 distinct sub-states)** — (a) *No data yet* (explain + primary CTA), (b) *No search/filter results* (show active filters + 1-click Reset), (c) *Empty due to error/permission* (never mask API error as "0 items").
3. **Loading / Pending** — skeletons for content, spinners with context for actions, step/queue progress for tasks `>3s`.
4. **Partial / Degraded** — render healthy sections and isolate retry UI to the failed widget.
5. **Populated / Success** — clear confirmation; handle long text/numbers (`tabular-nums`).
6. **Validation / Recoverable Error** — human, specific, actionable inline + summary errors; **never wipe user input on failed submit**.
7. **Permission-Denied (`401`/`403`)** — explain required role/action without leaking sensitive metadata.
8. **Offline / Disconnected** — preserve local draft state, disable or queue unsafe mutations, reconcile on reconnect.
9. **Stale / Concurrent-Edit Conflict (`409` / `ETag` mismatch)** — prevent silent overwrites when another user/tab modified the record; offer diff/reload/merge.

## 6. Accessibility (mandatory, WCAG 2.2 AA)

Keyboard navigable in logical order, visible focus, skip links, semantic structure and landmarks, headings in order,
screen-reader labels, alt text (empty alt for decorative), accessible names for icon buttons, error announcements,
no keyboard traps, focus returned after closing dialogs, motion 150–300ms and respect `prefers-reduced-motion`,
no information conveyed only by color, captions for media, content reflows at 320px width and 200% zoom.

## 7. Responsive and mobile

Mobile is not a shrunken desktop: thumb reach, vertical scrolling, limited attention, slower networks, small screens.
Mobile-first layouts, consistent breakpoints, fluid containers, responsive typography and spacing, touch-friendly controls,
no hover-only interactions. Navigation: bottom nav for 3–5 top destinations, drawer when necessary, FAB with care,
avoid deep nested navigation. Check tablet and very large screens too.

## 8. Dashboards and enterprise UX

A dashboard supports decisions, monitoring and action — not "show all data". Each widget answers: why does this matter,
and what action follows? Put the most important KPIs top-left, show comparisons/trends and time range, link to details.

Enterprise tables: sort, search, filter, paginate (or virtualize), sticky header and key columns, column visibility,
density options, bulk actions with clear selection state, keyboard access, responsive strategy (priority columns,
card view on mobile), export where needed. Breadcrumbs for deep hierarchies; consistent page titles and navigation.

Data visualization: pick the chart for the question (trend → line, comparison → bar, part-to-whole → stacked bar,
avoid pies with many slices), label axes and units, start bars at zero, no 3D, few colors, colorblind-safe palette,
show context (targets, previous period), provide a table alternative for accessibility.

## 9. Async (`HTTP 202` != Done) & AI / Chat Product UX

- **Async Lifecycle Honesty**: Distinguish `Submitted -> Queued (HTTP 202) -> Processing -> Indexing/Finalizing -> Completed -> Failed -> Cancelled`. Never show a green "Completed/Ready" state on `HTTP 202 Accepted` while background processing or indexing is still running. Prevent duplicate submits via UI lock + idempotency keys.
- **Human-AI UX Resilience**: AI must feel explainable, predictable, trustworthy. Show thinking/generating/streaming states, allow stop, retry, regenerate, edit prompt, copy; render markdown and code readably (including mobile); show sources/citations when available; communicate limitations and low confidence; handle 0-hit retrieval, mid-stream disconnects, tool refusal, and prompt-injection warnings in retrieved docs; require human confirmation for consequential actions.

## 10. Design review output & Severity-First Gate

For a design task or audit, analyze: business objective, user flow (`US-ID -> FLOW-ID -> SCR-ID -> STATE-ID -> AC-ID`), 12-domain adversarial edge cases, accessibility, responsive behavior, component scalability, design-system consistency, 9-state coverage, mobile usability, hierarchy clarity, and engineering feasibility. Give findings with severity (CRITICAL/HIGH/MEDIUM/LOW/NIT) and concrete fixes.
- **Severity-First Gate**: Any unmitigated CRITICAL blocker (data loss, deceptive `HTTP 202` completion, inaccessible core flow, or permission leak) forces `REJECT / REVISE` regardless of heuristic score. Always label empirical user testing as `NOT TESTED` when only expert heuristic review was performed.

Checklist: hierarchy clear · spacing and type consistent · contrast AA · one clear CTA · no clutter · flow clear ·
all states present · keyboard and screen-reader usable · mobile/tablet/desktop checked · no overflow · tokens used ·
components reusable · no hidden interactions.

## 11. Anti-patterns

Fancy over clear · excessive animation, gradients, glassmorphism, low-contrast neumorphism, heavy shadows ·
tiny text · overloaded dashboards · confusing navigation · long ungrouped forms · unclear or multiple primary CTAs ·
broken hover/focus states · half-done responsive · desktop simply shrunk for mobile · modal stacking · color without
semantic meaning · icons without labels · inconsistent components · UX that makes users think hard.

Good design feels simple, natural, fast, error-resistant, accessible and trustworthy. It rarely feels "wow";
it feels clear.
