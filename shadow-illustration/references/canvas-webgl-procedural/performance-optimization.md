# Performance Engineering, Responsive Budgets & GPU Profiling

## 1. Core Concepts
Sustaining `60fps` (`< 16.6ms`/frame) or `120fps` (`< 8.3ms`/frame) without draining laptop/mobile batteries requires **zero-allocation hot loops**, **Structure-of-Arrays (SoA) object pooling**, **draw-call batching/instancing**, **adaptive DPR scaling**, and **empirical DevTools/GPU profiling**.

## 2. Technical Rules
- **Zero Heap Allocation in `update()` / `render()`:** Never instantiate objects, closures, or arrays (`.map()`, `.filter()`) inside the frame loop. Pre-allocate `Float32Array` buffers or fixed-capacity object pools using `O(1)` swap-with-last removal.
- **Draw-Call & State Reduction:** In Canvas 2D, group identical fill/stroke styles into one `beginPath() ... fill()` pass and stamp pre-rendered offscreen sprites via `drawImage`. In WebGL2, sort draws by program/texture and collapse repeated geometry into `gl.drawArraysInstanced`.
- **Viewport Culling & Adaptive DPR:** Skip updating/drawing elements outside `[-margin, width + margin]`. Cap DPR (`<= 2` on desktop/Canvas 2D, `<= 1.5` for heavy full-screen mobile fragment shaders) and step down DPR by `0.25` if rolling average frame time exceeds `22ms` over 60 consecutive frames.

## 3. Implementation Examples
```ts
// Zero-allocation Structure-of-Arrays (SoA) pool with O(1) swap-with-last despawn
export class FloatParticlePool {
  readonly x: Float32Array
  readonly y: Float32Array
  readonly vx: Float32Array
  readonly vy: Float32Array
  readonly life: Float32Array
  activeCount = 0

  constructor(readonly capacity: number) {
    this.x = new Float32Array(capacity)
    this.y = new Float32Array(capacity)
    this.vx = new Float32Array(capacity)
    this.vy = new Float32Array(capacity)
    this.life = new Float32Array(capacity)
  }

  kill(index: number): void {
    const last = this.activeCount - 1
    if (index < 0 || index > last) return
    if (index !== last) {
      this.x[index] = this.x[last] ?? 0
      this.y[index] = this.y[last] ?? 0
      this.vx[index] = this.vx[last] ?? 0
      this.vy[index] = this.vy[last] ?? 0
      this.life[index] = this.life[last] ?? 0
    }
    this.activeCount = last
  }
}
```

## 4. Best Practices
- Listen to `matchMedia(\`(resolution: ${window.devicePixelRatio}dppx)\`)` so moving a browser window between a 1x external monitor and a 2x Retina display triggers a clean backing-store resize.
- Pause the `requestAnimationFrame` loop immediately via `IntersectionObserver` when scrolled off-screen.

## 5. Anti-patterns (WRONG vs RIGHT)
- **WRONG:** `particles = particles.filter(p => p.life > 0)` every frame (allocates a new array and triggers sawtooth GC frame drops).
- **RIGHT:** Use a pre-allocated TypedArray pool and swap dead slots with `activeCount - 1` in `O(1)`.
- **WRONG:** Rendering a full-screen multi-octave fragment shader at `dpr = 3` on a mobile phone (9x pixel fill-rate cost for imperceptible sharpness on soft gradients).
- **RIGHT:** Cap shader resolution at `dpr <= 1.5` on coarse-pointer mobile devices and let hardware bilinear filtering scale smoothly.

## 6. Production Considerations
- Profile with Chrome DevTools Performance (`4x CPU slowdown`), Rendering (*Frame Rendering Stats* / *Paint Flashing*), Memory Heap Snapshots (mount/unmount 5x), and Spector.js for WebGL draw-call audits.
