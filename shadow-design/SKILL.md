---
name: shadow-design
description: Design system tokens, evidence-tagged UX discovery, US-ID to state-machine user flows, 9-state component contracts, async HTTP 202 & human-AI UX resilience, 12-domain adversarial walkthroughs, and severity-first UX release gates. Works alongside antislop-ui and antislop-layoutmobile. Trigger with /shadow-design.
---

# Shadow Design (`/shadow-design`) — Product Design, User Flows, 9-State Machines & Design Systems

Use this skill before or during frontend/mobile/AI product implementation to establish an **Evidence-Disciplined Product Specification**, **Brownfield Pattern Inventory**, **User Story → Flow → State Traceability**, **Design System Tokens**, and **Severity-First UX Release Gate**.

> **Provenance & Safe Upstream Sync**: Enhanced with vendored reference modules and templates from `ai-product-designer-skill-pack` plus 4 audited `T1_AUDITED_MARKDOWN` external Git skill packs (`ghaida/intent`, `jpoindexter/ux-flow-skills`, `phuryn/pm-skills`, `Owl-Listener/designer-skills`), all tracked with license, commit SHA, and per-file SHA-256 checksums in [`UPSTREAM_PROVENANCE.json`](file:///d:/Ridhuan%20Ngoding%20Moment/SKILL/shadow-design/UPSTREAM_PROVENANCE.json). Verify integrity or safely pull upstream GitHub updates anytime via:
> ```bash
> python shadow-quality/scripts/skill_vendor_sync.py verify shadow-design
> python shadow-quality/scripts/skill_vendor_sync.py check-remote-updates shadow-design
> python shadow-quality/scripts/skill_vendor_sync.py update-remote shadow-design
> ```

---

## 0. Foreign-Key Reference Routing (Load Only What the Task Needs)

| Design Phase / Topic | Reference File |
|---|---|
| Discovery, JTBD & Evidence Tagging | [`references/ai-product-designer-skill-pack/01-discovery-and-evidence.md`](file:///d:/Ridhuan%20Ngoding%20Moment/SKILL/shadow-design/references/ai-product-designer-skill-pack/01-discovery-and-evidence.md) |
| User Stories (`US-ID`), Flows & Preconditions | [`references/ai-product-designer-skill-pack/02-story-to-flow.md`](file:///d:/Ridhuan%20Ngoding%20Moment/SKILL/shadow-design/references/ai-product-designer-skill-pack/02-story-to-flow.md) |
| 9-State Machines, Concurrency (`ETag`) & 12-Domain Edge Cases | [`references/ai-product-designer-skill-pack/03-state-machine-and-edge-cases.md`](file:///d:/Ridhuan%20Ngoding%20Moment/SKILL/shadow-design/references/ai-product-designer-skill-pack/03-state-machine-and-edge-cases.md) |
| Information Architecture, Navigation & Wayfinding | [`references/ai-product-designer-skill-pack/04-information-architecture-and-patterns.md`](file:///d:/Ridhuan%20Ngoding%20Moment/SKILL/shadow-design/references/ai-product-designer-skill-pack/04-information-architecture-and-patterns.md) |
| Existing Product Guardian & Token Discipline | [`references/ai-product-designer-skill-pack/05-existing-system-guardian.md`](file:///d:/Ridhuan%20Ngoding%20Moment/SKILL/shadow-design/references/ai-product-designer-skill-pack/05-existing-system-guardian.md) |
| Accessibility (WCAG 2.2 AA), Mobile & Microcopy | [`references/ai-product-designer-skill-pack/06-accessibility-responsive-content.md`](file:///d:/Ridhuan%20Ngoding%20Moment/SKILL/shadow-design/references/ai-product-designer-skill-pack/06-accessibility-responsive-content.md) |
| Privacy, RBAC, Security & Anti-Dark-Pattern Ethics | [`references/ai-product-designer-skill-pack/07-privacy-security-and-ethics.md`](file:///d:/Ridhuan%20Ngoding%20Moment/SKILL/shadow-design/references/ai-product-designer-skill-pack/07-privacy-security-and-ethics.md) |
| Async (`HTTP 202` != Done) & Human-AI Failure Modes | [`references/ai-product-designer-skill-pack/08-async-and-ai-ux.md`](file:///d:/Ridhuan%20Ngoding%20Moment/SKILL/shadow-design/references/ai-product-designer-skill-pack/08-async-and-ai-ux.md) |
| Severity-First UX Review & Release Gates | [`references/ai-product-designer-skill-pack/09-ux-evaluation-and-gates.md`](file:///d:/Ridhuan%20Ngoding%20Moment/SKILL/shadow-design/references/ai-product-designer-skill-pack/09-ux-evaluation-and-gates.md) |
| Engineering Handoff, Traceability & Metrics | [`references/ai-product-designer-skill-pack/10-handoff-and-measurement.md`](file:///d:/Ridhuan%20Ngoding%20Moment/SKILL/shadow-design/references/ai-product-designer-skill-pack/10-handoff-and-measurement.md) |
| Curated External Projects & Trust Tiers (`T0`–`T3`) | [`references/ai-product-designer-skill-pack/11-external-projects-and-trust.md`](file:///d:/Ridhuan%20Ngoding%20Moment/SKILL/shadow-design/references/ai-product-designer-skill-pack/11-external-projects-and-trust.md) |
| **Upstream Pack**: Design with Intent (`ghaida/intent`, CC0-1.0, `T1`) | [`references/external-upstreams/ghaida-intent/README.md`](file:///d:/Ridhuan%20Ngoding%20Moment/SKILL/shadow-design/references/external-upstreams/ghaida-intent/README.md) (`skills/intent`, `strategize`, `investigate`, `blueprint`, `journey`, `organize`, `wireframe`, `articulate`, `evaluate`, `fortify`, `include`, `transpose`, `localize`, `measure`, `philosopher`, `storytelling`, `specify`, `present`) |
| **Upstream Pack**: UX Flow Skills (`jpoindexter/ux-flow-skills`, MIT, `T1`) | [`references/external-upstreams/ux-flow-skills/README.md`](file:///d:/Ridhuan%20Ngoding%20Moment/SKILL/shadow-design/references/external-upstreams/ux-flow-skills/README.md) (15 production flow blueprints + `userflow` dispatcher — see §0b below) |
| **Upstream Pack**: PM Skills (`phuryn/pm-skills`, MIT, `T1`) | [`references/external-upstreams/pm-skills/README.md`](file:///d:/Ridhuan%20Ngoding%20Moment/SKILL/shadow-design/references/external-upstreams/pm-skills/README.md) (`pm-product-discovery`, `pm-product-strategy`, `pm-execution`, `pm-market-research`, `pm-data-analytics`, `pm-go-to-market`, `pm-ai-shipping`) |
| **Upstream Pack**: Designer Skills (`Owl-Listener/designer-skills`, MIT, `T1`) | [`references/external-upstreams/designer-skills/README.md`](file:///d:/Ridhuan%20Ngoding%20Moment/SKILL/shadow-design/references/external-upstreams/designer-skills/README.md) (`design-research`, `ux-strategy`, `interaction-design`, `ui-design`, `design-systems`, `visual-critique`, `prototyping-testing`, `design-ops`, `designer-toolkit`) |
| Feature Design Spec Template | [`templates/FEATURE-DESIGN.md`](file:///d:/Ridhuan%20Ngoding%20Moment/SKILL/shadow-design/templates/FEATURE-DESIGN.md) |
| UX Review & Release Gate Template | [`templates/UX-REVIEW.md`](file:///d:/Ridhuan%20Ngoding%20Moment/SKILL/shadow-design/templates/UX-REVIEW.md) |

### 0b. 15-Domain Battle-Tested UX Flow Routing (`ux-flow-skills`)
When designing or implementing any of these 15 core product flows, load the corresponding `T1` reference before writing UI code:
- **Onboarding & First-Run Activation**: [`skills/flow-onboarding/SKILL.md`](file:///d:/Ridhuan%20Ngoding%20Moment/SKILL/shadow-design/references/external-upstreams/ux-flow-skills/skills/flow-onboarding/SKILL.md)
- **Authentication, Passkeys, Magic Links, SSO & 2FA**: [`skills/flow-auth/SKILL.md`](file:///d:/Ridhuan%20Ngoding%20Moment/SKILL/shadow-design/references/external-upstreams/ux-flow-skills/skills/flow-auth/SKILL.md)
- **Empty States, Skeletons & Perceived Speed**: [`skills/flow-empty-states/SKILL.md`](file:///d:/Ridhuan%20Ngoding%20Moment/SKILL/shadow-design/references/external-upstreams/ux-flow-skills/skills/flow-empty-states/SKILL.md)
- **Permission Priming & Just-in-Time Prompts**: [`skills/flow-permissions/SKILL.md`](file:///d:/Ridhuan%20Ngoding%20Moment/SKILL/shadow-design/references/external-upstreams/ux-flow-skills/skills/flow-permissions/SKILL.md)
- **Checkout, Cart, Express Pay & Confirmation**: [`skills/flow-checkout/SKILL.md`](file:///d:/Ridhuan%20Ngoding%20Moment/SKILL/shadow-design/references/external-upstreams/ux-flow-skills/skills/flow-checkout/SKILL.md)
- **Pricing, Trials, Paywalls & Honest Cancellation**: [`skills/flow-paywall/SKILL.md`](file:///d:/Ridhuan%20Ngoding%20Moment/SKILL/shadow-design/references/external-upstreams/ux-flow-skills/skills/flow-paywall/SKILL.md)
- **Settings IA, Account Management & Danger Zones**: [`skills/flow-settings/SKILL.md`](file:///d:/Ridhuan%20Ngoding%20Moment/SKILL/shadow-design/references/external-upstreams/ux-flow-skills/skills/flow-settings/SKILL.md)
- **Sharing Links, Invites & Collaboration Cues**: [`skills/flow-sharing/SKILL.md`](file:///d:/Ridhuan%20Ngoding%20Moment/SKILL/shadow-design/references/external-upstreams/ux-flow-skills/skills/flow-sharing/SKILL.md)
- **Navigation (Tab Bar vs Sidebar vs Command Palette)**: [`skills/flow-navigation/SKILL.md`](file:///d:/Ridhuan%20Ngoding%20Moment/SKILL/shadow-design/references/external-upstreams/ux-flow-skills/skills/flow-navigation/SKILL.md)
- **App Shell (Sidebar+Main, 3-Pane, Master-Detail Collapse)**: [`skills/flow-app-shell/SKILL.md`](file:///d:/Ridhuan%20Ngoding%20Moment/SKILL/shadow-design/references/external-upstreams/ux-flow-skills/skills/flow-app-shell/SKILL.md)
- **Enterprise Data Tables, Bulk Actions & Pagination**: [`skills/flow-tables/SKILL.md`](file:///d:/Ridhuan%20Ngoding%20Moment/SKILL/shadow-design/references/external-upstreams/ux-flow-skills/skills/flow-tables/SKILL.md)
- **Search, Faceted Filters & Zero-Results Recovery**: [`skills/flow-search/SKILL.md`](file:///d:/Ridhuan%20Ngoding%20Moment/SKILL/shadow-design/references/external-upstreams/ux-flow-skills/skills/flow-search/SKILL.md)
- **Forms, Validation Timing, Wizards & Save-and-Resume**: [`skills/flow-forms/SKILL.md`](file:///d:/Ridhuan%20Ngoding%20Moment/SKILL/shadow-design/references/external-upstreams/ux-flow-skills/skills/flow-forms/SKILL.md)
- **Error Anatomy, Undo-over-Confirm, Offline & Work Preservation**: [`skills/flow-errors/SKILL.md`](file:///d:/Ridhuan%20Ngoding%20Moment/SKILL/shadow-design/references/external-upstreams/ux-flow-skills/skills/flow-errors/SKILL.md)
- **AI / Chat UX, Streaming, Tool-Use Display & Human-in-the-Loop**: [`skills/flow-ai-chat/SKILL.md`](file:///d:/Ridhuan%20Ngoding%20Moment/SKILL/shadow-design/references/external-upstreams/ux-flow-skills/skills/flow-ai-chat/SKILL.md)

---

## 1. Evidence Discipline & Existing Product Guardian (Before Drawing Screens)

1. **Mandatory Evidence Classification**:
   Every product/UX claim MUST be explicitly labeled:
   - `[EVIDENCE]`: Grounded in real codebase routes/components, analytics, support tickets, or dated user research.
   - `[ASSUMPTION]`: Plausible product hypothesis — must state **risk if wrong** and **validation plan**.
   - `[PROPOSAL]`: Recommended design direction awaiting Monarch/stakeholder decision.
   - `[NEEDS VALIDATION]`: Unverified usability or behavioral question.
   - *Strict Prohibition*: Never fabricate user interviews, quote fake personas as empirical evidence, or claim usability is "validated" without actual user testing.
2. **Existing Product Guardian (Brownfield UI Preservation)**:
   Before designing or modifying UI in an existing repository, build a compact pattern inventory (`pattern -> where used -> accepted behavior -> defects -> recommendation`). Reuse established navigation, shells, form patterns, table toolbars, modal/drawer rules, and status nomenclature unless fixing a documented usability/accessibility defect.

---

## 2. Design System Foundation (Tokens Before Components)

Never hardcode arbitrary hex colors, pixel spacings, or font sizes per page. Define semantic design tokens in a single source of truth (`tailwind.config`, CSS custom properties `:root`, or Flutter `ThemeData`):

1. **Typography Scale**:
   - Font families: `--font-sans` (UI body), `--font-display` (headings), `--font-mono` (IDs, code, financial numbers with `font-variant-numeric: tabular-nums`).
   - Strict hierarchy: Page Title (`h1`), Section Header (`h2`), Card Title (`h3`), Body (`1rem`/`16px` — prevents iOS auto-zoom on inputs), Secondary/Caption (`0.875rem`/`14px`).
2. **Semantic Color Tokens (WCAG 2.2 AA/AAA Contrast Verified)**:
   - Surfaces: `bg-canvas`, `bg-surface`, `bg-elevated`, `bg-muted`.
   - Text: `text-primary`, `text-secondary`, `text-muted`, `text-on-brand`.
   - Status: `status-success`, `status-warning`, `status-danger`, `status-info` (always pair color with an icon, shape, or text badge — never rely on color alone).
3. **Spacing, Radius & Elevation Scale**:
   - 4px/8px spatial grid (`4, 8, 12, 16, 24, 32, 48, 64px`).
   - Consistent border-radius and border-width across cards, inputs, modals, and buttons.

---

## 3. User Story → Flow → Wireframe Traceability (`US-ID -> FLOW-ID -> SCR-ID -> STATE-ID -> AC-ID`)

For every feature module, maintain stable IDs across revisions (`CONFIRMED | PROPOSED | UNKNOWN | DEFERRED`):
1. **Entry Point, Deep Links & Wayfinding**: How the user reaches the screen (including cold deep-link with expired auth or missing permissions), breadcrumbs, unsaved-change guard on back navigation, and return-to-origin behavior.
2. **Information Hierarchy & Microcopy**: Primary action (max 1 primary CTA per screen view using outcome verbs like `"Save invoice"`, never `"OK"`), secondary actions, and progressive disclosure. Error copy must state **what happened**, **why (if helpful)**, and **how to recover** while preserving all user-typed input.
3. **Responsive Reflow & I18n Contract (`320px/375px` Mobile -> `768px` Tablet -> `1440px` Desktop + `200%` Zoom)**:
   - How data tables transform or scroll horizontally with sticky key columns on mobile.
   - Touch target minimums (`44x44px` recommended, WCAG 2.2 minimum `24x24 CSS px`) and bottom sheet / drawer patterns on mobile vs modals/popovers on desktop.
   - Layout resilience for `+30–40%` translated text expansion (e.g., Bahasa Indonesia / German), locale-aware date/currency formatting, and logical CSS properties (`margin-inline`, `padding-inline`).

---

## 4. Mandatory 9-State Component & Transition Contract

Model interactive screens and components as explicit state transitions (`State + Event + Guard -> Next State / Side Effect / Visible Feedback`). Every data-driven or transactional view MUST account for all **9 states**:

1. **Initial / Pre-Action State**: Clear entry affordance, preconditions, and default focus/selection.
2. **Loading / Pending State**: Skeleton placeholders matching final geometry (zero CLS spikes); step/queue progress for operations `>3s`.
3. **Empty State (3 Distinct Sub-States)**:
   - *First-use / No data yet*: Welcoming explanation + primary CTA to create the first record.
   - *No filter/search results*: Show active query/filters + 1-click **"Reset filters"** button.
   - *Empty due to error or permission*: Never disguise a failed API fetch or `403 Forbidden` as "0 items".
4. **Partial / Degraded State**: When one sub-widget or non-critical service fails, render available data and isolate the retry banner to the failed section.
5. **Populated / Success State**: Handle long strings (`text-overflow: ellipsis` or clean wrapping), `tabular-nums`, and unambiguous completion feedback.
6. **Validation / Recoverable Error State**: Inline field-level errors linked via `aria-describedby` + error summary for long forms; **never wipe user-typed form input on failed submit**.
7. **Permission-Denied (`401`/`403`) State**: Explain which role/permission is required and provide a safe action (request access, switch account, or return home) without leaking sensitive record metadata.
8. **Offline / Disconnected State**: Detect network loss, disable or queue unsafe mutations, preserve local draft state, and auto-reconcile on reconnect.
9. **Stale / Concurrent-Edit Conflict (`409` / `ETag` Mismatch) State**: When another user or tab updates the same record, block silent overwrites; present a diff or choice to reload/merge changes safely.

---

## 5. Async (`HTTP 202 Accepted` != Completed) & Human-AI UX Contract

1. **Asynchronous Lifecycle Honesty**:
   - Distinguish **Submitted -> Queued (`HTTP 202`) -> Processing -> Indexing/Finalizing -> Completed -> Failed -> Cancelled**.
   - Never display a green `"Completed"` or `"Ready"` toast on `HTTP 202 Accepted` when background worker indexing or settlement is still running.
   - Prevent duplicate submissions via disabled/loading submit state + server idempotency keys.
2. **Human-AI Interaction Resilience**:
   - Explicitly design for: **hallucination/uncertainty warnings**, **source citation links**, **empty retrieval (0 RAG hits)**, **partial stream disconnect**, **tool/permission refusal**, **latency spikes**, and **prompt-injection quarantine in untrusted retrieved documents**.
   - Provide **Stop generating**, **Retry**, **Edit prompt**, and **Human confirmation gates** before any destructive, financial, legal, or external-sending action.

---

## 6. 12-Domain Adversarial UX Walkthrough & Severity-First Release Gate

Before signing off on any feature design ([`templates/FEATURE-DESIGN.md`](file:///d:/Ridhuan%20Ngoding%20Moment/SKILL/shadow-design/templates/FEATURE-DESIGN.md)) or UX review ([`templates/UX-REVIEW.md`](file:///d:/Ridhuan%20Ngoding%20Moment/SKILL/shadow-design/templates/UX-REVIEW.md)):
1. **Run the 12-Domain Adversarial Walkthrough**:
   Test the flow against: *(1) Input extremes/paste/Unicode, (2) Validation recovery, (3) Double-click/back-button/refresh mid-submit, (4) Deep-link/logged-out entry, (5) Multi-tab/concurrent edit (`ETag`), (6) Slow/offline/partial API, (7) Empty vs no-results vs error, (8) Role/permission revocation mid-session, (9) Destructive action undo/confirmation, (10) Long lists/pagination/bulk selection, (11) Keyboard-only/screen-reader/zoom, and (12) Locale/timezone/DST boundaries*.
2. **Severity-First UX Quality Gate**:
   Heuristic scores (0–100) are internal expert estimates (`NOT TESTED` with real users unless empirical testing was executed). **Any unmitigated CRITICAL blocker** (irreversible data loss, deceptive `HTTP 202` success, broken keyboard/screen-reader core path, or permission leak) forces a **`REJECT / REVISE`** decision regardless of numeric score.
3. **Ethical & Anti-Dark-Pattern Gate (72+ Catalog)**:
   Cross-check flows against [`ghaida-intent/skills/intent/references/ethical-design.md`](file:///d:/Ridhuan%20Ngoding%20Moment/SKILL/shadow-design/references/external-upstreams/ghaida-intent/skills/intent/references/ethical-design.md) and [`07-privacy-security-and-ethics.md`](file:///d:/Ridhuan%20Ngoding%20Moment/SKILL/shadow-design/references/ai-product-designer-skill-pack/07-privacy-security-and-ethics.md). Strictly prohibit:
   - *Roach Motels / Asymmetric Friction*: Unsubscribing, cancelling a trial, revoking consent, or deleting an account must be as direct as signing up.
   - *Confirmshaming, Fake Urgency & Pre-checked Opt-ins*: Never pre-check marketing/telemetry consent or fabricate countdown timers.
   - *AI-Specific Dark Patterns*: Never disguise AI-generated estimates as verified human/legal truth, hide model errors, or silently train on private tenant inputs without explicit opt-in (UU PDP / GDPR / EU DSA compliance).
