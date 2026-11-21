# Canvas, WebGL, Shaders & Procedural Visuals — Hub & Reference Guide

Use this decision hub when designing, building, optimizing, or auditing code-driven web graphics (interactive heroes, ambient backdrops, procedural illustrations, particle systems, custom 2D/3D visualizations).

## 1. End-to-End Build Workflow (Visual Quality First, Never Over-Engineer)

1. **Art Direction & Composition First:** Define reading-zone negative space, focal hierarchy, theme tokens, and motion restraint before writing draw code (`visual-design-principles.md`).
2. **Select the Simplest Renderer:** Choose SVG, Canvas 2D, WebGL2, or Hybrid based on profiling heuristics — not hype (`renderer-selection.md`).
3. **Separate the 6-Phase Lifecycle:** Keep `Initialize -> Resize -> Update(dt) -> Render -> Visibility -> Dispose` inside a framework-agnostic TypeScript module so React/Vue wrappers stay thin and leak-free.
4. **Engineer Resilience & Performance:** Apply zero-allocation loops, DPR budgets, `webglcontextlost`/`webglcontextrestored` GPU rebuilds, `prefers-reduced-motion` static keyframes, and graceful fallbacks.
5. **Verify Empirically:** Run deterministic seeded tests, cross-browser checks (Chrome/Firefox/Safari), context-loss recovery, and DevTools FPS/memory profiling (`testing-and-validation.md`).

## 2. Reference Guide (Load Only What the Task Needs)

Load the relevant reference documents when implementing or modifying visual rendering systems:

| Task | Reference |
| :--- | :--- |
| Choosing a rendering technology & 6-phase lifecycle | [renderer-selection.md](canvas-webgl-procedural/renderer-selection.md) |
| Canvas 2D drawing, Bézier curves, compositing & hit testing | [canvas-2d-techniques.md](canvas-webgl-procedural/canvas-2d-techniques.md) |
| Custom GLSL shaders, VAOs, instancing, FBOs & context recovery | [webgl-shaders.md](canvas-webgl-procedural/webgl-shaders.md) |
| Procedural noise, Poisson distributions & generative patterns | [procedural-generation.md](canvas-webgl-procedural/procedural-generation.md) |
| Delta-time math, fixed timestep, springs, easing & timelines | [animation-engineering.md](canvas-webgl-procedural/animation-engineering.md) |
| Pointer events, touch safety, gestures & interaction states | [interaction-patterns.md](canvas-webgl-procedural/interaction-patterns.md) |
| Draw-call batching, object pooling, adaptive DPR & GPU profiling | [performance-optimization.md](canvas-webgl-procedural/performance-optimization.md) |
| Composition, focal hierarchy, color harmony & anti-slop restraint | [visual-design-principles.md](canvas-webgl-procedural/visual-design-principles.md) |
| Feature detection, graceful fallback & WCAG reduced motion | [accessibility-and-fallback.md](canvas-webgl-procedural/accessibility-and-fallback.md) |
| Deterministic tests, visual regression, FPS & memory leak checks | [testing-and-validation.md](canvas-webgl-procedural/testing-and-validation.md) |

> Do not load unrelated references unnecessarily. Use multiple references when a task spans multiple domains (e.g., an interactive WebGL hero loads `renderer-selection.md`, `webgl-shaders.md`, `visual-design-principles.md`, and `accessibility-and-fallback.md`).

## 3. Strict-TS Implementation Examples

- **Canvas 2D Layered 6-Phase Renderer:** [layered-renderer.ts](canvas-webgl-procedural/examples/canvas-2d/layered-renderer.ts)
- **WebGL2 Shader with Full Context Recovery:** [recoverable-shader.ts](canvas-webgl-procedural/examples/webgl-shaders/recoverable-shader.ts)
- **Object-Pooled Particle System:** [pooled-particles.ts](canvas-webgl-procedural/examples/particle-systems/pooled-particles.ts)
- **Seeded Noise & Flow Field Generator:** [seeded-flow.ts](canvas-webgl-procedural/examples/procedural-patterns/seeded-flow.ts)
- **React Interactive Hero Integration:** [HeroCanvas.tsx](canvas-webgl-procedural/examples/interactive-hero/HeroCanvas.tsx)
