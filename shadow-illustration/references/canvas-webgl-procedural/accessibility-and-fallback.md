# Accessibility, Feature Detection & Graceful Degradation

## 1. Core Concepts
Resilient web graphics combine **runtime capability detection**, a **3-tier progressive degradation ladder** (`WebGL2 -> Canvas 2D -> Static CSS/SVG`), **live `prefers-reduced-motion` subscription**, and **WCAG 2.2 AA contrast/semantic compliance**.

## 2. Technical Rules
- **3-Tier Capability Ladder:** Feature-detect WebGL2 (`canvas.getContext('webgl2')`) and reject CPU software emulators (`SwiftShader` / `llvmpipe` via `WEBGL_debug_renderer_info`) -> fall back to lightweight Canvas 2D -> fall back to static CSS gradient/SVG poster when JS or Canvas is unavailable.
- **Live Reduced-Motion Compliance:** Check `window.matchMedia('(prefers-reduced-motion: reduce)')` on mount AND subscribe to `'change'` events. When active, stop `requestAnimationFrame` and render a single curated static keyframe (`renderAt(heroStillTime)`).
- **Semantic ARIA & Keyboard Safety:** Mark decorative backdrops `aria-hidden="true"` and `tabIndex={-1}`. For informative visualizations or diagrams, provide `role="img"` + descriptive `aria-label` (or visually hidden summary table) and keyboard-accessible controls.
- **Pause Control (WCAG 2.2.2):** For continuous non-essential motion exceeding 5 seconds, either honor `prefers-reduced-motion` + subtle ambient restraint or expose an accessible pause/play toggle.

## 3. Implementation Examples
```ts
export type RenderTier = 'webgl2' | 'canvas2d' | 'static-css'

export function detectOptimalRenderTier(preferWebGL = true): RenderTier {
  if (typeof document === 'undefined') return 'static-css'
  const testCanvas = document.createElement('canvas')
  if (preferWebGL) {
    const gl = testCanvas.getContext('webgl2')
    if (gl) {
      const dbg = gl.getExtension('WEBGL_debug_renderer_info')
      const renderer = dbg ? String(gl.getParameter(dbg.UNMASKED_RENDERER_WEBGL) || '') : ''
      if (!/SwiftShader|llvmpipe|Software/i.test(renderer)) return 'webgl2'
    }
  }
  return testCanvas.getContext('2d') ? 'canvas2d' : 'static-css'
}
```

## 4. Best Practices
- Feature-detect `typeof OffscreenCanvas !== 'undefined'` before transferring canvas control to a Web Worker; keep a main-thread fallback for older WebViews.
- Place a subtle semantic scrim gradient behind overlaid HTML text so contrast stays `>= 4.5:1` even during peak brightness of the animated backdrop.

## 5. Anti-patterns (WRONG vs RIGHT)
- **WRONG:** Checking `prefers-reduced-motion` only once at page load or leaving a blank/empty box when reduced motion is enabled.
- **RIGHT:** Subscribe to `MediaQueryList.addEventListener('change', ...)` and render an intentional, high-craft static keyframe when reduced motion is active.
- **WRONG:** Sniffing `navigator.userAgent` to guess WebGL or mobile GPU support.
- **RIGHT:** Probe context creation, shader compilation, and hardware renderer strings at runtime.

## 6. Production Considerations
- Verify in Playwright/DevTools with `emulateMedia({ reducedMotion: 'reduce' })` and forced WebGL failure that the page still looks complete and all overlaid CTAs remain 100% operable.
