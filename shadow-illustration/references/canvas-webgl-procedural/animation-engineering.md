# Animation Engineering: Frame-Rate Independence, Physics & Timelines

## 1. Core Concepts
Production animation decouples motion velocity from display refresh rate (`60Hz`, `90Hz`, `120Hz ProMotion`, `144Hz`) using **clamped delta time (`dt`)**, **exponential damping**, **mathematically consistent fixed-timestep accumulators**, **spring physics with sleep thresholds**, and **purpose-matched easing curves**.

## 2. Technical Rules
- **Visibility Resume Reset:** When `document.visibilityState` returns to `'visible'` or an element re-enters `IntersectionObserver`, reset `lastTime = performance.now()` before ticking so backgrounded durations never enter `dt`.
- **Delta-Time Clamping & Consistent Fixed Timestep:**
  - Clamp variable `dt = Math.min(Math.max((now - lastTime) / 1000, 0), 0.05)` (`50ms` ceiling).
  - Keep fixed-timestep physics mathematically aligned: at `FIXED_DT = 1 / 120` (~8.33ms), a `50ms` cap requires **`MAX_SUB_STEPS = 6`** (`6 * 8.33ms = 50ms`), or cap `MAX_FRAME_DT = 1 / 30` (~33.3ms) with `MAX_SUB_STEPS = 4`. If a stall exceeds `MAX_SUB_STEPS`, explicitly discard remaining `accumulator = 0` (documenting intentional slow-motion time dilation) to prevent spiral-of-death backlog.
- **Easing & Spring Selection:**
  - Use **Linear (`t`)** for constant-velocity ambient motion (continuous orbital drift, seamless noise panning) and **direct 1:1 scroll-linked scrubbing**.
  - Use **Ease-Out (`1 - (1 - t)^3`)** for entrances, **Ease-In-Out** for state transitions, and **critically damped springs** (`damping = 2 * Math.sqrt(stiffness * mass)`) for interactive pointer tracking.

## 3. Implementation Examples
```ts
// Frame-rate independent exponential damping + consistent 120Hz fixed-timestep accumulator
export function damp(current: number, target: number, lambda: number, dt: number): number {
  return current + (target - current) * (1 - Math.exp(-lambda * dt))
}

export function stepFixedPhysics(
  accumulator: number,
  rawDtSeconds: number,
  stepFn: (fixedDt: number) => void,
): { readonly remainingAccumulator: number; readonly alpha: number } {
  const FIXED_DT = 1 / 120
  const MAX_SUB_STEPS = 6 // Matches 0.05s (50ms) max frame delta at 120Hz
  const clampedDt = Math.min(Math.max(rawDtSeconds, 0), FIXED_DT * MAX_SUB_STEPS)
  let acc = accumulator + clampedDt
  let steps = 0
  while (acc >= FIXED_DT && steps < MAX_SUB_STEPS) {
    stepFn(FIXED_DT)
    acc -= FIXED_DT
    steps += 1
  }
  if (acc >= FIXED_DT) acc = 0 // Discard excess backlog on severe stall (spiral-of-death guard)
  return { remainingAccumulator: acc, alpha: acc / FIXED_DT }
}
```

## 4. Best Practices
- Put springs to sleep (`value = target; velocity = 0` and pause `rAF` if scene is otherwise static) once `Math.abs(target - value) < 1e-3 && Math.abs(velocity) < 1e-3`.
- Shape particle alpha with smooth lifecycle envelopes (`smoothstep(0, 0.15, age) * (1 - smoothstep(0.75, 1, age))`) so particles never pop abruptly.

## 5. Anti-patterns (WRONG vs RIGHT)
- **WRONG:** `x += (target - x) * 0.1` inside `requestAnimationFrame` (runs 2x faster at 120Hz than 60Hz).
- **RIGHT:** `x = damp(x, target, 8, dt)` using `1 - Math.exp(-lambda * dt)`.
- **WRONG:** Setting `MAX_FRAME_DT = 0.05`, `FIXED_DT = 1/120`, and `MAX_SUB_STEPS = 4` without clearing residue (leaves 2 sub-steps of unconsumed accumulator backlog every slow frame).
- **RIGHT:** Match `MAX_SUB_STEPS = 6` to `0.05s` (or `4` to `0.0333s`) and zero remaining backlog on stall.

## 6. Production Considerations
- When `prefers-reduced-motion: reduce` is active, bypass the `rAF` loop completely and render a single curated keyframe (`t = heroStillTime`).
