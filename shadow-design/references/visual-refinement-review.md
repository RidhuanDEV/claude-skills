# Visual Refinement Review (Clean-Room 9-Pass Anti-Slop Methodology)

Use this guide when refining an existing UI screen whose visual noise, competing accents, inconsistent spacing, or generic styling obscures the user's primary task. Pair with [Visual hierarchy method](external-upstreams/designer-skills/visual-critique/skills/critique-visual-hierarchy/SKILL.md), [Existing product guardian](ai-product-designer-skill-pack/05-existing-system-guardian.md), and [UX evaluation and gates](ai-product-designer-skill-pack/09-ux-evaluation-and-gates.md).

> **Local-First & Zero-External-Script Policy:** Never download or run unverified third-party capture/video scripts. Perform static HTML/CSS audits locally via [`scripts/visual_refinement_audit.py`](../scripts/visual_refinement_audit.py) and, when rendered browser verification is authorized, use the project's own dev server + controlled Playwright/`shadow-browser` workflow with external network requests blocked.

---

## 1. Establish the Task Baseline & 5-Line Direction Brief

Before editing any style, record the comparison baseline and write a **5-line product direction** derived strictly from the product and user task (never from generic trends):

1. **Product:** What the screen does and for whom, in one plain sentence.
2. **Character:** Two or three concrete adjectives (e.g., `calm, exact, warm` or `dense, operational, brisk` — avoid empty buzzwords like `clean`, `modern`, `sleek`, `minimal`).
3. **Focal Moment (One Bright Element):** The single cue, visual, chart, or state that carries color and prominence for the primary task. On a monitoring/ops screen, the first cue may be an active alarm with its recovery action directly adjacent.
4. **Quiet Chrome:** Navigation, containers, secondary labels, and neutral controls stay tinted-neutral with at most one primary accent so nothing competes with the focal cue.
5. **Preserved Product Trait:** One intentional visual decision already working well that MUST be kept (tie to task evidence, e.g., high-contrast alarm banner or tabular telemetry digits).

Record route/component, viewport (`375px`, `768px`, `1440px`), theme (`light`/`dark`), and representative data state so before/after comparisons hold variables constant. Mark unavailable browser checks explicitly as `NOT_RUN`.

---

## 2. Diagnostic Triage (Heavy Slop vs Light Slop vs No Slop)

Scan the screen for concrete slop signals before deciding change scope:

| Signal Category | What to Flag | Safe Local Fix |
| --- | --- | --- |
| **Competing Emphasis** | Non-interactive badges, notes, or decorative icons styled with the same accent fill, size, or weight as the primary CTA | Demote decorative/informational cues to neutral surface tokens; reserve accent fill for the single primary action or critical alert |
| **Chrome Noise** | Glowing drop shadows on every card, gradient text on routine labels, decorative emojis in headings/nav, inconsistent border radii | Strip glow/gradient chrome; enforce nested radius math (`outerRadius = innerRadius + padding`) |
| **Typography & Numbers** | Mixed heading weights, unaligned metrics, body text `< 14px` or contrast `< 4.5:1` (`< 3:1` UI) | Apply `font-variant-numeric: tabular-nums` to metrics/tables; tighten scale to existing design-system tokens |
| **Spacing & Grouping** | Equal spacing everywhere (no proximity grouping), dead empty bands above the fold | Group related items tightly (`4–8px`) and separate distinct sections (`24–32px`) using existing spacing tokens |
| **Motion & States** | Bouncy/looping decorative animations, missing `:focus-visible`, missing `disabled`/`loading`/`error` distinction, animating layout properties | One calm easing curve, `transform`/`opacity` only, honor `prefers-reduced-motion`, preserve all 5 interactive states + keyboard Tab reachability |

- **Heavy slop:** Multiple categories fail across the viewport → run all 9 passes in order.
- **Light slop:** Structure is sound with 2–4 isolated defects → polish mode; patch only audited locations.
- **No slop:** State so plainly; suggest at most 2–3 exact micro-refinements and wait before editing.

---

## 3. Focused 9-Pass Redline Order

Complete each pass across the affected region before moving to the next:

1. **Task & Hierarchy Pass:** Verify where eye attention lands first; remove or demote cues competing with the primary task cue or critical alert.
2. **Layout & Proximity Pass:** Tighten intra-group gaps and widen inter-group separation; eliminate dead empty bands on initial viewport (`375px` & `1440px`).
3. **Surface & Elevation Pass:** Flatten redundant nested cards; replace heavy glows with subtle border + tonal surface separation.
4. **Color & Contrast Pass:** Restrict primary accent to the primary action/focal element; enforce WCAG 2.2 AA (`>= 4.5:1` text, `>= 3:1` UI controls) and never rely on color alone for state/alarms.
5. **Typography & Tabular Pass:** Align heading/label hierarchy, line lengths (`55–75ch` prose), and `tabular-nums` on counts, timestamps, prices, and telemetry.
6. **Radius & Control Geometry Pass:** Align button/input radii with container radii (`outer = inner + pad`); verify `>= 44x44px` touch targets on mobile.
7. **Iconography & Imagery Pass:** Replace generic placeholder boxes or emoji chrome with meaningful product previews or consistent `currentColor` icons.
8. **State & Motion Pass:** Verify `default`, `hover`, `active`, `:focus-visible` (`>= 3:1`), `disabled`, plus `loading`/`empty`/`error` states; ensure `prefers-reduced-motion` disables non-essential motion.
9. **Keyboard & Template Check:** Tab through the screen end-to-end to confirm primary actions and recovery flows remain sequentially focusable; run the *template test* (if swapping the product name still fits, sharpen copy and product-specific cues).

---

## 4. Deterministic Local Audit & Reporting Contract

Run the offline static structural audit on local HTML/component fixtures before and after refinement:

```powershell
python shadow-design/scripts/visual_refinement_audit.py path/to/screen.html --primary-id approve-btn
python -m unittest discover -s shadow-design/tests -v
```

Report every finding as:
`**location -> observed cue -> effect on task -> proposed change -> verification**`

- **Hard Gate:** Any refinement that breaks sequential keyboard focus (`tabindex="-1"`, `disabled` without cause, or `display:none`/`aria-hidden="true"` on a core action) **blocks acceptance** (`REJECT`), even if visual hierarchy looks cleaner.
- Separate **observed structural/rendered evidence** from **predicted usability gains** (mark predictions as hypotheses until tested with users).

---

## 5. Source Attribution & Provenance

Methodology adapted in clean room from *Unslop* by Damir Sokolovsky (`heydamir`), pinned commit `620163eedb3529d9cd23a3994ed8d287d06f760d` (`tar_sha256: 93a3f53f388a703870d6b011aa27c2bd921b97bb1abca045336604aa809d19c2`), licensed under **CC BY 4.0**. Shadow Army rebuilt the workflow for local-first offline verification with zero third-party executable scripts, adding task-preservation rules, WCAG 2.2 AA & keyboard focus regression gates, and deterministic local audit tooling.
- [Upstream SKILL.md at pinned SHA](https://github.com/heydamir/unslop/blob/620163eedb3529d9cd23a3994ed8d287d06f760d/skills/unslop/SKILL.md)
- [Upstream CC BY 4.0 License](https://github.com/heydamir/unslop/blob/620163eedb3529d9cd23a3994ed8d287d06f760d/LICENSE)
