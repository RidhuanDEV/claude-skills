# Canvas 2D Engineering Techniques

## 1. Core Concepts
HTML5 Canvas 2D is an immediate-mode state machine where performance and visual crispness depend on geometry caching (`Path2D`), transform matrix discipline (`setTransform`), offscreen sprite stamping, and mathematical hit testing.

## 2. Technical Rules
- **Reusable Vector Geometry:** Pre-compile complex paths into `new Path2D(svgPathD)` during `init()`/`resize()` instead of re-emitting path commands every frame.
- **Smooth Organic Curves:** Construct C1-continuous splines using midpoint quadratic Bézier interpolation (`quadraticCurveTo(ctrlX, ctrlY, midX, midY)`), closing loops at the initial midpoint to prevent visible seams.
- **Transform & State Isolation:** Reset the matrix at the start of every frame via `ctx.setTransform(dpr, 0, 0, dpr, 0, 0)` and wrap localized `clip()` or `globalCompositeOperation` changes inside `ctx.save()` / `ctx.restore()`.
- **Hit Testing Hierarchy:** Use CSS-space math bounds (circle/AABB/polygon) first; use `ctx.isPointInPath(path2d, localX * dpr, localY * dpr)` for irregular curves; use a tiny offscreen flat-RGB color-picking canvas only for complex overlapping layers.

## 3. Implementation Examples
```ts
export function strokeSmoothClosedLoop(ctx: CanvasRenderingContext2D, pts: ReadonlyArray<{ readonly x: number; readonly y: number }>): void {
  if (pts.length < 3) return
  const first = pts[0]
  const second = pts[1]
  if (!first || !second) return
  const startMidX = (first.x + second.x) * 0.5
  const startMidY = (first.y + second.y) * 0.5
  ctx.beginPath()
  ctx.moveTo(startMidX, startMidY)
  for (let i = 1; i < pts.length; i++) {
    const curr = pts[i]
    const next = pts[(i + 1) % pts.length]
    if (!curr || !next) continue
    ctx.quadraticCurveTo(curr.x, curr.y, (curr.x + next.x) * 0.5, (curr.y + next.y) * 0.5)
  }
  ctx.closePath()
  ctx.stroke()
}
```

## 4. Best Practices
- Batch primitives sharing the same `fillStyle`/`strokeStyle` into a single `beginPath() ... fill()` call to minimize state flushes.
- Pre-render soft radial glows once onto an offscreen sprite canvas and stamp them with `ctx.drawImage(sprite, x - r, y - r)`.
- Pass `{ willReadFrequently: true }` only on offscreen staging canvases that perform repeated `getImageData` pixel manipulation.

## 5. Anti-patterns (WRONG vs RIGHT)
- **WRONG:** Calling `ctx.createRadialGradient(...)` or setting `ctx.shadowBlur = 32` inside a 60fps particle loop (triggers massive CPU software blur overhead).
- **RIGHT:** Allocate gradients in `resize()`/`setPalette()` and stamp pre-blurred offscreen sprites via `drawImage`.
- **WRONG:** Chaining `ctx.scale(dpr, dpr)` inside `render()` without resetting the transform matrix (accumulates exponential scale each frame).
- **RIGHT:** Use `ctx.setTransform(dpr, 0, 0, dpr, 0, 0)` at the start of every frame.

## 6. Production Considerations
- Re-cache gradients and offscreen layers whenever theme tokens (`light`/`dark`) or container dimensions change.
- Test blend modes (`'multiply'` on light surfaces, `'screen'` on dark surfaces) across Chromium, Firefox, and Safari to confirm consistent alpha premultiplication.
