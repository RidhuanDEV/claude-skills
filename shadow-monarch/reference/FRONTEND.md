# FRONTEND — Client Architecture, State & Rendering

Visual/UX rules live in DESIGN.md; framework idioms for TypeScript/React/Next live in lang-TYPESCRIPT-NODE.md,
Flutter in lang-DART-FLUTTER.md. This file covers engineering of client applications.

## 1. Architecture

Separate concerns: **UI (presentation) · state · business logic · data fetching · API communication**.
Avoid components that fetch, validate, transform, mutate, apply business rules and render hundreds of lines at once.
Extract hooks/services/view-models where it improves clarity; do not fragment into dozens of trivial components.

Feature-based structure:
```text
src/features/<feature>/{components, hooks, services|api, schemas, types}
src/shared/{components, hooks, lib, styles}
```
- UI components do not know API internals; an API client layer owns URLs, headers, error mapping.
- Form validation uses explicit schemas (e.g. Zod/Yup) shared with type definitions where possible.
- Business rules that matter for security or integrity are **re-enforced on the server**; the client only mirrors them for UX.

## 2. State

Ask: does this data really need to be global? Escalate only as needed:
local state → lifted state → context (low-frequency values: theme, auth user, locale) → external store (Zustand/Redux/Pinia/Riverpod).
- **Server state is not client state.** Use a server-state library (TanStack Query, SWR, RTK Query, Apollo) for caching,
  deduping, refetching, invalidation, optimistic updates — not hand-rolled `useEffect` + `useState` fetches.
- One source of truth. Derive values instead of syncing copies; do not mirror props into state.
- URL is state too: filters, pagination, tabs and selected IDs belong in the URL when users expect to share or refresh them.
- Model async UI states explicitly: `idle | loading | success | error` (discriminated unions), plus empty state.

## 3. TypeScript on the client

Types are design tools: domain models, discriminated unions for states and API results, type guards at boundaries,
`unknown` + validation for external data (never trust `as SomeType` on API responses — parse with a schema).
Avoid `any`, non-null assertions as a habit, and type gymnastics nobody can maintain.

## 4. Rendering and effects (React-family, adapt for others)

- Effects are for synchronizing with external systems, not for deriving data. Every subscription, timer, listener,
  observer, WebSocket/SSE and AbortController has cleanup.
- Watch for stale closures, unstable dependencies (new objects/functions each render), infinite effect loops,
  race conditions in async effects (ignore or abort outdated responses).
- Memoize (`memo`, `useMemo`, `useCallback`) only where profiling shows a problem or referential stability is required.
- Stable, unique `key`s from data IDs — never array index for reorderable lists.
- SSR/SSG/RSC: avoid hydration mismatches (no `Date.now()`, `Math.random()`, `window` during render); keep secrets and
  server-only code out of client bundles; know which components are server vs client.
- Error boundaries around risky subtrees; user-friendly fallbacks.

## 5. Performance

Measure first (Lighthouse, Web Vitals: LCP, INP, CLS; React Profiler; bundle analyzer). Then:
code splitting and lazy routes, virtualization for long lists, image optimization (correct size, modern formats,
lazy loading, explicit dimensions to prevent layout shift), debounce search inputs, avoid shipping large libraries for
trivial tasks, cache static assets with content hashes. Perceived performance matters: skeletons, optimistic UI, streaming.

## 6. Browser security (details in SECURITY.md)

- Never inject unsanitized HTML (`dangerouslySetInnerHTML`, `v-html`, `innerHTML`); sanitize with DOMPurify when rich text is required.
- Validate URLs before using them in `href`/`src` (block `javascript:`); use `rel="noopener noreferrer"` for external `target="_blank"`.
- No secrets in frontend code or public env vars (`NEXT_PUBLIC_*`, `VITE_*` are public).
- Tokens: prefer HttpOnly Secure SameSite cookies over `localStorage` for session tokens in high-risk apps; understand the XSS/CSRF trade-off.
- CSP compatible with required assets (maps, fonts, workers, media, analytics); avoid `unsafe-inline` scripts.

## 7. Accessibility and responsiveness (engineering side)

Semantic HTML first (`button`, `a`, `label`, `nav`, `main`, headings in order); ARIA only when native semantics are insufficient.
Keyboard operable, visible focus, focus management for modals/route changes, labels on inputs, alt text,
`prefers-reduced-motion`. Test at mobile, tablet, desktop, large screens, 200% zoom, long text and localized strings.
UI must tolerate unexpected content length.

## 8. Every data-driven view handles

loading · empty · error (with retry) · partial data · slow network · offline where relevant · permission denied ·
session expired (redirect or refresh flow) · double submit (disable or dedupe) · stale data after mutation (invalidate).

## 9. Frontend checklist

Concerns separated · server state via a proper library · no duplicated sources of truth · effects cleaned up ·
API responses validated · no secrets in bundle · no unsanitized HTML · accessible and keyboard-usable ·
responsive and tolerant of long content · all async states designed · measured before optimized.
