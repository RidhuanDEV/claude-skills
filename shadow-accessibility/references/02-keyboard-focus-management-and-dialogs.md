# 02 — Keyboard Navigation, Focus Management, Modals/Dialogs & Composite Widgets

## 1. Purpose & Activation Conditions
Ensure 100% of application workflows can be operated smoothly **without a mouse** — enforcing natural DOM tab order, high-contrast `:focus-visible` rings, airtight modal/drawer focus trapping with trigger-button focus restoration, and zero keyboard focus traps. Activate whenever building or auditing modals, drawers, dropdown menus, tabs, tables, or custom keyboard interactions.

## 2. Prerequisites
- Semantic interactive elements (`01`) and design tokens with a `>= 3:1` focus-ring color against all light/dark surfaces.

## 3. Technical Principles & Constraints
- **Natural DOM Order (`tabindex="0"` or `-1`, NEVER `tabindex > 0`):** Every interactive control must be reachable via `Tab` / `Shift+Tab` in logical visual reading order. Never use positive `tabindex="1"`, `"2"`, etc. — they hijack tab order across the whole page and break immediately when components move! Use `tabindex="-1"` strictly for programmatic focus targets (e.g., `<main id="main-content" tabindex="-1">`, error summary banners, or roving-tabindex inactive tabs).
- **Mandatory Visible Focus Indicator (WCAG 2.2 SC 2.4.7 & 2.4.11 Focus Not Obscured):**
  - Style `:focus-visible` with a `>= 2px` solid outline (`outline-offset: 2px`, `>= 3:1` contrast against adjacent background). NEVER strip focus rings globally (`outline: none`) without a visible `:focus-visible` replacement!
  - Ensure sticky headers or fixed footers do **NOT** completely cover the focused element when tabbing (`scroll-margin-top: 5rem; scroll-margin-bottom: 5rem;` on focusable elements!).
- **The 4 Non-Negotiable Modal / Drawer / Dialog Laws:**
  1. **Prefer Native `<dialog>` (`dialog.showModal()`):** Native Baseline `<dialog>` automatically places the dialog in the top layer, handles `Escape` closing, makes background content inert, and integrates cleanly with screen readers!
  2. **Trap Focus Inside Open Modal:** Pressing `Tab` on the last control inside the modal wraps cleanly to the first control; `Shift+Tab` on the first wraps to the last — focus NEVER escapes into background page links!
  3. **Close on `Escape`:** Pressing `Escape` closes the topmost open dialog/popover/menu cleanly (without discarding unsaved data silently if confirmation is warranted).
  4. **Deterministic Focus Restoration:** When the modal closes (via Cancel, `Escape`, backdrop click, or Delete completion), focus MUST return to the **exact trigger button** that opened it (or, if the trigger row itself was deleted, to the next logical sibling row or table heading — NEVER dumped to `document.body`!).
- **Roving `tabindex` For Composite Controls (Tabs, Toolbars, Radio Groups, Menus):** A 6-tab bar should be **1 `Tab` stop** (NOT 6!), where `ArrowLeft`/`ArrowRight` moves focus between tabs and `Home`/`End` jumps to first/last!

## 4. Architecture & Implementation

```ts
// Strict TypeScript Accessible Modal Focus-Trap & Trigger Restoration Controller (0 any, 0 casts)
export interface FocusableHandle {
  readonly id: string
  focus(): void
}

export class DialogFocusManager {
  private triggerElement: FocusableHandle | null = null
  private isOpen = false

  public open(trigger: FocusableHandle | null, initialFocusTarget: FocusableHandle): void {
    this.triggerElement = trigger
    this.isOpen = true
    initialFocusTarget.focus()
  }

  public handleTabKey(
    orderedModalControls: readonly FocusableHandle[],
    activeControlId: string,
    shiftKey: boolean,
  ): FocusableHandle | null {
    if (!this.isOpen || orderedModalControls.length === 0) return null
    const first = orderedModalControls[0]
    const last = orderedModalControls[orderedModalControls.length - 1]
    if (!first || !last) return null

    if (shiftKey && activeControlId === first.id) {
      last.focus()
      return last
    }
    if (!shiftKey && activeControlId === last.id) {
      first.focus()
      return first
    }
    return null
  }

  public close(fallbackTarget?: FocusableHandle): void {
    this.isOpen = false
    const restoreTo = this.triggerElement ?? fallbackTarget ?? null
    this.triggerElement = null
    restoreTo?.focus()
  }
}
```

```css
/* WCAG 2.2 AA Focus-Visible Ring + Sticky-Header Focus-Not-Obscured Guard + Pointer Craft */
:where(a[href], button:not(:disabled), input, select, textarea, summary, [tabindex]:not([tabindex="-1"])) {
  scroll-margin-block: 5.5rem;
}

:where(button:not(:disabled), [role="button"], summary, select:not(:disabled), label[for]) {
  cursor: pointer;
}

:where(button:disabled, select:disabled, input:disabled) {
  cursor: not-allowed;
}

:where(a[href], button, input, select, textarea, summary, [tabindex]):focus-visible {
  outline: 2px solid var(--focus-ring, #2563eb);
  outline-offset: 2px;
}
```

### Standard WAI-ARIA Keyboard Interaction Contract Matrix

