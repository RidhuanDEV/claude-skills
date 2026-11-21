# Procedural & Generative Graphics Engineering

## 1. Core Concepts
Procedural graphics translate deterministic mathematical functions — **seeded PRNGs**, **coherent gradient/simplex noise**, **fractal Brownian motion (fBm)**, **curl fields**, and **blue-noise spatial distributions** — into organic, infinitely scalable visual systems that stay reproducible across reloads and devices.

## 2. Technical Rules
- **Deterministic Seeded PRNG:** Never use raw `Math.random()` in generative visuals. Use a seeded 32-bit generator (e.g., Mulberry32) with separate PRNG instances for layout, palette, and motion so tuning animation speed never scrambles spatial layout.
- **Noise & Octave Budgets:** Use 2D/3D Value, Perlin, or Simplex noise for continuous fields; cap fBm at `3–5 octaves` (`gain = 0.5`, `lacunarity = 2.0`) for real-time web loops; use **Curl Noise** (`vx = dN/dy`, `vy = -dN/dx`) for divergence-free particle ribbons that never clump into sinks.
- **Anti-Clumping Spatial Distributions:** Use **Poisson-Disc Sampling**, **Stratified Jittered Grids** (`grid + ±0.25 * cell`), or **Phyllotaxis Golden Angle (`137.507764°`)** instead of uniform random placement.

## 3. Implementation Examples
```ts
// Deterministic Mulberry32 PRNG + 2D Curl Velocity Approximation
export function createMulberry32(seed: number): () => number {
  let state = seed >>> 0
  return (): number => {
    state = (state + 0x6d2b79f5) >>> 0
    let t = Math.imul(state ^ (state >>> 15), 1 | state)
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296
  }
}

export function computeCurl2D(
  noise2D: (x: number, y: number) => number,
  x: number,
  y: number,
  eps = 0.001,
): { readonly vx: number; readonly vy: number } {
  const dndy = (noise2D(x, y + eps) - noise2D(x, y - eps)) / (2 * eps)
  const dndx = (noise2D(x + eps, y) - noise2D(x - eps, y)) / (2 * eps)
  return { vx: dndy, vy: -dndx }
}
```

## 4. Best Practices
- Attenuate procedural density using a radial or directional falloff mask (`smoothstep`) so regions behind UI headlines and buttons remain calm.
- Use Marching Squares on a coarse 2D noise grid for crisp, resolution-independent topographic contour lines.

## 5. Anti-patterns (WRONG vs RIGHT)
- **WRONG:** Using `Math.random()` inside `render()` or placing points with raw uniform `[Math.random() * w, Math.random() * h]` (produces flickering or ugly overlapping clusters and empty voids).
- **RIGHT:** Generate layout coordinates once per seed using stratified jittered grids or Poisson-disc sampling.
- **WRONG:** Evaluating 8+ octave 3D Simplex noise per pixel at 3x mobile DPR (overheats mobile GPUs).
- **RIGHT:** Use 3–4 octaves, domain-warp at lower resolution, or bake static noise octaves into a Seamless Tile Texture.

## 6. Production Considerations
- Expose `seed` as a component prop/config so designers can curate and lock an exact approved visual composition in production and visual regression tests.
