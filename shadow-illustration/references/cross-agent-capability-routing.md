# Capability discovery and format selection

Inspect the actual host tools, file access, project scripts, lockfiles, and installed commands. Record the authorized operation, capability evidence, versions when available, output path, and checks the host can perform. Capabilities can coexist.

| Available capability | Feasible work | Evidence to report |
|---|---|---|
| Image generation or editing | Raster concepts, variations, controlled edits and supported alpha outputs | Tool invocation and saved artifact. Verify transparency and identity visually. |
| Code and files | Authored SVG, procedural geometry and deterministic exports | Source, command and rendered artifact if a renderer is present. |
| Compatible exporter and player | Timeline, frame sequence or interactive rig | Actual export, player version and playback observations for the requested features. |
| Text only | Brief, model sheet specification, storyboard, style guide or handoff | Written deliverable. Mark visual and runtime verification as NOT_RUN. |

Decide in this order. Honor an explicit format. Then identify the surface and size, editability, visual complexity, static or interactive behavior, the existing pipeline, and the target renderer. Choose a format for each role if master and runtime needs differ.

| Need | Starting choice | Verify |
|---|---|---|
| Flat, line or isometric illustration with editable forms | Layered SVG | Renderer subset, live strokes, scaling and crop |
| Painterly texture, photo-like detail or complex lighting | PNG/WebP, or JPEG for opaque artwork where suitable | Color profile, compression artifacts and storage/decode budget |
| Layered raster handoff | Editor native source or OpenRaster when both editors support it | Round trip for layers, alpha, masks and blend modes |
| Small vector interaction | CSS/SVG using supported properties | Fallback, transform origin and target browser/component renderer |
| Timeline animation | Existing Lottie JSON or dotLottie pipeline | Platform-specific feature compatibility and playback |
| Input-driven interaction | Existing compatible Rive workflow | Export/editor access, state machine and runtime inputs |
| Pixel art or frame-based delivery | Spritesheet or GIF as requested | Frame metadata, timing, scaling, transparency and fallback |
| High-frequency procedural motion, particle backdrop, or 3D scene | HTML5 `<canvas>` 2D / WebGL / Three.js + static fallback | DPR scaling (`<=2`), `prefers-reduced-motion` static frame, unmount cleanup |
| Dynamic social OG cards, certificates, responsive WebP/AVIF, or PWA icon sets | Programmatic pipeline (`Sharp`, `Pillow`, `Satori`/`resvg`) | Pixel dimensions, byte budget, explicit fonts, maskable 80% safe zone |
| UI icon system or custom technical/isometric diagram | `24×24` SVG (`currentColor`) / semantic SVG diagram | Optical balance, dark/light contrast, RTL directional mirroring, Okabe-Ito safety |
| Print banners, posters, or physical packaging | CMYK ICC / Vector PDF/X-4 at 300 DPI | Bleed (`3–5 mm`), inner safe margin, outlined/embedded fonts |

Match style to intent. For flat art, protect silhouette and value grouping. For isometric art, keep axes and depth consistent. Keep line art legible at its minimum size. For textured art, retain raster detail rather than forcing path geometry. For pixel art, preserve the pixel grid and check integer scaling when applicable.

Use the available compatible project route. Missing image generation may justify a brief or a simple SVG if that matches intent. Missing rendering leaves visual review open. Missing an editor/exporter leaves the relevant native export undelivered. Ask about a material change of format or cost when the evidence cannot resolve it. Never treat a missing tool as permission to install it or send an asset to another service.

For a cross-agent handoff, include accessible file paths or approved transfer references, hashes for existing files, the master and allowed variations, brief or prompt, assigned output and tool requirements, target format, and verification still pending. Confirm the next agent can access the referenced material.
