---
name: shadow-design
description: Design system tokens, user flows, wireframe specifications, component contracts, UI states (Loading/Empty/Error/Success), and cross-page visual consistency. Works alongside antislop-ui and antislop-layoutmobile. Trigger with /shadow-design.
---

# Shadow Design (`/shadow-design`) — Design System, User Flows & Component Contracts

Use this skill before or during frontend/mobile implementation to establish a cohesive **Design System**, **User Journey Map**, and **Component State Contract** so every screen feels intentionally crafted and consistent across the entire application.

---

## 1. Design System Foundation (Tokens Before Components)

Never hardcode arbitrary hex colors, pixel spacings, or font sizes per page. Define semantic design tokens in a single source of truth (`tailwind.config`, CSS custom properties `:root`, or Flutter `ThemeData`):

1. **Typography Scale**:
   - Font families: `--font-sans` (UI body), `--font-display` (headings), `--font-mono` (IDs, code, financial numbers with `font-variant-numeric: tabular-nums`).
   - Strict hierarchy: Page Title (`h1`), Section Header (`h2`), Card Title (`h3`), Body (`1rem`/`16px`), Secondary/Caption (`0.875rem`/`14px`).
2. **Semantic Color Tokens (WCAG AA/AAA Contrast Verified)**:
   - Surfaces: `bg-canvas`, `bg-surface`, `bg-elevated`, `bg-muted`.
   - Text: `text-primary`, `text-secondary`, `text-muted`, `text-on-brand`.
   - Status: `status-success`, `status-warning`, `status-danger`, `status-info` (always pair color with an icon or text badge — never rely on color alone).
3. **Spacing, Radius & Elevation Scale**:
   - 4px/8px spatial grid (`4, 8, 12, 16, 24, 32, 48, 64px`).
   - Consistent border-radius and border-width across cards, inputs, modals, and buttons.

---

## 2. User Flow & Wireframe Specification

For every feature module, document:
1. **Entry Point & Navigation Path**: How the user reaches the screen, breadcrumbs, and back-navigation behavior.
2. **Information Hierarchy**: Primary action (max 1 primary CTA per screen view), secondary actions, and progressive disclosure (don't dump 30 fields into a single ungrouped form).
3. **Responsive Reflow Contract (`375px` Mobile -> `768px` Tablet -> `1440px` Desktop)**:
   - How data tables transform or scroll horizontally with sticky key columns on mobile.
   - Touch target minimums (`44x44px`) and bottom sheet / drawer patterns on mobile vs modals/popovers on desktop.

---

## 3. Mandatory 5-State Component Contract

Every data-driven page or component MUST explicitly design and implement all 5 states:
1. **Loading State**: Skeleton placeholders matching the final layout geometry (avoid layout shift / CLS spikes).
2. **Empty State**: Clear explanation of why no data exists + a direct CTA button to create the first item or reset active filters.
3. **Populated / Ideal State**: Including edge cases for long names/titles (`text-overflow: ellipsis` or clean wrapping) and large numbers (`tabular-nums`).
4. **Validation / Partial Error State**: Inline field-level error messages linked via `aria-describedby`, preserving user-typed form input.
5. **System / Network Error State**: Human-readable explanation with a **Retry** button and request correlation ID.
