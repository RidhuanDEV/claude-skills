export function createMulberry32(seed: number): () => number {
  let state = seed >>> 0
  return (): number => {
    state = (state + 0x6d2b79f5) >>> 0
    let t = Math.imul(state ^ (state >>> 15), 1 | state)
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296
  }
}

function hash2D(ix: number, iy: number, seed: number): number {
  let h = Math.imul(ix, 374761393) + Math.imul(iy, 668265263) + Math.imul(seed, 1442695041)
  h = (h ^ (h >>> 13)) >>> 0
  h = Math.imul(h, 1274126177) >>> 0
  return ((h ^ (h >>> 16)) >>> 0) / 4294967296
}

function smoothstep(t: number): number {
  return t * t * (3 - 2 * t)
}

export function valueNoise2D(x: number, y: number, seed = 42): number {
  const ix = Math.floor(x)
  const iy = Math.floor(y)
  const fx = smoothstep(x - ix)
  const fy = smoothstep(y - iy)

  const v00 = hash2D(ix, iy, seed)
  const v10 = hash2D(ix + 1, iy, seed)
  const v01 = hash2D(ix, iy + 1, seed)
  const v11 = hash2D(ix + 1, iy + 1, seed)

  const nx0 = v00 + (v10 - v00) * fx
  const nx1 = v01 + (v11 - v01) * fx
  return nx0 + (nx1 - nx0) * fy
}

export function fbm2D(x: number, y: number, octaves = 3, seed = 42): number {
  let value = 0
  let amplitude = 0.5
  let frequency = 1
  let norm = 0
  const safeOctaves = Math.min(Math.max(octaves, 1), 5)
  for (let i = 0; i < safeOctaves; i++) {
    value += amplitude * valueNoise2D(x * frequency, y * frequency, seed + i * 97)
    norm += amplitude
    amplitude *= 0.5
    frequency *= 2.0
  }
  return norm > 0 ? value / norm : 0
}

export function sampleCurlFlow2D(
  x: number,
  y: number,
  seed = 42,
): { readonly vx: number; readonly vy: number } {
  const eps = 0.01
  const dndy = (fbm2D(x, y + eps, 3, seed) - fbm2D(x, y - eps, 3, seed)) / (2 * eps)
  const dndx = (fbm2D(x + eps, y, 3, seed) - fbm2D(x - eps, y, 3, seed)) / (2 * eps)
  return { vx: dndy, vy: -dndx }
}
