# Offline Procedural Pixel-Art VFX & Sprite-Sheet Engineering

Use this playbook when authoring, recoloring, validating, or exporting code-driven pixel-art VFX animations and Aseprite-compatible sprite sheets for 2D/WebGL/Godot/Unity/Phaser games **100% offline with zero third-party npm packages, zero remote CLI installers, and zero network servers**.

---

## 1. Security & Offline-First Non-Negotiables

1. **Zero Runtime Dependencies:** Core rendering, PNG encoding (`node:zlib`), contact sheets, and Aseprite JSON atlases run strictly on Node.js built-ins (`>=18`). Never add `esbuild` or arbitrary install-script packages just to render sprites.
2. **Zero External Publishing / Pipe-to-Shell:** Never suggest or execute `curl ... | sh`, `irm ... | iex`, or third-party game publishing CLIs (`patch.gg` / `pch`).
3. **Zero Wildcard Preview Servers:** Inspect rendered `contact.png` and sprite-sheet PNGs locally; if a local preview server is ever authorized, bind strictly to `127.0.0.1`.
4. **Deterministic Seeds Only:** Never call `Math.random()` inside effects. Every effect uses a seeded PRNG (`mulberry32`) so identical inputs produce bit-for-bit identical PNGs and JSON atlases.

---

## 2. Two-Buffer Pixel-Art Architecture

Each effect writes into two aligned low-resolution pixel buffers (`W x H`, typically `32x32` to `96x96`):

1. **`color` buffer (`Uint8ClampedArray`, RGBA):** Hard palette-ramped pixel silhouettes. Opacity fade uses a **4×4 Bayer ordered dithering threshold** instead of blurry vector gradients so 1x pixel silhouettes remain crisp when scaled with nearest-neighbor (`image-rendering: pixelated`).
2. **`light` buffer (`Float32Array`, RGB additive glow):** Soft radial energy around hot cores, sparks, and arcs. During compositing:
   - Over opaque backdrops: `out = min(255, bg_blend + light * glowStrength)`
   - Over transparent sprite sheets: light energy converts into premultiplied-safe translucent color so additive warmth survives export cleanly.

### Palette Ramps (Dark Shadow → Midtone → Bright Core → White Hero Flash)
Use 5-step curated ramps (darkest edge to hottest white core) so any effect can be recolored via `--palette` without rewriting geometry:
- `fire`, `ice`, `arcane`, `poison`, `holy`, `cyber`, `shadow`

---

## 3. Timing, Hit-Stop (`act`) & Aseprite Atlas Contract

An impact effect floating on a static sprite looks pasted on. Combat/action effects declare an **`act`** timing block exported into `meta.pixelfx.act`:

- `windup`: seconds the character prepares before `t = 0`
- `hits`: ordered array of `{ t, freeze }` impact timestamps and hit-stop freeze durations (`0.05–0.18s`)
- `recovery`: follow-through duration after the peak frame

Exported sprite sheets (`--sheet`) produce:
- `<name>.png`: transparent horizontal/grid sprite sheet (nearest-neighbor crisp pixels)
- `<name>.json`: Aseprite-compatible `frames` map + `meta.pixelfx` (`fps`, `loop`, `frameSize`, `columns`, `pivot`, `palette`, `seed`, `act`)

---

## 4. Pixel-Art VFX Redline Diagnostics

| Visual Symptom | Engineering Fix |
| --- | --- |
| Reads as mush at 1x | Reduce palette to `<= 5` ramp steps, enlarge primary silhouette, establish one focal core |
| Floaty impact, no punch | Use fast-in/slow-out easing (`1 - (1 - t)^4`), insert a 1–2 frame pure white hero flash at contact, shorten total duration |
| Mechanical/uniform particles | Vary particle angle, speed, lifetime, and spawn delay from the seeded PRNG; layer secondary sparks or embers |
| Washed-out glow | Lower additive `light` multiplier (`0.25–0.5`), darken outer rim step, reserve `#FFFFFF` strictly for the hottest core |
| Seam on loop wrap | Drive motion strictly with periodic functions (`sin(phase * 2π * n)`, `cos(...)`) and wrapped particle lifetimes `(t + offset) % 1` |
| One-shot pops off abruptly | Shrink radius, dither alpha out via 4×4 Bayer matrix, and verify the final frame ends empty (`0` opaque pixels) |

---

## 5. Offline CLI Toolkit (`pixelfx_engine.mjs`)

```powershell
# List built-in clean-room procedural effects and palettes
node shadow-illustration/scripts/pixelfx_engine.mjs list

# Render contact sheet + transparent sprite sheet + Aseprite JSON + interactive offline HTML animation player (0 deps)
node shadow-illustration/scripts/pixelfx_engine.mjs render fire/torch --sheet --preview --out tmp/vfx
node shadow-illustration/scripts/pixelfx_engine.mjs render ice/frost-nova --palette arcane --seed 7 --sheet --preview --out tmp/vfx

# Run deterministic quality checks (determinism, bounds, one-shot empty end, loop continuity, act order)
node shadow-illustration/scripts/pixelfx_engine.mjs check
```

---

## 6. Source Attribution & Provenance

Procedural two-buffer pixel-art VFX workflow, Bayer dithering compositing, `act` hit-stop metadata, and Aseprite-compatible sprite-sheet export pattern adapted in clean room from `patch-gg/pixelfx` (pinned commit `5294518ce7c72e48b6100a744596e0acf57f2826`, `tar_sha256: ca4ed4715d7befef3fe9fc3f4f443732cd52ee498403515ec881e543f1bd1c63`, licensed **MIT**). All Patch publishing instructions (`curl | sh` / `irm | iex`), `esbuild` dev dependencies, and wildcard HTTP preview servers were intentionally excluded.
