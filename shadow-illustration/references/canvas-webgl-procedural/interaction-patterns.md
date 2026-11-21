# Interaction Patterns: Pointer, Touch, Gestures & State Machines

## 1. Core Concepts
Interactive visuals bridge pointer/touch input with continuous graphical feedback through **Unified Pointer Events**, **cached coordinate normalization**, **damped influence envelopes**, and **non-intrusive scroll ergonomics**.

## 2. Technical Rules
- **Unified Pointer Pipeline:** Use `pointerdown`, `pointermove`, `pointerup`, `pointercancel`, and `pointerleave` instead of separate mouse and touch listeners.
- **Coordinate Normalization & WebGL Y-Flip:** Convert viewport coordinates using a cached `DOMRect` (updated on `ResizeObserver` and passive scroll) into `[0..1]`; pass `1.0 - normY` when targeting WebGL fragment `gl_FragCoord` / bottom-left UV conventions.
- **Scroll Non-Interference:** Set `pointer-events: none` on ambient background canvases (tracking pointer passively on `window`/parent) so mobile vertical scrolling, text selection, and button clicks are never hijacked. For direct-manipulation surfaces (pan/zoom diagrams), declare explicit CSS `touch-action: none` (or `touch-action: pan-y`) and pair `setPointerCapture(e.pointerId)` with `releasePointerCapture`.

## 3. Implementation Examples
```ts
export interface NormalizedPointer {
  readonly x: number
  readonly y: number
  readonly webglY: number
  readonly active: boolean
}

export function normalizePointerEvent(
  event: { readonly clientX: number; readonly clientY: number },
  rect: { readonly left: number; readonly top: number; readonly width: number; readonly height: number },
): NormalizedPointer {
  const w = Math.max(rect.width, 1)
  const h = Math.max(rect.height, 1)
  const x = Math.min(Math.max((event.clientX - rect.left) / w, 0), 1)
  const y = Math.min(Math.max((event.clientY - rect.top) / h, 0), 1)
  return { x, y, webglY: 1 - y, active: true }
}
```

## 4. Best Practices
- Fade a scalar `pointerInfluence` smoothly (`0 -> 1` on enter, `1 -> 0` on leave/cancel via exponential damping) so interactive fields never snap abruptly at canvas edges.
- Model direct-manipulation tools with an explicit state machine (`IDLE -> HOVERED -> PRESSED -> DRAGGING -> SETTLING`) and set `cursor: grab` / `cursor: grabbing` or `cursor: pointer` only over genuinely actionable targets.

## 5. Anti-patterns (WRONG vs RIGHT)
- **WRONG:** Calling `canvas.getBoundingClientRect()` synchronously inside every `pointermove` while mutating DOM styles (triggers forced synchronous layout thrashing).
- **RIGHT:** Cache the bounding rect in `ResizeObserver` + passive scroll listener and read cached bounds during `pointermove`.
- **WRONG:** Leaving a sticky hover highlight frozen at the last tap coordinate on mobile touch screens (`matchMedia('(hover: none)')`).
- **RIGHT:** Decay `pointerInfluence` back to `0` after `pointerup` / `pointercancel` on touch devices.

## 6. Production Considerations
- Ensure every interactive canvas control (e.g., node selection in a diagram) has an equivalent keyboard focusable trigger or accessible table/list fallback.
