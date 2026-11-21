# Testing, Profiling & Validation for Canvas, WebGL & Procedural Visuals

## 1. Core Concepts
Because canvas and WebGL output opaque pixels, code compilation alone never proves correctness. Production verification requires **deterministic seeded rendering hooks (`renderAt`)**, **simulated WebGL context loss/restore tests**, **cross-browser visual snapshots**, **rolling frame-time telemetry**, and **mount/unmount memory leak assertions**.

## 2. Technical Rules
- **Deterministic QA Hook:** Every renderer MUST expose `renderAt(timeSeconds: number)` and accept a fixed `seed` so automated tests can render an exact reproducible frame without `requestAnimationFrame` timing jitter.
- **Numerical Sanity Assertions:** Assert zero `NaN` or `Infinity` values across particle buffers, matrix transforms, and uniform arrays under edge inputs (`width = 0`, `1×1`, `375×812`, `3840×2160`, `dt = 0`, `dt = 12s`).
- **Context-Loss Drill:** Exercise `WEBGL_lose_context.loseContext()` followed by `restoreContext()` and assert zero uncaught errors plus successful program/VAO reconstruction.
- **Leak & Frame-Budget Gates:** Verify `p95` frame time `< 16.6ms` (desktop 60Hz) and confirm zero retained context/listener growth across 10 sequential mount/unmount cycles.

## 3. Implementation Examples
```ts
// Deterministic frame-time p95 sampler + context-loss test helper
export function measureFrameTimeP95(samplesMs: ReadonlyArray<number>): { readonly p50: number; readonly p95: number } {
  if (samplesMs.length === 0) return { p50: 0, p95: 0 }
  const sorted = [...samplesMs].sort((a, b) => a - b)
  const p50 = sorted[Math.floor(sorted.length * 0.5)] ?? 0
  const p95 = sorted[Math.floor(sorted.length * 0.95)] ?? 0
  return { p50, p95 }
}

export function triggerWebGlContextLossDrill(gl: WebGL2RenderingContext, delayMs = 150): boolean {
  const ext = gl.getExtension('WEBGL_lose_context')
  if (!ext) return false
  ext.loseContext()
  setTimeout(() => ext.restoreContext(), delayMs)
  return true
}
```

## 4. Best Practices
- Wait for `document.fonts.ready` and lock `?fixedTime=2.0&seed=42` before capturing Playwright visual regression screenshots.
- Test across **Chromium**, **Firefox**, and **WebKit/Safari** across `375×812` (mobile), `768×1024` (tablet), and `1440×900` (desktop) in both light and dark modes.

## 5. Anti-patterns (WRONG vs RIGHT)
- **WRONG:** Taking Playwright screenshots of an unseeded, live-running `requestAnimationFrame` canvas (produces 100% flaky pixel diffs on every CI run).
- **RIGHT:** Freeze time and seed via `renderAt(2.0)` or `prefers-reduced-motion: reduce` for deterministic pixel comparisons.
- **WRONG:** Claiming a WebGL component is "verified" based solely on `tsc --noEmit` without checking rendered frames or context disposal.
- **RIGHT:** Report `typecheck`, `shader compile`, `visual frame check`, `context-loss recovery`, and `FPS/memory profile` separately, marking any unrun check as `Not measured`.

## 6. Production Considerations
- Monitor active WebGL context count during SPA navigation tests: leaking > 8–16 contexts causes browsers to silently evict the oldest live canvas on the page.
