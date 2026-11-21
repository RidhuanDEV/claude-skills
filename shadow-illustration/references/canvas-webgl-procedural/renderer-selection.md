# Renderer Selection & 6-Phase Rendering Lifecycle

## 1. Core Concepts
Selecting a web graphics technology is a trade-off between **DOM accessibility (SVG)**, **immediate-mode 2D drawing simplicity (Canvas 2D)**, **GPU pixel/instance throughput (WebGL2/WebGPU)**, and **composite layering (Hybrid)**. Performance boundaries are heuristics driven by fill-rate, screen area, shader ALU cost, and browser compositing — never hard magic numbers.

## 2. Technical Rules
- **Profiling-First Selection:** Start with SVG for crisp editable vectors and DOM-accessible diagrams; choose Canvas 2D for dynamic procedural 2D drawings where DOM node churn would trigger layout recalculation; choose WebGL2/Shaders for full-screen pixel fields, 3D transforms, or GPU-instanced geometry; choose Hybrid (Canvas/WebGL backdrop + HTML/SVG overlay) when pairing atmospheric motion with accessible text/CTAs.
- **Strict 6-Phase Lifecycle Separation:** Every renderer MUST isolate `1. Initialize -> 2. Resize -> 3. Update(dt) -> 4. Render -> 5. Visibility -> 6. Dispose` inside a framework-agnostic TypeScript module.
- **Logical Coordinate Independence:** Run simulation math in normalized `[0..1]` or CSS-logical `[0..width]` space so window resizes or DPR changes (`1x` vs `2x`) never alter visual speed or proportions.

## 3. Implementation Examples
```ts
export interface RendererController {
  resize(cssWidth: number, cssHeight: number, dpr: number): void
  update(dtSeconds: number): void
  render(): void
  setVisibility(visible: boolean): void
  dispose(): void
}

export function computeEffectiveDpr(maxDpr = 2): number {
  const raw = typeof window !== 'undefined' ? window.devicePixelRatio || 1 : 1
  return Math.min(Math.max(raw, 1), maxDpr)
}
```

## 4. Best Practices
- Cache slow-changing background layers (gradients, static grids) onto an offscreen canvas and redraw only active foreground layers at 60fps.
- Keep React/Vue/Svelte components as thin wrappers that only bind `<canvas ref>`, `ResizeObserver`, theme token updates, and unmount disposal.

## 5. Anti-patterns (WRONG vs RIGHT)
- **WRONG:** Treating "300 SVG nodes" or "500 particles" as absolute hard limits without measuring device frame time, or mounting WebGL for a simple 3-color gradient that CSS/Canvas 2D renders at 0KB overhead.
- **RIGHT:** Treat element counts as initial starting heuristics and verify `p95 < 16.6ms` in Chrome DevTools Performance with `4x CPU slowdown`.
- **WRONG:** Mixing state mutation (`x += vx`) directly inside the `render()` draw function.
- **RIGHT:** Advance state strictly in `update(dt)` and keep `render()` a pure idempotent projection of current state.

## 6. Production Considerations
- Always provide a static render path (`renderAt(fixedTime)`) for `prefers-reduced-motion: reduce`, low-tier mobile fallback, and deterministic visual regression testing.
- Verify `dispose()` removes all observers/listeners and zeroes temporary canvas dimensions (`width = 0; height = 0`) so mobile Safari reclaims backing memory immediately.
