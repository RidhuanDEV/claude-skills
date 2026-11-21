---
name: shadow-illustration
description: "Full-Spectrum Visual, Illustration & Graphics Engineering. Use when creating, revising, or reviewing product illustrations, mascots, icons, technical diagrams, OG cards, HTML5 Canvas/WebGL/procedural art, raster/PNG/WebP/AVIF or SVG pipelines, print artwork, or Lottie/Rive motion handoffs."
---

# Shadow Illustration

## Start with the requested deliverable

1. Inspect screens, existing artwork and its source of truth, brand conventions, tools, actual renderer versions, asset registry, and verification paths. For an enhancement, compare what already exists against the requested capabilities before editing. Keep the approved master and existing integration contracts.
2. Record intended use, format, static versus animated versus interactive behavior, editability, target sizes, and available host capabilities. Apply [capability and format routing](references/cross-agent-capability-routing.md). Respect an explicit format and clarify only a consequential unresolved choice.
3. Establish a master and review one representative asset before expanding. Read only the applicable playbooks below. Include a reference comparison, contact sheet, or timeline frames when they help verify the requested work.
4. Deliver the requested sources and exports. Record provenance, runtime paths, and separate verification results using [export and handoff](references/asset-export-and-optimization.md).

| Task | Load |
|---|---|
| Define a style or review a visual family | [Art direction](references/art-direction.md), [composition and color](references/composition-and-color.md) |
| Create or revise a mascot or pose | [Character design](references/character-design.md) and the selected production method |
| Generate, edit, or export raster artwork | [Raster production](references/raster-production.md) |
| Draw editable SVG or fix path geometry | [Vector geometry](references/vector-geometry.md), [SVG authoring and rendering](references/svg-authoring-and-rendering.md) |
| Build HTML5 `<canvas>`, WebGL, GLSL shaders, particles, or procedural hero visuals | [Canvas, WebGL & procedural hub](references/canvas-webgl-procedural.md) (routes to 10 focused engineering modules + 5 strict-TS examples — load only the task-relevant modules) |
| Batch-generate OG cards, responsive `srcset`, favicons, PWA icons, or spritesheets via code | [Programmatic image pipelines](references/programmatic-image-pipelines.md) |
| Design UI icon systems, custom architecture diagrams, or annotated screenshots | [Iconography and diagrams](references/iconography-and-diagrams.md) |
| Manage sRGB/P3/CMYK print specs, alpha anti-halo, or safe SVGO optimization | [Color, print and optimization](references/color-print-and-optimization.md) |
| Animate a pose, transition, or frame sequence | [Motion design](references/motion-design-principles.md) and the target format reference |
| Export or debug Lottie JSON or dotLottie | [Lottie and dotLottie](references/lottie-and-dotlottie.md) |
| Design or deliver interactive motion for Rive | [Rive interactive animation](references/rive-interactive-animation.md) |
| Evaluate a new dependency or source | [Source register](references/open-source-source-register.md) |
| Validate the skill or a technical fixture | [Evaluation cases and evidence](evaluations.md) |

## Canvas, WebGL, Shaders & Procedural Visuals Reference Guide

Load the relevant reference documents when implementing or modifying visual rendering systems:

| Task | Reference |
|---|---|
| Choosing a rendering technology & 6-phase lifecycle | [renderer-selection.md](references/canvas-webgl-procedural/renderer-selection.md) |
| Canvas 2D drawing, Bézier curves, compositing & hit testing | [canvas-2d-techniques.md](references/canvas-webgl-procedural/canvas-2d-techniques.md) |
| Custom GLSL shaders, VAOs, instancing, FBOs & context recovery | [webgl-shaders.md](references/canvas-webgl-procedural/webgl-shaders.md) |
| Procedural noise, Poisson distributions & generative patterns | [procedural-generation.md](references/canvas-webgl-procedural/procedural-generation.md) |
| Animation, delta-time math, fixed timestep, springs & timelines | [animation-engineering.md](references/canvas-webgl-procedural/animation-engineering.md) |
| Mouse, touch, pointer events, gestures & interaction states | [interaction-patterns.md](references/canvas-webgl-procedural/interaction-patterns.md) |
| Rendering performance, object pooling, batching & GPU profiling | [performance-optimization.md](references/canvas-webgl-procedural/performance-optimization.md) |
| Accessibility, feature detection, fallback & reduced motion | [accessibility-and-fallback.md](references/canvas-webgl-procedural/accessibility-and-fallback.md) |
| Visual composition, focal hierarchy, color harmony & aesthetics | [visual-design-principles.md](references/canvas-webgl-procedural/visual-design-principles.md) |
| Testing, deterministic seeded rendering & visual verification | [testing-and-validation.md](references/canvas-webgl-procedural/testing-and-validation.md) |

Do not load unrelated references unnecessarily. Use multiple references when a task spans multiple domains. Production-ready strict-TS examples live under `references/canvas-webgl-procedural/examples/` ([layered-renderer.ts](references/canvas-webgl-procedural/examples/canvas-2d/layered-renderer.ts), [recoverable-shader.ts](references/canvas-webgl-procedural/examples/webgl-shaders/recoverable-shader.ts), [pooled-particles.ts](references/canvas-webgl-procedural/examples/particle-systems/pooled-particles.ts), [seeded-flow.ts](references/canvas-webgl-procedural/examples/procedural-patterns/seeded-flow.ts), [HeroCanvas.tsx](references/canvas-webgl-procedural/examples/interactive-hero/HeroCanvas.tsx)).

Use the host's available image tool for authorized raster generation. In Codex, load the installed imagegen skill when appropriate. For editable artwork, author deliberate paths and use the project's exporter. A text-only host delivers a brief, specification, or storyboard and identifies the unrun checks. Record actual host and tool evidence rather than assuming equivalent capabilities across agents.

This skill owns illustration direction, construction, exports, and visual review. Use Shadow Design for product journeys, components, and design tokens. Use Shadow Mobile or the project owner for platform integration. Use Shadow Accessibility for assistive-technology and interaction review. Shadow Monarch defines scope and execution permissions. Keep app copy and actions in live UI when the project requires it.

Report structural, visual, playback, integration, and provenance checks separately. A rendered PNG proves only the observed still. A parsed SVG or animation file cannot establish visual quality or runtime behavior.
