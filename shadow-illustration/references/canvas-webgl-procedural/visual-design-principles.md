# Visual Design Principles for Modern Web Graphics (Anti-Slop Craft)

## 1. Core Concepts
Production web graphics exist to **reinforce brand character, guide reading hierarchy, and create quiet spatial depth** — never to overpower typography, primary CTAs, or user comprehension. Restraint, negative space, and theme-token harmony separate editorial-grade product visuals from noisy tech demos.

## 2. Technical Rules
- **Reading-Zone Negative Space:** Map where the `H1`, subheadline, and primary CTA sit first. Attenuate visual contrast, line density, and motion velocity directly behind copy (`<= 12%` luminance delta in reading zones) and place the visual focal point in the complementary counterbalance region (e.g., right 45% on a left-aligned hero).
- **Three-Layer Depth Hierarchy:** Structure scenes into **1. Background Atmosphere** (`0–12%` contrast, slow tonal field), **2. Midground Motif** (`12–30%` contrast, coherent brand geometry/contours), and **3. Sparse Foreground Accent** (deliberate focal anchors or gentle pointer response — never uniform clutter across 100% of the viewport).
- **Strict Theme-Token Binding:** Read palette values from the application's CSS custom properties (`--bg`, `--surface`, `--primary`, `--border`, `--ink`) via `getComputedStyle(document.documentElement)`.

## 3. Implementation Examples
```ts
// Reading-zone attenuation mask + live CSS theme token extraction
export function readingZoneAttenuation(normX: number, normY: number, textCenterX = 0.28, textCenterY = 0.45): number {
  const dx = (normX - textCenterX) * 1.35
  const dy = normY - textCenterY
  const dist = Math.min(Math.sqrt(dx * dx + dy * dy), 1)
  // Smoothstep [0.18 .. 0.65]: calm behind headline/CTA, full strength in counterbalance zone
  const t = Math.min(Math.max((dist - 0.18) / (0.65 - 0.18), 0), 1)
  return 0.15 + 0.85 * (t * t * (3 - 2 * t))
}

export function readCssToken(tokenName: string, fallback: string): string {
  if (typeof window === 'undefined') return fallback
  const val = getComputedStyle(document.documentElement).getPropertyValue(tokenName).trim()
  return val || fallback
}
```

## 4. Best Practices
- Interpolate color gradients in perceptual **OKLCH** or linear RGB space to avoid muddy grey midtones.
- In **Light Mode**, use mineral/ink tones, crisp `0.75–1.25px` hairline strokes, and `'multiply'` shading; in **Dark Mode**, use deep tinted charcoal/navy surfaces and low-opacity (`0.08–0.22`) `'screen'` rim lighting.
- Keep ambient cycle periods calm (`8–20 seconds` per cycle) so motion feels breathable rather than frantic.

## 5. Anti-patterns (WRONG vs RIGHT)
- **WRONG:** Dropping a default neon purple/cyan/magenta particle swarm across the entire screen behind white headline text without checking contrast or brand identity.
- **RIGHT:** Derive palette from the project's semantic design tokens and attenuate visual density behind text so copy maintains `>= 4.5:1` WCAG AA contrast at all times.
- **WRONG:** Animating every layer at high speed simultaneously (destroys focal hierarchy).
- **RIGHT:** Keep 50%+ negative space calm and move only one primary motif layer with purposeful rhythm.

## 6. Production Considerations
- Always inspect the visual frozen at `t = heroStillTime`: if the static frame does not look like a well-composed illustration on its own, refine the composition before shipping motion.