| Widget | `Tab` / `Shift+Tab` | `Arrow` Keys | `Enter` / `Space` | `Escape` |
| :--- | :--- | :--- | :--- | :--- |
| **Button** | Focuses button | N/A | Both `Enter` & `Space` activate | N/A |
| **Link (`<a href>`)** | Focuses link | N/A | `Enter` navigates (`Space` scrolls) | N/A |
| **Modal Dialog (`<dialog>`)** | Traps & cycles inside dialog | N/A | Activates focused control | Closes dialog & restores trigger focus |
| **Tabs (`role="tablist"`)** | Moves into/out of tablist (1 stop) | `Left`/`Right` switches tabs; `Home`/`End` | Activates manual tab | N/A |
| **Dropdown Menu (`role="menu"`)** | Closes menu & moves to next focusable | `Up`/`Down` moves item focus | Activates item & restores trigger focus | Closes menu & restores trigger focus |
| **Row Delete Action** | Normal order | N/A | Opens confirm or deletes with Undo | Restores focus to next row / table heading |

## 5. Platform/Vendor Variations
- **macOS Safari Full Keyboard Access:** macOS Safari skips `<a>` and `<button>` on `Tab` unless "Use keyboard navigation to move focus between controls" is enabled in macOS System Settings (`Option+Tab` works regardless) — note this when testing on macOS so you don't misdiagnose Safari settings as a broken DOM!
- **Tailwind CSS v4 Preflight Warning:** Tailwind v4 sets `button { cursor: default }` — ALWAYS restore `cursor: pointer` on enabled interactive buttons and `cursor: not-allowed` on disabled buttons (`antislop-ui` Hard UI Craft Floor!).
- **Native Popover API (`popover="auto"`):** Baseline native HTML Popovers automatically close on `Escape` and light-dismiss outside clicks without brittle global `document.addEventListener('click')` listeners!

## 6. Decision Matrix & Trade-Offs

| Modal / Overlay Choice | Focus Trap & `inert` | `Escape` & Top Layer | Bundle Size | Recommendation |
| :--- | :--- | :--- | :--- | :--- |
| **Native `<dialog>` (`showModal()`)** | Built-in by browser! | Built-in! | `0 KB` | **Default** for simple/standard modals |
| **Radix Dialog / React Aria Modal** | Battle-tested + portal + restore | Built-in + nested stack | `~6–10 KB` | Best for complex nested modals/drawers in React |
| **Custom `div.modal-backdrop` without trap** | **BROKEN** (escapes to background) | Often missing | Fragile | **FORBIDDEN** |

## 7. Real Production Scenario
In an admin invoice table, pressing `Enter` on a row's "Approve" button opened a custom `<div>` modal. Keyboard users could not reach the "Confirm" button without tabbing past 80 background table rows first, pressing `Escape` did nothing, and after closing the modal focus reset to the top logo! Migrating to native `<dialog>` + `DialogFocusManager` trigger restoration + `scroll-margin-block: 5.5rem` (so the sticky header stopped hiding focused rows) cut keyboard approval time from 45 seconds to 3 seconds and passed WCAG 2.2 AA Focus Not Obscured (`2.4.11`).

## 8. Failure Modes & Edge Cases
- **WRONG:** Deleting a selected item from a list/modal and removing the focused button from the DOM without moving focus anywhere (screen-reader focus drops silently to `<body>`!).
  **RIGHT:** Explicitly focus the next item in the list, the previous item if the last was deleted, or the empty-state heading/add button.
- **WRONG:** Trapping focus inside an embedded map, rich-text editor, or widget with NO documented `Escape` / exit shortcut (WCAG 2.1.2 No Keyboard Trap — immediate AA failure!).
  **RIGHT:** Ensure users can always leave every embedded component using `Tab`/`Shift+Tab` or a clearly announced `Escape` shortcut.

## 9. Testing & Verification
- Perform a full **Keyboard-Only Smoke Test** (unplug/ignore mouse for 2 minutes): verify Skip Link, full `Tab`/`Shift+Tab` sweep, visible focus ring on every element, modal trap + `Escape` + exact trigger focus return, and zero elements hidden behind sticky headers.
- Run `python -m unittest discover -s shadow-accessibility/tests -v` (verifies `test_c04_modal_dialog_escape_restores_trigger_focus` and `a11y_html_verifier.py`).

## 10. Operational Considerations
- Pair focus-restoration checks with Playwright keyboard assertions (`page.keyboard.press('Tab')`, `page.keyboard.press('Escape')`, `expect(trigger).toBeFocused()`) inside `/shadow-browser`.

## 11. Authoritative References
- W3C WCAG 2.2 — *SC 2.1.1 Keyboard, 2.1.2 No Keyboard Trap, 2.4.7 Focus Visible, 2.4.11 Focus Not Obscured (Minimum)*.
- MDN Web Docs — *`<dialog>` Element & `inert` Attribute*.
- WAI-ARIA APG — *Modal Dialog Pattern & Roving Tabindex*.

## 12. Limitations & When NOT to Use
- Never add custom single-letter global hotkeys (`j`, `k`, `d` for delete!) without either requiring a modifier (`Ctrl`/`Alt`) or providing a toggle to disable/remap them — WCAG 2.1.4 Character Key Shortcuts forbids un-disableable single-key shortcuts that misfire for speech-input users!
